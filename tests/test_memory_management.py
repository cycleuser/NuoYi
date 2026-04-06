"""Tests for memory management and OCR model control."""

from __future__ import annotations

import pytest


def test_memory_utils_import():
    """Test memory management utilities are importable."""
    from nuoyi.utils import (
        aggressive_memory_cleanup,
        check_memory_available,
        get_current_memory_usage,
        clear_gpu_memory,
    )

    assert callable(aggressive_memory_cleanup)
    assert callable(check_memory_available)
    assert callable(get_current_memory_usage)
    assert callable(clear_gpu_memory)


def test_check_memory_available():
    """Test memory availability check."""
    from nuoyi.utils import check_memory_available

    is_available, free_mb = check_memory_available(100)
    assert isinstance(is_available, bool)
    assert isinstance(free_mb, float)


def test_get_current_memory_usage():
    """Test memory usage retrieval."""
    from nuoyi.utils import get_current_memory_usage

    usage = get_current_memory_usage()
    assert isinstance(usage, dict)
    assert "available" in usage


def test_marker_converter_disable_ocr():
    """Test MarkerPDFConverter with disable_ocr_models parameter."""
    from nuoyi.converter import MarkerPDFConverter

    converter = MarkerPDFConverter(
        disable_ocr_models=True,
        low_vram=True,
    )

    assert converter.disable_ocr_models is True
    assert converter.low_vram is True
    assert converter._models_loaded is False


def test_marker_converter_full_models():
    """Test MarkerPDFConverter with full models (default)."""
    from nuoyi.converter import MarkerPDFConverter

    converter = MarkerPDFConverter(
        disable_ocr_models=False,
    )

    assert converter.disable_ocr_models is False
    assert converter._models_loaded is False


def test_get_converter_with_disable_ocr():
    """Test get_converter with disable_ocr_models parameter."""
    from nuoyi.converter import get_converter

    converter = get_converter(
        engine="pymupdf",
        disable_ocr_models=True,
    )

    assert converter is not None


def test_api_convert_file_signature():
    """Test convert_file API has disable_ocr_models parameter."""
    from nuoyi.api import convert_file
    import inspect

    sig = inspect.signature(convert_file)
    params = list(sig.parameters.keys())

    assert "disable_ocr_models" in params


def test_api_convert_directory_signature():
    """Test convert_directory API has disable_ocr_models parameter."""
    from nuoyi.api import convert_directory
    import inspect

    sig = inspect.signature(convert_directory)
    params = list(sig.parameters.keys())

    assert "disable_ocr_models" in params


def test_cli_has_disable_ocr_flag():
    """Test CLI has --disable-ocr-models flag."""
    import sys
    from io import StringIO
    from nuoyi.cli import main

    old_argv = sys.argv
    old_stdout = sys.stdout

    try:
        sys.argv = ["nuoyi", "--help"]
        sys.stdout = StringIO()

        with pytest.raises(SystemExit):
            main()

        help_output = sys.stdout.getvalue()

        assert "--disable-ocr-models" in help_output

    finally:
        sys.argv = old_argv
        sys.stdout = old_stdout


def test_very_low_vram_threshold():
    """Test very low VRAM threshold constants."""
    from nuoyi.utils import VERY_LOW_VRAM_THRESHOLD_GB, LOW_VRAM_THRESHOLD_GB

    assert VERY_LOW_VRAM_THRESHOLD_GB == 4.0
    assert LOW_VRAM_THRESHOLD_GB == 6.0
    assert VERY_LOW_VRAM_THRESHOLD_GB < LOW_VRAM_THRESHOLD_GB


def test_setup_directml_env():
    """Test DirectML environment setup function."""
    from nuoyi.utils import _setup_directml_env
    import os

    old_value = os.environ.get("TORCH_DEVICE")

    try:
        _setup_directml_env()
        assert os.environ.get("TORCH_DEVICE") == "cuda"

    finally:
        if old_value is not None:
            os.environ["TORCH_DEVICE"] = old_value
        elif "TORCH_DEVICE" in os.environ:
            del os.environ["TORCH_DEVICE"]


def test_aggressive_memory_cleanup_no_gpu():
    """Test aggressive memory cleanup works without GPU."""
    from nuoyi.utils import aggressive_memory_cleanup

    result = aggressive_memory_cleanup()
    assert result is None


def test_marker_converter_parameters_conflict():
    """Test that disable_ocr_models and force_ocr conflict is handled."""
    from nuoyi.converter import MarkerPDFConverter

    converter = MarkerPDFConverter(
        disable_ocr_models=True,
        force_ocr=True,
    )

    assert converter.disable_ocr_models is True
    assert converter.force_ocr is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
