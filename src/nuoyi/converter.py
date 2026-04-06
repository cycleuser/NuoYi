"""
NuoYi - Document converters for PDF and DOCX to Markdown.

Supported PDF engines:

Local (free, offline):
- marker: Best quality, OCR, ~3GB models, GPU recommended
- mineru: Excellent for Chinese, OCR, ~1.5GB models, GPU optional
- docling: Balanced quality, ~1.5GB models, GPU optional
- pymupdf: Fastest, no GPU, digital PDFs only
- pdfplumber: Lightweight, good tables, no GPU

Cloud (API key required):
- llamaparse: LlamaIndex cloud service, excellent quality
- mathpix: Best for math/scientific documents

AMD GPU Support:
- ROCm: AMD GPUs on Linux (RX 500/5000/6000/7000 series)
- DirectML: AMD GPUs on Windows (all Radeon GPUs)
- Vulkan: Experimental cross-platform support

Acceleration backends:
- CUDA: NVIDIA GPUs
- ROCm: AMD GPUs (via HIP on Linux)
- DirectML: AMD/Intel/NVIDIA GPUs on Windows
- MPS: Apple Silicon Metal
- MLX: Apple MLX framework
- CPU: Universal fallback

Memory Optimization for Low VRAM (4-6GB):
- Automatic batch size reduction
- FP16/INT8 quantization
- Model offloading
- Aggressive garbage collection
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .utils import (
    DEFAULT_LANGS,
    LOW_VRAM_THRESHOLD_GB,
    VERY_LOW_VRAM_THRESHOLD_GB,
    aggressive_memory_cleanup,
    clean_markdown,
    clear_gpu_memory,
    enable_low_vram_mode,
    enable_very_low_vram_mode,
    get_current_memory_usage,
    get_gpu_memory_info,
    get_rocm_memory_info,
    is_amd_gpu_available,
    is_directml_available,
    is_rocm_available,
    select_device,
    setup_memory_optimization,
)

if TYPE_CHECKING:
    pass

setup_memory_optimization()

from docx import Document

SUPPORTED_ENGINES = [
    "auto",
    "marker",
    "mineru",
    "docling",
    "pymupdf",
    "pdfplumber",
    "llamaparse",
    "mathpix",
]

ENGINE_INFO = {
    "marker": {
        "type": "local",
        "gpu": "recommended",
        "models": "~3GB",
        "ocr": True,
        "notes": "Best quality, supports AMD via DirectML/ROCm",
        "amd_support": True,
    },
    "mineru": {
        "type": "local",
        "gpu": "optional",
        "models": "~1.5GB",
        "ocr": True,
        "notes": "Great for Chinese, supports AMD",
        "amd_support": True,
    },
    "docling": {
        "type": "local",
        "gpu": "optional",
        "models": "~1.5GB",
        "ocr": True,
        "notes": "Balanced, supports AMD",
        "amd_support": True,
    },
    "pymupdf": {
        "type": "local",
        "gpu": "no",
        "models": "none",
        "ocr": False,
        "notes": "Fastest, CPU only",
        "amd_support": True,
    },
    "pdfplumber": {
        "type": "local",
        "gpu": "no",
        "models": "none",
        "ocr": False,
        "notes": "Lightweight",
        "amd_support": True,
    },
    "llamaparse": {
        "type": "cloud",
        "gpu": "N/A",
        "models": "cloud",
        "ocr": True,
        "notes": "API key required",
        "amd_support": True,
    },
    "mathpix": {
        "type": "cloud",
        "gpu": "N/A",
        "models": "cloud",
        "ocr": True,
        "notes": "Math specialist",
        "amd_support": True,
    },
}


def _is_gpu_device(device: str) -> bool:
    return device in ("cuda", "rocm", "mps", "directml", "vulkan")


def _is_vulkan_device(device: str) -> bool:
    return device == "vulkan"


def _is_mlx_device(device: str) -> bool:
    return device == "mlx"


def _is_low_vram_device() -> bool:
    """Check if current GPU has low VRAM (<6GB)."""
    try:
        import torch

        if not torch.cuda.is_available():
            return False
        total, _ = get_gpu_memory_info()
        if total <= 0 and is_rocm_available():
            total, _ = get_rocm_memory_info()
        return total < LOW_VRAM_THRESHOLD_GB
    except Exception:
        return False


def _is_rocm_runtime() -> bool:
    """Check if running on ROCm runtime."""
    return is_rocm_available()


def _is_directml_runtime() -> bool:
    """Check if running on DirectML runtime."""
    return is_directml_available()


def _is_amd_gpu() -> bool:
    """Check if AMD GPU is available."""
    return is_amd_gpu_available()


def _get_amd_backend() -> str | None:
    """Get the AMD backend being used (rocm, directml, or None)."""
    if is_rocm_available():
        return "rocm"
    if is_directml_available():
        return "directml"
    return None


def _setup_amd_environment():
    """Set up environment for AMD GPU acceleration."""
    if is_rocm_available():
        os.environ["HSA_ENABLE_SDMA"] = "0"
        if "HSA_OVERRIDE_GFX_VERSION" not in os.environ:
            os.environ["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0"

    if is_directml_available():
        pass


class PyMuPDFConverter:
    """Fast PDF to Markdown using PyMuPDF4LLM.

    Type: Local, Free, Offline
    GPU: Not required
    OCR: No
    Install: pip install pymupdf4llm
    """

    def __init__(self, page_chunks: bool = True):
        self.page_chunks = page_chunks
        self._module = None

    def _get_module(self):
        if self._module is None:
            try:
                import pymupdf4llm

                self._module = pymupdf4llm
            except ImportError:
                raise ImportError("pip install pymupdf4llm")
        return self._module

    def convert_file(self, pdf_path: str) -> tuple[str, dict]:
        mod = self._get_module()
        md_text = mod.to_markdown(pdf_path, page_chunks=self.page_chunks)

        if isinstance(md_text, list):
            md_text = "\n\n".join(
                c.get("text", "") if isinstance(c, dict) else str(c) for c in md_text
            )

        return clean_markdown(md_text), {}

    @staticmethod
    def is_available() -> bool:
        try:
            import pymupdf4llm

            return True
        except ImportError:
            return False


class PDFPlumberConverter:
    """Lightweight PDF extraction.

    Type: Local, Free, Offline
    GPU: Not required
    OCR: No
    Install: pip install pdfplumber
    """

    def convert_file(self, pdf_path: str) -> tuple[str, dict]:
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("pip install pdfplumber")

        parts = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                tables = page.extract_tables()

                for table in tables or []:
                    if table:
                        parts.append(self._table_to_md(table))

                if text.strip():
                    parts.append(text.strip())

        return clean_markdown("\n\n".join(parts)), {}

    @staticmethod
    def _table_to_md(table: list[list]) -> str:
        if not table or not table[0]:
            return ""
        lines = []
        h = [str(c) if c else "" for c in table[0]]
        lines.append("| " + " | ".join(h) + " |")
        lines.append("| " + " | ".join(["---"] * len(h)) + " |")
        for row in table[1:]:
            cells = [str(c) if c else "" for c in row]
            cells.extend([""] * (len(h) - len(cells)))
            lines.append("| " + " | ".join(cells[: len(h)]) + " |")
        return "\n".join(lines)

    @staticmethod
    def is_available() -> bool:
        try:
            import pdfplumber

            return True
        except ImportError:
            return False


class DoclingConverter:
    """IBM Docling - balanced quality and speed.

    Type: Local, Free, Offline
    GPU: Optional
    OCR: Yes
    Models: ~1.5GB
    Install: pip install docling

    AMD Support: Works with ROCm (Linux) and DirectML (Windows)
    """

    def __init__(self, device: str = "auto"):
        self.device = select_device(device) if device != "auto" else "cpu"
        self._converter = None

    def _get_converter(self):
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter

                self._converter = DocumentConverter()
            except ImportError:
                raise ImportError("pip install docling")
        return self._converter

    def convert_file(self, pdf_path: str) -> tuple[str, dict]:
        conv = self._get_converter()
        result = conv.convert(pdf_path)

        if result and result.document:
            return clean_markdown(result.document.export_to_markdown()), {}

        return "", {}

    @staticmethod
    def is_available() -> bool:
        try:
            from docling.document_converter import DocumentConverter

            return True
        except ImportError:
            return False


class MinerUConverter:
    """MinerU - excellent for Chinese documents.

    Type: Local, Free, Offline
    GPU: Optional (CUDA/CPU)
    OCR: Yes
    Models: ~1.5GB
    Install: pip install magic-pdf[full]
    GitHub: https://github.com/opendatalab/MinerU

    AMD Support: Works with ROCm (Linux)

    Pros:
    - Excellent Chinese document support
    - Good table recognition
    - Smaller models than marker
    - Works on CPU
    """

    def __init__(self, device: str = "auto", langs: str = DEFAULT_LANGS):
        self.device = select_device(device) if device != "auto" else "cpu"
        self.langs = langs
        self._api = None

    def _get_api(self):
        if self._api is None:
            try:
                from magic_pdf.data.data_reader_writer import FileBasedDataReader
                from magic_pdf.data.dataset import PymuDocDataset
                from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze

                self._api = {
                    "FileBasedDataReader": FileBasedDataReader,
                    "PymuDocDataset": PymuDocDataset,
                    "doc_analyze": doc_analyze,
                }
            except ImportError:
                raise ImportError(
                    "Install MinerU:\n"
                    "  pip install magic-pdf[full]\n"
                    "See: https://github.com/opendatalab/MinerU"
                )
        return self._api

    def convert_file(self, pdf_path: str) -> tuple[str, dict]:
        api = self._get_api()

        reader = api["FileBasedDataReader"]()
        pdf_bytes = reader.read(pdf_path)

        ds = api["PymuDocDataset"](pdf_bytes)

        if ds.classify() == "ocr":
            infer_result = ds.apply_ocr()
        else:
            infer_result = ds.apply()

        content_list = infer_result.get_content_list(
            api["FileBasedDataReader"]().read(pdf_path),
            "",
        )

        md_text = content_list.get("markdown", "")
        images = content_list.get("images", {})

        return clean_markdown(md_text), images or {}

    @staticmethod
    def is_available() -> bool:
        try:
            from magic_pdf.data.dataset import PymuDocDataset

            return True
        except ImportError:
            return False


class MarkerPDFConverter:
    """marker-pdf - best quality output with AMD GPU support.

    Type: Local, Free, Offline
    GPU: Recommended (4GB+ VRAM), supports AMD via DirectML/ROCm
    OCR: Yes
    Models: ~3GB (full), ~1.5GB (minimal without OCR)
    Install: pip install marker-pdf

    Memory Management:
    - Lazy model loading (only loads when first file is processed)
    - Automatic memory cleanup after each file
    - OOM recovery with retry mechanism
    - Low VRAM optimization (<6GB)
    - Minimal model mode for digital PDFs (no OCR/table models)
    """

    def __init__(
        self,
        force_ocr: bool = False,
        page_range: str | None = None,
        langs: str = DEFAULT_LANGS,
        device: str = "auto",
        low_vram: bool = False,
        batch_size: int | None = None,
        disable_ocr_models: bool = False,
    ):
        self.force_ocr = force_ocr
        self.page_range = page_range
        self.langs = langs
        self.low_vram = low_vram
        self.batch_size = batch_size
        self.disable_ocr_models = disable_ocr_models
        self.converter = None
        self.artifact_dict = None
        self.device = self._select_device_with_memory_check(device)
        self._models_loaded = False
        self._file_count = 0

        if self.disable_ocr_models:
            print("[Memory] OCR models disabled - suitable for digital PDFs only")

        if self.low_vram:
            self._setup_low_vram_mode()

    def _select_device_with_memory_check(self, device: str) -> str:
        """Select device based on available memory."""
        selected = select_device(device)

        if selected == "cuda":
            try:
                total, free = get_gpu_memory_info()
                if total <= 0 and is_rocm_available():
                    total, free = get_rocm_memory_info()

                print(f"[Memory] GPU detected: {total:.1f}GB total, {free:.1f}GB free")

                if total <= LOW_VRAM_THRESHOLD_GB:
                    print(f"[Memory] Low VRAM mode auto-enabled (<{LOW_VRAM_THRESHOLD_GB}GB)")
                    self.low_vram = True
                elif total <= VERY_LOW_VRAM_THRESHOLD_GB:
                    print(
                        f"[Memory] Very low VRAM mode auto-enabled (<{VERY_LOW_VRAM_THRESHOLD_GB}GB)"
                    )
                    self.low_vram = True
                    enable_very_low_vram_mode()

            except Exception:
                pass

        return selected

    def _setup_low_vram_mode(self):
        """Setup optimizations for low VRAM."""
        print("[Memory] Enabling low VRAM optimizations...")

        enable_low_vram_mode()

        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.set_per_process_memory_fraction(0.7, 0)
                torch.cuda.empty_cache()
        except Exception:
            pass

        if self.batch_size is None:
            self.batch_size = 1

    def _load_models(self):
        """Lazy load models on first use."""
        if self._models_loaded:
            return

        if self.disable_ocr_models:
            print("[Memory] Loading marker-pdf minimal models (~1.5GB, no OCR)...")
        else:
            print("[Memory] Loading marker-pdf full models (~3GB)...")
        print("(First run downloads models)")

        try:
            total, free = get_gpu_memory_info()
            if total > 0:
                print(f"[Memory] Before loading: {free:.1f}GB free")

                min_required = 1.0 if self.disable_ocr_models else 2.0
                if free < min_required:
                    print(f"[Memory] WARNING: Low free memory ({free:.1f}GB)")
                    print("[Memory] Running aggressive cleanup...")
                    aggressive_memory_cleanup()

                    total, free = get_gpu_memory_info()
                    print(f"[Memory] After cleanup: {free:.1f}GB free")

                    min_required_after = 0.8 if self.disable_ocr_models else 1.5
                    if free < min_required_after:
                        raise RuntimeError(
                            f"Insufficient GPU memory: {free:.1f}GB free. "
                            f"Need at least {min_required_after}GB for model loading. "
                            f"Suggestions:\n"
                            f"  1. Use --device cpu\n"
                            f"  2. Use --engine pymupdf (no GPU)\n"
                            f"  3. Use --disable-ocr-models for digital PDFs\n"
                            f"  4. Close other GPU applications"
                        )
        except Exception:
            pass

        from marker.converters.pdf import PdfConverter

        if self.disable_ocr_models:
            self.artifact_dict = self._create_minimal_model_dict()
            print("[Memory] Minimal models loaded (layout only, ~1.5GB)")
        else:
            from marker.models import create_model_dict

            self.artifact_dict = create_model_dict()
            print("[Memory] Full models loaded (all features, ~3GB)")

        self.converter = PdfConverter(artifact_dict=self.artifact_dict)

        self._models_loaded = True

        try:
            mem_info = get_current_memory_usage()
            if mem_info.get("available"):
                print(
                    f"[Memory] After loading: {mem_info['allocated_gb']:.1f}GB used, {mem_info['free_gb']:.1f}GB free"
                )
        except Exception:
            pass

        print("[Memory] Models ready for conversion.")

    def _create_minimal_model_dict(self) -> dict:
        """Create minimal model dict without OCR models for digital PDFs.

        This loads only layout model (~1.5GB), saving ~1.5GB VRAM.
        Suitable for digital PDFs that don't need OCR.

        Warning: OCR-related features won't work with minimal models.
        """
        try:
            from surya.model.layout_predictor import LayoutPredictor

            print("[Memory] Creating minimal model dict (layout only)...")

            layout_model = LayoutPredictor(device=self.device if self.device != "auto" else None)

            return {
                "layout_model": layout_model,
                "recognition_model": None,
                "table_rec_model": None,
                "detection_model": None,
                "ocr_error_model": None,
            }
        except Exception as e:
            print(f"[Memory] Failed to create minimal models: {e}")
            print("[Memory] Falling back to full models...")
            from marker.models import create_model_dict

            return create_model_dict()

    def convert_file(self, pdf_path: str) -> tuple[str, dict]:
        """Convert PDF file with memory management and OOM handling."""
        self._load_models()

        max_retries = 2
        oom_count = 0

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    print(f"[Memory] Retry attempt {attempt}/{max_retries}")
                    aggressive_memory_cleanup()

                    mem_info = get_current_memory_usage()
                    if mem_info.get("available"):
                        print(f"[Memory] Free memory: {mem_info['free_gb']:.1f}GB")

                from marker.output import text_from_rendered

                rendered = self.converter(pdf_path)
                text, _, images = text_from_rendered(rendered)

                self._file_count += 1

                if self._file_count % 5 == 0 or self.low_vram:
                    clear_gpu_memory()

                    if self.low_vram:
                        aggressive_memory_cleanup()

                return clean_markdown(text), images or {}

            except RuntimeError as e:
                error_msg = str(e)

                if "out of memory" in error_msg.lower() or "CUDA out of memory" in error_msg:
                    oom_count += 1
                    print(f"[Memory] OOM error (attempt {oom_count}): {error_msg[:200]}...")

                    if attempt < max_retries:
                        print("[Memory] Clearing cache and retrying...")
                        aggressive_memory_cleanup()

                        import time

                        time.sleep(1)

                        continue
                    else:
                        print(f"[Memory] OOM after {max_retries} retries")
                        print("[Memory] Suggestions:")
                        print("  1. Use --low-vram flag")
                        print("  2. Use --device cpu")
                        print("  3. Use --engine pymupdf (no GPU required)")
                        print("  4. Close other GPU applications")
                        raise RuntimeError(
                            f"CUDA OOM after {max_retries} retries. "
                            f"Try: --low-vram, --device cpu, or --engine pymupdf"
                        ) from e
                else:
                    raise

            except Exception:
                raise

        raise RuntimeError("Unexpected error in convert_file")

    def cleanup(self):
        """Explicit cleanup of converter resources."""
        if self.converter is not None:
            try:
                del self.converter
                self.converter = None
            except Exception:
                pass

        if self.artifact_dict is not None:
            try:
                del self.artifact_dict
                self.artifact_dict = None
            except Exception:
                pass

        self._models_loaded = False
        aggressive_memory_cleanup()

        print("[Memory] Converter resources cleaned up")

    @staticmethod
    def is_available() -> bool:
        try:
            from marker.converters.pdf import PdfConverter

            return True
        except ImportError:
            return False


class LlamaParseConverter:
    """LlamaParse - cloud-based parsing by LlamaIndex.

    Type: Cloud (API key required)
    OCR: Yes
    Quality: Excellent
    Cost: Free tier available

    Setup:
        export LLAMA_CLOUD_API_KEY=your_key
    Install: pip install llama-parse
    Get API key: https://cloud.llamaindex.ai/
    """

    def __init__(self, api_key: str | None = None, result_type: str = "markdown"):
        self.api_key = api_key or os.environ.get("LLAMA_CLOUD_API_KEY")
        self.result_type = result_type
        self._parser = None

        if not self.api_key:
            raise ValueError(
                "LlamaParse requires API key. Set LLAMA_CLOUD_API_KEY env var or pass api_key param.\n"
                "Get free API key: https://cloud.llamaindex.ai/"
            )

    def _get_parser(self):
        if self._parser is None:
            try:
                from llama_parse import LlamaParse

                self._parser = LlamaParse(
                    api_key=self.api_key,
                    result_type=self.result_type,
                )
            except ImportError:
                raise ImportError("pip install llama-parse")
        return self._parser

    def convert_file(self, pdf_path: str) -> tuple[str, dict]:
        parser = self._get_parser()
        documents = parser.load_data(pdf_path)

        if documents:
            text = "\n\n".join(doc.text for doc in documents if doc.text)
            return clean_markdown(text), {}

        return "", {}

    @staticmethod
    def is_available() -> bool:
        try:
            from llama_parse import LlamaParse

            return bool(os.environ.get("LLAMA_CLOUD_API_KEY"))
        except ImportError:
            return False


class MathpixConverter:
    """Mathpix - best for math/scientific documents.

    Type: Cloud (API key required)
    OCR: Yes (specialized for math)
    Quality: Excellent for STEM documents
    Cost: Pay per page

    Setup:
        export MATHPIX_APP_ID=your_app_id
        export MATHPIX_APP_KEY=your_app_key
    Install: pip install mathpix
    Get API keys: https://mathpix.com/
    """

    def __init__(
        self,
        app_id: str | None = None,
        app_key: str | None = None,
        output_format: str = "md",
    ):
        self.app_id = app_id or os.environ.get("MATHPIX_APP_ID")
        self.app_key = app_key or os.environ.get("MATHPIX_APP_KEY")
        self.output_format = output_format

        if not self.app_id or not self.app_key:
            raise ValueError(
                "Mathpix requires APP_ID and APP_KEY. Set environment variables:\n"
                "  export MATHPIX_APP_ID=your_id\n"
                "  export MATHPIX_APP_KEY=your_key\n"
                "Get API keys: https://mathpix.com/"
            )

    def convert_file(self, pdf_path: str) -> tuple[str, dict]:
        try:
            import base64
            import json

            import requests
        except ImportError:
            raise ImportError("pip install requests")

        with open(pdf_path, "rb") as f:
            pdf_data = f.read()

        response = requests.post(
            "https://api.mathpix.com/v3/pdf",
            headers={
                "app_id": self.app_id,
                "app_key": self.app_key,
                "Content-type": "application/json",
            },
            json={
                "url": f"data:application/pdf;base64,{base64.b64encode(pdf_data).decode()}",
                "formats": [self.output_format],
            },
        )

        if response.status_code != 200:
            raise RuntimeError(f"Mathpix API error: {response.text}")

        result = response.json()
        pdf_id = result.get("pdf_id")

        if not pdf_id:
            raise RuntimeError(f"No PDF ID in response: {result}")

        status_url = f"https://api.mathpix.com/v3/pdf/{pdf_id}"

        import time

        for _ in range(60):
            time.sleep(2)
            status_resp = requests.get(
                status_url,
                headers={"app_id": self.app_id, "app_key": self.app_key},
            )
            status = status_resp.json()

            if status.get("status") == "completed":
                content_url = f"https://api.mathpix.com/v3/pdf/{pdf_id}.{self.output_format}"
                content_resp = requests.get(
                    content_url,
                    headers={"app_id": self.app_id, "app_key": self.app_key},
                )
                return clean_markdown(content_resp.text), {}

            if status.get("status") == "error":
                raise RuntimeError(f"Mathpix processing error: {status}")

        raise RuntimeError("Mathpix timeout (120s)")

    @staticmethod
    def is_available() -> bool:
        return bool(os.environ.get("MATHPIX_APP_ID") and os.environ.get("MATHPIX_APP_KEY"))


def select_engine(engine: str = "auto", has_gpu: bool = True) -> str:
    """Auto-select best available engine."""
    if engine != "auto":
        return engine

    if has_gpu:
        try:
            total, _ = get_gpu_memory_info()
            if total <= 0 and is_rocm_available():
                total, _ = get_rocm_memory_info()

            if total >= 4 and MarkerPDFConverter.is_available():
                backend_info = ""
                if _is_amd_gpu():
                    backend_info = f" (AMD via {_get_amd_backend() or 'auto'})"
                print(f"[Engine] Auto-selected: marker{backend_info}")
                return "marker"
        except Exception:
            pass

    if PyMuPDFConverter.is_available():
        print("[Engine] Auto-selected: pymupdf")
        return "pymupdf"

    if PDFPlumberConverter.is_available():
        print("[Engine] Auto-selected: pdfplumber")
        return "pdfplumber"

    return "marker"


def get_converter(
    engine: str = "auto",
    force_ocr: bool = False,
    page_range: str | None = None,
    langs: str = DEFAULT_LANGS,
    device: str = "auto",
    low_vram: bool = False,
    disable_ocr_models: bool = False,
    api_key: str | None = None,
    app_id: str | None = None,
    app_key: str | None = None,
):
    """Get PDF converter by engine name.

    Args:
        engine: Engine name (auto, marker, docling, pymupdf, pdfplumber, llamaparse, mathpix)
        force_ocr: Force OCR (marker only)
        page_range: Page range (marker only)
        langs: Languages for OCR
        device: GPU device (marker/docling)
            - auto: Auto-detect best device
            - cuda: NVIDIA GPU
            - rocm: AMD GPU on Linux
            - directml: AMD/Intel GPU on Windows
            - mps: Apple Metal
            - mlx: Apple MLX
            - cpu: CPU only
        low_vram: Low VRAM mode (<6GB)
        disable_ocr_models: Disable OCR models for marker (saves ~1.5GB, for digital PDFs)
        api_key: API key for LlamaParse
        app_id: App ID for Mathpix
        app_key: App key for Mathpix
    """
    has_gpu = device != "cpu" and (
        _is_gpu_device(device) or _is_mlx_device(device) or device == "auto"
    )

    selected = select_engine(engine, has_gpu)

    if selected == "llamaparse":
        if LlamaParseConverter.is_available() or api_key:
            print("[Converter] Using LlamaParse (cloud)")
            return LlamaParseConverter(api_key=api_key)
        raise ValueError(
            "LlamaParse requires API key.\n"
            "Set: export LLAMA_CLOUD_API_KEY=your_key\n"
            "Get key: https://cloud.llamaindex.ai/"
        )

    if selected == "mathpix":
        if MathpixConverter.is_available() or (app_id and app_key):
            print("[Converter] Using Mathpix (cloud)")
            return MathpixConverter(app_id=app_id, app_key=app_key)
        raise ValueError(
            "Mathpix requires APP_ID and APP_KEY.\n"
            "Set: export MATHPIX_APP_ID=your_id\n"
            "Set: export MATHPIX_APP_KEY=your_key\n"
            "Get keys: https://mathpix.com/"
        )

    if selected == "pymupdf":
        if PyMuPDFConverter.is_available():
            print("[Converter] Using PyMuPDF4LLM (fast, offline)")
            return PyMuPDFConverter()

    if selected == "pdfplumber":
        if PDFPlumberConverter.is_available():
            print("[Converter] Using pdfplumber (lightweight)")
            return PDFPlumberConverter()

    if selected == "docling":
        if DoclingConverter.is_available():
            amd_info = ""
            if _is_amd_gpu():
                amd_info = f" (AMD via {_get_amd_backend()})"
            print(f"[Converter] Using Docling (balanced){amd_info}")
            return DoclingConverter(device=device)

    if selected == "mineru":
        if MinerUConverter.is_available():
            amd_info = ""
            if _is_amd_gpu():
                amd_info = f" (AMD via {_get_amd_backend()})"
            print(f"[Converter] Using MinerU (great for Chinese){amd_info}")
            return MinerUConverter(device=device, langs=langs)

    if selected == "marker":
        if MarkerPDFConverter.is_available():
            amd_info = ""
            if _is_amd_gpu():
                backend = _get_amd_backend()
                amd_info = f" (AMD via {backend.upper()})" if backend else ""

            vram_info = ""
            if low_vram:
                vram_info = " [Low VRAM mode]"

            ocr_info = ""
            if disable_ocr_models:
                ocr_info = " [No OCR models - digital PDFs only]"

            print(f"[Converter] Using marker-pdf (best quality){amd_info}{vram_info}{ocr_info}")
            return MarkerPDFConverter(
                force_ocr=force_ocr,
                page_range=page_range,
                langs=langs,
                device=device,
                low_vram=low_vram,
                disable_ocr_models=disable_ocr_models,
            )

    raise ImportError(
        "No PDF converter available. Install one of:\n"
        "  pip install marker-pdf         # Best quality, GPU\n"
        "  pip install magic-pdf[full]    # MinerU, Chinese docs\n"
        "  pip install docling            # Balanced, ~1.5GB\n"
        "  pip install pymupdf4llm        # Fastest, no GPU\n"
        "  pip install pdfplumber         # Lightweight\n"
        "  pip install llama-parse        # Cloud, API key\n"
        "  pip install requests           # For Mathpix cloud\n"
        "\nFor AMD GPUs:\n"
        "  Windows: pip install torch-directml  # DirectML support\n"
        "  Linux: Use ROCm PyTorch build        # ROCm support\n"
    )


def list_available_engines() -> dict[str, dict]:
    """List all available engines with their status."""
    engines = {}

    for name, info in ENGINE_INFO.items():
        available = False
        if name == "marker":
            available = MarkerPDFConverter.is_available()
        elif name == "mineru":
            available = MinerUConverter.is_available()
        elif name == "docling":
            available = DoclingConverter.is_available()
        elif name == "pymupdf":
            available = PyMuPDFConverter.is_available()
        elif name == "pdfplumber":
            available = PDFPlumberConverter.is_available()
        elif name == "llamaparse":
            available = LlamaParseConverter.is_available()
        elif name == "mathpix":
            available = MathpixConverter.is_available()

        engines[name] = {**info, "available": available}

    return engines


def print_engines_info():
    """Print engine comparison table."""
    engines = list_available_engines()

    print("\n=== PDF Conversion Engines ===\n")
    print(f"{'Engine':<12} {'Type':<8} {'GPU':<12} {'Available':<10} {'Notes'}")
    print("-" * 70)

    for name, info in engines.items():
        avail = "[OK]" if info["available"] else "[--]"
        gpu = info.get("gpu", "N/A")
        notes = info.get("notes", "")
        amd = " [AMD]" if info.get("amd_support") else ""

        print(f"{name:<12} {info['type']:<8} {gpu:<12} {avail:<10} {notes}{amd}")

    print("\n" + "=" * 70)
    print("AMD GPU Support:")
    print("  Windows: Use --device directml for AMD Radeon GPUs")
    print("  Linux:   Use --device rocm for AMD Radeon GPUs")
    print("  Low VRAM: Use --low-vram for 4-6GB GPUs")
    print("=" * 70)

    print("\nInstall commands:")
    print("  pip install marker-pdf         # Best quality")
    print("  pip install magic-pdf[full]    # MinerU (Chinese docs)")
    print("  pip install docling            # Balanced")
    print("  pip install pymupdf4llm        # Fastest")
    print("  pip install pdfplumber         # Lightweight")
    print("  pip install llama-parse        # Cloud (LLAMA_CLOUD_API_KEY)")
    print("  pip install requests           # For Mathpix (MATHPIX_APP_ID/KEY)")

    print("\nAMD GPU Setup:")
    print("  Windows: pip install torch-directml")
    print("  Linux:   Install ROCm PyTorch from https://pytorch.org/get-started/locally/")
    print(
        "           pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/rocm6.2"
    )


class DocxConverter:
    """DOCX to Markdown using python-docx."""

    def convert_file(self, docx_path: str) -> str:
        doc = Document(docx_path)
        parts = []

        for element in doc.element.body:
            if element.tag.endswith("p"):
                for para in doc.paragraphs:
                    if para._element == element:
                        md = self._para_to_md(para)
                        if md:
                            parts.append(md)
                        break
            elif element.tag.endswith("tbl"):
                for table in doc.tables:
                    if table._element == element:
                        md = self._table_to_md(table)
                        if md:
                            parts.append(md)
                        break

        return "\n\n".join(parts)

    @staticmethod
    def _para_to_md(para) -> str:
        text = para.text.strip()
        if not text:
            return ""

        style = para.style.name.lower() if para.style else ""

        if "heading 1" in style or style == "title":
            return f"# {text}"
        if "heading 2" in style:
            return f"## {text}"
        if "heading 3" in style:
            return f"### {text}"
        if "heading 4" in style:
            return f"#### {text}"
        if "list" in style:
            return f"- {text}"

        parts = []
        for run in para.runs:
            t = run.text
            if not t:
                continue
            if run.bold:
                t = f"**{t}**"
            if run.italic:
                t = f"*{t}*"
            parts.append(t)

        return "".join(parts) if parts else text

    @staticmethod
    def _table_to_md(table) -> str:
        rows = []
        for row in table.rows:
            cells = [c.text.strip().replace("\n", " ") for c in row.cells]
            rows.append(cells)

        if not rows:
            return ""

        lines = []
        lines.append("| " + " | ".join(rows[0]) + " |")
        lines.append("| " + " | ".join(["---"] * len(rows[0])) + " |")
        for row in rows[1:]:
            row.extend([""] * (len(rows[0]) - len(row)))
            lines.append("| " + " | ".join(row[: len(rows[0])]) + " |")

        return "\n".join(lines)
