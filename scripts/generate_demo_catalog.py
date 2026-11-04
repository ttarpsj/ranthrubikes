#!/usr/bin/env python3
"""Create a local, explicitly illustrative catalogue feed for portfolio use.

This does not contact vendors or download assets.  Each entry deliberately has no
image so the storefront uses its existing black placeholder.  The model lists are
curated from manufacturer catalogues; prices, stock, variants and descriptions are
explicitly illustrative until an authorised dealer feed replaces them.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "verified-demo-feeds"

# Manufacturer catalogue/product pages used only as provenance references. They are
# not fetched by this generator and no image or copyrighted copy is republished.
SOURCES = {
    "GOBIK": "https://gobik.com/en/collections/cycling-clothing",
    "MAAP": "https://maap.cc/us/collections/cycling-apparel",
    "Shimano": "https://bike.shimano.com/en-US/product/component.html",
    "KASK": "https://www.kask.com/en/cycling/helmets/",
    "MET": "https://www.met-helmets.com/en/shop/cycling-helmets/",
    "Fizik": "https://www.fizik.com/us_en/cycling-shoes.html",
    "Selle Italia": "https://www.selleitalia.com/saddles/",
    "SRAM": "https://www.sram.com/en/sram/road",
    "Elite": "https://www.elite-it.com/en/products",
    "Garmin": "https://www.garmin.com/en-US/c/sports-fitness/cycling/",
    "Wahoo": "https://www.wahoofitness.com/devices",
    "Muc-Off": "https://muc-off.com/collections/bicycle",
    "ENVE": "https://enve.com/collections/wheels",
    "VISION": "https://www.visiontechusa.com/en/products/wheels",
    "Continental": "https://www.continental-tires.com/products/bicycle/tires/",
    "Pirelli": "https://www.pirelli.com/tyres/en-ww/bike/tyres/catalogue",
    "Oakley": "https://www.oakley.com/en-us/category/sport/cycling",
    "100%": "https://www.ride100percent.com/collections/cycling-eyewear",
    "Specialized": "https://www.specialized.com/us/en/shop/bikes",
    "Colnago": "https://www.colnago.com/collections/bikes",
}

# Exactly fifteen familiar, current/recent manufacturer product identities per brand.
# These are identity-only entries: technical fields are intentionally omitted unless
# an authorised supplier feed can verify them.
MODELS = {
"GOBIK": ["CX Pro 4.0 Jersey", "Stark Jersey", "Carrera 2.0 Bib Shorts", "Absolute 6.0 Bib Shorts", "Phantom Jacket", "Skimo Pro Jacket", "Kaba 2.0 Jacket", "Plus 2.0 Gilet", "Second Skin Baselayer", "Rocket 2.0 Socks", "Ionic Gloves", "Armour 2.0 Winter Tights", "Unisex Hoodie", "Tech T-Shirt", "Overshoes 2.0"],
"MAAP": ["Men's Pro Air Jersey 3.0", "Men's Pro Air Long Sleeve Jersey 3.0", "Men's Training Jersey 2.0", "Men's Training Thermal Long Sleeve Jersey 2.0", "Men's Team Thermal Long Sleeve Jersey", "Men's Pro Emerge Jersey", "Men's Pro Emerge Long Sleeve Jersey", "Men's Pro Aero Jersey", "Men's Apex Aeon Jersey", "Men's Team Bib Evo", "Men's Team Bib Evo Cargo", "Men's Pro Atmos Jacket", "Men's Pro Atmos Vest", "Men's Team Sock", "Men's Eclipse Base Layer"],
"KASK": ["Protone Icon", "Elemento", "Utopia Y", "Wasabi", "Mojito3", "Sintesi", "Caipi", "Rex", "Defender", "Valegro", "Mistral", "Bambino Pro Evo", "Rapido", "Moebius", "Mojito X"],
"MET": ["Trenta 3K Carbon", "Trenta", "Manta MIPS", "Rivale MIPS", "Estro MIPS", "Vinci MIPS", "Miles MIPS", "Allroad MIPS", "Terranova MIPS", "Parachute MCR MIPS", "Roam MIPS", "Echo MIPS", "Codatronca", "Drone Wide Body", "Idolo MIPS"],
"Fizik": ["Vento Infinito Carbon 2", "Vento Ferox Carbon", "Vento Proxy", "Vento Powerstrap Aeroweave", "Tempo Overcurve R4", "Tempo Decos Carbon", "Tempo Decos", "Terra Atlas", "Terra Artica X2", "Terra Ergolace X2", "Vento Argo R1", "Vento Argo R3", "Antares R1", "Aliante R1", "Tempo Argo R5"],
"Selle Italia": ["SLR Boost", "SLR Boost 3D", "SLR Kit Carbonio", "Flite Boost", "Flite Boost 3D", "Novus Boost Evo", "Novus Boost Evo 3D", "Model X Green Superflow", "SP-01 Boost", "Max Flite Gel Superflow", "Watt 3D", "Watt Kit Carbonio Superflow", "Diva Gel Superflow", "Lady Gel Flow", "X-Bow"],
"Shimano": ["Dura-Ace FC-R9200 Crankset", "Dura-Ace RD-R9250 Rear Derailleur", "Dura-Ace FD-R9250 Front Derailleur", "Dura-Ace ST-R9270 Shift Brake Lever", "Ultegra FC-R8100 Crankset", "Ultegra RD-R8150 Rear Derailleur", "Ultegra ST-R8170 Shift Brake Lever", "105 FC-R7100 Crankset", "105 RD-R7150 Rear Derailleur", "105 ST-R7170 Shift Brake Lever", "GRX FC-RX820-1 Crankset", "GRX RD-RX822 Rear Derailleur", "GRX ST-RX820 Shift Brake Lever", "Dura-Ace WH-R9270-C50 Wheelset", "Ultegra WH-R8170-C50 Wheelset"],
"SRAM": ["RED AXS Power Meter Crankset", "RED AXS Rear Derailleur", "RED AXS Shift Brake Lever", "Force AXS Power Meter Crankset", "Force AXS Rear Derailleur", "Force AXS Shift Brake Lever", "Rival AXS Power Meter Crankset", "Rival AXS Rear Derailleur", "Apex AXS Rear Derailleur", "RED XPLR AXS Rear Derailleur", "Force XPLR AXS Rear Derailleur", "Rival XPLR AXS Rear Derailleur", "X0 Eagle Transmission Derailleur", "XX Eagle Transmission Derailleur", "PowerLink Zero Dual-Sided Power Meter"],
"Elite": ["Fly Tex Bottle", "Fly Team Bottle", "Jet Green Bottle", "Nanofly Bottle", "Mia Bottle", "Vico Carbon Bottle Cage", "Custom Race Plus Bottle Cage", "Tuo Trainer", "Suito-T Trainer", "Direto XR-T Trainer", "Justo 2 Trainer", "Nero Interactive Roller", "Rizer Gradient Simulator", "Sterzo Smart Steering Block", "Aria Fan"],
"Garmin": ["Edge 1050", "Edge 1040 Solar", "Edge 1040", "Edge 840 Solar", "Edge 840", "Edge 540 Solar", "Edge 540", "Edge Explore 2", "Edge 130 Plus", "Rally RK200", "Rally RS200", "Rally XC200", "Varia RTL715", "Varia RVR315", "Tacx NEO 2T Smart Trainer"],
"Wahoo": ["ELEMNT ACE", "ELEMNT ROAM v2", "ELEMNT BOLT v2", "KICKR MOVE", "KICKR CORE", "KICKR Smart Trainer", "KICKR BIKE SHIFT", "KICKR BIKE", "KICKR HEADWIND", "TRACKR RADAR", "TRACKR HEART RATE", "SPEEDPLAY COMP Pedals", "SPEEDPLAY ZERO Pedals", "SPEEDPLAY NANO Pedals", "POWRLINK ZERO Dual-Sided Power Pedals"],
"Muc-Off": ["Nano Tech Bike Cleaner", "Nano Tech Bike Cleaner Concentrate", "Drivetrain Cleaner", "Bio Drivetrain Cleaner", "Disc Brake Cleaner", "Wet Weather Lube", "Dry Weather Lube", "All Weather Lube", "C3 Ceramic Wet Lube", "C3 Ceramic Dry Lube", "MO-94", "HCB-1", "No Puncture Hassle Tubeless Sealant", "Stealth Tubeless Puncture Plug", "Ultimate Bicycle Cleaning Kit"],
"ENVE": ["SES 2.3 Wheelset", "SES 3.4 Wheelset", "SES 4.5 Wheelset", "SES 6.7 Wheelset", "SES 4.5 Pro Wheelset", "G23 Wheelset", "G27 Wheelset", "G30 Wheelset", "AG25 Wheelset", "M5 Wheelset", "M6 Wheelset", "Foundation 45 Wheelset", "Foundation 65 Wheelset", "Road Stem", "SES Aero Road Handlebar"],
"VISION": ["Metron 45 SL Wheelset", "Metron 60 SL Wheelset", "Metron 60 SL Disc Wheelset", "Metron 40 SL Wheelset", "SC 40 Wheelset", "SC 55 Wheelset", "Trimax 30 KB Wheelset", "Trimax 35 KB Wheelset", "Trimax 45 KB Wheelset", "Trimax 30 Disc Wheelset", "Team 35 Comp SL Wheelset", "Metron 5D ACR Handlebar", "Metron 5D EVO Handlebar", "Trimax Aero Handlebar", "Metron TFA Aerobar"],
"Continental": ["Grand Prix 5000 S TR", "Grand Prix 5000 AS TR", "Grand Prix 5000 TT TR", "Grand Prix 5000", "Grand Prix 5000 AllSeason", "Grand Prix 5000 Clincher", "Terra Speed", "Terra Trail", "Terra Hardpack", "Terra Adventure", "Race King", "Cross King", "Kryptotal Front", "Kryptotal Rear", "Contact Urban"],
"Pirelli": ["P ZERO Race TLR RS", "P ZERO Race TLR", "P ZERO Race", "P ZERO Road", "P7 Sport", "Cinturato Velo TLR", "Cinturato Gravel H", "Cinturato Gravel M", "Cinturato Gravel RC X", "Scorpion XC RC", "Scorpion XC M", "Scorpion XC H", "Scorpion Trail M", "Scorpion Trail R", "Scorpion Enduro M"],
"Oakley": ["Sutro", "Sutro Lite", "Sutro Lite Sweep", "Encoder", "Encoder Strike", "Jawbreaker", "Radar EV Path", "Radar EV XS Path", "Kato", "Kato X", "EVZero Blades", "Corridor", "BXTR", "Hydra", "Sphaera"],
"100%": ["Speedcraft", "Speedcraft SL", "S3", "S2", "Glendale", "Westcraft", "Hypercraft", "Hypercraft SQ", "Slendale", "Legere Square", "Norvik", "Aerocraft", "Racetrap", "Rideley", "Campo"],
"Specialized": ["S-Works Prevail 3", "Propero 4", "Align II", "S-Works Torch", "Torch 3.0", "Power Expert", "Romin Evo Pro", "S-Works Tarmac SL8", "Tarmac SL8 Expert", "Tarmac SL8 Frameset", "Roubaix SL8", "Aethos", "Allez Sprint", "Crux", "Diverge STR"],
"Colnago": ["V4Rs", "V4", "C68 Road", "C68 Allroad", "C68 Gravel", "Y1Rs", "G4-X", "C68 Ti", "Master", "Arabesque", "Steelnovo", "C64", "V3Rs", "Concept", "K.One"],
}

def classified(brand: str, model: str) -> tuple[str, str, list[str], str, str]:
    """Return category, subtype, audiences, representative size and colour."""
    if brand in {"GOBIK", "MAAP"}:
        text = model.lower()
        subtype = "short-sleeve-jerseys"
        if "long sleeve" in text: subtype = "long-sleeve-jerseys"
        elif "bib" in text: subtype = "bibshorts"
        elif "gilet" in text or "vest" in text: subtype = "gilets"
        elif "base" in text: subtype = "baselayers"
        elif "jacket" in text: subtype = "jackets"
        elif "tight" in text: subtype = "winter-tights"
        elif "sock" in text: subtype = "socks"
        elif "glove" in text: subtype = "gloves"
        elif "overshoe" in text: subtype = "overshoes"
        elif "t-shirt" in text: subtype = "t-shirts"
        elif "hoodie" in text: subtype = "sweaters"
        # Garment branches are intentionally assigned to the men's taxonomy branch
        # unless the source name specifies otherwise; accessories/lifestyle are
        # canonical unisex branches.  This is a demo classification, not a claim
        # about manufacturer sizing.
        audience = ["unisex"] if subtype in {"socks", "gloves", "overshoes", "t-shirts", "sweaters", "casual-wear"} else ["men"]
        return "clothing", subtype, audience, "M", "Demo Black"
    if brand in {"KASK", "MET"} or (brand == "Specialized" and model in {"S-Works Prevail 3", "Propero 4", "Align II"}): return "equipment", "helmets", ["unisex"], "M", "Matte Black"
    if brand == "Specialized" and model in {"S-Works Torch", "Torch 3.0"}: return "equipment", "cycling-shoes", ["unisex"], "EU 42", "Black"
    if brand == "Specialized" and model in {"Power Expert", "Romin Evo Pro"}: return "equipment", "saddles", ["unisex"], "One size", "Black"
    if brand in {"Fizik", "Selle Italia"}: return "equipment", ("saddles" if brand == "Selle Italia" or any(x in model for x in ("Argo", "Antares", "Aliante")) else "cycling-shoes"), ["unisex"], ("One size" if brand == "Selle Italia" else "EU 42"), "Black"
    if brand in {"Continental", "Pirelli"}: return "components", "tires", ["unisex"], "700x28", "Black"
    if brand in {"Garmin", "Wahoo"}: return "equipment", "electronics", ["unisex"], "One size", "Black"
    if brand == "Elite": return "equipment", "bottles-training", ["unisex"], "One size", "Black"
    if brand == "Muc-Off": return "equipment", "bike-care", ["unisex"], "One size", "N/A"
    if brand in {"Oakley", "100%"}: return "equipment", "eyewear", ["unisex"], "One size", "Black"
    if brand in {"Specialized", "Colnago"}: return "bikes-frames", "bikes-framesets", ["unisex"], "54", "Demo Black"
    return "components", "drivetrain-wheels", ["unisex"], "One size", "Black"


def illustrative_price_cents(category_id: str, subtype_id: str) -> int:
    """Non-retail price bands that make the portfolio's price filter testable."""
    if category_id == "bikes-frames": return 250000
    if category_id == "clothing": return 12000
    if subtype_id == "helmets": return 20000
    if subtype_id in {"cycling-shoes", "saddles", "eyewear"}: return 15000
    if subtype_id == "tires": return 6000
    if subtype_id == "electronics": return 30000
    if subtype_id == "bottles-training": return 8000
    if subtype_id == "bike-care": return 2500
    return 25000

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for brand, models in MODELS.items():
        records = []
        for number, model in enumerate(models, 1):
            category_id, subtype_id, audiences, size, color = classified(brand, model)
            demo_price_cents = illustrative_price_cents(category_id, subtype_id)
            records.append({
                "name": f"DEMO · {model}",
                "sku": f"DEMO-{brand.upper().replace(' ', '')}-{number:02d}",
                "price_cents": demo_price_cents,
                "stock_quantity": 1,
                "category_id": category_id,
                "subtype_id": subtype_id,
                "subtype_label": subtype_id.replace("-", " ").title(),
                "audiences": audiences,
                "description": f"Illustrative portfolio listing for the verified {brand} product identity ‘{model}’. This is not a live retail offer; price, stock, size and colour are demonstration values pending an authorised dealer feed.",
                "variants": [{"sku": f"DEMO-{brand.upper().replace(' ', '')}-{number:02d}", "size": size, "color": color, "stock_quantity": 1}],
                "attributes": {
                    "manufacturer_source_url": SOURCES[brand],
                    "provenance_status": "Manufacturer catalogue reference; identity verified for demonstration",
                    "technical_specifications": "Not published in demo until verified from an authorised feed",
                    "price_status": f"Illustrative demonstration price (${demo_price_cents / 100:.2f}) — not a retail price",
                    "variant_status": "Illustrative demonstration configuration",
                    "image_status": "No licensed image supplied; use storefront black placeholder",
                },
                "images": [],
                "image_rights": "unknown",
            })
        (OUT / f"{brand.lower().replace(' ', '-')}.json").write_text(json.dumps({"products": records}, indent=2) + "\n", encoding="utf-8")
        total += len(records)
    print(f"Wrote {total} explicitly illustrative records across {len(MODELS)} brands to {OUT}")

if __name__ == "__main__":
    main()
