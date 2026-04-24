from unittest.mock import MagicMock, patch

import pytest

from src.core.url_fetcher import fetch_url, validate_url


class TestValidateUrl:
    def test_empty_url(self):
        ok, msg = validate_url("")
        assert not ok
        assert "empty" in msg.lower()

    def test_invalid_scheme(self):
        ok, msg = validate_url("ftp://example.com/file.txt")
        assert not ok
        assert "http" in msg.lower()

    def test_missing_host(self):
        ok, msg = validate_url("https://")
        assert not ok

    def test_valid_http(self):
        with patch("src.core.url_fetcher._is_private_ip", return_value=False):
            ok, msg = validate_url("http://example.com")
        assert ok
        assert msg == ""

    def test_valid_https(self):
        with patch("src.core.url_fetcher._is_private_ip", return_value=False):
            ok, msg = validate_url("https://example.com/page")
        assert ok

    def test_private_ip_blocked(self):
        with patch("src.core.url_fetcher._is_private_ip", return_value=True):
            ok, msg = validate_url("http://192.168.1.1")
        assert not ok
        assert "private" in msg.lower() or "internal" in msg.lower()

    def test_localhost_blocked(self):
        ok, msg = validate_url("http://localhost/admin")
        assert not ok


class TestFetchUrl:
    def _mock_response(self, content: str, content_type="text/html", status=200):
        resp = MagicMock()
        resp.status_code = status
        resp.headers = {"Content-Type": content_type}
        resp.encoding = "utf-8"
        resp.iter_content.return_value = [content.encode("utf-8")]
        resp.raise_for_status = MagicMock()
        return resp

    def test_fetch_returns_html(self):
        with patch("src.core.url_fetcher._is_private_ip", return_value=False), patch(
            "requests.get"
        ) as mock_get:
            mock_get.return_value = self._mock_response("<h1>Hello</h1>")
            result = fetch_url("https://example.com")
        assert "Hello" in result

    def test_invalid_url_raises(self):
        with pytest.raises(RuntimeError, match="http"):
            fetch_url("ftp://example.com")

    def test_timeout_raises(self):
        import requests as req_lib

        with patch("src.core.url_fetcher._is_private_ip", return_value=False), patch(
            "requests.get", side_effect=req_lib.exceptions.Timeout
        ):
            with pytest.raises(RuntimeError, match="timed out"):
                fetch_url("https://example.com")
