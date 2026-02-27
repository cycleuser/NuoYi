# Changelog

All notable changes to NuoYi will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-27

### Changed

- Removed try/except imports for all dependencies (marker-pdf, PyMuPDF, python-docx)
  - Missing dependencies now raise clear ImportError immediately
- Version is now defined only in `src/nuoyi/__init__.py` (single source of truth)
  - `pyproject.toml` reads version dynamically via hatchling

## [0.1.0] - 2026-02-27

### Added

- Initial release of NuoYi
- PDF to Markdown conversion using marker-pdf
- DOCX to Markdown conversion using python-docx
- Command-line interface with batch processing support
- PySide6 GUI for batch conversion
- Automatic GPU/CPU device selection based on available VRAM
- Automatic fallback to CPU on CUDA out of memory errors
- Image extraction from PDFs with automatic path updates in markdown
- Multi-language support (default: Chinese and English)
- Page range selection for partial PDF conversion
- Force OCR option for digital PDFs
- Markdown post-processing to fix broken citation links from marker-pdf
  - Removes invalid internal page anchors (e.g., `[Author](#page-10-0)` -> `Author`)
  - Fixes unbalanced parentheses in academic citations
  - Prevents KaTeX parse errors in Markdown renderers
