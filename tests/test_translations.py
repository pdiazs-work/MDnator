"""Tests for i18n translations module."""

import pytest

from src.i18n.translations import LANGUAGES, TRANSLATIONS, t


def test_all_languages_present():
    for lang in LANGUAGES:
        assert lang in TRANSLATIONS, f"Missing translation block for '{lang}'"


def test_english_has_all_keys():
    en_keys = set(TRANSLATIONS["en"].keys())
    assert len(en_keys) > 0


def test_all_languages_have_en_keys():
    en_keys = set(TRANSLATIONS["en"].keys())
    for lang, strings in TRANSLATIONS.items():
        missing = en_keys - set(strings.keys())
        assert not missing, f"Language '{lang}' is missing keys: {missing}"


def test_t_returns_english_for_unknown_lang():
    result = t("xx", "convert_docs_btn")
    assert result == TRANSLATIONS["en"]["convert_docs_btn"]


def test_t_returns_key_if_missing_everywhere():
    result = t("en", "this_key_does_not_exist")
    assert result == "this_key_does_not_exist"


def test_t_format_kwargs():
    result = t("en", "upload_hint", max_mb=10, max_files=5)
    assert "10" in result
    assert "5" in result


def test_t_all_languages_smoke():
    for lang in LANGUAGES:
        val = t(lang, "convert_docs_btn")
        assert isinstance(val, str)
        assert val != ""


@pytest.mark.parametrize("lang", list(LANGUAGES.keys()))
def test_t_format_upload_hint(lang):
    result = t(lang, "upload_hint", max_mb=25, max_files=10)
    assert isinstance(result, str)
    assert result != ""
