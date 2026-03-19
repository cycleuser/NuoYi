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
            "expandable_segments:True,garbage_collection_threshold:0.5,max_split_size_mb:128"
        )
        os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
    else:
        os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
        os.environ.setdefault(
            "PYTORCH_CUDA_ALLOC_CONF",
            "expandable_segments:True,garbage_collection_threshold:0.6",
        )


def enable_low_vram_mode():
    """Enable aggressive memory saving mode for low VRAM GPUs."""
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = (
        "expandable_segments:True,garbage_collection_threshold:0.5,max_split_size_mb:64"
    )
    os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.set_per_process_memory_fraction(0.8, 0)
    except Exception:
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
    """Get total and free GPU memory in GB for CUDA. Returns (0, 0) if no GPU."""
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
    """Check if Vulkan is available for GPU acceleration."""
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


def is_openvino_available() -> bool:
    """Check if OpenVINO is available."""
    try:
        import openvino

        return True
    except ImportError:
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


def get_device_info() -> dict:
    """Get detailed information about all available acceleration devices."""
    info = {
        "cuda": {"available": False, "name": None, "memory_gb": 0.0, "count": 0},
        "rocm": {"available": False, "name": None, "memory_gb": 0.0, "count": 0},
        "directml": {"available": False, "name": None, "count": 0},
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
        info["directml"]["available"] = True
        info["directml"]["name"] = get_directml_device_name()
        info["directml"]["count"] = get_directml_device_count()

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
        if is_vulkan_available():
            devices = get_vulkan_devices()
            print(f"[Device] Using Vulkan. Found devices: {devices}")
            return "vulkan"
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
            return "cuda"
        print("[Device] DirectML not available, trying other backends...")
        preferred = "auto"

    if preferred == "rocm":
        if is_rocm_available():
            total, free = get_rocm_memory_info()
            print(f"[Device] AMD ROCm GPU detected: {total:.1f}GB total, {free:.1f}GB free")
            if free >= min_vram_gb:
                print(f"[Device] Using ROCm (sufficient VRAM: {free:.1f}GB >= {min_vram_gb}GB)")
                return "cuda"
            else:
                print(f"[Device] WARNING: Low VRAM ({free:.1f}GB < {min_vram_gb}GB)")
                print("[Device] Forcing ROCm anyway. OOM may occur.")
                return "cuda"
        print("[Device] ROCm not available, trying other backends...")
        preferred = "auto"

    if preferred == "cuda":
        if is_cuda_available():
            total, free = get_gpu_memory_info()
            print(f"[Device] NVIDIA GPU detected: {total:.1f}GB total, {free:.1f}GB free")
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

        if device_info["cuda"]["available"]:
            total, free = get_gpu_memory_info()
            print(f"[Device] NVIDIA CUDA GPU found: {device_info['cuda']['name']} ({total:.1f}GB)")
            if free >= min_vram_gb or total >= min_vram_gb:
                print(f"[Device] Auto-selected: CUDA")
                return "cuda"
            print(f"[Device] Low VRAM ({free:.1f}GB), checking alternatives...")

        if device_info["rocm"]["available"]:
            total, free = get_rocm_memory_info()
            print(f"[Device] AMD ROCm GPU found: {device_info['rocm']['name']} ({total:.1f}GB)")
            if free >= min_vram_gb or total >= min_vram_gb:
                print(f"[Device] Auto-selected: ROCm")
                return "cuda"
            print(f"[Device] Low VRAM ({free:.1f}GB), checking alternatives...")

        if device_info["directml"]["available"]:
            print(f"[Device] DirectML device found: {device_info['directml']['name']}")
            print("[Device] Auto-selected: DirectML (best for AMD on Windows)")
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
    print("\n=== Device Information ===")
    print(f"System: {info['system']['system']} ({info['system']['machine']})")

    if info["cuda"]["available"]:
        print(f"CUDA:      Available - {info['cuda']['name']} ({info['cuda']['memory_gb']:.1f}GB)")
    else:
        print("CUDA:      Not available")

    if info["rocm"]["available"]:
        print(f"ROCm:      Available - {info['rocm']['name']} ({info['rocm']['memory_gb']:.1f}GB)")
    else:
        print("ROCm:      Not available")

    if info["directml"]["available"]:
        print(f"DirectML:  Available - {info['directml']['name']}")
    else:
        print("DirectML:  Not available")

    print(f"MPS:       {'Available' if info['mps']['available'] else 'Not available'}")
    print(f"MLX:       {'Available' if info['mlx']['available'] else 'Not available'}")

    if info["vulkan"]["available"]:
        print(f"Vulkan:    Available - {info['vulkan']['devices']}")
    else:
        print("Vulkan:    Not available")

    print(f"OpenVINO:  {'Available' if info['openvino']['available'] else 'Not available'}")
    print("===========================\n")

    print("Recommendations:")
    if info["system"]["is_windows"]:
        if info["directml"]["available"]:
            print("  - Use --device directml for AMD/Intel GPUs on Windows")
        if info["cuda"]["available"]:
            print("  - Use --device cuda for NVIDIA GPUs")
    elif info["system"]["is_linux"]:
        if info["rocm"]["available"]:
            print("  - Use --device rocm for AMD GPUs")
        if info["cuda"]["available"]:
            print("  - Use --device cuda for NVIDIA GPUs")
    elif info["system"]["is_apple_silicon"]:
        print("  - Use --device mlx for Apple MLX framework")
        print("  - Use --device mps for Apple Metal")


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
