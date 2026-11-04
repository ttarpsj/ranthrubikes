import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from import_products import ImportErrorWithContext, load_taxonomy, validate_taxonomy_path  # noqa: E402


class CatalogTaxonomyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.taxonomy = load_taxonomy()

    def test_top_level_order_is_stable(self):
        self.assertEqual(
            [item["id"] for item in self.taxonomy["top_level"]],
            ["new-arrivals", "ran-thru-collection", "clothing", "equipment", "components", "bikes-frames", "brands", "sale"],
        )

    def test_clothing_branches_are_exact(self):
        garments = ["short-sleeve-jerseys", "long-sleeve-jerseys", "bibshorts", "gilets", "baselayers", "jackets", "winter-tights", "skinsuits"]
        self.assertEqual([item["id"] for item in self.taxonomy["clothing"]["men"]], garments)
        self.assertEqual([item["id"] for item in self.taxonomy["clothing"]["women"]], garments)
        self.assertEqual([item["id"] for item in self.taxonomy["clothing"]["lifestyle"]], ["t-shirts", "sweaters", "casual-wear"])
        self.assertEqual([item["id"] for item in self.taxonomy["clothing"]["accessories"]], ["gloves", "socks", "warmers", "overshoes"])

    def test_garment_can_target_multiple_audiences(self):
        result = validate_taxonomy_path({
            "category_id": "clothing",
            "subtype_id": "skinsuits",
            "audiences": ["men", "women"],
            "tags": ["new-arrivals", "ran-thru-collection"],
        }, self.taxonomy, "fixture")
        self.assertEqual(result[3], ["men", "women"])
        self.assertEqual(result[4], ["new-arrivals", "ran-thru-collection"])

    def test_accessories_are_unisex_only(self):
        with self.assertRaises(ImportErrorWithContext):
            validate_taxonomy_path({
                "category_id": "clothing",
                "subtype_id": "socks",
                "audiences": ["men"],
                "tags": [],
            }, self.taxonomy, "fixture")

    def test_unknown_collection_tag_is_rejected(self):
        with self.assertRaises(ImportErrorWithContext):
            validate_taxonomy_path({
                "category_id": "equipment",
                "subtype_id": "bottles",
                "subtype_label": "Bottles",
                "audiences": ["unisex"],
                "tags": ["created-recently"],
            }, self.taxonomy, "fixture")

    def test_public_export_uses_explicit_tags(self):
        products = json.loads((ROOT / "data" / "products.json").read_text(encoding="utf-8"))["products"]
        for product in products:
            self.assertEqual(product["is_new"], "new-arrivals" in product["tags"])
            self.assertEqual(product["is_ran_thru"], "ran-thru-collection" in product["tags"])
            if product["is_sale"]:
                self.assertLess(product["sale_price_cents"], product["price_cents"])


if __name__ == "__main__":
    unittest.main()
