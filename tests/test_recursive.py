"""
Test recursive directory scanning functionality.
"""

import pytest
from pathlib import Path
import tempfile


class TestRecursiveDirectoryScanning:
    """Test recursive directory scanning for PDF and DOCX files."""

    def test_find_pdf_files_flat(self):
        """Test finding PDF files in a flat directory."""
        from nuoyi.utils import find_pdf_files

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            # Create some PDF files
            (tmpdir / "file1.pdf").touch()
            (tmpdir / "file2.pdf").touch()
            (tmpdir / "file.txt").touch()

            files = find_pdf_files(tmpdir, recursive=False)
            assert len(files) == 2
            assert all(f.suffix == ".pdf" for f in files)

    def test_find_pdf_files_recursive(self):
        """Test finding PDF files recursively."""
        from nuoyi.utils import find_pdf_files

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            # Create nested structure
            subdir1 = tmpdir / "subdir1"
            subdir2 = tmpdir / "subdir1" / "subdir2"
            subdir1.mkdir()
            subdir2.mkdir()

            # Create PDF files at different levels
            (tmpdir / "root.pdf").touch()
            (subdir1 / "file1.pdf").touch()
            (subdir2 / "file2.pdf").touch()
            (subdir2 / "file3.pdf").touch()

            files = find_pdf_files(tmpdir, recursive=True)
            assert len(files) == 4
            assert all(f.suffix == ".pdf" for f in files)

    def test_find_docx_files_recursive(self):
        """Test finding DOCX files recursively."""
        from nuoyi.utils import find_docx_files

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            subdir = tmpdir / "docs"
            subdir.mkdir()

            (tmpdir / "root.docx").touch()
            (subdir / "nested.docx").touch()

            files = find_docx_files(tmpdir, recursive=True)
            assert len(files) == 2

    def test_find_documents_mixed(self):
        """Test finding both PDF and DOCX files."""
        from nuoyi.utils import find_documents

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            subdir = tmpdir / "mixed"
            subdir.mkdir()

            (tmpdir / "file1.pdf").touch()
            (tmpdir / "file2.docx").touch()
            (subdir / "file3.pdf").touch()
            (subdir / "file4.docx").touch()

            files = find_documents(tmpdir, recursive=True)
            assert len(files) == 4
            assert sum(1 for f in files if f.suffix == ".pdf") == 2
            assert sum(1 for f in files if f.suffix == ".docx") == 2

    def test_scan_directory_flat(self):
        """Test scan_directory in non-recursive mode."""
        from nuoyi.utils import scan_directory

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            subdir = tmpdir / "subdir"
            subdir.mkdir()

            (tmpdir / "file1.pdf").touch()
            (subdir / "file2.pdf").touch()

            result = scan_directory(tmpdir, recursive=False)
            assert result["total_files"] == 1
            assert len(result["pdf_files"]) == 1
            assert len(result["subdirs"]) == 0

    def test_scan_directory_recursive(self):
        """Test scan_directory in recursive mode."""
        from nuoyi.utils import scan_directory

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            subdir1 = tmpdir / "subdir1"
            subdir2 = tmpdir / "subdir1" / "subdir2"
            subdir1.mkdir()
            subdir2.mkdir()

            (tmpdir / "root.pdf").touch()
            (subdir1 / "file1.pdf").touch()
            (subdir2 / "file2.pdf").touch()

            result = scan_directory(tmpdir, recursive=True)
            assert result["total_files"] == 3
            assert len(result["pdf_files"]) == 3
            assert len(result["subdirs"]) == 2
            assert "subdir1" in result["subdirs"]
            assert (
                "subdir1/subdir2" in result["subdirs"]
                or str(Path("subdir1/subdir2")) in result["subdirs"]
            )

    def test_empty_directory(self):
        """Test scanning an empty directory."""
        from nuoyi.utils import scan_directory

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            result = scan_directory(tmpdir, recursive=True)
            assert result["total_files"] == 0
            assert len(result["pdf_files"]) == 0
            assert len(result["docx_files"]) == 0
            assert len(result["subdirs"]) == 0

    def test_no_pdf_files_in_subdirs(self):
        """Test that recursive=False doesn't find files in subdirs."""
        from nuoyi.utils import find_pdf_files

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            subdir = tmpdir / "hidden"
            subdir.mkdir()
            (subdir / "secret.pdf").touch()

            files = find_pdf_files(tmpdir, recursive=False)
            assert len(files) == 0

            files_recursive = find_pdf_files(tmpdir, recursive=True)
            assert len(files_recursive) == 1
