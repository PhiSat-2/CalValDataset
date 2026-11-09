![CalValDataset PhiSat-2 Toolkit Dashboard](assets/phisat2-toolkit-dashboard.png)

# CalValDataset

This repository provides PhiSat-2 Level-1 **products' references and associated metadata**, organized into **geometry**, **image_quality** and **radiometry**. A reference identifies a product on Insula by its name, catalogue ID and acquisition dates. Associated metadata includes site coordinates, expected local band paths and any curated pixel regions of interest. The repository does not contain the satellite imagery itself.

**Phi-Down** is the Python client used to authenticate to Insula, search its catalogue for acquisitions covering the configured site coordinates, and resolve and download product archives. Updating the local catalogues means adding newly discovered references and refreshing metadata in JSON files. It does not download imagery, process pixels or publish changes back to Insula; imagery is downloaded separately on request.

This branch prepares **calvaldataset 0.1.1** as an installable Python package. It has not yet been published to PyPI. The GitHub repository remains the source of code, catalogue snapshots and examples.

## Repository contents

The package uses a `src/` layout. Bundled JSONs are release snapshots; installed commands operate on writable workspace copies.

| File or directory | Detailed role |
|---|---|
| [pyproject.toml](pyproject.toml) | Package/version metadata, Python/dependency requirements, bundled data, license and the `calval` console entry point. |
| [src/calvaldataset/cli.py](src/calvaldataset/cli.py) | Implements `init`, `list`, `download` and `update`; parses filters, data/credential/personal-site options and dispatches operations. Listing and download previews are offline. |
| [src/calvaldataset/catalogue.py](src/calvaldataset/catalogue.py) | Offline JSON/CSV validation and I/O; merges release/workspace/personal sites, validates credentials, defines band destinations and discovers extracted TIFFs. |
| [src/calvaldataset/paths.py](src/calvaldataset/paths.py) | Resolves OS/user-selected data directories, initializes missing snapshots/templates without overwriting user files and finds credentials. Prevents use of the installed package as a writable workspace. |
| [src/calvaldataset/update.py](src/calvaldataset/update.py) | Queries all candidate pages through Phi-Down, verifies exact coverage and updates category metadata while preserving sessions/crops. Produces change/error reports without downloading imagery. |
| [src/calvaldataset/download.py](src/calvaldataset/download.py) | Filters references, resolves exact archive names through Phi-Down, caches downloads, checks extraction paths and organizes all eight TIFFs at standard destinations while preserving original files. |
| [src/calvaldataset/__init__.py](src/calvaldataset/__init__.py) | Exposes the package version and Python API for catalogues, workspace initialization and merged site lists. |
| [src/calvaldataset/__main__.py](src/calvaldataset/__main__.py) | Connects `python -m calvaldataset` to the same CLI as `calval`. |
| [src/calvaldataset/data/](src/calvaldataset/data/) | Immutable release resources: geometry/image_quality/radiometry product-reference JSONs, sites.csv and credential/personal-site templates. Contains no imagery or real credentials. |
| [examples/01_read_catalogues.py](examples/01_read_catalogues.py) | Runs the installed package's offline list command with user-supplied filters. |
| [examples/02_download_products.py](examples/02_download_products.py) | Previews or downloads a sample session/the full dataset; forwards credential and personal-site options. |
| [examples/03_update_datasets.py](examples/03_update_datasets.py) | Previews the merged site list; `--run` updates all sites or a selected released/personal site. |
| [tests/test_package.py](tests/test_package.py) | Regression tests for packaged data, workspace isolation, site merging, filters, credential errors, crop/session preservation, pagination and simulated downloads. |
| [.github/workflows/package.yml](.github/workflows/package.yml) | Builds/checks distributions and runs tests on Windows/Linux and Python 3.11/3.12. Does not publish to PyPI. |
| [MANIFEST.in](MANIFEST.in) | Includes examples, tests and supporting files in the source distribution. |
| [requirements.txt](requirements.txt) | Convenience installer for the local package; dependency definitions live in pyproject.toml. |
| [.s5cfg.example](.s5cfg.example) | Credential template for source users; real credentials are never bundled. |
| [LICENSE](LICENSE) | Apache-2.0 license for repository code. |

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
  sites.csv                   Local base list
  sites.personal.csv.example  Personal-site template
  sites.personal.csv          Optional user-maintained additions
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

## Released and personal reference sites

Keep personal sites in a separate file so they remain independent of release snapshots. Initialize a workspace, copy the header-only template once, and add your rows:

```powershell
calval init --data-dir ./calval-data
Copy-Item ./calval-data/sites.personal.csv.example ./calval-data/sites.personal.csv
```

```csv
Site,Latitude,Longitude,Country,Location,Categories
My reference site,45.123,9.456,Italy,MY01,radiometry
Another personal site,44.123,10.456,Italy,MY02,geometry;image_quality
```

Use the actual coordinates of your sites; these rows only illustrate the format. `sites.personal.csv` is detected automatically beside the base list. An explicit `--personal-sites` file is added without replacing the released list:

```powershell
calval update --all --data-dir ./calval-data
calval update --site MY01 --data-dir ./calval-data
calval update --all --personal-sites ../private-sites.csv
calval list --site MY01 --personal-sites ../private-sites.csv
```

The effective list merges **current bundled release sites, workspace sites, then personal sites**. Codes identify matching sites; later layers win, preserving your personal name/coordinate/category choices and the code's canonical spelling. Sites added by a newer package release also appear in older workspaces. Existing local rows and personal CSV files are never overwritten. Names shared by different codes are rejected explicitly. A header-only personal CSV is valid; an explicitly requested missing file is an error.

Personal sites configure searches. Run `update` to discover their products before expecting `list` or `download` to find new entries. Updating writes category JSONs and reports, not the input CSVs or installed resources. Keep codes stable; use `;` between categories and EPSG:4326 point coordinates (west/south negative). Personal files matching `*.personal.csv` are Git-ignored; workspaces normally live outside the source repo.

The existing `--sites` option selects an alternative **base** list rather than extending the release list. Use `--personal-sites` for additive customization. With an alternative base, the default personal CSV is looked up beside that file.

## Update catalogues from Insula

```powershell
calval update --site LCFR
calval update --all
```

The updater searches all candidate pages and keeps products whose footprints cover the exact reference point, including its boundary and with no buffer in the final check. New products are added to the configured category JSON files. Crop definitions, band destinations and existing session identifiers are preserved. New sessions are appended even if their acquisition dates are earlier.

Every product has a numeric `metadata.resolution` of **4.75 metres**. An unanalysed product has `"bbox": []`; crop availability is independent of its eight band paths and does not affect downloads. The original 16 crops remain intact. This package stores crop definitions and does not perform image-quality analysis or alter raster pixel values.

Each update prints a short summary and writes `reports/last_update.json`, with status `UPDATED`, `NO_UPDATES`, `PARTIAL_ERROR` or `ERROR`. The report records new products, metadata and site-list changes, search errors and previously catalogued products no longer returned by Insula. Use `--report path.json` to choose a different report.

An unsuccessful search is distinguished from a verified zero-result search. Existing products are retained, including after a site or category is removed from the search list. Updates run when requested by the command; scheduling periodic execution is a separate operation.

## Included catalogue snapshot

| Category | Site/product entries | Entries with existing crops |
|---|---:|---:|
| geometry | 19 | 5 |
| image_quality | 16 | 2 |
| radiometry | 65 | 9 |
| Total | 100 | 16 |

**Site/product entries** counts catalogue records: each is a category/site/product association. A product assigned to two categories contributes one entry in each, so the 100 entries represent **84 unique products**, not 100 separate acquisitions.

**Entries with existing crops** counts the subset of those records with at least one saved pixel ROI in `bbox` (`x_min`, `y_min`, `x_max`, `y_max` and a label). These are analysis regions inside the original image, not geographic search footprints or pre-cropped images stored in the repo. `bbox: []` means no ROI has been defined yet; the product and all eight bands remain available. The 16 crop-bearing entries are already included in the 100 total entries, not added to them. The same acquisition may have crop entries in more than one category.


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
