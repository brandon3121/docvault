from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.models import Document

from .test_documents import origins, upload  # noqa: F401


def parse_api_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_upload_returns_uploaded_at_with_utc_zone(client, origins, session_factory):  # noqa: F811
    before = datetime.now(timezone.utc)
    body = upload(client, origins).json()
    after = datetime.now(timezone.utc)

    uploaded_at = parse_api_datetime(body["uploaded_at"])
    assert body["uploaded_at"].endswith(("Z", "+00:00"))
    assert uploaded_at.utcoffset() == timedelta(0)
    assert before <= uploaded_at <= after

    with session_factory() as db:
        stored = db.scalar(select(Document.uploaded_at).where(Document.id == body["id"]))
    assert stored.replace(tzinfo=timezone.utc) == uploaded_at


def test_stored_uploaded_at_without_zone_is_serialized_as_utc(client, origins, session_factory):  # noqa: F811
    document_id = upload(client, origins).json()["id"]
    # 18:36 in Mexico City on 1 Nov 2026 is 00:36 UTC on 2 Nov 2026.
    with session_factory() as db:
        db.execute(update(Document).where(Document.id == document_id).values(uploaded_at=datetime(2026, 11, 2, 0, 36)))
        db.commit()

    detail = client.get(f"/api/documents/{document_id}").json()
    listed = client.get("/api/documents").json()["items"][0]

    for value in (detail["uploaded_at"], listed["uploaded_at"]):
        assert parse_api_datetime(value) == datetime(2026, 11, 2, 0, 36, tzinfo=timezone.utc)
        assert value.endswith(("Z", "+00:00"))
