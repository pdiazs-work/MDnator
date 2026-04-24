# MDnator — Bitácora de Hitos

## v1.3.0 — 2026-04-24
**i18n + YouTube + Audio tabs**
- Selector de idioma (10 idiomas) actualiza toda la UI sin recargar
- Tab YouTube: transcripción via youtube-transcript-api, párrafos de 60s con timestamps
- Tab Audio: transcripción via OpenAI Whisper API (whisper-1), key del usuario por sesión
- Módulo i18n propio: ~50 claves × 10 idiomas, sin servicios externos, uso comercial libre
- 87 tests pasando (46 nuevos)
- requirements.txt: openai==2.32.0

## v1.2.1 — 2026-04-24
**UX polish**
- Emojis en tabs, hints mejorados, Clear button con ícono y tamaño lg
- APP_DESCRIPTION actualizado para mencionar los 3 modos de entrada

## v1.2.0 — 2026-04-24
**Tab "Plain Text → Markdown"**
- Heurística para detectar headings (ALL CAPS / Title Case), listas y bloques de código
- `src/core/text_formatter.py` con `format_plain_text()`

## v1.1.0 — 2026-04-24
**Tab "From URL"**
- SSRF-safe fetcher (`src/core/url_fetcher.py`)
- `_is_private_ip()` bloquea RFC1918/loopback, URL reconstruida via `urlunparse()`

## v1.0.0 — 2026-04-24
**Primera versión estable + auto-deploy**
- Deploy automático a HF Spaces via tags `v*` con `deploy.yml`
- CI con permisos correctos, CodeQL configurado

## Hitos previos (sin versión semver)
- Space creado en Hugging Face: `pdiazs-work/MDnator`
- Pre-commit hooks: ruff, detect-secrets
- Tests unitarios con pytest
- Dependencias vulnerables auditadas y parchadas
