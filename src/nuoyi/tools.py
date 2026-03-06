"""
NuoYi - OpenAI function-calling tool definitions.

Provides TOOLS list and dispatch() for LLM agent integration.
"""

from __future__ import annotations

import json
from typing import Any

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "nuoyi_convert_file",
            "description": (
                "Convert a single PDF or DOCX file to Markdown. Uses "
                "marker-pdf with surya OCR for high-quality offline "
                "conversion. Returns the Markdown text and output path."
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
                        "enum": ["auto", "cpu", "cuda", "mps"],
                        "description": "Compute device for model inference.",
                        "default": "auto",
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
                "Batch-convert all PDF and DOCX files in a directory "
                "to Markdown files."
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
                        "enum": ["auto", "cpu", "cuda", "mps"],
                        "description": "Compute device.",
                        "default": "auto",
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
