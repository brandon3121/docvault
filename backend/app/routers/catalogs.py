from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db, require_admin
from app.destinations import DestinationNode, descendant_ids, load_destination_tree
from app.models import Destination, Document, DocumentType, Owner
from app.schemas import (
    DestinationIn,
    DestinationOut,
    DocumentTypeIn,
    DocumentTypeOut,
    OwnerIn,
    OwnerOut,
)
from app.search import contains_pattern, normalize_text

router = APIRouter(prefix="/api", tags=["catalogs"])

OWNER_SEARCH_LIMIT = 20


def _not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{resource} not found")


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _any_row(db: Session, *condition) -> bool:
    return bool(db.scalar(select(exists().where(*condition))))


def _destination_out(db: Session, destination_id: int) -> DestinationNode:
    return next(node for node in load_destination_tree(db) if node.id == destination_id)


def _validate_parent(db: Session, parent_id: int | None, destination_id: int | None = None) -> None:
    if parent_id is None:
        return
    if db.get(Destination, parent_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent destination not found")
    if destination_id is not None and parent_id in descendant_ids(db, destination_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A destination cannot be moved under itself or its descendants",
        )


@router.get("/destinations", response_model=list[DestinationOut], dependencies=[Depends(get_current_user)])
def list_destinations(db: Session = Depends(get_db)) -> list[DestinationNode]:
    return load_destination_tree(db)


@router.post(
    "/destinations",
    response_model=DestinationOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_destination(payload: DestinationIn, db: Session = Depends(get_db)) -> DestinationNode:
    _validate_parent(db, payload.parent_id)
    destination = Destination(name=payload.name, parent_id=payload.parent_id)
    db.add(destination)
    db.commit()
    return _destination_out(db, destination.id)


@router.put("/destinations/{destination_id}", response_model=DestinationOut, dependencies=[Depends(require_admin)])
def update_destination(destination_id: int, payload: DestinationIn, db: Session = Depends(get_db)) -> DestinationNode:
    destination = db.get(Destination, destination_id)
    if destination is None:
        raise _not_found("Destination")
    _validate_parent(db, payload.parent_id, destination_id)
    destination.name = payload.name
    destination.parent_id = payload.parent_id
    db.commit()
    return _destination_out(db, destination.id)


@router.delete(
    "/destinations/{destination_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_destination(destination_id: int, db: Session = Depends(get_db)) -> Response:
    destination = db.get(Destination, destination_id)
    if destination is None:
        raise _not_found("Destination")
    if _any_row(db, Document.destination_id == destination_id):
        raise _conflict("Destination has documents")
    if _any_row(db, Destination.parent_id == destination_id):
        raise _conflict("Destination has child destinations")
    db.delete(destination)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _ensure_unique_type_name(db: Session, name: str, exclude_id: int | None = None) -> None:
    query = select(DocumentType.id).where(func.normalize_text(DocumentType.name) == normalize_text(name))
    if exclude_id is not None:
        query = query.where(DocumentType.id != exclude_id)
    if db.scalar(query) is not None:
        raise _conflict("Document type already exists")


@router.get("/document-types", response_model=list[DocumentTypeOut], dependencies=[Depends(get_current_user)])
def list_document_types(db: Session = Depends(get_db)) -> list[DocumentType]:
    return list(db.scalars(select(DocumentType).order_by(func.normalize_text(DocumentType.name))))


@router.post(
    "/document-types",
    response_model=DocumentTypeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_document_type(payload: DocumentTypeIn, db: Session = Depends(get_db)) -> DocumentType:
    _ensure_unique_type_name(db, payload.name)
    document_type = DocumentType(name=payload.name)
    db.add(document_type)
    db.commit()
    return document_type


@router.put("/document-types/{type_id}", response_model=DocumentTypeOut, dependencies=[Depends(require_admin)])
def update_document_type(type_id: int, payload: DocumentTypeIn, db: Session = Depends(get_db)) -> DocumentType:
    document_type = db.get(DocumentType, type_id)
    if document_type is None:
        raise _not_found("Document type")
    _ensure_unique_type_name(db, payload.name, exclude_id=type_id)
    document_type.name = payload.name
    db.commit()
    return document_type


@router.delete(
    "/document-types/{type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_document_type(type_id: int, db: Session = Depends(get_db)) -> Response:
    document_type = db.get(DocumentType, type_id)
    if document_type is None:
        raise _not_found("Document type")
    if _any_row(db, Document.document_type_id == type_id):
        raise _conflict("Document type has documents")
    db.delete(document_type)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/owners", response_model=list[OwnerOut], dependencies=[Depends(get_current_user)])
def list_owners(q: str | None = Query(None, max_length=255), db: Session = Depends(get_db)) -> list[Owner]:
    query = select(Owner).order_by(func.normalize_text(Owner.full_name)).limit(OWNER_SEARCH_LIMIT)
    if q and q.strip():
        query = query.where(func.normalize_text(Owner.full_name).like(contains_pattern(q), escape="\\"))
    return list(db.scalars(query))


@router.post(
    "/owners",
    response_model=OwnerOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_owner(payload: OwnerIn, db: Session = Depends(get_db)) -> Owner:
    owner = Owner(full_name=payload.full_name, department=payload.department or None)
    db.add(owner)
    db.commit()
    return owner


@router.put("/owners/{owner_id}", response_model=OwnerOut, dependencies=[Depends(require_admin)])
def update_owner(owner_id: int, payload: OwnerIn, db: Session = Depends(get_db)) -> Owner:
    owner = db.get(Owner, owner_id)
    if owner is None:
        raise _not_found("Owner")
    owner.full_name = payload.full_name
    owner.department = payload.department or None
    db.commit()
    return owner


@router.delete("/owners/{owner_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_owner(owner_id: int, db: Session = Depends(get_db)) -> Response:
    owner = db.get(Owner, owner_id)
    if owner is None:
        raise _not_found("Owner")
    if _any_row(db, Document.owner_id == owner_id):
        raise _conflict("Owner has documents")
    db.delete(owner)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
