#!/usr/bin/env python3
"""Audit catalog image references without treating a populated URL as a usable asset.

Only local, published product assets beneath public/images/products are counted as
working.  Remote URLs are deliberately classified separately: public reachability
does not establish a product match or reuse permission.
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "products.db"
PUBLIC = ROOT / "public"
REPORT = ROOT / "data" / "product-image-audit.json"
STATIC_REPORT = ROOT / "static-export" / "data" / "product-image-audit.json"


def local_path(url: str) -> Path | None:
    if not url.startswith("/") or url.startswith("//"):
        return None
    candidate = (PUBLIC / url.lstrip("/")).resolve()
    try:
        candidate.relative_to(PUBLIC.resolve())
    except ValueError:
        return None
    return candidate


def main() -> None:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    products = list(con.execute("SELECT id, slug, name, brand FROM products ORDER BY id"))
    refs = {p["id"]: list(con.execute(
        "SELECT url, alt_text, display_order, is_primary FROM product_images WHERE product_id=? ORDER BY is_primary DESC, display_order, id",
        (p["id"],),
    )) for p in products}
    permitted = {row["product_id"] for row in con.execute(
        "SELECT DISTINCT product_id FROM product_image_sources WHERE published=1 AND rights_status IN ('cleared','licensed')"
    )}
    source_policy = {row["brand"]: row for row in con.execute(
        "SELECT brand, requires_credentials, requires_agreement FROM catalog_sources"
    )}

    rows, totals = [], Counter()
    for product in products:
        image_rows = refs[product["id"]]
        local = [local_path(image["url"]) for image in image_rows]
        existing = [path for path in local if path and path.is_file()]
        remote = [image["url"] for image in image_rows if local_path(image["url"]) is None]
        broken_local = [image["url"] for image, path in zip(image_rows, local) if path and not path.is_file()]
        protected_source = source_policy.get(product["brand"])
        status = "permission_required" if protected_source and (
            protected_source["requires_credentials"] or protected_source["requires_agreement"]
        ) else "missing"
        if remote:
            status = "unverified_remote"
        elif broken_local:
            status = "broken_local"
        elif image_rows and len(existing) == len(image_rows) and product["id"] in permitted:
            status = "working"
        elif image_rows:
            status = "permission_required"
        totals[status] += 1
        if len(existing) > 1 and status == "working":
            totals["multiple_images"] += 1
        rows.append({
            "id": product["id"], "slug": product["slug"], "name": product["name"], "brand": product["brand"],
            "status": status, "image_urls": [image["url"] for image in image_rows],
            "existing_local_images": ["/" + str(path.relative_to(PUBLIC)).replace("\\\\", "/") for path in existing],
            "broken_local_references": broken_local, "remote_references": remote,
        })

    sources = list(con.execute("SELECT brand, requires_credentials, requires_agreement FROM catalog_sources ORDER BY brand"))
    report = {
        "policy": "Working means a local file exists and its product_image_sources record is published with cleared or licensed rights.",
        "summary": {
            "total_products": len(products), "products_with_working_images": totals["working"],
            "products_with_multiple_images": totals["multiple_images"], "products_missing_images": totals["missing"],
            "products_with_broken_image_references": totals["broken_local"] + totals["unverified_remote"],
            "products_requiring_photography_permissions": totals["permission_required"] + totals["unverified_remote"],
        },
        "configured_sources_requiring_credentials_or_agreement": [dict(row) for row in sources if row["requires_credentials"] or row["requires_agreement"]],
        "products": rows,
    }
    payload = json.dumps(report, indent=2) + "\n"
    REPORT.write_text(payload, encoding="utf-8")
    STATIC_REPORT.parent.mkdir(parents=True, exist_ok=True)
    STATIC_REPORT.write_text(payload, encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
