from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class DestinationIn(BaseModel):
    name: Name
    parent_id: int | None = None


class DestinationOut(BaseModel):
    id: int
    name: str
    parent_id: int | None
    depth: int
    path: str


class OwnerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str


class DocumentOut(BaseModel):
    id: int
    title: str
    document_type_id: int
    document_type_name: str
    destination_id: int
    destination_path: str
    owner_id: int | None
    owner_name: str | None
    owner_name_extracted: str | None
    owner_name_edited: bool
    document_date: date | None
    document_date_extracted: date | None
    document_date_edited: bool
    original_filename: str
    sha256: str
    uploaded_by: int
    uploaded_by_name: str
    uploaded_at: datetime


class DocumentPage(BaseModel):
    items: list[DocumentOut]
    total: int
    limit: int
    offset: int


class DocumentUpdate(BaseModel):
    destination_id: int | None = None
    owner_full_name: str | None = None
    document_date: date | None = None
