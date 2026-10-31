import pytest
from sqlalchemy import select

from app.models import Document

from .test_documents import make_pdf, origins, upload  # noqa: F401


@pytest.fixture
def document(client, origins):  # noqa: F811
    response = upload(client, origins, owner_full_name="Ana Prueba Ficticia", filename="borrable.pdf")
    assert response.status_code == 201
    return response.json()


def test_dba_deletes_document(client, login_as, document):
    login_as("dba", role="user")
    assert client.delete(f"/api/documents/{document['id']}").status_code == 204


def test_admin_with_other_username_cannot_delete(client, login_as, document):
    login_as("root", role="admin")
    assert client.delete(f"/api/documents/{document['id']}").status_code == 403


def test_regular_user_cannot_delete(client, login_as, document):
    login_as("bob", role="user")
    assert client.delete(f"/api/documents/{document['id']}").status_code == 403


def test_delete_requires_session(client, document):
    client.cookies.clear()
    assert client.delete(f"/api/documents/{document['id']}").status_code == 401


@pytest.mark.parametrize("username", ["DBA", "dba2", "dba "])
def test_similar_usernames_cannot_delete(client, login_as, document, username):
    login_as(username, role="admin")
    assert client.delete(f"/api/documents/{document['id']}").status_code == 403


def test_deleted_document_is_hidden_from_reads(client, login_as, document):
    document_id = document["id"]
    login_as("dba", role="user")
    assert client.delete(f"/api/documents/{document_id}").status_code == 204

    def listed(**params):
        return [item["id"] for item in client.get("/api/documents", params=params).json()["items"]]

    assert document_id not in listed()
    assert document_id not in listed(q="borrable")
    assert document_id not in listed(owner="Ana Prueba")
    assert document_id not in listed(destination_id=document["destination_id"])
    assert client.get(f"/api/documents/{document_id}").status_code == 404
    assert client.get(f"/api/documents/{document_id}/file").status_code == 404
    assert client.patch(f"/api/documents/{document_id}", json={"document_date": "2024-01-01"}).status_code == 404


def test_deleted_document_keeps_row_and_file(client, login_as, document, session_factory, storage_path):
    dba = login_as("dba", role="user")
    assert client.delete(f"/api/documents/{document['id']}").status_code == 204

    with session_factory() as db:
        row = db.scalar(select(Document).where(Document.id == document["id"]))
    assert row is not None
    assert row.deleted_at is not None
    assert row.deleted_by_id == dba.id
    assert (storage_path / row.storage_path).is_file()


def test_delete_twice_returns_404(client, login_as, document):
    login_as("dba", role="user")
    assert client.delete(f"/api/documents/{document['id']}").status_code == 204
    assert client.delete(f"/api/documents/{document['id']}").status_code == 404


def test_delete_unknown_document_returns_404(client, login_as):
    login_as("dba", role="user")
    assert client.delete("/api/documents/9999").status_code == 404


def test_other_documents_remain_visible(client, origins, login_as, document):  # noqa: F811
    other = upload(client, origins, content=make_pdf("visible"), filename="visible.pdf").json()
    login_as("dba", role="user")
    client.delete(f"/api/documents/{document['id']}")

    body = client.get("/api/documents").json()
    assert [item["id"] for item in body["items"]] == [other["id"]]
    assert body["total"] == 1


def test_reupload_after_delete_creates_new_document(
    client, origins, login_as, document, session_factory, storage_path  # noqa: F811
):
    login_as("dba", role="user")
    assert client.delete(f"/api/documents/{document['id']}").status_code == 204

    response = upload(client, origins, owner_full_name="Ana Prueba Ficticia", filename="borrable.pdf")
    assert response.status_code == 201
    reuploaded = response.json()
    assert reuploaded["id"] != document["id"]
    assert reuploaded["sha256"] == document["sha256"]

    with session_factory() as db:
        rows = db.scalars(select(Document).where(Document.sha256 == document["sha256"]).order_by(Document.id)).all()
    assert [(row.id, row.deleted_at is None) for row in rows] == [(document["id"], False), (reuploaded["id"], True)]
    assert (storage_path / rows[1].storage_path).is_file()
    assert client.get(f"/api/documents/{reuploaded['id']}/file").status_code == 200


def test_active_reupload_is_still_duplicate(client, origins, login_as, document):  # noqa: F811
    login_as("dba", role="user")
    client.delete(f"/api/documents/{document['id']}")
    reuploaded = upload(client, origins, owner_full_name="Ana Prueba Ficticia", filename="borrable.pdf").json()

    response = upload(client, origins, owner_full_name="Ana Prueba Ficticia", filename="borrable.pdf")
    assert response.status_code == 409
    assert response.json()["detail"]["document_id"] == reuploaded["id"]
