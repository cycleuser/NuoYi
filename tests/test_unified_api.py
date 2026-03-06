"""
Comprehensive tests for NuoYi unified API, tools, and CLI flags.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestToolResult:
    def test_success(self):
        from nuoyi.api import ToolResult
        r = ToolResult(success=True, data={"markdown": "# Hello"})
        assert r.success is True

    def test_failure(self):
        from nuoyi.api import ToolResult
        r = ToolResult(success=False, error="file not found")
        assert r.error == "file not found"

    def test_to_dict(self):
        from nuoyi.api import ToolResult
        d = ToolResult(success=True, data="md").to_dict()
        assert set(d.keys()) == {"success", "data", "error", "metadata"}

    def test_default_metadata_isolation(self):
        from nuoyi.api import ToolResult
        r1 = ToolResult(success=True)
        r2 = ToolResult(success=True)
        r1.metadata["x"] = 1
        assert "x" not in r2.metadata


class TestConvertFileAPI:
    def test_missing_file(self):
        from nuoyi.api import convert_file
        result = convert_file("/no/such/file.pdf")
        assert result.success is False
        assert "File not found" in result.error

    def test_unsupported_format(self):
        from nuoyi.api import convert_file
        with tempfile.NamedTemporaryFile(suffix=".txt") as f:
            result = convert_file(f.name)
            assert result.success is False
            assert "Unsupported format" in result.error

    def test_accepts_path_object(self):
        from nuoyi.api import convert_file
        result = convert_file(Path("/nonexistent.pdf"))
        assert result.success is False


class TestConvertDirectoryAPI:
    def test_invalid_directory(self):
        from nuoyi.api import convert_directory
        result = convert_directory("/nonexistent/dir")
        assert result.success is False
        assert "Not a directory" in result.error

    def test_empty_directory(self):
        from nuoyi.api import convert_directory
        with tempfile.TemporaryDirectory() as d:
            result = convert_directory(d)
            assert result.success is True
            assert result.data["success"] == 0
            assert result.data["failed"] == 0


class TestToolsSchema:
    def test_tools_count(self):
        from nuoyi.tools import TOOLS
        assert len(TOOLS) == 2

    def test_tool_names(self):
        from nuoyi.tools import TOOLS
        names = [t["function"]["name"] for t in TOOLS]
        assert "nuoyi_convert_file" in names
        assert "nuoyi_convert_directory" in names

    def test_structure(self):
        from nuoyi.tools import TOOLS
        for tool in TOOLS:
            assert tool["type"] == "function"
            func = tool["function"]
            assert "name" in func
            assert "description" in func
            params = func["parameters"]
            assert params["type"] == "object"
            assert "properties" in params
            for req in params["required"]:
                assert req in params["properties"]


class TestToolsDispatch:
    def test_unknown_tool(self):
        from nuoyi.tools import dispatch
        with pytest.raises(ValueError):
            dispatch("bad", {})

    def test_dispatch_convert_file_missing(self):
        from nuoyi.tools import dispatch
        result = dispatch("nuoyi_convert_file", {"input_path": "/no.pdf"})
        assert isinstance(result, dict)
        assert result["success"] is False

    def test_dispatch_convert_directory_empty(self):
        from nuoyi.tools import dispatch
        with tempfile.TemporaryDirectory() as d:
            result = dispatch("nuoyi_convert_directory", {"input_dir": d})
            assert result["success"] is True

    def test_dispatch_json_string(self):
        from nuoyi.tools import dispatch
        args = json.dumps({"input_path": "/no.pdf"})
        result = dispatch("nuoyi_convert_file", args)
        assert isinstance(result, dict)


class TestCLIFlags:
    def _run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "nuoyi"] + list(args),
            capture_output=True, text=True, timeout=15,
        )

    def test_version_flag(self):
        r = self._run_cli("-V")
        assert r.returncode == 0
        assert "nuoyi" in r.stdout.lower()

    def test_help_has_unified_flags(self):
        r = self._run_cli("--help")
        assert "--json" in r.stdout
        assert "--quiet" in r.stdout or "-q" in r.stdout
        assert "--verbose" in r.stdout or "-v" in r.stdout


class TestPackageExports:
    def test_version(self):
        import nuoyi
        assert hasattr(nuoyi, "__version__")

    def test_toolresult(self):
        from nuoyi import ToolResult
        assert callable(ToolResult)

    def test_converters(self):
        from nuoyi import MarkerPDFConverter, DocxConverter
        assert MarkerPDFConverter is not None
        assert DocxConverter is not None
