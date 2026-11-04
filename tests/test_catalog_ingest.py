import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from catalog_ingest.pipeline import BRAND_CONFIGS, load_brand, normalise


class CatalogIngestTest(unittest.TestCase):
    def test_every_requested_brand_has_a_safe_config(self):
        self.assertEqual(len(list(BRAND_CONFIGS.glob("*.json"))), 20)
        for path in BRAND_CONFIGS.glob("*.json"):
            config=load_brand(__import__("json").loads(path.read_text())["brand"])
            self.assertTrue(config["requires_agreement"])
            self.assertFalse(config["public_metadata_allowed"])

    def test_valid_feed_record_normalises_to_reviewable_catalog_data(self):
        item, reason=normalise({
            "name":"Training Jersey", "description":"Feed description", "price":"129.00", "sku":"MAAP-001",
            "stock_quantity":"4", "category_id":"clothing", "subtype_id":"short-sleeve-jerseys",
            "audiences":["men"], "images":["https://licensed.example/jersey.jpg"], "image_rights":"licensed",
        },load_brand("MAAP"))
        self.assertIsNone(reason)
        self.assertEqual(item["price"],12900)
        self.assertEqual(item["identifier"],"MAAP-001")

    def test_invalid_price_is_rejected(self):
        item,reason=normalise({"name":"Bad","sku":"BAD-1","category_id":"equipment","price":"unknown"},load_brand("MAAP"))
        self.assertIsNone(item)
        self.assertIn("price",reason)


if __name__ == "__main__": unittest.main()
