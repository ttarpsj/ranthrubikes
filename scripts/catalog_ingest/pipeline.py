from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import shutil
import sqlite3
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from import_products import ImportErrorWithContext, ROOT, load_taxonomy, validate_taxonomy_path


DB = ROOT / "database" / "products.db"
BRAND_CONFIGS = ROOT / "config" / "brands"
BACKUPS = ROOT / "database" / "backups"


class IngestError(ValueError):
    pass


def slugify(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-")


def normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def cents(value: Any) -> int | None:
    if value is None or value == "": return None
    if isinstance(value, int): return value
    try: return round(float(str(value).replace("$", "").replace(",", "")) * 100)
    except ValueError: return None


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def migrate(con: sqlite3.Connection) -> None:
    columns = {row[1] for row in con.execute("PRAGMA table_info(products)")}
    for name, definition in {
        "catalog_imported": "INTEGER NOT NULL DEFAULT 0 CHECK(catalog_imported IN (0,1))",
        "manual_description": "INTEGER NOT NULL DEFAULT 0 CHECK(manual_description IN (0,1))",
        "manual_price": "INTEGER NOT NULL DEFAULT 0 CHECK(manual_price IN (0,1))",
        "manual_merchandising": "INTEGER NOT NULL DEFAULT 0 CHECK(manual_merchandising IN (0,1))",
    }.items():
        if name not in columns: con.execute(f"ALTER TABLE products ADD COLUMN {name} {definition}")
    con.executescript("""
    CREATE TABLE IF NOT EXISTS catalog_sources (
      id INTEGER PRIMARY KEY, brand TEXT NOT NULL UNIQUE, source_type TEXT NOT NULL,
      source_ref TEXT, requires_credentials INTEGER NOT NULL DEFAULT 0,
      requires_agreement INTEGER NOT NULL DEFAULT 0, rate_limit_seconds REAL NOT NULL DEFAULT 1,
      public_metadata_allowed INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS catalog_import_runs (
      id INTEGER PRIMARY KEY, brand TEXT, source_path TEXT, started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      completed_at TEXT, dry_run INTEGER NOT NULL, imported_count INTEGER NOT NULL DEFAULT 0,
      review_count INTEGER NOT NULL DEFAULT 0, rejected_count INTEGER NOT NULL DEFAULT 0, notes TEXT
    );
    CREATE TABLE IF NOT EXISTS catalog_import_records (
      id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL REFERENCES catalog_sources(id),
      external_id TEXT, fingerprint TEXT NOT NULL, raw_payload TEXT NOT NULL,
      status TEXT NOT NULL CHECK(status IN ('imported','review','rejected','duplicate-review')),
      reason TEXT, product_id INTEGER REFERENCES products(id), run_id INTEGER REFERENCES catalog_import_runs(id),
      imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(source_id, fingerprint)
    );
    CREATE TABLE IF NOT EXISTS product_external_ids (
      product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
      brand TEXT NOT NULL, identifier_type TEXT NOT NULL, identifier TEXT NOT NULL,
      PRIMARY KEY(brand, identifier_type, identifier)
    );
    CREATE TABLE IF NOT EXISTS product_attributes (
      product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
      attribute_key TEXT NOT NULL, attribute_value TEXT NOT NULL,
      PRIMARY KEY(product_id, attribute_key)
    );
    CREATE TABLE IF NOT EXISTS product_image_sources (
      id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
      source_url TEXT NOT NULL, rights_status TEXT NOT NULL CHECK(rights_status IN ('unknown','cleared','licensed','rejected')),
      rights_note TEXT, local_path TEXT, published INTEGER NOT NULL DEFAULT 0 CHECK(published IN (0,1)),
      UNIQUE(product_id, source_url)
    );
    CREATE TABLE IF NOT EXISTS product_review_state (
      product_id INTEGER PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
      state TEXT NOT NULL CHECK(state IN ('approved','review','rejected')),
      reason TEXT, reviewed_at TEXT, approved_at TEXT
    );
    """)
    con.execute("INSERT OR IGNORE INTO product_review_state(product_id,state,approved_at) SELECT id,'approved',CURRENT_TIMESTAMP FROM products WHERE catalog_imported=0")


def load_brand(brand: str) -> dict[str, Any]:
    path = BRAND_CONFIGS / f"{slugify(brand)}.json"
    if not path.is_file(): raise IngestError(f"No configuration for brand '{brand}'")
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("brand") != brand: raise IngestError(f"Brand config mismatch in {path.name}")
    return config


def source_id(con: sqlite3.Connection, config: dict[str, Any]) -> int:
    con.execute("""INSERT INTO catalog_sources(brand,source_type,source_ref,requires_credentials,requires_agreement,rate_limit_seconds,public_metadata_allowed)
        VALUES(?,?,?,?,?,?,?) ON CONFLICT(brand) DO UPDATE SET source_type=excluded.source_type,source_ref=excluded.source_ref,
        requires_credentials=excluded.requires_credentials,requires_agreement=excluded.requires_agreement,rate_limit_seconds=excluded.rate_limit_seconds,
        public_metadata_allowed=excluded.public_metadata_allowed,updated_at=CURRENT_TIMESTAMP""",
        (config["brand"], config["source_type"], config.get("source_ref"), int(config.get("requires_credentials",False)), int(config.get("requires_agreement",False)), config.get("rate_limit_seconds",1), int(config.get("public_metadata_allowed",False))))
    return con.execute("SELECT id FROM catalog_sources WHERE brand=?",(config["brand"],)).fetchone()[0]


def category(record: dict[str, Any], config: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    taxonomy = load_taxonomy()
    category_id = record.get("category_id") or config.get("category_map",{}).get(str(record.get("category","")).strip().lower())
    known = {item["id"]: item["label"] for item in taxonomy["top_level"] if item.get("kind")=="category"}
    if category_id not in known: return None, None, None
    subtype_id = record.get("subtype_id") or record.get("product_type")
    if category_id == "clothing" and not subtype_id: return None, None, None
    return category_id, known[category_id], str(subtype_id).strip() if subtype_id else None


def normalise(record: dict[str, Any], config: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    name = str(record.get("name") or record.get("title") or "").strip()
    description = str(record.get("description") or record.get("short_description") or "").strip()
    price = cents(record.get("price_cents") if record.get("price_cents") is not None else record.get("price"))
    stock = record.get("stock_quantity", record.get("stock", 0))
    try: stock = max(0, int(stock))
    except (TypeError, ValueError): stock = 0
    category_id, category_label, subtype_id = category(record,config)
    identifier = str(record.get("sku") or record.get("mpn") or record.get("manufacturer_sku") or "").strip()
    if not name: return None, "missing product name"
    if price is None or price < 0: return None, "missing or invalid price"
    if not category_id: return None, "missing or invalid Ran Thru category mapping"
    if not identifier: return None, "missing manufacturer SKU/MPN"
    try:
        category_id, category_label, subtype_id, audiences, tags = validate_taxonomy_path({
            "category_id": category_id, "subtype_id": subtype_id,
            "subtype_label": record.get("subtype_label") or subtype_id,
            "audiences": record.get("audiences", ["unisex"]), "tags": record.get("tags", []),
        }, load_taxonomy(), "external feed")
    except ImportErrorWithContext as error:
        return None, str(error)
    variants = record.get("variants") if isinstance(record.get("variants"),list) else []
    if not variants: variants=[{"sku":identifier,"stock_quantity":stock,"size":record.get("size"),"color":record.get("color")}]
    return {"name":name,"description":description,"price":price,"stock":stock,"category_id":category_id,"category":category_label,"subtype_id":subtype_id,"audiences":audiences,"tags":tags,"identifier":identifier,"variants":variants,"attributes":record.get("attributes",{}),"images":record.get("images",[]),"rights_status":record.get("image_rights","unknown")}, None


def existing_product(con: sqlite3.Connection, brand: str, item: dict[str, Any]) -> tuple[int | None, str | None]:
    row = con.execute("SELECT product_id FROM product_external_ids WHERE brand=? AND identifier=?",(brand,item["identifier"])).fetchone()
    if row: return row[0], None
    row = con.execute("SELECT id FROM products WHERE lower(brand)=lower(?) AND replace(replace(lower(name),' ',''),'-','')=?",(brand,normalized_name(item["name"]))).fetchone()
    return (row[0], "name fallback requires review") if row else (None,None)


def _unique_slug(con: sqlite3.Connection, value: str) -> str:
    base=slugify(value) or "product"; slug=base; index=2
    while con.execute("SELECT 1 FROM products WHERE slug=?",(slug,)).fetchone(): slug=f"{base}-{index}"; index+=1
    return slug


def import_records(brand: str, records: list[dict[str, Any]], source_path: str, *, dry_run: bool=False, override_manual: bool=False) -> dict[str,int]:
    config=load_brand(brand)
    con=connect(); summary={"created":0,"updated":0,"review":0,"rejected":0,"duplicate_review":0}
    try:
        if dry_run:
            tables={row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for raw in records:
                item,reason=normalise(raw,config)
                if not item:
                    summary["rejected"]+=1
                    continue
                if "product_external_ids" in tables:
                    existing,fallback=existing_product(con,brand,item)
                else:
                    existing,fallback=None,None
                if not fallback: summary["updated" if existing else "created"]+=1
                summary["duplicate_review" if fallback else "review"]+=1
            return summary
        migrate(con)
        with con:
            sid=source_id(con,config)
            run=con.execute("INSERT INTO catalog_import_runs(brand,source_path,dry_run) VALUES(?,?,?)",(brand,source_path,int(dry_run))).lastrowid
            for raw in records:
                fingerprint=hashlib.sha256(json.dumps(raw,sort_keys=True,default=str).encode()).hexdigest()
                item,reason=normalise(raw,config)
                status="rejected" if reason else "review"; product_id=None
                if item:
                    product_id, fallback=existing_product(con,brand,item)
                    if fallback: status="duplicate-review"; reason=fallback
                    elif not dry_run:
                        is_new=product_id is None
                        if product_id is None:
                            product_id=con.execute("INSERT INTO products(name,slug,description,price_cents,category,active,brand,product_type,category_id,subtype_id,catalog_imported) VALUES(?,?,?,?,?,?,?,?,?,?,1)",(item["name"],_unique_slug(con,f"{brand}-{item['name']}"),item["description"],item["price"],item["category"],0,brand,item["subtype_id"],item["category_id"],item["subtype_id"])).lastrowid
                        else:
                            current=con.execute("SELECT manual_description,manual_price FROM products WHERE id=?",(product_id,)).fetchone()
                            if override_manual or not current["manual_description"]: con.execute("UPDATE products SET name=?,description=?,category=?,category_id=?,subtype_id=?,product_type=? WHERE id=?",(item["name"],item["description"],item["category"],item["category_id"],item["subtype_id"],item["subtype_id"],product_id))
                            if override_manual or not current["manual_price"]: con.execute("UPDATE products SET price_cents=? WHERE id=?",(item["price"],product_id))
                        con.execute("INSERT OR REPLACE INTO product_external_ids(product_id,brand,identifier_type,identifier) VALUES(?,?,?,?)",(product_id,brand,"manufacturer_sku",item["identifier"]))
                        con.execute("INSERT OR REPLACE INTO product_review_state(product_id,state,reason) VALUES(?,?,?)",(product_id,"review","Imported product requires approval"))
                        con.execute("UPDATE products SET active=0 WHERE id=?",(product_id,))
                        con.execute("DELETE FROM product_variants WHERE product_id=?",(product_id,))
                        con.execute("DELETE FROM product_audiences WHERE product_id=?",(product_id,))
                        con.execute("DELETE FROM product_tags WHERE product_id=?",(product_id,))
                        for variant in item["variants"]:
                            sku=str(variant.get("sku") or item["identifier"]).strip()
                            con.execute("INSERT OR REPLACE INTO product_variants(product_id,sku,size,color,stock_quantity,active) VALUES(?,?,?,?,?,1)",(product_id,sku,variant.get("size"),variant.get("color"),max(0,int(variant.get("stock_quantity",item["stock"]) or 0))))
                        for audience in item["audiences"]: con.execute("INSERT INTO product_audiences(product_id,audience) VALUES(?,?)",(product_id,audience))
                        for tag in item["tags"]: con.execute("INSERT INTO product_tags(product_id,tag) VALUES(?,?)",(product_id,tag))
                        for key,value in (item["attributes"] or {}).items():
                            if value is not None: con.execute("INSERT OR REPLACE INTO product_attributes(product_id,attribute_key,attribute_value) VALUES(?,?,?)",(product_id,str(key),str(value)))
                        for image in item["images"] if isinstance(item["images"],list) else []:
                            url=image.get("url") if isinstance(image,dict) else image
                            if url: con.execute("INSERT OR IGNORE INTO product_image_sources(product_id,source_url,rights_status,published) VALUES(?,?,?,0)",(product_id,str(url),item["rights_status"]))
                        summary["created" if is_new else "updated"]+=1
                if not dry_run:
                    con.execute("INSERT OR REPLACE INTO catalog_import_records(source_id,external_id,fingerprint,raw_payload,status,reason,product_id,run_id) VALUES(?,?,?,?,?,?,?,?)",(sid,item["identifier"] if item else None,fingerprint,json.dumps(raw),status,reason,product_id,run))
                summary[status.replace("-","_")]+=1
            if not dry_run: con.execute("UPDATE catalog_import_runs SET completed_at=CURRENT_TIMESTAMP,imported_count=?,review_count=?,rejected_count=? WHERE id=?",(summary["created"]+summary["updated"],summary["review"]+summary["duplicate_review"],summary["rejected"],run))
        return summary
    finally: con.close()


def approve(con: sqlite3.Connection, slug: str) -> None:
    product=con.execute("SELECT id,price_cents FROM products WHERE slug=?",(slug,)).fetchone()
    if not product: raise IngestError(f"Unknown product '{slug}'")
    variants=con.execute("SELECT COUNT(*) FROM product_variants WHERE product_id=? AND stock_quantity>=0",(product["id"],)).fetchone()[0]
    rights=con.execute("SELECT COUNT(*) FROM product_image_sources WHERE product_id=? AND rights_status IN ('cleared','licensed')",(product["id"],)).fetchone()[0]
    if product["price_cents"] < 0 or not variants: raise IngestError("Approval requires valid pricing and at least one variant")
    if con.execute("SELECT COUNT(*) FROM product_image_sources WHERE product_id=?",(product["id"],)).fetchone()[0] and not rights: raise IngestError("Approval requires rights-cleared images or no images")
    con.execute("UPDATE products SET active=1 WHERE id=?",(product["id"],))
    con.execute("UPDATE product_review_state SET state='approved',reason=NULL,reviewed_at=CURRENT_TIMESTAMP,approved_at=CURRENT_TIMESTAMP WHERE product_id=?",(product["id"],))


def download_licensed_images(con: sqlite3.Connection, slug: str, *, dry_run: bool=False) -> int:
    """Download only images explicitly marked cleared/licensed by the feed agreement."""
    product=con.execute("SELECT id FROM products WHERE slug=?",(slug,)).fetchone()
    if not product: raise IngestError(f"Unknown product '{slug}'")
    rows=con.execute("SELECT id,source_url FROM product_image_sources WHERE product_id=? AND rights_status IN ('cleared','licensed') AND local_path IS NULL",(product["id"],)).fetchall()
    target=ROOT / "public" / "images" / "products" / slug
    count=0
    for index,row in enumerate(rows):
        parsed=urllib.parse.urlparse(row["source_url"])
        extension=Path(parsed.path).suffix.lower()
        if extension not in {".jpg",".jpeg",".png",".webp"}: extension=".jpg"
        destination=target / f"licensed-{index + 1}{extension}"
        if not dry_run:
            target.mkdir(parents=True,exist_ok=True)
            try:
                request=urllib.request.Request(row["source_url"],headers={"User-Agent":"RanThruCatalog/1.0"})
                with urllib.request.urlopen(request,timeout=30) as response: destination.write_bytes(response.read())
            except OSError as error:
                raise IngestError(f"could not download licensed image: {error}") from error
            url=f"/images/products/{slug}/{destination.name}"
            con.execute("UPDATE product_image_sources SET local_path=?,published=0 WHERE id=?",(str(destination.relative_to(ROOT)),row["id"]))
            con.execute("INSERT INTO product_images(product_id,url,alt_text,display_order,is_primary) VALUES(?,?,?,?,?)",(product["id"],url,slug.replace("-"," "),index,int(index==0)))
        count+=1
    return count


def backup() -> Path:
    BACKUPS.mkdir(parents=True,exist_ok=True)
    destination=BACKUPS / f"products-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
    shutil.copy2(DB,destination); return destination
