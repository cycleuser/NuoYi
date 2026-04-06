"""
NuoYi - Unified Python API.

Provides ToolResult-based wrappers for programmatic usage
and agent integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

_converter_cache: dict = {}


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }


def _get_cached_converter(
    converter_type: str,
    *,
    force_ocr: bool = False,
    page_range: str | None = None,
    langs: str = "zh,en",
    device: str = "auto",
    disable_ocr_models: bool = False,
    low_vram: bool = False,
):
    """Get or create a cached converter instance.

    This prevents reloading models for each file in batch operations.
    """
    global _converter_cache

    cache_key = (
        converter_type,
        force_ocr,
        page_range,
        langs,
        device,
        disable_ocr_models,
        low_vram,
    )

    if cache_key not in _converter_cache:
        if converter_type == "marker":
            from .converter import MarkerPDFConverter

            _converter_cache[cache_key] = MarkerPDFConverter(
                force_ocr=force_ocr,
                page_range=page_range,
                langs=langs,
                device=device,
                disable_ocr_models=disable_ocr_models,
                low_vram=low_vram,
            )
        elif converter_type == "docx":
            from .converter import DocxConverter

            _converter_cache[cache_key] = DocxConverter()

    return _converter_cache[cache_key]


def clear_converter_cache():
    """Clear the converter cache to free GPU memory."""
    global _converter_cache

    for _key, converter in list(_converter_cache.items()):
        if hasattr(converter, "cleanup"):
            try:
                converter.cleanup()
            except Exception:
                pass

    _converter_cache.clear()
    print("[Memory] Converter cache cleared")


def convert_file(
    input_path: str | Path,
    *,
    output_path: str | Path | None = None,
    force_ocr: bool = False,
    page_range: str | None = None,
    langs: str = "zh,en",
    device: str = "auto",
    disable_ocr_models: bool = False,
    low_vram: bool = False,
    use_cache: bool = True,
) -> ToolResult:
    """Convert a single PDF or DOCX file to Markdown.

    Parameters
    ----------
    input_path : str or Path
        Path to the input PDF or DOCX file.
    output_path : str, Path, or None
        Output .md file path. Defaults to input stem + .md.
    force_ocr : bool
        Force OCR even for digital PDFs.
    page_range : str or None
        Page range, e.g. '0-5,10,15-20'.
    langs : str
        Comma-separated language codes.
    device : str
        Compute device: auto, cuda, rocm, mps, mlx, or cpu.
    disable_ocr_models : bool
        Disable OCR models for marker (saves ~1.5GB VRAM, for digital PDFs only).
    low_vram : bool
        Enable low VRAM mode with GPU offloading.
    use_cache : bool
        Use cached converter to avoid reloading models (default: True).

    Returns
    -------
    ToolResult
        With data containing the markdown text and output path.
    """
    input_path = Path(input_path)
    if not input_path.exists():
        return ToolResult(success=False, error=f"File not found: {input_path}")

    suffix = input_path.suffix.lower()
    if suffix not in (".pdf", ".docx"):
        return ToolResult(
            success=False,
            error=f"Unsupported format: {suffix}. Use .pdf or .docx",
        )

    if output_path is None:
        output_path = input_path.with_suffix(".md")
    else:
        output_path = Path(output_path)

    try:
        from . import __version__
        from .utils import save_images_and_update_markdown

        images = {}
        if suffix == ".pdf":
            if use_cache:
                converter = _get_cached_converter(
                    "marker",
                    force_ocr=force_ocr,
                    page_range=page_range,
                    langs=langs,
                    device=device,
                    disable_ocr_models=disable_ocr_models,
                    low_vram=low_vram,
                )
            else:
                from .converter import MarkerPDFConverter

                converter = MarkerPDFConverter(
                    force_ocr=force_ocr,
                    page_range=page_range,
                    langs=langs,
                    device=device,
                    disable_ocr_models=disable_ocr_models,
                    low_vram=low_vram,
                )
            content, images = converter.convert_file(str(input_path))
        else:
            if use_cache:
                converter = _get_cached_converter("docx")
            else:
                from .converter import DocxConverter

                converter = DocxConverter()
            content = converter.convert_file(str(input_path))

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if images:
            content = save_images_and_update_markdown(content, images, output_path.parent, "images")

        output_path.write_text(content, encoding="utf-8")

        return ToolResult(
            success=True,
            data={
                "markdown": content,
                "output_path": str(output_path),
                "image_count": len(images),
            },
            metadata={
                "input_path": str(input_path),
                "format": suffix,
                "version": __version__,
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def convert_directory(
    input_dir: str | Path,
    *,
    output_dir: str | Path | None = None,
    force_ocr: bool = False,
    page_range: str | None = None,
    langs: str = "zh,en",
    device: str = "auto",
    recursive: bool = False,
    disable_ocr_models: bool = False,
    low_vram: bool = False,
    on_progress: callable | None = None,
) -> ToolResult:
    """Batch-convert all PDF/DOCX files in a directory with optimized memory management.

    Parameters
    ----------
    input_dir : str or Path
        Directory containing files to convert.
    output_dir : str, Path, or None
        Output directory. Defaults to input_dir.
    force_ocr : bool
        Force OCR even for digital PDFs.
    page_range : str or None
        Page range for PDFs.
    langs : str
        Comma-separated language codes.
    device : str
        Compute device: auto, cuda, rocm, mps, mlx, or cpu.
    recursive : bool
        If True, search subdirectories recursively.
    disable_ocr_models : bool
        Disable OCR models for marker (saves ~1.5GB VRAM, for digital PDFs only).
    low_vram : bool
        Enable low VRAM mode with GPU offloading.
    on_progress : callable or None
        Progress callback: on_progress(current, total, filename, success)

    Returns
    -------
    ToolResult
        With data containing per-file results and summary.
    """
    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        return ToolResult(success=False, error=f"Not a directory: {input_dir}")

    if output_dir is None:
        output_dir = input_dir
    else:
        output_dir = Path(output_dir)

    from .utils import create_output_directories, find_documents, get_output_path

    files = find_documents(input_dir, recursive=recursive)

    if not files:
        return ToolResult(
            success=True,
            data={"files": [], "success": 0, "failed": 0},
            metadata={"input_dir": str(input_dir), "recursive": recursive},
        )

    create_output_directories(files, input_dir, output_dir, recursive)

    print(f"[Batch] Converting {len(files)} files...")

    results = []
    success_count = 0
    failed_count = 0

    for i, f in enumerate(files, 1):
        out_path = get_output_path(f, input_dir, output_dir, recursive)

        filename = str(f.relative_to(input_dir)) if recursive else f.name
        print(f"[Batch] {i}/{len(files)}: {filename}")

        try:
            r = convert_file(
                f,
                output_path=out_path,
                force_ocr=force_ocr,
                page_range=page_range,
                langs=langs,
                device=device,
                disable_ocr_models=disable_ocr_models,
                use_cache=True,
            )

            if r.success:
                success_count += 1
                print(f"[Batch] ✓ {filename}")
            else:
                failed_count += 1
                print(f"[Batch] ✗ {filename}: {r.error}")

            if on_progress:
                on_progress(i, len(files), filename, r.success)

        except Exception as e:
            failed_count += 1
            r = ToolResult(success=False, error=str(e))
            print(f"[Batch] ✗ {filename}: {e}")

            if on_progress:
                on_progress(i, len(files), filename, False)

        results.append(
            {
                "file": filename,
                "success": r.success,
                "output": str(out_path) if r.success else None,
                "error": r.error,
            }
        )

        if i % 5 == 0:
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

    clear_converter_cache()

    from . import __version__

    print(f"[Batch] Done: {success_count}/{len(files)} successful")

    return ToolResult(
        success=failed_count == 0,
        data={
            "files": results,
            "success": success_count,
            "failed": failed_count,
        },
        metadata={
            "input_dir": str(input_dir.resolve()),
            "output_dir": str(output_dir.resolve()),
            "total": len(files),
            "recursive": recursive,
            "version": __version__,
        },
    )
