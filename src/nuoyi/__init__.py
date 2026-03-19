"""
NuoYi - A simple tool to transform PDF and DOCX to Markdown.

PDF Conversion Engines:

Local (free, offline):
- marker: Best quality, OCR, ~3GB models, GPU recommended
- mineru: Excellent for Chinese, OCR, ~1.5GB models, GPU optional
- docling: Balanced, OCR, ~1.5GB models, GPU optional
- pymupdf: Fastest, no GPU, no OCR
- pdfplumber: Lightweight, good tables, no GPU, no OCR

Cloud (API key required):
- llamaparse: LlamaIndex cloud, excellent quality
- mathpix: Best for math/scientific documents

Acceleration backends (for marker/mineru/docling):
- CUDA: NVIDIA GPUs
- ROCm: AMD GPUs (Linux)
- DirectML: AMD/Intel GPUs (Windows)
- MPS: Apple Metal (macOS)
- MLX: Apple MLX (macOS)
- CPU: Universal fallback

Usage:
    # CLI - auto select engine
    nuoyi input.pdf -o output.md

    # CLI - use specific engine
    nuoyi input.pdf --engine mineru
    nuoyi input.pdf --engine pymupdf

    # CLI - list available engines
    nuoyi --list-engines

    # GUI mode
    nuoyi --gui

    # Web mode
    nuoyi --web

    # Python module
    from nuoyi import get_converter

    converter = get_converter(engine="mineru", device="mps")
    text, images = converter.convert_file("input.pdf")
"""

__version__ = "0.3.1"
__author__ = "CycleUser"
__license__ = "GPL-3.0"

from .api import (
    ToolResult,
    convert_directory as api_convert_directory,
    convert_file as api_convert_file,
)
from .converter import (
    DocxConverter,
    MarkerPDFConverter,
    get_converter,
    list_available_engines,
)
from .utils import (
    DEFAULT_LANGS,
    SUPPORTED_DEVICES,
    SUPPORTED_LANGUAGES,
    clean_markdown,
    clear_directml_memory,
    clear_gpu_memory,
    clear_mlx_memory,
    enable_low_vram_mode,
    get_device_info,
    get_directml_device_count,
    get_directml_device_name,
    get_gpu_memory_info,
    get_recommended_batch_size,
    get_rocm_memory_info,
    get_system_info,
    get_vulkan_devices,
    is_cuda_available,
    is_directml_available,
    is_mlx_available,
    is_mps_available,
    is_openvino_available,
    is_rocm_available,
    is_vulkan_available,
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
    "get_converter",
    "list_available_engines",
    "ToolResult",
    "api_convert_file",
    "api_convert_directory",
    "SUPPORTED_DEVICES",
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGS",
    "clean_markdown",
    "clear_gpu_memory",
    "clear_mlx_memory",
    "clear_directml_memory",
    "enable_low_vram_mode",
    "get_device_info",
    "get_gpu_memory_info",
    "get_rocm_memory_info",
    "get_directml_device_name",
    "get_directml_device_count",
    "get_vulkan_devices",
    "get_system_info",
    "get_recommended_batch_size",
    "is_cuda_available",
    "is_rocm_available",
    "is_directml_available",
    "is_mps_available",
    "is_mlx_available",
    "is_vulkan_available",
    "is_openvino_available",
    "list_available_devices",
    "print_device_info",
    "save_images_and_update_markdown",
    "select_device",
    "setup_memory_optimization",
]
