"""
NuoYi - Command-line interface for document conversion.

Supported acceleration backends:
- CUDA: NVIDIA GPUs
- ROCm: AMD GPUs
- MPS: Apple Silicon Metal
- MLX: Apple MLX framework
- CPU: Universal fallback
"""

import argparse
import sys
from pathlib import Path

from . import __version__
from .converter import DocxConverter, MarkerPDFConverter
from .utils import (
    DEFAULT_LANGS,
    SUPPORTED_DEVICES,
    SUPPORTED_LANGUAGES,
    list_available_devices,
    print_device_info,
    save_images_and_update_markdown,
)


def convert_single_file(
    input_path: Path,
    output_path: Path,
    force_ocr: bool,
    page_range: str,
    langs: str,
    device: str = "auto",
):
    """Convert a single PDF or DOCX file."""
    suffix = input_path.suffix.lower()
    images = {}

    if suffix == ".pdf":
        converter = MarkerPDFConverter(
            force_ocr=force_ocr,
            page_range=page_range,
            langs=langs,
            device=device,
        )
        content, images = converter.convert_file(str(input_path))

    elif suffix == ".docx":
        converter = DocxConverter()
        content = converter.convert_file(str(input_path))

    elif suffix == ".doc":
        print("Error: Legacy .doc format is not supported. Please convert to .docx first.")
        sys.exit(1)

    else:
        print(f"Error: Unsupported format: {suffix}")
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if images:
        content = save_images_and_update_markdown(content, images, output_path.parent, "images")

    output_path.write_text(content, encoding="utf-8")
    print(f"Done! Output: {output_path}")


def convert_directory(
    input_dir: Path,
    output_dir: Path,
    force_ocr: bool,
    page_range: str,
    langs: str,
    device: str = "auto",
    recursive: bool = False,
):
    """Batch convert all PDF/DOCX files in a directory."""
    from .utils import find_documents

    files = find_documents(input_dir, recursive=recursive)
    if not files:
        print("No PDF/DOCX files found in directory.")
        return

    print(f"Found {len(files)} files to process.\n")
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_converter = None
    docx_converter = None

    pdf_files = [f for f in files if f.suffix.lower() == ".pdf"]
    docx_files = [f for f in files if f.suffix.lower() == ".docx"]

    if pdf_files:
        pdf_converter = MarkerPDFConverter(
            force_ocr=force_ocr,
            page_range=page_range,
            langs=langs,
            device=device,
        )

    if docx_files:
        docx_converter = DocxConverter()

    success = 0
    failed = 0

    for i, file_path in enumerate(files, 1):
        suffix = file_path.suffix.lower()
        print(f"[{i}/{len(files)}] {file_path.name}...", end=" ", flush=True)

        try:
            images = {}
            if suffix == ".pdf" and pdf_converter:
                content, images = pdf_converter.convert_file(str(file_path))
            elif suffix == ".docx" and docx_converter:
                content = docx_converter.convert_file(str(file_path))
            else:
                print("SKIPPED (no converter)")
                continue

            out_path = output_dir / f"{file_path.stem}.md"

            if images:
                images_subdir = f"{file_path.stem}_images"
                content = save_images_and_update_markdown(
                    content, images, output_dir, images_subdir
                )

            out_path.write_text(content, encoding="utf-8")
            print("OK")
            success += 1

        except Exception as e:
            print(f"ERROR: {e}")
            failed += 1

    print(f"\nBatch complete: {success} succeeded, {failed} failed.")


def main():
    """Main entry point for NuoYi CLI."""
    parser = argparse.ArgumentParser(
        prog="nuoyi",
        description="NuoYi - Convert PDF/DOCX to Markdown using marker-pdf (offline)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  nuoyi paper.pdf                        # Single file
  nuoyi paper.pdf -o output/result.md    # Custom output
  nuoyi ./papers --batch                 # Batch directory
  nuoyi ./papers --batch -o ./output     # Batch with output dir
  nuoyi ./papers --batch -r              # Recursive batch (all subdirs)
  nuoyi paper.pdf --device cuda          # Use NVIDIA GPU
  nuoyi paper.pdf --device rocm          # Use AMD GPU
  nuoyi paper.pdf --device mps           # Use Apple Metal
  nuoyi paper.pdf --device mlx           # Use Apple MLX
  nuoyi --gui                            # Launch GUI

Acceleration Backends:
  cuda   - NVIDIA GPUs (CUDA)
  rocm   - AMD GPUs (ROCm/HIP)
  mps    - Apple Silicon Metal Performance Shaders
  mlx    - Apple MLX framework (experimental)
  cpu    - Universal fallback (slowest but most compatible)
  auto   - Automatic selection (default)

Notes:
  marker-pdf models (~2-3 GB) are downloaded automatically on first run.
  After that, everything works fully offline.

  Use --list-devices to see available acceleration options on your system.
        """,
    )

    parser.add_argument(
        "input",
        nargs="?",
        help="Input PDF/DOCX file or directory (with --batch)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path (single file) or directory (batch mode)",
    )
    parser.add_argument(
        "--force-ocr",
        action="store_true",
        help="Force OCR even for digital PDFs with embedded text",
    )
    parser.add_argument(
        "--page-range",
        help="Page range to convert, e.g. '0-5,10,15-20'",
    )
    lang_codes = ", ".join(SUPPORTED_LANGUAGES.keys())
    parser.add_argument(
        "--langs",
        default=DEFAULT_LANGS,
        help=f"Comma-separated languages (default: {DEFAULT_LANGS}). Supported: {lang_codes}",
    )
    parser.add_argument(
        "--list-langs",
        action="store_true",
        help="List all supported languages and exit",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available acceleration devices and exit",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all PDF/DOCX files in the input directory",
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Recursively process subdirectories (with --batch)",
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=SUPPORTED_DEVICES,
        help="Device for model inference: auto (default), cuda, rocm, mps, mlx, or cpu",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch PySide6 GUI mode",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"NuoYi {__version__}",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress non-essential output",
    )

    args = parser.parse_args()

    if args.list_langs:
        print("Supported languages:")
        for code, name in SUPPORTED_LANGUAGES.items():
            print(f"  {code:4s}  {name}")
        print(f"\nDefault: {DEFAULT_LANGS}")
        print(f'Usage:   nuoyi paper.pdf --langs "{DEFAULT_LANGS}"')
        sys.exit(0)

    if args.list_devices:
        print("Available acceleration devices:\n")
        available = list_available_devices()
        device_descriptions = {
            "cuda": "NVIDIA GPU (CUDA)",
            "rocm": "AMD GPU (ROCm/HIP)",
            "mps": "Apple Silicon Metal",
            "mlx": "Apple MLX Framework",
            "cpu": "CPU (universal fallback)",
        }
        for device in ["cuda", "rocm", "mps", "mlx", "cpu"]:
            status = "✓ available" if device in available else "✗ not available"
            desc = device_descriptions.get(device, "")
            print(f"  {device:6s}  {desc:30s}  {status}")
        print("\nUse --device <name> to select a specific device.")
        print("Use --device auto for automatic selection.")
        print("\nDetailed device information:")
        print_device_info()
        sys.exit(0)

    if args.gui:
        from .gui import run_gui

        run_gui()

    if not args.input:
        parser.print_help()
        print("\nError: Input file or directory is required (or use --gui).")
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Path not found: {args.input}")
        sys.exit(1)

    force_ocr = args.force_ocr
    page_range = args.page_range
    langs = args.langs
    device = args.device

    if input_path.is_file():
        output_path = Path(args.output) if args.output else input_path.with_suffix(".md")

        print(f"Input:  {input_path}")
        print(f"Output: {output_path}")
        print(f"Force OCR: {force_ocr}")
        if page_range:
            print(f"Page Range: {page_range}")
        print(f"Languages: {langs}")
        print(f"Device: {device}")
        print()

        convert_single_file(input_path, output_path, force_ocr, page_range, langs, device)

    elif input_path.is_dir():
        if not args.batch:
            print(f"Error: {input_path} is a directory. Use --batch to process all files in it.")
            sys.exit(1)

        output_dir = Path(args.output) if args.output else input_path
        print(f"Input dir:  {input_path}")
        print(f"Output dir: {output_dir}")
        print(f"Force OCR: {force_ocr}")
        if page_range:
            print(f"Page Range: {page_range}")
        print(f"Languages: {langs}")
        print(f"Device: {device}")
        print()

        convert_directory(input_path, output_dir, force_ocr, page_range, langs, device)

    else:
        print(f"Error: Invalid path: {args.input}")
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Path not found: {args.input}")
        sys.exit(1)

    force_ocr = args.force_ocr
    page_range = args.page_range
    langs = args.langs
    device = args.device

    # Single file mode
    if input_path.is_file():
        output_path = Path(args.output) if args.output else input_path.with_suffix(".md")

        print(f"Input:  {input_path}")
        print(f"Output: {output_path}")
        print(f"Force OCR: {force_ocr}")
        if page_range:
            print(f"Page Range: {page_range}")
        print(f"Languages: {langs}")
        print(f"Device: {device}")
        print()

        convert_single_file(input_path, output_path, force_ocr, page_range, langs, device)

    # Batch directory mode
    elif input_path.is_dir():
        if not args.batch:
            print(f"Error: {input_path} is a directory. Use --batch to process all files in it.")
            sys.exit(1)

        output_dir = Path(args.output) if args.output else input_path
        print(f"Input dir:  {input_path}")
        print(f"Output dir: {output_dir}")
        print(f"Recursive:  {args.recursive}")
        print(f"Force OCR: {force_ocr}")
        if page_range:
            print(f"Page Range: {page_range}")
        print(f"Languages: {langs}")
        print(f"Device: {device}")
        print()

        convert_directory(
            input_path, output_dir, force_ocr, page_range, langs, device, args.recursive
        )

    else:
        print(f"Error: Invalid path: {args.input}")
        sys.exit(1)


if __name__ == "__main__":
    main()
