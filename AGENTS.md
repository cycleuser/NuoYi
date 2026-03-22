# AGENTS.md

Guidelines for agentic coding agents working on the NuoYi codebase.

## Project Overview

NuoYi converts PDF and DOCX documents to Markdown using multiple PDF engines (marker, mineru, docling, pymupdf, pdfplumber, llamaparse, mathpix). Supports CLI, GUI (PySide6), Web (Flask), and Python API interfaces.

**AMD GPU Support:**
- Windows: DirectML (all AMD GPUs including RX580, RX590, RX 6000/7000)
- Linux: ROCm (RDNA GPUs only - RX 5000/6000/7000 series)
- **RX580/RX590 (Polaris) do NOT support ROCm - use DirectML on Windows**

## Build, Test, and Lint Commands

```bash
# Install in development mode
pip install -e ".[dev]"

# Install with GUI/Web support
pip install -e ".[gui]"
pip install -e ".[web]"

# Install with AMD GPU support (Windows) - IMPORTANT: order matters!
pip install -e "."              # First install nuoyi (includes torch)
pip install torch-directml      # Then install DirectML

# Run all tests
pytest

# Run a single test function (IMPORTANT)
pytest tests/test_basic.py::test_version
pytest tests/test_basic.py::TestUtilityFunctions::test_get_gpu_memory_info

# Run specific test file
pytest tests/test_basic.py

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
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from docx import Document
from marker.converters.pdf import PdfConverter

from .utils import clean_markdown
from .converter import DocxConverter
```

- Always include `from __future__ import annotations` for modern type hints
- Order: `__future__`, standard library, third-party, local imports (blank lines between)
- Absolute imports for third-party, relative for local (`.module`)
- Import specific names, avoid `from module import *`

### Formatting

- **Line length**: 100 characters
- **Indentation**: 4 spaces
- **Blank lines**: Two between top-level, one between methods
- **Quotes**: Prefer double quotes
- **Trailing commas**: Use in multi-line structures

### Type Hints

```python
from __future__ import annotations

def convert_file(
    input_path: str | Path,
    *,
    output_path: str | Path | None = None,
    force_ocr: bool = False,
) -> ToolResult:
    ...
```

- Use `str | Path` union syntax (Python 3.10+)
- Type all parameters and returns
- Use `T | None` for optional types
- Use `*` for keyword-only args
- Use `tuple[str, dict]` for tuple return types

### Naming Conventions

- **Modules**: `snake_case` (`converter.py`, `utils.py`)
- **Classes**: `PascalCase` (`ToolResult`, `MarkerPDFConverter`)
- **Functions**: `snake_case` (`convert_file`, `clean_markdown`)
- **Constants**: `UPPER_SNAKE_CASE` (`DEFAULT_LANGS`, `SUPPORTED_ENGINES`)
- **Private methods**: `_method_name`
- **Private module functions**: `_function_name`

### Docstrings

```python
def convert_file(pdf_path: str) -> tuple[str, dict]:
    """Convert PDF to Markdown and extract images.

    Parameters
    ----------
    pdf_path : str
        Path to the PDF file.

    Returns
    -------
    tuple[str, dict]
        Tuple of (markdown_text, images_dict).
    """
```

- Triple-double-quotes with module/class/function description
- Use NumPy-style docstrings for complex functions
- Simple one-liners acceptable for straightforward functions

### Error Handling

```python
# API functions: Return ToolResult with success=False
def convert_file(path: Path) -> ToolResult:
    if not path.exists():
        return ToolResult(success=False, error=f"File not found: {path}")
    try:
        return ToolResult(success=True, data={...})
    except Exception as e:
        return ToolResult(success=False, error=str(e))

# CLI functions: Use sys.exit(1)
def main():
    if not input_path.exists():
        print(f"Error: Path not found: {args.input}")
        sys.exit(1)

# Internal/library functions: Raise exceptions
def _get_module(self):
    if self._module is None:
        try:
            import pymupdf4llm
            self._module = pymupdf4llm
        except ImportError:
            raise ImportError("pip install pymupdf4llm")
    return self._module
```

### Data Classes

```python
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class ToolResult:
    """Standard return type for NuoYi API functions."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }
```

### Testing

```python
import pytest

def test_version():
    """Test that version is accessible."""
    from nuoyi import __version__
    assert __version__ == "0.3.0"

class TestUtilityFunctions:
    """Test utility functions."""

    def test_get_gpu_memory_info(self):
        """Test GPU memory info retrieval."""
        from nuoyi import get_gpu_memory_info
        total, free = get_gpu_memory_info()
        assert isinstance(total, float)
        assert total >= 0
```

- Use `pytest` framework
- Function names: `test_<name>` prefix
- Class names: `Test<Name>` prefix
- Import inside test functions (lazy imports)
- Use `tempfile.TemporaryDirectory()` for filesystem tests
- Group related tests in classes

## Project Structure

```
NuoYi/
├── src/nuoyi/
│   ├── __init__.py      # Version, exports, public API
│   ├── __main__.py      # `python -m nuoyi` entry point
│   ├── api.py           # ToolResult, convert_file, convert_directory
│   ├── cli.py           # Command-line interface
│   ├── converter.py     # PDF/DOCX converters (marker, mineru, docling, etc.)
│   ├── tools.py         # OpenAI function-calling tools
│   ├── utils.py         # Utility functions (device selection, memory, etc.)
│   ├── amd_accel.py     # AMD GPU acceleration module (ROCm, Vulkan detection)
│   ├── directml_backend.py  # DirectML backend for AMD on Windows
│   ├── gui.py           # PySide6 GUI (optional)
│   └── web.py           # Flask web interface (optional)
├── tests/
│   ├── test_basic.py          # Core functionality tests
│   ├── test_unified_api.py    # API tests
│   └── test_recursive.py      # Recursive batch tests
├── AMD_GPU_SETUP.md     # AMD GPU setup guide
└── pyproject.toml
```

## Configuration

```toml
# pyproject.toml excerpt
[tool.ruff]
target-version = "py39"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "C4"]
ignore = ["E501"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

## Key Dependencies

- `marker-pdf>=1.0.0` - PDF conversion (best quality, OCR, GPU)
- `PyMuPDF>=1.23.0` - PDF operations
- `python-docx>=0.8.11` - DOCX conversion
- `Pillow>=9.0.0` - Image processing
- `PySide6>=6.5.0` - GUI (optional, `[gui]` extra)
- `flask>=2.0.0` - Web interface (optional, `[web]` extra)
- `pytest>=7.0.0` - Testing (dev dependency)
- `torch-directml>=0.2.0` - AMD GPU support on Windows (optional, `[amd-windows]` extra)

## Code Patterns

### Converter Pattern

```python
class SomeConverter:
    """Converter description with Type/GPU/OCR/Install info."""

    def __init__(self, device: str = "auto", langs: str = "zh,en"):
        self.device = device
        self._converter = None  # Lazy initialization

    def convert_file(self, pdf_path: str) -> tuple[str, dict]:
        """Convert PDF to markdown. Returns (markdown, images)."""
        ...

    @staticmethod
    def is_available() -> bool:
        """Check if converter dependencies are installed."""
        try:
            import required_module
            return True
        except ImportError:
            return False
```

### CLI Pattern

- Use `argparse` for argument parsing
- Provide `--list-*` flags for introspection (`--list-engines`, `--list-devices`)
- Support both single file and batch directory modes
- Use `sys.exit(1)` for errors, `sys.exit(0)` for help/list commands
- For AMD GPUs on Windows: recommend `--device directml`
- For AMD GPUs on Linux: recommend `--device rocm` (RDNA only)
- For low VRAM: recommend `--low-vram` flag

### AMD GPU Detection Pattern

```python
from nuoyi.utils import is_amd_gpu_available, is_directml_available, is_rocm_available
from nuoyi.directml_backend import is_polaris_gpu

# Check for AMD GPU
if is_amd_gpu_available():
    if is_directml_available():  # Windows
        device_name = get_directml_device_name()
        if is_polaris_gpu(device_name):
            # RX400/500 series - must use DirectML
            print("Polaris GPU detected - use DirectML")
    elif is_rocm_available():  # Linux
        # RDNA GPUs only
        pass
```

## Cursor/Copilot Rules

No Cursor or Copilot rules found in this repository.