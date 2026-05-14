#!/usr/bin/env python3
"""Convert Essential-GraphRAG.pdf to perfect Markdown using Doc2X.

Features:
- Doc2X cloud API with LaTeX formula support
- Images automatically downloaded from CDN and saved to ./images/
- All <img> tags in markdown replaced with local references
- Quality verification after conversion

Usage:
    python convert_graphrag.py
    python convert_graphrag.py --pdf /path/to/Essential-GraphRAG.pdf
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

API_KEY = "sk-gud34s0k89fpzw33ie9a8z9ekjlkem1b"


def convert(pdf_path: str, output_dir: str | None = None) -> bool:
    from nuoyi.converter import Doc2xConverter, aggregate_markdown, split_pdf
    from nuoyi.utils import clean_markdown, save_images_and_update_markdown

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        return False

    if output_dir is None:
        output_dir = str(pdf_path.parent)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"Doc2X Conversion: {pdf_path.name}")
    print(f"{'=' * 60}")

    os.environ["DOC2X_API_KEY"] = API_KEY

    import fitz
    doc = fitz.open(str(pdf_path))
    page_count = len(doc)
    doc.close()

    print(f"Pages: {page_count}")

    max_pages = 50
    needs_split = page_count > max_pages

    if needs_split:
        print(f"Splitting into chunks of {max_pages} pages...")
        split_files = split_pdf(str(pdf_path), max_pages=max_pages)
    else:
        split_files = [str(pdf_path)]

    results = []
    for i, chunk_path in enumerate(split_files, 1):
        print(f"\n[Chunk {i}/{len(split_files)}] Processing {Path(chunk_path).name}...")
        converter = Doc2xConverter(api_key=API_KEY, formula="latex")
        md_text, images = converter.convert_file(chunk_path)
        results.append((md_text, images))
        print(f"  Chars: {len(md_text):,}, Images: {len(images)}")

    if len(results) > 1:
        print(f"\nAggregating {len(results)} chunks...")
        final_md, all_images = aggregate_markdown(results)
    else:
        final_md, all_images = results[0]

    final_md = clean_markdown(final_md)

    output_stem = pdf_path.stem
    output_md = output_dir / f"{output_stem}_doc2x.md"

    if all_images:
        print(f"\nSaving {len(all_images)} images to images/...")
        final_md = save_images_and_update_markdown(
            final_md, all_images, output_dir, "images"
        )

    output_md.write_text(final_md, encoding="utf-8")

    formula_inline = final_md.count("\\(") // 2
    formula_display = final_md.count("\\[") // 2
    formula_dollar = final_md.count("$") // 2
    image_count = len(all_images)

    print(f"\n{'=' * 60}")
    print("Conversion Complete!")
    print(f"{'=' * 60}")
    print(f"  Output:       {output_md}")
    print(f"  Pages:        {page_count}")
    print(f"  Size:         {len(final_md):,} chars")
    print(f"  Images:       {image_count}")
    print(f"  Inline math:  ~{formula_inline}")
    print(f"  Display math: ~{formula_display}")
    print(f"  Dollar math:  ~{formula_dollar}")
    print(f"  Images dir:   {output_dir / 'images' if all_images else 'N/A'}")
    print(f"{'=' * 60}")

    print("\nQuality Check:")
    checks = {
        "Has substantial content": len(final_md) > 1000,
        "Has headings (#)": "#" in final_md,
        "Has LaTeX formulas": "\\(" in final_md or "\\[" in final_md or "$" in final_md,
        "Images saved locally": "images/" in final_md if all_images else True,
        "No external CDN URLs": "noedgeai.com" not in final_md if all_images else True,
    }
    all_passed = True
    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
        print(f"  [{status}] {check}")

    print(f"\n  Preview:\n{'-' * 40}")
    print(final_md[:600])
    print(f"{'-' * 40}...")

    return all_passed


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert PDF to Markdown via Doc2X")
    parser.add_argument(
        "--pdf",
        default="/Users/fred/Documents/GitHub/Working/Essential-GraphRAG.pdf",
        help="Path to PDF file",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: same as PDF)",
    )
    args = parser.parse_args()

    success = convert(args.pdf, args.output_dir)
    sys.exit(0 if success else 1)
