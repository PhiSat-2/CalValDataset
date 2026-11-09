# CalValDataset

Browse, download and update PhiSat-2 Level-1 calibration and validation datasets from Insula through **Phi-Down**. Products are grouped into **geometry**, **image_quality** and **radiometry**.

This branch prepares **calvaldataset 0.1.0** as an installable Python package. It has not yet been published to PyPI. The GitHub repository remains the source of code, catalogue snapshots and examples.

## Install

Python 3.11 or later is required. Install this branch directly:

```powershell
python -m pip install "git+https://github.com/lorenzopapa5/CalValDataset.git@feature/pypi-package"
```

For local development, clone the branch and install from its root:

```powershell
git clone --branch feature/pypi-package https://github.com/lorenzopapa5/CalValDataset.git
cd CalValDataset
python -m pip install .
calval --version
```

After the first PyPI release, installation will also be available as:

```powershell
python -m pip install calvaldataset
```

Both `calval ...` and `python -m calvaldataset ...` expose the same interface.

## Quick start

```powershell
# Browse local catalogues without authentication or network access.
calval list --category radiometry
calval list --site LCFR

# Download and extract the products for La Crau.
calval download --site LCFR --unzip

# Search Insula for new acquisitions at La Crau.
calval update --site LCFR

# Check all configured sites.
calval update --all
```

Downloads and live updates require the Insula credentials described below. Listing products does not require credentials.

## Writable data and credentials

The package includes an initial snapshot of the three JSON catalogues, the site list and a credential template. These installed resources are immutable defaults. On first use, missing files are copied into a writable user-data directory; existing catalogues, crops, credentials and custom sites are never overwritten by initialization or a package upgrade.

The default location follows the operating system's user-data convention, such as `%LOCALAPPDATA%/calvaldataset` on Windows and `~/.local/share/calvaldataset` on Linux. Run `calval init` to display the actual paths.

Choose a specific directory with `--data-dir` (before or after the subcommand), or set the `CALVAL_DATA_DIR` environment variable:

```powershell
calval init --data-dir ./calval-data
```

**Enter your own Insula username and password in a local `.s5cfg` file before downloading or updating.** Copy the template produced by initialization and edit the copy:

```powershell
Copy-Item ./calval-data/.s5cfg.example ./calval-data/.s5cfg
```

```ini
[phisat2]
username = YOUR_INSULA_USERNAME
password = YOUR_INSULA_PASSWORD
```

Replace the placeholders with your credentials. Keep the file private. It is excluded from Git and is never included in the package.

Credential lookup uses, in order: `--config`, `CALVAL_CONFIG`, `.s5cfg` in the selected data directory, then `.s5cfg` in the current working directory. For example:

```powershell
calval download --site LCFR --unzip --data-dir ./calval-data
calval update --site LCFR --data-dir ./calval-data
calval update --all --config ./private/.s5cfg
```

A workspace has this structure:

```text
calval-data/
  geometry/geometry_dataset.json
  image_quality/image_quality_dataset.json
  radiometry/radiometry_dataset.json
  sites.csv
  .s5cfg.example
  .s5cfg                      User-created credentials
  downloads/                  Shared ZIP cache, created at download time
  reports/last_update.json    Created by catalogue updates
```

Session directories appear only when imagery is downloaded. Multiple workspaces can coexist using different `--data-dir` values.

## Product selection and downloads

```powershell
calval list --category image_quality --site BAOT --session Session1
calval list --site LCFR --format json
calval download --site LCFR --dry-run
calval download --category image_quality --site BAOT --session Session1 --unzip
calval download --all --unzip
```

Use an exact name with `--product`, repeating the option for several products. Names may include or omit `.zip`. `--site` accepts a site code or full name; `--location` remains an alias.

For an edited selection, create a JSON file containing the desired `entries` and pass `calval download --json selection.json --unzip`. Only that selection file is updated if its band mappings need updating; it never replaces the complete catalogues.

Products are organized under `category/site_code/SessionN/` in the workspace. Each entry declares eight relative paths, `bands/b_0.tiff` through `bands/b_7.tiff`. With `--unzip`, the downloader discovers the original TIFFs and exposes them at those standard paths, preserving the original archive and extracted package. Hard links avoid duplicate raster storage where supported; a copy is used otherwise. Missing or ambiguous bands generate an error.

A shared ZIP cache prevents repeated network downloads for products assigned to multiple categories. The downloader resolves names through the platform-files API rather than assuming catalogue UUIDs are downloadable file IDs.

## Add sites and update catalogues

Edit `sites.csv` in the workspace printed by `calval init`. Append rows below its existing header:

```csv
Site,Latitude,Longitude,Country,Location,Categories
New site,45.123,9.456,Italy,NEW1,geometry
Another site,44.123,10.456,Italy,NEW2,image_quality;radiometry
```

Site names and location codes must be unique. Keep location codes stable when changing coordinates. Categories are `geometry`, `image_quality` and `radiometry`, separated by `;` when a site belongs to several categories. Coordinates are reference points in EPSG:4326; west and south are negative.

```powershell
calval update --site NEW1
calval update --all
calval update --all --sites ./alternative-sites.csv
```

The updater searches all candidate pages and keeps products whose footprints cover the exact reference point, including its boundary and with no buffer in the final check. New products are added to the configured category JSON files. Crop definitions, band destinations and existing session identifiers are preserved. New sessions are appended even if their acquisition dates are earlier.

Every product has a numeric `metadata.resolution` of **4.75 metres**. An unanalysed product has `"bbox": []`; crop availability is independent of its eight band paths and does not affect downloads. The original 16 crops remain intact. This package stores crop definitions and does not perform image-quality analysis or alter raster pixel values.

Each update prints a short summary and writes `reports/last_update.json`, with status `UPDATED`, `NO_UPDATES`, `PARTIAL_ERROR` or `ERROR`. The report records new products, metadata and site-list changes, search errors and previously catalogued products no longer returned by Insula. Use `--report path.json` to choose a different report.

An unsuccessful search is distinguished from a verified zero-result search. Existing products are retained, including after a site or category is removed from the search list. Updates run when requested by the command; scheduling periodic execution is a separate operation.

## Included catalogue snapshot

The package ships **84 unique products** in 100 category entries, based on the Insula check of **9 November 2026**. Baotou products belong to two categories. Local updates can add further products independently of package releases.

| Site | Code | Categories | Unique L1 products |
|---|---|---|---:|
| Railroad Valley Playa | RVUS | radiometry | 3 |
| La Crau | LCFR | radiometry | 5 |
| Gobabeb | GHNA | radiometry | 11 |
| Baotou | BAOT | image_quality, radiometry | 16 |
| Jarvselja | JAES | geometry | 2 |
| Jolanda di Savoia | JSIT | radiometry | 0 |
| Lonzee | LOBE | radiometry | 0 |
| Wytham Woods | WWUK | geometry | 1 |
| Princess Elisabeth | PEAN | radiometry | 5 |
| Libya-4 | LYB4 | radiometry | 5 |
| Libya-1 | LYB1 | radiometry | 6 |
| Algeria-3 | ALG3 | radiometry | 5 |
| Shadnagar | SHAD | radiometry | 9 |
| Piedmont | PIED | geometry | 1 |
| Grosseto | GROS | geometry | 1 |
| Pueblo Range | PRING | geometry | 6 |
| Sioux Falls Range | SFRG | geometry | 8 |

## Python API and examples

```python
from calvaldataset import ensure_workspace, load_catalogues

root = ensure_workspace()  # Or ensure_workspace(Path("./calval-data"))
catalogues = load_catalogues(root)
entries = catalogues["radiometry"]["entries"]
```

The [examples](examples/README.md) provide runnable scripts for reading metadata, selective/full downloads and updates. They use the installed package rather than modifying the import search path.

## Build and verify

```powershell
python -m pip install ".[dev]"
python -m build
python -m twine check dist/*
python -m unittest discover -s tests -v
```

The wheel and source archive are written to `dist/`. The regression suite covers packaged seed data, writable workspace initialization, CLI selection, credential errors, update idempotence, crop preservation, pagination, download caching and band organization with simulated archives. It does not download satellite imagery. GitHub Actions repeats package checks on Windows and Linux with Python 3.11 and 3.12.

PyPI publication and a merge into `main` are separate release steps. No upload is performed by the build or the CI workflow.
