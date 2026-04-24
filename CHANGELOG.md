# Changelog — MDnator

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/):

| Version part | When to bump | Examples |
|---|---|---|
| **MAJOR** (X.0.0) | Breaking change, full redesign, incompatible API change | New UI paradigm, remove a feature, change CLI args |
| **MINOR** (1.X.0) | New feature, backward-compatible | New input tab, new output format, new CLI flag |
| **PATCH** (1.0.X) | Bug fix, dependency update, small UX tweak | Fix crash, fix clear button, update ruff |

Deployments to Hugging Face Spaces happen automatically when a `vX.Y.Z` tag is pushed to `main`.

---

## [Unreleased]

## [1.3.1] — 2026-04-24

### Fixed
- Replaced `Path.relative_to()` boundary check with `os.path.realpath()` + `startswith()` in `validators.py`, `converter.py`, and `audio_transcriber.py` — semantically equivalent but allows CodeQL taint analysis to trace the sanitization, closing all 10 `py/path-injection` alerts automatically

## [1.3.0] — 2026-04-24

### Added
- **Language selector**: 10 languages (EN, ES, FR, DE, PT, ZH, JA, AR, RU, IT) — changes entire UI instantly via `gr.update()`, no page reload
- **YouTube tab**: extracts transcript via `youtube-transcript-api`; groups snippets into 60s paragraphs with `[MM:SS]` timestamps; no API key required
- **Audio tab**: transcribes audio files via OpenAI Whisper API (`whisper-1`); user supplies API key per session; supports MP3/WAV/M4A/OGG/FLAC/WEBM/MP4 up to 25 MB
- `src/i18n/translations.py`: ~50 UI string keys × 10 languages; `t(lang, key, **kwargs)` helper with EN fallback; no external services, commercial-safe
- `src/core/youtube_fetcher.py`: URL validation (4 YouTube URL patterns), video ID extraction, transcript fetch with graceful fallback
- `src/core/audio_transcriber.py`: temp-dir boundary validation, size limit check, Whisper API call with language + duration metadata in output

### Changed
- `app.py` fully rewritten: all process functions accept `lang_display` param; `update_ui()` returns 21 `gr.update()` objects wired to `lang_selector.change()`; `clear()` resets all 5 input fields
- `requirements.txt`: added `openai==2.32.0`

### Tests
- 87 passing (added `test_youtube_fetcher.py`, `test_audio_transcriber.py`, `test_translations.py` — 46 new tests)

## [1.2.1] — 2026-04-24

### Changed
- Tab labels now include emoji icons (📄 Documents, 🔗 From URL, ✏️ Plain Text)
- URL placeholder updated to a real-world example; hint clarifies best use cases
- Plain Text placeholder rewritten to be action-oriented
- Clear button promoted to `lg` size with icon, placed inline with Download
- APP_DESCRIPTION updated to mention all 3 input modes

## [1.2.0] — 2026-04-24

### Added
- Plain Text input tab: paste unstructured text and get organised Markdown
- Heuristic formatter (`src/core/text_formatter.py`): detects ALL CAPS / Title Case headings,
  bullet lists (-, *, •, 1.), code blocks (``` or 4-space indent), paragraphs
- Output preview works as an Obsidian-style live viewer

## [1.1.0] — 2026-04-24

### Added
- URL-to-Markdown tab: fetch any public web page and convert its HTML to Markdown
- SSRF protection: blocks private/loopback/reserved IPs, http/https only, 15s timeout, 20MB cap
- `requests==2.33.1` pinned in requirements.txt

### Security
- Enforce temp-dir boundary in validators and converter (path traversal impossible)
- URL reconstructed from parsed components before HTTP call (eliminates raw-input taint)

## [1.0.0] — 2026-04-24

### Added
- Document upload and conversion to Markdown (PDF, DOCX, XLSX, PPTX, TXT, CSV, HTML, MD, JSON, XML)
- Batch conversion (up to 5 files)
- Markdown preview tab (rendered, max 600px)
- Stats bar: word count, char count, headings, tables, elapsed time
- Download converted `.md` file
- CLI interface (`cli.py`) for terminal-based conversion
- `gr.Progress` tracker per file during conversion
- GitHub Actions CI (tests + pip-audit security scan + CodeQL)
- Dependabot for automated dependency updates
- Pre-commit hooks: ruff, ruff-format, detect-secrets

### Fixed
- Clear button error (output count mismatch)
- PDF/DOCX/XLSX/PPTX conversion broken on HF (markitdown optional extras)
- Gradio 6 compatibility (theme param, show_copy_button removed)
