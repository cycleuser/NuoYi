"""
NuoYi - OpenAI function-calling tool definitions.

Provides TOOLS list and dispatch() for LLM agent integration.
"""

from __future__ import annotations

import json
from typing import Any

from .utils import SUPPORTED_DEVICES, SUPPORTED_ENGINES

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "nuoyi_convert_file",
            "description": (
                "Convert a single PDF or DOCX file to Markdown. Supports "
                "multiple engines: marker (best quality), mineru (Chinese docs), "
                "docling (balanced), pymupdf (fastest), pdfplumber (lightweight), "
                "llamaparse/mathpix/mineru-cloud/doc2x (cloud, API key required). "
                "Returns the Markdown text and output path."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "input_path": {
                        "type": "string",
                        "description": "Path to the input PDF or DOCX file.",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output .md file path (default: same name with .md).",
                    },
                    "engine": {
                        "type": "string",
                        "enum": SUPPORTED_ENGINES,
                        "description": (
                            "PDF engine: auto (default), marker, mineru, docling, "
                            "pymupdf, pdfplumber, llamaparse, mathpix, mineru-cloud, doc2x."
                        ),
                        "default": "auto",
                    },
                    "force_ocr": {
                        "type": "boolean",
                        "description": "Force OCR even for digital PDFs.",
                        "default": False,
                    },
                    "page_range": {
                        "type": "string",
                        "description": "Page range, e.g. '0-5,10,15-20'.",
                    },
                    "langs": {
                        "type": "string",
                        "description": "Comma-separated language codes.",
                        "default": "zh,en",
                    },
                    "device": {
                        "type": "string",
                        "enum": SUPPORTED_DEVICES,
                        "description": (
                            "Compute device: cuda (NVIDIA), rocm (AMD Linux), "
                            "directml (AMD/Intel Windows), mps/mlx (Apple), "
                            "vulkan, openvino (Intel), cpu."
                        ),
                        "default": "auto",
                    },
                    "low_vram": {
                        "type": "boolean",
                        "description": "Enable low VRAM mode for GPUs with <8GB memory.",
                        "default": False,
                    },
                    "api_key": {
                        "type": "string",
                        "description": "API key for cloud engines (LlamaParse/MinerU Cloud/Doc2x).",
                    },
                    "app_id": {
                        "type": "string",
                        "description": "App ID for Mathpix.",
                    },
                    "app_key": {
                        "type": "string",
                        "description": "App key for Mathpix.",
                    },
                },
                "required": ["input_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "nuoyi_convert_directory",
            "description": (
                "Batch-convert all PDF and DOCX files in a directory to Markdown files. "
                "Supports multiple engines and recursive directory scanning."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "input_dir": {
                        "type": "string",
                        "description": "Directory containing files to convert.",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Output directory (default: same as input).",
                    },
                    "engine": {
                        "type": "string",
                        "enum": SUPPORTED_ENGINES,
                        "description": (
                            "PDF engine: auto (default), marker, mineru, docling, "
                            "pymupdf, pdfplumber, llamaparse, mathpix, mineru-cloud, doc2x."
                        ),
                        "default": "auto",
                    },
                    "force_ocr": {
                        "type": "boolean",
                        "description": "Force OCR even for digital PDFs.",
                        "default": False,
                    },
                    "langs": {
                        "type": "string",
                        "description": "Comma-separated language codes.",
                        "default": "zh,en",
                    },
                    "device": {
                        "type": "string",
                        "enum": SUPPORTED_DEVICES,
                        "description": (
                            "Compute device: cuda (NVIDIA), rocm (AMD Linux), "
                            "directml (AMD/Intel Windows), mps/mlx (Apple), "
                            "vulkan, openvino (Intel), cpu."
                        ),
                        "default": "auto",
                    },
                    "low_vram": {
                        "type": "boolean",
                        "description": "Enable low VRAM mode for GPUs with <8GB memory.",
                        "default": False,
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Recursively process subdirectories.",
                        "default": False,
                    },
                },
                "required": ["input_dir"],
            },
        },
    },
]


def dispatch(name: str, arguments: dict[str, Any] | str) -> dict:
    """Dispatch a tool call to the appropriate API function."""
    if isinstance(arguments, str):
        arguments = json.loads(arguments)

    if name == "nuoyi_convert_file":
        from .api import convert_file

        result = convert_file(**arguments)
        return result.to_dict()

    if name == "nuoyi_convert_directory":
        from .api import convert_directory

        result = convert_directory(**arguments)
        return result.to_dict()

    raise ValueError(f"Unknown tool: {name}")
