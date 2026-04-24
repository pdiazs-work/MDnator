"""Tests for audio_transcriber module."""

import os
import tempfile

import pytest

from src.core.audio_transcriber import (
    _MAX_AUDIO_MB,
    AUDIO_EXTENSIONS,
    validate_audio_file,
)


def _make_temp_audio(suffix: str, size_bytes: int = 100) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(b"0" * size_bytes)
    tmp.close()
    return tmp.name


def test_valid_audio_file():
    path = _make_temp_audio(".mp3")
    try:
        ok, msg = validate_audio_file(path)
        assert ok is True
        assert msg == ""
    finally:
        os.unlink(path)


@pytest.mark.parametrize("ext", sorted(AUDIO_EXTENSIONS))
def test_all_supported_extensions(ext):
    path = _make_temp_audio(ext)
    try:
        ok, msg = validate_audio_file(path)
        assert ok is True
    finally:
        os.unlink(path)


def test_unsupported_extension():
    path = _make_temp_audio(".pdf")
    try:
        ok, msg = validate_audio_file(path)
        assert ok is False
        assert ".pdf" in msg
    finally:
        os.unlink(path)


def test_empty_path():
    ok, msg = validate_audio_file("")
    assert ok is False
    assert msg == "no_audio"


def test_nonexistent_file():
    ok, msg = validate_audio_file("/tmp/nonexistent_audio_file_xyz.mp3")
    assert ok is False


def test_file_outside_temp_dir():
    ok, msg = validate_audio_file(os.path.abspath(__file__))
    assert ok is False
    assert msg == "no_audio"


def test_oversized_file():
    size_bytes = int(_MAX_AUDIO_MB * 1024 * 1024) + 1
    path = _make_temp_audio(".mp3", size_bytes=size_bytes)
    try:
        ok, msg = validate_audio_file(path)
        assert ok is False
        assert "MB" in msg
    finally:
        os.unlink(path)
