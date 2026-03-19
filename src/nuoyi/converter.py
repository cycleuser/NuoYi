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

Acceleration backends (for marker/mineru/docling):
- CUDA: NVIDIA GPUs
- ROCm: AMD GPUs (via HIP)
- MPS: Apple Silicon Metal
- MLX: Apple MLX framework
- CPU: Universal fallback
"""

from __future__ import annotations

import gc
import os
from typing import TYPE_CHECKING

from .utils import (
    DEFAULT_LANGS,
    clean_markdown,
    clear_gpu_memory,
    clear_mlx_memory,
    enable_low_vram_mode,
    get_gpu_memory_info,
    get_recommended_batch_size,
    select_device,
    setup_memory_optimization,
)

if TYPE_CHECKING:
    from pathlib import Path

setup_memory_optimization()

import fitz
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
        "notes": "Best quality",
    },
    "mineru": {
        "type": "local",
        "gpu": "optional",
        "models": "~1.5GB",
        "ocr": True,
        "notes": "Great for Chinese",
    },
    "docling": {
        "type": "local",
        "gpu": "optional",
        "models": "~1.5GB",
        "ocr": True,
        "notes": "Balanced",
    },
    "pymupdf": {"type": "local", "gpu": "no", "models": "none", "ocr": False, "notes": "Fastest"},
    "pdfplumber": {
        "type": "local",
        "gpu": "no",
        "models": "none",
        "ocr": False,
        "notes": "Lightweight",
    },
    "llamaparse": {
        "type": "cloud",
        "gpu": "N/A",
        "models": "cloud",
        "ocr": True,
        "notes": "API key required",
    },
    "mathpix": {
        "type": "cloud",
        "gpu": "N/A",
        "models": "cloud",
        "ocr": True,
        "notes": "Math specialist",
    },
}

LOW_VRAM_THRESHOLD_GB = 8.0


def _is_gpu_device(device: str) -> bool:
    return device in ("cuda", "rocm", "mps")


def _is_mlx_device(device: str) -> bool:
    return device == "mlx"


def _is_low_vram_device() -> bool:
    try:
        import torch

        if not torch.cuda.is_available():
            return False
        total, _ = get_gpu_memory_info()
        return total < LOW_VRAM_THRESHOLD_GB
    except Exception:
        return False


def _is_rocm_runtime() -> bool:
    try:
        import torch

        return hasattr(torch.version, "hip") and torch.version.hip is not None
    except Exception:
        return False


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
    """marker-pdf - best quality output.

    Type: Local, Free, Offline
    GPU: Recommended (4GB+ VRAM)
    OCR: Yes
    Models: ~3GB
    Install: pip install marker-pdf
    """

    def __init__(
        self,
        force_ocr: bool = False,
        page_range: str | None = None,
        langs: str = DEFAULT_LANGS,
        device: str = "auto",
        low_vram: bool = False,
        batch_size: int | None = None,
    ):
        self.force_ocr = force_ocr
        self.page_range = page_range
        self.langs = langs
        self.low_vram = low_vram
        self.batch_size = batch_size
        self.device = select_device(device)
        self.converter = None
        self.artifact_dict = None

        if self.low_vram or (_is_gpu_device(self.device) and _is_low_vram_device()):
            enable_low_vram_mode()
            self.low_vram = True

        self._setup_env()
        self._load_models()

    def _setup_env(self):
        if _is_mlx_device(self.device):
            os.environ["MLX_DEVICE"] = "gpu"
        else:
            os.environ["TORCH_DEVICE"] = self.device

    def _load_models(self):
        from marker.config.parser import ConfigParser
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict

        config = {"output_format": "markdown"}
        if self.force_ocr:
            config["force_ocr"] = True
        if self.page_range:
            config["page_range"] = self.page_range
        if self.langs:
            config["languages"] = self.langs

        cp = ConfigParser(config)
        display = self._device_display()

        print(f"Loading marker-pdf models on {display}...")
        print("(First run downloads ~2-3 GB)")

        try:
            self._clear_mem()
            self.artifact_dict = create_model_dict()
            self.converter = PdfConverter(
                config=cp.generate_config_dict(),
                artifact_dict=self.artifact_dict,
                processor_list=cp.get_processors(),
                renderer=cp.get_renderer(),
            )
            print(f"Models loaded on {display}.")

        except RuntimeError as e:
            if "out of memory" in str(e).lower() and _is_gpu_device(self.device):
                print(f"[WARNING] OOM, falling back to CPU...")
                self._clear_mem()
                self.device = "cpu"
                os.environ["TORCH_DEVICE"] = "cpu"
                self.artifact_dict = create_model_dict()
                self.converter = PdfConverter(
                    config=cp.generate_config_dict(),
                    artifact_dict=self.artifact_dict,
                    processor_list=cp.get_processors(),
                    renderer=cp.get_renderer(),
                )
            else:
                raise

    def _device_display(self) -> str:
        if self.device == "cuda" and _is_rocm_runtime():
            return "ROCm"
        return {"mps": "MPS", "mlx": "MLX", "cpu": "CPU"}.get(self.device, self.device.upper())

    def _clear_mem(self):
        if _is_mlx_device(self.device):
            clear_mlx_memory()
        else:
            clear_gpu_memory()
        gc.collect()

    def convert_file(self, pdf_path: str) -> tuple[str, dict]:
        from marker.output import text_from_rendered

        self._clear_mem()
        rendered = self.converter(pdf_path)
        text, _, images = text_from_rendered(rendered)
        return clean_markdown(text), images or {}

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
            if total >= 4 and MarkerPDFConverter.is_available():
                print("[Engine] Auto-selected: marker")
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
        low_vram: Low VRAM mode (marker)
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
            print("[Converter] Using Docling (balanced)")
            return DoclingConverter(device=device)

    if selected == "mineru":
        if MinerUConverter.is_available():
            print("[Converter] Using MinerU (great for Chinese)")
            return MinerUConverter(device=device, langs=langs)

    if selected == "marker":
        if MarkerPDFConverter.is_available():
            print("[Converter] Using marker-pdf (best quality)")
            return MarkerPDFConverter(
                force_ocr=force_ocr,
                page_range=page_range,
                langs=langs,
                device=device,
                low_vram=low_vram,
            )

    raise ImportError(
        "No PDF converter available. Install one of:\n"
        "  pip install marker-pdf         # Best quality, GPU\n"
        "  pip install magic-pdf[full]    # MinerU, Chinese docs\n"
        "  pip install docling            # Balanced, ~1.5GB\n"
        "  pip install pymupdf4llm        # Fastest, no GPU\n"
        "  pip install pdfplumber         # Lightweight\n"
        "  pip install llama-parse        # Cloud, API key\n"
        "  pip install requests           # For Mathpix cloud"
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

        print(f"{name:<12} {info['type']:<8} {gpu:<12} {avail:<10} {notes}")

    print("\nInstall commands:")
    print("  pip install marker-pdf         # Best quality")
    print("  pip install magic-pdf[full]    # MinerU (Chinese docs)")
    print("  pip install docling            # Balanced")
    print("  pip install pymupdf4llm        # Fastest")
    print("  pip install pdfplumber         # Lightweight")
    print("  pip install llama-parse        # Cloud (LLAMA_CLOUD_API_KEY)")
    print("  pip install requests           # For Mathpix (MATHPIX_APP_ID/KEY)")


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
