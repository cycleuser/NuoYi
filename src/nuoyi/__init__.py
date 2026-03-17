"""
NuoYi - A simple tool to transform PDF and DOCX to Markdown.

Fully offline conversion using marker-pdf (surya OCR + layout detection).
Supports both CLI and PySide6 GUI interfaces.

Supported acceleration backends:
- CUDA: NVIDIA GPUs
- ROCm: AMD GPUs
- MPS: Apple Silicon Metal Performance Shaders
- MLX: Apple MLX framework (experimental)
- CPU: Universal fallback

Usage:
    # CLI - single file
    nuoyi input.pdf -o output.md

    # CLI - batch directory
    nuoyi ./papers --batch

    # CLI - list available devices
    nuoyi --list-devices

    # GUI mode
    nuoyi --gui

    # As Python module
    from nuoyi import MarkerPDFConverter, DocxConverter

    converter = MarkerPDFConverter()
    text, images = converter.convert_file("input.pdf")
"""

__version__ = "0.2.6"
__author__ = "CycleUser"
__license__ = "GPL-3.0"

from .api import (
    ToolResult,
)
from .api import (
    convert_directory as api_convert_directory,
)
from .api import (
    convert_file as api_convert_file,
)
from .converter import (
    DocxConverter,
    MarkerPDFConverter,
)
from .utils import (
    DEFAULT_LANGS,
    SUPPORTED_DEVICES,
    SUPPORTED_LANGUAGES,
    clean_markdown,
    clear_gpu_memory,
    clear_mlx_memory,
    get_device_info,
    get_gpu_memory_info,
    get_rocm_memory_info,
    is_cuda_available,
    is_mlx_available,
    is_mps_available,
    is_rocm_available,
    list_available_devices,
    print_device_info,
    save_images_and_update_markdown,
    select_device,
    setup_memory_optimization,
)

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "MarkerPDFConverter",
    "DocxConverter",
    "ToolResult",
    "api_convert_file",
    "api_convert_directory",
    "SUPPORTED_DEVICES",
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGS",
    "clean_markdown",
    "clear_gpu_memory",
    "clear_mlx_memory",
    "get_device_info",
    "get_gpu_memory_info",
    "get_rocm_memory_info",
    "is_cuda_available",
    "is_mlx_available",
    "is_mps_available",
    "is_rocm_available",
    "list_available_devices",
    "print_device_info",
    "save_images_and_update_markdown",
    "select_device",
    "setup_memory_optimization",
]
