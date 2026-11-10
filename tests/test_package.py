"""Regression checks for installed resources, writable data and the public CLI."""
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from importlib import resources
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from calvaldataset import CATEGORIES, Site, __version__, ensure_workspace, load_catalogues, load_sites
from calvaldataset.catalogue import expected_band_paths, read_json, read_sites, read_site_lists, write_json
from calvaldataset.cli import main, make_parser
from calvaldataset.download import download_entries, extract_archive
from calvaldataset.paths import credential_path
from calvaldataset.update import search_one_site, update_catalogues

OLD = "PHISAT-2_L1_000001340_20241007034054_20241007034103_E04D392C"
NEW = "PHISAT-2_L1_000001553_20241231034302_20241231034308_8E698850"
SITE = Site("Example", 1, 1, "Example", "EXAMPLE", ("geometry", "radiometry"))


def product(name, footprint="POLYGON((0 0,2 0,2 2,0 2,0 0))"):
    return {"Name": name + ".zip", "Id": name[-8:], "GeoFootprint": footprint}


class Catalogue:
    def __init__(self, names=(OLD,), error=False):
        self.products = [product(name) for name in names]
        self.error = error

    def query_catalogue(self, **kwargs):
        if self.error:
            raise ConnectionError("Simulated Insula failure")
        size, page = kwargs["results_per_page"], kwargs["page"]
        self.json_data = {"features": [], "page": {"totalPages": max(1, (len(self.products) + size - 1) // size)}}
        return pd.DataFrame(self.products[page * size:(page + 1) * size])


class Downloader:
    def __init__(self):
        self.calls = 0

    def resolve_product(self, name):
        return {"Name": name, "Id": "platform-file-id"}

    def download_product(self, **kwargs):
        self.calls += 1
        assert kwargs["product_id"] == "platform-file-id"
        path = Path(kwargs["output_dir"]) / kwargs["file_name"]
        with zipfile.ZipFile(path, "w") as archive:
            for index in range(8):
                archive.writestr(f"original/bands/Bp_4096_12345_12_{index}.tiff", f"band-{index}".encode())
        return str(path)


class WorkspaceTests(unittest.TestCase):
    def test_distribution_name_and_python_import_version(self):
        self.assertEqual(version('phisat2-calvaldataset'), __version__)

    def test_installed_seed_and_idempotent_initialization(self):
        seed = resources.files("calvaldataset").joinpath("data")
        self.assertIn("YOUR_INSULA_PASSWORD", seed.joinpath(".s5cfg.example").read_text())
        self.assertFalse(seed.joinpath(".s5cfg").is_file())
        with tempfile.TemporaryDirectory() as temporary:
            root = ensure_workspace(Path(temporary))
            documents = load_catalogues(root)
            entries = [e for doc in documents.values() for e in doc["entries"]]
            self.assertEqual(len(entries), 103)
            self.assertEqual(len({e["metadata"]["session_id"] for e in entries}), 87)
            self.assertEqual(sum(bool(e.get("bbox")) for e in entries), 16)
            self.assertTrue(all(e["bands"] == expected_band_paths(e) and e["metadata"]["resolution"] == 4.75 for e in entries))
            sites_path = root / "sites.csv"
            original = sites_path.read_bytes()
            sites_path.write_bytes(original + b"\n")
            ensure_workspace(root)
            self.assertEqual(sites_path.read_bytes(), original + b"\n")
            self.assertFalse((root / ".s5cfg").exists())

    def test_package_resources_are_never_a_writable_workspace(self):
        import calvaldataset
        with self.assertRaises(ValueError):
            ensure_workspace(Path(calvaldataset.__file__).parent / "data")

    def test_environment_directory_and_credential_precedence(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict(os.environ, {"CALVAL_DATA_DIR": temporary}):
                self.assertEqual(ensure_workspace(), Path(temporary).resolve())
            with patch.dict(os.environ, {"CALVAL_CONFIG": str(Path(temporary) / "environment.s5cfg")}):
                self.assertEqual(credential_path(Path(temporary)).name, "environment.s5cfg")
                self.assertEqual(credential_path(Path(temporary), Path("explicit.s5cfg")).name, "explicit.s5cfg")


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = ensure_workspace(Path(self.temp.name))
        for category in CATEGORIES:
            write_json(self.root / category / f"{category}_dataset.json", {"schema_version": 1, "entries": []})

    def test_update_no_updates_crops_and_new_acquisitions(self):
        first = update_catalogues(Catalogue(), [SITE], self.root)
        self.assertEqual(first["new_products"], [OLD])
        self.assertEqual(first["added_entries"], 2)
        path = self.root / "geometry/geometry_dataset.json"
        document = read_json(path)
        crop = [{"x_min": 1, "y_min": 2, "x_max": 3, "y_max": 4, "label": "Measured"}]
        document["entries"][0]["bbox"] = crop
        write_json(path, document)
        before = path.read_bytes()
        second = update_catalogues(Catalogue(), [SITE], self.root)
        self.assertEqual(second["status"], "NO_UPDATES")
        self.assertEqual(path.read_bytes(), before)
        third = update_catalogues(Catalogue((OLD, NEW)), [SITE], self.root)
        self.assertEqual(third["new_products"], [NEW])
        entries = read_json(path)["entries"]
        self.assertEqual(entries[0]["bbox"], crop)
        self.assertEqual(entries[0]["session"], "Session1")
        self.assertEqual(entries[1]["bbox"], [])
        self.assertEqual(entries[1]["bands"], expected_band_paths(entries[1]))
        self.assertEqual(entries[1]["metadata"]["resolution"], 4.75)
        self.assertEqual(list((self.root / "geometry").iterdir()), [path])

    def test_configuration_changes_and_search_errors(self):
        update_catalogues(Catalogue(), [SITE], self.root)
        before = load_catalogues(self.root)
        failed = update_catalogues(Catalogue(error=True), [SITE], self.root)
        self.assertEqual(failed["status"], "PARTIAL_ERROR")
        self.assertNotIn("products_found", failed["sites"][0])
        self.assertEqual(load_catalogues(self.root), before)
        extra = Site("Another", 2, 2, "Example", "OTHER", ("image_quality",))
        changed = Site(SITE.name, 1.1, 1.2, SITE.country, SITE.location, SITE.categories)
        report = update_catalogues(Catalogue(()), [changed, extra], self.root)
        self.assertEqual(report["configuration_changes"]["added"], ["OTHER"])
        self.assertEqual(report["configuration_changes"]["changed"], ["EXAMPLE"])
        self.assertEqual(report["sites"][0]["products_found"], 0)
        self.assertEqual(load_catalogues(self.root), before)

    def test_shared_download_cache_and_standard_band_paths(self):
        update_catalogues(Catalogue(), [SITE], self.root)
        entries = [e for d in load_catalogues(self.root).values() for e in d["entries"]]
        downloader = Downloader()
        with redirect_stdout(io.StringIO()):
            self.assertEqual(download_entries(entries, self.root, downloader, unzip=True), 0)
            self.assertEqual(download_entries(entries, self.root, downloader, unzip=True), 0)
        self.assertEqual(downloader.calls, 1)
        for entry in entries:
            for index in range(8):
                self.assertEqual((self.root / entry["bands"][f"b_{index}"]).read_bytes(), f"band-{index}".encode())

    def test_archive_path_traversal(self):
        path = self.root / "bad.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("../escaped.txt", "bad")
        with self.assertRaises(ValueError):
            extract_archive(path, self.root / "target")
        self.assertFalse((self.root / "escaped.txt").exists())


class SearchTests(unittest.TestCase):
    def test_boundary_coverage_and_pagination(self):
        catalogue = Catalogue((OLD, NEW))
        catalogue.products[1]["GeoFootprint"] = "POLYGON((1 1,2 1,2 2,1 2,1 1))"
        found = search_one_site(catalogue, SITE, page_size=1)
        self.assertEqual(len(found), 2)
        catalogue.products[1]["GeoFootprint"] = "POLYGON((1.00001 0,2 0,2 2,1.00001 2,1.00001 0))"
        self.assertEqual(len(search_one_site(catalogue, SITE)), 1)

    def test_repeated_pages_raise_incomplete_search_error(self):
        class Repeated(Catalogue):
            def query_catalogue(self, **kwargs):
                self.json_data = {}
                return pd.DataFrame(self.products)
        with self.assertRaisesRegex(RuntimeError, "Repeated catalogue page"):
            search_one_site(Repeated(), SITE, page_size=1)


class PersonalSiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = ensure_workspace(Path(self.temp.name))
        self.personal = self.root / 'sites.personal.csv'
        self.header = 'Site,Latitude,Longitude,Country,Location,Categories\n'

    def test_additions_and_overrides_preserve_both_files(self):
        self.personal.write_text(self.header + 'Personal,1,1,Example,MY01,radiometry\nMy La Crau,43.5,4.8,France,lcfr,geometry\n', encoding='utf-8')
        before = (self.root / 'sites.csv').read_bytes(), self.personal.read_bytes()
        sites = load_sites(self.root)
        self.assertEqual(len(sites), 22)
        custom = next(s for s in sites if s.location == 'LCFR')
        self.assertEqual(custom.name, 'My La Crau')
        self.assertEqual(custom.categories, ('geometry',))
        ensure_workspace(self.root)
        self.assertEqual(((self.root / 'sites.csv').read_bytes(), self.personal.read_bytes()), before)

    def test_empty_default_and_missing_explicit_files(self):
        self.assertEqual(len(load_sites(self.root)), 21)
        self.personal.write_text(self.header, encoding='utf-8')
        self.assertEqual(len(load_sites(self.root)), 21)
        with self.assertRaises(FileNotFoundError):
            load_sites(self.root, personal_path=self.root / 'missing.csv')

    def test_name_conflict_is_reported(self):
        self.personal.write_text(self.header + 'La Crau,1,1,Example,DIFFERENT,radiometry\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'shared by codes'):
            load_sites(self.root)

    def test_release_additions_reach_older_workspaces(self):
        base = self.root / 'sites.csv'
        lines = base.read_text(encoding='utf-8-sig').splitlines()
        base.write_text('\n'.join([lines[0], *lines[2:]]) + '\n', encoding='utf-8')
        self.personal.write_text(self.header + 'Personal,1,1,Example,MY01,radiometry\n', encoding='utf-8')
        before = base.read_bytes(), self.personal.read_bytes()
        self.assertEqual(len(read_site_lists(base)), 21)
        self.assertEqual(len(load_sites(self.root)), 22)
        self.assertEqual((base.read_bytes(), self.personal.read_bytes()), before)

    def test_cli_update_and_list_personal_site(self):
        self.personal.write_text(self.header + 'Personal,1,1,Example,MY01,radiometry\n', encoding='utf-8')
        before = self.personal.read_bytes()
        with patch('calvaldataset.cli.make_searcher', return_value=Catalogue()), redirect_stdout(io.StringIO()):
            code = main(['update', '--site', 'MY01', '--data-dir', str(self.root)])
        self.assertEqual(code, 0)
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(['list', '--site', 'MY01', '--format', 'json', '--data-dir', str(self.root)])
        self.assertEqual(code, 0)
        entries = json.loads(out.getvalue())['entries']
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['location'], 'MY01')
        self.assertEqual(self.personal.read_bytes(), before)


class CLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def invoke(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main([*args, "--data-dir", str(self.root)])
        return code, out.getvalue(), err.getvalue()

    def test_list_without_credentials_and_zero_result_site(self):
        with patch("calvaldataset.cli.make_searcher", side_effect=AssertionError("Network must not be used")):
            code, out, err = self.invoke("list", "--category", "radiometry", "--site", "LCFR", "--format", "json")
            self.assertEqual(code, 0, err)
            self.assertEqual(len(json.loads(out)["entries"]), 5)
            code, out, err = self.invoke("list", "--site", "JSIT", "--format", "json")
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out)["entries"], [])

    def test_dry_run_site_alias_and_unknown_site(self):
        with patch("calvaldataset.cli.make_searcher", side_effect=AssertionError("Network must not be used")):
            code, out, err = self.invoke("download", "--site", "La Crau", "--dry-run")
            self.assertEqual(code, 0, err)
            self.assertIn("5 unique products", out)
        code, out, err = self.invoke("list", "--site", "NOT_A_SITE")
        self.assertEqual(code, 2)
        self.assertIn("Unknown site", err)

    def test_download_selection_does_not_replace_full_catalogues(self):
        root = ensure_workspace(self.root)
        before = copy.deepcopy(load_catalogues(root))
        path = root / "selection.json"
        write_json(path, {"entries": [before["image_quality"]["entries"][0]]})
        with patch("calvaldataset.cli.make_searcher", return_value=Downloader()):
            code, out, err = self.invoke("download", "--json", str(path), "--unzip")
        self.assertEqual(code, 0, err)
        self.assertEqual(load_catalogues(root), before)
        entry = read_json(path)["entries"][0]
        self.assertTrue(all((root / p).is_file() for p in entry["bands"].values()))

    def test_update_without_credentials_writes_error_report(self):
        code, out, err = self.invoke("update", "--site", "LCFR", "--config", str(self.root / "missing.s5cfg"))
        self.assertEqual(code, 2)
        self.assertEqual(read_json(self.root / "reports/last_update.json")["status"], "ERROR")

    def test_update_site_and_all(self):
        with patch("calvaldataset.cli.make_searcher", return_value=Catalogue(())):
            self.assertEqual(self.invoke("update", "--site", "LCFR")[0], 0)
            report = read_json(self.root / "reports/last_update.json")
            self.assertEqual(len(report["sites"]), 1)
            self.assertEqual(report["sites"][0]["location"], "LCFR")
            self.assertEqual(self.invoke("update", "--all")[0], 0)
            self.assertEqual(len(read_json(self.root / "reports/last_update.json")["sites"]), 21)

    def test_global_options_before_and_after_subcommand(self):
        before = make_parser().parse_args(["--data-dir", str(self.root), "list"])
        after = make_parser().parse_args(["list", "--data-dir", str(self.root)])
        self.assertEqual(before.data_dir, after.data_dir)

    def test_module_entry_point_outside_repository(self):
        environment = dict(os.environ, CALVAL_DATA_DIR=str(self.root))
        run = subprocess.run([sys.executable, "-m", "calvaldataset", "--version"],
                             cwd=self.root, env=environment, text=True, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn(__version__, run.stdout)


if __name__ == "__main__":
    unittest.main()
