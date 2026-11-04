#!/usr/bin/env python3
"""Import locally supplied, rights-cleared product photographs.

Images are discovered in product-images/incoming/<product-slug-or-id>/ and are
published as optimized WebP files below public/images/products/<product-slug>/.
An optional product-images/mapping.json can match individual files by SKU,
slug, or product ID and supply accessible alt text.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "products.db"
INCOMING = ROOT / "product-images" / "incoming"
MAPPING = ROOT / "product-images" / "mapping.json"
PUBLIC = ROOT / "public"
DESTINATION = PUBLIC / "images" / "products"
REPORT = ROOT / "data" / "product-image-import-report.json"
SUPPORTED = {".jpg", ".jpeg", ".png", ".webp"}
MAX_EDGE = 2000


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def natural_key(path: Path) -> list[Any]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


def load_mapping(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"Invalid mapping JSON: {error}") from error
    entries = payload.get("files", payload)
    if not isinstance(entries, dict):
        raise SystemExit("mapping.json must be an object, or contain a 'files' object")
    if not all(isinstance(value, dict) for value in entries.values()):
        raise SystemExit("Every mapping entry must be an object")
    return {str(key).replace("\\", "/"): value for key, value in entries.items()}


def products(connection: sqlite3.Connection) -> tuple[dict[str, sqlite3.Row], dict[str, sqlite3.Row], dict[str, sqlite3.Row]]:
    rows = list(connection.execute("SELECT id, slug, name FROM products"))
    by_slug = {row["slug"]: row for row in rows}
    by_id = {str(row["id"]): row for row in rows}
    by_sku = {row["sku"]: row for row in connection.execute(
        "SELECT v.sku, p.id, p.slug, p.name FROM product_variants v JOIN products p ON p.id=v.product_id"
    )}
    return by_slug, by_id, by_sku


def identify(relative: Path, mapping: dict[str, dict[str, Any]], by_slug: dict[str, sqlite3.Row], by_id: dict[str, sqlite3.Row], by_sku: dict[str, sqlite3.Row]) -> tuple[sqlite3.Row | None, dict[str, Any]]:
    metadata = mapping.get(relative.as_posix(), {})
    if metadata:
        matches = [metadata[key] for key in ("sku", "slug", "product_id") if metadata.get(key) is not None]
        if len(matches) != 1:
            return None, metadata
        key = "sku" if "sku" in metadata else "slug" if "slug" in metadata else "product_id"
        return {"sku": by_sku, "slug": by_slug, "product_id": by_id}[key].get(str(metadata[key])), metadata
    if len(relative.parts) > 1:
        key = relative.parts[0]
        return by_slug.get(key) or by_id.get(key) or by_sku.get(key), metadata
    return None, metadata


def optimize(source: Path, output: Path) -> None:
    try:
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if "transparency" in image.info else "RGB")
            output.parent.mkdir(parents=True, exist_ok=True)
            image.save(output, "WEBP", quality=85, method=6)
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError(str(error)) from error


def local_url(path: Path) -> str:
    return "/" + path.relative_to(PUBLIC).as_posix()


def validate_urls(connection: sqlite3.Connection) -> list[str]:
    broken = []
    for row in connection.execute("SELECT url FROM product_images WHERE url LIKE '/%'"):
        candidate = (PUBLIC / row["url"].lstrip("/")).resolve()
        try:
            candidate.relative_to(PUBLIC.resolve())
        except ValueError:
            broken.append(row["url"])
            continue
        if not candidate.is_file():
            broken.append(row["url"])
    return broken


def main() -> None:
    parser = argparse.ArgumentParser(description="Import locally supplied product photos and export the catalog")
    parser.add_argument("--source", type=Path, default=INCOMING, help="folder containing <slug-or-id>/image files")
    parser.add_argument("--mapping", type=Path, default=MAPPING, help="optional explicit file mapping JSON")
    parser.add_argument("--dry-run", action="store_true", help="report matches without changing files or the catalog")
    args = parser.parse_args()
    source = args.source.resolve()
    if not source.is_dir():
        raise SystemExit(f"Image source folder does not exist: {source}")
    mapping = load_mapping(args.mapping)
    files = sorted((path for path in source.rglob("*") if path.is_file()), key=natural_key)
    report: dict[str, Any] = {"generated_at": datetime.now(timezone.utc).isoformat(), "source": str(source), "successful_imports": [], "unmatched_files": [], "duplicate_images": [], "invalid_files": [], "products_without_images": [], "broken_published_urls": []}
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    by_slug, by_id, by_sku = products(connection)
    seen_hashes: dict[str, Path] = {}
    grouped: dict[int, list[tuple[Path, sqlite3.Row, dict[str, Any]]]] = defaultdict(list)
    for file in files:
        relative = file.relative_to(source)
        if file.suffix.lower() not in SUPPORTED:
            report["unmatched_files"].append({"file": relative.as_posix(), "reason": "unsupported format"})
            continue
        value = digest(file)
        if value in seen_hashes:
            report["duplicate_images"].append({"file": relative.as_posix(), "duplicate_of": seen_hashes[value].relative_to(source).as_posix()})
            continue
        seen_hashes[value] = file
        product, metadata = identify(relative, mapping, by_slug, by_id, by_sku)
        if product is None:
            report["unmatched_files"].append({"file": relative.as_posix(), "reason": "no product matched by folder or mapping"})
            continue
        grouped[product["id"]].append((file, product, metadata))
    if not args.dry_run:
        try:
            connection.execute("BEGIN")
            for product_id, images in grouped.items():
                existing = list(connection.execute("SELECT url FROM product_images WHERE product_id=?", (product_id,)))
                next_order = connection.execute("SELECT COALESCE(MAX(display_order), -1) + 1 FROM product_images WHERE product_id=?", (product_id,)).fetchone()[0]
                primary = not existing
                for position, (file, product, metadata) in enumerate(images, start=1):
                    # The short content hash makes repeated batches collision-safe while
                    # retaining a readable, naturally ordered filename.
                    filename = f"{position:02d}-{re.sub(r'[^a-z0-9-]+', '-', file.stem.lower()).strip('-')}-{digest(file)[:10]}.webp"
                    output = DESTINATION / product["slug"] / filename
                    url = local_url(output)
                    if any(row["url"] == url for row in existing):
                        report["duplicate_images"].append({"file": file.relative_to(source).as_posix(), "duplicate_of": url})
                        continue
                    try:
                        optimize(file, output)
                    except ValueError as error:
                        report["invalid_files"].append({"file": file.relative_to(source).as_posix(), "reason": str(error)})
                        continue
                    alt = str(metadata.get("alt_text") or product["name"]).strip()
                    connection.execute("INSERT INTO product_images(product_id,url,alt_text,display_order,is_primary) VALUES(?,?,?,?,?)", (product_id, url, alt, next_order, int(primary)))
                    report["successful_imports"].append({"product_id": product_id, "slug": product["slug"], "file": file.relative_to(source).as_posix(), "url": url, "alt_text": alt, "primary": primary})
                    next_order += 1
                    primary = False
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        # Export only after the image records and files commit successfully.
        from export_products import export, validate
        validate(connection)
        export(connection)
    report["products_without_images"] = [dict(row) for row in connection.execute("SELECT id, slug, name FROM products WHERE NOT EXISTS (SELECT 1 FROM product_images WHERE product_images.product_id=products.id) ORDER BY slug")]
    report["broken_published_urls"] = validate_urls(connection)
    report["summary"] = {key: len(report[key]) for key in ("successful_imports", "unmatched_files", "duplicate_images", "invalid_files", "products_without_images", "broken_published_urls")}
    if args.dry_run:
        connection.close()
        print(json.dumps(report["summary"], indent=2))
        return
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    connection.close()
    print(json.dumps(report["summary"], indent=2))
    if report["invalid_files"] or report["broken_published_urls"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
