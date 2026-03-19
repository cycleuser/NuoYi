"""
NuoYi - Basic tests for package functionality.
"""


def test_version():
    """Test that version is accessible."""
    from nuoyi import __version__

    assert __version__ == "0.3.0"


def test_imports():
    """Test that main classes can be imported."""
    from nuoyi import (
        DocxConverter,
        MarkerPDFConverter,
        clean_markdown,
        select_device,
    )

    # These should be importable
    assert MarkerPDFConverter is not None
    assert DocxConverter is not None
    assert callable(clean_markdown)
    assert callable(select_device)


def test_clean_markdown():
    """Test markdown cleanup function."""
    from nuoyi import clean_markdown

    # Test excessive newlines
    text = "Hello\n\n\n\n\n\nWorld"
    result = clean_markdown(text)
    assert result == "Hello\n\n\nWorld"

    # Test Windows line endings
    text = "Hello\r\nWorld"
    result = clean_markdown(text)
    assert result == "Hello\nWorld"

    # Test stripping
    text = "  Hello World  "
    result = clean_markdown(text)
    assert result == "Hello World"


def test_clean_markdown_citation_links():
    """Test cleanup of broken citation links from marker-pdf."""
    from nuoyi import clean_markdown

    # Test page anchor links removal
    # [Author](#page-10-0) -> Author
    text = "written in VBA [Zhou and](#page-10-0) [Li, 2006](#page-10-0)"
    result = clean_markdown(text)
    assert "[#page" not in result
    assert "Zhou and" in result
    assert "Li, 2006" in result

    # Test multiple page anchors
    text = "See [Smith, 2020](#page-5-0) and [Jones, 2021](#page-12-3)"
    result = clean_markdown(text)
    assert result == "See Smith, 2020 and Jones, 2021"

    # Test bookmark anchors
    text = "Reference [Author](#_bookmark45) here"
    result = clean_markdown(text)
    assert result == "Reference Author here"

    # Test empty link targets
    text = "Some [text]() here"
    result = clean_markdown(text)
    assert result == "Some text here"

    # Test fixing broken citations with missing opening parenthesis
    text = "as mentioned by Smith, 2020) in the paper"
    result = clean_markdown(text)
    assert "(Smith, 2020)" in result

    # Test complex citation repair
    text = "[Zhou and](#page-10-0) [Li, 2006; Wang et al., 2008)](#page-10-0)"
    result = clean_markdown(text)
    assert result == "(Zhou and Li, 2006; Wang et al., 2008)"


def test_supported_languages():
    """Test that language constants are properly defined."""
    from nuoyi import DEFAULT_LANGS, SUPPORTED_LANGUAGES

    # Should have exactly 10 languages
    assert len(SUPPORTED_LANGUAGES) == 10

    # All expected codes present
    expected_codes = {"zh", "en", "ja", "fr", "ru", "de", "es", "pt", "it", "ko"}
    assert set(SUPPORTED_LANGUAGES.keys()) == expected_codes

    # DEFAULT_LANGS should be a comma-separated string of valid codes
    for code in DEFAULT_LANGS.split(","):
        assert code in SUPPORTED_LANGUAGES


def test_select_device_cpu():
    """Test device selection with CPU preference."""
    from nuoyi import select_device

    # CPU should always return "cpu"
    result = select_device("cpu")
    assert result == "cpu"


def test_docx_converter():
    """Test DOCX converter can be instantiated."""
    from nuoyi import DocxConverter

    converter = DocxConverter()
    assert converter is not None


class TestUtilityFunctions:
    """Test utility functions."""

    def test_get_gpu_memory_info(self):
        """Test GPU memory info retrieval."""
        from nuoyi import get_gpu_memory_info

        total, free = get_gpu_memory_info()
        assert isinstance(total, float)
        assert isinstance(free, float)
        assert total >= 0
        assert free >= 0

    def test_setup_memory_optimization(self):
        """Test memory optimization setup."""
        import os

        from nuoyi import setup_memory_optimization

        # Should not raise
        setup_memory_optimization()

        # Should set environment variable
        assert "PYTORCH_CUDA_ALLOC_CONF" in os.environ

    def test_save_images_empty(self):
        """Test save_images_and_update_markdown with empty images."""
        import tempfile
        from pathlib import Path

        from nuoyi import save_images_and_update_markdown

        markdown = "# Test\n\nSome content"
        images = {}

        with tempfile.TemporaryDirectory() as tmpdir:
            result = save_images_and_update_markdown(markdown, images, Path(tmpdir), "images")

        # Should return unchanged markdown
        assert result == markdown
