"""Shared metadata helpers for the CalVal JSON catalogues (no imagery dependencies)."""
from __future__ import annotations

import configparser
import csv
import json
import re
from dataclasses import asdict, dataclass, replace
from importlib import resources
from pathlib import Path

from .paths import default_data_dir, ensure_workspace

ROOT = default_data_dir()
CATEGORIES = ("geometry", "image_quality", "radiometry")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def product_name(value: str) -> str:
    name = value.strip()
    if name.lower().endswith(".zip"):
        name = name[:-4]
    if not re.fullmatch(r"PHISAT-2_[A-Za-z0-9_-]+", name):
        raise ValueError(f"Invalid PhiSat-2 product name: {value!r}")
    return name


def load_dataset(category: str, root: Path = ROOT) -> dict:
    if category not in CATEGORIES:
        raise ValueError(f"Unknown category: {category}")
    path = root / category / f"{category}_dataset.json"
    return read_json(path) if path.is_file() else {"schema_version": 1, "entries": []}


def load_catalogues(root: Path = ROOT) -> dict:
    documents = {category: load_dataset(category, root) for category in CATEGORIES}
    for category, document in documents.items():
        keys, destinations = set(), set()
        for entry in document["entries"]:
            if entry["category"] != category or not re.fullmatch(r"[A-Za-z0-9_-]+", entry["location"]):
                raise ValueError(f"Invalid category/location in {category} catalogue")
            if not re.fullmatch(r"Session[1-9]\d*", entry["session"]):
                raise ValueError(f"Invalid session: {entry['session']}")
            key = (entry["location"], product_name(entry["metadata"]["session_id"]))
            destination = (entry["location"], entry["session"])
            if key in keys or destination in destinations:
                raise ValueError(f"Duplicate product or session in {category}: {key}")
            keys.add(key)
            destinations.add(destination)
    return documents


@dataclass(frozen=True)
class Site:
    name: str
    latitude: float
    longitude: float
    country: str
    location: str
    categories: tuple[str, ...]

    def configuration(self) -> dict:
        data = asdict(self)
        data["categories"] = list(self.categories)
        return data


def read_sites(path: Path, *, allow_empty: bool = False) -> list[Site]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"Site", "Latitude", "Longitude", "Country", "Location", "Categories"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Sites CSV requires: {', '.join(sorted(required))}")
        sites, names, locations = [], set(), set()
        for number, row in enumerate(reader, 2):
            name = (row["Site"] or "").strip()
            location = (row["Location"] or "").strip()
            categories = tuple(sorted({c.strip() for c in (row["Categories"] or "").split(";") if c.strip()}))
            latitude, longitude = float(row["Latitude"]), float(row["Longitude"])
            if not name or not re.fullmatch(r"[A-Za-z0-9_-]+", location):
                raise ValueError(f"Invalid site name or location code on row {number}")
            if name.casefold() in names or location.casefold() in locations:
                raise ValueError(f"Duplicate site name or location code on row {number}")
            if not categories or set(categories) - set(CATEGORIES):
                raise ValueError(f"Invalid Categories on row {number}; separate multiple categories with ';'")
            if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                raise ValueError(f"Invalid coordinates on row {number}")
            sites.append(Site(name, latitude, longitude, (row["Country"] or "").strip(), location, categories))
            names.add(name.casefold())
            locations.add(location.casefold())
    if not sites and not allow_empty:
        raise ValueError("Sites CSV is empty")
    return sites


def merge_sites(base: list[Site], additional: list[Site]) -> list[Site]:
    """Merge by site code; later definitions win without writing either file."""
    merged = {site.location.casefold(): site for site in base}
    for site in additional:
        key = site.location.casefold()
        if key in merged:
            site = replace(site, location=merged[key].location)
        merged[key] = site
    names = {}
    for site in merged.values():
        name = site.name.casefold()
        if name in names:
            raise ValueError(f"Site name {site.name!r} is shared by codes {names[name]} and {site.location}; use unique names")
        names[name] = site.location
    return list(merged.values())


def read_site_lists(base_path: Path, personal_path: Path | None = None) -> list[Site]:
    """Add a private CSV to the distributed list; an absent default is optional."""
    sites = read_sites(base_path)
    explicit = personal_path is not None
    personal_path = personal_path if explicit else base_path.parent / "sites.personal.csv"
    if personal_path.resolve() == base_path.resolve():
        raise ValueError("The personal site list must be separate from the distributed site list")
    if explicit or personal_path.exists():
        sites = merge_sites(sites, read_sites(personal_path, allow_empty=True))
    return sites


def load_sites(root: Path = ROOT, base_path: Path | None = None,
               personal_path: Path | None = None) -> list[Site]:
    """Combine release defaults, local sites and private additions in that order."""
    root = ensure_workspace(root)
    local = read_site_lists(base_path or root / "sites.csv", personal_path)
    if base_path is not None:
        return local
    # New release sites also appear in workspaces created by an earlier version.
    resource = resources.files("calvaldataset").joinpath("data", "sites.csv")
    with resources.as_file(resource) as released_path:
        return merge_sites(read_sites(released_path), local)


def validate_config(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Missing {path}; run calval init, then copy its .s5cfg.example to .s5cfg and enter your Insula credentials")
    config = configparser.ConfigParser(interpolation=None)
    config.read(path, encoding="utf-8-sig")
    if "phisat2" not in config:
        raise ValueError("Credential file requires a [phisat2] section")
    for key in ("username", "password"):
        value = config["phisat2"].get(key, "").strip()
        if not value or value.startswith("YOUR_INSULA_"):
            raise ValueError(f"Set '{key}' in the local credential file")


def entry_directory(entry: dict, root: Path = ROOT) -> Path:
    path = (root / entry.get("directory", f"{entry['category']}/{entry['location']}/{entry['session']}")).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Entry directory is outside dataset root")
    return path


def expected_band_paths(entry: dict) -> dict:
    """Declare stable local TIFF destinations independently of crop availability."""
    folder = entry.get("directory", f"{entry['category']}/{entry['location']}/{entry['session']}")
    return {f"b_{i}": f"{folder}/bands/b_{i}.tiff" for i in range(8)}


def discover_bands(entry: dict, root: Path = ROOT) -> dict:
    candidates = {}
    for path in entry_directory(entry, root).rglob("*"):
        if path.suffix.lower() not in {".tif", ".tiff"}:
            continue
        match = re.search(r"(?:_|-)([0-7])$", path.stem)
        if match:
            candidates.setdefault(f"b_{match[1]}", []).append(path)
    result = {}
    expected = expected_band_paths(entry)
    for key, paths in candidates.items():
        canonical = (root / expected[key]).resolve()
        if canonical in [path.resolve() for path in paths]:
            result[key] = expected[key]
        elif len(paths) == 1:
            result[key] = paths[0].relative_to(root.resolve()).as_posix()
        else:
            raise ValueError(f"Ambiguous TIFF filenames for {key}: {paths}")
    return result
