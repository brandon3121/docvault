from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Destination
from app.search import normalize_text


@dataclass(frozen=True)
class DestinationNode:
    id: int
    name: str
    parent_id: int | None
    depth: int
    path: str


def _children_by_parent(db: Session) -> dict[int | None, list[Destination]]:
    children: dict[int | None, list[Destination]] = defaultdict(list)
    for destination in db.scalars(select(Destination)):
        children[destination.parent_id].append(destination)
    for siblings in children.values():
        siblings.sort(key=lambda destination: normalize_text(destination.name) or "")
    return children


def load_destination_tree(db: Session) -> list[DestinationNode]:
    children = _children_by_parent(db)
    nodes: list[DestinationNode] = []

    def visit(parent_id: int | None, depth: int, prefix: str) -> None:
        for destination in children.get(parent_id, []):
            path = f"{prefix} / {destination.name}" if prefix else destination.name
            nodes.append(
                DestinationNode(destination.id, destination.name, destination.parent_id, depth, path)
            )
            visit(destination.id, depth + 1, path)

    visit(None, 0, "")
    return nodes


def descendant_ids(db: Session, root_id: int) -> set[int]:
    children = _children_by_parent(db)
    found = {root_id}
    pending = [root_id]
    while pending:
        for child in children.get(pending.pop(), []):
            if child.id not in found:
                found.add(child.id)
                pending.append(child.id)
    return found
