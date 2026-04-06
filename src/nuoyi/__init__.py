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

AMD GPU Support:
- Windows: Use --device directml (AMD Radeon GPUs)
  * RX580, RX590, RX 6000/7000 series
  * Polaris GPUs (RX 400/500) require DirectML
- Linux: Use --device rocm (AMD Radeon GPUs)
  * Only newer AMD GPUs (RDNA, CDNA)
  * RX580/RX590 NOT supported on ROCm
- Low VRAM: Use --low-vram for 4-6GB GPUs

Acceleration backends:
- CUDA: NVIDIA GPUs
- ROCm: AMD GPUs (Linux only, newer GPUs)
- DirectML: AMD/Intel GPUs (Windows only)
- MPS: Apple Metal (macOS)
- MLX: Apple MLX (macOS)
- CPU: Universal fallback

Usage:
    # CLI - auto select engine
    nuoyi input.pdf -o output.md

    # CLI - AMD GPU on Windows (RX580, RX590, etc.)
    nuoyi input.pdf --device directml

    # CLI - AMD GPU on Linux (RDNA GPUs only)
    nuoyi input.pdf --device rocm

    # CLI - low VRAM mode for 6GB GPUs
    nuoyi input.pdf --device directml --low-vram

    # CLI - list available engines
    nuoyi --list-engines

    # CLI - show AMD GPU info
    nuoyi --amd-info

    # GUI mode
    nuoyi --gui

    # Web mode
    nuoyi --web

    # Python module
    from nuoyi import get_converter

    converter = get_converter(engine="marker", device="directml")
    text, images = converter.convert_file("input.pdf")
"""

__version__ = "0.4.11"
__author__ = "CycleUser"
__license__ = "GPL-3.0"

from .api import (
    ToolResult,
    clear_converter_cache,
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
    LOW_VRAM_THRESHOLD_GB,
    SUPPORTED_DEVICES,
    SUPPORTED_LANGUAGES,
    clean_markdown,
    clear_directml_memory,
    clear_gpu_memory,
    clear_mlx_memory,
    clear_all_gpu_memory,
    enable_low_vram_mode,
    enable_very_low_vram_mode,
    optimize_for_cpu_inference,
    get_device_info,
    get_directml_device_count,
    get_directml_device_name,
    get_gpu_memory_info,
    get_recommended_batch_size,
    get_rocm_memory_info,
    get_system_info,
    get_vulkan_devices,
    is_amd_gpu_available,
    is_cuda_available,
    is_directml_available,
    is_mlx_available,
    is_mps_available,
    is_openvino_available,
    is_rocm_available,
    is_vulkan_available,
    is_torch_vulkan_available,
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
    "clear_converter_cache",
    "SUPPORTED_DEVICES",
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGS",
    "LOW_VRAM_THRESHOLD_GB",
    "clean_markdown",
    "clear_gpu_memory",
    "clear_mlx_memory",
    "clear_directml_memory",
    "clear_all_gpu_memory",
    "enable_low_vram_mode",
    "enable_very_low_vram_mode",
    "optimize_for_cpu_inference",
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
    "is_torch_vulkan_available",
    "is_openvino_available",
    "is_amd_gpu_available",
    "list_available_devices",
    "print_device_info",
    "save_images_and_update_markdown",
    "select_device",
    "setup_memory_optimization",
]


def get_amd_info():
    """Get detailed AMD GPU information."""
    try:
        from .amd_accel import get_amd_device_report

        return get_amd_device_report()
    except ImportError:
        return "AMD acceleration module not available."


def setup_for_amd_gpu(device: str = "auto", low_vram: bool = False):
    """
    Set up NuoYi for optimal AMD GPU usage.

    Args:
        device: Device preference ("auto", "directml", "rocm", "cuda", "cpu")
        low_vram: Enable low VRAM mode for 4-6GB GPUs

    Returns:
        Configuration dict with device info
    """
    try:
        from .amd_accel import setup_marker_for_amd

        return setup_marker_for_amd(device=device, low_vram=low_vram)
    except ImportError:
        config = {
            "device": select_device(device),
            "low_vram": low_vram,
            "amd_gpu": None,
            "backend": "unknown",
        }
        if low_vram:
            enable_low_vram_mode()
        return config
