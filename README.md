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

**Convert documents, web pages, or plain text to clean Markdown in seconds.**
No installation, no sign-up, no data stored.

[![Try on Hugging Face](https://img.shields.io/badge/🤗-Try%20on%20HF%20Spaces-yellow)](https://huggingface.co/spaces/pdiazs-work/MDnator)
[![CI](https://github.com/pdiazs-work/MDnator/actions/workflows/ci.yml/badge.svg)](https://github.com/pdiazs-work/MDnator/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Gradio 6.12](https://img.shields.io/badge/Gradio-6.12-orange.svg)](https://gradio.app/)
[![Version](https://img.shields.io/badge/version-1.2.1-blueviolet)](./CHANGELOG.md)

---

## Screenshots

**📄 Document conversion** — upload PDF, DOCX, XLSX, PPTX and more, get Markdown instantly

![Documents tab](docs/screenshots/tab-documents.png)

**🔗 URL to Markdown** — paste any public web page URL and convert its content

![URL tab](docs/screenshots/tab-url.png)

**✏️ Plain Text formatter** — paste unstructured text and get organised Markdown with auto-detected headings, lists and code blocks

![Plain Text tab](docs/screenshots/tab-plaintext.png)

---

## Features

| Feature | Details |
|---|---|
| 📄 **Document conversion** | PDF, DOCX, XLSX, PPTX, TXT, CSV, HTML, MD, JSON, XML |
| 🔗 **URL to Markdown** | Fetches any public web page and converts its HTML |
| ✏️ **Plain Text formatter** | Heuristic detection of headings, lists, code blocks |
| 👁 **Live preview** | Source + rendered Markdown preview side by side |
| 📊 **Stats bar** | Word count, char count, headings, tables, elapsed time |
| ⬇️ **Download** | Download the result as a `.md` file |
| 📦 **Batch** | Convert up to 5 files at once |
| 🖥 **CLI** | Terminal-based conversion via `cli.py` |
| 🔒 **Privacy** | Files processed in temp memory, deleted after conversion, no data stored |

---

## Security

- File paths restricted to the system temp directory (path traversal impossible)
- URL fetcher blocks private/loopback/reserved IPs (SSRF protection)
- URLs reconstructed from parsed components before HTTP call
- Strict file extension whitelist + 20 MB size limit
- No user data logged or persisted
- `pip-audit` runs on every CI build — currently **no known vulnerabilities**
- CodeQL analysis on every PR

---

## Local Setup

```bash
# Clone
git clone https://github.com/pdiazs-work/MDnator.git
cd MDnator

# Virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# Install dev dependencies (includes runtime + dev tools)
pip install -r requirements-dev.txt

# Run
python app.py
# → Open http://localhost:7860
```

## CLI Usage

```bash
# Single file to stdout
python cli.py document.pdf

# Save to file
python cli.py report.docx -o report.md

# Batch — multiple files into one output
python cli.py file1.pdf file2.docx -o combined.md
```

## Running Tests

```bash
pytest tests/ -v
# 41 tests, all passing
```

---

## Architecture

```
app.py                        ← Gradio UI — 3 input tabs + shared output panel
cli.py                        ← CLI interface
CHANGELOG.md                  ← Semantic versioning history

src/
  config/settings.py          ← Constants (limits, allowed extensions, app metadata)
  core/
    validators.py             ← File validation: extension + size + temp-dir boundary
    converter.py              ← markitdown engine with path-safety checks
    url_fetcher.py            ← HTTP fetcher with SSRF protection
    text_formatter.py         ← Heuristic plain-text → Markdown formatter
  utils/logger.py             ← Structured logging (no file contents in logs)

tests/                        ← pytest unit tests (41 tests)
.github/workflows/
  ci.yml                      ← Tests + pip-audit security scan on every PR
  deploy.yml                  ← Auto-deploy to HF Space on git tag push
```

**Stack**: Python 3.12 · Gradio 6.12 · [markitdown](https://github.com/microsoft/markitdown) (Microsoft) · requests · pytest

---

## Deployment

Deploy to Hugging Face Spaces is fully automated via git tags:

```bash
git tag v1.2.1
git push origin v1.2.1
# → GitHub Actions pushes to HF Space automatically
```

See [CHANGELOG.md](./CHANGELOG.md) for the full version history and semver convention.

---

## License

MIT — see [LICENSE](./LICENSE)

---
---

# MDnator — Conversor Universal a Markdown

**Convierte documentos, páginas web o texto plano a Markdown limpio en segundos.**
Sin instalación, sin registro, sin almacenamiento de datos.

[![Pruébalo en Hugging Face](https://img.shields.io/badge/🤗-Probar%20en%20HF%20Spaces-yellow)](https://huggingface.co/spaces/pdiazs-work/MDnator)

---

## Características

| Función | Detalle |
|---|---|
| 📄 **Conversión de documentos** | PDF, DOCX, XLSX, PPTX, TXT, CSV, HTML, MD, JSON, XML |
| 🔗 **URL a Markdown** | Descarga cualquier página web pública y convierte su contenido |
| ✏️ **Formateador de texto plano** | Detecta automáticamente títulos, listas y bloques de código |
| 👁 **Vista previa en vivo** | Panel Source + Preview renderizado en paralelo |
| 📊 **Panel de estadísticas** | Palabras, caracteres, títulos, tablas, tiempo de conversión |
| ⬇️ **Descarga** | Descarga el resultado como archivo `.md` |
| 📦 **Lote** | Convierte hasta 5 archivos a la vez |
| 🖥 **CLI** | Conversión desde terminal vía `cli.py` |
| 🔒 **Privacidad** | Archivos procesados en memoria temporal, eliminados automáticamente |

---

## Configuración local

```bash
git clone https://github.com/pdiazs-work/MDnator.git
cd MDnator
python -m venv venv
venv\Scripts\activate          # Linux/Mac: source venv/bin/activate
pip install -r requirements-dev.txt
python app.py
# → Abre http://localhost:7860
```

## Seguridad

- Rutas de archivo restringidas al directorio temporal del sistema (imposible path traversal)
- Fetcher de URLs bloquea IPs privadas/internas (protección SSRF)
- Lista blanca estricta de extensiones + límite de 20 MB por archivo
- Sin datos de usuario guardados ni registrados
- `pip-audit` en cada build de CI — actualmente **sin vulnerabilidades conocidas**

## Versiones

Ver [CHANGELOG.md](./CHANGELOG.md) para el historial completo y la convención semver utilizada.

## Licencia

MIT — ver [LICENSE](./LICENSE)
