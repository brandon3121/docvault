import logging
import re
import shutil
import subprocess
import time
from datetime import date
from pathlib import Path

import pymupdf

from app.config import get_settings
from app.search import collapse_spaces, normalize_text
from app.validation import ValidationFailure, clean_owner_full_name, validate_document_date

logger = logging.getLogger(__name__)

MAX_OCR_PAGES = 2
OCR_DPI = 300
OCR_LANGUAGE = "spa"
OCR_PAGE_SEGMENTATION_MODE = "6"

OWNER_EXCLUDED_WORDS = frozenset(
    {
        "grupo",
        "cinbersol",
        "acepto",
        "carta",
        "responsiva",
        "fecha",
        "firma",
        "nombre",
        "entrega",
        "recibe",
        "equipo",
    }
)
OWNER_MIN_WORDS = 2
OWNER_MAX_WORDS = 5
OWNER_WORD_PATTERN = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*")

DATE_PATTERN = re.compile(
    r"\bfecha\s*:\s*(\d{1,2})\s*[/-]\s*(\d{1,2})\s*[/-]\s*(\d{4})\b",
    re.IGNORECASE,
)


def _ocr_image(png: bytes, timeout: float) -> str:
    settings = get_settings()
    command = shutil.which(settings.tesseract_cmd)
    if command is None:
        logger.warning("Tesseract not found: %s", settings.tesseract_cmd)
        return ""
    result = subprocess.run(
        [command, "stdin", "stdout", "-l", OCR_LANGUAGE, "--psm", OCR_PAGE_SEGMENTATION_MODE],
        input=png,
        capture_output=True,
        timeout=timeout,
        check=True,
    )
    return result.stdout.decode("utf-8", errors="replace")


def extract_text(pdf_path: Path | str) -> str:
    deadline = time.monotonic() + get_settings().ocr_timeout_seconds
    try:
        with pymupdf.open(pdf_path) as document:
            texts = []
            for page in document.pages(0, min(MAX_OCR_PAGES, document.page_count)):
                text = page.get_text()
                if not text.strip():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise subprocess.TimeoutExpired("tesseract", get_settings().ocr_timeout_seconds)
                    png = page.get_pixmap(dpi=OCR_DPI, colorspace=pymupdf.csGRAY).tobytes("png")
                    text = _ocr_image(png, remaining)
                texts.append(text)
            return "\n".join(texts)
    except Exception:
        logger.exception("Text extraction failed for %s", pdf_path)
        return ""


def parse_date(text: str) -> date | None:
    match = DATE_PATTERN.search(text)
    if match is None:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return validate_document_date(date(year, month, day))
    except (ValueError, ValidationFailure):
        return None


def _owner_candidate(line: str) -> str | None:
    words = line.split(" ")
    if not OWNER_MIN_WORDS <= len(words) <= OWNER_MAX_WORDS:
        return None
    if not all(OWNER_WORD_PATTERN.fullmatch(word) for word in words):
        return None
    if line.isupper():
        return None
    if OWNER_EXCLUDED_WORDS.intersection(re.split(r"['’\s-]+", normalize_text(line))):
        return None
    try:
        return clean_owner_full_name(line)
    except ValidationFailure:
        return None


def parse_owner(text: str) -> str | None:
    lines = [collapse_spaces(line) for line in text.splitlines()]
    candidates = [candidate for line in lines if line and (candidate := _owner_candidate(line))]
    return candidates[0] if len(candidates) == 1 else None


def suggest(pdf_path: Path | str) -> dict[str, str | None]:
    text = extract_text(pdf_path)
    document_date = parse_date(text)
    return {
        "document_date": document_date.isoformat() if document_date else None,
        "owner_full_name": parse_owner(text),
    }
