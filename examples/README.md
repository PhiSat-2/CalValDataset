# Runnable examples

These scripts demonstrate the real dataset workflows. They replace the former
unit-test folder and reuse the repository's main modules.

Run the commands below from the repository root with the virtual environment's
Python interpreter. Each script also resolves repository paths when executed
from another directory.

| Script | Purpose | Default behaviour |
|---|---|---|
| [01_read_catalogues.py](01_read_catalogues.py) | Read JSON catalogues and display products, dates and crop counts | Local metadata only |
| [02_download_products.py](02_download_products.py) | Download a sample session or the entire dataset | Preview Baotou Session1 in image_quality |
| [03_update_datasets.py](03_update_datasets.py) | Query configured sites and update the catalogues | Preview the configured sites |

## Configure Insula credentials

Before downloading products or running a live update, copy
[.s5cfg.example](../.s5cfg.example) to `.s5cfg` in the repository root, then enter
your **Insula username and password** in the `[phisat2]` section:

```ini
[phisat2]
username = YOUR_INSULA_USERNAME
password = YOUR_INSULA_PASSWORD
```

Replace both placeholders with your own credentials. The local credential file
is excluded from Git. Previewing catalogues and site lists requires no credentials.

## Read products

```powershell
python examples/01_read_catalogues.py --category radiometry --location LYB1
```

## Download products

```powershell
# Preview the sample session.
python examples/02_download_products.py

# Download and extract the sample session.
python examples/02_download_products.py --download --unzip

# Select a different session.
python examples/02_download_products.py --category radiometry --location LCFR --session Session2 --download --unzip

# Download and extract the complete dataset.
python examples/02_download_products.py --all --download --unzip
```

The downloader creates the category/site/session directories and uses a shared
ZIP cache. The main downloader also supports `--json` and repeated `--product`
arguments for custom selections; see the [main README](../README.md).

## Update catalogues

Copy [sites.personal.csv.example](../sites.personal.csv.example) to
`sites.personal.csv` once, then add your coordinates, stable site codes and
categories there. This local file is automatically added to the released list
and is left unchanged by updates. Use `--personal-sites` for a different CSV.

```powershell
# Preview the site list.
python examples/03_update_datasets.py

# Query one site and update its catalogues.
python examples/03_update_datasets.py --only LCFR --run

# Query all sites and update the dataset.
python examples/03_update_datasets.py --run

# Add a separate personal list to the released sites.
python examples/03_update_datasets.py --personal-sites ../private-sites.csv --run
```

Live updates write `reports/last_update.json` and preserve existing products,
session identifiers and crop metadata. These are executable usage examples,
not an automated test suite.
