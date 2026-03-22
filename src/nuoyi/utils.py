"""
NuoYi - Utility functions for document conversion.

Memory management, device selection, and markdown processing utilities.

Supported acceleration backends:
- CUDA: NVIDIA GPUs (Linux, Windows)
- ROCm: AMD GPUs via HIP (Linux)
- DirectML: AMD/Intel/NVIDIA GPUs on Windows (best for AMD on Windows)
- MPS: Apple Silicon Metal Performance Shaders (macOS)
- MLX: Apple MLX framework (macOS, experimental)
- Vulkan: Cross-platform GPU acceleration (experimental)
- OpenVINO: Intel CPU/GPU acceleration
- CPU: Universal fallback

AMD GPU Support:
- RX 500 series (RX 580, RX 590, etc.)
- RX Vega series
- RX 5000 series
- RX 6000 series
- RX 7000 series
"""

from __future__ import annotations

import gc
import os
import platform
import re
import subprocess
from pathlib import Path

SUPPORTED_LANGUAGES = {
    "zh": "Chinese / 中文",
    "en": "English",
    "ja": "Japanese / 日本語",
    "fr": "French / Français",
    "ru": "Russian / Русский",
    "de": "German / Deutsch",
    "es": "Spanish / Español",
    "pt": "Portuguese / Português",
    "it": "Italian / Italiano",
    "ko": "Korean / 한국어",
}

DEFAULT_LANGS = "zh,en"

SUPPORTED_DEVICES = ["auto", "cpu", "cuda", "rocm", "directml", "mps", "mlx", "vulkan", "openvino"]

SUPPORTED_ENGINES = [
    "auto",
    "marker",
    "mineru",
    "docling",
    "pymupdf",
    "pdfplumber",
    "llamaparse",
    "mathpix",
]

LOW_VRAM_THRESHOLD_GB = 6.0
VERY_LOW_VRAM_THRESHOLD_GB = 4.0


def get_system_info() -> dict:
    """Get system information for device selection."""
    info = {
        "system": platform.system().lower(),
        "machine": platform.machine().lower(),
        "is_apple_silicon": False,
        "is_windows": False,
        "is_linux": False,
    }
    if info["system"] == "darwin":
        info["is_apple_silicon"] = info["machine"] == "arm64"
    info["is_windows"] = info["system"] == "windows"
    info["is_linux"] = info["system"] == "linux"
    return info


def setup_memory_optimization(low_vram: bool = False):
    """Configure PyTorch for better memory management across all backends."""
    if low_vram:
        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = (
            "expandable_segments:True,garbage_collection_threshold:0.5,max_split_size_mb:64"
        )
        os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
    else:
        os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
        os.environ.setdefault(
            "PYTORCH_CUDA_ALLOC_CONF",
            "expandable_segments:True,garbage_collection_threshold:0.6",
        )


def enable_low_vram_mode():
    """Enable aggressive memory saving mode for low VRAM GPUs (4-6GB)."""
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = (
        "expandable_segments:True,garbage_collection_threshold:0.4,max_split_size_mb:32"
    )
    os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["OMP_NUM_THREADS"] = "4"
    os.environ["MKL_NUM_THREADS"] = "4"

    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.set_per_process_memory_fraction(0.75, 0)
            torch.cuda.empty_cache()
    except Exception:
        pass


def enable_very_low_vram_mode():
    """Enable ultra-aggressive memory saving for very low VRAM GPUs (<4GB)."""
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = (
        "expandable_segments:True,garbage_collection_threshold:0.3,max_split_size_mb:16"
    )
    os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["OMP_NUM_THREADS"] = "2"
    os.environ["MKL_NUM_THREADS"] = "2"

    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.set_per_process_memory_fraction(0.6, 0)
            torch.cuda.empty_cache()
    except Exception:
        pass


def optimize_for_cpu_inference():
    """Optimize settings for CPU inference when GPU is not available."""
    cpu_count = os.cpu_count() or 4

    os.environ["OMP_NUM_THREADS"] = str(cpu_count)
    os.environ["MKL_NUM_THREADS"] = str(cpu_count)
    os.environ["OPENBLAS_NUM_THREADS"] = str(cpu_count)
    os.environ["VECLIB_MAXIMUM_THREADS"] = str(cpu_count)
    os.environ["NUMEXPR_NUM_THREADS"] = str(cpu_count)
    os.environ["TOKENIZERS_PARALLELISM"] = "true"

    try:
        import torch

        if hasattr(torch, "set_num_threads"):
            torch.set_num_threads(cpu_count)
        print(f"[CPU] Optimized for {cpu_count} threads")
    except ImportError:
        pass


def get_recommended_batch_size(vram_gb: float) -> int:
    """Get recommended batch size based on available VRAM."""
    if vram_gb < 4:
        return 1
    elif vram_gb < 6:
        return 1
    elif vram_gb < 8:
        return 2
    elif vram_gb < 12:
        return 4
    else:
        return 8


def get_gpu_memory_info() -> tuple[float, float]:
    """Get total and free GPU memory in GB for CUDA/ROCm. Returns (0, 0) if no GPU."""
    try:
        import torch

        if not torch.cuda.is_available():
            return (0.0, 0.0)
        device = torch.cuda.current_device()
        total = torch.cuda.get_device_properties(device).total_memory / (1024**3)
        reserved = torch.cuda.memory_reserved(device) / (1024**3)
        free = total - reserved
        return (total, free)
    except Exception:
        return (0.0, 0.0)


def get_rocm_memory_info() -> tuple[float, float]:
    """Get AMD ROCm GPU memory in GB. Returns (0, 0) if no ROCm GPU."""
    try:
        import torch

        if not torch.cuda.is_available():
            return (0.0, 0.0)
        if not hasattr(torch.version, "hip") or torch.version.hip is None:
            return (0.0, 0.0)
        device = torch.cuda.current_device()
        total = torch.cuda.get_device_properties(device).total_memory / (1024**3)
        reserved = torch.cuda.memory_reserved(device) / (1024**3)
        free = total - reserved
        return (total, free)
    except Exception:
        return (0.0, 0.0)


def get_directml_device_name() -> str | None:
    """Get DirectML device name on Windows."""
    if platform.system().lower() != "windows":
        return None
    try:
        import torch_directml

        return torch_directml.device_name(torch_directml.device())
    except Exception:
        return None


def get_directml_memory_info() -> tuple[float, float]:
    """Get DirectML device memory info. Returns estimated values."""
    try:
        import torch_directml

        device_name = torch_directml.device_name(torch_directml.device())
        if device_name:
            return (_estimate_vram_from_gpu_name(device_name), 0.0)
    except Exception:
        pass
    return (0.0, 0.0)


def _estimate_vram_from_gpu_name(name: str) -> float:
    """Estimate VRAM from GPU name."""
    name_upper = name.upper()

    vram_patterns = {
        "8GB": 8.0, " 8G": 8.0, " 8 GB": 8.0,
        "6GB": 6.0, " 6G": 6.0, " 6 GB": 6.0,
        "12GB": 12.0, " 12G": 12.0,
        "16GB": 16.0, " 16G": 16.0, " 16 GB": 16.0,
        "4GB": 4.0, " 4G": 4.0,
        "20GB": 20.0, "24GB": 24.0,
    }

    for pattern, vram in vram_patterns.items():
        if pattern in name_upper:
            return vram

    known_vram = {
        "RX 580": 8.0, "RX 590": 8.0, "RX 570": 4.0,
        "RX 480": 8.0, "RX 470": 4.0,
        "RX 5600 XT": 6.0, "RX 5700": 8.0, "RX 5700 XT": 8.0,
        "RX 6600": 8.0, "RX 6600 XT": 8.0, "RX 6700 XT": 12.0,
        "RX 6800": 16.0, "RX 6800 XT": 16.0, "RX 6900 XT": 16.0,
        "RX 7600": 8.0, "RX 7700 XT": 12.0, "RX 7800 XT": 16.0,
        "RX 7900 XT": 20.0, "RX 7900 XTX": 24.0,
        "VEGA 56": 8.0, "VEGA 64": 8.0,
        "GTX 1060": 6.0, "GTX 1070": 8.0, "GTX 1080": 8.0,
        "RTX 2060": 6.0, "RTX 2070": 8.0, "RTX 2080": 8.0,
        "RTX 3060": 12.0, "RTX 3070": 8.0, "RTX 3080": 10.0,
        "RTX 4060": 8.0, "RTX 4070": 12.0, "RTX 4080": 16.0,
    }

    for gpu_model, vram in known_vram.items():
        if gpu_model.upper() in name_upper:
            return vram

    return 8.0


def clear_gpu_memory():
    """Release unused GPU memory for all backends."""
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            torch.mps.empty_cache()
        gc.collect()
    except Exception:
        gc.collect()


def clear_mlx_memory():
    """Release MLX memory cache."""
    try:
        import mlx.core as mx

        mx.clear_cache()
    except Exception:
        pass


def clear_directml_memory():
    """Release DirectML memory."""
    try:
        import torch_directml

        del torch_directml
    except Exception:
        pass
    gc.collect()


def clear_all_gpu_memory():
    """Clear memory for all GPU backends."""
    clear_gpu_memory()
    clear_mlx_memory()
    clear_directml_memory()
    gc.collect()


def is_cuda_available() -> bool:
    """Check if NVIDIA CUDA is available."""
    try:
        import torch

        if not torch.cuda.is_available():
            return False
        if hasattr(torch.version, "hip") and torch.version.hip is not None:
            return False
        return True
    except Exception:
        return False


def is_rocm_available() -> bool:
    """Check if AMD ROCm is available (Linux only)."""
    try:
        import torch

        if not torch.cuda.is_available():
            return False
        return hasattr(torch.version, "hip") and torch.version.hip is not None
    except Exception:
        return False


def is_directml_available() -> bool:
    """Check if DirectML is available (Windows only, supports AMD/Intel/NVIDIA)."""
    if platform.system().lower() != "windows":
        return False
    try:
        import torch_directml

        return True
    except ImportError:
        return False


def is_mps_available() -> bool:
    """Check if Apple MPS is available."""
    try:
        import torch

        return (
            hasattr(torch.backends, "mps")
            and torch.backends.mps.is_available()
            and torch.backends.mps.is_built()
        )
    except Exception:
        return False


def is_mlx_available() -> bool:
    """Check if Apple MLX is available."""
    try:
        import mlx.core

        return True
    except ImportError:
        return False


def is_vulkan_available() -> bool:
    """Check if Vulkan is available for GPU acceleration.

    First checks PyTorch Vulkan backend, then falls back to system Vulkan.
    """
    try:
        import torch

        if hasattr(torch.backends, "vulkan"):
            if torch.backends.vulkan.is_available():
                return True
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["vulkaninfo", "--summary"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0 and "deviceName" in result.stdout
    except Exception:
        return False


def is_torch_vulkan_available() -> bool:
    """Check if PyTorch has Vulkan backend compiled in."""
    try:
        import torch

        return (
            hasattr(torch.backends, "vulkan")
            and torch.backends.vulkan.is_available()
        )
    except Exception:
        return False


def get_torch_vulkan_device_count() -> int:
    """Get number of Vulkan devices available in PyTorch."""
    try:
        import torch

        if hasattr(torch.backends, "vulkan") and hasattr(torch.backends.vulkan, "num_vulkan_devices"):
            return torch.backends.vulkan.num_vulkan_devices()
    except Exception:
        pass
    return 0


def is_openvino_available() -> bool:
    """Check if OpenVINO is available."""
    try:
        import openvino

        return True
    except ImportError:
        return False


def is_amd_gpu_available() -> bool:
    """Check if any AMD GPU is available (via ROCm, DirectML, or Vulkan)."""
    if is_rocm_available():
        return True
    if is_directml_available():
        try:
            import torch_directml

            name = torch_directml.device_name(torch_directml.device())
            if name:
                name_upper = name.upper()
                if any(amd_id in name_upper for amd_id in ["AMD", "RADEON", "RX", "VEGA", "NAVI"]):
                    return True
        except Exception:
            pass
    if is_vulkan_available():
        devices = get_vulkan_devices()
        for device in devices:
            if "AMD" in device.upper() or "RADEON" in device.upper():
                return True
    return False


def get_directml_device_count() -> int:
    """Get number of DirectML devices."""
    try:
        import torch_directml

        return torch_directml.device_count()
    except Exception:
        return 0


def get_vulkan_devices() -> list[str]:
    """Get list of Vulkan devices."""
    devices = []
    try:
        result = subprocess.run(
            ["vulkaninfo", "--summary"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "deviceName" in line:
                    name = line.split("=", 1)[-1].strip()
                    devices.append(name)
    except Exception:
        pass
    return devices


def get_amd_gpu_info() -> dict:
    """Get detailed AMD GPU information."""
    info = {
        "available": False,
        "backend": None,
        "name": None,
        "vram_gb": 0.0,
        "driver_version": None,
    }

    if is_rocm_available():
        try:
            import torch

            info["available"] = True
            info["backend"] = "rocm"
            info["name"] = torch.cuda.get_device_name(0)
            total, _ = get_rocm_memory_info()
            info["vram_gb"] = total
            info["driver_version"] = f"HIP {torch.version.hip}"
            return info
        except Exception:
            pass

    if is_directml_available():
        try:
            import torch_directml

            name = torch_directml.device_name(torch_directml.device())
            if name and any(amd_id in name.upper() for amd_id in ["AMD", "RADEON", "RX", "VEGA", "NAVI"]):
                info["available"] = True
                info["backend"] = "directml"
                info["name"] = name
                info["vram_gb"] = _estimate_vram_from_gpu_name(name)
                return info
        except Exception:
            pass

    return info


def get_device_info() -> dict:
    """Get detailed information about all available acceleration devices."""
    info = {
        "cuda": {"available": False, "name": None, "memory_gb": 0.0, "count": 0},
        "rocm": {"available": False, "name": None, "memory_gb": 0.0, "count": 0},
        "directml": {"available": False, "name": None, "count": 0, "is_amd": False},
        "amd": get_amd_gpu_info(),
        "mps": {"available": False},
        "mlx": {"available": False},
        "vulkan": {"available": False, "devices": []},
        "openvino": {"available": False},
        "cpu": {"available": True},
        "system": get_system_info(),
    }

    if is_cuda_available():
        try:
            import torch

            info["cuda"]["available"] = True
            info["cuda"]["name"] = torch.cuda.get_device_name(0)
            info["cuda"]["count"] = torch.cuda.device_count()
            total, _ = get_gpu_memory_info()
            info["cuda"]["memory_gb"] = total
        except Exception:
            pass

    if is_rocm_available():
        try:
            import torch

            info["rocm"]["available"] = True
            info["rocm"]["name"] = torch.cuda.get_device_name(0)
            info["rocm"]["count"] = torch.cuda.device_count()
            total, _ = get_rocm_memory_info()
            info["rocm"]["memory_gb"] = total
        except Exception:
            pass

    if is_directml_available():
        try:
            import torch_directml

            name = torch_directml.device_name(torch_directml.device())
            info["directml"]["available"] = True
            info["directml"]["name"] = name
            info["directml"]["count"] = torch_directml.device_count()
            if name:
                name_upper = name.upper()
                info["directml"]["is_amd"] = any(
                    amd_id in name_upper for amd_id in ["AMD", "RADEON", "RX", "VEGA", "NAVI"]
                )
        except Exception:
            pass

    info["mps"]["available"] = is_mps_available()
    info["mlx"]["available"] = is_mlx_available()

    if is_vulkan_available():
        info["vulkan"]["available"] = True
        info["vulkan"]["devices"] = get_vulkan_devices()

    info["openvino"]["available"] = is_openvino_available()

    return info


def select_device(preferred: str = "auto", min_vram_gb: float = 6.0) -> str:
    """
    Select the best device for running marker-pdf.

    Args:
        preferred: Device preference - "auto" or specific device name
        min_vram_gb: Minimum VRAM required to use GPU (default 6GB)

    Returns:
        Device string for torch/marker-pdf
    """
    system_info = get_system_info()

    if preferred == "cpu":
        print("[Device] Using CPU as requested.")
        return "cpu"

    if preferred == "openvino":
        if is_openvino_available():
            print("[Device] Using OpenVINO (Intel optimization).")
            return "openvino"
        print("[Device] OpenVINO not available, trying other backends...")
        preferred = "auto"

    if preferred == "vulkan":
        vulkan_devices = get_vulkan_devices()
        torch_vulkan = is_torch_vulkan_available()

        if torch_vulkan:
            device_count = get_torch_vulkan_device_count()
            print(f"[Device] PyTorch Vulkan backend available!")
            print(f"[Device] Vulkan devices: {vulkan_devices}")
            print(f"[Device] Device count: {device_count}")

            amd_devices = [d for d in vulkan_devices if "AMD" in d.upper() or "RADEON" in d.upper() or "RX" in d.upper()]
            if amd_devices:
                print(f"[Device] AMD GPU(s) detected: {amd_devices}")
                print(f"[Device] Using Vulkan for AMD GPU acceleration")

            os.environ["TORCH_DEVICE"] = "vulkan"
            return "vulkan"

        if is_vulkan_available():
            print(f"[Device] System Vulkan available: {vulkan_devices}")
            print(f"[Device] PyTorch Vulkan backend NOT compiled in")
            print(f"[Device]")
            print(f"[Device] To use Vulkan with PyTorch, you need to compile PyTorch with Vulkan support:")
            print(f"[Device]   1. Run: scripts\\build_vulkan_pytorch.ps1")
            print(f"[Device]   Or see: BUILD_VULKAN_PYTORCH.md")
            print(f"[Device]")
            print(f"[Device] Falling back to CPU...")

            optimize_for_cpu_inference()
            return "cpu"

        print("[Device] Vulkan not available, trying other backends...")
        preferred = "auto"

    if preferred == "mlx":
        if is_mlx_available():
            print("[Device] Using MLX (Apple Silicon MLX framework).")
            return "mlx"
        print("[Device] MLX not available, trying other backends...")
        preferred = "auto"

    if preferred == "mps":
        if is_mps_available():
            print("[Device] Using MPS (Apple Silicon Metal).")
            return "mps"
        print("[Device] MPS not available, trying other backends...")
        preferred = "auto"

    if preferred == "directml":
        if is_directml_available():
            device_name = get_directml_device_name()
            print(f"[Device] Using DirectML: {device_name}")

            try:
                from .directml_backend import is_polaris_gpu, get_polaris_vram, configure_marker_for_directml

                if is_polaris_gpu(device_name):
                    vram = get_polaris_vram(device_name)
                    print(f"[Device] Polaris GPU detected (RX400/500 series)")
                    print(f"[Device] VRAM: {vram:.1f}GB - This GPU does NOT support ROCm")
                    print(f"[Device] DirectML is the ONLY GPU option on Windows")

                    if vram <= LOW_VRAM_THRESHOLD_GB:
                        print(f"[Device] Low VRAM mode enabled for {vram:.1f}GB")
                        enable_low_vram_mode()

                    config = configure_marker_for_directml(low_vram=(vram <= LOW_VRAM_THRESHOLD_GB))
                    if config.get("torch_patched"):
                        print(f"[Device] PyTorch patched for DirectML successfully")
                else:
                    total_vram = _estimate_vram_from_gpu_name(device_name or "")
                    if total_vram <= LOW_VRAM_THRESHOLD_GB:
                        print(f"[Device] Low VRAM detected ({total_vram:.1f}GB), enabling optimizations...")
                        enable_low_vram_mode()
                    configure_marker_for_directml(low_vram=(total_vram <= LOW_VRAM_THRESHOLD_GB))

            except ImportError:
                total_vram = _estimate_vram_from_gpu_name(device_name or "")
                if total_vram <= LOW_VRAM_THRESHOLD_GB:
                    enable_low_vram_mode()
                os.environ["TORCH_DEVICE"] = "cuda"

            return "cuda"
        print("[Device] DirectML not available, trying other backends...")
        print("[Device] Install with: pip install torch-directml")
        preferred = "auto"

    if preferred == "rocm":
        if is_rocm_available():
            total, free = get_rocm_memory_info()
            print(f"[Device] AMD ROCm GPU detected: {total:.1f}GB total, {free:.1f}GB free")

            _setup_rocm_env()

            if total <= LOW_VRAM_THRESHOLD_GB:
                print(f"[Device] Low VRAM ({total:.1f}GB), enabling optimizations...")
                enable_low_vram_mode()
                return "cuda"

            if free >= min_vram_gb:
                print(f"[Device] Using ROCm (sufficient VRAM: {free:.1f}GB >= {min_vram_gb}GB)")
                return "cuda"
            else:
                print(f"[Device] WARNING: Low VRAM ({free:.1f}GB < {min_vram_gb}GB)")
                print("[Device] Enabling low VRAM optimizations...")
                enable_low_vram_mode()
                return "cuda"
        print("[Device] ROCm not available, trying other backends...")
        preferred = "auto"

    if preferred == "cuda":
        if is_cuda_available():
            total, free = get_gpu_memory_info()
            print(f"[Device] NVIDIA GPU detected: {total:.1f}GB total, {free:.1f}GB free")

            if total <= LOW_VRAM_THRESHOLD_GB:
                print(f"[Device] Low VRAM ({total:.1f}GB), enabling optimizations...")
                enable_low_vram_mode()

            if free >= min_vram_gb:
                print(f"[Device] Using CUDA (sufficient VRAM: {free:.1f}GB >= {min_vram_gb}GB)")
                return "cuda"
            else:
                print(f"[Device] WARNING: Low VRAM ({free:.1f}GB < {min_vram_gb}GB)")
                print("[Device] Forcing CUDA anyway. OOM may occur.")
                return "cuda"
        print("[Device] CUDA not available, trying other backends...")
        preferred = "auto"

    if preferred == "auto":
        device_info = get_device_info()

        if device_info["rocm"]["available"]:
            total, free = get_rocm_memory_info()
            print(f"[Device] AMD ROCm GPU found: {device_info['rocm']['name']} ({total:.1f}GB)")
            _setup_rocm_env()

            if total <= LOW_VRAM_THRESHOLD_GB:
                enable_low_vram_mode()

            print(f"[Device] Auto-selected: ROCm (AMD)")
            return "cuda"

        if device_info["cuda"]["available"]:
            total, free = get_gpu_memory_info()
            print(f"[Device] NVIDIA CUDA GPU found: {device_info['cuda']['name']} ({total:.1f}GB)")

            if total <= LOW_VRAM_THRESHOLD_GB:
                enable_low_vram_mode()

            print(f"[Device] Auto-selected: CUDA")
            return "cuda"

        if device_info["directml"]["available"]:
            print(f"[Device] DirectML device found: {device_info['directml']['name']}")
            is_amd = device_info['directml'].get('is_amd', False)

            if is_amd:
                print("[Device] Auto-selected: DirectML (AMD GPU)")
            else:
                print("[Device] Auto-selected: DirectML")

            vram = _estimate_vram_from_gpu_name(device_info['directml']['name'] or "")
            if vram <= LOW_VRAM_THRESHOLD_GB:
                enable_low_vram_mode()

            _setup_directml_env()
            return "cuda"

        if device_info["mlx"]["available"]:
            print("[Device] Apple MLX framework available.")
            print("[Device] Auto-selected: MLX (Apple Silicon)")
            return "mlx"

        if device_info["mps"]["available"]:
            print("[Device] Apple MPS available.")
            print("[Device] Auto-selected: MPS (Apple Silicon Metal)")
            return "mps"

        if device_info["openvino"]["available"]:
            print("[Device] OpenVINO available.")
            print("[Device] Auto-selected: OpenVINO (Intel optimization)")
            return "openvino"

    print("[Device] No GPU acceleration available, using CPU.")
    return "cpu"


def _setup_rocm_env():
    """Set up environment variables for ROCm."""
    os.environ["HSA_ENABLE_SDMA"] = "0"

    if "HSA_OVERRIDE_GFX_VERSION" not in os.environ:
        os.environ["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0"

    os.environ["ROCM_PATH"] = os.environ.get("ROCM_PATH", "/opt/rocm")


def get_directml_info() -> dict:
    """Get detailed DirectML information."""
    info = {
        "available": False,
        "device_name": None,
        "is_polaris": False,
        "vram_gb": 0.0,
        "supports_rocm": False,
        "requires_directml": False,
    }

    if platform.system().lower() != "windows":
        info["note"] = "DirectML is only for Windows. On Linux, use ROCm or CPU."
        return info

    try:
        import torch_directml

        device = torch_directml.device()
        name = torch_directml.device_name(device)

        info["available"] = True
        info["device_name"] = name

        try:
            from .directml_backend import is_polaris_gpu, get_polaris_vram

            info["is_polaris"] = is_polaris_gpu(name)
            if info["is_polaris"]:
                info["vram_gb"] = get_polaris_vram(name)
                info["supports_rocm"] = False
                info["requires_directml"] = True
            else:
                info["vram_gb"] = _estimate_vram_from_gpu_name(name)
        except ImportError:
            info["vram_gb"] = _estimate_vram_from_gpu_name(name)

        return info

    except ImportError:
        info["error"] = "torch-directml not installed. Run: pip install torch-directml"
        return info
    except Exception as e:
        info["error"] = str(e)
        return info


def list_available_devices() -> list[str]:
    """List all available acceleration devices."""
    available = ["cpu"]
    device_info = get_device_info()

    if device_info["cuda"]["available"]:
        available.append("cuda")
    if device_info["rocm"]["available"]:
        available.append("rocm")
    if device_info["directml"]["available"]:
        available.append("directml")
    if device_info["mps"]["available"]:
        available.append("mps")
    if device_info["mlx"]["available"]:
        available.append("mlx")
    if device_info["vulkan"]["available"]:
        available.append("vulkan")
    if device_info["openvino"]["available"]:
        available.append("openvino")

    return available


def print_device_info():
    """Print detailed device information for debugging."""
    info = get_device_info()
    print("\n" + "=" * 60)
    print("Device Information")
    print("=" * 60)
    print(f"System: {info['system']['system']} ({info['system']['machine']})")

    if info["cuda"]["available"]:
        print(f"CUDA:      [OK] {info['cuda']['name']} ({info['cuda']['memory_gb']:.1f}GB)")
    else:
        print("CUDA:      [--] Not available")

    if info["rocm"]["available"]:
        print(f"ROCm:      [OK] {info['rocm']['name']} ({info['rocm']['memory_gb']:.1f}GB)")
    else:
        print("ROCm:      [--] Not available")

    if info["directml"]["available"]:
        is_amd = info['directml'].get('is_amd', False)
        amd_marker = " (AMD)" if is_amd else ""
        print(f"DirectML:  [OK] {info['directml']['name']}{amd_marker}")
    else:
        print("DirectML:  [--] Not available")

    print(f"MPS:       [{'OK' if info['mps']['available'] else '--'}] {'Available' if info['mps']['available'] else 'Not available'}")
    print(f"MLX:       [{'OK' if info['mlx']['available'] else '--'}] {'Available' if info['mlx']['available'] else 'Not available'}")

    if info["vulkan"]["available"]:
        print(f"Vulkan:    [OK] {info['vulkan']['devices']}")
    else:
        print("Vulkan:    [--] Not available")

    print(f"OpenVINO:  [{'OK' if info['openvino']['available'] else '--'}] {'Available' if info['openvino']['available'] else 'Not available'}")
    print("=" * 60)

    print("\nRecommendations:")
    if info["system"]["is_windows"]:
        if info["directml"]["available"]:
            is_amd = info['directml'].get('is_amd', False)
            if is_amd:
                print("  - Use --device directml for AMD GPU (RECOMMENDED)")
                print("  - For RX580/RX590 with 8GB VRAM: marker-pdf should work well")
                print("  - For 6GB VRAM: use --low-vram flag")
            else:
                print("  - Use --device directml for GPU acceleration")
        if info["cuda"]["available"]:
            print("  - Use --device cuda for NVIDIA GPUs")
    elif info["system"]["is_linux"]:
        if info["rocm"]["available"]:
            print("  - Use --device rocm for AMD GPUs (RECOMMENDED)")
            print("  - For RX580/RX590 with 8GB VRAM: marker-pdf should work well")
            print("  - For 6GB VRAM: use --low-vram flag")
        if info["cuda"]["available"]:
            print("  - Use --device cuda for NVIDIA GPUs")
    elif info["system"]["is_apple_silicon"]:
        print("  - Use --device mlx for Apple MLX framework")
        print("  - Use --device mps for Apple Metal")

    print("\nLow VRAM Tips (4-6GB):")
    print("  - Use --low-vram flag")
    print("  - Close other GPU applications")
    print("  - Consider using pymupdf or pdfplumber for simpler documents")
    print("")


def clean_markdown(text: str) -> str:
    """Clean up marker-pdf output with fixes for common issues."""
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    text = re.sub(r"\[([^\]]+)\]\(#page-\d+(?:-\d+)*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(#_?bookmark\d+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(\)", r"\1", text)
    text = re.sub(
        r"(?<![(\w])"
        r"([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)?"
        r"(?:\s+et\s+al\.)?"
        r",?\s*\d{4}[a-z]?"
        r"(?:\s*;\s*"
        r"[A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)?(?:\s+et\s+al\.)?"
        r",?\s*\d{4}[a-z]?)*"
        r")\)",
        r"(\1)",
        text,
    )
    text = re.sub(r"\(\(([^)]+)\)\)", r"(\1)", text)
    return text.strip()


def save_images_and_update_markdown(
    markdown_text: str, images: dict, output_dir: Path, images_subdir: str = "images"
) -> str:
    """Save extracted images and update markdown references."""
    if not images:
        return markdown_text

    images_dir = output_dir / images_subdir
    images_dir.mkdir(parents=True, exist_ok=True)

    saved_count = 0

    for img_name, img_data in images.items():
        try:
            img_path = images_dir / img_name

            if hasattr(img_data, "save"):
                img_data.save(str(img_path))
                saved_count += 1
            elif isinstance(img_data, bytes):
                with open(img_path, "wb") as f:
                    f.write(img_data)
                saved_count += 1
            elif isinstance(img_data, str):
                import base64

                try:
                    img_bytes = base64.b64decode(img_data)
                    with open(img_path, "wb") as f:
                        f.write(img_bytes)
                    saved_count += 1
                except Exception:
                    print(f"  [Warning] Could not decode base64 image: {img_name}")
            else:
                print(f"  [Warning] Unknown image format for: {img_name} ({type(img_data)})")

        except Exception as e:
            print(f"  [Warning] Failed to save image {img_name}: {e}")

    if saved_count > 0:
        print(f"  Saved {saved_count} images to {images_subdir}/")

    updated_text = markdown_text

    for img_name in images.keys():
        old_ref = f"]({img_name})"
        new_ref = f"]({images_subdir}/{img_name})"
        if old_ref in updated_text:
            updated_text = updated_text.replace(old_ref, new_ref)

        old_ref = f"](./{img_name})"
        new_ref = f"]({images_subdir}/{img_name})"
        if old_ref in updated_text:
            updated_text = updated_text.replace(old_ref, new_ref)

        base_name = Path(img_name).name
        if base_name != img_name:
            old_ref = f"]({img_name})"
            new_ref = f"]({images_subdir}/{base_name})"
            if old_ref in updated_text:
                updated_text = updated_text.replace(old_ref, new_ref)

    return updated_text


def find_pdf_files(directory: Path, recursive: bool = False) -> list[Path]:
    """Find all PDF files in a directory."""
    pattern = "**/*.pdf" if recursive else "*.pdf"
    return sorted(directory.glob(pattern))


def find_docx_files(directory: Path, recursive: bool = False) -> list[Path]:
    """Find all DOCX files in a directory."""
    pattern = "**/*.docx" if recursive else "*.docx"
    return sorted(directory.glob(pattern))


def find_documents(
    directory: Path, recursive: bool = False, extensions: tuple[str, ...] = (".pdf", ".docx")
) -> list[Path]:
    """Find all PDF and DOCX files in a directory."""
    files = []
    if recursive:
        for ext in extensions:
            files.extend(directory.glob(f"**/*{ext}"))
    else:
        for ext in extensions:
            files.extend(directory.glob(f"*{ext}"))
    return sorted(files)


def scan_directory(directory: Path, recursive: bool = False) -> dict:
    """Scan a directory for PDF and DOCX files."""
    pdf_files = find_pdf_files(directory, recursive)
    docx_files = find_docx_files(directory, recursive)

    result = {
        "pdf_files": pdf_files,
        "docx_files": docx_files,
        "total_files": len(pdf_files) + len(docx_files),
        "subdirs": [],
    }

    if recursive:
        for ext in (".pdf", ".docx"):
            for file in directory.glob(f"**/*{ext}"):
                subdir = file.parent.relative_to(directory)
                if subdir != Path(".") and str(subdir) not in result["subdirs"]:
                    result["subdirs"].append(str(subdir))
        result["subdirs"].sort()

    return result


def get_output_path(
    input_file: Path,
    input_dir: Path,
    output_dir: Path,
    recursive: bool = False,
    suffix: str = "_md",
) -> Path:
    """Calculate output path preserving directory structure."""
    if not recursive:
        return output_dir / f"{input_file.stem}.md"

    try:
        rel_path = input_file.relative_to(input_dir)
    except ValueError:
        return output_dir / f"{input_file.stem}.md"

    output_parts = []
    for part in rel_path.parts[:-1]:
        output_parts.append(f"{part}{suffix}")

    output_parts.append(f"{input_file.stem}.md")

    return output_dir / Path(*output_parts)


def create_output_directories(
    files: list[Path],
    input_dir: Path,
    output_dir: Path,
    recursive: bool = False,
    suffix: str = "_md",
):
    """Create output directories preserving input structure."""
    if not recursive:
        output_dir.mkdir(parents=True, exist_ok=True)
        return

    for file in files:
        output_path = get_output_path(file, input_dir, output_dir, recursive, suffix)
        output_path.parent.mkdir(parents=True, exist_ok=True)