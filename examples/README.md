# Runnable package examples

Install the package first with `python -m pip install .` from the repository root.
These scripts use the installed `calvaldataset` package and its writable workspace.
They also work when invoked from outside the repository.

```powershell
# Read metadata without credentials or network access.
python examples/01_read_catalogues.py --category radiometry --site LCFR

# Preview the default sample session.
python examples/02_download_products.py

# Download and extract the sample or the complete dataset.
python examples/02_download_products.py --download --unzip
python examples/02_download_products.py --all --download --unzip

# Preview the configured sites or run live updates.
python examples/03_update_datasets.py
python examples/03_update_datasets.py --only LCFR --run
python examples/03_update_datasets.py --run
```

Set `CALVAL_DATA_DIR` or pass `--data-dir` to choose a workspace. Run `calval init`
to display its paths. Before downloads or live updates, copy its `.s5cfg.example`
to `.s5cfg` and enter your **Insula username and password** in `[phisat2]`.
Use `--config` or `CALVAL_CONFIG` for credentials stored elsewhere.

To keep custom sites independent of releases, copy the workspace's
`sites.personal.csv.example` to `sites.personal.csv` and add your rows there.
It is detected automatically. Alternatively, pass `--personal-sites path.csv`
to the download/update examples (or the corresponding `calval` commands).
Release, workspace and personal sites are merged; personal definitions win for
matching codes, and updates never rewrite the personal CSV.

Previewing needs no credentials. These examples complement the package regression
tests in [tests](../tests); they are practical usage examples rather than tests.
See the [main README](../README.md) for the full command-line interface.
