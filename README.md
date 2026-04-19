---
title: MDnator
emoji: 📄
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: mit
---

# MDnator - Universal Markdown Converter

Convierte documentos a Markdown limpio en segundos, sin instalar nada.

## Características

- **Formatos soportados**: PDF, DOCX, XLSX, PPTX, TXT, CSV, HTML, MD, JSON, XML
- **Límite de archivo**: 20 MB
- **Descarga directa** del archivo `.md` generado
- **Sin registro ni almacenamiento** — los archivos se procesan en memoria y se eliminan automáticamente

## Uso local

```bash
# 1. Clonar el repositorio
git clone https://github.com/pdiazs-work/MDnator.git
cd MDnator

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar la app
python app.py
```

Abre `http://localhost:7860` en tu navegador.

## Arquitectura

```
app.py                  ← Entry point Gradio
src/
  config/settings.py   ← Constantes y configuración
  core/validators.py   ← Validación de archivos (extensión, tamaño)
  core/converter.py    ← Motor de conversión con markitdown
  utils/logger.py      ← Logging estructurado
tests/                 ← Tests unitarios con pytest
```

**Stack**: Python 3.10+ · Gradio 4.44 · markitdown (Microsoft) · pytest

## Seguridad

- Whitelist estricta de extensiones permitidas
- Límite de 20 MB por archivo
- Archivos temporales eliminados automáticamente tras cada conversión
- Sin persistencia de datos de usuario
- Logs sin contenido de archivos (solo metadata: nombre, tamaño, tiempo)
- Sin exposición de stack traces al usuario

## Licencia

MIT — ver [LICENSE](./LICENSE)
