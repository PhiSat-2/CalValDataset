#!/usr/bin/env python3
"""Show or run a catalogue update using the sites configured in sites.csv.

Run from the repository root:
    python examples/03_update_datasets.py
    python examples/03_update_datasets.py --only LCFR --run
    python examples/03_update_datasets.py --run

Add sites and categories to sites.csv and enter Insula credentials in .s5cfg
before running a live update. No imagery is downloaded by an update.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dataset import ROOT, read_sites


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="Check one site by name or location code")
    parser.add_argument("--run", action="store_true", help="Connect to Insula and update the JSON catalogues")
    args = parser.parse_args(argv)
    sites = read_sites(ROOT / "sites.csv")
    selected = [site for site in sites if not args.only or args.only.casefold() in (site.name.casefold(), site.location.casefold())]
    if not selected:
        parser.error(f"Unknown site or location code: {args.only}")
    for site in selected:
        print(f"{site.location}: {site.name} ({site.latitude}, {site.longitude}) -> {', '.join(site.categories)}")
    if not args.run:
        print("\nPreview only. Add --run to query Insula, update the catalogues and write the report.")
        return 0
    from update_datasets import main as update_main
    return update_main(["--only", args.only] if args.only else [])


if __name__ == "__main__":
    raise SystemExit(main())
