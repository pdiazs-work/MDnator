import os
import re
import tempfile
import time
from urllib.parse import urlparse

import gradio as gr

from src.config.settings import (
    ALLOWED_EXTENSIONS,
    APP_DESCRIPTION,
    APP_TITLE,
    MAX_BATCH_FILES,
    MAX_CONCURRENT_USERS,
    MAX_FILE_SIZE_MB,
)
from src.core.converter import DocumentConverter
from src.core.text_formatter import format_plain_text
from src.core.url_fetcher import fetch_url, validate_url
from src.core.validators import validate_file
from src.utils.logger import get_logger

_logger = get_logger(__name__)
_converter = DocumentConverter()

_PREVIEW_PLACEHOLDER = "*Convert a document to see the rendered preview.*"


def _compute_stats(markdown: str, elapsed: float, label: str = "") -> str:
    words = len(markdown.split())
    chars = len(markdown)
    headings = len(re.findall(r"^#{1,6}\s", markdown, re.MULTILINE))
    tables = len(re.findall(r"^\|.+\|", markdown, re.MULTILINE))
    parts = []
    if label:
        parts.append(label)
    parts += [
        f"{words:,} words",
        f"{chars:,} chars",
        f"{headings} heading{'s' if headings != 1 else ''}",
    ]
    if tables:
        parts.append(f"{tables} table{'s' if tables != 1 else ''}")
    parts.append(f"{elapsed:.1f}s")
    return " · ".join(parts)


def _emit(markdown: str, elapsed: float, label: str = "") -> tuple:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp_out:
        tmp_out.write(markdown)
        tmp_path = tmp_out.name
    stats = _compute_stats(markdown, elapsed, label=label)
    return (
        markdown,
        gr.update(value=tmp_path, visible=True),
        markdown,
        gr.update(value=stats, visible=True),
    )


def process_files(
    file_paths: list[str] | str | None, progress: gr.Progress = gr.Progress()
):
    if not file_paths:
        raise gr.Error("Please upload a file before converting.")

    if isinstance(file_paths, str):
        file_paths = [file_paths]

    if len(file_paths) > MAX_BATCH_FILES:
        raise gr.Error(f"Maximum {MAX_BATCH_FILES} files at once.")

    results = []
    errors = []
    start = time.monotonic()
    total = len(file_paths)

    progress(0, desc="Starting…")
    for i, fp in enumerate(file_paths):
        name = os.path.basename(fp)
        progress(i / total, desc=f"Converting {name}…")
        ok, msg = validate_file(fp)
        if not ok:
            errors.append(f"**{name}**: {msg}")
            progress((i + 1) / total, desc=f"Skipped {name}")
            continue
        try:
            md = _converter.convert(fp)
            header = f"## {name}\n\n" if total > 1 else ""
            results.append(f"{header}{md}")
        except RuntimeError as exc:
            _logger.error("Conversion error | file=%s | %s", name, exc)
            errors.append(f"**{name}**: {exc}")
        except Exception as exc:
            _logger.error("Unexpected error | file=%s | %s", name, type(exc).__name__)
            errors.append(f"**{name}**: Unexpected error.")
        progress((i + 1) / total, desc=f"Done {name}")

    if not results:
        raise gr.Error("No files converted successfully.\n" + "\n".join(errors))

    progress(1, desc="Building output…")
    markdown = "\n\n---\n\n".join(results)
    if errors:
        markdown += "\n\n---\n\n> **Some files could not be converted:**\n" + "\n".join(
            f"> {e}" for e in errors
        )

    label = f"{len(results)} files" if len(results) > 1 else ""
    return _emit(markdown, time.monotonic() - start, label=label)


def process_url(url: str, progress: gr.Progress = gr.Progress()):
    url = url.strip()
    if not url:
        raise gr.Error("Please enter a URL.")

    ok, msg = validate_url(url)
    if not ok:
        raise gr.Error(msg)

    progress(0.2, desc="Fetching page…")
    start = time.monotonic()
    try:
        html = fetch_url(url)
    except RuntimeError as exc:
        raise gr.Error(str(exc))

    progress(0.6, desc="Converting to Markdown…")
    tmp_html_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", delete=False, encoding="utf-8"
        ) as tmp_html:
            tmp_html.write(html)
            tmp_html_path = tmp_html.name

        markdown = _converter.convert(tmp_html_path)
    except RuntimeError as exc:
        raise gr.Error(f"Conversion failed: {exc}")
    finally:
        if tmp_html_path:
            try:
                os.unlink(tmp_html_path)
            except OSError:
                pass

    if not markdown.strip():
        raise gr.Error("The page returned no readable content.")

    progress(1, desc="Done")
    domain = urlparse(url).netloc
    return _emit(markdown, time.monotonic() - start, label=domain)


def process_text(raw_text: str):
    if not raw_text or not raw_text.strip():
        raise gr.Error("Please paste some text before formatting.")

    start = time.monotonic()
    markdown = format_plain_text(raw_text)

    if not markdown.strip():
        raise gr.Error("No content could be extracted from the input.")

    return _emit(markdown, time.monotonic() - start, label="plain text")


def clear():
    return (
        gr.update(value=None),  # file_input
        gr.update(value=""),  # url_input
        gr.update(value=""),  # text_input
        gr.update(value=None),  # output_text
        gr.update(value=None, visible=False),  # download_file
        _PREVIEW_PLACEHOLDER,  # output_preview
        gr.update(value="", visible=False),  # stats_output
    )


_file_types = sorted(ALLOWED_EXTENSIONS)
_formats_hint = ", ".join(sorted(ext.lstrip(".").upper() for ext in ALLOWED_EXTENSIONS))

with gr.Blocks(title=APP_TITLE) as demo:
    gr.Markdown(f"# {APP_TITLE}\n\n{APP_DESCRIPTION}")

    with gr.Row():
        with gr.Column(scale=1):
            with gr.Tabs():
                with gr.Tab("Documents"):
                    file_input = gr.File(
                        label="Upload document(s)",
                        file_types=_file_types,
                        file_count="multiple",
                        type="filepath",
                        height=160,
                    )
                    gr.Markdown(
                        f"**Formats:** {_formats_hint}  \n"
                        f"**Limit:** {MAX_FILE_SIZE_MB} MB per file · max {MAX_BATCH_FILES} files"
                    )
                    convert_files_btn = gr.Button(
                        "Convert Documents", variant="primary", size="lg"
                    )

                with gr.Tab("From URL"):
                    url_input = gr.Textbox(
                        label="Web page URL",
                        placeholder="https://example.com/article",
                        lines=1,
                        max_lines=1,
                    )
                    gr.Markdown(
                        "Paste any public web page URL. "
                        "Private/internal addresses are blocked.  \n"
                        f"**Limit:** {MAX_FILE_SIZE_MB} MB response"
                    )
                    convert_url_btn = gr.Button(
                        "Fetch & Convert", variant="primary", size="lg"
                    )

                with gr.Tab("Plain Text"):
                    text_input = gr.Textbox(
                        label="Paste plain text",
                        placeholder="Paste any unstructured text here.\n\nMDnator will detect headings, lists, code blocks and convert to organised Markdown.",
                        lines=12,
                        max_lines=40,
                    )
                    gr.Markdown(
                        "Detects **headings** (ALL CAPS or Title Case), "
                        "**lists** (-, *, •, 1.), "
                        "**code blocks** (``` or 4-space indent), "
                        "and **paragraphs** automatically."
                    )
                    convert_text_btn = gr.Button(
                        "Format as Markdown", variant="primary", size="lg"
                    )

            with gr.Row():
                clear_btn = gr.Button("Clear all", variant="secondary", size="sm")
            download_file = gr.File(
                label="Download .md",
                visible=False,
                interactive=False,
            )

        with gr.Column(scale=2):
            with gr.Tabs():
                with gr.Tab("Source"):
                    output_text = gr.Textbox(
                        label="Markdown",
                        lines=25,
                        interactive=False,
                        buttons=["copy"],
                        placeholder="Your converted Markdown will appear here...",
                    )
                with gr.Tab("Preview"):
                    output_preview = gr.Markdown(
                        value=_PREVIEW_PLACEHOLDER,
                        max_height=600,
                    )
            stats_output = gr.Textbox(
                label="Stats",
                interactive=False,
                visible=False,
                lines=1,
                max_lines=1,
            )

    _outputs = [output_text, download_file, output_preview, stats_output]

    convert_files_btn.click(fn=process_files, inputs=[file_input], outputs=_outputs)
    convert_url_btn.click(fn=process_url, inputs=[url_input], outputs=_outputs)
    convert_text_btn.click(fn=process_text, inputs=[text_input], outputs=_outputs)
    clear_btn.click(fn=clear, outputs=[file_input, url_input, text_input] + _outputs)

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=MAX_CONCURRENT_USERS).launch(
        theme=gr.themes.Soft()
    )
