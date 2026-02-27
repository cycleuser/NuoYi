"""
NuoYi - Entry point for running as a module.

Usage:
    python -m nuoyi input.pdf -o output.md
    python -m nuoyi --gui
"""

from nuoyi.cli import main

if __name__ == "__main__":
    main()
