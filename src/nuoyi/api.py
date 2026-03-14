"""
NuoYi - Unified Python API.

Provides ToolResult-based wrappers for programmatic usage
and agent integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class ToolResult:
    """Standardised return type for all NuoYi API functions."""

    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }


def convert_file(
    input_path: str | Path,
    *,
    output_path: str | Path | None = None,
    force_ocr: bool = False,
    page_range: str | None = None,
    langs: str = "zh,en",
    device: str = "auto",
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
        from .converter import DocxConverter, MarkerPDFConverter
        from .utils import save_images_and_update_markdown

        images = {}
        if suffix == ".pdf":
            converter = MarkerPDFConverter(
                force_ocr=force_ocr,
                page_range=page_range,
                langs=langs,
                device=device,
            )
            content, images = converter.convert_file(str(input_path))
        else:
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
) -> ToolResult:
    """Batch-convert all PDF/DOCX files in a directory.

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

    exts = (".pdf", ".docx")
    files = sorted(f for f in input_dir.iterdir() if f.suffix.lower() in exts)

    if not files:
        return ToolResult(
            success=True,
            data={"files": [], "success": 0, "failed": 0},
            metadata={"input_dir": str(input_dir)},
        )

    results = []
    success_count = 0
    failed_count = 0

    for f in files:
        out_path = output_dir / f"{f.stem}.md"
        r = convert_file(
            f,
            output_path=out_path,
            force_ocr=force_ocr,
            page_range=page_range,
            langs=langs,
            device=device,
        )
        results.append(
            {
                "file": f.name,
                "success": r.success,
                "output": str(out_path) if r.success else None,
                "error": r.error,
            }
        )
        if r.success:
            success_count += 1
        else:
            failed_count += 1

    from . import __version__

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
            "version": __version__,
        },
    )
