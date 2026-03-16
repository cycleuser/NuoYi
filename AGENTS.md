# AGENTS.md

Guidelines for agentic coding agents working on the NuoYi codebase.

## Project Overview

NuoYi converts PDF and DOCX documents to Markdown using marker-pdf (surya OCR + layout detection). Supports CLI, GUI (PySide6), and Python API interfaces.

## Build, Test, and Lint Commands

```bash
# Install in development mode
pip install -e ".[dev]"

# Install with GUI support
pip install -e ".[gui]"

# Run all tests
pytest

# Run a single test function (IMPORTANT)
pytest tests/test_basic.py::test_version
pytest tests/test_basic.py::TestUtilityFunctions::test_get_gpu_memory_info

# Run tests with coverage
pytest --cov=src/nuoyi --cov-report=term-missing

# Run linting with ruff
ruff check src/ tests/
ruff check --fix src/ tests/

# Build package
python -m build
```

## Code Style Guidelines

### Imports

```python
# Order: standard library, third-party, local imports (separate with blank lines)
import os
from pathlib import Path
from typing import Tuple

from docx import Document
from marker.converters.pdf import PdfConverter

from .utils import clean_markdown
```

- Absolute imports for third-party, relative for local (`.module`)
- Import specific names, avoid `from module import *`

### Formatting

- **Line length**: 100 characters
- **Indentation**: 4 spaces
- **Blank lines**: Two between top-level, one between methods
- **Quotes**: Prefer double quotes

### Type Hints

```python
from __future__ import annotations

def convert_file(
    input_path: str | Path,
    *,
    output_path: str | Path | None = None,
) -> ToolResult:
    ...
```

- Use `str | Path` union syntax
- Type all parameters and returns
- Use `T | None` for optional
- Use `*` for keyword-only args

### Naming Conventions

- **Modules**: `snake_case` (`converter.py`)
- **Classes**: `PascalCase` (`ToolResult`)
- **Functions**: `snake_case` (`convert_file`)
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: `_method_name`

### Docstrings

```python
def convert_file(pdf_path: str) -> Tuple[str, dict]:
    """Convert PDF to Markdown and extract images.
    
    Returns:
        Tuple of (markdown_text, images_dict)
    """
```

- Triple-double-quotes
- Args/Returns for complex functions

### Error Handling

```python
# API: Return ToolResult with success=False
def convert_file(path: Path) -> ToolResult:
    if not path.exists():
        return ToolResult(success=False, error="File not found")
    try:
        return ToolResult(success=True, data={...})
    except Exception as e:
        return ToolResult(success=False, error=str(e))

# CLI: sys.exit(1)
# Internal: Raise exceptions
```

### Data Classes

```python
@dataclass
class ToolResult:
    """Standard return type for NuoYi API."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)
```

### Testing

```python
import pytest

def test_version():
    from nuoyi import __version__
    assert __version__ == "0.2.0"

class TestToolResult:
    def test_success(self):
        r = ToolResult(success=True, data={"md": "# Hi"})
        assert r.success is True
```

- Use `pytest`, `test_` prefix
- Import inside test functions
- Use `tempfile.TemporaryDirectory()` for FS tests

## Project Structure

```
NuoYi/
├── src/nuoyi/
│   ├── __init__.py      # Version, exports
│   ├── __main__.py      # `python -m nuoyi`
│   ├── converter.py     # Converters
│   ├── cli.py           # CLI
│   ├── api.py           # ToolResult, API
│   ├── tools.py         # OpenAI tools
│   ├── utils.py         # Utilities
│   └── gui.py           # PySide6 GUI
├── tests/
│   ├── test_basic.py
│   └── test_unified_api.py
└── pyproject.toml
```

## Configuration (pyproject.toml)

```toml
[tool.ruff]
target-version = "py39"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "C4"]
ignore = ["E501"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
```

## Key Dependencies

- `marker-pdf>=1.0.0` - PDF conversion
- `PyMuPDF>=1.23.0` - PDF operations
- `python-docx>=0.8.11` - DOCX conversion
- `Pillow>=9.0.0` - Image processing
- `PySide6>=6.5.0` - GUI (optional)
- `pytest>=7.0.0` - Testing

## Cursor/Copilot Rules

No Cursor or Copilot rules found in this repository.