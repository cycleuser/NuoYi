#!/usr/bin/env python3
"""
Auto-select best PDF engine based on content type.

Usage:
    python auto_convert.py input_directory [output_directory]

This script automatically:
1. Detects if PDF is digital (has text) or scanned (image-only)
2. Uses pymupdf for digital PDFs (fast, no GPU)
3. Uses marker for scanned PDFs (with OCR)
"""

from __future__ import annotations

import sys
from pathlib import Path


def is_digital_pdf(pdf_path: Path) -> bool:
    """Check if PDF has extractable text (digital) or is image-only (scanned)."""
    try:
        import fitz

        doc = fitz.open(str(pdf_path))
        total_text = 0

        # Check first 3 pages
        for page_num in range(min(3, len(doc))):
            page = doc[page_num]
            text = page.get_text()
            total_text += len(text.strip())

        doc.close()

        # If less than 50 chars total, likely scanned
        return total_text >= 50

    except Exception as e:
        print(f"Warning: Could not check {pdf_path}: {e}")
        return True  # Assume digital


def convert_pdf_smart(
    input_path: Path,
    output_path: Path | None = None,
) -> bool:
    """Convert PDF using optimal engine."""
    from nuoyi.converter import get_converter, DocxConverter

    if output_path is None:
        output_path = input_path.with_suffix(".md")

    print(f"\n{'=' * 60}")
    print(f"Processing: {input_path.name}")
    print(f"{'=' * 60}")

    # Detect PDF type
    is_digital = is_digital_pdf(input_path)

    if is_digital:
        print(f"Type: Digital PDF (has text)")
        print(f"Engine: pymupdf (fast, no GPU)")

        try:
            from nuoyi.converter import PyMuPDFConverter

            converter = PyMuPDFConverter()
            content, images = converter.convert_file(str(input_path))

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")

            print(f"✅ Success: {output_path}")
            return True

        except Exception as e:
            print(f"❌ Failed: {e}")
            return False
    else:
        print(f"Type: Scanned PDF (image-only)")
        print(f"Engine: marker (with OCR, low VRAM mode)")

        try:
            converter = get_converter(
                engine="marker",
                low_vram=True,
                device="auto",
            )
            content, images = converter.convert_file(str(input_path))

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")

            print(f"✅ Success: {output_path}")
            return True

        except Exception as e:
            print(f"❌ Failed: {e}")
            return False


def batch_convert_directory(
    input_dir: Path,
    output_dir: Path | None = None,
    recursive: bool = False,
) -> dict:
    """Batch convert all PDFs in directory with smart engine selection."""

    if output_dir is None:
        output_dir = input_dir

    # Find all PDF files
    from nuoyi.utils import find_documents

    files = find_documents(input_dir, recursive=recursive)
    pdf_files = [f for f in files if f.suffix.lower() == ".pdf"]

    print(f"\nFound {len(pdf_files)} PDF files to process")
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Recursive: {recursive}")

    results = {
        "total": len(pdf_files),
        "success": 0,
        "failed": 0,
        "digital": 0,
        "scanned": 0,
    }

    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}]")

        # Determine output path
        if recursive:
            try:
                rel_path = pdf_file.relative_to(input_dir)
                output_path = output_dir / rel_path.with_suffix(".md")
            except ValueError:
                output_path = output_dir / f"{pdf_file.stem}.md"
        else:
            output_path = output_dir / f"{pdf_file.stem}.md"

        # Check PDF type for statistics
        is_digital = is_digital_pdf(pdf_file)
        if is_digital:
            results["digital"] += 1
        else:
            results["scanned"] += 1

        # Convert
        success = convert_pdf_smart(pdf_file, output_path)

        if success:
            results["success"] += 1
        else:
            results["failed"] += 1

    # Print summary
    print(f"\n{'=' * 60}")
    print("Conversion Summary")
    print(f"{'=' * 60}")
    print(f"Total files:    {results['total']}")
    print(f"Digital PDFs:   {results['digital']}")
    print(f"Scanned PDFs:   {results['scanned']}")
    print(f"Success:        {results['success']}")
    print(f"Failed:         {results['failed']}")
    print(f"{'=' * 60}\n")

    return results


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python auto_convert.py <input_dir> [output_dir]")
        print("\nOptions:")
        print("  input_dir   Directory containing PDF files")
        print("  output_dir  Output directory (default: same as input)")
        print("\nExamples:")
        print("  python auto_convert.py ./pdfs")
        print("  python auto_convert.py ./pdfs ./output")
        sys.exit(1)

    input_dir = Path(sys.argv[1])

    if not input_dir.exists():
        print(f"Error: Directory not found: {input_dir}")
        sys.exit(1)

    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    # Ask about recursive
    recursive = False
    try:
        response = input("Process subdirectories recursively? [y/N]: ").strip().lower()
        recursive = response in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()

    results = batch_convert_directory(input_dir, output_dir, recursive)

    if results["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
