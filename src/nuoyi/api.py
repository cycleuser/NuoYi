"""
NuoYi - Unified Python API.

Provides ToolResult-based wrappers for programmatic usage
and agent integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
    existing_files: str = "ask",
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
    existing_files : str
        How to handle existing output files: 'ask', 'overwrite', 'skip', or 'update'.
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

    existing_output_files = []
    for f in files:
        out_path = get_output_path(f, input_dir, output_dir, recursive)
        if out_path.exists():
            existing_output_files.append((f, out_path))

    if existing_output_files and existing_files == "ask":
        print(f"\n[Batch] Found {len(existing_output_files)} existing output files.")
        print("Choose how to handle them:")
        print("  [1] Overwrite all - Replace all existing files")
        print("  [2] Skip all - Keep all existing files")
        print("  [3] Update all - Only convert if source is newer")
        print("  [4] Ask for each file individually")
        print()

        try:
            choice = input("Enter your choice (1/2/3/4) [default: 4]: ").strip()
            if choice in ("1", "overwrite"):
                existing_files = "overwrite"
                print("[Batch] Will overwrite all existing files.")
            elif choice in ("2", "skip"):
                existing_files = "skip"
                print("[Batch] Will skip all existing files.")
            elif choice in ("3", "update"):
                existing_files = "update"
                print("[Batch] Will only convert files newer than existing.")
            else:
                existing_files = "ask_each"
                print("[Batch] Will ask for each file.")
        except (EOFError, KeyboardInterrupt):
            print("\n[Batch] Cancelled. Defaulting to 'skip' mode.")
            existing_files = "skip"

    print(f"[Batch] Converting {len(files)} files...")

    results = []
    success_count = 0
    failed_count = 0
    skipped_count = 0

    for i, f in enumerate(files, 1):
        out_path = get_output_path(f, input_dir, output_dir, recursive)

        filename = str(f.relative_to(input_dir)) if recursive else f.name

        should_convert = True
        if out_path.exists():
            if existing_files == "skip":
                should_convert = False
                print(f"[Batch] {i}/{len(files)}: {filename} - Skipping (already exists)")
            elif existing_files == "update":
                src_mtime = f.stat().st_mtime
                out_mtime = out_path.stat().st_mtime
                if src_mtime <= out_mtime:
                    should_convert = False
                    print(f"[Batch] {i}/{len(files)}: {filename} - Skipping (source not newer)")
                else:
                    print(f"[Batch] {i}/{len(files)}: {filename} - Updating (source is newer)")
            elif existing_files == "ask_each":
                print(f"\n[Batch] {i}/{len(files)}: {filename}")
                print(f"  Output file already exists: {out_path}")
                print("  [o] Overwrite this file")
                print("  [s] Skip this file")
                print("  [u] Update if source is newer")
                print("  [O] Overwrite all remaining")
                print("  [S] Skip all remaining")
                print("  [U] Update all remaining")
                try:
                    choice = input("  Your choice (o/s/u/O/S/U) [default: s]: ").strip().lower()
                    if choice == "o":
                        should_convert = True
                        print("  Will overwrite.")
                    elif choice == "s":
                        should_convert = False
                        print("  Will skip.")
                    elif choice == "u":
                        src_mtime = f.stat().st_mtime
                        out_mtime = out_path.stat().st_mtime
                        if src_mtime > out_mtime:
                            should_convert = True
                            print("  Will update (source is newer).")
                        else:
                            should_convert = False
                            print("  Will skip (source not newer).")
                    elif choice == "O":
                        existing_files = "overwrite"
                        should_convert = True
                        print("  Will overwrite all remaining files.")
                    elif choice == "S":
                        existing_files = "skip"
                        should_convert = False
                        print("  Will skip all remaining files.")
                    elif choice == "U":
                        existing_files = "update"
                        src_mtime = f.stat().st_mtime
                        out_mtime = out_path.stat().st_mtime
                        if src_mtime > out_mtime:
                            should_convert = True
                            print("  Will update all remaining files (this file: newer).")
                        else:
                            should_convert = False
                            print("  Will update all remaining files (this file: not newer).")
                    else:
                        should_convert = False
                        print("  Will skip (default).")
                except (EOFError, KeyboardInterrupt):
                    print("\n  Cancelled. Skipping this file.")
                    should_convert = False
            elif existing_files == "overwrite":
                print(f"[Batch] {i}/{len(files)}: {filename} - Overwriting existing file")
                should_convert = True

        if not should_convert:
            skipped_count += 1
            results.append(
                {
                    "file": filename,
                    "success": True,
                    "output": str(out_path),
                    "error": None,
                    "skipped": True,
                }
            )
            continue

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
                error_msg = r.error or "Unknown error"
                if "CUDA OOM" in error_msg or "CUDA out of memory" in error_msg:
                    print(f"[Batch] ✗ {filename}: CUDA OOM")
                    print(f"[Batch] Attempting fallback to CPU...")
                    try:
                        r_cpu = convert_file(
                            f,
                            output_path=out_path,
                            force_ocr=force_ocr,
                            page_range=page_range,
                            langs=langs,
                            device="cpu",
                            disable_ocr_models=disable_ocr_models,
                            use_cache=False,
                        )
                        if r_cpu.success:
                            success_count += 1
                            print(f"[Batch] ✓ {filename} (CPU fallback)")
                            r = r_cpu
                        else:
                            failed_count += 1
                            print(f"[Batch] ✗ {filename}: CPU fallback failed - {r_cpu.error}")
                    except Exception as e_cpu:
                        failed_count += 1
                        print(f"[Batch] ✗ {filename}: CPU fallback failed - {e_cpu}")
                        r = ToolResult(
                            success=False, error=f"CUDA OOM, CPU fallback failed: {e_cpu}"
                        )
                else:
                    failed_count += 1
                    print(f"[Batch] ✗ {filename}: {error_msg}")

            if on_progress:
                on_progress(i, len(files), filename, r.success)

        except Exception as e:
            error_msg = str(e)
            if "CUDA OOM" in error_msg or "CUDA out of memory" in error_msg:
                print(f"[Batch] ✗ {filename}: CUDA OOM")
                print(f"[Batch] Attempting fallback to CPU...")
                try:
                    r = convert_file(
                        f,
                        output_path=out_path,
                        force_ocr=force_ocr,
                        page_range=page_range,
                        langs=langs,
                        device="cpu",
                        disable_ocr_models=disable_ocr_models,
                        use_cache=False,
                    )
                    if r.success:
                        success_count += 1
                        print(f"[Batch] ✓ {filename} (CPU fallback)")
                    else:
                        failed_count += 1
                        print(f"[Batch] ✗ {filename}: CPU fallback failed - {r.error}")
                except Exception as e_cpu:
                    failed_count += 1
                    r = ToolResult(success=False, error=f"CUDA OOM, CPU fallback failed: {e_cpu}")
                    print(f"[Batch] ✗ {filename}: CPU fallback failed - {e_cpu}")
            else:
                failed_count += 1
                r = ToolResult(success=False, error=error_msg)
                print(f"[Batch] ✗ {filename}: {error_msg}")

            if on_progress:
                on_progress(i, len(files), filename, False)

        results.append(
            {
                "file": filename,
                "success": r.success,
                "output": str(out_path) if r.success else None,
                "error": r.error,
                "skipped": False,
            }
        )

        if i % 5 == 0:
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
            except Exception:
                pass

        if i % 10 == 0:
            try:
                import gc

                gc.collect()
                clear_converter_cache()
            except Exception:
                pass

    clear_converter_cache()

    from . import __version__

    print(
        f"[Batch] Done: {success_count} converted, {skipped_count} skipped, {failed_count} failed"
    )

    return ToolResult(
        success=failed_count == 0,
        data={
            "files": results,
            "success": success_count,
            "skipped": skipped_count,
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
