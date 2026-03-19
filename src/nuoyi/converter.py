"""
NuoYi - Document converters for PDF and DOCX to Markdown.

Supports marker-pdf for PDF conversion and python-docx for DOCX.

Acceleration backends:
- CUDA: NVIDIA GPUs
- ROCm: AMD GPUs (via HIP, uses CUDA interface)
- MPS: Apple Silicon Metal Performance Shaders
- MLX: Apple MLX framework (experimental, may need surya-mlx)
- CPU: Universal fallback
"""

import gc
import os
from typing import Tuple

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

setup_memory_optimization()

import fitz
from docx import Document
from marker.config.parser import ConfigParser
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered


LOW_VRAM_THRESHOLD_GB = 8.0


def _is_gpu_device(device: str) -> bool:
    """Check if device is a GPU type that can experience OOM."""
    return device in ("cuda", "rocm", "mps")


def _is_mlx_device(device: str) -> bool:
    """Check if device is MLX."""
    return device == "mlx"


def _is_low_vram_device() -> bool:
    """Check if current GPU has low VRAM (<8GB)."""
    try:
        import torch

        if not torch.cuda.is_available():
            return False
        total, free = get_gpu_memory_info()
        return total < LOW_VRAM_THRESHOLD_GB
    except Exception:
        return False


class MarkerPDFConverter:
    """Primary PDF to Markdown converter using marker-pdf.

    Models are loaded once and reused across multiple files.
    Automatically handles GPU memory issues with CPU fallback.

    Supported devices:
    - cuda: NVIDIA GPUs
    - rocm: AMD GPUs (uses CUDA interface internally)
    - mps: Apple Silicon Metal
    - mlx: Apple MLX framework (experimental)
    - cpu: Universal fallback

    Memory optimization:
    - low_vram: Enable aggressive memory optimization for GPUs with <8GB VRAM
    - batch_size: Number of pages to process at once (auto-determined if not set)
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

        if self.low_vram or (_is_gpu_device(self.device) and _is_low_vram_device()):
            self._enable_low_vram()
            self.low_vram = True

        if self.batch_size is None and _is_gpu_device(self.device):
            total, free = get_gpu_memory_info()
            self.batch_size = get_recommended_batch_size(free if free > 0 else total)
            if self.low_vram:
                self.batch_size = max(1, self.batch_size // 2)

        self._setup_device_environment()
        self._build_and_load_models()

    def _enable_low_vram(self):
        """Enable low VRAM optimization mode."""
        print("[Memory] Enabling low VRAM optimization mode...")
        enable_low_vram_mode()

    def _setup_device_environment(self):
        """Set up environment variables for the selected device."""
        if _is_mlx_device(self.device):
            os.environ["MLX_DEVICE"] = "gpu"
        else:
            os.environ["TORCH_DEVICE"] = self.device

    def _build_config(self) -> dict:
        """Build configuration dict for marker-pdf."""
        config = {"output_format": "markdown"}
        if self.force_ocr:
            config["force_ocr"] = True
        if self.page_range:
            config["page_range"] = self.page_range
        if self.langs:
            config["languages"] = self.langs
        return config

    def _build_and_load_models(self):
        """Build config parser and load models."""
        config = self._build_config()
        config_parser = ConfigParser(config)
        self._load_models_with_fallback(config_parser)

    def _load_models_with_fallback(self, config_parser):
        """Load marker-pdf models with automatic CPU fallback on OOM."""
        device_display = self._get_device_display()

        print(f"Loading marker-pdf models on {device_display}...")
        print("(First run downloads ~2-3 GB of model weights)")

        if self.low_vram:
            print("[Memory] Low VRAM mode enabled - using aggressive memory optimization")

        try:
            self._clear_device_memory()
            self.artifact_dict = create_model_dict()
            self.converter = PdfConverter(
                config=config_parser.generate_config_dict(),
                artifact_dict=self.artifact_dict,
                processor_list=config_parser.get_processors(),
                renderer=config_parser.get_renderer(),
            )
            print(f"Models loaded successfully on {device_display}.")

        except RuntimeError as e:
            self._handle_load_error(e, config_parser)
        except MemoryError:
            self._handle_memory_error(config_parser)

    def _get_device_display(self) -> str:
        """Get display name for current device."""
        if self.device == "cuda" and _is_rocm_runtime():
            return "ROCm"
        device_names = {
            "mps": "MPS (Apple Metal)",
            "mlx": "MLX (Apple Silicon)",
            "cpu": "CPU",
        }
        return device_names.get(self.device, self.device.upper())

    def _handle_load_error(self, error: RuntimeError, config_parser):
        """Handle RuntimeError during model loading (e.g., CUDA OOM)."""
        error_msg = str(error).lower()
        is_oom = "out of memory" in error_msg or "oom" in error_msg

        if not is_oom:
            raise error

        if _is_gpu_device(self.device):
            print(f"\n[WARNING] {self.device.upper()} out of memory! Falling back to CPU...")
            print("[WARNING] This will be slower but avoids memory issues.\n")

            self._clear_device_memory()
            self.artifact_dict = None
            self.converter = None

            self.device = "cpu"
            os.environ["TORCH_DEVICE"] = "cpu"
            if "MLX_DEVICE" in os.environ:
                del os.environ["MLX_DEVICE"]

            print("Reloading models on CPU...")
            self.artifact_dict = create_model_dict()
            self.converter = PdfConverter(
                config=config_parser.generate_config_dict(),
                artifact_dict=self.artifact_dict,
                processor_list=config_parser.get_processors(),
                renderer=config_parser.get_renderer(),
            )
            print("Models loaded successfully on CPU.")
        else:
            raise error

    def _handle_memory_error(self, config_parser):
        """Handle MemoryError by falling back to CPU."""
        print("\n[WARNING] Memory error! Falling back to CPU...")

        self._clear_device_memory()
        self.device = "cpu"
        os.environ["TORCH_DEVICE"] = "cpu"
        if "MLX_DEVICE" in os.environ:
            del os.environ["MLX_DEVICE"]

        self.artifact_dict = create_model_dict()
        self.converter = PdfConverter(
            config=config_parser.generate_config_dict(),
            artifact_dict=self.artifact_dict,
            processor_list=config_parser.get_processors(),
            renderer=config_parser.get_renderer(),
        )
        print("Models loaded successfully on CPU.")

    def _clear_device_memory(self):
        """Clear memory for the current device."""
        if _is_mlx_device(self.device):
            clear_mlx_memory()
        else:
            clear_gpu_memory()
        self._force_gc()

    @staticmethod
    def _force_gc():
        """Force garbage collection."""
        gc.collect()

    def convert_file(self, pdf_path: str) -> Tuple[str, dict]:
        """Convert a single PDF file to Markdown text and extract images.

        Returns:
            Tuple of (markdown_text, images_dict) where images_dict maps
            image filenames to PIL Image objects or base64 data.
        """
        try:
            self._clear_device_memory()
            rendered = self.converter(pdf_path)
            text, _, images = text_from_rendered(rendered)
            return clean_markdown(text), images or {}

        except RuntimeError as e:
            return self._handle_conversion_error(e, pdf_path)
        except MemoryError:
            return self._retry_on_cpu(pdf_path)

    def _handle_conversion_error(self, error: RuntimeError, pdf_path: str):
        """Handle RuntimeError during conversion."""
        error_msg = str(error).lower()
        is_oom = "out of memory" in error_msg or "oom" in error_msg

        if not is_oom:
            raise error

        if _is_gpu_device(self.device):
            print(f"\n[WARNING] {self.device.upper()} OOM during conversion! Retrying on CPU...")
            return self._retry_on_cpu(pdf_path)
        raise error

    def _retry_on_cpu(self, pdf_path: str) -> Tuple[str, dict]:
        """Retry conversion on CPU after GPU failure."""
        self._clear_device_memory()

        self.device = "cpu"
        os.environ["TORCH_DEVICE"] = "cpu"
        if "MLX_DEVICE" in os.environ:
            del os.environ["MLX_DEVICE"]

        self._rebuild_converter()

        rendered = self.converter(pdf_path)
        text, _, images = text_from_rendered(rendered)
        return clean_markdown(text), images or {}

    def _rebuild_converter(self):
        """Rebuild the converter for the current device."""
        config = self._build_config()
        config_parser = ConfigParser(config)

        self.artifact_dict = create_model_dict()
        self.converter = PdfConverter(
            config=config_parser.generate_config_dict(),
            artifact_dict=self.artifact_dict,
            processor_list=config_parser.get_processors(),
            renderer=config_parser.get_renderer(),
        )

    @staticmethod
    def get_page_count(pdf_path: str) -> int:
        """Quick page count using PyMuPDF."""
        try:
            doc = fitz.open(pdf_path)
            count = len(doc)
            doc.close()
            return count
        except Exception:
            return 0


def _is_rocm_runtime() -> bool:
    """Check if current CUDA runtime is actually ROCm/HIP."""
    try:
        import torch

        return hasattr(torch.version, "hip") and torch.version.hip is not None
    except Exception:
        return False


class DocxConverter:
    """DOCX to Markdown converter using python-docx."""

    def convert_file(self, docx_path: str) -> str:
        """Convert a DOCX file to Markdown."""
        doc = Document(docx_path)
        markdown_parts = []

        for element in doc.element.body:
            if element.tag.endswith("p"):
                for para in doc.paragraphs:
                    if para._element == element:
                        md = self._paragraph_to_markdown(para)
                        if md:
                            markdown_parts.append(md)
                        break
            elif element.tag.endswith("tbl"):
                for table in doc.tables:
                    if table._element == element:
                        md = self._table_to_markdown(table)
                        if md:
                            markdown_parts.append(md)
                        break

        return "\n\n".join(markdown_parts)

    @staticmethod
    def _paragraph_to_markdown(para) -> str:
        text = para.text.strip()
        if not text:
            return ""

        style = para.style.name.lower() if para.style else ""

        if "heading 1" in style or style == "title":
            return f"# {text}"
        elif "heading 2" in style:
            return f"## {text}"
        elif "heading 3" in style:
            return f"### {text}"
        elif "heading 4" in style:
            return f"#### {text}"
        elif "list" in style:
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
    def _table_to_markdown(table) -> str:
        rows = []
        for row in table.rows:
            cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
            rows.append(cells)

        if not rows:
            return ""

        lines = []
        lines.append("| " + " | ".join(rows[0]) + " |")
        lines.append("| " + " | ".join(["---"] * len(rows[0])) + " |")
        for row in rows[1:]:
            while len(row) < len(rows[0]):
                row.append("")
            lines.append("| " + " | ".join(row[: len(rows[0])]) + " |")

        return "\n".join(lines)
