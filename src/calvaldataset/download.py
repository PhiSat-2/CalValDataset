#!/usr/bin/env python3
"""Plan or download CalVal products with Phi-Down into category/site/session."""
from __future__ import annotations

import os
import shutil
import zipfile
from pathlib import Path

from .catalogue import (
    CATEGORIES, ROOT, discover_bands, entry_directory, expected_band_paths, load_catalogues,
    product_name, read_json, validate_config, write_json,
)


def extract_archive(archive_path: Path, folder: Path) -> None:
    """Check members before extraction, retaining the original archive."""
    folder = folder.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            if not (folder / member.filename).resolve().is_relative_to(folder):
                raise ValueError(f"Archive member escapes target: {member.filename}")
        archive.extractall(folder)


def organize_bands(entry: dict, root: Path) -> None:
    """Expose extracted TIFFs at the stable paths declared in the catalogue."""
    root = root.resolve()
    discovered = discover_bands(entry, root)
    expected = expected_band_paths(entry)
    missing = set(expected) - set(discovered)
    if missing:
        raise FileNotFoundError(f"Missing TIFF bands after extraction: {', '.join(sorted(missing))}")
    for key, relative_target in expected.items():
        source = root / discovered[key]
        target = root / relative_target
        if source.resolve() == target.resolve():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        # Preserve the original package layout; hard links avoid an extra raster copy.
        try:
            os.link(source, target)
        except OSError:
            shutil.copy2(source, target)
    entry["bands"] = expected


def download_entries(entries: list[dict], root: Path, searcher, *, unzip: bool = False) -> int:
    root = root.resolve()
    cache = root / "downloads"
    cache.mkdir(parents=True, exist_ok=True)
    failures = 0
    for entry in entries:
        try:
            name = product_name(entry["metadata"]["session_id"]) + ".zip"
            archive = cache / name
            if not archive.is_file() or not zipfile.is_zipfile(archive):
                # Resolve through the platform-files API. Catalogue IDs need not be
                # downloadable platform-file IDs, so never pass a CSV UUID blindly.
                product = searcher.resolve_product(name)
                if product_name(str(product["Name"])) + ".zip" != name:
                    raise ValueError(f"Insula returned a different product for {name}")
                downloaded = Path(searcher.download_product(
                    product_id=product["Id"], output_dir=str(cache),
                    file_name=name, overwrite=True, unzip=False,
                ))
                if not zipfile.is_zipfile(downloaded):
                    raise ValueError(f"Invalid downloaded ZIP: {name}")
                if downloaded.resolve() != archive.resolve():
                    shutil.copy2(downloaded, archive)
            folder = entry_directory(entry, root)
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / name
            if not target.is_file() or not zipfile.is_zipfile(target):
                shutil.copy2(archive, target)
            if unzip:
                marker = folder / ".extracted_product"
                if not marker.is_file() or marker.read_text(encoding="utf-8") != name:
                    extract_archive(target, folder)
                organize_bands(entry, root)
                marker.write_text(name, encoding="utf-8")
            print(f"OK {entry['category']}/{entry['location']}/{entry['session']}: {name}")
        except Exception as exc:
            failures += 1
            print(f"ERROR {entry['metadata']['session_id']}: {exc}")
    return failures


def select_entries(documents: dict, *, category: str | None = None,
                   location: str | None = None, session: str | None = None,
                   products: list[str] | None = None, allow_empty: bool = False) -> list[dict]:
    requested = {product_name(name) for name in products or []}
    selected = [entry for cat, doc in documents.items() for entry in doc["entries"]
                if (not category or cat == category)
                and (not location or entry["location"].casefold() == location.casefold())
                and (not session or entry["session"].casefold() == session.casefold())
                and (not requested or product_name(entry["metadata"]["session_id"]) in requested)]
    missing = requested - {product_name(e["metadata"]["session_id"]) for e in selected}
    if missing:
        raise ValueError(f"Products not found with these filters: {', '.join(sorted(missing))}")
    if not selected and not allow_empty:
        raise ValueError("No products match the requested filters")
    return selected
