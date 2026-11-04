# Master product folders

Folders beginning with `_` are examples/templates and are ignored by the importer. Copy `_template` to a new folder named with the product slug, add `product.json` and local photographs, then run `python scripts/sync_products.py`.

Each configured `images[].file` must be a file inside that product folder. The importer copies it to `public/images/products/<slug>/` while retaining the filename.

Use the canonical `category_id`, `subtype_id`, `audiences`, and `tags` fields shown in `_template/product.json`. The exact allowed hierarchy lives in `config/taxonomy.json`; see `CATALOG.md` for clothing rules, tag-only collections, multi-audience products, and publishing instructions.
