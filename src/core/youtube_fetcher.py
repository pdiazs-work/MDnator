"""YouTube URL → Markdown transcript via youtube-transcript-api."""

import re

from src.utils.logger import get_logger

_logger = get_logger(__name__)

_YT_PATTERNS = [
    r"(?:https?://)?(?:www\.)?youtube\.com/watch\?(?:.*&)?v=([\w-]{11})",
    r"(?:https?://)?youtu\.be/([\w-]{11})",
    r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([\w-]{11})",
    r"(?:https?://)?(?:www\.)?youtube\.com/embed/([\w-]{11})",
]


def validate_youtube_url(url: str) -> tuple[bool, str]:
    url = url.strip()
    if not url:
        return False, "URL cannot be empty."
    for pattern in _YT_PATTERNS:
        if re.search(pattern, url):
            return True, ""
    return (
        False,
        "Not a valid YouTube URL. Accepted formats: youtube.com/watch?v=..., youtu.be/...",
    )


def extract_video_id(url: str) -> str | None:
    for pattern in _YT_PATTERNS:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def fetch_youtube(url: str) -> str:
    """Fetch YouTube transcript and return Markdown.

    Tries multiple transcript languages in order.
    Raises RuntimeError on failure.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # noqa: PLC0415
    except ImportError:
        raise RuntimeError("youtube-transcript-api is not installed.")

    url = url.strip()
    ok, err = validate_youtube_url(url)
    if not ok:
        raise RuntimeError(err)

    video_id = extract_video_id(url)
    if not video_id:
        raise RuntimeError("Could not extract video ID from URL.")

    canonical = f"https://www.youtube.com/watch?v={video_id}"
    _logger.info("YouTube fetch | video_id=%s", video_id)

    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        try:
            transcript = transcript_list.find_transcript(
                ["en", "es", "fr", "de", "pt", "zh", "ja", "ar", "ru", "it"]
            )
        except Exception:
            transcript = next(iter(transcript_list))
        snippets = list(transcript.fetch())
    except Exception as exc:
        _logger.warning(
            "YouTube transcript failed | video_id=%s | error=%s",
            video_id,
            type(exc).__name__,
        )
        raise RuntimeError(
            f"Could not retrieve transcript for this video.\n"
            f"Possible reasons: video has no subtitles, subtitles are disabled, "
            f"or YouTube is temporarily blocking requests.\n"
            f"Video URL: {canonical}"
        ) from exc

    if not snippets:
        raise RuntimeError("This video has no available transcript.")

    # Build Markdown
    lines = [
        "# YouTube Transcript",
        "",
        f"**Source:** [{canonical}]({canonical})",
        f"**Video ID:** `{video_id}`",
        "",
        "---",
        "",
    ]

    # Group snippets into paragraphs (~60 seconds each)
    para_texts: list[str] = []
    current_para: list[str] = []
    para_start = 0.0

    for snippet in snippets:
        start = snippet.start
        text = snippet.text.strip().replace("\n", " ")
        if not text:
            continue

        if not current_para:
            para_start = start

        current_para.append(text)

        if start - para_start >= 60:
            mins, secs = divmod(int(para_start), 60)
            para_texts.append(f"**[{mins}:{secs:02d}]** {' '.join(current_para)}")
            current_para = []
            para_start = start

    if current_para:
        mins, secs = divmod(int(para_start), 60)
        para_texts.append(f"**[{mins}:{secs:02d}]** {' '.join(current_para)}")

    lines.extend(para_texts)
    _logger.info(
        "YouTube transcript ok | video_id=%s | paragraphs=%d", video_id, len(para_texts)
    )
    return "\n\n".join(lines) if len(lines) > 7 else "\n".join(lines)
