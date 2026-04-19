import os
import tempfile

import pytest

from src.core.validators import validate_extension, validate_file, validate_size
from src.config.settings import MAX_FILE_SIZE_BYTES


def test_extension_invalid():
    ok, msg = validate_extension("malware.exe")
    assert not ok
    assert ".exe" in msg


def test_extension_valid():
    ok, msg = validate_extension("document.pdf")
    assert ok
    assert msg == ""


def test_extension_case_insensitive():
    ok, _ = validate_extension("REPORT.PDF")
    assert ok


def test_size_exceeds_limit(tmp_path):
    big = tmp_path / "big.txt"
    big.write_bytes(b"x" * (MAX_FILE_SIZE_BYTES + 1))
    ok, msg = validate_size(str(big))
    assert not ok
    assert "20 MB" in msg


def test_validate_file_missing():
    ok, msg = validate_file("/nonexistent/path/file.pdf")
    assert not ok


def test_validate_file_ok(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("hello world")
    ok, msg = validate_file(str(f))
    assert ok
    assert msg == ""
