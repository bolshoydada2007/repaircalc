"""Загрузка YML-фида Максидома в базу RepairCalc (шаг 12).

- Отбирает только категории из CATEGORY_MAP (~1820 офферов).
- products: source='maxidom', updated_at = дата фида, price -> result_price,
  package_area из названия (м2 упаковки), price_per_m2 = price / package_area.
- Подкатегория фида и класс ламината сохраняются в raw_json для шага 13.
- Идемпотентно: перед вставкой удаляет прежние записи source='maxidom'
  и заглушки source='stub' в наших категориях.
"""

import json
import re
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "repaircalc.db"
XML_PATH = BASE_DIR / "maxidom_yml.xml"

# id категории фида -> наша категория (100-103) и подкатегория для подбора
CATEGORY_MAP = {
    "31151": (100, "все"),
    "28579": (101, "все"),
    "27848": (101, "под покраску"),
    "25340": (102, "ванная"),
    "25343": (102, "кухня"),
    "25345": (102, "напольная"),
    "29227": (103, "31 класс"),
    "29228": (103, "32 класс"),
    "29229": (103, "33 класс"),
    "29230": (103, "34 класс"),
}

M2_RE = re.compile(r"(\d+[.,]\d+)\s*м2", re.IGNORECASE)


def extract_area_m2(name: str):
    """Площадь упаковки из названия: '... 2,221м2' -> 2.221. Иначе None."""
    m = M2_RE.search(name)
    if not m:
        return None
    return float(m.group(1).replace(",", "."))


def parse_feed(xml_path: Path):
    """Парсит YML, возвращает (дата фида, список офферов наших категорий)."""
    feed_date = None
    offers = []
    for event, elem in ET.iterparse(xml_path, events=("start", "end")):
        tag = elem.tag.split("}")[-1]
        if event == "start" and tag == "yml_catalog":
            feed_date = elem.get("date")
            continue
        if event != "end" or tag != "offer":
            continue
        children = {}
        params = {}
        for child in elem:
            ctag = child.tag.split("}")[-1]
            if ctag == "param":
                params[child.get("name")] = (child.text or "").strip()
            else:
                children[ctag] = (child.text or "").strip()
        cat_id = children.get("categoryId", "")
        if cat_id not in CATEGORY_MAP:
            elem.clear()
            continue
        our_cat, subcat = CATEGORY_MAP[cat_id]
        name = children.get("name", "")
        price_raw = children.get("price", "")
        try:
            price = float(price_raw)
        except ValueError:
            price = None
        area = extract_area_m2(name)
        offers.append({
            "sku": f"maxidom_{elem.get('id')}",
            "name": name,
            "category_id": our_cat,
            "feed_category_id": cat_id,
            "subcat": subcat,
            "description": children.get("description", ""),
            "price": price,
            "area": area,
            "price_per_m2": round(price / area, 2) if price and area else None,
            "in_stock": 1 if elem.get("available", "true") == "true" else 0,
            "url": children.get("picture", "") or children.get("url", ""),
            "raw": {"params": params, "feed": children},
        })
        elem.clear()
    return feed_date, offers


def import_into_db(feed_date: str, offers: list, db_path: Path = DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE source='maxidom'")
    cur.execute("DELETE FROM products WHERE source='stub'")
    rows = []
    for o in offers:
        raw = dict(o["raw"])
        raw["subcat"] = o["subcat"]
        raw["feed_category_id"] = o["feed_category_id"]
        rows.append((
            o["sku"],                      # sku
            o["name"],                     # name
            o["category_id"],              # category_id
            o["description"],              # description
            "",                            # marketing_description
            None,                          # unit (уточним на шаге 13)
            None,                          # quantity_in_package
            o["area"],                     # package_area (м2 упаковки)
            o["price"],                    # result_price (цена за упаковку)
            o["price_per_m2"],             # price_per_m2
            o["in_stock"],                 # in_stock
            None,                          # rating
            None,                          # recsys_rating
            json.dumps(raw, ensure_ascii=False),  # raw_json
            "maxidom",                     # source
            o["url"],                      # url (картинка товара)
            feed_date,                     # updated_at
        ))
    cur.executemany(
        "INSERT INTO products (sku, name, category_id, description, "
        "marketing_description, unit, quantity_in_package, package_area, "
        "result_price, price_per_m2, in_stock, rating, recsys_rating, "
        "raw_json, source, url, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()
    return len(rows)


def main():
    if not XML_PATH.exists():
        raise SystemExit(
            f"Файл {XML_PATH} не найден. Сначала скачай фид: "
            "curl.exe -L -o maxidom_yml.xml https://fidsout.maxidom.ru/fids/export_yandex_spb.xml"
        )
    feed_date, offers = parse_feed(XML_PATH)
    n = import_into_db(feed_date, offers)
    print(f"Дата фида: {feed_date}")
    print(f"Загружено товаров: {n}")
    for cat in (100, 101, 102, 103):
        conn = sqlite3.connect(DB_PATH)
        cnt = conn.execute(
            "SELECT COUNT(*) FROM products WHERE category_id=? AND source='maxidom'",
            (cat,),
        ).fetchone()[0]
        conn.close()
        print(f"  категория {cat}: {cnt} товаров")


if __name__ == "__main__":
    main()
