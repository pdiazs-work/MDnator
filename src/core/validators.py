import os
from pathlib import Path

from src.config.settings import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES
from src.utils.logger import get_logger

_logger = get_logger(__name__)


def validate_extension(filename: str) -> tuple[bool, str]:
    """Check that the file extension is in the allowed list."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return (
            False,
            f"File type '{ext}' is not allowed. Accepted formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return True, ""


def validate_size(file_path: str) -> tuple[bool, str]:
    """Check that the file does not exceed the maximum allowed size."""
    try:
        size = os.path.getsize(file_path)
    except OSError:
        return False, "Could not read the file."
    if size > MAX_FILE_SIZE_BYTES:
        mb = size / (1024 * 1024)
        return False, f"File size ({mb:.1f} MB) exceeds the 20 MB limit."
    return True, ""


def validate_file(file_path: str) -> tuple[bool, str]:
    """Run all validation checks on the uploaded file."""
    if not file_path or not os.path.exists(file_path):
        return False, "No file was received."

    ok, msg = validate_extension(file_path)
    if not ok:
        return False, msg

    ok, msg = validate_size(file_path)
    if not ok:
        return False, msg

    _logger.info(
        "Archivo válido | tamaño=%d bytes | ruta=%s",
        os.path.getsize(file_path),
        Path(file_path).name,
    )
    return True, ""
