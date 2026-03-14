# AGENTS.md

Guidelines for agentic coding agents working on the NuoYi codebase.

## Project Overview

NuoYi is a Python package for converting PDF and DOCX documents to Markdown using marker-pdf (surya OCR + layout detection). It supports CLI, GUI (PySide6), and Python API interfaces.

## Build, Test, and Lint Commands

```bash
# Install in development mode
pip install -e ".[dev]"

# Install with GUI support
pip install -e ".[gui]"

# Install all dependencies
pip install -e ".[all]"

# Run all tests
pytest

# Run a single test file
pytest tests/test_basic.py

# Run a single test function
pytest tests/test_basic.py::test_version
pytest tests/test_basic.py::TestUtilityFunctions::test_get_gpu_memory_info

# Run tests with coverage
pytest --cov=src/nuoyi --cov-report=term-missing

# Run linting with ruff
ruff check src/ tests/

# Run ruff with auto-fix
ruff check --fix src/ tests/

# Build package
python -m build

# Type check (if mypy installed)
mypy src/nuoyi
```

## Code Style Guidelines

### Imports

```python
# Order: standard library, third-party, local imports
# Separate groups with blank lines

import gc
import os
import re
from pathlib import Path
from typing import Tuple

from docx import Document
from marker.converters.pdf import PdfConverter

from .utils import clean_markdown, DEFAULT_LANGS
```

- Use absolute imports for third-party packages
- Use relative imports for local modules (`.module`)
- Import specific names, avoid `from module import *`

### Formatting

- **Line length**: 100 characters maximum (configured in pyproject.toml)
- **Indentation**: 4 spaces
- **Blank lines**: Two blank lines between top-level definitions, one between methods
- **Quotes**: Prefer double quotes for strings, single quotes acceptable for consistency

### Type Hints

```python
from __future__ import annotations  # Use for modern type syntax

def function(arg: str) -> Tuple[str, dict]:
    ...

def convert_file(
    input_path: str | Path,
    *,
    output_path: str | Path | None = None,
) -> ToolResult:
    ...
```

- Use `from __future__ import annotations` for Python 3.10+ union syntax (`str | Path`)
- Type all function parameters and return values
- Use `Optional[T]` or `T | None` for optional values
- Use `*` in function signatures to force keyword-only arguments after it

### Naming Conventions

- **Modules**: `snake_case` (`converter.py`, `utils.py`)
- **Classes**: `PascalCase` (`MarkerPDFConverter`, `DocxConverter`, `ToolResult`)
- **Functions/Methods**: `snake_case` (`convert_file`, `clean_markdown`)
- **Constants**: `UPPER_SNAKE_CASE` (`SUPPORTED_LANGUAGES`, `DEFAULT_LANGS`)
- **Private methods**: Prefix with underscore (`_load_models_with_fallback`)
- **Protected members**: Single underscore prefix

### Docstrings

```python
def convert_file(self, pdf_path: str) -> Tuple[str, dict]:
    """Convert a single PDF file to Markdown text and extract images.
    
    Returns:
        Tuple of (markdown_text, images_dict) where images_dict maps
        image filenames to PIL Image objects or base64 data.
    """
    ...

def select_device(preferred: str = "auto", min_vram_gb: float = 6.0) -> str:
    """
    Select the best device for running marker-pdf.

    Args:
        preferred: "auto", "cuda", "cpu", or "mps"
        min_vram_gb: Minimum VRAM required to use GPU (default 6GB)

    Returns:
        Device string: "cuda", "cpu", or "mps"
    """
    ...
```

- Use triple-double-quotes for docstrings
- One-line summary for simple functions
- Multi-line with Args/Returns sections for complex functions
- Document parameters and return values

### Error Handling

```python
# For API functions: Return ToolResult with success=False
def convert_file(input_path: str | Path, ...) -> ToolResult:
    if not input_path.exists():
        return ToolResult(success=False, error=f"File not found: {input_path}")
    try:
        # ... conversion logic
        return ToolResult(success=True, data={...})
    except Exception as e:
        return ToolResult(success=False, error=str(e))

# For CLI: Print error and sys.exit(1)
if not input_path.exists():
    print(f"Error: Path not found: {args.input}")
    sys.exit(1)

# For internal functions: Raise exceptions
except RuntimeError as e:
    error_msg = str(e).lower()
    if "cuda" in error_msg and "out of memory" in error_msg:
        # Handle CUDA OOM with fallback
        ...
    raise
```

### Data Classes

```python
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class ToolResult:
    """Standardised return type for all NuoYi API functions."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)
```

- Use `@dataclass` for data containers
- Use `field(default_factory=dict)` for mutable default values

### Testing

```python
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

def test_version():
    """Test that version is accessible."""
    from nuoyi import __version__
    assert __version__ == "0.2.0"

class TestToolResult:
    def test_success(self):
        from nuoyi.api import ToolResult
        r = ToolResult(success=True, data={"markdown": "# Hello"})
        assert r.success is True

    def test_failure(self):
        from nuoyi.api import ToolResult
        r = ToolResult(success=False, error="file not found")
        assert r.error == "file not found"
```

- Use `pytest` framework
- Test functions prefixed with `test_`
- Test classes prefixed with `Test`
- Import inside test functions to avoid import-time side effects
- Use `tempfile.TemporaryDirectory()` for file system tests

## Project Structure

```
NuoYi/
├── src/nuoyi/
│   ├── __init__.py      # Package exports, version
│   ├── __main__.py      # Entry point for `python -m nuoyi`
│   ├── converter.py     # MarkerPDFConverter, DocxConverter classes
│   ├── cli.py           # Command-line interface
│   ├── api.py           # ToolResult, convert_file, convert_directory
│   ├── tools.py         # OpenAI function-calling tool definitions
│   ├── utils.py         # Utility functions, constants
│   └── gui.py           # PySide6 GUI (optional)
├── tests/
│   ├── test_basic.py        # Basic functionality tests
│   └── test_unified_api.py  # API and CLI tests
├── pyproject.toml       # Project configuration
└── requirements.txt     # Dependency reference
```

## Ruff Configuration (pyproject.toml)

```toml
[tool.ruff]
target-version = "py39"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "C4"]
ignore = ["E501"]
```

## Pytest Configuration (pyproject.toml)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

## Key Dependencies

- `marker-pdf>=1.0.0` - PDF conversion engine
- `PyMuPDF>=1.23.0` - PDF page counting
- `python-docx>=0.8.11` - DOCX conversion
- `Pillow>=9.0.0` - Image processing
- `PySide6>=6.5.0` - GUI (optional)
- `pytest>=7.0.0` - Testing (dev)