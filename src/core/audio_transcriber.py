"""Audio file → Markdown transcript.

Three backends (selected by `provider`):
- "free"   : faster-whisper locally on CPU (model: tiny) — no API key needed
- "openai" : OpenAI Whisper API (whisper-1) — requires user's OpenAI key
- "gemini" : Google Gemini 1.5 Flash audio understanding — requires user's Gemini key

API keys are used only for the duration of the request and are never logged or stored.
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

_GEMINI_MIME = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".webm": "audio/webm",
    ".mp4": "audio/mp4",
}

_GEMINI_PROMPT = (
    "You are an expert transcriptionist. Listen to the audio and return ONLY the "
    "verbatim transcript, formatted as clean Markdown. Use headings if the speaker "
    "clearly changes topic; use bullet lists if items are enumerated. Preserve the "
    "speaker's original tone and idiomatic expressions. Do NOT add introductions, "
    "summaries, or any text outside the transcript itself."
)


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
        segments, info = model.transcribe(
            real,
            beam_size=5,
            vad_filter=True,
            language_detection_segments=3,
            language_detection_threshold=0.7,
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
    """Transcribe using OpenAI Whisper API (whisper-1)."""
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


def _transcribe_gemini(file_path: str, api_key: str) -> str:
    """Transcribe using Google Gemini 1.5 Flash multimodal audio understanding."""
    try:
        import google.generativeai as genai  # noqa: PLC0415
    except ImportError:
        raise RuntimeError(
            "google-generativeai is not installed. Add 'google-generativeai' to requirements.txt."
        )

    real = os.path.realpath(os.path.abspath(file_path))
    if not real.startswith(_TEMP_DIR_STR):
        raise RuntimeError("Invalid audio file path.")
    resolved = Path(real)
    filename = resolved.name
    mime = _GEMINI_MIME.get(resolved.suffix.lower(), "audio/mpeg")

    _logger.info("Gemini transcription start | file=%s", filename)
    try:
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel("gemini-1.5-flash")
        with open(real, "rb") as f:
            audio_bytes = f.read()
        response = model.generate_content(
            [
                {"mime_type": mime, "data": audio_bytes},
                _GEMINI_PROMPT,
            ]
        )
        text = response.text or ""
    except Exception as exc:
        _logger.warning(
            "Gemini transcription failed | file=%s | error=%s",
            filename,
            type(exc).__name__,
        )
        error_str = str(exc)
        if "API_KEY_INVALID" in error_str or "400" in error_str:
            raise RuntimeError(
                "Invalid Gemini API key. Check your key at aistudio.google.com."
            )
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            raise RuntimeError(
                "Gemini rate limit reached. Please wait a moment and try again."
            )
        raise RuntimeError(f"Transcription failed: {exc}") from exc

    if not text.strip():
        raise RuntimeError("The audio file contains no recognisable speech.")

    _logger.info(
        "Gemini transcription complete | file=%s | chars=%d", filename, len(text)
    )
    return _build_markdown(filename, text, None, None)


def transcribe_audio(file_path: str, api_key: str = "", provider: str = "free") -> str:
    """Transcribe audio file to Markdown.

    provider: "free" (local faster-whisper), "openai" (Whisper API), "gemini" (Gemini 1.5 Flash)
    API keys are used only in-memory for the duration of this call and are never logged.
    """
    if provider == "openai":
        if not api_key or not api_key.strip():
            raise RuntimeError(
                "An OpenAI API key is required for OpenAI transcription."
            )
        return _transcribe_openai(file_path, api_key)
    if provider == "gemini":
        if not api_key or not api_key.strip():
            raise RuntimeError(
                "A Gemini API key is required. Get one free at aistudio.google.com."
            )
        return _transcribe_gemini(file_path, api_key)
    return _transcribe_free(file_path)
