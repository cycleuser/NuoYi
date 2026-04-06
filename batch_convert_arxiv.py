#!/usr/bin/env python3
"""
Batch convert arXiv PDFs to Markdown with GPU offloading.

Usage:
    python batch_convert_arxiv.py

Configuration:
    Edit INPUT_DIR and OUTPUT_DIR below to customize paths.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from nuoyi.api import convert_directory, clear_converter_cache

try:
    import torch
except ImportError:
    torch = None


def main():
    INPUT_DIR = "/home/fred/Documents/参考文献/arXiv_45000/pdfs/arxiv"
    OUTPUT_DIR = "/home/fred/Documents/参考文献/arXiv_45000/markdown"

    DEVICE = "cuda"
    LOW_VRAM = True
    RECURSIVE = False

    print("=" * 70)
    print("arXiv PDF Batch Conversion with GPU Offloading")
    print("=" * 70)
    print(f"Input:  {INPUT_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Device: {DEVICE}")
    print(f"Low VRAM Mode: {LOW_VRAM} (Layout GPU, OCR CPU)")
    print("=" * 70)
    print()

    input_path = Path(INPUT_DIR)
    if not input_path.exists():
        print(f"Error: Input directory not found: {INPUT_DIR}")
        sys.exit(1)

    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    if torch and torch.cuda.is_available():
        torch.cuda.empty_cache()
        print("[Memory] GPU cache cleared")

    result = convert_directory(
        INPUT_DIR,
        output_dir=OUTPUT_DIR,
        device=DEVICE,
        low_vram=LOW_VRAM,
        recursive=RECURSIVE,
    )

    print()
    print("=" * 70)
    print("Conversion Summary:")
    print("=" * 70)
    print(f"Total files:   {result.metadata.get('total', 0)}")
    print(f"Successful:    {result.data.get('success', 0)}")
    print(f"Failed:        {result.data.get('failed', 0)}")
    print("=" * 70)

    if result.data.get("failed", 0) > 0:
        print("\nFailed files (first 10):")
        failed_count = 0
        for file_info in result.data.get("files", []):
            if not file_info.get("success"):
                print(f"  ✗ {file_info['file']}")
                if file_info.get("error"):
                    print(f"    Error: {file_info['error'][:200]}")
                failed_count += 1
                if failed_count >= 10:
                    break

    if result.data.get("success", 0) > 0:
        print("\nSuccessful files (first 5):")
        success_count = 0
        for file_info in result.data.get("files", []):
            if file_info.get("success"):
                print(f"  ✓ {file_info['file']}")
                success_count += 1
                if success_count >= 5:
                    break

    clear_converter_cache()

    if torch and torch.cuda.is_available():
        torch.cuda.empty_cache()

    print()
    print("✅ Batch conversion completed!")

    if result.data.get("failed", 0) > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
