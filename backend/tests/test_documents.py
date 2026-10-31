import hashlib
from datetime import date, timedelta

import pytest

from app.validation import DOCUMENT_DATE_RANGE_MESSAGE, OWNER_NAME_WORDS_MESSAGE

MINIMAL_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


def make_pdf(marker: str) -> bytes:
    return MINIMAL_PDF + f"% {marker}\n".encode()


@pytest.fixture
def origins(client, login_as):
    login_as()
    root = client.post("/api/destinations", json={"name": "Matriz"}).json()
    branch = client.post("/api/destinations", json={"name": "Sucursal Norte", "parent_id": root["id"]}).json()
    other = client.post("/api/destinations", json={"name": "Almacén"}).json()
    return {"root": root, "branch": branch, "other": other}


def upload(client, origins, content: bytes | None = None, filename: str = "carta.pdf", **fields):
    data = {
        "destination_id": str(origins["branch"]["id"]),
        "owner_full_name": "Juan García",
    }
    data.update({key: str(value) for key, value in fields.items() if value is not None})
    files = {"file": (filename, content if content is not None else make_pdf(filename), "application/pdf")}
    return client.post("/api/documents", data=data, files=files)


def test_upload_without_title_uses_filename(client, origins, storage_path):
    content = make_pdf("valid")
    response = upload(client, origins, content=content, filename="Carta laptop Dell.pdf")

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Carta laptop Dell"
    assert body["original_filename"] == "Carta laptop Dell.pdf"
    sha256 = hashlib.sha256(content).hexdigest()
    assert body["sha256"] == sha256
    assert body["destination_path"] == "Matriz / Sucursal Norte"
    assert body["owner_name_edited"] is False
    assert body["document_date_edited"] is False
    stored = storage_path / "documents" / sha256[:2] / sha256[2:4] / f"{sha256}.pdf"
    assert stored.read_bytes() == content
    assert list((storage_path / "documents" / ".tmp").iterdir()) == []


def test_upload_assigns_responsive_letter_type(client, origins):
    body = upload(client, origins).json()
    assert body["document_type_name"] == "Carta responsiva"


def test_upload_ignores_document_type_id(client, origins):
    response = upload(client, origins, document_type_id=9999)
    assert response.status_code == 201
    assert response.json()["document_type_name"] == "Carta responsiva"


def test_upload_requires_owner(client, origins):
    data = {"destination_id": str(origins["branch"]["id"])}
    files = {"file": ("a.pdf", make_pdf("no-owner"), "application/pdf")}
    assert client.post("/api/documents", data=data, files=files).status_code == 400


def test_upload_single_word_owner_returns_400(client, origins):
    response = upload(client, origins, owner_full_name="  Juan  ")
    assert response.status_code == 400
    assert response.json()["detail"] == OWNER_NAME_WORDS_MESSAGE


def test_owner_name_is_cleaned_and_kept_as_written(client, origins):
    response = upload(client, origins, owner_full_name="  María   de la  Luz  Ríos ")
    assert response.json()["owner_name"] == "María de la Luz Ríos"


def test_owner_is_reused_ignoring_accents_case_and_spaces(client, origins):
    first = upload(client, origins, owner_full_name="José Pérez", filename="a.pdf").json()
    second = upload(client, origins, owner_full_name="jose  perez", filename="b.pdf").json()

    assert first["owner_id"] == second["owner_id"]
    assert second["owner_name"] == "José Pérez"
    assert len(client.get("/api/owners", params={"q": "perez"}).json()) == 1


def test_upload_non_pdf_returns_400(client, origins, storage_path):
    response = upload(client, origins, content=b"hello, not a pdf", filename="fake.pdf")
    assert response.status_code == 400
    assert list((storage_path / "documents" / ".tmp").iterdir()) == []


def test_upload_too_large_returns_413(client, origins):
    content = MINIMAL_PDF + b"0" * (1024 * 1024 + 1)
    assert upload(client, origins, content=content).status_code == 413


def test_upload_same_pdf_twice_returns_409_with_existing_id(client, origins):
    content = make_pdf("duplicate")
    first = upload(client, origins, content=content)
    second = upload(client, origins, content=content, filename="copia.pdf")

    assert second.status_code == 409
    assert second.json()["detail"]["document_id"] == first.json()["id"]


def test_upload_date_one_year_ago_is_accepted(client, origins):
    last_year = date.today() - timedelta(days=365)
    response = upload(client, origins, document_date=last_year.isoformat())
    assert response.status_code == 201
    assert response.json()["document_date"] == last_year.isoformat()


def test_upload_year_0266_returns_400(client, origins):
    response = upload(client, origins, document_date="0266-05-10")
    assert response.status_code == 400
    assert response.json()["detail"] == DOCUMENT_DATE_RANGE_MESSAGE


def test_upload_date_before_2000_returns_400(client, origins):
    response = upload(client, origins, document_date="1999-12-31")
    assert response.status_code == 400
    assert response.json()["detail"] == DOCUMENT_DATE_RANGE_MESSAGE


def test_upload_first_day_of_2000_is_accepted(client, origins):
    response = upload(client, origins, document_date="2000-01-01")
    assert response.status_code == 201
    assert response.json()["document_date"] == "2000-01-01"


def test_upload_today_is_accepted(client, origins):
    assert upload(client, origins, document_date=date.today().isoformat()).status_code == 201


def test_upload_without_date_is_accepted(client, origins):
    response = upload(client, origins)
    assert response.status_code == 201
    assert response.json()["document_date"] is None


def test_upload_future_date_returns_400(client, origins):
    tomorrow = date.today() + timedelta(days=1)
    assert upload(client, origins, document_date=tomorrow.isoformat()).status_code == 400


def test_upload_invalid_date_format_returns_400(client, origins):
    assert upload(client, origins, document_date="15/03/2024").status_code == 400


def test_upload_unknown_origin_returns_400(client, origins):
    assert upload(client, origins, destination_id=9999).status_code == 400


def test_upload_requires_origin(client, origins):
    data = {"owner_full_name": "Juan García"}
    files = {"file": ("a.pdf", make_pdf("no-origin"), "application/pdf")}
    assert client.post("/api/documents", data=data, files=files).status_code == 400


def test_file_requires_session(client, origins):
    document_id = upload(client, origins).json()["id"]
    client.cookies.clear()
    assert client.get(f"/api/documents/{document_id}/file").status_code == 401


def test_file_is_served_inline(client, origins):
    content = make_pdf("inline")
    document_id = upload(client, origins, content=content, filename="carta.pdf").json()["id"]
    response = client.get(f"/api/documents/{document_id}/file")

    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline")


def test_filename_query_parameter_is_ignored(client, origins):
    laptop = upload(client, origins, filename="Carta laptop Dell.pdf").json()
    monitor = upload(client, origins, filename="Carta monitor.pdf").json()

    body = client.get("/api/documents", params={"q": "lapt"}).json()
    assert body["total"] == 2
    assert {item["id"] for item in body["items"]} == {laptop["id"], monitor["id"]}
    for query in ['"', "NEAR(", "AND", "*"]:
        assert client.get("/api/documents", params={"q": query}).json()["total"] == 2


def test_remaining_filters_work_together(client, origins):
    match = upload(
        client, origins, filename="a.pdf", owner_full_name="Laura Pérez", document_date="2024-03-10"
    ).json()
    upload(client, origins, filename="b.pdf", owner_full_name="Laura Pérez", document_date="2023-03-10")
    upload(client, origins, filename="c.pdf", owner_full_name="Juan García", document_date="2024-03-10")
    upload(
        client,
        origins,
        filename="d.pdf",
        owner_full_name="Laura Pérez",
        document_date="2024-03-10",
        destination_id=origins["other"]["id"],
    )

    body = client.get(
        "/api/documents",
        params={
            "owner": "laura perez",
            "destination_id": origins["root"]["id"],
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
            "q": "b",
        },
    ).json()
    assert [item["id"] for item in body["items"]] == [match["id"]]


def test_owner_filter(client, origins):
    upload(client, origins, owner_full_name="José Pérez", filename="a.pdf")
    upload(client, origins, owner_full_name="Ana Gómez", filename="b.pdf")

    body = client.get("/api/documents", params={"owner": "perez"}).json()
    assert [item["owner_name"] for item in body["items"]] == ["José Pérez"]


def test_date_range_filter(client, origins):
    upload(client, origins, document_date="2024-01-15", filename="enero.pdf")
    upload(client, origins, document_date="2024-03-10", filename="marzo.pdf")
    upload(client, origins, document_date="2024-06-01", filename="junio.pdf")
    upload(client, origins, filename="sin-fecha.pdf")

    body = client.get("/api/documents", params={"date_from": "2024-02-01", "date_to": "2024-06-01"}).json()
    assert [item["title"] for item in body["items"]] == ["junio", "marzo"]


def test_origin_filter_includes_branches(client, origins):
    upload(client, origins, filename="en-sucursal.pdf")
    upload(client, origins, destination_id=origins["other"]["id"], filename="en-almacen.pdf")

    body = client.get("/api/documents", params={"destination_id": origins["root"]["id"]}).json()
    assert [item["title"] for item in body["items"]] == ["en-sucursal"]


def test_list_orders_by_date_desc_and_caps_limit(client, origins):
    upload(client, origins, document_date="2020-01-01", filename="viejo.pdf")
    upload(client, origins, filename="sin-fecha.pdf")
    upload(client, origins, document_date="2023-01-01", filename="nuevo.pdf")

    body = client.get("/api/documents", params={"limit": 500}).json()
    assert body["limit"] == 100
    assert [item["title"] for item in body["items"]] == ["nuevo", "viejo", "sin-fecha"]


def test_patch_owner_marks_owner_name_edited(client, origins):
    document_id = upload(client, origins).json()["id"]
    response = client.patch(f"/api/documents/{document_id}", json={"owner_full_name": "Laura  Ruiz"})

    assert response.status_code == 200
    body = response.json()
    assert body["owner_name"] == "Laura Ruiz"
    assert body["owner_name_edited"] is True
    assert body["document_date_edited"] is False


def test_patch_single_word_owner_returns_400(client, origins):
    document_id = upload(client, origins).json()["id"]
    response = client.patch(f"/api/documents/{document_id}", json={"owner_full_name": "Laura"})
    assert response.status_code == 400
    assert response.json()["detail"] == OWNER_NAME_WORDS_MESSAGE


def test_patch_year_0266_returns_400(client, origins):
    document_id = upload(client, origins, document_date="2020-01-01").json()["id"]
    response = client.patch(f"/api/documents/{document_id}", json={"document_date": "0266-05-10"})
    assert response.status_code == 400
    assert response.json()["detail"] == DOCUMENT_DATE_RANGE_MESSAGE
    assert client.get(f"/api/documents/{document_id}").json()["document_date"] == "2020-01-01"


def test_patch_origin_and_date(client, origins):
    document_id = upload(client, origins).json()["id"]
    response = client.patch(
        f"/api/documents/{document_id}",
        json={"destination_id": origins["other"]["id"], "document_date": "2022-05-05"},
    )

    body = response.json()
    assert body["destination_path"] == "Almacén"
    assert body["document_date"] == "2022-05-05"
    assert body["document_date_edited"] is True


def test_patch_future_date_returns_400(client, origins):
    document_id = upload(client, origins).json()["id"]
    tomorrow = date.today() + timedelta(days=1)
    response = client.patch(f"/api/documents/{document_id}", json={"document_date": tomorrow.isoformat()})
    assert response.status_code == 400
    assert response.json()["detail"] == DOCUMENT_DATE_RANGE_MESSAGE


def test_patch_by_other_regular_user_returns_403(client, origins, login_as):
    document_id = upload(client, origins).json()["id"]
    login_as(username="bob", role="user")
    response = client.patch(f"/api/documents/{document_id}", json={"document_date": "2022-01-01"})
    assert response.status_code == 403


def test_delete_origin_with_documents_returns_409(client, origins):
    upload(client, origins)
    assert client.delete(f"/api/destinations/{origins['branch']['id']}").status_code == 409
    assert client.delete(f"/api/destinations/{origins['other']['id']}").status_code == 204
