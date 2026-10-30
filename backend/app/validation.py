from datetime import date

from app.search import collapse_spaces

MIN_DOCUMENT_YEAR = 2000
OWNER_NAME_MAX_LENGTH = 255

DOCUMENT_DATE_RANGE_MESSAGE = f"La fecha debe estar entre {MIN_DOCUMENT_YEAR} y hoy"
DOCUMENT_DATE_FORMAT_MESSAGE = "La fecha debe tener el formato AAAA-MM-DD"
OWNER_NAME_REQUIRED_MESSAGE = "Escribe el nombre completo del propietario"
OWNER_NAME_WORDS_MESSAGE = "Escribe nombre y al menos un apellido"
OWNER_NAME_LENGTH_MESSAGE = f"El nombre del propietario admite como máximo {OWNER_NAME_MAX_LENGTH} caracteres"


class ValidationFailure(ValueError):
    pass


def min_document_date() -> date:
    return date(MIN_DOCUMENT_YEAR, 1, 1)


def validate_document_date(value: date | None) -> date | None:
    if value is not None and not min_document_date() <= value <= date.today():
        raise ValidationFailure(DOCUMENT_DATE_RANGE_MESSAGE)
    return value


def clean_owner_full_name(value: str | None) -> str:
    cleaned = collapse_spaces(value)
    if not cleaned:
        raise ValidationFailure(OWNER_NAME_REQUIRED_MESSAGE)
    if len(cleaned.split(" ")) < 2:
        raise ValidationFailure(OWNER_NAME_WORDS_MESSAGE)
    if len(cleaned) > OWNER_NAME_MAX_LENGTH:
        raise ValidationFailure(OWNER_NAME_LENGTH_MESSAGE)
    return cleaned
