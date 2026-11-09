#!/usr/bin/env python3
"""Read the dataset JSON files and print a selection without contacting Insula.

Run from the repository root:
    python examples/01_read_catalogues.py
    python examples/01_read_catalogues.py --category radiometry --location LYB1
"""
import argparse
import sys
from pathlib import Path

# Make repository modules available when this file is executed directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dataset import CATEGORIES, load_catalogues
from download_and_organize import select_entries


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--category", choices=CATEGORIES)
    parser.add_argument("--location", help="Site code, for example LCFR or BAOT")
    parser.add_argument("--session", help="Session identifier, for example Session1")
    args = parser.parse_args(argv)
    try:
        entries = select_entries(load_catalogues(), category=args.category,
                                 location=args.location, session=args.session)
    except ValueError as exc:
        parser.error(str(exc))
    for entry in entries:
        metadata = entry["metadata"]
        print(f"{entry['category']}/{entry['location']}/{entry['session']}")
        print(f"  Product: {metadata['session_id']}")
        print(f"  Acquisition: {metadata.get('acquisition_start', 'Unknown')}")
        print(f"  Defined crops: {len(entry.get('bbox') or [])}")
    print(f"\n{len(entries)} category entries; "
          f"{len({e['metadata']['session_id'] for e in entries})} unique products")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
