"""
NuoYi - Command-line interface for document conversion.
"""

import argparse
import sys
from pathlib import Path

from .converter import (
    DocxConverter,
    MarkerPDFConverter,
)
from .utils import save_images_and_update_markdown, SUPPORTED_LANGUAGES, DEFAULT_LANGS


def convert_single_file(input_path: Path, output_path: Path,
                        force_ocr: bool, page_range: str,
                        langs: str, device: str = "auto"):
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
        content = save_images_and_update_markdown(
            content, images, output_path.parent, "images"
        )
    
    output_path.write_text(content, encoding="utf-8")
    print(f"Done! Output: {output_path}")


def convert_directory(input_dir: Path, output_dir: Path,
                      force_ocr: bool, page_range: str,
                      langs: str, device: str = "auto"):
    """Batch convert all PDF/DOCX files in a directory."""
    exts = ('.pdf', '.docx')
    files = sorted(
        f for f in input_dir.iterdir()
        if f.suffix.lower() in exts
    )
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
  nuoyi paper.pdf --device cpu           # Force CPU (low VRAM)
  nuoyi --gui                            # Launch GUI

Notes:
  marker-pdf models (~2-3 GB) are downloaded automatically on first run.
  After that, everything works fully offline.

  Use --device cpu if you encounter CUDA out of memory errors.
  The 'auto' mode (default) will detect GPU memory and fall back to CPU if needed.
        """,
    )

    parser.add_argument(
        "input", nargs="?",
        help="Input PDF/DOCX file or directory (with --batch)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (single file) or directory (batch mode)",
    )
    parser.add_argument(
        "--force-ocr", action="store_true",
        help="Force OCR even for digital PDFs with embedded text",
    )
    parser.add_argument(
        "--page-range",
        help="Page range to convert, e.g. '0-5,10,15-20'",
    )
    lang_codes = ", ".join(SUPPORTED_LANGUAGES.keys())
    parser.add_argument(
        "--langs", default=DEFAULT_LANGS,
        help=f"Comma-separated languages (default: {DEFAULT_LANGS}). "
             f"Supported: {lang_codes}",
    )
    parser.add_argument(
        "--list-langs", action="store_true",
        help="List all supported languages and exit",
    )
    parser.add_argument(
        "--batch", action="store_true",
        help="Process all PDF/DOCX files in the input directory",
    )
    parser.add_argument(
        "--device", default="auto",
        choices=["auto", "cpu", "cuda", "mps"],
        help="Device for model inference: auto (default), cpu, cuda, or mps",
    )
    parser.add_argument(
        "--gui", action="store_true",
        help="Launch PySide6 GUI mode",
    )
    parser.add_argument(
        "-V", "--version", action="store_true",
        help="Show version and exit",
    )

    args = parser.parse_args()

    # --- Version ---
    if args.version:
        from . import __version__
        print(f"NuoYi version {__version__}")
        sys.exit(0)

    # --- List languages ---
    if args.list_langs:
        print("Supported languages:")
        for code, name in SUPPORTED_LANGUAGES.items():
            print(f"  {code:4s}  {name}")
        print(f"\nDefault: {DEFAULT_LANGS}")
        print(f"Usage:   nuoyi paper.pdf --langs \"{DEFAULT_LANGS}\"")
        sys.exit(0)

    # --- GUI mode ---
    if args.gui:
        from .gui import run_gui
        run_gui()

    # --- CLI mode ---
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

    # Single file mode
    if input_path.is_file():
        output_path = (
            Path(args.output) if args.output
            else input_path.with_suffix(".md")
        )

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
            print(
                f"Error: {input_path} is a directory. "
                "Use --batch to process all files in it."
            )
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


if __name__ == "__main__":
    main()
