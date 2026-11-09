#!/usr/bin/env python3
"""Preview or download a sample session, or the entire dataset.

Run from the repository root:
    python examples/02_download_products.py
    python examples/02_download_products.py --download --unzip
    python examples/02_download_products.py --all --download --unzip

Set your Insula username and password in .s5cfg before downloading.
"""
import argparse
import sys
from pathlib import Path

# Reuse the production downloader rather than duplicating its implementation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dataset import CATEGORIES
from download_and_organize import main as download_main


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--category", choices=CATEGORIES, default="image_quality")
    parser.add_argument("--location", default="BAOT")
    parser.add_argument("--session", default="Session1")
    parser.add_argument("--all", action="store_true", help="Select the entire dataset instead of the sample session")
    parser.add_argument("--download", action="store_true", help="Download the selection; otherwise only print a preview")
    parser.add_argument("--unzip", action="store_true", help="Extract ZIP files and organize TIFFs at the declared band paths")
    args = parser.parse_args(argv)
    command = [] if args.all else ["--category", args.category, "--location", args.location, "--session", args.session]
    if args.download:
        command.append("--download")
    if args.unzip:
        command.append("--unzip")
    return download_main(command)


if __name__ == "__main__":
    raise SystemExit(main())
