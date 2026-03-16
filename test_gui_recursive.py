"""
Test script to verify GUI recursive directory scanning works correctly.
"""

from pathlib import Path
import tempfile
from src.nuoyi.utils import find_documents


def test_gui_recursive_logic():
    """Test the logic that will be used in GUI for recursive scanning."""

    print("=" * 60)
    print("GUI Recursive Scanning Logic Test")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test directory structure
        projects = tmpdir / "projects"
        project_a = projects / "ProjectA"
        project_b = projects / "ProjectB"
        docs = project_a / "docs"

        projects.mkdir(parents=True)
        project_a.mkdir()
        project_b.mkdir()
        docs.mkdir()

        # Create sample files
        files_created = [
            projects / "overview.pdf",
            project_a / "spec.pdf",
            project_a / "notes.docx",
            docs / "manual.pdf",
            project_b / "design.pdf",
        ]

        for f in files_created:
            f.touch()

        print(f"\nCreated {len(files_created)} files in nested directories")

        # Test non-recursive
        print("\n--- Non-recursive scan (GUI checkbox unchecked) ---")
        flat_files = find_documents(projects, recursive=False)
        print(f"Files found: {len(flat_files)}")
        for f in flat_files:
            print(f"  - {f.name}")

        # Test recursive
        print("\n--- Recursive scan (GUI checkbox checked) ---")
        recursive_files = find_documents(projects, recursive=True)
        print(f"Files found: {len(recursive_files)}")
        for f in recursive_files:
            rel_path = f.relative_to(projects)
            print(f"  - {rel_path}")

        # Verify results
        print("\n--- Verification ---")
        assert len(flat_files) == 1, f"Expected 1 file in flat scan, got {len(flat_files)}"
        assert len(recursive_files) == 5, (
            f"Expected 5 files in recursive scan, got {len(recursive_files)}"
        )

        # Test path display logic
        print("\n--- Path display in GUI table ---")
        for f in recursive_files:
            try:
                rel_path = f.relative_to(projects)
                display_name = str(rel_path)
            except ValueError:
                display_name = f.name
            print(f"  Table cell: {display_name}")

        print("\n✅ All tests passed!")
        print("=" * 60)


if __name__ == "__main__":
    test_gui_recursive_logic()
