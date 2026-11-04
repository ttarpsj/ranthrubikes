#!/usr/bin/env python3
"""One-command master folder → SQLite → public JSON synchronization."""
import argparse
import shutil
from import_products import ImportErrorWithContext, ROOT, TAXONOMY, synchronize
from export_products import connect, export, validate


def main() -> None:
    parser = argparse.ArgumentParser(description="Synchronize master products, images, SQLite, and products.json")
    parser.add_argument("--dry-run", action="store_true", help="validate master folders and preview without changes")
    args = parser.parse_args()
    try:
        result = synchronize(dry_run=args.dry_run)
        if args.dry_run:
            connection = connect()
            try:
                validate(connection)
            finally:
                connection.close()
            print(f"Dry run: {result['scanned']} folders, {result['images']} images, {result['review']} taxonomy records requiring review; no files or database records changed")
            return
        connection = connect()
        try:
            validate(connection)
            export(connection)
        finally:
            connection.close()
        shutil.copy2(TAXONOMY, ROOT / "data" / "taxonomy.json")
        print(f"Synchronized: {result['scanned']} folders, {result['inserted']} inserted, {result['updated']} updated, {result['images']} images, {result['review']} taxonomy records requiring review; exported products and taxonomy JSON")
    except ImportErrorWithContext as error:
        raise SystemExit(f"Synchronization failed: {error}") from error


if __name__ == "__main__":
    main()
