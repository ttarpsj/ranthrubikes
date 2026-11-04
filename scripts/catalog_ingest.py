#!/usr/bin/env python3
"""Authorized external catalog feeds → review queue → static storefront JSON."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from catalog_ingest.adapters import AdapterError, fetch_structured_json
from catalog_ingest.parsers import FeedParseError, parse_feed
from catalog_ingest.pipeline import BRAND_CONFIGS, IngestError, approve, backup, connect, download_licensed_images, import_records, load_brand, migrate
from export_products import export, validate


def brands() -> list[str]:
    return [json.loads(path.read_text(encoding="utf-8"))["brand"] for path in sorted(BRAND_CONFIGS.glob("*.json"))]


def main() -> None:
    parser=argparse.ArgumentParser(description="Safe, review-first Ran Thru catalog ingestion")
    commands=parser.add_subparsers(dest="command",required=True)
    ingest=commands.add_parser("import",help="Import one authorized CSV, JSON, or XML feed")
    ingest.add_argument("--brand",required=True,choices=brands())
    ingest.add_argument("--file",required=True,type=Path)
    ingest.add_argument("--dry-run",action="store_true")
    ingest.add_argument("--override-manual",action="store_true",help="Permit feed values to replace manually locked price/description fields")
    all_feeds=commands.add_parser("import-all",help="Import files named <brand>.csv/.json/.xml from a directory")
    all_feeds.add_argument("--input-dir",required=True,type=Path)
    all_feeds.add_argument("--dry-run",action="store_true")
    commands.add_parser("validate",help="Validate the SQLite catalog for static export")
    review=commands.add_parser("review",help="List review and rejected imported records")
    review.add_argument("--status",choices=["review","rejected","duplicate-review"])
    approved=commands.add_parser("approve",help="Approve a reviewed product after pricing, availability, and image-rights checks")
    approved.add_argument("--slug",required=True)
    commands.add_parser("approve-demo",help="Approve explicitly labelled demonstration records after validation")
    images=commands.add_parser("download-images",help="Download only explicitly licensed/cleared feed images for one product")
    images.add_argument("--slug",required=True)
    images.add_argument("--dry-run",action="store_true")
    metadata=commands.add_parser("metadata",help="Fetch explicitly approved public structured JSON after a robots/rate-limit check")
    metadata.add_argument("--brand",required=True,choices=brands())
    metadata.add_argument("--url",required=True)
    commands.add_parser("sources",help="List configured sources and authorization blockers")
    commands.add_parser("export",help="Rebuild public-safe data/products.json")
    commands.add_parser("backup",help="Copy database/products.db into database/backups")
    args=parser.parse_args()
    try:
        if args.command=="sources":
            for brand in brands():
                config=load_brand(brand)
                status="configured" if config.get("source_ref") else "no source configured"
                blockers=[]
                if config.get("requires_credentials"): blockers.append("credentials")
                if config.get("requires_agreement"): blockers.append("agreement")
                print(f"{brand} | {status} | {config['source_type']} | {', '.join(blockers) or 'none'}")
        elif args.command=="metadata":
            config=load_brand(args.brand)
            payload=fetch_structured_json(args.url,user_agent="RanThruCatalog/1.0 (+authorized catalog ingestion)",rate_limit_seconds=float(config.get("rate_limit_seconds",1)),allow_public_metadata=bool(config.get("public_metadata_allowed",False)))
            print(json.dumps(payload,indent=2))
        elif args.command in {"import","import-all"}:
            jobs=[]
            if args.command=="import": jobs=[(args.brand,args.file)]
            else:
                for brand in brands():
                    stem=brand.lower().replace(" ","-")
                    found=next((args.input_dir / f"{stem}{suffix}" for suffix in (".csv",".json",".xml") if (args.input_dir / f"{stem}{suffix}").is_file()),None)
                    if found: jobs.append((brand,found))
            if not jobs: raise IngestError("No configured feed files found")
            total={"created":0,"updated":0,"review":0,"rejected":0,"duplicate_review":0}
            for brand,path in jobs:
                result=import_records(brand,parse_feed(path),str(path),dry_run=args.dry_run,override_manual=getattr(args,"override_manual",False))
                print(f"{brand}: {result}")
                for key in total: total[key]+=result[key]
            print(f"Total: {total}")
        elif args.command=="backup": print(backup())
        else:
            con=connect(); migrate(con)
            with con:
                if args.command=="approve": approve(con,args.slug); print(f"Approved: {args.slug}")
                elif args.command=="approve-demo":
                    rows=con.execute("SELECT slug FROM products WHERE catalog_imported=1 AND name LIKE 'DEMO %' ORDER BY slug").fetchall()
                    for row in rows: approve(con,row["slug"])
                    print(f"Approved demonstration products: {len(rows)}")
                elif args.command=="download-images": print(f"Licensed images {'ready' if args.dry_run else 'downloaded'}: {download_licensed_images(con,args.slug,dry_run=args.dry_run)}")
                elif args.command=="review":
                    sql="SELECT p.slug,p.brand,p.name,r.state,r.reason FROM product_review_state r JOIN products p ON p.id=r.product_id WHERE r.state!='approved'"
                    values=[]
                    if args.status: sql+=" AND r.state=?"; values=[args.status]
                    for row in con.execute(sql+" ORDER BY p.brand,p.name",values): print(" | ".join(str(value or "") for value in row))
                elif args.command=="validate": validate(con); print("Catalog validation: OK")
                elif args.command=="export": validate(con); export(con); print("Exported data/products.json")
            con.close()
    except (IngestError,FeedParseError,AdapterError,ValueError) as error:
        raise SystemExit(f"Catalog ingestion failed: {error}") from error

if __name__=="__main__": main()
