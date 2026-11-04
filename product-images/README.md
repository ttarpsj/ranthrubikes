# Local product image ingestion

Only place photographs that you own or are authorized to publish in `incoming`.
The importer never downloads images or creates remote image URLs.

## Fast path

1. Put JPEG, PNG, or WebP files into a product folder named for its product slug
   (or stable database ID), for example `product-images/incoming/ran-thru-merino-sock/01.jpg`.
   Files are ordered naturally: `01`, `02`, then `10`; the first is the primary
   catalog image when the product has no existing image.
2. From the project root, run:

   ```powershell
   python scripts/ingest_product_images.py
   ```

The command writes optimized WebP assets to `public/images/products/<slug>/`,
adds correctly ordered `product_images` records, updates `data/products.json`,
and writes `data/product-image-import-report.json`.

## Explicit mapping

Use `mapping.json` when a filename or folder cannot identify a product. Keys
are paths relative to `incoming`; match using exactly one of `sku`, `slug`, or
`product_id`. `alt_text` is optional and defaults to the existing product name.

```json
{
  "files": {
    "camera-drop/front.jpeg": { "sku": "RTB-001", "alt_text": "Ran Thru Merino Sock, side view" }
  }
}
```

Run `python scripts/ingest_product_images.py --dry-run` to check a batch first.
Unmatched files, duplicate content, invalid images, products still missing
images, and broken published URLs are all listed in the report. Local URL
checks use the same `public/` path Laravel Herd serves; open `/shop` after the
command to inspect the visible catalog image.
