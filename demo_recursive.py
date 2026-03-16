#!/usr/bin/env python3
"""
Demo script showing recursive directory scanning in NuoYi.

This demonstrates the new --recursive flag for batch conversion.
"""

from pathlib import Path
import tempfile
from nuoyi.utils import scan_directory, find_documents


def demo_recursive_scanning():
    """Demonstrate recursive directory scanning."""

    print("=" * 60)
    print("NuoYi Recursive Directory Scanning Demo")
    print("=" * 60)

    # Create a sample directory structure
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create nested structure
        projects = tmpdir / "projects"
        project_a = projects / "ProjectA"
        project_b = projects / "ProjectB"
        docs = project_a / "docs"
        reports = project_b / "reports"

        projects.mkdir(parents=True)
        project_a.mkdir()
        project_b.mkdir()
        docs.mkdir()
        reports.mkdir()

        # Create sample files
        (projects / "overview.pdf").touch()
        (project_a / "spec.pdf").touch()
        (project_a / "notes.docx").touch()
        (docs / "manual.pdf").touch()
        (project_b / "design.pdf").touch()
        (reports / "quarterly.docx").touch()
        (reports / "annual.pdf").touch()

        print(f"\nCreated sample directory structure:")
        print(f"  {tmpdir}/")
        print(f"    └── projects/")
        print(f"        ├── overview.pdf")
        print(f"        ├── ProjectA/")
        print(f"        │   ├── spec.pdf")
        print(f"        │   ├── notes.docx")
        print(f"        │   └── docs/")
        print(f"        │       └── manual.pdf")
        print(f"        └── ProjectB/")
        print(f"            ├── design.pdf")
        print(f"            └── reports/")
        print(f"                ├── quarterly.docx")
        print(f"                └── annual.pdf")

        # Demo 1: Non-recursive scan
        print("\n" + "-" * 60)
        print("1. Non-recursive scan (--batch without -r):")
        print("-" * 60)
        result = scan_directory(projects, recursive=False)
        print(f"   Files found: {result['total_files']}")
        print(f"   PDF files: {len(result['pdf_files'])}")
        print(f"   DOCX files: {len(result['docx_files'])}")
        print(f"   Subdirectories: {len(result['subdirs'])}")
        print(f"   Files:")
        for f in result["pdf_files"] + result["docx_files"]:
            print(f"     - {f.name}")

        # Demo 2: Recursive scan
        print("\n" + "-" * 60)
        print("2. Recursive scan (--batch -r):")
        print("-" * 60)
        result = scan_directory(projects, recursive=True)
        print(f"   Files found: {result['total_files']}")
        print(f"   PDF files: {len(result['pdf_files'])}")
        print(f"   DOCX files: {len(result['docx_files'])}")
        print(f"   Subdirectories with documents: {len(result['subdirs'])}")
        print(f"   Subdirectories: {', '.join(result['subdirs'])}")
        print(f"   Files:")
        for f in result["pdf_files"] + result["docx_files"]:
            rel_path = f.relative_to(projects)
            print(f"     - {rel_path}")

        # Demo 3: Using find_documents
        print("\n" + "-" * 60)
        print("3. Using find_documents() API:")
        print("-" * 60)

        pdfs = find_documents(projects, recursive=True, extensions=(".pdf",))
        print(f"   Found {len(pdfs)} PDF files recursively")

        docx_files = find_documents(projects, recursive=True, extensions=(".docx",))
        print(f"   Found {len(docx_files)} DOCX files recursively")

        print("\n" + "=" * 60)
        print("CLI Usage:")
        print("=" * 60)
        print(f"  # Convert all files in directory (non-recursive)")
        print(f"  nuoyi {projects} --batch")
        print(f"\n  # Convert all files recursively (including subdirectories)")
        print(f"  nuoyi {projects} --batch --recursive")
        print(f"  nuoyi {projects} --batch -r")
        print("=" * 60)
        print()


if __name__ == "__main__":
    demo_recursive_scanning()
