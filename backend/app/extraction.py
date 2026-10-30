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

AREA_NAMES = ("Seguridad",)
OWNER_EXCLUDED_WORDS = ("grupo", "cinbersol", "acepto")
OWNER_MIN_WORDS = 2
OWNER_MAX_WORDS = 5

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


def _is_area_line(line: str) -> bool:
    words = re.findall(r"\w+", normalize_text(line))
    areas = {normalize_text(area) for area in AREA_NAMES}
    return len(words) == 1 and words[0] in areas


def _is_owner_candidate(line: str) -> bool:
    words = line.split(" ")
    if not OWNER_MIN_WORDS <= len(words) <= OWNER_MAX_WORDS:
        return False
    if not all(word.isalpha() for word in words):
        return False
    normalized = normalize_text(line)
    return not any(excluded in normalized for excluded in OWNER_EXCLUDED_WORDS)


def parse_owner(text: str) -> str | None:
    lines = [collapse_spaces(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    candidates = [
        line
        for line, next_line in zip(lines, lines[1:])
        if _is_area_line(next_line) and _is_owner_candidate(line)
    ]
    if len(candidates) != 1:
        return None
    try:
        return clean_owner_full_name(candidates[0])
    except ValidationFailure:
        return None


def suggest(pdf_path: Path | str) -> dict[str, str | None]:
    text = extract_text(pdf_path)
    document_date = parse_date(text)
    return {
        "document_date": document_date.isoformat() if document_date else None,
        "owner_full_name": parse_owner(text),
    }
