# Product catalog workflow

The SQLite catalog at `database/products.db` remains the storefront’s source of truth. Manage it through `master/<slug>/` folders instead of TablePlus. The importer updates existing products by slug, preserves their numeric IDs, and never deletes database products merely because their folders are absent.

## Add a product

1. Copy `master/_template` to `master/<unique-slug>/`.
2. Rename the example image file entries in `product.json` to actual photographs placed in that same folder. Every configured photo must exist locally. The first photo, or the one marked `primary: true`, is the card photo.
3. Complete the canonical category fields, description, price, and active status. Prices are cents: `$45.00` is `4500`.
4. Add sizes and colors under `variants`; each SKU must be unique across the whole catalog. Set `stock_quantity` and optional variant-specific pricing.
5. Set `compare_at_price_cents` only when the regular price is higher. That creates a valid sale automatically. Never add a fabricated discount percentage.

## Taxonomy fields

`config/taxonomy.json` is the one shared taxonomy used by product import, public export, shop tiles and filters, and the hamburger navigation. Do not duplicate category lists in product manifests or frontend code.

- `category_id` is one of `clothing`, `equipment`, `components`, or `bikes-frames`.
- `subtype_id` is required for Clothing. Clothing values must match the IDs in `config/taxonomy.json`. Equipment, Components, and Bikes & Frames may use a stable catalog-specific subtype ID plus a human-readable `subtype_label`; the storefront derives those options from published products.
- `audiences` accepts canonical IDs: `men`, `women`, and `unisex`. A garment legitimately sold to both Men and Women uses `["men", "women"]`. Lifestyle and Accessories must use exactly `["unisex"]`.
- `tags` accepts `new-arrivals` and `ran-thru-collection`. These two collections are tag-only: creation time and brand name never grant membership.
- `brand` is a catalog value, not a taxonomy definition. The Brands view is generated from active product records.

Valid Clothing garment example:

```json
{
  "category_id": "clothing",
  "subtype_id": "short-sleeve-jerseys",
  "subtype_label": "Short Sleeve Jerseys",
  "audiences": ["men", "women"],
  "tags": ["new-arrivals", "ran-thru-collection"]
}
```

Valid unisex Accessories example:

```json
{
  "category_id": "clothing",
  "subtype_id": "socks",
  "subtype_label": "Socks",
  "audiences": ["unisex"],
  "tags": []
}
```

The importer rejects unknown category paths, invalid Clothing subtypes, duplicate tags or audiences, contradictory audience assignments, duplicate slugs, and duplicate SKUs. Safe legacy mappings are migrated automatically. Records that cannot be mapped without guessing remain intact and are listed in SQLite table `catalog_taxonomy_review` for manual correction.

See `master/_example/product.json` for a complete manifest. A missing or failed product photo displays the storefront’s solid-black placeholder.

## Synchronize and publish

Run one command from the repository root:

```powershell
python scripts/sync_products.py
```

Use `python scripts/sync_products.py --dry-run` to validate manifests and preview the folder/image count without changing SQLite, generated images, or JSON. A normal sync validates, upserts products, synchronizes image/variant records, copies photos to `public/images/products/<slug>/`, and exports the public-safe `data/products.json`.

To deactivate a product, set `active` to `false` in its manifest and synchronize. To remove an image, remove its image object from `product.json`, then synchronize; its SQLite image record is removed, while unrelated files are never deleted. Update pricing, variants, or photographs in the folder and run the same command again.

Commit the master folders, `database/products.db`, generated `data/products.json`, and generated public images. Pushing to `main` validates the master folders, synchronizes the catalog, exports JSON, and deploys Pages.

## Privacy

Only active products and their public storefront fields are exported. Never place supplier notes, cost prices, credentials, private launch material, or Stripe secret keys in a manifest or SQLite. If unpublished products cannot live in the public repository, keep their master folders and database in a private repository or private source branch, run synchronization in a private build step, and publish only the generated Pages artifact.

## Authorized supplier-feed ingestion

Use `scripts/catalog_ingest.py` for authorized supplier data. It supports CSV, JSON, and XML files; it does not guess manufacturer endpoints, bypass access controls, or scrape blocked pages. Brand configurations live in `config/brands/` for GOBIK, MAAP, Shimano, KASK, MET, Fizik, Selle Italia, SRAM, Elite, Garmin, Wahoo, Muc-Off, ENVE, VISION, Continental, Pirelli, Oakley, 100%, Specialized, and Colnago. Every included configuration is deliberately feed-first and marks credentials/dealer agreement as required until Ran Thru has an approved source.

```powershell
# Make a recoverable SQLite copy before any import
python scripts/catalog_ingest.py backup

# Show which feeds are actually configured and what authorization is missing
python scripts/catalog_ingest.py sources

# Preview one authorized dealer file without changing data
python scripts/catalog_ingest.py import --brand MAAP --file examples/authorized-feed.json --dry-run

# Import one brand into the review queue (never publicly active by default)
python scripts/catalog_ingest.py import --brand MAAP --file path/to/authorized-maap.json

# Import configured <brand>.csv/.json/.xml exports from one directory
python scripts/catalog_ingest.py import-all --input-dir path/to/feeds --dry-run

# Inspect rejection/review work, then approve after editorial checks
python scripts/catalog_ingest.py review
python scripts/catalog_ingest.py approve --slug maap-example-training-jersey

# Rebuild the public-safe static catalog only after approvals
python scripts/catalog_ingest.py export
```

Required incoming fields are `name`, a manufacturer `sku` or `mpn`, valid `price`/`price_cents`, canonical `category_id`, Clothing `subtype_id` where applicable, `audiences`, and stock or variants. See `examples/authorized-feed.json`. New records remain inactive in `product_review_state` until approved; duplicate brand + manufacturer SKU/MPN records update their canonical product, while same-brand name matches are held for review.

The importer preserves manually locked descriptions, prices, and merchandising fields. Use `--override-manual` only with editorial authorization. Image URLs are internal metadata until their `image_rights` value is `cleared` or `licensed`. Only then may `download-images --slug <slug>` download them to `public/images/products/<slug>/`; unknown-rights images are neither downloaded nor published. The optional structured-JSON adapter requires an explicit approved URL, checks `robots.txt`, uses a declared user agent and rate limit, and never handles login, paywalls, or anti-bot restrictions.

`examples/verified-demo-feeds/` is a separate, clearly labeled demonstration catalog. It uses public manufacturer pages only to verify product identity and limited public details; it has no licensed images and does not claim live Ran Thru stock. Items are prefixed `DEMO ·` in the storefront and use black image placeholders. It exists solely to exercise the catalog path until authorized dealer files are supplied.

### Rebuild the local demonstration catalog

The portfolio demonstration catalogue is deliberately generated separately from
authorised dealer feeds. It contains product identities and provenance links for
the twenty configured brands, but no republished product imagery, live stock, or
retail price claims. Generated records use an explicit `DEMO-` SKU, a clearly
identified illustrative price band, an illustrative configuration, and an internal provenance
attribute. Do not treat it as retail data.

```powershell
# Recreate the 20 local demonstration feed files (no network requests)
python scripts/generate_demo_catalog.py

# Preview then import through the same review-first ingestion path
python scripts/catalog_ingest.py import-all --input-dir examples/verified-demo-feeds --dry-run
python scripts/catalog_ingest.py backup
python scripts/catalog_ingest.py import-all --input-dir examples/verified-demo-feeds

# Approve only records visibly labelled DEMO, validate, and rebuild the local shop JSON
python scripts/catalog_ingest.py approve-demo
python scripts/catalog_ingest.py validate
python scripts/catalog_ingest.py export
```

Repeating the import updates the same canonical records by their `DEMO-` SKU; it
does not create duplicates. Replace these feeds with authorised brand exports for
any commercial use.

After a brand has granted written permission for a public structured-JSON URL, set that brand configuration's `public_metadata_allowed` to `true` and use `python scripts/catalog_ingest.py metadata --brand <brand> --url <approved-url>`. The command refuses every currently supplied brand configuration until that approval is recorded. To protect an editorial correction from later feed updates, set the corresponding `products.manual_description`, `products.manual_price`, or `products.manual_merchandising` field to `1`; feeds otherwise update only importer-managed values.
