import re
import unicodedata

_WORD_PATTERN = re.compile(r"\w+")


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_marks.casefold().split())


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def contains_pattern(value: str) -> str:
    return f"%{escape_like(normalize_text(value) or '')}%"


def build_fts_query(text: str) -> str | None:
    words = _WORD_PATTERN.findall(text)
    if not words:
        return None
    return " ".join(f'"{word}"*' for word in words)
