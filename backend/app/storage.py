import hashlib
import os
import tempfile
from pathlib import Path
from typing import BinaryIO

from app.config import get_settings

CHUNK_SIZE = 1024 * 1024
PDF_MAGIC = b"%PDF"


class InvalidPdfError(Exception):
    pass


class UploadTooLargeError(Exception):
    pass


def storage_root() -> Path:
    return Path(get_settings().storage_path)


def relative_document_path(sha256: str) -> str:
    return f"documents/{sha256[:2]}/{sha256[2:4]}/{sha256}.pdf"


def resolve_document_path(relative_path: str) -> Path:
    return storage_root() / relative_path


def spool_pdf(source: BinaryIO, max_bytes: int) -> tuple[Path, str]:
    temp_dir = storage_root() / "documents" / ".tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(dir=temp_dir, suffix=".part")
    temp_path = Path(temp_name)
    digest = hashlib.sha256()
    size = 0

    try:
        with os.fdopen(fd, "wb") as output:
            while chunk := source.read(CHUNK_SIZE):
                if size == 0 and not chunk.startswith(PDF_MAGIC):
                    raise InvalidPdfError
                size += len(chunk)
                if size > max_bytes:
                    raise UploadTooLargeError
                digest.update(chunk)
                output.write(chunk)
            if size == 0:
                raise InvalidPdfError
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise

    return temp_path, digest.hexdigest()


def commit_spooled_file(temp_path: Path, sha256: str) -> tuple[str, bool]:
    relative_path = relative_document_path(sha256)
    final_path = resolve_document_path(relative_path)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    already_existed = final_path.exists()
    os.replace(temp_path, final_path)
    return relative_path, already_existed
