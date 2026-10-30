from datetime import date, datetime
from pathlib import PureWindowsPath

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import Select, and_, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.deps import get_current_user, get_db
from app.destinations import descendant_ids, load_destination_tree
from app.models import Destination, Document, DocumentType, Owner, User
from app.schemas import DocumentOut, DocumentPage, DocumentUpdate
from app.search import build_fts_query, collapse_spaces, contains_pattern, normalize_text
from app.storage import (
    InvalidPdfError,
    UploadTooLargeError,
    commit_spooled_file,
    resolve_document_path,
    spool_pdf,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_PAGE_SIZE = 100
TITLE_MAX_LENGTH = 500
OWNER_NAME_MAX_LENGTH = 255
RESPONSIVE_LETTER_TYPE = "Carta responsiva"


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _duplicate(document_id: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"message": "Document already exists", "document_id": document_id},
    )


def _parse_optional_int(value: str | None, field: str) -> int | None:
    if value is None or not value.strip():
        return None
    try:
        return int(value)
    except ValueError:
        raise _bad_request(f"{field} must be an integer") from None


def _parse_optional_date(value: str | None) -> date | None:
    if value is None or not value.strip():
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise _bad_request("document_date must use the YYYY-MM-DD format") from None


def _validate_document_date(value: date | None) -> date | None:
    if value is not None and value > date.today():
        raise _bad_request("document_date cannot be in the future")
    return value


def _require_existing(db: Session, model: type, object_id: int, field: str) -> None:
    if db.get(model, object_id) is None:
        raise _bad_request(f"{field} does not exist")


def _clean_owner_full_name(value: str | None) -> str:
    cleaned = collapse_spaces(value)
    if not cleaned:
        raise _bad_request("owner_full_name is required")
    if len(cleaned.split(" ")) < 2:
        raise _bad_request("owner_full_name must include at least a first name and a last name")
    if len(cleaned) > OWNER_NAME_MAX_LENGTH:
        raise _bad_request(f"owner_full_name must be at most {OWNER_NAME_MAX_LENGTH} characters")
    return cleaned


def _get_or_create_owner(db: Session, full_name: str) -> Owner:
    owner = db.scalar(
        select(Owner)
        .where(func.normalize_text(Owner.full_name) == normalize_text(full_name))
        .order_by(Owner.id)
        .limit(1)
    )
    if owner is None:
        owner = Owner(full_name=full_name)
        db.add(owner)
        db.flush()
    return owner


def _responsive_letter_type_id(db: Session) -> int:
    type_id = db.scalar(select(DocumentType.id).where(DocumentType.name == RESPONSIVE_LETTER_TYPE))
    if type_id is None:
        raise RuntimeError(f"Document type '{RESPONSIVE_LETTER_TYPE}' is missing; run the migrations")
    return type_id


def _safe_filename(filename: str | None, sha256: str) -> str:
    name = PureWindowsPath(filename or "").name.strip()
    return name or f"{sha256}.pdf"


def _title_from_filename(filename: str) -> str:
    stem = PureWindowsPath(filename).stem.strip() or filename
    return stem[:TITLE_MAX_LENGTH]


def _owner_name_differs(owner: Owner | None, extracted_name: str | None) -> bool:
    current_name = owner.full_name if owner else None
    return normalize_text(current_name) != normalize_text(extracted_name)


def _with_relations(query: Select) -> Select:
    return query.options(
        joinedload(Document.document_type),
        joinedload(Document.owner),
        joinedload(Document.uploader),
    )


def _get_document(db: Session, document_id: int) -> Document:
    document = db.scalar(_with_relations(select(Document)).where(Document.id == document_id))
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


def _destination_paths(db: Session) -> dict[int, str]:
    return {node.id: node.path for node in load_destination_tree(db)}


def _to_out(document: Document, destination_paths: dict[int, str]) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        title=document.title,
        document_type_id=document.document_type_id,
        document_type_name=document.document_type.name,
        destination_id=document.destination_id,
        destination_path=destination_paths.get(document.destination_id, ""),
        owner_id=document.owner_id,
        owner_name=document.owner.full_name if document.owner else document.owner_name_extracted,
        owner_name_extracted=document.owner_name_extracted,
        owner_name_edited=document.owner_name_edited,
        document_date=document.document_date,
        document_date_extracted=document.document_date_extracted,
        document_date_edited=document.document_date_edited,
        original_filename=document.original_filename,
        sha256=document.sha256,
        uploaded_by=document.uploaded_by,
        uploaded_by_name=document.uploader.full_name,
        uploaded_at=document.uploaded_at,
    )


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def create_document(
    file: UploadFile = File(...),
    destination_id: str | None = Form(None),
    owner_full_name: str | None = Form(None),
    document_date: str | None = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentOut:
    target_destination_id = _parse_optional_int(destination_id, "destination_id")
    if target_destination_id is None:
        raise _bad_request("destination_id is required")
    _require_existing(db, Destination, target_destination_id, "destination_id")
    owner_name = _clean_owner_full_name(owner_full_name)
    parsed_date = _validate_document_date(_parse_optional_date(document_date))
    type_id = _responsive_letter_type_id(db)

    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    try:
        temp_path, sha256 = spool_pdf(file.file, max_bytes)
    except InvalidPdfError:
        raise _bad_request("The file is not a PDF") from None
    except UploadTooLargeError:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"The file exceeds {get_settings().max_upload_mb} MB",
        ) from None

    existing_id = db.scalar(select(Document.id).where(Document.sha256 == sha256))
    if existing_id is not None:
        temp_path.unlink(missing_ok=True)
        raise _duplicate(existing_id)

    original_filename = _safe_filename(file.filename, sha256)
    relative_path, file_already_existed = commit_spooled_file(temp_path, sha256)
    try:
        owner = _get_or_create_owner(db, owner_name)
        document = Document(
            title=_title_from_filename(original_filename),
            document_type_id=type_id,
            destination_id=target_destination_id,
            owner_id=owner.id,
            owner_name_extracted=None,
            owner_name_edited=False,
            document_date=parsed_date,
            document_date_extracted=None,
            document_date_edited=False,
            original_filename=original_filename,
            storage_path=relative_path,
            sha256=sha256,
            extracted_text=None,
            uploaded_by=user.id,
        )
        db.add(document)
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_id = db.scalar(select(Document.id).where(Document.sha256 == sha256))
        if existing_id is not None:
            raise _duplicate(existing_id) from None
        if not file_already_existed:
            resolve_document_path(relative_path).unlink(missing_ok=True)
        raise
    except BaseException:
        db.rollback()
        if not file_already_existed:
            resolve_document_path(relative_path).unlink(missing_ok=True)
        raise

    return _to_out(_get_document(db, document.id), _destination_paths(db))


@router.get("", response_model=DocumentPage)
def list_documents(
    q: str | None = Query(None, max_length=500),
    owner: str | None = Query(None, max_length=255),
    destination_id: int | None = None,
    document_type_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentPage:
    limit = min(limit, MAX_PAGE_SIZE)
    query = select(Document).outerjoin(Owner, Document.owner_id == Owner.id)

    fts_query = build_fts_query(q) if q else None
    if fts_query:
        matches = (
            text("SELECT rowid FROM document_fts WHERE document_fts MATCH :fts")
            .bindparams(fts=fts_query)
            .columns(Document.id)
        )
        query = query.where(Document.id.in_(matches))
    if owner and owner.strip():
        pattern = contains_pattern(owner)
        query = query.where(
            or_(
                func.normalize_text(Owner.full_name).like(pattern, escape="\\"),
                and_(
                    Document.owner_id.is_(None),
                    func.normalize_text(Document.owner_name_extracted).like(pattern, escape="\\"),
                ),
            )
        )
    if destination_id is not None:
        query = query.where(Document.destination_id.in_(descendant_ids(db, destination_id)))
    if document_type_id is not None:
        query = query.where(Document.document_type_id == document_type_id)
    if date_from is not None:
        query = query.where(Document.document_date >= date_from)
    if date_to is not None:
        query = query.where(Document.document_date <= date_to)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    documents = db.scalars(
        _with_relations(query)
        .order_by(
            Document.document_date.desc().nulls_last(),
            Document.uploaded_at.desc(),
            Document.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    ).all()

    paths = _destination_paths(db)
    return DocumentPage(
        items=[_to_out(document, paths) for document in documents],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentOut:
    return _to_out(_get_document(db, document_id), _destination_paths(db))


@router.get("/{document_id}/file")
def get_document_file(
    document_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    path = resolve_document_path(document.storage_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=document.original_filename,
        content_disposition_type="inline",
    )


@router.patch("/{document_id}", response_model=DocumentOut)
def update_document(
    document_id: int,
    payload: DocumentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentOut:
    document = _get_document(db, document_id)
    if user.role != "admin" and document.uploaded_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to edit this document")

    changes = payload.model_fields_set
    if "destination_id" in changes:
        if payload.destination_id is None:
            raise _bad_request("destination_id is required")
        _require_existing(db, Destination, payload.destination_id, "destination_id")
        document.destination_id = payload.destination_id
    if "owner_full_name" in changes:
        owner = _get_or_create_owner(db, _clean_owner_full_name(payload.owner_full_name))
        document.owner_id = owner.id
        document.owner = owner
        document.owner_name_edited = _owner_name_differs(owner, document.owner_name_extracted)
    if "document_date" in changes:
        document.document_date = _validate_document_date(payload.document_date)
        document.document_date_edited = document.document_date != document.document_date_extracted

    db.commit()
    return _to_out(_get_document(db, document_id), _destination_paths(db))
