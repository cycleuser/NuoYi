#!/usr/bin/env python3
"""
Test script to verify directory structure preservation with _md suffix.
"""

from pathlib import Path
import tempfile
import shutil
from src.nuoyi.utils import (
    find_documents,
    create_output_directories,
    get_output_path,
)


def test_directory_structure_preservation():
    """Test that output directory structure matches input with _md suffix."""

    print("=" * 70)
    print("Directory Structure Preservation Test")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create input directory structure
        input_dir = tmpdir / "input"
        input_dir.mkdir()

        # Create nested structure
        projects = input_dir / "projects"
        project_a = projects / "ProjectA"
        project_b = projects / "ProjectB"
        docs = project_a / "docs"
        reports = project_b / "reports"

        projects.mkdir()
        project_a.mkdir()
        project_b.mkdir()
        docs.mkdir()
        reports.mkdir()

        # Create sample PDF files
        files_created = [
            input_dir / "overview.pdf",
            project_a / "spec.pdf",
            project_a / "notes.docx",
            docs / "manual.pdf",
            project_b / "design.pdf",
            reports / "quarterly.docx",
        ]

        for f in files_created:
            f.touch()

        print(f"\n✓ Created {len(files_created)} files in nested directories")

        # Create output directory
        output_dir = tmpdir / "output"
        output_dir.mkdir()

        print(f"✓ Created output directory: {output_dir}")

        # Test get_output_path function
        print("\n--- Testing get_output_path() ---")
        for f in files_created:
            out_path = get_output_path(f, input_dir, output_dir, recursive=True)
            rel_input = f.relative_to(input_dir)
            rel_output = out_path.relative_to(output_dir)
            print(f"  {str(rel_input):40s} -> {str(rel_output)}")

        # Create output directories
        print("\n--- Creating output directories ---")
        files = find_documents(input_dir, recursive=True)
        create_output_directories(files, input_dir, output_dir, recursive=True)

        # Verify directory structure
        print("\n--- Verifying output directory structure ---")
        expected_dirs = [
            "projects_md",
            "projects_md/ProjectA_md",
            "projects_md/ProjectB_md",
            "projects_md/ProjectA_md/docs_md",
            "projects_md/ProjectB_md/reports_md",
        ]

        for expected in expected_dirs:
            dir_path = output_dir / expected
            if dir_path.exists() and dir_path.is_dir():
                print(f"  ✓ {expected}")
            else:
                print(f"  ✗ {expected} (MISSING!)")
                return False

        # Test file paths
        print("\n--- Verifying file output paths ---")
        for f in files_created:
            out_path = get_output_path(f, input_dir, output_dir, recursive=True)
            expected_suffix = "_md" in str(out_path.relative_to(output_dir))
            print(f"  {f.name:25s} -> {out_path.name:20s} (in _md dir: {expected_suffix})")

        # Verify structure matches
        print("\n--- Verifying structure preservation ---")
        input_structure = set()
        for f in files_created:
            rel_path = f.relative_to(input_dir)
            input_structure.add(str(rel_path.parent))

        output_structure = set()
        for f in output_dir.rglob("*.md"):
            rel_path = f.relative_to(output_dir)
            # Remove _md suffix to compare
            parts = [p.replace("_md", "") for p in rel_path.parts[:-1]]
            output_structure.add("/".join(parts))

        print(f"  Input directories:  {sorted(input_structure)}")
        print(f"  Output directories: {sorted(output_structure)}")

        if input_structure == output_structure:
            print("\n✓ SUCCESS: Output directory structure matches input!")
            print("✓ All subdirectories have _md suffix as expected")
            return True
        else:
            print("\n✗ FAIL: Directory structures don't match")
            return False


def test_non_recursive_mode():
    """Test that non-recursive mode puts all files in flat output directory."""

    print("\n" + "=" * 70)
    print("Non-Recursive Mode Test")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create input with subdirectories
        input_dir = tmpdir / "input"
        input_dir.mkdir()
        subdir = input_dir / "subdir"
        subdir.mkdir()

        (input_dir / "file1.pdf").touch()
        (subdir / "file2.pdf").touch()

        output_dir = tmpdir / "output"
        output_dir.mkdir()

        files = find_documents(input_dir, recursive=True)
        create_output_directories(files, input_dir, output_dir, recursive=False)

        # Check all files are in root of output_dir
        md_files = list(output_dir.glob("*.md"))

        print(f"  Files in output root: {len(md_files)}")
        print(f"  Subdirectories: {len(list(output_dir.iterdir())) - len(md_files)}")

        if len(md_files) == 2 and len(list(output_dir.iterdir())) == 2:
            print("✓ Non-recursive mode: All files in flat directory")
            return True
        else:
            print("✗ Non-recursive mode failed")
            return False


if __name__ == "__main__":
    result1 = test_directory_structure_preservation()
    result2 = test_non_recursive_mode()

    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    if result1 and result2:
        print("✓ ALL TESTS PASSED!")
    else:
        print("✗ SOME TESTS FAILED!")
    print("=" * 70)
