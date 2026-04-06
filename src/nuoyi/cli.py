"""
NuoYi - Command-line interface for document conversion.

Supported PDF engines:

Local (free, offline):
- marker: Best quality, OCR, GPU recommended, ~3GB models
- mineru: Excellent for Chinese, OCR, GPU optional, ~1.5GB
- docling: Balanced quality, OCR, GPU optional, ~1.5GB
- pymupdf: Fastest, no GPU, no OCR
- pdfplumber: Lightweight, good tables, no GPU, no OCR

Cloud (API key required):
- llamaparse: LlamaIndex cloud, excellent quality
- mathpix: Best for math/scientific documents

AMD GPU Support:
- Windows: Use --device directml (AMD Radeon GPUs)
- Linux: Use --device rocm (AMD Radeon GPUs)
- Low VRAM: Use --low-vram for 4-6GB GPUs

Acceleration backends:
- CUDA: NVIDIA GPUs
- ROCm: AMD GPUs (Linux)
- DirectML: AMD/Intel GPUs (Windows)
- MPS: Apple Metal (macOS)
- MLX: Apple MLX (macOS)
- CPU: Universal fallback
"""

import argparse
import platform
import sys
from pathlib import Path

from . import __version__
from .converter import DocxConverter, get_converter
from .utils import (
    DEFAULT_LANGS,
    SUPPORTED_DEVICES,
    SUPPORTED_ENGINES,
    SUPPORTED_LANGUAGES,
    is_amd_gpu_available,
    list_available_devices,
    print_device_info,
    prompt_kill_cuda_processes,
    save_images_and_update_markdown,
    setup_memory_optimization,
)


def convert_single_file(
    input_path: Path,
    output_path: Path,
    force_ocr: bool,
    page_range: str | None,
    langs: str,
    device: str = "auto",
    low_vram: bool = False,
    engine: str = "auto",
    disable_ocr_models: bool = False,
):
    """Convert a single PDF or DOCX file."""
    suffix = input_path.suffix.lower()
    images = {}

    if suffix == ".pdf":
        converter = get_converter(
            engine=engine,
            force_ocr=force_ocr,
            page_range=page_range,
            langs=langs,
            device=device,
            low_vram=low_vram,
            disable_ocr_models=disable_ocr_models,
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
    page_range: str | None,
    langs: str,
    device: str = "auto",
    low_vram: bool = False,
    engine: str = "auto",
    recursive: bool = False,
    disable_ocr_models: bool = False,
):
    """Batch convert all PDF/DOCX files in a directory with optimized memory."""

    from .api import clear_converter_cache
    from .api import convert_directory as api_convert_directory

    result = api_convert_directory(
        input_dir=input_dir,
        output_dir=output_dir,
        force_ocr=force_ocr,
        page_range=page_range,
        langs=langs,
        device=device,
        recursive=recursive,
        disable_ocr_models=disable_ocr_models,
    )

    if not result.success:
        print("\nConversion completed with errors:")
        for file_result in result.data.get("files", []):
            if not file_result["success"]:
                print(f"  ✗ {file_result['file']}: {file_result['error']}")

    if result.metadata.get("recursive"):
        print("Output directory structure preserved.")

    clear_converter_cache()


DEVICE_DESCRIPTIONS = {
    "cuda": "NVIDIA GPUs (CUDA)",
    "rocm": "AMD GPUs - Linux only (ROCm/HIP)",
    "directml": "AMD/Intel/NVIDIA GPUs - Windows only",
    "mps": "Apple Silicon Metal (macOS)",
    "mlx": "Apple MLX framework (macOS)",
    "vulkan": "Cross-platform GPU (experimental)",
    "openvino": "Intel CPU/GPU optimization",
    "cpu": "CPU (universal fallback)",
}

ENGINE_DESCRIPTIONS = {
    "marker": "Best quality, OCR, GPU recommended (~3GB) [AMD: DirectML/ROCm]",
    "mineru": "Great for Chinese, OCR, GPU optional (~1.5GB) [AMD: ROCm]",
    "docling": "Balanced, OCR, GPU optional (~1.5GB) [AMD: DirectML/ROCm]",
    "pymupdf": "Fastest, no GPU, no OCR",
    "pdfplumber": "Lightweight, good tables, no GPU, no OCR",
    "llamaparse": "Cloud, API key (LLAMA_CLOUD_API_KEY)",
    "mathpix": "Cloud, math specialist, API key required",
}


def main():
    """Main entry point for NuoYi CLI."""
    parser = argparse.ArgumentParser(
        prog="nuoyi",
        description="NuoYi - Convert PDF/DOCX to Markdown (with AMD GPU support)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  nuoyi paper.pdf                        # Auto-select engine
  nuoyi paper.pdf --engine pymupdf       # Fast, no GPU
  nuoyi paper.pdf --engine marker        # Best quality
  nuoyi paper.pdf --engine mineru        # Chinese docs
  nuoyi paper.pdf --engine llamaparse    # Cloud (needs API key)
  nuoyi paper.pdf --device cuda          # Use NVIDIA GPU
  nuoyi paper.pdf --device directml      # Use AMD GPU on Windows
  nuoyi paper.pdf --device rocm          # Use AMD GPU on Linux
  nuoyi paper.pdf --low-vram             # Low VRAM mode (4-6GB)
  nuoyi ./papers --batch                 # Batch directory
  nuoyi --gui                            # Launch GUI
  nuoyi --web                            # Launch Web Interface
  nuoyi --web --port 8080                # Web on port 8080
  nuoyi --list-engines                   # Show all engines
  nuoyi --amd-info                       # Show AMD GPU info

PDF Engines (Local, Free):
  marker     Best quality, OCR, layout detection
             Install: pip install marker-pdf
             AMD Support: DirectML (Windows) / ROCm (Linux RDNA only)
  mineru     Excellent for Chinese documents
             Install: pip install magic-pdf[full]
  docling    Balanced quality, IBM
             Install: pip install docling
  pymupdf    Fastest, no OCR, digital PDFs
             Install: pip install pymupdf4llm
  pdfplumber Lightweight, good tables
             Install: pip install pdfplumber

PDF Engines (Cloud, API key):
  llamaparse LlamaIndex cloud, excellent quality
             Set: export LLAMA_CLOUD_API_KEY=xxx
  mathpix    Math/scientific documents
             Set: export MATHPIX_APP_ID=xxx MATHPIX_APP_KEY=xxx

AMD GPU Support (IMPORTANT for RX580/RX590):
  Windows:   Use --device directml (ONLY option for AMD on Windows)
             RX580, RX590, RX 6000/7000 series all work with DirectML
             Install: pip install torch-directml
  
  Linux:     Use --device rocm (ONLY for RDNA GPUs: RX 5000/6000/7000)
             RX580/RX590 (Polaris) are NOT supported by ROCm!
             For RX580/RX590 on Linux: Use CPU or pymupdf engine

  Low VRAM:  Use --low-vram for 4-6GB GPUs
             RX580 8GB should work without --low-vram
             RX580 4GB needs --low-vram flag

DirectML Installation (Windows AMD):
  pip install torch-directml
  nuoyi input.pdf --device directml

Low VRAM Tips (4-6GB):
  - Use --low-vram flag
  - Close other GPU applications
  - Consider pymupdf for simpler documents
        """,
    )

    parser.add_argument("input", nargs="?", help="Input PDF/DOCX file or directory")
    parser.add_argument("-o", "--output", help="Output file/directory path")
    parser.add_argument("--force-ocr", action="store_true", help="Force OCR (marker engine)")
    parser.add_argument("--page-range", help="Page range, e.g. '0-5,10,15-20'")
    parser.add_argument(
        "--langs", default=DEFAULT_LANGS, help=f"Languages (default: {DEFAULT_LANGS})"
    )
    parser.add_argument("--list-langs", action="store_true", help="List supported languages")
    parser.add_argument("--list-devices", action="store_true", help="List available devices")
    parser.add_argument("--list-engines", action="store_true", help="List available PDF engines")
    parser.add_argument("--amd-info", action="store_true", help="Show detailed AMD GPU information")
    parser.add_argument("--batch", action="store_true", help="Batch process directory")
    parser.add_argument("-r", "--recursive", action="store_true", help="Recursive directory scan")
    parser.add_argument(
        "--engine",
        default="auto",
        choices=SUPPORTED_ENGINES,
        help="PDF engine (auto/marker/mineru/docling/pymupdf/pdfplumber/llamaparse/mathpix)",
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=SUPPORTED_DEVICES,
        help="GPU device: cuda (NVIDIA), directml (AMD Windows), rocm (AMD Linux), mps/mlx (Apple), cpu",
    )
    parser.add_argument("--low-vram", action="store_true", help="Low VRAM mode (4-6GB GPUs)")
    parser.add_argument(
        "--disable-ocr-models",
        action="store_true",
        help="Disable OCR models for marker (saves ~1.5GB VRAM, for digital PDFs only)",
    )
    parser.add_argument("--gui", action="store_true", help="Launch GUI")
    parser.add_argument("--web", action="store_true", help="Launch Web Interface")
    parser.add_argument("--host", default="0.0.0.0", help="Web server host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5000, help="Web server port (default: 5000)")
    parser.add_argument("-V", "--version", action="version", version=f"NuoYi {__version__}")

    args = parser.parse_args()

    if args.list_langs:
        print("Supported languages:")
        for code, name in SUPPORTED_LANGUAGES.items():
            print(f"  {code:4s}  {name}")
        sys.exit(0)

    if args.amd_info:
        print("\n" + "=" * 70)
        print("AMD GPU Information")
        print("=" * 70)

        try:
            from .directml_backend import (
                get_directml_install_instructions,
                get_polaris_vram,
                is_polaris_gpu,
                setup_directml_for_torch,
                test_directml,
            )

            if platform.system().lower() == "windows":
                print("\n[DirectML Status]")
                config = setup_directml_for_torch()
                print(f"  Available: {config.get('available', False)}")
                if config.get("available"):
                    print(f"  Device: {config.get('device_name', 'Unknown')}")
                    print(f"  VRAM: {config.get('vram_gb', 0):.1f}GB")
                    print(f"  Is Polaris: {config.get('is_polaris', False)}")

                    if config.get("is_polaris"):
                        print("\n[Polaris GPU Detected (RX 400/500 series)]")
                        print(f"  This GPU: {config.get('device_name', 'Unknown')}")
                        print(f"  VRAM: {config.get('vram_gb', 0):.1f}GB")
                        print("  ROCm Support: NO (Polaris GPUs not supported)")
                        print("  DirectML: REQUIRED for GPU acceleration")
                        print("  Installation: pip install torch-directml")

                    print("\n[DirectML Test]")
                    test_directml()
                else:
                    print(f"  Error: {config.get('error', 'Unknown error')}")
                    print(get_directml_install_instructions())
            else:
                print("\n[Linux System]")
                print("  For AMD GPUs: Use --device rocm (RDNA GPUs only)")
                print("  RX580/RX590: NOT supported by ROCm (Polaris architecture)")
                print("  For RX580/RX590: Use CPU mode or pymupdf engine")

        except ImportError:
            print("DirectML backend module not available.")

        print("\n[General AMD GPU Info]")
        if is_amd_gpu_available():
            print("  AMD GPU detected!")
            from .utils import get_amd_gpu_info

            amd_info = get_amd_gpu_info()
            print(f"  Backend: {amd_info.get('backend', 'Unknown')}")
            print(f"  Name: {amd_info.get('name', 'Unknown')}")
            print(f"  VRAM: {amd_info.get('vram_gb', 0):.1f}GB")
        else:
            print("  No AMD GPU detected via standard APIs.")

        print_device_info()
        print("=" * 70)
        sys.exit(0)

    if args.list_engines or args.list_devices:
        from .converter import list_available_engines

        engines = list_available_engines()
        print("\n=== Available PDF Engines ===\n")
        print(f"{'Engine':<12} {'Type':<8} {'GPU':<12} {'Status':<10} Notes")
        print("-" * 80)
        for name, info in engines.items():
            status = "[OK]" if info["available"] else "[--]"
            gpu = info.get("gpu", "N/A")
            notes = info.get("notes", "")
            amd = " [AMD]" if info.get("amd_support") else ""
            print(f"{name:<12} {info['type']:<8} {gpu:<12} {status:<10} {notes}{amd}")

        print("\n" + "=" * 80)
        print("AMD GPU Support:")
        print("  Windows: Use --device directml for AMD Radeon GPUs")
        print("  Linux:   Use --device rocm for AMD Radeon GPUs")
        print("  Low VRAM: Use --low-vram for 4-6GB GPUs")
        print("=" * 80)

        print("\nInstall commands:")
        print("  pip install marker-pdf         # Best quality")
        print("  pip install magic-pdf[full]    # MinerU (Chinese docs)")
        print("  pip install docling            # Balanced")
        print("  pip install pymupdf4llm        # Fastest")
        print("  pip install pdfplumber         # Lightweight")
        print("  pip install llama-parse        # Cloud (LLAMA_CLOUD_API_KEY)")
        print("  pip install requests           # For Mathpix")

        print("\nAMD GPU Setup:")
        print("  Windows: pip install torch-directml")
        print(
            "  Linux:   pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/rocm6.2"
        )

        if args.list_devices:
            print("\n=== Acceleration Devices ===\n")
            available = list_available_devices()
            device_order = ["cuda", "rocm", "directml", "mps", "mlx", "vulkan", "openvino", "cpu"]
            for device in device_order:
                status = "[OK]" if device in available else "[--]"
                desc = DEVICE_DESCRIPTIONS.get(device, "")
                print(f"  {status} {device:10s}  {desc}")
            print_device_info()

        sys.exit(0)

    if args.gui:
        from .gui import run_gui

        run_gui()

    if args.web:
        from .web import run_web

        run_web(host=args.host, port=args.port)

    if not args.input:
        parser.print_help()
        print("\nError: Input file or directory required.")
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Path not found: {args.input}")
        sys.exit(1)

    force_ocr = args.force_ocr
    page_range = args.page_range or None
    langs = args.langs
    device = args.device
    low_vram = args.low_vram
    engine = args.engine
    disable_ocr_models = args.disable_ocr_models

    if disable_ocr_models and force_ocr:
        print("Warning: --disable-ocr-models conflicts with --force-ocr")
        print("         OCR models disabled, force_ocr will be ignored")
        force_ocr = False

    setup_memory_optimization(low_vram=low_vram)

    should_check_cuda = device in ("auto", "cuda") and engine in (
        "auto",
        "marker",
        "mineru",
        "docling",
    )
    if should_check_cuda:
        min_vram = 2.0 if low_vram else 4.0
        if not prompt_kill_cuda_processes(min_free_vram_gb=min_vram):
            print("Aborted.")
            sys.exit(0)

    if input_path.is_file():
        output_path = Path(args.output) if args.output else input_path.with_suffix(".md")

        print(f"Input:  {input_path}")
        print(f"Output: {output_path}")
        print(f"Engine: {engine}")
        if engine in ("auto", "marker"):
            print(f"Device: {device}")
            if low_vram:
                print("Low VRAM: True (optimized for 4-6GB)")
            if disable_ocr_models:
                print("OCR Models: Disabled (digital PDFs only, saves ~1.5GB)")
        if force_ocr:
            print("Force OCR: True")
        if page_range:
            print(f"Page Range: {page_range}")
        print()

        convert_single_file(
            input_path,
            output_path,
            force_ocr,
            page_range,
            langs,
            device,
            low_vram,
            engine,
            disable_ocr_models,
        )

    elif input_path.is_dir():
        if not args.batch:
            print(f"Error: {input_path} is a directory. Use --batch to process.")
            sys.exit(1)

        output_dir = Path(args.output) if args.output else input_path
        print(f"Input dir:  {input_path}")
        print(f"Output dir: {output_dir}")
        print(f"Engine: {engine}")
        if engine in ("auto", "marker"):
            print(f"Device: {device}")
            if low_vram:
                print("Low VRAM: True (optimized for 4-6GB)")
            if disable_ocr_models:
                print("OCR Models: Disabled (digital PDFs only, saves ~1.5GB)")
        if args.recursive:
            print("Recursive: True")
        print()

        convert_directory(
            input_path,
            output_dir,
            force_ocr,
            page_range,
            langs,
            device,
            low_vram,
            engine,
            args.recursive,
            disable_ocr_models,
        )

    else:
        print(f"Error: Invalid path: {args.input}")
        sys.exit(1)


if __name__ == "__main__":
    main()
