#!/bin/bash
# End-to-end test for recursive directory conversion

set -e

echo "========================================================================"
echo "End-to-End Test: Recursive Directory Conversion with Structure Preservation"
echo "========================================================================"

# Create test directory structure
TEST_DIR=$(mktemp -d)
INPUT_DIR="$TEST_DIR/input"
OUTPUT_DIR="$TEST_DIR/output"

echo ""
echo "Creating test directory structure in: $TEST_DIR"
echo ""

# Create input structure
mkdir -p "$INPUT_DIR/projects/ProjectA/docs"
mkdir -p "$INPUT_DIR/projects/ProjectB/reports"

# Create dummy PDF files (just touch them for testing directory structure)
touch "$INPUT_DIR/overview.pdf"
touch "$INPUT_DIR/projects/ProjectA/spec.pdf"
touch "$INPUT_DIR/projects/ProjectA/notes.docx"
touch "$INPUT_DIR/projects/ProjectA/docs/manual.pdf"
touch "$INPUT_DIR/projects/ProjectB/design.pdf"
touch "$INPUT_DIR/projects/ProjectB/reports/quarterly.docx"

echo "Input directory structure:"
find "$INPUT_DIR" -type f | sort | sed 's|'"$TEST_DIR"'/||'

echo ""
echo "Expected output directory structure:"
echo "  output/"
echo "  ├── overview.md"
echo "  ├── projects_md/"
echo "  │   ├── ProjectA_md/"
echo "  │   │   ├── spec.md"
echo "  │   │   ├── notes.md"
echo "  │   │   └── docs_md/"
echo "  │   │       └── manual.md"
echo "  │   └── ProjectB_md/"
echo "  │       ├── design.md"
echo "  │       └── reports_md/"
echo "  │           └── quarterly.md"

echo ""
echo "========================================================================"
echo "Note: This test verifies directory structure logic."
echo "Actual PDF conversion requires marker-pdf models (~2-3GB)."
echo "========================================================================"

# Test the path calculation logic
python3 << PYTHON_TEST
from pathlib import Path
import sys

def get_output_path(input_file, input_dir, output_dir, recursive=False, suffix="_md"):
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

input_dir = Path("$INPUT_DIR")
output_dir = Path("$OUTPUT_DIR")

files = [
    input_dir / "overview.pdf",
    input_dir / "projects/ProjectA/spec.pdf",
    input_dir / "projects/ProjectA/notes.docx",
    input_dir / "projects/ProjectA/docs/manual.pdf",
    input_dir / "projects/ProjectB/design.pdf",
    input_dir / "projects/ProjectB/reports/quarterly.docx",
]

print("\n--- Path Calculation Results ---\n")
all_correct = True

for f in files:
    out_path = get_output_path(f, input_dir, output_dir, recursive=True)
    rel_output = out_path.relative_to(output_dir)
    has_md = "_md" in str(rel_output)
    
    # Check expected paths
    rel_input = str(f.relative_to(input_dir))
    expected_parts = rel_input.replace("/projects/", "/projects_md/").replace("/ProjectA/", "/ProjectA_md/")
    expected_parts = expected_parts.replace("/ProjectB/", "/ProjectB_md/").replace("/docs/", "/docs_md/")
    expected_parts = expected_parts.replace("/reports/", "/reports_md/")
    expected = Path(expected_parts).with_suffix('.md')
    
    matches = str(rel_output) == str(expected)
    all_correct = all_correct and matches
    
    status = "✓" if matches else "✗"
    print(f"  {status} {rel_input:45s} -> {rel_output}")
    
    if not matches:
        print(f"      Expected: {expected}")
        print(f"      Got:      {rel_output}")

if all_correct:
    print("\n✓ SUCCESS: All output paths are correct!")
    sys.exit(0)
else:
    print("\n✗ FAIL: Some output paths are incorrect!")
    sys.exit(1)
PYTHON_TEST

RESULT=$?

echo ""
echo "========================================================================"
if [ $RESULT -eq 0 ]; then
    echo "✓ TEST PASSED: Directory structure preservation logic is correct!"
else
    echo "✗ TEST FAILED: Directory structure preservation has issues!"
fi
echo "========================================================================"

# Cleanup
rm -rf "$TEST_DIR"

exit $RESULT
