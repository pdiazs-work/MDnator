import os
import tempfile
import time
from pathlib import Path

from markitdown import MarkItDown

from src.utils.logger import get_logger

_logger = get_logger(__name__)

_TEMP_DIR = Path(tempfile.gettempdir()).resolve()
_TEMP_DIR_STR = str(_TEMP_DIR) + os.sep


class DocumentConverter:
    """Convert supported documents to Markdown using markitdown."""

    def __init__(self) -> None:
        self._md = MarkItDown()

    def convert(self, file_path: str) -> str:
        """Convert the file at file_path to a Markdown string."""
        start = time.monotonic()

        real = os.path.realpath(os.path.abspath(file_path))
        if not real.startswith(_TEMP_DIR_STR):
            raise RuntimeError("File path is outside the expected upload directory.")
        resolved = Path(real)
        filename = resolved.name

        try:
            size = resolved.stat().st_size
            result = self._md.convert(real)
            text = result.text_content or ""
        except FileNotFoundError:
            _logger.error("File not found | file=%s", filename)
            raise RuntimeError("File not found.")
        except PermissionError:
            _logger.error("Permission denied | file=%s", filename)
            raise RuntimeError("Permission denied when reading the file.")
        except Exception as exc:
            _logger.error(
                "Conversion failed | file=%s | error=%s", filename, type(exc).__name__
            )
            raise RuntimeError("Could not convert the file.") from exc

        elapsed = time.monotonic() - start
        _logger.info(
            "Conversión exitosa | file=%s | size=%d bytes | tiempo=%.2fs",
            filename,
            size,
            elapsed,
        )
        return text
