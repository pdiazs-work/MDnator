from src.core.text_formatter import format_plain_text


def test_empty_input():
    assert format_plain_text("") == ""
    assert format_plain_text("   \n  ") == ""


def test_simple_paragraph():
    result = format_plain_text("Hello world. This is a test.")
    assert "Hello world" in result


def test_allcaps_heading():
    text = "INTRODUCTION\n\nSome paragraph text here."
    result = format_plain_text(text)
    assert result.startswith("# INTRODUCTION")


def test_title_case_heading():
    text = "Getting Started\n\nFirst paragraph of content."
    result = format_plain_text(text)
    assert "# Getting Started" in result or "## Getting Started" in result


def test_list_dash():
    text = "Items:\n- First item\n- Second item\n- Third item"
    result = format_plain_text(text)
    assert "- First item" in result
    assert "- Second item" in result


def test_list_bullet_normalised():
    text = "• Option one\n• Option two"
    result = format_plain_text(text)
    assert "- Option one" in result
    assert "- Option two" in result


def test_numbered_list():
    text = "Steps:\n1. Do this\n2. Then that\n3. Finally"
    result = format_plain_text(text)
    assert "1. Do this" in result
    assert "2. Then that" in result


def test_existing_markdown_heading_preserved():
    text = "## Already Markdown\n\nSome text."
    result = format_plain_text(text)
    assert "## Already Markdown" in result


def test_existing_code_fence_preserved():
    text = "```python\nprint('hello')\n```"
    result = format_plain_text(text)
    assert "```python" in result
    assert "print('hello')" in result


def test_multiple_blank_lines_collapsed():
    text = "Para one.\n\n\n\nPara two."
    result = format_plain_text(text)
    assert "\n\n\n" not in result


def test_long_line_not_heading():
    long = "This is a very long line that definitely should not be treated as a heading because it exceeds the threshold."
    result = format_plain_text(long)
    assert not result.startswith("#")


def test_no_trailing_newline():
    result = format_plain_text("Hello world")
    assert not result.endswith("\n")
