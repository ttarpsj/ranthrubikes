from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


class FeedParseError(ValueError):
    pass


def _text(value: Any) -> str | None:
    value = str(value).strip() if value is not None else ""
    return value or None


def _xml_product(element: ET.Element) -> dict[str, Any]:
    record = {child.tag.rsplit("}", 1)[-1]: _text(child.text) for child in element if len(child) == 0}
    record["variants"] = [
        {child.tag.rsplit("}", 1)[-1]: _text(child.text) for child in variant if len(child) == 0}
        for variant in element.findall("./variant")
    ]
    record["images"] = [
        _text(image.get("url") or image.text) for image in element.findall("./image") if _text(image.get("url") or image.text)
    ]
    record["attributes"] = {
        attribute.get("name"): _text(attribute.text)
        for attribute in element.findall("./attribute") if attribute.get("name") and _text(attribute.text)
    }
    return record


def parse_feed(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [{key: value for key, value in row.items() if key} for row in csv.DictReader(handle)]
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload.get("products", payload.get("items", [])) if isinstance(payload, dict) else payload
        if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
            raise FeedParseError("JSON feeds must contain a product list or a products/items array")
        return records
    if suffix == ".xml":
        root = ET.parse(path).getroot()
        products = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1].lower() in {"product", "item"}]
        if not products:
            raise FeedParseError("XML feed contains no product or item elements")
        return [_xml_product(product) for product in products]
    raise FeedParseError("Supported feed formats are CSV, JSON, and XML")
