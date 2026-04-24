import os
import re
import tempfile
import time
from urllib.parse import urlparse

import gradio as gr

from src.config.settings import (
    ALLOWED_EXTENSIONS,
    APP_TITLE,
    MAX_BATCH_FILES,
    MAX_CONCURRENT_USERS,
    MAX_FILE_SIZE_MB,
)
from src.core.audio_transcriber import (
    _MAX_AUDIO_MB,
    AUDIO_EXTENSIONS,
    transcribe_audio,
    validate_audio_file,
)
from src.core.converter import DocumentConverter
from src.core.text_formatter import format_plain_text
from src.core.url_fetcher import fetch_url, validate_url
from src.core.validators import validate_file
from src.core.youtube_fetcher import fetch_youtube, validate_youtube_url
from src.i18n.translations import LANGUAGES, t
from src.utils.logger import get_logger

_logger = get_logger(__name__)
_converter = DocumentConverter()

_LANG_KEYS = list(LANGUAGES.keys())
_LANG_DISPLAY = list(LANGUAGES.values())
_DEFAULT_LANG = "en"


def _lang_key(display: str) -> str:
    for k, v in LANGUAGES.items():
        if v == display:
            return k
    return _DEFAULT_LANG


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
    file_paths: list[str] | str | None,
    lang_display: str,
    progress: gr.Progress = gr.Progress(),
):
    lang = _lang_key(lang_display)
    if not file_paths:
        raise gr.Error(t(lang, "err_no_file"))

    if isinstance(file_paths, str):
        file_paths = [file_paths]

    if len(file_paths) > MAX_BATCH_FILES:
        raise gr.Error(t(lang, "err_max_files", max_files=MAX_BATCH_FILES))

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
        raise gr.Error(t(lang, "err_no_results") + "\n" + "\n".join(errors))

    progress(1, desc="Building output…")
    markdown = "\n\n---\n\n".join(results)
    if errors:
        markdown += "\n\n---\n\n> **Some files could not be converted:**\n" + "\n".join(
            f"> {e}" for e in errors
        )

    label = f"{len(results)} files" if len(results) > 1 else ""
    return _emit(markdown, time.monotonic() - start, label=label)


def process_url(url: str, lang_display: str, progress: gr.Progress = gr.Progress()):
    lang = _lang_key(lang_display)
    url = url.strip()
    if not url:
        raise gr.Error(t(lang, "err_no_url"))

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
        raise gr.Error(t(lang, "err_no_content"))

    progress(1, desc="Done")
    domain = urlparse(url).netloc
    return _emit(markdown, time.monotonic() - start, label=domain)


def process_text(raw_text: str, lang_display: str):
    lang = _lang_key(lang_display)
    if not raw_text or not raw_text.strip():
        raise gr.Error(t(lang, "err_no_text"))

    start = time.monotonic()
    markdown = format_plain_text(raw_text)

    if not markdown.strip():
        raise gr.Error(t(lang, "err_no_content"))

    return _emit(markdown, time.monotonic() - start, label="plain text")


def process_youtube(url: str, lang_display: str, progress: gr.Progress = gr.Progress()):
    lang = _lang_key(lang_display)
    url = url.strip()
    if not url:
        raise gr.Error(t(lang, "err_no_youtube"))

    ok, msg = validate_youtube_url(url)
    if not ok:
        raise gr.Error(msg)

    progress(0.3, desc="Fetching transcript…")
    start = time.monotonic()
    try:
        markdown = fetch_youtube(url)
    except RuntimeError as exc:
        raise gr.Error(str(exc))

    progress(1, desc="Done")
    return _emit(markdown, time.monotonic() - start, label="YouTube")


def process_audio(
    file_path: str | None,
    api_key: str,
    lang_display: str,
    progress: gr.Progress = gr.Progress(),
):
    lang = _lang_key(lang_display)
    if not file_path:
        raise gr.Error(t(lang, "err_no_audio"))

    if not api_key or not api_key.strip():
        raise gr.Error(t(lang, "err_no_apikey"))

    ok, msg = validate_audio_file(file_path)
    if not ok:
        if msg == "no_audio":
            raise gr.Error(t(lang, "err_no_audio"))
        raise gr.Error(msg)

    progress(0.2, desc="Uploading to Whisper API…")
    start = time.monotonic()
    try:
        markdown = transcribe_audio(file_path, api_key.strip())
    except RuntimeError as exc:
        raise gr.Error(str(exc))

    progress(1, desc="Done")
    return _emit(markdown, time.monotonic() - start, label="audio")


def update_ui(lang_display: str):
    lang = _lang_key(lang_display)
    return (
        gr.update(label=t(lang, "upload_label")),
        gr.update(
            value=t(
                lang, "upload_hint", max_mb=MAX_FILE_SIZE_MB, max_files=MAX_BATCH_FILES
            )
        ),
        gr.update(value=t(lang, "convert_docs_btn")),
        gr.update(label=t(lang, "url_label"), placeholder=t(lang, "url_placeholder")),
        gr.update(value=t(lang, "url_hint", max_mb=MAX_FILE_SIZE_MB)),
        gr.update(value=t(lang, "fetch_btn")),
        gr.update(label=t(lang, "text_label"), placeholder=t(lang, "text_placeholder")),
        gr.update(value=t(lang, "text_hint")),
        gr.update(value=t(lang, "format_btn")),
        gr.update(
            label=t(lang, "youtube_label"), placeholder=t(lang, "youtube_placeholder")
        ),
        gr.update(value=t(lang, "youtube_hint")),
        gr.update(value=t(lang, "youtube_btn")),
        gr.update(label=t(lang, "audio_label")),
        gr.update(value=t(lang, "audio_hint", max_mb=_MAX_AUDIO_MB)),
        gr.update(
            label=t(lang, "audio_apikey_label"),
            placeholder=t(lang, "audio_apikey_placeholder"),
        ),
        gr.update(value=t(lang, "audio_btn")),
        gr.update(value=t(lang, "clear_btn")),
        gr.update(label=t(lang, "download_label")),
        gr.update(
            label=t(lang, "output_label"), placeholder=t(lang, "output_placeholder")
        ),
        gr.update(label=t(lang, "stats_label")),
        gr.update(value=t(lang, "app_description")),
    )


def clear(lang_display: str):
    lang = _lang_key(lang_display)
    return (
        gr.update(value=None),
        gr.update(value=""),
        gr.update(value=""),
        gr.update(value=None),
        gr.update(value=None),
        gr.update(value=None, visible=False),
        t(lang, "preview_placeholder"),
        gr.update(value="", visible=False),
        gr.update(value=""),
    )


_file_types = sorted(ALLOWED_EXTENSIONS)
_audio_types = sorted(AUDIO_EXTENSIONS)
_formats_hint = ", ".join(sorted(ext.lstrip(".").upper() for ext in ALLOWED_EXTENSIONS))

with gr.Blocks(title=APP_TITLE) as demo:
    with gr.Row():
        with gr.Column(scale=4):
            app_desc = gr.Markdown(value=t(_DEFAULT_LANG, "app_description"))
        with gr.Column(scale=1):
            lang_selector = gr.Dropdown(
                choices=_LANG_DISPLAY,
                value=LANGUAGES[_DEFAULT_LANG],
                label=t(_DEFAULT_LANG, "language_label"),
                interactive=True,
            )

    with gr.Row():
        with gr.Column(scale=1):
            with gr.Tabs():
                with gr.Tab(t(_DEFAULT_LANG, "tab_documents")):
                    file_input = gr.File(
                        label=t(_DEFAULT_LANG, "upload_label"),
                        file_types=_file_types,
                        file_count="multiple",
                        type="filepath",
                        height=160,
                    )
                    docs_hint = gr.Markdown(
                        value=t(
                            _DEFAULT_LANG,
                            "upload_hint",
                            max_mb=MAX_FILE_SIZE_MB,
                            max_files=MAX_BATCH_FILES,
                        )
                    )
                    convert_files_btn = gr.Button(
                        t(_DEFAULT_LANG, "convert_docs_btn"),
                        variant="primary",
                        size="lg",
                    )

                with gr.Tab(t(_DEFAULT_LANG, "tab_url")):
                    url_input = gr.Textbox(
                        label=t(_DEFAULT_LANG, "url_label"),
                        placeholder=t(_DEFAULT_LANG, "url_placeholder"),
                        lines=1,
                        max_lines=1,
                    )
                    url_hint = gr.Markdown(
                        value=t(_DEFAULT_LANG, "url_hint", max_mb=MAX_FILE_SIZE_MB)
                    )
                    convert_url_btn = gr.Button(
                        t(_DEFAULT_LANG, "fetch_btn"), variant="primary", size="lg"
                    )

                with gr.Tab(t(_DEFAULT_LANG, "tab_plaintext")):
                    text_input = gr.Textbox(
                        label=t(_DEFAULT_LANG, "text_label"),
                        placeholder=t(_DEFAULT_LANG, "text_placeholder"),
                        lines=12,
                        max_lines=40,
                    )
                    text_hint = gr.Markdown(value=t(_DEFAULT_LANG, "text_hint"))
                    convert_text_btn = gr.Button(
                        t(_DEFAULT_LANG, "format_btn"), variant="primary", size="lg"
                    )

                with gr.Tab(t(_DEFAULT_LANG, "tab_youtube")):
                    youtube_input = gr.Textbox(
                        label=t(_DEFAULT_LANG, "youtube_label"),
                        placeholder=t(_DEFAULT_LANG, "youtube_placeholder"),
                        lines=1,
                        max_lines=1,
                    )
                    youtube_hint = gr.Markdown(value=t(_DEFAULT_LANG, "youtube_hint"))
                    convert_youtube_btn = gr.Button(
                        t(_DEFAULT_LANG, "youtube_btn"), variant="primary", size="lg"
                    )

                with gr.Tab(t(_DEFAULT_LANG, "tab_audio")):
                    audio_input = gr.File(
                        label=t(_DEFAULT_LANG, "audio_label"),
                        file_types=_audio_types,
                        file_count="single",
                        type="filepath",
                        height=140,
                    )
                    audio_hint = gr.Markdown(
                        value=t(_DEFAULT_LANG, "audio_hint", max_mb=_MAX_AUDIO_MB)
                    )
                    audio_apikey_input = gr.Textbox(
                        label=t(_DEFAULT_LANG, "audio_apikey_label"),
                        placeholder=t(_DEFAULT_LANG, "audio_apikey_placeholder"),
                        type="password",
                        lines=1,
                        max_lines=1,
                    )
                    convert_audio_btn = gr.Button(
                        t(_DEFAULT_LANG, "audio_btn"), variant="primary", size="lg"
                    )

            gr.Markdown("---")
            with gr.Row():
                clear_btn = gr.Button(
                    t(_DEFAULT_LANG, "clear_btn"),
                    variant="secondary",
                    size="lg",
                    scale=1,
                )
                download_file = gr.File(
                    label=t(_DEFAULT_LANG, "download_label"),
                    visible=False,
                    interactive=False,
                    scale=2,
                )

        with gr.Column(scale=2):
            with gr.Tabs():
                with gr.Tab(t(_DEFAULT_LANG, "tab_source")):
                    output_text = gr.Textbox(
                        label=t(_DEFAULT_LANG, "output_label"),
                        lines=25,
                        interactive=False,
                        placeholder=t(_DEFAULT_LANG, "output_placeholder"),
                    )
                with gr.Tab(t(_DEFAULT_LANG, "tab_preview")):
                    output_preview = gr.Markdown(
                        value=t(_DEFAULT_LANG, "preview_placeholder"),
                        max_height=600,
                    )
            stats_output = gr.Textbox(
                label=t(_DEFAULT_LANG, "stats_label"),
                interactive=False,
                visible=False,
                lines=1,
                max_lines=1,
            )

    _outputs = [output_text, download_file, output_preview, stats_output]

    _ui_components = [
        file_input,
        docs_hint,
        convert_files_btn,
        url_input,
        url_hint,
        convert_url_btn,
        text_input,
        text_hint,
        convert_text_btn,
        youtube_input,
        youtube_hint,
        convert_youtube_btn,
        audio_input,
        audio_hint,
        audio_apikey_input,
        convert_audio_btn,
        clear_btn,
        download_file,
        output_text,
        stats_output,
        app_desc,
    ]

    convert_files_btn.click(
        fn=process_files, inputs=[file_input, lang_selector], outputs=_outputs
    )
    convert_url_btn.click(
        fn=process_url, inputs=[url_input, lang_selector], outputs=_outputs
    )
    convert_text_btn.click(
        fn=process_text, inputs=[text_input, lang_selector], outputs=_outputs
    )
    convert_youtube_btn.click(
        fn=process_youtube, inputs=[youtube_input, lang_selector], outputs=_outputs
    )
    convert_audio_btn.click(
        fn=process_audio,
        inputs=[audio_input, audio_apikey_input, lang_selector],
        outputs=_outputs,
    )
    clear_btn.click(
        fn=clear,
        inputs=[lang_selector],
        outputs=[file_input, url_input, text_input, youtube_input, audio_input]
        + _outputs,
    )
    lang_selector.change(fn=update_ui, inputs=[lang_selector], outputs=_ui_components)

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=MAX_CONCURRENT_USERS).launch(
        theme=gr.themes.Soft()
    )
