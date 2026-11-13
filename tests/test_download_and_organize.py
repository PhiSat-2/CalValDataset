import tempfile
import unittest
import zipfile
from pathlib import Path

from download_and_organize import download_entries


PRODUCT = "PHISAT-2_L1_000001340_20241007034054_20241007034103_E04D392C"


class FakeSearcher:
    def resolve_product(self, name):
        return {"Name": f"8/{name}", "Id": "fake-product-id"}

    def download_product(self, *, output_dir, file_name, **kwargs):
        archive = Path(output_dir) / file_name
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("placeholder.txt", "test")
        return str(archive)


class DownloadProductNameTests(unittest.TestCase):
    def test_download_accepts_insula_path_prefixed_product_name(self):
        entry = {
            "category": "image_quality",
            "location": "BAOT",
            "session": "Session1",
            "metadata": {"session_id": PRODUCT},
        }

        with tempfile.TemporaryDirectory() as temporary:
            failures = download_entries([entry], Path(temporary), FakeSearcher())

            self.assertEqual(failures, 0)
            self.assertTrue(
                (Path(temporary) / "downloads" / f"{PRODUCT}.zip").is_file()
            )


if __name__ == "__main__":
    unittest.main()
