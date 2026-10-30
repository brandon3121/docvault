import shutil
from datetime import date

import pymupdf
import pytest

from app import extraction
from app.extraction import parse_date, parse_owner, suggest

from .test_documents import make_pdf, origins, upload  # noqa: F401

LETTER_TEXT = """GRUPO EJEMPLO
CARTA RESPONSIVA
Fecha: 25/02/2026
Acepto recibir el equipo descrito y me hago responsable de su uso.
Entrega Recibe
__________________ __________________
Ana Prueba Ficticia
Seguridad
"""

requires_tesseract = pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract is not installed")


def image_only_pdf(text: str) -> bytes:
    with pymupdf.open() as source:
        page = source.new_page(width=595, height=842)
        page.insert_text((60, 80), text, fontsize=14)
        pixmap = page.get_pixmap(dpi=200, colorspace=pymupdf.csGRAY)
    with pymupdf.open() as scanned:
        scanned.new_page(width=595, height=842).insert_image(pymupdf.Rect(0, 0, 595, 842), pixmap=pixmap)
        return scanned.tobytes(garbage=3, deflate=True)


def text_layer_pdf(text: str) -> bytes:
    with pymupdf.open() as document:
        document.new_page(width=595, height=842).insert_text((60, 80), text, fontsize=12)
        return document.tobytes()


def test_parse_letter_date_and_owner():
    assert parse_date(LETTER_TEXT) == date(2026, 2, 25)
    assert parse_owner(LETTER_TEXT) == "Ana Prueba Ficticia"


def test_parse_date_tolerates_spaces_and_dashes():
    assert parse_date("fecha :  03 - 07 - 2024") == date(2024, 7, 3)


def test_parse_date_out_of_range_returns_none():
    assert parse_date("Fecha: 10/10/0266") is None


def test_parse_date_without_label_returns_none():
    assert parse_date("Entregado el 25/02/2026 en oficina") is None


def test_parse_date_invalid_calendar_day_returns_none():
    assert parse_date("Fecha: 31/02/2024") is None


def test_parse_owner_single_word_returns_none():
    assert parse_owner("Firma\nAna\nSeguridad\n") is None


def test_parse_owner_two_candidates_returns_none():
    text = "Ana Prueba Ficticia\nSeguridad\nLuis Ejemplo Falso\nSeguridad\n"
    assert parse_owner(text) is None


def test_parse_owner_rejects_excluded_words_and_digits():
    assert parse_owner("Grupo Cinbersol Norte\nSeguridad\n") is None
    assert parse_owner("Ana Prueba 2\nSeguridad\n") is None


def test_parse_owner_requires_area_on_next_line():
    assert parse_owner("Ana Prueba Ficticia\nSistemas y redes\n") is None


def test_suggest_uses_text_layer_without_tesseract(tmp_path, monkeypatch):
    monkeypatch.setattr(extraction.shutil, "which", lambda _name: None)
    path = tmp_path / "carta.pdf"
    path.write_bytes(text_layer_pdf(LETTER_TEXT))
    assert suggest(path) == {"document_date": "2026-02-25", "owner_full_name": "Ana Prueba Ficticia"}


def test_extract_requires_session(client):
    files = {"file": ("a.pdf", make_pdf("anon"), "application/pdf")}
    assert client.post("/api/documents/extract", files=files).status_code == 401


def test_extract_non_pdf_returns_400(client, origins):  # noqa: F811
    files = {"file": ("fake.pdf", b"not a pdf", "application/pdf")}
    assert client.post("/api/documents/extract", files=files).status_code == 400


def test_extract_without_text_or_tesseract_returns_nulls(client, origins, storage_path, monkeypatch):  # noqa: F811
    monkeypatch.setattr(extraction.shutil, "which", lambda _name: None)
    files = {"file": ("scan.pdf", image_only_pdf("Fecha: 25/02/2026"), "application/pdf")}
    response = client.post("/api/documents/extract", files=files)

    assert response.status_code == 200
    assert response.json() == {"document_date": None, "owner_full_name": None}
    assert list((storage_path / "documents" / ".tmp").iterdir()) == []


def test_extract_with_text_layer_returns_suggestion(client, origins):  # noqa: F811
    files = {"file": ("carta.pdf", text_layer_pdf(LETTER_TEXT), "application/pdf")}
    response = client.post("/api/documents/extract", files=files)
    assert response.json() == {"document_date": "2026-02-25", "owner_full_name": "Ana Prueba Ficticia"}


def test_upload_with_different_extracted_owner_marks_edited(client, origins):  # noqa: F811
    body = upload(
        client,
        origins,
        owner_full_name="Ana Prueba Corregida",
        owner_name_extracted="Ana Prueba Ficticia",
        document_date="2026-02-25",
        document_date_extracted="2026-02-25",
    ).json()

    assert body["owner_name"] == "Ana Prueba Corregida"
    assert body["owner_name_extracted"] == "Ana Prueba Ficticia"
    assert body["owner_name_edited"] is True
    assert body["document_date_extracted"] == "2026-02-25"
    assert body["document_date_edited"] is False


def test_upload_with_matching_extracted_owner_is_not_edited(client, origins):  # noqa: F811
    body = upload(
        client,
        origins,
        owner_full_name="ana  prueba ficticia",
        owner_name_extracted="Ana Prueba Ficticia",
        document_date="2026-02-24",
        document_date_extracted="2026-02-25",
    ).json()

    assert body["owner_name_edited"] is False
    assert body["document_date_edited"] is True


def test_upload_ignores_client_edited_flags(client, origins):  # noqa: F811
    body = upload(client, origins, owner_name_edited="true", document_date_edited="true").json()
    assert body["owner_name_extracted"] is None
    assert body["owner_name_edited"] is False
    assert body["document_date_edited"] is False


@requires_tesseract
def test_ocr_on_scanned_pdf(client, origins):  # noqa: F811
    lines = ["CARTA RESPONSIVA", "Fecha: 25/02/2026", "", "Ana Prueba Ficticia", "Seguridad"]
    files = {"file": ("scan.pdf", image_only_pdf("\n".join(lines)), "application/pdf")}
    response = client.post("/api/documents/extract", files=files)

    assert response.status_code == 200
    assert response.json() == {"document_date": "2026-02-25", "owner_full_name": "Ana Prueba Ficticia"}
