"""
NuoYi - Utility functions for document conversion.

Memory management, device selection, and markdown processing utilities.
"""

import gc
import os
import re
from pathlib import Path
from typing import Tuple


# Supported languages for OCR recognition
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


def setup_memory_optimization():
    """Configure PyTorch for better memory management."""
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    os.environ.setdefault(
        "PYTORCH_CUDA_ALLOC_CONF",
        "expandable_segments:True,garbage_collection_threshold:0.6"
    )


def get_gpu_memory_info() -> Tuple[float, float]:
    """Get total and free GPU memory in GB. Returns (0, 0) if no GPU."""
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


def clear_gpu_memory():
    """Release unused GPU memory."""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        gc.collect()
    except Exception:
        gc.collect()


def select_device(preferred: str = "auto", min_vram_gb: float = 6.0) -> str:
    """
    Select the best device for running marker-pdf.

    Args:
        preferred: "auto", "cuda", "cpu", or "mps"
        min_vram_gb: Minimum VRAM required to use GPU (default 6GB)

    Returns:
        Device string: "cuda", "cpu", or "mps"
    """
    if preferred == "cpu":
        print("[Device] Forcing CPU mode as requested.")
        return "cpu"

    if preferred == "mps":
        try:
            import torch
            if torch.backends.mps.is_available():
                print("[Device] Using MPS (Apple Silicon GPU).")
                return "mps"
        except Exception:
            pass
        print("[Device] MPS not available, falling back to CPU.")
        return "cpu"

    if preferred in ("cuda", "auto"):
        try:
            import torch
            if torch.cuda.is_available():
                total, free = get_gpu_memory_info()
                print(f"[Device] GPU detected: {total:.1f}GB total, {free:.1f}GB free")

                if free >= min_vram_gb:
                    print(f"[Device] Using CUDA (sufficient VRAM: {free:.1f}GB >= {min_vram_gb}GB)")
                    return "cuda"
                else:
                    print(f"[Device] WARNING: Low VRAM ({free:.1f}GB < {min_vram_gb}GB required)")
                    if preferred == "cuda":
                        print("[Device] Forcing CUDA anyway (--device cuda). OOM may occur.")
                        return "cuda"
                    else:
                        print("[Device] Falling back to CPU to avoid OOM.")
                        return "cpu"
        except Exception as e:
            print(f"[Device] CUDA detection failed: {e}")

    print("[Device] Using CPU.")
    return "cpu"


def clean_markdown(text: str) -> str:
    """Clean up marker-pdf output with fixes for common issues.
    
    Handles:
    - Excessive newlines
    - Windows line endings
    - Broken citation links (e.g., [Author](#page-X-Y) -> Author)
    - Invalid internal page anchors that cause KaTeX parse errors
    """
    # Fix Windows line endings
    text = text.replace('\r\n', '\n')
    
    # Reduce excessive newlines
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    
    # Fix broken citation/reference links from marker-pdf
    # Pattern: [text](#page-X-Y) or [text](#page-X-Y-Z) -> text
    # These internal page anchors are invalid in converted markdown
    # and cause KaTeX parse errors in some renderers
    text = re.sub(r'\[([^\]]+)\]\(#page-\d+(?:-\d+)*\)', r'\1', text)
    
    # Also handle other common internal anchor patterns
    # [text](#_bookmark123) -> text
    text = re.sub(r'\[([^\]]+)\]\(#_?bookmark\d+\)', r'\1', text)
    
    # Remove empty link targets: [text]() -> text
    text = re.sub(r'\[([^\]]+)\]\(\)', r'\1', text)
    
    # Fix citation patterns that lost their opening parenthesis
    # Match: "Author, Year)" or "Author and Author, Year)" or "Author et al., Year)"
    # ending with ) but missing opening (
    # Negative lookbehind ensures we don't match already-parenthesized citations
    text = re.sub(
        r'(?<![(\w])'  # not preceded by ( or word char
        r'([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)?'  # Author or Author and Author
        r'(?:\s+et\s+al\.)?'  # optional et al.
        r',?\s*\d{4}[a-z]?'  # , Year
        r'(?:\s*;\s*'  # ; separator
        r'[A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)?(?:\s+et\s+al\.)?'  # more authors
        r',?\s*\d{4}[a-z]?)*'  # more years
        r')\)',  # closing )
        r'(\1)',
        text
    )
    
    # Clean up double parentheses that might result from over-correction
    text = re.sub(r'\(\(([^)]+)\)\)', r'(\1)', text)
    
    return text.strip()


def save_images_and_update_markdown(
    markdown_text: str,
    images: dict,
    output_dir: Path,
    images_subdir: str = "images"
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
            
            if hasattr(img_data, 'save'):
                img_data.save(str(img_path))
                saved_count += 1
            elif isinstance(img_data, bytes):
                with open(img_path, 'wb') as f:
                    f.write(img_data)
                saved_count += 1
            elif isinstance(img_data, str):
                import base64
                try:
                    img_bytes = base64.b64decode(img_data)
                    with open(img_path, 'wb') as f:
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
        
        old_ref = f"](./{ img_name})"
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
