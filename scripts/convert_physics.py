#!/usr/bin/env python3
"""Batch convert all PDF/DOCX files in a directory tree to Markdown.

Preserves directory structure. Saves images in images/ subdir alongside each .md.
Uses marker engine for best formula/code/table quality.

Usage:
    python convert_batch.py <input_dir> <output_dir>

Example:
    python scripts/convert_batch.py /home/user/papers /home/user/papers_md
"""

from __future__ import annotations

import argparse
import gc
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

SUPPORTED_EXTENSIONS = (".pdf", ".docx")


def find_all_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for ext in SUPPORTED_EXTENSIONS:
        files.extend(root.rglob(f"**/*{ext}"))
    return sorted(files)


def get_output_path(input_file: Path, input_root: Path, output_root: Path) -> Path:
    rel = input_file.relative_to(input_root)
    return output_root / rel.with_suffix(".md")


def main():
    parser = argparse.ArgumentParser(
        description="批量转换目录下所有 PDF/DOCX 文件为 Markdown，保持目录结构",
    )
    parser.add_argument(
        "input_dir",
        type=Path,
        help="输入目录（包含 PDF/DOCX 文件）",
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        help="输出目录（Markdown 文件将镜像输入目录的层级结构）",
    )
    parser.add_argument(
        "--engine",
        default="marker",
        help="PDF 引擎 (marker/mineru/docling/pymupdf/pdfplumber/auto，默认: marker)",
    )
    parser.add_argument(
        "--force-ocr",
        action="store_true",
        help="强制对数字版 PDF 也使用 OCR",
    )
    parser.add_argument(
        "--langs",
        default="zh,en",
        help="语言代码，逗号分隔 (默认: zh,en)",
    )
    parser.add_argument(
        "--device",
        default="auto",
        help="计算设备 (auto/cuda/directml/rocm/cpu，默认: auto)",
    )
    parser.add_argument(
        "--low-vram",
        action="store_true",
        help="启用低显存模式（适合 4-6GB GPU）",
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="强制重新转换所有文件（不跳过已存在的输出）",
    )

    args = parser.parse_args()

    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not input_dir.is_dir():
        print(f"错误: 输入目录不存在: {input_dir}")
        sys.exit(1)

    from nuoyi import (
        api_convert_file,
        clear_converter_cache,
        get_gpu_memory_info,
        print_engines_info,
    )

    print("=" * 60)
    print("  NuoYi - 批量转换")
    print("=" * 60)
    print(f"  输入目录: {input_dir}")
    print(f"  输出目录: {output_dir}")
    print(f"  引擎: {args.engine}")
    print(f"  设备: {args.device}")
    if args.low_vram:
        print(f"  低显存模式: 已启用")
    print()

    print_engines_info()
    print()

    try:
        total_gpu, free_gpu = get_gpu_memory_info()
        if total_gpu > 0:
            print(f"  GPU 显存: {total_gpu:.0f}GB 总量 / {free_gpu:.0f}GB 可用")
        else:
            print("  GPU: 未检测到，使用 CPU")
    except Exception:
        print("  GPU: 检测失败，将使用 CPU")
    print()

    files = find_all_files(input_dir)
    total = len(files)
    print(f"  发现 {total} 个文件待转换")
    print("=" * 60)
    print()

    if total == 0:
        print("没有找到 PDF 或 DOCX 文件。")
        return

    success_count = 0
    fail_count = 0
    skip_count = 0
    start_time = time.time()

    for idx, f in enumerate(files, 1):
        out_path = get_output_path(f, input_dir, output_dir)
        rel_name = f.relative_to(input_dir)

        if not args.no_skip and out_path.exists():
            src_mtime = f.stat().st_mtime
            out_mtime = out_path.stat().st_mtime
            if src_mtime <= out_mtime:
                skip_count += 1
                print(f"[{idx}/{total}] {rel_name} - 跳过（已存在且为最新）")
                continue
            else:
                print(f"[{idx}/{total}] {rel_name} - 源文件已更新，重新转换...")
        else:
            print(f"[{idx}/{total}] {rel_name}")

        try:
            result = api_convert_file(
                f,
                output_path=out_path,
                engine=args.engine,
                force_ocr=args.force_ocr,
                langs=args.langs,
                device=args.device,
                low_vram=args.low_vram,
                use_cache=True,
            )
            if result.success:
                success_count += 1
                print(f"  ✓ 成功 -> {out_path}")
            else:
                fail_count += 1
                print(f"  ✗ 失败: {result.error}")
        except Exception as e:
            fail_count += 1
            print(f"  ✗ 异常: {e}")

        if idx % 10 == 0:
            try:
                clear_converter_cache()
            except Exception:
                pass
            try:
                gc.collect()
            except Exception:
                pass

    clear_converter_cache()
    gc.collect()

    elapsed = time.time() - start_time
    print()
    print("=" * 60)
    print(f"  转换完成: {success_count} 成功 / {skip_count} 跳过 / {fail_count} 失败")
    print(f"  耗时: {elapsed:.1f} 秒 ({elapsed/60:.1f} 分钟)")
    print(f"  输出目录: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
