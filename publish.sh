#!/bin/bash
# NuoYi - Build and upload to PyPI
# Usage: ./publish.sh [test|prod]

set -e

TARGET="${1:-test}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== NuoYi PyPI Publisher ==="

# Read version from __init__.py
VERSION=$(grep -oP '__version__\s*=\s*"\K[^"]+' src/nuoyi/__init__.py)
echo "Version: $VERSION"

# Step 1: Clean old builds
echo ""
echo "[1/4] Cleaning old builds..."
rm -rf dist/ build/ src/*.egg-info

# Step 2: Install build tools
echo "[2/4] Checking build tools..."
python -m pip install --quiet build twine

# Step 3: Build
echo "[3/4] Building sdist and wheel..."
python -m build

echo ""
echo "Built files:"
ls -lh dist/

# Step 4: Upload
echo ""
if [ "$TARGET" = "prod" ]; then
    echo "[4/4] Uploading to PyPI (production)..."
    echo "WARNING: This will publish to the real PyPI!"
    read -p "Continue? [y/N] " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        python -m twine upload dist/*
        echo ""
        echo "Done! Install with: pip install nuoyi==$VERSION"
    else
        echo "Cancelled."
    fi
elif [ "$TARGET" = "test" ]; then
    echo "[4/4] Uploading to TestPyPI..."
    python -m twine upload --repository testpypi dist/*
    echo ""
    echo "Done! Test install with:"
    echo "  pip install -i https://test.pypi.org/simple/ nuoyi==$VERSION"
else
    echo "[4/4] Skipping upload (unknown target: $TARGET)"
    echo "Usage: ./publish.sh [test|prod]"
fi
