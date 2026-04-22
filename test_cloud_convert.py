#!/usr/bin/env python3
"""Test script: convert papers/paper.pdf using cloud API with key import.

This script demonstrates:
1. API key import (from string, file, or environment)
2. Key validation before use
3. PDF conversion with cloud engines (Doc2x, MinerU Cloud)
4. Automatic PDF splitting for large documents
5. Markdown aggregation with image/formula preservation

Usage:
    # Convert with API key
    python test_cloud_convert.py --key YOUR_KEY

    # Import key from .env file
    python test_cloud_convert.py --key-file .env

    # Use MinerU Cloud instead of Doc2x
    python test_cloud_convert.py --engine mineru-cloud --key YOUR_KEY

    # Skip key validation (faster)
    python test_cloud_convert.py --key YOUR_KEY --no-validate

    # List configured keys
    python test_cloud_convert.py --list-keys
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Ensure we use local source, not installed package
sys.path.insert(0, str(Path(__file__).parent / "src"))


# ============================================================
# API Key Import / Management
# ============================================================

class APIKeyManager:
    """Manage API keys for cloud converters.

    Supports:
    - Direct key string
    - Environment variable import
    - Key file import (.env, .key, .txt)
    - Key export to environment
    """

    KEYS = {
        "doc2x": "DOC2X_API_KEY",
        "mineru-cloud": "MINERU_API_KEY",
        "llamaparse": "LLAMA_CLOUD_API_KEY",
        "mathpix": "MATHPIX_APP_KEY",
    }

    @classmethod
    def validate_key(cls, key: str, engine: str = "doc2x") -> tuple[bool, str]:
        """Validate API key by testing against the service.

        Parameters
        ----------
        key : str
            The API key to validate.
        engine : str
            Target engine name.

        Returns
        -------
        tuple[bool, str]
            (is_valid, message).
        """
        import requests

        if engine == "doc2x":
            try:
                # Doc2x doesn't have a user info endpoint, so we validate by
                # checking if the key format looks correct
                if not key.startswith("sk-"):
                    return False, "Invalid key format (should start with 'sk-')"
                # We can't validate without uploading, so just check format
                return True, "Key format valid (Doc2x has no user info endpoint)"
            except Exception as e:
                return False, str(e)

        elif engine == "mineru-cloud":
            try:
                resp = requests.get(
                    "https://mineru.net/api/v1/user/info",
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=10,
                )
                data = resp.json()
                if data.get("success"):
                    return True, "Key valid"
                return False, data.get("msg", "Authentication failed")
            except Exception as e:
                return False, str(e)

        return False, f"Unknown engine: {engine}"

    @classmethod
    def import_key(cls, key: str, engine: str = "doc2x", validate: bool = True) -> bool:
        """Import an API key string and set environment variable.

        Parameters
        ----------
        key : str
            The API key value.
        engine : str
            Target engine name (doc2x, mineru-cloud, llamaparse, mathpix).
        validate : bool
            Whether to validate the key before importing (default: True).

        Returns
        -------
        bool
            True if key was imported successfully.
        """
        env_var = cls.KEYS.get(engine)
        if not env_var:
            print(f"[KeyManager] Unknown engine: {engine}")
            return False

        if not key or not key.strip():
            print("[KeyManager] Empty key provided")
            return False

        key = key.strip()

        # Validate key if requested
        if validate:
            print(f"[KeyManager] Validating key for {engine}...")
            is_valid, message = cls.validate_key(key, engine)
            if not is_valid:
                print(f"[KeyManager] ✗ Key validation failed: {message}")
                print(f"[KeyManager] Proceeding anyway (setting env var)")
            else:
                print(f"[KeyManager] ✓ Key validated: {message}")

        os.environ[env_var] = key
        masked = key[:5] + "..." + key[-4:] if len(key) > 9 else "***"
        print(f"[KeyManager] Imported key for {engine} -> {env_var}")
        print(f"[KeyManager] Key: {masked}")
        return True

    @classmethod
    def import_from_file(cls, filepath: str, engine: str = "doc2x") -> bool:
        """Import API key from a file.

        Supports formats:
        - Plain text: just the key
        - .env: KEY=value
        - JSON: {"key": "..."}

        Parameters
        ----------
        filepath : str
            Path to the key file.
        engine : str
            Target engine name.

        Returns
        -------
        bool
            True if key was imported successfully.
        """
        path = Path(filepath)
        if not path.exists():
            print(f"[KeyManager] File not found: {filepath}")
            return False

        content = path.read_text().strip()

        # Try .env format: KEY=value
        if "=" in content and not content.startswith("{"):
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() in cls.KEYS.values():
                            os.environ[k.strip()] = v.strip()
                            print(f"[KeyManager] Loaded {k.strip()} from {filepath}")
                            return True

        # Try JSON format
        if content.startswith("{"):
            import json
            data = json.loads(content)
            env_var = cls.KEYS.get(engine)
            if env_var and env_var in data:
                os.environ[env_var] = data[env_var]
                print(f"[KeyManager] Loaded {env_var} from {filepath}")
                return True

        # Plain text - just the key
        if content:
            return cls.import_key(content, engine)

        print(f"[KeyManager] No valid key found in {filepath}")
        return False

    @classmethod
    def check_available(cls, engine: str = "doc2x") -> bool:
        """Check if API key is available for the engine."""
        env_var = cls.KEYS.get(engine)
        if not env_var:
            return False
        return bool(os.environ.get(env_var))

    @classmethod
    def list_keys(cls) -> dict[str, str]:
        """List all configured keys (masked)."""
        result = {}
        for engine, env_var in cls.KEYS.items():
            key = os.environ.get(env_var, "")
            if key:
                masked = key[:5] + "..." + key[-4:] if len(key) > 9 else "***"
                result[engine] = masked
            else:
                result[engine] = "(not set)"
        return result


# ============================================================
# Cloud Conversion Test
# ============================================================

def convert_with_cloud(
    pdf_path: str,
    output_dir: str,
    engine: str = "doc2x",
    api_key: str | None = None,
    max_pages: int = 50,
) -> dict:
    """Convert PDF to Markdown using cloud engine.

    Parameters
    ----------
    pdf_path : str
        Path to input PDF.
    output_dir : str
        Directory for output markdown and images.
    engine : str
        Cloud engine: doc2x, mineru-cloud.
    api_key : str or None
        API key (if not set in environment).
    max_pages : int
        Max pages per chunk for splitting.

    Returns
    -------
    dict
        Result with success, output_path, page_count, image_count.
    """
    from nuoyi.converter import (
        Doc2xConverter,
        MinerUCloudConverter,
        aggregate_markdown,
        split_pdf,
    )
    from nuoyi.utils import clean_markdown, save_images_and_update_markdown

    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Import key if provided
    if api_key:
        if not APIKeyManager.import_key(api_key, engine):
            return {"success": False, "error": "Failed to import API key"}

    if not APIKeyManager.check_available(engine):
        return {
            "success": False,
            "error": f"No API key available for {engine}. Set env var or pass --key.",
        }

    print(f"\n{'='*60}")
    print(f"Converting: {pdf_path.name}")
    print(f"Engine: {engine}")
    print(f"Output: {output_dir}")
    print(f"{'='*60}\n")

    # Check if PDF needs splitting
    import fitz
    doc = fitz.open(str(pdf_path))
    page_count = len(doc)
    doc.close()

    needs_split = page_count > max_pages

    if needs_split:
        print(f"[Split] PDF has {page_count} pages, splitting into chunks of {max_pages}...")
        split_files = split_pdf(str(pdf_path), max_pages=max_pages)
    else:
        split_files = [str(pdf_path)]

    # Convert each chunk
    results = []
    for i, chunk_path in enumerate(split_files, 1):
        print(f"\n[Chunk {i}/{len(split_files)}] Converting: {Path(chunk_path).name}")

        try:
            if engine == "doc2x":
                converter = Doc2xConverter()
            elif engine == "mineru-cloud":
                converter = MinerUCloudConverter()
            else:
                return {"success": False, "error": f"Unknown engine: {engine}"}

            md_text, images = converter.convert_file(chunk_path)
            results.append((md_text, images))

            img_count = len(images) if images else 0
            print(f"[Chunk {i}] ✓ Success - {len(md_text)} chars, {img_count} images")

        except Exception as e:
            print(f"[Chunk {i}] ✗ Failed: {e}")
            return {"success": False, "error": str(e), "chunk": i}

    # Aggregate results
    if len(results) > 1:
        print(f"\n[Aggregate] Merging {len(results)} chunks...")
        final_md, all_images = aggregate_markdown(results)
    else:
        final_md, all_images = results[0]

    final_md = clean_markdown(final_md)

    # Save output
    output_md = output_dir / f"{pdf_path.stem}_{engine}.md"
    images_dir = output_dir / f"{pdf_path.stem}_{engine}_images"

    if all_images:
        final_md = save_images_and_update_markdown(
            final_md, all_images, output_dir, f"{pdf_path.stem}_{engine}_images"
        )

    output_md.write_text(final_md, encoding="utf-8")

    # Stats
    formula_count = final_md.count("\\(") + final_md.count("\\[") + final_md.count("$")
    image_count = len(all_images) if all_images else 0

    print(f"\n{'='*60}")
    print(f"Conversion Complete!")
    print(f"  Output: {output_md}")
    print(f"  Pages: {page_count}")
    print(f"  Markdown size: {len(final_md):,} chars")
    print(f"  Images: {image_count}")
    print(f"  Formulas: ~{formula_count}")
    print(f"{'='*60}\n")

    return {
        "success": True,
        "output_path": str(output_md),
        "images_dir": str(images_dir) if all_images else None,
        "page_count": page_count,
        "char_count": len(final_md),
        "image_count": image_count,
        "formula_count": formula_count,
    }


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Test cloud PDF-to-Markdown conversion with API key import",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert with hardcoded key
  python test_cloud_convert.py

  # Convert with custom key
  python test_cloud_convert.py --key your-api-key

  # Use MinerU Cloud instead of Doc2x
  python test_cloud_convert.py --engine mineru-cloud --key your-key

  # Import key from file
  python test_cloud_convert.py --key-file .env

  # Convert specific PDF
  python test_cloud_convert.py --pdf my_paper.pdf
        """,
    )

    parser.add_argument(
        "--key",
        type=str,
        default=None,
        help="API key for cloud converter (default: prompts if not set)",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip API key validation before import",
    )
    parser.add_argument(
        "--key-file",
        type=str,
        help="Import API key from file (.env, .key, .txt)",
    )
    parser.add_argument(
        "--engine",
        choices=["doc2x", "mineru-cloud"],
        default="doc2x",
        help="Cloud engine to use (default: doc2x)",
    )
    parser.add_argument(
        "--pdf",
        type=str,
        default="papers/paper.pdf",
        help="Path to PDF file (default: papers/paper.pdf)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="papers",
        help="Output directory (default: papers/)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="Max pages per chunk for splitting (default: 50)",
    )
    parser.add_argument(
        "--list-keys",
        action="store_true",
        help="List configured API keys and exit",
    )

    args = parser.parse_args()

    # List keys mode
    if args.list_keys:
        print("Configured API Keys:")
        for engine, status in APIKeyManager.list_keys().items():
            print(f"  {engine}: {status}")
        return

    # Import key from file if specified
    if args.key_file:
        if not APIKeyManager.import_from_file(args.key_file, args.engine):
            print("Failed to import key from file")
            sys.exit(1)
    elif args.key:
        # Import key directly
        validate = not args.no_validate
        if not APIKeyManager.import_key(args.key, args.engine, validate=validate):
            print("Failed to import API key")
            sys.exit(1)
    else:
        # Try environment variable
        env_var = APIKeyManager.KEYS.get(args.engine)
        if env_var and os.environ.get(env_var):
            print(f"[KeyManager] Using key from environment variable {env_var}")
        else:
            print(f"\nError: No API key provided for {args.engine}")
            print(f"  Option 1: Pass --key YOUR_KEY")
            print(f"  Option 2: Set environment variable {APIKeyManager.KEYS[args.engine]}")
            print(f"  Option 3: Use --key-file .env")
            sys.exit(1)

    # Show key status
    print("\n[Status] API Keys:")
    for engine, status in APIKeyManager.list_keys().items():
        print(f"  {engine}: {status}")

    # Check PDF exists
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"\nError: PDF not found: {pdf_path}")
        sys.exit(1)

    # Run conversion
    result = convert_with_cloud(
        pdf_path=str(pdf_path),
        output_dir=args.output_dir,
        engine=args.engine,
        api_key=args.key,
        max_pages=args.max_pages,
    )

    if not result["success"]:
        error = result.get("error", "Unknown error")
        print(f"\n{'='*60}")
        print(f"Conversion Failed")
        print(f"{'='*60}")
        print(f"Error: {error}")
        print()

        # Provide troubleshooting
        if "unauthorized" in error.lower() or "认证" in error or "token" in error.lower() or "expired" in error.lower():
            print("Troubleshooting - API Key Issues:")
            print("  1. Your API key may be expired or invalid")
            print("  2. Get a new key from:")
            print("     - Doc2x: https://doc2x.noedgeai.com/")
            print("     - MinerU: https://mineru.net/")
            print("  3. Run with a valid key:")
            print(f"     python test_cloud_convert.py --engine {args.engine} --key YOUR_NEW_KEY")
            print()
        elif "timeout" in error.lower():
            print("Troubleshooting - Timeout:")
            print("  1. The PDF may be too large for the API")
            print("  2. Try splitting with --max-pages 10")
            print("  3. Check your internet connection")
            print()
        else:
            print("Troubleshooting:")
            print("  1. Check the error message above")
            print("  2. Try with --no-validate to skip key validation")
            print("  3. Check API service status")
            print()

        sys.exit(1)

    # Verify output
    output_path = Path(result["output_path"])
    if not output_path.exists():
        print(f"\nError: Output file not created: {output_path}")
        sys.exit(1)

    content = output_path.read_text(encoding="utf-8")

    # Quality checks
    print("\n[Quality Check]")
    checks = {
        "Has content": len(content) > 100,
        "Has formulas (LaTeX)": "\\(" in content or "\\[" in content or "$" in content,
        "Has headings": "#" in content,
        "Has image refs": "![" in content or "image_" in content,
        "Has tables": "<table>" in content or ("|" in content and "---" in content),
    }

    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n✓ All quality checks passed!")
    else:
        print("\n⚠ Some quality checks failed (may be normal for this document)")

    print(f"\nOutput saved to: {output_path}")
    print(f"Preview (first 500 chars):\n{'-'*40}")
    print(content[:500])
    print(f"{'-'*40}...")


if __name__ == "__main__":
    main()
