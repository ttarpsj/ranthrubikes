#!/usr/bin/env python3
"""Remove catalog image references that cannot be published under catalog policy."""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "products.db"


def main() -> None:
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys = ON")
    rows = list(con.execute("""
        SELECT i.id, i.product_id, i.url
        FROM product_images i
        LEFT JOIN product_image_sources s
          ON s.product_id=i.product_id AND s.local_path=i.url
             AND s.published=1 AND s.rights_status IN ('cleared','licensed')
        WHERE s.id IS NULL
    """))
    for image_id, product_id, url in rows:
        con.execute("""
            INSERT OR IGNORE INTO product_image_sources
              (product_id, source_url, rights_status, rights_note, local_path, published)
            VALUES (?, ?, 'rejected',
                    'Removed from storefront: no cleared or licensed local product-photography record.',
                    ?, 0)
        """, (product_id, url, url))
        con.execute("DELETE FROM product_images WHERE id=?", (image_id,))
    con.commit()
    print(f"Removed {len(rows)} non-publishable image reference(s).")


if __name__ == "__main__":
    main()
