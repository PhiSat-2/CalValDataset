"""PhiSat-2 calibration and validation catalogue tools."""

from .catalogue import CATEGORIES, Site, load_catalogues, load_dataset, load_sites, read_sites
from .paths import default_data_dir, ensure_workspace

__version__ = "0.1.1"
__all__ = ["CATEGORIES", "Site", "load_catalogues", "load_dataset", "load_sites", "read_sites",
           "default_data_dir", "ensure_workspace", "__version__"]
