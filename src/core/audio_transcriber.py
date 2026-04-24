"""Audio file → Markdown transcript via OpenAI Whisper API."""

import os
import tempfile
from pathlib import Path

from src.utils.logger import get_logger

_logger = get_logger(__name__)

_TEMP_DIR = Path(tempfile.gettempdir()).resolve()

AUDIO_EXTENSIONS = frozenset({".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".mp4"})

_MAX_AUDIO_MB = 25  # OpenAI Whisper API hard limit is 25 MB


def validate_audio_file(file_path: str) -> tuple[bool, str]:
    if not file_path:
        return False, "no_audio"
    resolved = Path(os.path.abspath(file_path)).resolve()
    try:
        resolved.relative_to(_TEMP_DIR)
    except ValueError:
        return False, "no_audio"
    if not resolved.is_file():
        return False, "no_audio"
    ext = resolved.suffix.lower()
    if ext not in AUDIO_EXTENSIONS:
        return (
            False,
            f"Unsupported audio format '{ext}'. Accepted: {', '.join(sorted(AUDIO_EXTENSIONS))}",
        )
    size_mb = resolved.stat().st_size / (1024 * 1024)
    if size_mb > _MAX_AUDIO_MB:
        return (
            False,
            f"Audio file ({size_mb:.1f} MB) exceeds the {_MAX_AUDIO_MB} MB limit (OpenAI Whisper API).",
        )
    return True, ""


def transcribe_audio(file_path: str, api_key: str) -> str:
    """Transcribe audio file using OpenAI Whisper API.

    Returns a Markdown-formatted transcript.
    Raises RuntimeError on any failure.
    """
    try:
        from openai import OpenAI  # noqa: PLC0415
    except ImportError:
        raise RuntimeError(
            "openai package not installed. Add 'openai' to requirements.txt."
        )

    resolved = Path(os.path.abspath(file_path)).resolve()
    filename = resolved.name

    _logger.info("Audio transcription start | file=%s", filename)
    try:
        client = OpenAI(api_key=api_key.strip())
        with open(str(resolved), "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
            )
    except Exception as exc:
        _logger.warning(
            "Transcription failed | file=%s | error=%s", filename, type(exc).__name__
        )
        error_str = str(exc)
        if "401" in error_str or "Incorrect API key" in error_str:
            raise RuntimeError("Invalid OpenAI API key. Check your key and try again.")
        if "429" in error_str:
            raise RuntimeError(
                "OpenAI rate limit reached. Please wait a moment and try again."
            )
        raise RuntimeError(f"Transcription failed: {exc}") from exc

    text = getattr(response, "text", "") or ""
    duration = getattr(response, "duration", None)
    language = getattr(response, "language", None)

    if not text.strip():
        raise RuntimeError("The audio file contains no recognisable speech.")

    lines = [f"# Transcript — {filename}", ""]
    if language:
        lines.append(f"**Detected language:** {language}")
    if duration:
        mins, secs = divmod(int(duration), 60)
        lines.append(f"**Duration:** {mins}m {secs:02d}s")
    if language or duration:
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(text.strip())

    _logger.info("Transcription complete | file=%s | chars=%d", filename, len(text))
    return "\n".join(lines)
