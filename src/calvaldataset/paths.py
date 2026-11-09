"""Keep immutable package resources separate from writable user data."""
from __future__ import annotations

import os
from importlib import resources
from pathlib import Path

from platformdirs import user_data_path


def default_data_dir() -> Path:
    """Choose an explicit environment override or the OS user-data directory."""
    override = os.environ.get("CALVAL_DATA_DIR")
    return Path(override).expanduser().resolve() if override else user_data_path("calvaldataset", appauthor=False)


def ensure_workspace(root: Path | None = None) -> Path:
    """Copy missing seed files once; never overwrite custom sites or catalogues."""
    root = (Path(root) if root is not None else default_data_dir()).expanduser().resolve()
    if root.is_relative_to(Path(__file__).resolve().parent):
        raise ValueError("Choose a data directory outside the installed calvaldataset package")
    seed = resources.files("calvaldataset").joinpath("data")
    paths = [f"{c}/{c}_dataset.json" for c in ("geometry", "image_quality", "radiometry")]
    paths += ["sites.csv", "sites.personal.csv.example", ".s5cfg.example"]
    for relative in paths:
        destination = root / relative
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation preserves a file created by another process.
            try:
                with destination.open("xb") as stream:
                    stream.write(seed.joinpath(*relative.split("/")).read_bytes())
            except FileExistsError:
                pass
    return root


def credential_path(root: Path, explicit: Path | None = None) -> Path:
    """Resolve an explicit file, environment setting, workspace or local config."""
    if explicit is not None:
        return explicit.expanduser().resolve()
    override = os.environ.get("CALVAL_CONFIG")
    if override:
        return Path(override).expanduser().resolve()
    for candidate in (root / ".s5cfg", Path.cwd() / ".s5cfg"):
        if candidate.is_file():
            return candidate.resolve()
    return root / ".s5cfg"
