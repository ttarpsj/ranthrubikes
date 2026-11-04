#!/usr/bin/env python3
"""Validate the private SQLite catalog and export its safe public representation."""
import argparse, json, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "products.db"
OUT = ROOT / "data" / "products.json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, slug TEXT NOT NULL UNIQUE,
 description TEXT NOT NULL, price_cents INTEGER NOT NULL CHECK(price_cents >= 0),
 category TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 stripe_checkout_url TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 brand TEXT, product_type TEXT, is_new INTEGER NOT NULL DEFAULT 0 CHECK(is_new IN (0,1)),
 is_sale INTEGER NOT NULL DEFAULT 0 CHECK(is_sale IN (0,1)), sale_price_cents INTEGER CHECK(sale_price_cents >= 0),
 is_ran_thru INTEGER NOT NULL DEFAULT 0 CHECK(is_ran_thru IN (0,1)), featured_rank INTEGER,
 category_id TEXT, subtype_id TEXT
);
CREATE TABLE IF NOT EXISTS product_images (
 id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
 url TEXT NOT NULL, alt_text TEXT, display_order INTEGER NOT NULL DEFAULT 0,
 is_primary INTEGER NOT NULL DEFAULT 0 CHECK(is_primary IN (0,1))
);
CREATE TABLE IF NOT EXISTS product_variants (
 id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
 sku TEXT NOT NULL UNIQUE, size TEXT, color TEXT, stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK(stock_quantity >= 0),
 price_cents INTEGER CHECK(price_cents >= 0), active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1))
);
CREATE TABLE IF NOT EXISTS product_audiences (
 product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
 audience TEXT NOT NULL, PRIMARY KEY(product_id,audience)
);
CREATE TABLE IF NOT EXISTS product_tags (
 product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
 tag TEXT NOT NULL, PRIMARY KEY(product_id,tag)
);
"""

def connect():
    if not DB.exists(): raise SystemExit(f"Catalog database not found: {DB}")
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; con.execute("PRAGMA foreign_keys = ON"); return con

def validate(con):
    for table in ("products", "product_images", "product_variants", "product_audiences", "product_tags"):
        if not con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
            raise SystemExit(f"Missing required table: {table}")
    bad = con.execute("SELECT slug FROM products WHERE trim(name)='' OR trim(slug)='' OR price_cents<0").fetchall()
    if bad: raise SystemExit("Invalid product records: " + ", ".join(x[0] for x in bad))
    columns = {row[1] for row in con.execute("PRAGMA table_info(products)")}
    required = {'brand','product_type','is_new','is_sale','sale_price_cents','is_ran_thru','featured_rank','category_id','subtype_id'}
    if missing := required - columns: raise SystemExit("Missing product metadata columns: " + ", ".join(sorted(missing)))
    invalid_sale = con.execute("SELECT slug FROM products WHERE is_sale=1 AND (sale_price_cents IS NULL OR sale_price_cents>=price_cents)").fetchall()
    if invalid_sale: raise SystemExit("Invalid sale pricing: " + ", ".join(x[0] for x in invalid_sale))

def export(con):
    catalog=[]
    for p in con.execute("SELECT id,name,slug,description,price_cents,category,stripe_checkout_url,created_at,brand,product_type,is_new,is_sale,sale_price_cents,is_ran_thru,featured_rank,category_id,subtype_id FROM products WHERE active=1 ORDER BY category,name"):
        images=[dict(x) for x in con.execute("SELECT url,alt_text,display_order,is_primary FROM product_images WHERE product_id=? ORDER BY is_primary DESC,display_order,id",(p['id'],)) if x['url'].strip()]
        variants=[dict(x) for x in con.execute("SELECT sku,size,color,COALESCE(price_cents,?) price_cents,stock_quantity FROM product_variants WHERE product_id=? AND active=1 ORDER BY id",(p['price_cents'],p['id'])) if x['sku'].strip()]
        audiences=[row[0] for row in con.execute("SELECT audience FROM product_audiences WHERE product_id=? ORDER BY audience",(p['id'],))]
        tags=[row[0] for row in con.execute("SELECT tag FROM product_tags WHERE product_id=? ORDER BY tag",(p['id'],))]
        catalog.append({'name':p['name'],'slug':p['slug'],'description':p['description'],'price_cents':p['price_cents'],'sale_price_cents':p['sale_price_cents'] if p['is_sale'] else None,'category':p['category'],'category_id':p['category_id'],'subtype_id':p['subtype_id'],'audiences':audiences,'tags':tags,'brand':p['brand'],'product_type':p['product_type'],'is_new':'new-arrivals' in tags,'is_sale':bool(p['is_sale']),'is_ran_thru':'ran-thru-collection' in tags,'featured_rank':p['featured_rank'],'created_at':p['created_at'],'checkout_url':p['stripe_checkout_url'],'images':images,'variants':variants,'available': any(v['stock_quantity']>0 for v in variants) if variants else False})
    OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps({'products':catalog},indent=2)+"\n",encoding='utf-8')

def seed():
    DB.parent.mkdir(exist_ok=True); con=sqlite3.connect(DB); con.executescript(SCHEMA)
    if con.execute('SELECT COUNT(*) FROM products').fetchone()[0]==0:
        products=[('Ran Thru Merino Sock','ran-thru-merino-sock','Technical merino socks for long days in the saddle.',2800,'Apparel'),('Allroad Bottle','allroad-bottle','Insulated, easy-clean bottle for every ride.',2200,'Accessories'),('Workshop Tee','workshop-tee','Everyday cotton tee cut for the workshop.',4500,'Apparel')]
        for i,p in enumerate(products,1):
            con.execute('INSERT INTO products(name,slug,description,price_cents,category) VALUES(?,?,?,?,?)',p)
            con.execute('INSERT INTO product_images(product_id,url,alt_text,is_primary) VALUES(?,?,?,1)',(i,f'https://images.unsplash.com/photo-{[1576435728678,1558981806,1529422643029][i-1]}-68d0fbf94e91?auto=format&fit=crop&w=1200&q=85',p[0]))
            con.execute('INSERT INTO product_variants(product_id,sku,size,color,stock_quantity) VALUES(?,?,?,?,?)',(i,f'RTB-{i:03d}','One size','Natural',8))
    con.commit(); con.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--init-sample',action='store_true'); parser.add_argument('--validate',action='store_true'); args=parser.parse_args()
    if args.init_sample: seed()
    con=connect(); validate(con)
    if not args.validate: export(con)
