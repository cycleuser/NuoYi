#!/usr/bin/env python3
"""
Standalone test for directory structure preservation.
Tests the logic without importing the full module.
"""

from pathlib import Path
import tempfile


def get_output_path(
    input_file: Path,
    input_dir: Path,
    output_dir: Path,
    recursive: bool = False,
    suffix: str = "_md",
) -> Path:
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


def test_structure_preservation():
    """Test directory structure preservation with _md suffix."""

    print("=" * 70)
    print("Directory Structure Preservation Test")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create input structure
        input_dir = tmpdir / "input"
        input_dir.mkdir()

        projects = input_dir / "projects"
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

        print(f"\n✓ Created {len(files_created)} files")

        # Test output paths
        output_dir = tmpdir / "output"
        output_dir.mkdir()

        print("\n--- Output Paths (recursive=True) ---")
        for f in files_created:
            out_path = get_output_path(f, input_dir, output_dir, recursive=True)
            rel_input = f.relative_to(input_dir)
            rel_output = out_path.relative_to(output_dir)

            # Verify _md suffix
            has_md_suffix = "_md" in str(rel_output)

            print(f"  {str(rel_input):45s} -> {str(rel_output)}")
            print(f"     {'✓' if has_md_suffix else '✗'} Contains _md suffix: {has_md_suffix}")

        # Verify expected paths
        print("\n--- Verification ---")
        expected = [
            (input_dir / "overview.pdf", "overview.md"),
            (project_a / "spec.pdf", "projects_md/ProjectA_md/spec.md"),
            (docs / "manual.pdf", "projects_md/ProjectA_md/docs_md/manual.md"),
            (reports / "quarterly.docx", "projects_md/ProjectB_md/reports_md/quarterly.md"),
        ]

        all_correct = True
        for input_file, expected_rel in expected:
            out_path = get_output_path(input_file, input_dir, output_dir, recursive=True)
            actual_rel = str(out_path.relative_to(output_dir))
            matches = actual_rel == expected_rel
            all_correct = all_correct and matches
            print(f"  {'✓' if matches else '✗'} {expected_rel}")

        # Test non-recursive
        print("\n--- Non-recursive Mode ---")
        for f in files_created:
            out_path = get_output_path(f, input_dir, output_dir, recursive=False)
            rel_output = out_path.relative_to(output_dir)
            has_no_subdir = len(rel_output.parts) == 1
            print(f"  {f.name:25s} -> {rel_output} (flat: {'✓' if has_no_subdir else '✗'})")

        if all_correct:
            print("\n✓ SUCCESS: All paths correct with _md suffix!")
            return True
        else:
            print("\n✗ FAIL: Some paths incorrect")
            return False


if __name__ == "__main__":
    success = test_structure_preservation()
    print("\n" + "=" * 70)
    print(f"Result: {'PASS' if success else 'FAIL'}")
    print("=" * 70)
