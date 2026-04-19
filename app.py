import tempfile

import gradio as gr

from src.config.settings import (
    ALLOWED_EXTENSIONS,
    APP_DESCRIPTION,
    APP_TITLE,
    MAX_CONCURRENT_USERS,
)
from src.core.converter import DocumentConverter
from src.core.validators import validate_file
from src.utils.logger import get_logger

_logger = get_logger(__name__)
_converter = DocumentConverter()


def process(file_path: str | None):
    if not file_path:
        raise gr.Error("Please upload a file before converting.")

    ok, msg = validate_file(file_path)
    if not ok:
        raise gr.Error(msg)

    try:
        markdown = _converter.convert(file_path)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as tmp_out:
            tmp_out.write(markdown)
            tmp_path = tmp_out.name

        return markdown, gr.File(value=tmp_path, visible=True, label="Download .md")

    except RuntimeError as exc:
        _logger.error("Conversion error | %s", exc)
        raise gr.Error(str(exc))
    except Exception as exc:
        _logger.error("Unexpected error | %s", type(exc).__name__)
        raise gr.Error("Unexpected error while processing the file.")


file_types = sorted(ALLOWED_EXTENSIONS)

with gr.Blocks(title=APP_TITLE, theme=gr.themes.Soft()) as demo:
    gr.Markdown(f"# {APP_TITLE}\n{APP_DESCRIPTION}")

    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(
                label="Upload your document",
                file_types=file_types,
                type="filepath",
            )
            convert_btn = gr.Button("Convert to Markdown", variant="primary")

        with gr.Column(scale=2):
            output_text = gr.Textbox(
                label="Markdown output",
                lines=25,
                show_copy_button=True,
                interactive=False,
            )
            download_file = gr.File(
                label="Download .md",
                visible=False,
                interactive=False,
            )

    convert_btn.click(
        fn=process,
        inputs=[file_input],
        outputs=[output_text, download_file],
    )

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=MAX_CONCURRENT_USERS).launch()
