"""The calval command-line interface."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .catalogue import CATEGORIES, load_catalogues, load_sites, read_json, validate_config, write_json
from .download import download_entries, select_entries
from .paths import credential_path, ensure_workspace


def common_options(parser, *, child=False):
    default = argparse.SUPPRESS if child else None
    parser.add_argument("--data-dir", type=Path, default=default,
                        help="Writable catalogues, sites, reports and downloads directory (or CALVAL_DATA_DIR)")
    parser.add_argument("--config", type=Path, default=default,
                        help="Insula .s5cfg file (or CALVAL_CONFIG)")
    parser.add_argument("--personal-sites", type=Path, default=default,
                        help="Additional personal CSV; default: sites.personal.csv beside the base list")


def selection_options(parser):
    parser.add_argument("--category", choices=CATEGORIES)
    parser.add_argument("--site", "--location", dest="site", help="Site code or name, for example LCFR")
    parser.add_argument("--session", help="Session identifier, for example Session1")
    parser.add_argument("--product", action="append", help="Exact product name; repeat for multiple products")


def make_parser():
    parser = argparse.ArgumentParser(prog="calval", description="Browse, download and update PhiSat-2 CalVal catalogues.")
    parser.add_argument("--version", action="version", version=f"phisat2-calvaldataset {__version__}")
    common_options(parser)
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("init", help="Create local catalogues, sites.csv and a credential template")
    common_options(initialize, child=True)
    listing = commands.add_parser("list", help="List local product metadata without connecting to Insula")
    common_options(listing, child=True)
    selection_options(listing)
    listing.add_argument("--format", choices=("table", "json"), default="table")
    download = commands.add_parser("download", help="Download selected products or the complete dataset")
    common_options(download, child=True)
    selection_options(download)
    download.add_argument("--all", action="store_true", help="Download the entire dataset")
    download.add_argument("--json", type=Path, help="Read an edited JSON catalogue selection")
    download.add_argument("--unzip", action="store_true", help="Extract and organize the eight TIFF bands")
    download.add_argument("--dry-run", action="store_true", help="Preview without authentication or downloads")
    update = commands.add_parser("update", help="Search Insula and update the local JSON catalogues")
    common_options(update, child=True)
    scope = update.add_mutually_exclusive_group(required=True)
    scope.add_argument("--site", "--location", dest="site", help="Site code or name")
    scope.add_argument("--all", action="store_true", help="Check every site in the site list")
    update.add_argument("--sites", type=Path, help="Alternative sites.csv; default: <data-dir>/sites.csv")
    update.add_argument("--report", type=Path, help="Default: <data-dir>/reports/last_update.json")
    return parser


def resolve_site(root: Path, requested: str | None, sites_path: Path | None = None,
                 personal_path: Path | None = None) -> str | None:
    if not requested:
        return None
    for site in load_sites(root, sites_path, personal_path):
        if requested.casefold() in (site.name.casefold(), site.location.casefold()):
            return site.location
    # Retained products can still be downloaded after their site leaves the search list.
    if sites_path is None:
        for document in load_catalogues(root).values():
            for entry in document["entries"]:
                if requested.casefold() in (entry["location"].casefold(), entry["metadata"].get("site", "").casefold()):
                    return entry["location"]
    raise ValueError(f"Unknown site name or code: {requested}")


def display_entries(entries: list[dict], *, output_format="table") -> None:
    if output_format == "json":
        print(json.dumps({"entries": entries}, ensure_ascii=False, indent=2))
        return
    print("CATEGORY       SITE   SESSION     ACQUISITION  PRODUCT")
    for entry in entries:
        metadata = entry["metadata"]
        print(f"{entry['category']:<14} {entry['location']:<6} {entry['session']:<11} "
              f"{metadata.get('acquisition_date', ''):<12} {metadata['session_id']}")
    print(f"\n{len(entries)} category entries; {len({e['metadata']['session_id'] for e in entries})} unique products")


def make_searcher(config: Path):
    validate_config(config)
    from phidown import PhiSat2Searcher
    return PhiSat2Searcher(config_file=str(config))


def run_update(args, root: Path) -> int:
    from .update import LOGGER, print_report, update_catalogues
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
    if not LOGGER.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        LOGGER.addHandler(handler)
    report_path = args.report or root / "reports/last_update.json"
    try:
        sites = load_sites(root, args.sites, args.personal_sites)
        site_code = resolve_site(root, args.site, args.sites, args.personal_sites)
        searcher = make_searcher(credential_path(root, args.config))
        report = update_catalogues(searcher, sites, root, report_path, only=site_code)
        print_report(report, report_path)
        return 1 if report["failed_sites"] else 0
    except Exception as exc:
        try:
            baseline = read_json(report_path).get("sites_configuration", {}) if report_path.is_file() else {}
        except (ValueError, OSError):
            baseline = {}
        write_json(report_path, {"status": "ERROR", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
                                "sites_configuration": baseline, "error": f"{type(exc).__name__}: {exc}"})
        raise


def execute(args) -> int:
    root = ensure_workspace(args.data_dir)
    if args.command == "init":
        print(f"Data directory: {root}")
        print(f"Site list: {root / 'sites.csv'}")
        print(f"Personal sites: copy {root / 'sites.personal.csv.example'} to sites.personal.csv, then add your rows.")
        print(f"Copy {root / '.s5cfg.example'} to {root / '.s5cfg'} and enter your Insula credentials.")
        return 0
    if args.command == "update":
        return run_update(args, root)
    if args.command == "download" and args.all and any((args.category, args.site, args.session, args.product, args.json)):
        raise ValueError("--all cannot be combined with selection filters or --json")
    documents = load_catalogues(root)
    source_path = getattr(args, "json", None)
    if source_path:
        if args.unzip and source_path.resolve().is_relative_to(Path(__file__).resolve().parent):
            raise ValueError("Use a writable JSON selection outside the installed package")
        source = read_json(source_path)
        documents = {category: {"entries": [e for e in source["entries"] if e["category"] == category]}
                     for category in CATEGORIES}
        if sum(len(doc["entries"]) for doc in documents.values()) != len(source["entries"]):
            raise ValueError("Input JSON contains an unknown category")
    site_code = resolve_site(root, args.site, personal_path=args.personal_sites)
    selected = select_entries(documents, category=args.category, location=site_code,
                              session=args.session, products=args.product, allow_empty=args.command == "list")
    display_entries(selected, output_format=getattr(args, "format", "table"))
    if args.command == "list" or args.dry_run:
        return 0
    searcher = make_searcher(credential_path(root, args.config))
    failures = download_entries(selected, root, searcher, unzip=args.unzip)
    if args.unzip:
        if source_path:
            write_json(source_path, source)
        else:
            for category, document in documents.items():
                write_json(root / category / f"{category}_dataset.json", document)
    return 1 if failures else 0


def main(argv=None) -> int:
    args = make_parser().parse_args(argv)
    try:
        return execute(args)
    except (ValueError, KeyError, OSError, RuntimeError) as exc:
        print(f"calval: {exc}", file=sys.stderr)
        return 2
