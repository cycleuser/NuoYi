"""
NuoYi - Document converters for PDF and DOCX to Markdown.

Supports marker-pdf for PDF conversion and python-docx for DOCX.
"""

import os
from typing import Tuple

from .utils import (
    clear_gpu_memory,
    clean_markdown,
    select_device,
    setup_memory_optimization,
)

# Run memory setup early
setup_memory_optimization()

# --- PyMuPDF (for page counting) ---
import fitz

# --- marker-pdf (primary conversion engine) ---
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from marker.config.parser import ConfigParser

# --- python-docx (DOCX support) ---
from docx import Document


class MarkerPDFConverter:
    """Primary PDF to Markdown converter using marker-pdf.

    Models are loaded once and reused across multiple files.
    Automatically handles GPU memory issues with CPU fallback.
    """

    def __init__(self, force_ocr: bool = False, page_range: str = None,
                 langs: str = "zh,en", device: str = "auto"):
        self.force_ocr = force_ocr
        self.page_range = page_range
        self.langs = langs

        # Select device with automatic fallback
        self.device = select_device(device)

        # Set environment variable for marker-pdf/torch
        os.environ["TORCH_DEVICE"] = self.device

        # Build config
        config = {"output_format": "markdown"}
        if force_ocr:
            config["force_ocr"] = True
        if page_range:
            config["page_range"] = page_range
        if langs:
            config["languages"] = langs

        config_parser = ConfigParser(config)

        # Try to load models, with CPU fallback on OOM
        self._load_models_with_fallback(config_parser)

    def _load_models_with_fallback(self, config_parser):
        """Load marker-pdf models with automatic CPU fallback on CUDA OOM."""
        print(f"Loading marker-pdf models on {self.device.upper()}...")
        print("(First run downloads ~2-3 GB of model weights)")

        try:
            clear_gpu_memory()
            self.artifact_dict = create_model_dict()
            self.converter = PdfConverter(
                config=config_parser.generate_config_dict(),
                artifact_dict=self.artifact_dict,
                processor_list=config_parser.get_processors(),
                renderer=config_parser.get_renderer(),
            )
            print(f"Models loaded successfully on {self.device.upper()}.")

        except RuntimeError as e:
            error_msg = str(e).lower()
            if "cuda" in error_msg and ("out of memory" in error_msg or "oom" in error_msg):
                if self.device != "cpu":
                    print(f"\n[WARNING] CUDA out of memory! Falling back to CPU...")
                    print("[WARNING] This will be slower but avoids memory issues.\n")

                    # Clean up GPU memory
                    clear_gpu_memory()
                    self.artifact_dict = None
                    self.converter = None

                    # Switch to CPU
                    self.device = "cpu"
                    os.environ["TORCH_DEVICE"] = "cpu"

                    # Retry on CPU
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
                    raise
            else:
                raise

    def convert_file(self, pdf_path: str) -> Tuple[str, dict]:
        """Convert a single PDF file to Markdown text and extract images.
        
        Returns:
            Tuple of (markdown_text, images_dict) where images_dict maps
            image filenames to PIL Image objects or base64 data.
        """
        try:
            clear_gpu_memory()
            rendered = self.converter(pdf_path)
            text, _, images = text_from_rendered(rendered)
            return clean_markdown(text), images or {}

        except RuntimeError as e:
            error_msg = str(e).lower()
            if "cuda" in error_msg and ("out of memory" in error_msg or "oom" in error_msg):
                if self.device != "cpu":
                    print(f"\n[WARNING] CUDA OOM during conversion! Retrying on CPU...")
                    clear_gpu_memory()

                    # Rebuild converter on CPU
                    self.device = "cpu"
                    os.environ["TORCH_DEVICE"] = "cpu"

                    config = {"output_format": "markdown"}
                    if self.force_ocr:
                        config["force_ocr"] = True
                    if self.page_range:
                        config["page_range"] = self.page_range
                    if self.langs:
                        config["languages"] = self.langs

                    config_parser = ConfigParser(config)
                    self.artifact_dict = create_model_dict()
                    self.converter = PdfConverter(
                        config=config_parser.generate_config_dict(),
                        artifact_dict=self.artifact_dict,
                        processor_list=config_parser.get_processors(),
                        renderer=config_parser.get_renderer(),
                    )

                    # Retry conversion
                    rendered = self.converter(pdf_path)
                    text, _, images = text_from_rendered(rendered)
                    return clean_markdown(text), images or {}
            raise

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
            lines.append("| " + " | ".join(row[:len(rows[0])]) + " |")

        return "\n".join(lines)
