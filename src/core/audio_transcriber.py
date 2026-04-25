"""Audio file → Markdown transcript.

Two backends:
- Free (default): faster-whisper running locally on CPU (model: tiny)
- Premium: OpenAI Whisper API (requires api_key)
"""

import os
import tempfile
from pathlib import Path

from src.utils.logger import get_logger

_logger = get_logger(__name__)

_TEMP_DIR = Path(tempfile.gettempdir()).resolve()
_TEMP_DIR_STR = str(_TEMP_DIR) + os.sep

AUDIO_EXTENSIONS = frozenset({".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".mp4"})

_MAX_AUDIO_MB = 100


def _safe_audio_path(file_path: str) -> Path | None:
    try:
        real = os.path.realpath(os.path.abspath(file_path))
        if not real.startswith(_TEMP_DIR_STR):
            return None
        return Path(real)
    except (ValueError, OSError):
        return None


def validate_audio_file(file_path: str) -> tuple[bool, str]:
    if not file_path:
        return False, "no_audio"
    resolved = _safe_audio_path(file_path)
    if resolved is None or not resolved.is_file():
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
            f"Audio file ({size_mb:.1f} MB) exceeds the {_MAX_AUDIO_MB} MB limit.",
        )
    return True, ""


def _build_markdown(
    filename: str, text: str, language: str | None, duration: float | None
) -> str:
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
    return "\n".join(lines)


def _transcribe_free(file_path: str) -> str:
    """Transcribe using faster-whisper (tiny model, CPU, no API key needed)."""
    try:
        from faster_whisper import WhisperModel  # noqa: PLC0415
    except ImportError:
        raise RuntimeError(
            "faster-whisper is not installed. Add 'faster-whisper' to requirements.txt."
        )

    real = os.path.realpath(os.path.abspath(file_path))
    if not real.startswith(_TEMP_DIR_STR):
        raise RuntimeError("Invalid audio file path.")
    filename = Path(real).name

    _logger.info("Free transcription start | file=%s", filename)
    try:
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        # Detect language first so the decoder uses the right token
        detected_language, _ = model.detect_language(real)
        segments, info = model.transcribe(
            real,
            language=detected_language,
            beam_size=5,
            vad_filter=True,
        )
        text = " ".join(seg.text.strip() for seg in segments)
        language = info.language
        duration = info.duration
    except Exception as exc:
        _logger.warning(
            "Free transcription failed | file=%s | error=%s",
            filename,
            type(exc).__name__,
        )
        raise RuntimeError(f"Transcription failed: {exc}") from exc

    if not text.strip():
        raise RuntimeError("The audio file contains no recognisable speech.")

    _logger.info(
        "Free transcription complete | file=%s | chars=%d", filename, len(text)
    )
    return _build_markdown(filename, text, language, duration)


def _transcribe_openai(file_path: str, api_key: str) -> str:
    """Transcribe using OpenAI Whisper API."""
    try:
        from openai import OpenAI  # noqa: PLC0415
    except ImportError:
        raise RuntimeError(
            "openai package not installed. Add 'openai' to requirements.txt."
        )

    real = os.path.realpath(os.path.abspath(file_path))
    if not real.startswith(_TEMP_DIR_STR):
        raise RuntimeError("Invalid audio file path.")
    filename = Path(real).name

    _logger.info("OpenAI transcription start | file=%s", filename)
    try:
        client = OpenAI(api_key=api_key.strip())
        with open(real, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
            )
    except Exception as exc:
        _logger.warning(
            "OpenAI transcription failed | file=%s | error=%s",
            filename,
            type(exc).__name__,
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

    _logger.info(
        "OpenAI transcription complete | file=%s | chars=%d", filename, len(text)
    )
    return _build_markdown(filename, text, language, duration)


def transcribe_audio(file_path: str, api_key: str = "") -> str:
    """Transcribe audio. Uses OpenAI API if api_key provided, otherwise faster-whisper."""
    if api_key and api_key.strip():
        return _transcribe_openai(file_path, api_key)
    return _transcribe_free(file_path)
