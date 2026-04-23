---
title: MDnator
emoji: 📄
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 6.12.0
app_file: app.py
pinned: false
license: mit
---

# MDnator — Universal Markdown Converter

Convert any document to clean Markdown in seconds. No installation, no sign-up, no data stored.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Gradio](https://img.shields.io/badge/Gradio-6.12-orange.svg)](https://gradio.app/)

---

## Features

- **Supported formats**: PDF, DOCX, XLSX, PPTX, TXT, CSV, HTML, MD, JSON, XML
- **File limit**: 20 MB per file
- **Direct download** of the generated `.md` file
- **Privacy first** — files are processed in memory and deleted automatically after conversion

## Local Setup

```bash
# Clone the repository
git clone https://github.com/pdiazs-work/MDnator.git
cd MDnator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies (includes dev tools)
pip install -r requirements-dev.txt

# Run the app
python app.py
```

Open `http://localhost:7860` in your browser.

## Running Tests

```bash
pytest tests/ -v
```

## Architecture

```
app.py                   ← Gradio entry point
src/
  config/settings.py    ← Constants and configuration
  core/validators.py    ← File validation (extension, size)
  core/converter.py     ← Conversion engine (markitdown)
  utils/logger.py       ← Structured logging
tests/                  ← Unit tests (pytest)
```

**Stack**: Python 3.10+ · Gradio 6.12 · markitdown (Microsoft) · pytest

## Security

- Strict file extension whitelist
- 20 MB file size limit
- Temporary files deleted automatically after each conversion
- No user data is stored or logged
- Stack traces never exposed to the user

## License

MIT — see [LICENSE](./LICENSE)

---

## Español

Convierte cualquier documento a Markdown limpio en segundos. Sin instalación, sin registro, sin almacenamiento de datos.

**Formatos soportados**: PDF, DOCX, XLSX, PPTX, TXT, CSV, HTML, MD, JSON, XML

**Configuración local**: Clona el repo, crea un entorno virtual, instala `requirements.txt` y ejecuta `python app.py`.

**Seguridad**: Los archivos se procesan en memoria y se eliminan automáticamente. No se guarda ningún dato del usuario.
