import os
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
        raise gr.Error("Por favor sube un archivo antes de convertir.")

    ok, msg = validate_file(file_path)
    if not ok:
        raise gr.Error(msg)

    tmp_out = None
    try:
        markdown = _converter.convert(file_path)

        suffix = ".md"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, delete=False, encoding="utf-8"
        ) as tmp_out:
            tmp_out.write(markdown)
            tmp_path = tmp_out.name

        return markdown, gr.File(value=tmp_path, visible=True, label="Descargar .md")

    except RuntimeError as exc:
        _logger.error("Error en process | %s", exc)
        raise gr.Error(str(exc))
    except Exception as exc:
        _logger.error("Error inesperado en process | %s", type(exc).__name__)
        raise gr.Error("Error inesperado al procesar el archivo.")


file_types = [ext for ext in sorted(ALLOWED_EXTENSIONS)]

with gr.Blocks(title=APP_TITLE, theme=gr.themes.Soft()) as demo:
    gr.Markdown(f"# {APP_TITLE}\n{APP_DESCRIPTION}")

    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(
                label="Sube tu documento",
                file_types=file_types,
                type="filepath",
            )
            convert_btn = gr.Button("Convertir a Markdown", variant="primary")

        with gr.Column(scale=2):
            output_text = gr.Textbox(
                label="Resultado en Markdown",
                lines=25,
                show_copy_button=True,
                interactive=False,
            )
            download_file = gr.File(
                label="Descargar .md",
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
