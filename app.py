import re
import tempfile
import time

import gradio as gr

from src.config.settings import (
    ALLOWED_EXTENSIONS,
    APP_DESCRIPTION,
    APP_TITLE,
    MAX_CONCURRENT_USERS,
    MAX_FILE_SIZE_MB,
)
from src.core.converter import DocumentConverter
from src.core.validators import validate_file
from src.utils.logger import get_logger

_logger = get_logger(__name__)
_converter = DocumentConverter()


def _compute_stats(markdown: str, elapsed: float, file_count: int = 1) -> str:
    words = len(markdown.split())
    chars = len(markdown)
    headings = len(re.findall(r"^#{1,6}\s", markdown, re.MULTILINE))
    tables = len(re.findall(r"^\|.+\|", markdown, re.MULTILINE))
    parts = []
    if file_count > 1:
        parts.append(f"{file_count} files")
    parts += [
        f"{words:,} words",
        f"{chars:,} chars",
        f"{headings} heading{'s' if headings != 1 else ''}",
    ]
    if tables:
        parts.append(f"{tables} table{'s' if tables != 1 else ''}")
    parts.append(f"{elapsed:.1f}s")
    return " · ".join(parts)


def process(file_path: str | None):
    if not file_path:
        raise gr.Error("Please upload a file before converting.")

    ok, msg = validate_file(file_path)
    if not ok:
        raise gr.Error(msg)

    start = time.monotonic()
    try:
        markdown = _converter.convert(file_path)
    except RuntimeError as exc:
        _logger.error("Conversion error | %s", exc)
        raise gr.Error(str(exc))
    except Exception as exc:
        _logger.error("Unexpected error | %s", type(exc).__name__)
        raise gr.Error("Unexpected error while processing the file.")
    elapsed = time.monotonic() - start

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp_out:
        tmp_out.write(markdown)
        tmp_path = tmp_out.name

    stats = _compute_stats(markdown, elapsed)

    return (
        markdown,
        gr.update(value=tmp_path, visible=True),
        markdown,
        gr.update(value=stats, visible=True),
    )


_file_types = sorted(ALLOWED_EXTENSIONS)
_formats_hint = ", ".join(sorted(ext.lstrip(".").upper() for ext in ALLOWED_EXTENSIONS))

with gr.Blocks(title=APP_TITLE) as demo:
    gr.Markdown(f"# {APP_TITLE}\n{APP_DESCRIPTION}")

    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(
                label="Upload your document",
                file_types=_file_types,
                type="filepath",
            )
            gr.Markdown(
                f"**Formats:** {_formats_hint}  \n**Max size:** {MAX_FILE_SIZE_MB} MB"
            )
            convert_btn = gr.Button("Convert to Markdown", variant="primary", size="lg")
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
                        value="*Convert a document to see the rendered preview.*"
                    )
            stats_output = gr.Textbox(
                label="Stats",
                interactive=False,
                visible=False,
                lines=1,
                max_lines=1,
            )

    convert_btn.click(
        fn=process,
        inputs=[file_input],
        outputs=[output_text, download_file, output_preview, stats_output],
    )

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=MAX_CONCURRENT_USERS).launch(
        theme=gr.themes.Soft()
    )
