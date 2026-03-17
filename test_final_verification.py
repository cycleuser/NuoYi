#!/usr/bin/env python3
"""
Standalone verification test for directory structure preservation.
"""

from pathlib import Path
import tempfile
import os


def get_output_path(input_file, input_dir, output_dir, recursive=False, suffix="_md"):
    """Calculate output path preserving directory structure."""
    if not recursive:
        return output_dir / f"{input_file.stem}.md"

    try:
        rel_path = input_file.relative_to(input_dir)
    except ValueError:
        return output_dir / f"{input_file.stem}.md"

    output_parts = []
    for part in rel_path.parts[:-1]:
        output_parts.append(f"{part}{suffix}")
    output_parts.append(f"{input_file.stem}.md")

    return output_dir / Path(*output_parts)


def create_output_directories(files, input_dir, output_dir, recursive=False, suffix="_md"):
    """Create output directories preserving input structure."""
    if not recursive:
        output_dir.mkdir(parents=True, exist_ok=True)
        return

    for file in files:
        output_path = get_output_path(file, input_dir, output_dir, recursive, suffix)
        output_path.parent.mkdir(parents=True, exist_ok=True)


def main():
    print("=" * 70)
    print("Directory Structure Preservation - End-to-End Test")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        input_dir = tmpdir / "input"
        output_dir = tmpdir / "output"

        # Create test structure
        (input_dir / "projects" / "ProjectA" / "docs").mkdir(parents=True)
        (input_dir / "projects" / "ProjectB" / "reports").mkdir(parents=True)

        # Create test files
        files = [
            input_dir / "overview.pdf",
            input_dir / "projects" / "ProjectA" / "spec.pdf",
            input_dir / "projects" / "ProjectA" / "notes.docx",
            input_dir / "projects" / "ProjectA" / "docs" / "manual.pdf",
            input_dir / "projects" / "ProjectB" / "design.pdf",
            input_dir / "projects" / "ProjectB" / "reports" / "quarterly.docx",
        ]

        for f in files:
            f.touch()

        print("\n✓ Input structure created")
        print("\nInput files:")
        for f in files:
            print(f"  {f.relative_to(input_dir)}")

        # Create output directories
        create_output_directories(files, input_dir, output_dir, recursive=True)

        print("\n✓ Output directories created")
        print("\nOutput directory structure:")
        for root, dirs, filenames in os.walk(output_dir):
            root_path = Path(root)
            level = root_path.relative_to(output_dir)

            # Print directory name
            if str(level) != ".":
                indent = "  " * len(level.parts)
                print(f"{indent}{root_path.name}/")

            # Print files
            for filename in filenames:
                indent = "  " * (len(level.parts) + 1)
                print(f"{indent}{filename}")

        # Verify structure
        print("\n" + "=" * 70)
        print("Verification")
        print("=" * 70)

        expected_structure = {
            "overview.md",
            "projects_md/ProjectA_md/spec.md",
            "projects_md/ProjectA_md/notes.md",
            "projects_md/ProjectA_md/docs_md/manual.md",
            "projects_md/ProjectB_md/design.md",
            "projects_md/ProjectB_md/reports_md/quarterly.md",
        }

        # Check each file
        all_correct = True
        for f in files:
            out_path = get_output_path(f, input_dir, output_dir, recursive=True)
            rel_output = out_path.relative_to(output_dir)
            expected = str(rel_output)

            # Verify _md suffix in all directory components
            has_md_suffix = all(
                part.endswith("_md") or part.endswith(".md") for part in rel_output.parts
            )

            status = "✓" if has_md_suffix else "✗"
            print(f"  {status} {str(f.relative_to(input_dir)):45s} -> {rel_output}")

            if not has_md_suffix:
                all_correct = False
                print(f"      ERROR: Missing _md suffix!")

            # Verify file would be in correct location
            expected_path = output_dir / expected
            if str(rel_output) not in expected_structure:
                print(f"      ERROR: Unexpected path!")
                all_correct = False

        # Verify directories exist
        print("\nDirectory verification:")
        expected_dirs = [
            "projects_md",
            "projects_md/ProjectA_md",
            "projects_md/ProjectB_md",
            "projects_md/ProjectA_md/docs_md",
            "projects_md/ProjectB_md/reports_md",
        ]

        for dir_name in expected_dirs:
            dir_path = output_dir / dir_name
            exists = dir_path.exists() and dir_path.is_dir()
            status = "✓" if exists else "✗"
            print(f"  {status} {dir_name}")
            if not exists:
                all_correct = False

        print("\n" + "=" * 70)
        if all_correct:
            print("✓ SUCCESS: All directory structures preserved with _md suffix!")
            return 0
        else:
            print("✗ FAIL: Directory structure preservation has issues!")
            return 1
        print("=" * 70)


if __name__ == "__main__":
    import sys

    sys.exit(main())
