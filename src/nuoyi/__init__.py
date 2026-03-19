"""
NuoYi - A simple tool to transform PDF and DOCX to Markdown.

Fully offline conversion using marker-pdf (surya OCR + layout detection).
Supports both CLI and PySide6 GUI interfaces.

Supported acceleration backends:
- CUDA: NVIDIA GPUs (Linux, Windows)
- ROCm: AMD GPUs via HIP (Linux)
- DirectML: AMD/Intel/NVIDIA GPUs on Windows
- MPS: Apple Silicon Metal Performance Shaders (macOS)
- MLX: Apple MLX framework (macOS, experimental)
- Vulkan: Cross-platform GPU acceleration
- OpenVINO: Intel CPU/GPU optimization
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

    # With specific device
    converter = MarkerPDFConverter(device="directml", low_vram=True)
"""

__version__ = "0.2.8"
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
