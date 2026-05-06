"""YouTube URL → Markdown transcript.

Three-layer extraction cascade:
  1. yt-dlp  — most robust, handles auto-generated captions
  2. youtube-transcript-api — fallback for cases yt-dlp can't reach
  3. YouTube Data API v3 (BYOK) — official API, manual captions only
"""

import os
import re
import tempfile

import requests

from src.utils.logger import get_logger

_logger = get_logger(__name__)

_YT_PATTERNS = [
    r"(?:https?://)?(?:www\.)?youtube\.com/watch\?(?:.*&)?v=([\w-]{11})",
    r"(?:https?://)?youtu\.be/([\w-]{11})",
    r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([\w-]{11})",
    r"(?:https?://)?(?:www\.)?youtube\.com/embed/([\w-]{11})",
]

_LANG_PREF = ["en", "es", "fr", "de", "pt", "zh", "ja", "ar", "ru", "it"]


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


# ---------------------------------------------------------------------------
# Layer 1: yt-dlp
# ---------------------------------------------------------------------------


def _fetch_via_ytdlp(video_id: str) -> list[dict]:
    """Download subtitles via yt-dlp Python API. Returns [{start, text}, ...]."""
    try:
        import yt_dlp  # noqa: PLC0415
    except ImportError:
        raise RuntimeError("yt-dlp is not installed.")

    url = f"https://www.youtube.com/watch?v={video_id}"
    with tempfile.TemporaryDirectory() as tmpdir:
        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitlesformat": "json3",
            "subtitleslangs": _LANG_PREF + ["all"],
            "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        # Find a downloaded subtitle file
        sub_file = None
        for lang in _LANG_PREF:
            candidate = os.path.join(tmpdir, f"{video_id}.{lang}.json3")
            if os.path.exists(candidate):
                sub_file = candidate
                break
        if sub_file is None:
            # Pick any .json3 file available
            for fname in os.listdir(tmpdir):
                if fname.endswith(".json3"):
                    sub_file = os.path.join(tmpdir, fname)
                    break

        if sub_file is None:
            raise RuntimeError("yt-dlp: no subtitle file found.")

        import json  # noqa: PLC0415

        with open(sub_file, encoding="utf-8") as f:
            data = json.load(f)

        snippets = []
        for event in data.get("events", []):
            start_ms = event.get("tStartMs", 0)
            segs = event.get("segs", [])
            text = "".join(s.get("utf8", "") for s in segs).strip()
            text = text.replace("\n", " ").strip()
            if text and text != "\n":
                snippets.append({"start": start_ms / 1000.0, "text": text})

        if not snippets:
            raise RuntimeError("yt-dlp: subtitle file was empty.")

        _logger.info(
            "yt-dlp success | video_id=%s | snippets=%d", video_id, len(snippets)
        )
        return snippets


# ---------------------------------------------------------------------------
# Layer 2: youtube-transcript-api
# ---------------------------------------------------------------------------


def _fetch_via_transcript_api(video_id: str) -> list[dict]:
    """Fetch via youtube-transcript-api. Returns [{start, text}, ...]."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # noqa: PLC0415
    except ImportError:
        raise RuntimeError("youtube-transcript-api is not installed.")

    api = YouTubeTranscriptApi()
    transcript_list = api.list(video_id)
    try:
        transcript = transcript_list.find_transcript(_LANG_PREF)
    except Exception:
        transcript = next(iter(transcript_list))

    raw = list(transcript.fetch())
    snippets = [
        {"start": s.start, "text": s.text.strip().replace("\n", " ")} for s in raw
    ]
    _logger.info(
        "transcript-api success | video_id=%s | snippets=%d", video_id, len(snippets)
    )
    return snippets


# ---------------------------------------------------------------------------
# Layer 3: YouTube Data API v3 (BYOK, manual captions only)
# ---------------------------------------------------------------------------


def _fetch_via_youtube_api(video_id: str, api_key: str) -> list[dict]:
    """Fetch via YouTube Data API v3. Returns [{start, text}, ...].

    Only works for videos with manually uploaded captions.
    Auto-generated captions are not accessible through this API.
    """
    base = "https://www.googleapis.com/youtube/v3"

    # 1. List available caption tracks
    resp = requests.get(
        f"{base}/captions",
        params={"videoId": video_id, "key": api_key, "part": "snippet"},
        timeout=15,
    )
    if resp.status_code == 403:
        raise RuntimeError(
            "YouTube API key is invalid or lacks permission. "
            "Make sure the YouTube Data API v3 is enabled in your Google Cloud project."
        )
    resp.raise_for_status()
    tracks = resp.json().get("items", [])
    if not tracks:
        raise RuntimeError(
            "No manually uploaded captions found for this video via YouTube Data API. "
            "Auto-generated captions are not accessible through the official API."
        )

    # Pick the best track by language preference
    chosen = None
    for lang in _LANG_PREF:
        for track in tracks:
            if track["snippet"].get("language", "").startswith(lang):
                chosen = track
                break
        if chosen:
            break
    if chosen is None:
        chosen = tracks[0]

    # 2. Download the caption track via timedtext endpoint
    # (The captions.download endpoint requires OAuth for most tracks)
    timed_resp = requests.get(
        "https://www.youtube.com/api/timedtext",
        params={
            "v": video_id,
            "lang": chosen["snippet"].get("language", "en"),
            "fmt": "json3",
            "key": api_key,
        },
        timeout=15,
    )

    if timed_resp.status_code != 200 or not timed_resp.text.strip():
        raise RuntimeError(
            "Could not download caption track via YouTube Data API. "
            "The track may be restricted."
        )

    try:
        data = timed_resp.json()
    except Exception:
        raise RuntimeError("YouTube Data API returned an unreadable caption format.")

    snippets = []
    for event in data.get("events", []):
        start_ms = event.get("tStartMs", 0)
        segs = event.get("segs", [])
        text = "".join(s.get("utf8", "") for s in segs).strip().replace("\n", " ")
        if text:
            snippets.append({"start": start_ms / 1000.0, "text": text})

    if not snippets:
        raise RuntimeError("YouTube Data API: caption track was empty.")

    _logger.info(
        "YouTube API v3 success | video_id=%s | snippets=%d", video_id, len(snippets)
    )
    return snippets


# ---------------------------------------------------------------------------
# Markdown builder
# ---------------------------------------------------------------------------


def _snippets_to_markdown(snippets: list[dict], canonical: str, video_id: str) -> str:
    """Convert snippet list to Markdown with ~60s paragraph grouping."""
    lines = [
        "# YouTube Transcript",
        "",
        f"**Source:** [{canonical}]({canonical})",
        f"**Video ID:** `{video_id}`",
        "",
        "---",
        "",
    ]

    para_texts: list[str] = []
    current_para: list[str] = []
    para_start = 0.0

    for snippet in snippets:
        start = snippet["start"]
        text = snippet["text"]
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
    return "\n\n".join(lines) if len(lines) > 7 else "\n".join(lines)


# ---------------------------------------------------------------------------
# Paste-transcript formatter
# ---------------------------------------------------------------------------

_TS_WITH_BRACKETS = re.compile(r"^\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.*)")
_TS_PLAIN = re.compile(r"^(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)")
_SPEAKER_TAG = re.compile(r"^-\s*\[([^\]]+)\]\s*")


def _ts_to_seconds(ts: str) -> float:
    parts = ts.split(":")
    parts = [float(p) for p in parts]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def _format_seconds(secs: float) -> str:
    total = int(secs)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_transcript_paste(text: str) -> str:
    """Format a pasted transcript as structured Markdown.

    - If timestamps are detected (MM:SS or HH:MM:SS at line start or in [brackets]),
      groups lines into ~60-second paragraphs with bold timestamp markers.
    - Otherwise splits into ~150-word paragraphs at sentence boundaries.
    - Detects speaker tags like "- [Speaker]" and bolds them.
    """
    lines = [ln.rstrip() for ln in text.strip().splitlines()]

    # --- Try to parse timestamped lines ---
    snippets: list[dict] = []
    for line in lines:
        if not line:
            continue
        m = _TS_WITH_BRACKETS.match(line) or _TS_PLAIN.match(line)
        if m:
            ts_str, body = m.group(1), m.group(2).strip()
            if body:
                snippets.append({"start": _ts_to_seconds(ts_str), "text": body})

    if len(snippets) >= 3:
        # Build grouped paragraphs (~60s each)
        header = [
            "# YouTube Transcript",
            "",
            "*Pasted transcript with timestamps.*",
            "",
            "---",
            "",
        ]
        para_texts: list[str] = []
        current: list[str] = []
        para_start = snippets[0]["start"]

        for snip in snippets:
            if not current:
                para_start = snip["start"]
            current.append(snip["text"])
            if snip["start"] - para_start >= 60:
                para_texts.append(
                    f"**[{_format_seconds(para_start)}]** {' '.join(current)}"
                )
                current = []

        if current:
            para_texts.append(
                f"**[{_format_seconds(para_start)}]** {' '.join(current)}"
            )

        return "\n\n".join(header + para_texts)

    # --- No timestamps: split into ~150-word paragraphs at sentence boundaries ---
    # Flatten all lines into one string, then split on sentence-ending punctuation
    full = " ".join(ln for ln in lines if ln)

    # Handle speaker tags: bold them
    full = _SPEAKER_TAG.sub(lambda m: f"**{m.group(1)}:** ", full)

    words = full.split()
    paragraphs: list[str] = []
    chunk: list[str] = []

    for word in words:
        chunk.append(word)
        if len(chunk) >= 150 and word.endswith((".", "?", "!", "…")):
            paragraphs.append(" ".join(chunk))
            chunk = []

    if chunk:
        paragraphs.append(" ".join(chunk))

    header_lines = [
        "# YouTube Transcript",
        "",
        "*Pasted transcript — no timestamps available.*",
        "",
        "---",
        "",
    ]
    return "\n\n".join(header_lines + paragraphs)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def fetch_youtube(url: str, api_key: str = "") -> str:
    """Fetch YouTube transcript and return Markdown.

    Tries three extraction methods in order:
      1. yt-dlp (most robust, handles auto-generated captions)
      2. youtube-transcript-api (fallback)
      3. YouTube Data API v3 (only if api_key provided; manual captions only)

    Raises RuntimeError if all methods fail.
    """
    url = url.strip()
    ok, err = validate_youtube_url(url)
    if not ok:
        raise RuntimeError(err)

    video_id = extract_video_id(url)
    if not video_id:
        raise RuntimeError("Could not extract video ID from URL.")

    canonical = f"https://www.youtube.com/watch?v={video_id}"
    _logger.info("YouTube fetch | video_id=%s", video_id)

    snippets: list[dict] = []
    errors: list[str] = []

    # Layer 1: yt-dlp
    try:
        snippets = _fetch_via_ytdlp(video_id)
    except Exception as exc:
        _logger.warning("yt-dlp failed | video_id=%s | %s", video_id, exc)
        errors.append(f"yt-dlp: {exc}")

    # Layer 2: youtube-transcript-api
    if not snippets:
        try:
            snippets = _fetch_via_transcript_api(video_id)
        except Exception as exc:
            _logger.warning("transcript-api failed | video_id=%s | %s", video_id, exc)
            errors.append(f"transcript-api: {exc}")

    # Layer 3: YouTube Data API v3 (BYOK)
    if not snippets and api_key:
        try:
            snippets = _fetch_via_youtube_api(video_id, api_key.strip())
        except Exception as exc:
            _logger.warning("YouTube API v3 failed | video_id=%s | %s", video_id, exc)
            errors.append(f"YouTube API v3: {exc}")

    if not snippets:
        raise RuntimeError(
            "Could not retrieve transcript for this video.\n"
            "Tried: yt-dlp, youtube-transcript-api"
            + (", YouTube Data API v3" if api_key else "")
            + f".\nPossible reasons: video has no subtitles, subtitles are disabled, "
            f"or YouTube is blocking requests from this server.\n"
            f"Video URL: {canonical}\n\n"
            f"Tip: Use the 'Paste transcript' tab to paste a transcript manually "
            f"(e.g. from youtubetotranscript.com)."
        )

    markdown = _snippets_to_markdown(snippets, canonical, video_id)
    _logger.info(
        "YouTube transcript ok | video_id=%s | snippets=%d", video_id, len(snippets)
    )
    return markdown
