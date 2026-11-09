#!/usr/bin/env python3
"""Check every configured site on Insula, update CalVal JSON files and report changes."""
from __future__ import annotations

import argparse
import copy
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from shapely import wkt as shapely_wkt
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry

from dataset import (
    ROOT, Site, expected_band_paths, load_catalogues, product_name, read_json, read_site_lists,
    validate_config, write_json,
)

LOGGER = logging.getLogger("calval-update")

def make_candidate_aoi(site: Site, half_width_degrees: float) -> str:
    """Build an AOI ONLY for candidate retrieval, not for inclusion."""
    if half_width_degrees <= 0:
        raise ValueError("Candidate AOI half-width must be positive")
    x, y, d = site.longitude, site.latitude, half_width_degrees
    if y - d < -90 or y + d > 90 or x - d < -180 or x + d > 180:
        raise ValueError(f"Candidate AOI crosses global coordinate bounds for {site.name}")
    return (
        f"POLYGON(({x-d:.10f} {y-d:.10f},"
        f"{x+d:.10f} {y-d:.10f},"
        f"{x+d:.10f} {y+d:.10f},"
        f"{x-d:.10f} {y+d:.10f},"
        f"{x-d:.10f} {y-d:.10f}))"
    )


def footprint_geometry(value: Any) -> BaseGeometry:
    """Convert GeoFootprint from GeoJSON dict, JSON string, or WKT string."""
    if isinstance(value, BaseGeometry):
        geom = value
    elif isinstance(value, dict):
        geom = shape(value)
    elif isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            raise ValueError("Empty footprint")
        geom = shape(json.loads(candidate)) if candidate.startswith("{") else shapely_wkt.loads(candidate)
    else:
        raise ValueError(f"Missing/unrecognized footprint type: {type(value).__name__}")
    if geom.is_empty or not geom.is_valid:
        raise ValueError("Empty or invalid GeoFootprint; cannot safely verify exact coverage")
    if geom.geom_type not in {"Polygon", "MultiPolygon", "GeometryCollection"}:
        raise ValueError(f"Unexpected footprint geometry: {geom.geom_type}")
    return geom


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        if bool(pd.isna(value)):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


def dates_from_row(row: dict[str, Any]) -> tuple[str, str, str]:
    contents = row.get("ContentDate")
    if isinstance(contents, str) and contents.lstrip().startswith("{"):
        contents = json.loads(contents)
    if not isinstance(contents, dict):
        contents = {}
    start = as_text(contents.get("Start"))
    end = as_text(contents.get("End"))
    return (start[:10] if start else "", start, end)


def _pagination_total_pages(payload: Any) -> int | None:
    if not isinstance(payload, dict):
        return None
    block = payload.get("page")
    if isinstance(block, dict):
        total = block.get("totalPages")
        if isinstance(total, int):
            return total
    return None


def search_one_site(
    searcher: Any,
    site: Site,
    *,
    product_type: str = "L1",
    page_size: int = 100,
    max_pages: int = 500,
    candidate_half_width: float = 0.0001,
) -> list[dict[str, str | float]]:
    """Search all candidate pages and retain ONLY footprints covering this point."""
    point = Point(site.longitude, site.latitude)
    aoi = make_candidate_aoi(site, candidate_half_width)
    found: dict[str, dict[str, str | float]] = {}
    page_signatures: set[tuple[str, ...]] = set()

    for page in range(max_pages):
        batch = searcher.query_catalogue(
            product_type=product_type,
            aoi_wkt=aoi,
            results_per_page=page_size,
            page=page,
        )
        if not isinstance(batch, pd.DataFrame):
            raise RuntimeError("Unexpected result from Phi-Down: expected pandas DataFrame")
        raw = getattr(searcher, "json_data", None)
        if isinstance(raw, dict) and not isinstance(raw.get("features", []), list):
            raise RuntimeError("Unexpected Insula response: 'features' is not a list")
        if batch.empty:
            return list(found.values())

        for field in ("GeoFootprint", "Id", "Name"):
            if field not in batch.columns:
                raise RuntimeError(f"Catalogue lacks required column {field!r}")

        # Guard against servers that silently ignore the requested page number.
        signature = tuple(sorted(as_text(v) for v in batch["Id"].tolist()))
        if signature in page_signatures:
            raise RuntimeError("Repeated catalogue page: pagination may be ignored; results incomplete")
        page_signatures.add(signature)

        for row in batch.to_dict(orient="records"):
            name = as_text(row["Name"])
            product_id = as_text(row["Id"])
            if not product_id and not name:
                raise RuntimeError("A catalogue product lacks both ID and Name")
            try:
                geom = footprint_geometry(row["GeoFootprint"])
            except Exception as exc:
                raise RuntimeError(f"Cannot validate footprint for product {name or product_id}: {exc}") from exc
            if not geom.covers(point):
                continue
            acq_date, start, end = dates_from_row(row)
            dedupe_key = product_id or (name + "|" + start)
            found[dedupe_key] = {
                "Site": site.name,
                "Country": site.country,
                "Latitude": site.latitude,
                "Longitude": site.longitude,
                "Product ID": product_id,
                "Product name": name,
                "Product type": as_text(row.get("ProductType")) or product_type,
                "Acquisition date": acq_date,
                "Acquisition start": start,
                "Acquisition end": end,
                "Catalogue URL": as_text(row.get("PlatformUrl")),
            }

        total_pages = _pagination_total_pages(raw)
        LOGGER.info("  page %d | candidates: %d | exact matches so far: %d", page + 1, len(batch), len(found))
        if total_pages is not None and page + 1 >= total_pages:
            return list(found.values())
        if len(batch) < page_size:
            return list(found.values())

    raise RuntimeError(f"Reached max-pages={max_pages}; cannot guarantee complete results")


def merge_site(documents: dict, site: Site, rows: list[dict]) -> tuple[dict, dict]:
    """Stage a site's complete results; preserve crops, bands and existing sessions."""
    staged = copy.deepcopy(documents)
    changes = {"added_entries": [], "updated_entries": 0}
    for category in site.categories:
        entries = staged[category]["entries"]
        index = {(e["location"], product_name(e["metadata"]["session_id"])): e for e in entries}
        next_session = max((int(e["session"][7:]) for e in entries if e["location"] == site.location), default=0)
        for row in sorted(rows, key=lambda row: product_name(row["Product name"])):
            name = product_name(row["Product name"])
            key = site.location, name
            is_new = key not in index
            if is_new:
                next_session += 1
                session = f"Session{next_session}"
                entry = {
                    "category": category, "location": site.location, "session": session,
                    "directory": f"{category}/{site.location}/{session}",
                    "bbox": [],
                    "metadata": {"payload": "PSat2", "resolution": 4.75, "session_id": name},
                }
                entries.append(entry)
                index[key] = entry
                changes["added_entries"].append({"category": category, "session": session, "product": name})
            else:
                entry = index[key]
            entry["bands"] = expected_band_paths(entry)
            before = copy.deepcopy(entry["metadata"])
            timestamps = re.search(r"_(\d{14})_(\d{14})_", name)
            inferred = ["", ""] if timestamps is None else [
                datetime.strptime(token, "%Y%m%d%H%M%S").strftime("%Y-%m-%dT%H:%M:%SZ")
                for token in timestamps.groups()
            ]
            start = row.get("Acquisition start") or inferred[0]
            end = row.get("Acquisition end") or inferred[1]
            entry["metadata"].update({
                "resolution": 4.75,
                "site": site.name, "country": site.country,
                "latitude": site.latitude, "longitude": site.longitude,
                "product_name": name + ".zip", "product_type": row.get("Product type") or "L1",
                "acquisition_start": start, "acquisition_end": end, "acquisition_date": start[:10],
            })
            # An empty API field must not erase previously collected information.
            for source, target in (("Product ID", "product_id"), ("Catalogue URL", "catalogue_url")):
                if row.get(source):
                    entry["metadata"][target] = row[source]
            if not is_new and entry["metadata"] != before:
                changes["updated_entries"] += 1
        entries.sort(key=lambda e: (e["location"], int(e["session"][7:])))
    return staged, changes


def update_catalogues(searcher, sites: list[Site], root: Path = ROOT,
                      report_path: Path | None = None, *, only: str | None = None,
                      page_size: int = 100, max_pages: int = 500) -> dict:
    report_path = report_path or root / "reports/last_update.json"
    previous = read_json(report_path) if report_path.is_file() else {}
    documents = load_catalogues(root)
    original = copy.deepcopy(documents)
    known = {e["metadata"]["session_id"] for d in documents.values() for e in d["entries"]}
    selected = [s for s in sites if not only or only.casefold() in (s.name.casefold(), s.location.casefold())]
    if not selected:
        raise ValueError(f"Unknown site or location code: {only}")
    previous_sites = previous.get("sites_configuration", {})
    configuration = {s.location: s.configuration() for s in sites}
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "first_check": not bool(previous_sites),
        "sites_configuration": configuration,
        "configuration_changes": {
            "added": sorted(set(configuration) - set(previous_sites)) if previous_sites else [],
            "changed": sorted(k for k in configuration.keys() & previous_sites.keys() if configuration[k] != previous_sites[k]),
            "removed_from_site_list": sorted(set(previous_sites) - set(configuration)),
        },
        "sites": [],
    }
    for site in selected:
        LOGGER.info("Checking %s (%s)", site.name, site.location)
        try:
            rows = search_one_site(searcher, site, page_size=page_size, max_pages=max_pages)
            found = {product_name(row["Product name"]) for row in rows}
            old_site_products = {e["metadata"]["session_id"] for d in documents.values()
                                 for e in d["entries"] if e["location"] == site.location}
            documents, changes = merge_site(documents, site, rows)
            report["sites"].append({
                "site": site.name, "location": site.location, "status": "OK",
                "products_found": len(found), **changes,
                "previous_products_not_returned": sorted(old_site_products - found),
            })
            LOGGER.info("  %d found, %d category entries added, %d metadata entries updated",
                        len(found), len(changes["added_entries"]), changes["updated_entries"])
        except Exception as exc:
            report["sites"].append({"site": site.name, "location": site.location,
                                    "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"})
            LOGGER.error("  ERROR: %s", exc)
    all_names = {e["metadata"]["session_id"] for d in documents.values() for e in d["entries"]}
    report["new_products"] = sorted(all_names - known)
    report["added_entries"] = sum(len(s.get("added_entries", [])) for s in report["sites"])
    report["updated_entries"] = sum(s.get("updated_entries", 0) for s in report["sites"])
    report["failed_sites"] = sum(s["status"] == "ERROR" for s in report["sites"])
    report["dataset_changed"] = documents != original
    config_changed = any(report["configuration_changes"].values())
    report["status"] = "PARTIAL_ERROR" if report["failed_sites"] else (
        "UPDATED" if report["dataset_changed"] or config_changed else "NO_UPDATES")
    # Only catalogue JSON files are written here: no acquisition folders or imagery.
    for category, document in documents.items():
        path = root / category / f"{category}_dataset.json"
        if document != original[category] or not path.is_file():
            write_json(path, document)
    write_json(report_path, report)
    return report


def print_report(report: dict, report_path: Path) -> None:
    print(f"\n{report['status']}: {len(report['new_products'])} new unique products, "
          f"{report['added_entries']} added category entries, "
          f"{report['updated_entries']} metadata updates, {report['failed_sites']} failed sites.")
    changes = report["configuration_changes"]
    print(f"Sites: {len(changes['added'])} added, {len(changes['changed'])} modified, "
          f"{len(changes['removed_from_site_list'])} removed from the search list.")
    print(f"Report: {report_path}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sites", type=Path, default=ROOT / "sites.csv")
    parser.add_argument("--personal-sites", type=Path, help="CSV added to --sites; default: sites.personal.csv beside the base list")
    parser.add_argument("--dataset-root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=ROOT / ".s5cfg")
    parser.add_argument("--only", help="Check one site name or location code")
    parser.add_argument("--report", type=Path, help="Default: <dataset-root>/reports/last_update.json")
    args = parser.parse_args(argv)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
    if not LOGGER.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        LOGGER.addHandler(handler)
    report_path = args.report or args.dataset_root / "reports/last_update.json"
    try:
        sites = read_site_lists(args.sites, args.personal_sites)
        validate_config(args.config)
        from phidown import PhiSat2Searcher
        report = update_catalogues(PhiSat2Searcher(config_file=str(args.config)), sites,
                                   args.dataset_root, report_path, only=args.only)
        print_report(report, report_path)
        return 1 if report["failed_sites"] else 0
    except Exception as exc:
        # A failed setup must not erase the baseline used to detect site-list changes.
        try:
            baseline = read_json(report_path).get("sites_configuration", {}) if report_path.is_file() else {}
        except (ValueError, OSError):
            baseline = {}
        write_json(report_path, {"status": "ERROR", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
                                "sites_configuration": baseline, "error": f"{type(exc).__name__}: {exc}"})
        LOGGER.error("Update failed: %s. Report: %s", exc, report_path)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
