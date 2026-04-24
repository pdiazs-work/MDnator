"""Tests for youtube_fetcher module."""

import pytest

from src.core.youtube_fetcher import extract_video_id, validate_youtube_url


@pytest.mark.parametrize(
    "url,expected_valid",
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", True),
        ("https://youtu.be/dQw4w9WgXcQ", True),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", True),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", True),
        ("http://youtu.be/dQw4w9WgXcQ", True),
        ("youtu.be/dQw4w9WgXcQ", True),
        ("https://vimeo.com/123456", False),
        ("https://example.com", False),
        ("", False),
        ("   ", False),
    ],
)
def test_validate_youtube_url(url, expected_valid):
    valid, msg = validate_youtube_url(url)
    assert valid == expected_valid
    if not expected_valid and url.strip():
        assert msg != ""


@pytest.mark.parametrize(
    "url,expected_id",
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?list=PL&v=abc1234XYZW", "abc1234XYZW"),
        ("https://vimeo.com/123456", None),
    ],
)
def test_extract_video_id(url, expected_id):
    assert extract_video_id(url) == expected_id
