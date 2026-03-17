"""
NuoYi - Utility functions for document conversion.

Memory management, device selection, and markdown processing utilities.

Supported acceleration backends:
- CUDA: NVIDIA GPUs
- ROCm: AMD GPUs (via HIP)
- MPS: Apple Silicon (Metal Performance Shaders)
- MLX: Apple MLX framework (experimental)
- CPU: Fallback for all platforms
"""

from __future__ import annotations

import gc
import os
import platform
import re
from pathlib import Path
from typing import Tuple

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

SUPPORTED_DEVICES = ["auto", "cpu", "cuda", "rocm", "mps", "mlx"]


def get_system_info() -> dict:
    """Get system information for device selection."""
    info = {
        "system": platform.system().lower(),
        "machine": platform.machine().lower(),
        "is_apple_silicon": False,
    }
    if info["system"] == "darwin":
        info["is_apple_silicon"] = info["machine"] == "arm64"
    return info


def setup_memory_optimization():
    """Configure PyTorch for better memory management across all backends."""
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    os.environ.setdefault(
        "PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True,garbage_collection_threshold:0.6"
    )


def get_gpu_memory_info() -> Tuple[float, float]:
    """Get total and free GPU memory in GB. Returns (0, 0) if no GPU available."""
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


def get_rocm_memory_info() -> Tuple[float, float]:
    """Get AMD ROCm GPU memory in GB. Returns (0, 0) if no ROCm GPU available."""
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
    """Check if AMD ROCm is available."""
    try:
        import torch

        if not torch.cuda.is_available():
            return False
        return hasattr(torch.version, "hip") and torch.version.hip is not None
    except Exception:
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
        import mlx.core as mx

        return True
    except ImportError:
        return False


def get_device_info() -> dict:
    """Get detailed information about available devices."""
    info = {
        "cuda": {"available": False, "name": None, "memory_gb": 0.0},
        "rocm": {"available": False, "name": None, "memory_gb": 0.0},
        "mps": {"available": False},
        "mlx": {"available": False},
        "cpu": {"available": True},
        "system": get_system_info(),
    }

    if is_cuda_available():
        try:
            import torch

            info["cuda"]["available"] = True
            info["cuda"]["name"] = torch.cuda.get_device_name(0)
            total, _ = get_gpu_memory_info()
            info["cuda"]["memory_gb"] = total
        except Exception:
            pass

    if is_rocm_available():
        try:
            import torch

            info["rocm"]["available"] = True
            info["rocm"]["name"] = torch.cuda.get_device_name(0)
            total, _ = get_rocm_memory_info()
            info["rocm"]["memory_gb"] = total
        except Exception:
            pass

    info["mps"]["available"] = is_mps_available()
    info["mlx"]["available"] = is_mlx_available()

    return info


def select_device(preferred: str = "auto", min_vram_gb: float = 6.0) -> str:
    """
    Select the best device for running marker-pdf.

    Args:
        preferred: Device preference - "auto", "cpu", "cuda", "rocm", "mps", or "mlx"
        min_vram_gb: Minimum VRAM required to use GPU (default 6GB)

    Returns:
        Device string: "cuda", "rocm", "mps", "mlx", or "cpu"
    """
    system_info = get_system_info()

    if preferred == "cpu":
        print("[Device] Forcing CPU mode as requested.")
        return "cpu"

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

    if preferred == "rocm":
        if is_rocm_available():
            total, free = get_rocm_memory_info()
            print(f"[Device] AMD ROCm GPU detected: {total:.1f}GB total, {free:.1f}GB free")
            if free >= min_vram_gb:
                print(f"[Device] Using ROCm (sufficient VRAM: {free:.1f}GB >= {min_vram_gb}GB)")
                return "cuda"
            else:
                print(f"[Device] WARNING: Low VRAM ({free:.1f}GB < {min_vram_gb}GB required)")
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
                print(f"[Device] WARNING: Low VRAM ({free:.1f}GB < {min_vram_gb}GB required)")
                print("[Device] Forcing CUDA anyway. OOM may occur.")
                return "cuda"
        print("[Device] CUDA not available, trying other backends...")
        preferred = "auto"

    if preferred == "auto":
        device_info = get_device_info()

        if device_info["cuda"]["available"]:
            total, free = get_gpu_memory_info()
            print(f"[Device] NVIDIA CUDA GPU found: {device_info['cuda']['name']} ({total:.1f}GB)")
            if free >= min_vram_gb:
                print(f"[Device] Auto-selected: CUDA (sufficient VRAM: {free:.1f}GB)")
                return "cuda"
            else:
                print(f"[Device] Low VRAM ({free:.1f}GB), checking alternatives...")

        if device_info["rocm"]["available"]:
            total, free = get_rocm_memory_info()
            print(f"[Device] AMD ROCm GPU found: {device_info['rocm']['name']} ({total:.1f}GB)")
            if free >= min_vram_gb:
                print(f"[Device] Auto-selected: ROCm (sufficient VRAM: {free:.1f}GB)")
                return "cuda"
            else:
                print(f"[Device] Low VRAM ({free:.1f}GB), checking alternatives...")

        if device_info["mlx"]["available"]:
            print("[Device] Apple MLX framework available.")
            print("[Device] Auto-selected: MLX (Apple Silicon)")
            return "mlx"

        if device_info["mps"]["available"]:
            print("[Device] Apple MPS available.")
            print("[Device] Auto-selected: MPS (Apple Silicon Metal)")
            return "mps"

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
    if device_info["mps"]["available"]:
        available.append("mps")
    if device_info["mlx"]["available"]:
        available.append("mlx")

    return available


def print_device_info():
    """Print detailed device information for debugging."""
    info = get_device_info()
    print("\n=== Device Information ===")
    print(f"System: {info['system']['system']} ({info['system']['machine']})")

    if info["cuda"]["available"]:
        print(f"CUDA:   Available - {info['cuda']['name']} ({info['cuda']['memory_gb']:.1f}GB)")
    else:
        print("CUDA:   Not available")

    if info["rocm"]["available"]:
        print(f"ROCm:   Available - {info['rocm']['name']} ({info['rocm']['memory_gb']:.1f}GB)")
    else:
        print("ROCm:   Not available")

    print(f"MPS:    {'Available' if info['mps']['available'] else 'Not available'}")
    print(f"MLX:    {'Available' if info['mlx']['available'] else 'Not available'}")
    print("===========================\n")


def clean_markdown(text: str) -> str:
    """Clean up marker-pdf output with fixes for common issues.

    Handles:
    - Excessive newlines
    - Windows line endings
    - Broken citation links (e.g., [Author](#page-X-Y) -> Author)
    - Invalid internal page anchors that cause KaTeX parse errors
    """
    # Fix Windows line endings
    text = text.replace("\r\n", "\n")

    # Reduce excessive newlines
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    # Fix broken citation/reference links from marker-pdf
    # Pattern: [text](#page-X-Y) or [text](#page-X-Y-Z) -> text
    # These internal page anchors are invalid in converted markdown
    # and cause KaTeX parse errors in some renderers
    text = re.sub(r"\[([^\]]+)\]\(#page-\d+(?:-\d+)*\)", r"\1", text)

    # Also handle other common internal anchor patterns
    # [text](#_bookmark123) -> text
    text = re.sub(r"\[([^\]]+)\]\(#_?bookmark\d+\)", r"\1", text)

    # Remove empty link targets: [text]() -> text
    text = re.sub(r"\[([^\]]+)\]\(\)", r"\1", text)

    # Fix citation patterns that lost their opening parenthesis
    # Match: "Author, Year)" or "Author and Author, Year)" or "Author et al., Year)"
    # ending with ) but missing opening (
    # Negative lookbehind ensures we don't match already-parenthesized citations
    text = re.sub(
        r"(?<![(\w])"  # not preceded by ( or word char
        r"([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)?"  # Author or Author and Author
        r"(?:\s+et\s+al\.)?"  # optional et al.
        r",?\s*\d{4}[a-z]?"  # , Year
        r"(?:\s*;\s*"  # ; separator
        r"[A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)?(?:\s+et\s+al\.)?"  # more authors
        r",?\s*\d{4}[a-z]?)*"  # more years
        r")\)",  # closing )
        r"(\1)",
        text,
    )

    # Clean up double parentheses that might result from over-correction
    text = re.sub(r"\(\(([^)]+)\)\)", r"(\1)", text)

    return text.strip()


def save_images_and_update_markdown(
    markdown_text: str, images: dict, output_dir: Path, images_subdir: str = "images"
) -> str:
    """Save extracted images and update markdown references.

    Args:
        markdown_text: The markdown content with image references
        images: Dict mapping image filenames to image data (PIL Image or bytes)
        output_dir: Directory where the markdown file will be saved
        images_subdir: Subdirectory name for images (default: "images")

    Returns:
        Updated markdown text with corrected image paths
    """
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


def find_pdf_files(
    directory: Path,
    recursive: bool = False,
) -> list[Path]:
    """Find all PDF files in a directory.

    Args:
        directory: Directory to search
        recursive: If True, search subdirectories recursively

    Returns:
        List of PDF file paths, sorted
    """
    pattern = "**/*.pdf" if recursive else "*.pdf"
    return sorted(directory.glob(pattern))


def find_docx_files(
    directory: Path,
    recursive: bool = False,
) -> list[Path]:
    """Find all DOCX files in a directory.

    Args:
        directory: Directory to search
        recursive: If True, search subdirectories recursively

    Returns:
        List of DOCX file paths, sorted
    """
    pattern = "**/*.docx" if recursive else "*.docx"
    return sorted(directory.glob(pattern))


def find_documents(
    directory: Path,
    recursive: bool = False,
    extensions: tuple[str, ...] = (".pdf", ".docx"),
) -> list[Path]:
    """Find all PDF and DOCX files in a directory.

    Args:
        directory: Directory to search
        recursive: If True, search subdirectories recursively
        extensions: Tuple of file extensions to search for

    Returns:
        List of document file paths, sorted
    """
    files = []
    if recursive:
        for ext in extensions:
            files.extend(directory.glob(f"**/*{ext}"))
    else:
        for ext in extensions:
            files.extend(directory.glob(f"*{ext}"))
    return sorted(files)


def scan_directory(
    directory: Path,
    recursive: bool = False,
) -> dict:
    """Scan a directory for PDF and DOCX files.

    Args:
        directory: Directory to scan
        recursive: If True, scan subdirectories recursively

    Returns:
        Dictionary with 'pdf_files', 'docx_files', 'total_files', and 'subdirs'
    """
    pdf_files = find_pdf_files(directory, recursive)
    docx_files = find_docx_files(directory, recursive)

    result = {
        "pdf_files": pdf_files,
        "docx_files": docx_files,
        "total_files": len(pdf_files) + len(docx_files),
        "subdirs": [],
    }

    if recursive:
        # Find all subdirectories that contain documents
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
    """Calculate output path preserving directory structure.

    Args:
        input_file: Path to input file
        input_dir: Root input directory
        output_dir: Root output directory
        recursive: If True, preserve subdirectory structure
        suffix: Suffix to add to each subdirectory name (default: "_md")

    Returns:
        Output file path with preserved structure and _md suffix on directories
    """
    if not recursive:
        # Flat mode: all files go directly to output_dir
        return output_dir / f"{input_file.stem}.md"

    # Recursive mode: preserve directory structure with _md suffix
    try:
        rel_path = input_file.relative_to(input_dir)
    except ValueError:
        # File not under input_dir, fallback to flat mode
        return output_dir / f"{input_file.stem}.md"

    # Build output path with _md suffix on each directory component
    output_parts = []
    for part in rel_path.parts[:-1]:  # All parts except filename
        output_parts.append(f"{part}{suffix}")

    # Add filename (without extension) + .md
    output_parts.append(f"{input_file.stem}.md")

    return output_dir / Path(*output_parts)


def create_output_directories(
    files: list[Path],
    input_dir: Path,
    output_dir: Path,
    recursive: bool = False,
    suffix: str = "_md",
):
    """Create output directories preserving input structure.

    Args:
        files: List of input file paths
        input_dir: Root input directory
        output_dir: Root output directory
        recursive: If True, create subdirectories with _md suffix
        suffix: Suffix to add to each subdirectory name
    """
    if not recursive:
        output_dir.mkdir(parents=True, exist_ok=True)
        return

    # Create all necessary output directories
    for file in files:
        output_path = get_output_path(file, input_dir, output_dir, recursive, suffix)
        output_path.parent.mkdir(parents=True, exist_ok=True)
