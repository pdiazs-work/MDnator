import os
import tempfile
from pathlib import Path

from src.config.settings import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES
from src.utils.logger import get_logger

_logger = get_logger(__name__)

# Gradio always writes uploaded files to the system temp directory.
# We enforce this so that no path traversal outside temp is possible.
_TEMP_DIR = Path(tempfile.gettempdir()).resolve()


def _safe_path(file_path: str) -> Path | None:
    """Resolve file_path and verify it lives inside the system temp directory."""
    try:
        resolved = Path(os.path.abspath(file_path)).resolve()
        resolved.relative_to(_TEMP_DIR)  # raises ValueError if not under temp
        return resolved
    except (ValueError, OSError):
        return None


def validate_extension(filename: str) -> tuple[bool, str]:
    """Check that the file extension is in the allowed list."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return (
            False,
            f"File type '{ext}' is not allowed. Accepted formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return True, ""


def validate_size(file_path: str | Path) -> tuple[bool, str]:
    """Check that the file does not exceed the maximum allowed size."""
    try:
        size = Path(file_path).stat().st_size
    except OSError:
        return False, "Could not read the file."
    if size > MAX_FILE_SIZE_BYTES:
        mb = size / (1024 * 1024)
        return False, f"File size ({mb:.1f} MB) exceeds the 20 MB limit."
    return True, ""


def validate_file(file_path: str) -> tuple[bool, str]:
    """Run all validation checks on the uploaded file."""
    if not file_path:
        return False, "No file was received."

    resolved = _safe_path(file_path)
    if resolved is None or not resolved.is_file():
        return False, "No file was received."

    ok, msg = validate_extension(resolved.name)
    if not ok:
        return False, msg

    ok, msg = validate_size(resolved)
    if not ok:
        return False, msg

    _logger.info(
        "Archivo válido | tamaño=%d bytes | ruta=%s",
        resolved.stat().st_size,
        resolved.name,
    )
    return True, ""
