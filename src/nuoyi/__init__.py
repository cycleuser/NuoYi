"""
NuoYi - A simple tool to transform PDF and DOCX to Markdown.

Fully offline conversion using marker-pdf (surya OCR + layout detection).
Supports both CLI and PySide6 GUI interfaces.

Usage:
    # CLI - single file
    nuoyi input.pdf -o output.md

    # CLI - batch directory
    nuoyi ./papers --batch

    # GUI mode
    nuoyi --gui

    # As Python module
    from nuoyi import MarkerPDFConverter, DocxConverter
    
    converter = MarkerPDFConverter()
    text, images = converter.convert_file("input.pdf")
"""

__version__ = "0.2.0"
__author__ = "CycleUser"
__license__ = "GPL-3.0"

from .converter import (
    DocxConverter,
    MarkerPDFConverter,
)
from .utils import (
    clean_markdown,
    clear_gpu_memory,
    get_gpu_memory_info,
    save_images_and_update_markdown,
    select_device,
    setup_memory_optimization,
)

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__license__",
    # Converters
    "MarkerPDFConverter",
    "DocxConverter",
    # Utilities
    "clean_markdown",
    "clear_gpu_memory",
    "get_gpu_memory_info",
    "save_images_and_update_markdown",
    "select_device",
    "setup_memory_optimization",
]
