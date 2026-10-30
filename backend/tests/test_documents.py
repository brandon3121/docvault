import hashlib
from datetime import date, timedelta

import pytest

MINIMAL_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


def make_pdf(marker: str) -> bytes:
    return MINIMAL_PDF + f"% {marker}\n".encode()


@pytest.fixture
def catalogs(client, login_as):
    login_as()
    root = client.post("/api/destinations", json={"name": "Finanzas"}).json()
    child = client.post("/api/destinations", json={"name": "Facturas", "parent_id": root["id"]}).json()
    other = client.post("/api/destinations", json={"name": "Legal"}).json()
    document_type = client.post("/api/document-types", json={"name": "Contrato"}).json()
    return {"root": root, "child": child, "other": other, "type": document_type}


def upload(client, catalogs, content: bytes | None = None, filename: str = "doc.pdf", **fields):
    data = {
        "title": "Contrato de arrendamiento",
        "document_type_id": str(catalogs["type"]["id"]),
        "destination_id": str(catalogs["child"]["id"]),
    }
    data.update({key: str(value) for key, value in fields.items()})
    files = {"file": (filename, content if content is not None else make_pdf(filename), "application/pdf")}
    return client.post("/api/documents", data=data, files=files)


def test_upload_valid_pdf_stores_file_by_hash(client, catalogs, storage_path):
    content = make_pdf("valid")
    response = upload(client, catalogs, content=content)

    assert response.status_code == 201
    body = response.json()
    sha256 = hashlib.sha256(content).hexdigest()
    assert body["sha256"] == sha256
    assert body["destination_path"] == "Finanzas / Facturas"
    assert body["owner_name_edited"] is False
    assert body["document_date_edited"] is False
    stored = storage_path / "documents" / sha256[:2] / sha256[2:4] / f"{sha256}.pdf"
    assert stored.read_bytes() == content
    assert list((storage_path / "documents" / ".tmp").iterdir()) == []


def test_upload_non_pdf_returns_400(client, catalogs, storage_path):
    response = upload(client, catalogs, content=b"hello, not a pdf", filename="fake.pdf")
    assert response.status_code == 400
    assert list((storage_path / "documents" / ".tmp").iterdir()) == []


def test_upload_too_large_returns_413(client, catalogs):
    content = MINIMAL_PDF + b"0" * (1024 * 1024 + 1)
    assert upload(client, catalogs, content=content).status_code == 413


def test_upload_same_pdf_twice_returns_409_with_existing_id(client, catalogs):
    content = make_pdf("duplicate")
    first = upload(client, catalogs, content=content)
    second = upload(client, catalogs, content=content, title="Otro título")

    assert second.status_code == 409
    assert second.json()["detail"]["document_id"] == first.json()["id"]


def test_upload_future_date_returns_400(client, catalogs):
    tomorrow = date.today() + timedelta(days=1)
    assert upload(client, catalogs, document_date=tomorrow.isoformat()).status_code == 400


def test_upload_unknown_destination_returns_400(client, catalogs):
    assert upload(client, catalogs, destination_id=9999).status_code == 400


def test_upload_creates_owner_from_name(client, catalogs):
    response = upload(client, catalogs, owner_name="María López")
    assert response.status_code == 201
    assert response.json()["owner_name"] == "María López"
    owners = client.get("/api/owners", params={"q": "maria"}).json()
    assert [owner["full_name"] for owner in owners] == ["María López"]


def test_file_requires_session(client, catalogs):
    document_id = upload(client, catalogs).json()["id"]
    client.cookies.clear()
    assert client.get(f"/api/documents/{document_id}/file").status_code == 401


def test_file_is_served_inline(client, catalogs):
    content = make_pdf("inline")
    document_id = upload(client, catalogs, content=content, filename="contrato.pdf").json()["id"]
    response = client.get(f"/api/documents/{document_id}/file")

    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline")


def test_search_by_title(client, catalogs):
    upload(client, catalogs, title="Contrato de arrendamiento", filename="a.pdf")
    upload(client, catalogs, title="Factura de luz", filename="b.pdf")

    body = client.get("/api/documents", params={"q": "arrendam"}).json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Contrato de arrendamiento"


def test_search_escapes_fts_syntax(client, catalogs):
    upload(client, catalogs, title="Contrato AND anexo", filename="a.pdf")
    for query in ['"', "NEAR(", "AND", "*", "-anexo", "contrato OR"]:
        assert client.get("/api/documents", params={"q": query}).status_code == 200


def test_search_reflects_title_updates(client, catalogs):
    document_id = upload(client, catalogs, title="Borrador").json()["id"]
    client.patch(f"/api/documents/{document_id}", json={"title": "Escritura definitiva"})

    assert client.get("/api/documents", params={"q": "borrador"}).json()["total"] == 0
    assert client.get("/api/documents", params={"q": "escritura"}).json()["total"] == 1


def test_owner_filter(client, catalogs):
    upload(client, catalogs, owner_name="José Pérez", filename="a.pdf")
    upload(client, catalogs, owner_name="Ana Gómez", filename="b.pdf")
    upload(client, catalogs, filename="c.pdf")

    body = client.get("/api/documents", params={"owner": "perez"}).json()
    assert [item["owner_name"] for item in body["items"]] == ["José Pérez"]


def test_date_range_filter(client, catalogs):
    upload(client, catalogs, title="Enero", document_date="2024-01-15", filename="a.pdf")
    upload(client, catalogs, title="Marzo", document_date="2024-03-10", filename="b.pdf")
    upload(client, catalogs, title="Junio", document_date="2024-06-01", filename="c.pdf")
    upload(client, catalogs, title="Sin fecha", filename="d.pdf")

    body = client.get("/api/documents", params={"date_from": "2024-02-01", "date_to": "2024-06-01"}).json()
    assert [item["title"] for item in body["items"]] == ["Junio", "Marzo"]


def test_destination_filter_includes_children(client, catalogs):
    upload(client, catalogs, title="En hijo", filename="a.pdf")
    upload(client, catalogs, title="En otro", destination_id=catalogs["other"]["id"], filename="b.pdf")

    body = client.get("/api/documents", params={"destination_id": catalogs["root"]["id"]}).json()
    assert [item["title"] for item in body["items"]] == ["En hijo"]


def test_list_orders_by_date_desc_and_caps_limit(client, catalogs):
    upload(client, catalogs, title="Viejo", document_date="2020-01-01", filename="a.pdf")
    upload(client, catalogs, title="Sin fecha", filename="b.pdf")
    upload(client, catalogs, title="Nuevo", document_date="2023-01-01", filename="c.pdf")

    body = client.get("/api/documents", params={"limit": 500}).json()
    assert body["limit"] == 100
    assert [item["title"] for item in body["items"]] == ["Nuevo", "Viejo", "Sin fecha"]


def test_patch_marks_owner_name_edited(client, catalogs):
    document_id = upload(client, catalogs).json()["id"]
    response = client.patch(f"/api/documents/{document_id}", json={"owner_name": "Laura Ruiz"})

    assert response.status_code == 200
    body = response.json()
    assert body["owner_name"] == "Laura Ruiz"
    assert body["owner_name_edited"] is True
    assert body["document_date_edited"] is False


def test_patch_future_date_returns_400(client, catalogs):
    document_id = upload(client, catalogs).json()["id"]
    tomorrow = date.today() + timedelta(days=1)
    response = client.patch(f"/api/documents/{document_id}", json={"document_date": tomorrow.isoformat()})
    assert response.status_code == 400


def test_patch_by_other_regular_user_returns_403(client, catalogs, login_as):
    document_id = upload(client, catalogs).json()["id"]
    login_as(username="bob", role="user")
    response = client.patch(f"/api/documents/{document_id}", json={"title": "Cambio"})
    assert response.status_code == 403


def test_delete_catalog_with_documents_returns_409(client, catalogs):
    upload(client, catalogs)
    assert client.delete(f"/api/destinations/{catalogs['child']['id']}").status_code == 409
    assert client.delete(f"/api/document-types/{catalogs['type']['id']}").status_code == 409
    assert client.delete(f"/api/destinations/{catalogs['other']['id']}").status_code == 204
