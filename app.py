import os
import re
import tempfile
import time

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
from src.core.validators import validate_file
from src.utils.logger import get_logger

_logger = get_logger(__name__)
_converter = DocumentConverter()

_PREVIEW_PLACEHOLDER = "*Convert a document to see the rendered preview.*"


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


def process(file_paths: list[str] | str | None, progress: gr.Progress = gr.Progress()):
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
        progress((i) / total, desc=f"Converting {name}…")
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
        detail = "\n".join(errors)
        raise gr.Error(f"No files converted successfully.\n{detail}")

    progress(1, desc="Building output…")
    markdown = "\n\n---\n\n".join(results)
    if errors:
        markdown += "\n\n---\n\n> **Some files could not be converted:**\n" + "\n".join(
            f"> {e}" for e in errors
        )

    elapsed = time.monotonic() - start

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp_out:
        tmp_out.write(markdown)
        tmp_path = tmp_out.name

    stats = _compute_stats(markdown, elapsed, file_count=len(results))

    return (
        markdown,
        gr.update(value=tmp_path, visible=True),
        markdown,
        gr.update(value=stats, visible=True),
    )


def clear():
    return (
        gr.update(value=None),  # file_input
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
            with gr.Row():
                convert_btn = gr.Button(
                    "Convert", variant="primary", size="lg", scale=3
                )
                clear_btn = gr.Button("Clear", variant="secondary", size="lg", scale=1)
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

    convert_btn.click(fn=process, inputs=[file_input], outputs=_outputs)
    clear_btn.click(fn=clear, outputs=[file_input] + _outputs)

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=MAX_CONCURRENT_USERS).launch(
        theme=gr.themes.Soft()
    )
