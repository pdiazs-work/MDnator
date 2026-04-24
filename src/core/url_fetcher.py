import ipaddress
import socket
from urllib.parse import urlparse

import requests

from src.config.settings import MAX_FILE_SIZE_BYTES
from src.utils.logger import get_logger

_logger = get_logger(__name__)

_TIMEOUT = 15
_ALLOWED_SCHEMES = {"http", "https"}
_BLOCKED_CONTENT_TYPES = {"application/octet-stream", "application/zip"}


def _is_private_ip(hostname: str) -> bool:
    """Return True if hostname resolves to a private/loopback/link-local address."""
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(hostname))
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except (socket.gaierror, ValueError):
        return True


def validate_url(url: str) -> tuple[bool, str]:
    url = url.strip()
    if not url:
        return False, "URL cannot be empty."
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return False, "Only http:// and https:// URLs are supported."
    if not parsed.netloc:
        return False, "Invalid URL — missing host."
    if _is_private_ip(parsed.hostname or ""):
        return False, "Requests to private or internal addresses are not allowed."
    return True, ""


def fetch_url(url: str) -> str:
    """Fetch URL and return its HTML/text content as a string.

    Raises RuntimeError on any failure.
    """
    url = url.strip()
    ok, msg = validate_url(url)
    if not ok:
        raise RuntimeError(msg)

    try:
        resp = requests.get(
            url,
            timeout=_TIMEOUT,
            stream=True,
            headers={
                "User-Agent": "MDnator/1.1 (+https://huggingface.co/spaces/pdiazs-work/MDnator)"
            },
        )
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        _logger.warning("URL fetch timeout | url=%s", url)
        raise RuntimeError("Request timed out (15 s). Try a smaller page.")
    except requests.exceptions.TooManyRedirects:
        raise RuntimeError("Too many redirects.")
    except requests.exceptions.RequestException as exc:
        _logger.warning("URL fetch failed | url=%s | error=%s", url, type(exc).__name__)
        raise RuntimeError(f"Could not fetch URL: {exc}")

    content_type = resp.headers.get("Content-Type", "").split(";")[0].strip()
    if content_type in _BLOCKED_CONTENT_TYPES:
        raise RuntimeError(f"Unsupported content type: {content_type}")

    chunks = []
    total = 0
    for chunk in resp.iter_content(chunk_size=32768, decode_unicode=False):
        total += len(chunk)
        if total > MAX_FILE_SIZE_BYTES:
            raise RuntimeError(
                f"Response exceeds {MAX_FILE_SIZE_BYTES // (1024*1024)} MB limit."
            )
        chunks.append(chunk)

    raw = b"".join(chunks)
    encoding = resp.encoding or "utf-8"
    try:
        return raw.decode(encoding, errors="replace")
    except (LookupError, UnicodeDecodeError):
        return raw.decode("utf-8", errors="replace")
