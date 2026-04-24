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
