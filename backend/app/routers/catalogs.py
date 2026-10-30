from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db, require_admin
from app.destinations import DestinationNode, descendant_ids, load_destination_tree
from app.models import Destination, Document, Owner
from app.schemas import DestinationIn, DestinationOut, OwnerOut
from app.search import contains_pattern

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
    destination.name = payload.name
    if "parent_id" in payload.model_fields_set:
        _validate_parent(db, payload.parent_id, destination_id)
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


@router.get("/owners", response_model=list[OwnerOut], dependencies=[Depends(get_current_user)])
def list_owners(q: str | None = Query(None, max_length=255), db: Session = Depends(get_db)) -> list[Owner]:
    query = select(Owner).order_by(func.normalize_text(Owner.full_name)).limit(OWNER_SEARCH_LIMIT)
    if q and q.strip():
        query = query.where(func.normalize_text(Owner.full_name).like(contains_pattern(q), escape="\\"))
    return list(db.scalars(query))
