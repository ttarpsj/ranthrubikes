#!/usr/bin/env python3
"""Import folder-managed products into the existing SQLite catalog."""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "master"
DB = ROOT / "database" / "products.db"
PUBLIC_IMAGES = ROOT / "public" / "images" / "products"
TAXONOMY = ROOT / "config" / "taxonomy.json"

PRODUCT_COLUMNS = {
    "brand": "TEXT",
    "product_type": "TEXT",
    "is_new": "INTEGER NOT NULL DEFAULT 0 CHECK(is_new IN (0,1))",
    "is_sale": "INTEGER NOT NULL DEFAULT 0 CHECK(is_sale IN (0,1))",
    "sale_price_cents": "INTEGER CHECK(sale_price_cents >= 0)",
    "is_ran_thru": "INTEGER NOT NULL DEFAULT 0 CHECK(is_ran_thru IN (0,1))",
    "featured_rank": "INTEGER",
    "category_id": "TEXT",
    "subtype_id": "TEXT",
}


class ImportErrorWithContext(ValueError):
    pass


@dataclass
class ProductSource:
    directory: Path
    data: dict[str, Any]
    images: list[dict[str, Any]]
    variants: list[dict[str, Any]]


def boolean(value: Any, field: str, context: str) -> bool:
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    raise ImportErrorWithContext(f"{context}: {field} must be true or false")


def integer(value: Any, field: str, context: str, *, minimum: int = 0, nullable: bool = False) -> int | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        suffix = " or null" if nullable else ""
        raise ImportErrorWithContext(f"{context}: {field} must be an integer >= {minimum}{suffix}")
    return value


def text(value: Any, field: str, context: str, *, required: bool = False) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ImportErrorWithContext(f"{context}: {field} must be a non-empty string")
    return value.strip()


def safe_file(directory: Path, filename: str, context: str) -> Path:
    candidate = (directory / filename).resolve()
    try:
        candidate.relative_to(directory.resolve())
    except ValueError as error:
        raise ImportErrorWithContext(f"{context}: image file must stay inside the product folder") from error
    if not candidate.is_file():
        raise ImportErrorWithContext(f"{context}: missing image file: {filename}")
    return candidate


def load_taxonomy() -> dict[str, Any]:
    try:
        taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ImportErrorWithContext(f"invalid taxonomy configuration: {error}") from error
    top_ids = [item.get("id") for item in taxonomy.get("top_level", [])]
    if len(top_ids) != len(set(top_ids)):
        raise ImportErrorWithContext("taxonomy contains duplicate top-level IDs")
    for branch, items in taxonomy.get("clothing", {}).items():
        ids = [item.get("id") for item in items]
        if len(ids) != len(set(ids)):
            raise ImportErrorWithContext(f"taxonomy clothing.{branch} contains duplicate subtype IDs")
    return taxonomy


def validate_taxonomy_path(data: dict[str, Any], taxonomy: dict[str, Any], context: str) -> tuple[str, str | None, str | None, list[str], list[str]]:
    category_id = text(data.get("category_id"), "category_id", context, required=True)
    category_items = {item["id"]: item for item in taxonomy["top_level"] if item.get("kind") == "category"}
    if category_id not in category_items:
        raise ImportErrorWithContext(f"{context}: unknown category_id '{category_id}'")
    raw_audiences = data.get("audiences", [])
    if not isinstance(raw_audiences, list):
        raise ImportErrorWithContext(f"{context}: audiences must be an array")
    allowed_audiences = {item["id"] for item in taxonomy["audiences"]}
    audiences = [text(value, "audiences[]", context, required=True) for value in raw_audiences]
    if len(audiences) != len(set(audiences)) or any(value not in allowed_audiences for value in audiences):
        raise ImportErrorWithContext(f"{context}: audiences must contain unique canonical IDs")
    raw_tags = data.get("tags", [])
    if not isinstance(raw_tags, list):
        raise ImportErrorWithContext(f"{context}: tags must be an array")
    allowed_tags = {item["id"] for item in taxonomy["tags"]}
    tags = [text(value, "tags[]", context, required=True) for value in raw_tags]
    if len(tags) != len(set(tags)) or any(value not in allowed_tags for value in tags):
        raise ImportErrorWithContext(f"{context}: tags must contain unique canonical IDs")
    subtype_id = text(data.get("subtype_id"), "subtype_id", context, required=category_id == "clothing")
    subtype_label = text(data.get("subtype_label"), "subtype_label", context)
    if category_id == "clothing":
        clothing = taxonomy["clothing"]
        garment_ids = {item["id"] for item in clothing["men"]}
        lifestyle_ids = {item["id"] for item in clothing["lifestyle"]}
        accessory_ids = {item["id"] for item in clothing["accessories"]}
        labels = {item["id"]: item["label"] for items in clothing.values() for item in items}
        if subtype_id in garment_ids:
            if not audiences or any(value not in {"men", "women"} for value in audiences):
                raise ImportErrorWithContext(f"{context}: garment subtypes require men and/or women audiences")
        elif subtype_id in lifestyle_ids or subtype_id in accessory_ids:
            if audiences != ["unisex"]:
                raise ImportErrorWithContext(f"{context}: Lifestyle and Accessories subtypes require audiences: ['unisex']")
        else:
            raise ImportErrorWithContext(f"{context}: invalid Clothing subtype_id '{subtype_id}'")
        subtype_label = labels[subtype_id]
    elif subtype_id and not subtype_label:
        raise ImportErrorWithContext(f"{context}: subtype_label is required for non-Clothing subtypes")
    return category_id, category_items[category_id]["label"], subtype_id, audiences, tags


def validate_product(directory: Path, taxonomy: dict[str, Any]) -> ProductSource:
    manifest = directory / "product.json"
    context = str(manifest.relative_to(ROOT))
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ImportErrorWithContext(f"{context}: invalid JSON ({error.msg})") from error
    if not isinstance(data, dict):
        raise ImportErrorWithContext(f"{context}: root value must be an object")

    slug = text(data.get("slug"), "slug", context, required=True)
    if slug != directory.name:
        raise ImportErrorWithContext(f"{context}: slug must match folder name '{directory.name}'")
    if not all(character.islower() or character.isdigit() or character == "-" for character in slug):
        raise ImportErrorWithContext(f"{context}: slug may contain only lowercase letters, digits, and hyphens")

    category_id, category_label, subtype_id, audiences, tags = validate_taxonomy_path(data, taxonomy, context)
    subtype_label = text(data.get("subtype_label"), "subtype_label", context)
    if category_id == "clothing":
        subtype_label = next(item["label"] for items in taxonomy["clothing"].values() for item in items if item["id"] == subtype_id)
    normalized = {
        "name": text(data.get("name"), "name", context, required=True),
        "slug": slug,
        "brand": text(data.get("brand"), "brand", context),
        "category": category_label,
        "category_id": category_id,
        "product_type": subtype_label,
        "subtype_id": subtype_id,
        "audiences": audiences,
        "tags": tags,
        "description": text(data.get("description"), "description", context, required=True),
        "price_cents": integer(data.get("price_cents"), "price_cents", context),
        "compare_at_price_cents": integer(data.get("compare_at_price_cents"), "compare_at_price_cents", context, nullable=True),
        "is_new": "new-arrivals" in tags,
        "is_ran_thru": "ran-thru-collection" in tags,
        "active": boolean(data.get("active", True), "active", context),
        "featured_rank": integer(data.get("featured_rank"), "featured_rank", context, minimum=0, nullable=True),
        "stripe_checkout_url": text(data.get("stripe_checkout_url"), "stripe_checkout_url", context),
    }
    compare_at = normalized["compare_at_price_cents"]
    if compare_at is not None and compare_at <= normalized["price_cents"]:
        raise ImportErrorWithContext(f"{context}: compare_at_price_cents must exceed price_cents")

    raw_images = data.get("images", [])
    if not isinstance(raw_images, list):
        raise ImportErrorWithContext(f"{context}: images must be an array")
    images = []
    primary_count = 0
    seen_files: set[str] = set()
    for index, image in enumerate(raw_images):
        image_context = f"{context}: images[{index}]"
        if not isinstance(image, dict):
            raise ImportErrorWithContext(f"{image_context} must be an object")
        filename = text(image.get("file"), "file", image_context, required=True)
        if filename in seen_files:
            raise ImportErrorWithContext(f"{image_context}: duplicate image filename '{filename}'")
        seen_files.add(filename)
        source = safe_file(directory, filename, image_context)
        primary = boolean(image.get("primary", index == 0), "primary", image_context)
        primary_count += int(primary)
        images.append({"file": filename, "source": source, "alt_text": text(image.get("alt_text"), "alt_text", image_context) or normalized["name"], "display_order": integer(image.get("display_order", index), "display_order", image_context), "primary": primary})
    if images and primary_count != 1:
        raise ImportErrorWithContext(f"{context}: images must designate exactly one primary image")

    raw_variants = data.get("variants", [])
    if not isinstance(raw_variants, list):
        raise ImportErrorWithContext(f"{context}: variants must be an array")
    variants = []
    seen_skus: set[str] = set()
    for index, variant in enumerate(raw_variants):
        variant_context = f"{context}: variants[{index}]"
        if not isinstance(variant, dict):
            raise ImportErrorWithContext(f"{variant_context} must be an object")
        sku = text(variant.get("sku"), "sku", variant_context, required=True)
        if sku in seen_skus:
            raise ImportErrorWithContext(f"{variant_context}: duplicate SKU '{sku}'")
        seen_skus.add(sku)
        variants.append({"sku": sku, "size": text(variant.get("size"), "size", variant_context), "color": text(variant.get("color"), "color", variant_context), "stock_quantity": integer(variant.get("stock_quantity", 0), "stock_quantity", variant_context), "price_cents": integer(variant.get("price_cents"), "price_cents", variant_context, nullable=True), "active": boolean(variant.get("active", True), "active", variant_context)})
    return ProductSource(directory, normalized, images, variants)


def scan_master() -> list[ProductSource]:
    if not MASTER.exists():
        return []
    taxonomy = load_taxonomy()
    products = []
    slugs: set[str] = set()
    skus: set[str] = set()
    for directory in sorted(path for path in MASTER.iterdir() if path.is_dir() and not path.name.startswith("_")):
        if not (directory / "product.json").is_file():
            raise ImportErrorWithContext(f"{directory.relative_to(ROOT)}: missing product.json")
        product = validate_product(directory, taxonomy)
        if product.data["slug"] in slugs:
            raise ImportErrorWithContext(f"duplicate product slug: {product.data['slug']}")
        slugs.add(product.data["slug"])
        for variant in product.variants:
            if variant["sku"] in skus:
                raise ImportErrorWithContext(f"duplicate SKU across master folders: {variant['sku']}")
            skus.add(variant["sku"])
        products.append(product)
    return products


def migrate_schema(connection: sqlite3.Connection) -> None:
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    missing = {"products", "product_images", "product_variants"} - tables
    if missing:
        raise ImportErrorWithContext(f"database is missing required tables: {', '.join(sorted(missing))}")
    columns = {row[1] for row in connection.execute("PRAGMA table_info(products)")}
    for name, definition in PRODUCT_COLUMNS.items():
        if name not in columns:
            connection.execute(f"ALTER TABLE products ADD COLUMN {name} {definition}")
    connection.execute("CREATE TABLE IF NOT EXISTS catalog_import_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    connection.execute("CREATE TABLE IF NOT EXISTS product_audiences (product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE, audience TEXT NOT NULL, PRIMARY KEY(product_id,audience))")
    connection.execute("CREATE TABLE IF NOT EXISTS product_tags (product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE, tag TEXT NOT NULL, PRIMARY KEY(product_id,tag))")
    connection.execute("CREATE TABLE IF NOT EXISTS catalog_taxonomy_review (product_id INTEGER PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE, reason TEXT NOT NULL)")
    connection.execute("INSERT OR IGNORE INTO catalog_import_migrations(version) VALUES ('001-master-folder-import')")
    applied = connection.execute("SELECT 1 FROM catalog_import_migrations WHERE version='002-canonical-taxonomy'").fetchone()
    if not applied:
        rows = connection.execute("SELECT id,slug,category,product_type,is_new,is_ran_thru FROM products").fetchall()
        for product_id, slug, category, product_type, is_new, is_ran_thru in rows:
            key = (product_type or "").strip().lower()
            mapping = {
                "socks": ("clothing", "socks", "unisex"),
                "t-shirt": ("clothing", "t-shirts", "unisex"),
                "t-shirts": ("clothing", "t-shirts", "unisex"),
                "bottle": ("equipment", "bottle", "unisex"),
            }.get(key)
            if mapping:
                category_id, subtype_id, audience = mapping
                connection.execute("UPDATE products SET category_id=?,subtype_id=? WHERE id=? AND category_id IS NULL", (category_id, subtype_id, product_id))
                connection.execute("INSERT OR IGNORE INTO product_audiences(product_id,audience) VALUES(?,?)", (product_id, audience))
            elif connection.execute("SELECT category_id FROM products WHERE id=?", (product_id,)).fetchone()[0] is None:
                connection.execute("INSERT OR REPLACE INTO catalog_taxonomy_review(product_id,reason) VALUES(?,?)", (product_id, f"Cannot safely map category='{category}' product_type='{product_type}'"))
            if is_new:
                connection.execute("INSERT OR IGNORE INTO product_tags(product_id,tag) VALUES(?, 'new-arrivals')", (product_id,))
            if is_ran_thru:
                connection.execute("INSERT OR IGNORE INTO product_tags(product_id,tag) VALUES(?, 'ran-thru-collection')", (product_id,))
        connection.execute("INSERT INTO catalog_import_migrations(version) VALUES ('002-canonical-taxonomy')")


def existing_sku_conflicts(connection: sqlite3.Connection, source: ProductSource) -> None:
    for variant in source.variants:
        row = connection.execute("SELECT p.slug FROM product_variants v JOIN products p ON p.id=v.product_id WHERE v.sku=?", (variant["sku"],)).fetchone()
        if row and row[0] != source.data["slug"]:
            raise ImportErrorWithContext(f"{source.directory.relative_to(ROOT)}: SKU '{variant['sku']}' already belongs to '{row[0]}'")


def sync_product(connection: sqlite3.Connection, source: ProductSource) -> tuple[str, int]:
    data = source.data
    existing_sku_conflicts(connection, source)
    sale_price = data["price_cents"] if data["compare_at_price_cents"] is not None else None
    regular_price = data["compare_at_price_cents"] or data["price_cents"]
    row = connection.execute("SELECT id FROM products WHERE slug=?", (data["slug"],)).fetchone()
    values = (data["name"], data["description"], regular_price, data["category"], int(data["active"]), data["stripe_checkout_url"], data["brand"], data["product_type"], int(data["is_new"]), int(sale_price is not None), sale_price, int(data["is_ran_thru"]), data["featured_rank"], data["category_id"], data["subtype_id"])
    if row:
        product_id = row[0]
        connection.execute("UPDATE products SET name=?,description=?,price_cents=?,category=?,active=?,stripe_checkout_url=?,brand=?,product_type=?,is_new=?,is_sale=?,sale_price_cents=?,is_ran_thru=?,featured_rank=?,category_id=?,subtype_id=? WHERE id=?", (*values, product_id))
        action = "updated"
    else:
        cursor = connection.execute("INSERT INTO products(name,slug,description,price_cents,category,active,stripe_checkout_url,brand,product_type,is_new,is_sale,sale_price_cents,is_ran_thru,featured_rank,category_id,subtype_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (data["name"], data["slug"], data["description"], regular_price, data["category"], int(data["active"]), data["stripe_checkout_url"], data["brand"], data["product_type"], int(data["is_new"]), int(sale_price is not None), sale_price, int(data["is_ran_thru"]), data["featured_rank"], data["category_id"], data["subtype_id"]))
        product_id = cursor.lastrowid
        action = "inserted"
    connection.execute("DELETE FROM product_images WHERE product_id=?", (product_id,))
    connection.execute("DELETE FROM product_variants WHERE product_id=?", (product_id,))
    connection.execute("DELETE FROM product_audiences WHERE product_id=?", (product_id,))
    connection.execute("DELETE FROM product_tags WHERE product_id=?", (product_id,))
    connection.execute("DELETE FROM catalog_taxonomy_review WHERE product_id=?", (product_id,))
    for image in source.images:
        url = f"/images/products/{data['slug']}/{image['file']}"
        connection.execute("INSERT INTO product_images(product_id,url,alt_text,display_order,is_primary) VALUES(?,?,?,?,?)", (product_id, url, image["alt_text"], image["display_order"], int(image["primary"])))
    for variant in source.variants:
        connection.execute("INSERT INTO product_variants(product_id,sku,size,color,stock_quantity,price_cents,active) VALUES(?,?,?,?,?,?,?)", (product_id, variant["sku"], variant["size"], variant["color"], variant["stock_quantity"], variant["price_cents"], int(variant["active"])))
    for audience in data["audiences"]:
        connection.execute("INSERT INTO product_audiences(product_id,audience) VALUES(?,?)", (product_id, audience))
    for tag in data["tags"]:
        connection.execute("INSERT INTO product_tags(product_id,tag) VALUES(?,?)", (product_id, tag))
    return action, product_id


def stage_images(products: list[ProductSource]) -> tuple[Path, list[tuple[Path, Path]]]:
    staging = Path(tempfile.mkdtemp(prefix="ran-thru-product-import-", dir=ROOT))
    copies = []
    for product in products:
        for image in product.images:
            staged = staging / product.data["slug"] / image["file"]
            staged.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image["source"], staged)
            copies.append((staged, PUBLIC_IMAGES / product.data["slug"] / image["file"]))
    return staging, copies


def install_images(copies: list[tuple[Path, Path]]) -> list[tuple[Path, Path | None]]:
    backups: list[tuple[Path, Path | None]] = []
    for source, destination in copies:
        destination.parent.mkdir(parents=True, exist_ok=True)
        backup = None
        if destination.exists():
            backup = destination.with_name(f".{destination.name}.catalog-backup")
            shutil.copy2(destination, backup)
        shutil.copy2(source, destination)
        backups.append((destination, backup))
    return backups


def rollback_images(backups: list[tuple[Path, Path | None]]) -> None:
    for destination, backup in reversed(backups):
        if backup and backup.exists(): shutil.move(str(backup), str(destination))
        elif destination.exists(): destination.unlink()


def clear_backups(backups: list[tuple[Path, Path | None]]) -> None:
    for _, backup in backups:
        if backup and backup.exists(): backup.unlink()


def synchronize(*, dry_run: bool = False) -> dict[str, int]:
    sources = scan_master()
    if not DB.exists():
        raise ImportErrorWithContext(f"catalog database not found: {DB}")
    if dry_run:
        connection = sqlite3.connect(DB)
        try:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            missing = {"products", "product_images", "product_variants"} - tables
            if missing:
                raise ImportErrorWithContext(f"database is missing required tables: {', '.join(sorted(missing))}")
            review = connection.execute("SELECT COUNT(*) FROM catalog_taxonomy_review").fetchone()[0] if "catalog_taxonomy_review" in tables else 0
            summary = {"scanned": len(sources), "inserted": 0, "updated": 0, "images": sum(len(item.images) for item in sources), "review": review}
            for source in sources:
                existing_sku_conflicts(connection, source)
                exists = connection.execute("SELECT 1 FROM products WHERE slug=?", (source.data["slug"],)).fetchone()
                summary["updated" if exists else "inserted"] += 1
            return summary
        finally:
            connection.close()
    staging, copies = stage_images(sources)
    connection = sqlite3.connect(DB)
    connection.execute("PRAGMA foreign_keys = ON")
    backups: list[tuple[Path, Path | None]] = []
    summary = {"scanned": len(sources), "inserted": 0, "updated": 0, "images": len(copies), "review": 0}
    try:
        with connection:
            migrate_schema(connection)
            for source in sources:
                action, _ = sync_product(connection, source)
                summary[action] += 1
            summary["review"] = connection.execute("SELECT COUNT(*) FROM catalog_taxonomy_review").fetchone()[0]
            backups = install_images(copies)
    except Exception:
        rollback_images(backups)
        raise
    finally:
        connection.close()
        shutil.rmtree(staging, ignore_errors=True)
    clear_backups(backups)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Import master-folder products into SQLite")
    parser.add_argument("--dry-run", action="store_true", help="validate and preview without writing files or SQLite")
    args = parser.parse_args()
    try:
        result = synchronize(dry_run=args.dry_run)
    except ImportErrorWithContext as error:
        raise SystemExit(f"Import failed: {error}") from error
    mode = "Dry run" if args.dry_run else "Imported"
    print(f"{mode}: {result['scanned']} folders, {result['inserted']} inserted, {result['updated']} updated, {result['images']} images, {result['review']} taxonomy records requiring review")


if __name__ == "__main__":
    main()
