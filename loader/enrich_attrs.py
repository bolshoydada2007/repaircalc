"""Шаг 13: извлечение признаков умного подбора из raw_json (Максидом).

Для каждой категории вычисляет производные признаки и обновляет базу:
- products.package_area (м2 упаковки), quantity_in_package
  (литры у краски, шт в упаковке у плитки/ламината),
  price_per_m2 (если вычислился);
- raw_json['derived'] — структурированные признаки:
  moisture ('yes'/'no'), moisture_level ('high'/'mid'/'low'),
  room, wear_class ('31'...'34'), coverage_m2, price_tier.

Идемпотентно: можно запускать повторно, признаки пересчитываются заново.

Допущение: плотность краски 1.2 кг/л для перевода г/м2 в л/м2.
"""

import json
import re
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "repaircalc.db"

PAINT_DENSITY_KG_L = 1.2


def parse_num(s):
    """'10.05', '1,06' -> float; None если не число."""
    if s is None:
        return None
    s = s.strip().replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_range_avg(s):
    """'100-166', '0,08 - 0,12' -> среднее; одно число -> оно же."""
    if not s:
        return None
    parts = re.split(r"[-–]", s)
    nums = [parse_num(p) for p in parts]
    nums = [n for n in nums if n is not None]
    return sum(nums) / len(nums) if nums else None


def parse_pack_area_tile(s):
    """'1,79 м2 (9 шт.)' -> (1.79, 9). Без 'м2' или без числа -> None."""
    if not s:
        return None, None
    m = re.search(r"(\d+[.,]\d+)\s*м2", s, re.IGNORECASE)
    area = parse_num(m.group(1)) if m else None
    m_cnt = re.search(r"(\d+)\s*шт", s, re.IGNORECASE)
    count = int(m_cnt.group(1)) if m_cnt else None
    return area, count


def parse_paint_consumption_lm2(s):
    """Расход -> л/м2. Значения >=10 считаем г/м2:
    перевод через плотность (150 г/м2 / 1200 г/л = 0.125 л/м2)."""
    v = parse_range_avg(s)
    if v is None:
        return None
    lm2 = v / (PAINT_DENSITY_KG_L * 1000) if v >= 10 else v
    return round(lm2, 4)


WALLPAPER_MOISTURE = {
    "супермоющиеся": "high",
    "моющиеся": "mid",
    "влагостойкие": "mid",
    "не влагостойкие": "low",
}


def enrich_wallpaper(params, price, raw):
    length = parse_num(params.get("Длина"))
    width = parse_num(params.get("Ширина"))
    area = round(length * width, 3) if length and width else None
    moisture_level = WALLPAPER_MOISTURE.get(
        (params.get("Влагостойкость обоев") or "").strip().lower(), "unknown")
    return {
        "package_area": area,
        "quantity_in_package": 1,  # цена указана за рулон
        "price_per_m2": round(price / area, 2) if price and area else None,
        "derived": {"moisture_level": moisture_level, "room": "any"},
    }


def enrich_tile(params, price, raw):
    area, count = parse_pack_area_tile(params.get("В упаковке"))
    return {
        "package_area": area,
        "quantity_in_package": count,
        "price_per_m2": round(price / area, 2) if price and area else None,
        # подкатегория фида лежит на верхнем уровне raw_json
        "derived": {"moisture": "yes", "room": raw.get("subcat", "any")},
    }


def enrich_laminate(params, price, raw):
    # приоритет: параметр фида, затем прежняя колонка (из названия)
    area = parse_num(params.get("Площадь покрытия упаковкой"))
    count = parse_num(params.get("Количество в упаковке"))
    wear = (params.get("Износостойкость") or "").strip()
    wear = wear if wear in ("31", "32", "33", "34") else None
    moisture = (params.get("Влагостойкость") or "").strip().lower()
    return {
        "package_area": area,
        "quantity_in_package": int(count) if count else None,
        "price_per_m2": round(price / area, 2) if price and area else None,
        "derived": {
            "wear_class": wear,
            "moisture": "yes" if moisture == "да" else
                        "no" if moisture == "нет" else None,
            "room": "any",
        },
    }


def enrich_paint(params, price, raw):
    volume = parse_num(params.get("Литраж банки")) or parse_num(params.get("Объем"))
    consumption = parse_paint_consumption_lm2(params.get("Расход материала"))
    coverage = round(volume / consumption, 2) if volume and consumption else None
    moisture = (params.get("Влагостойкость") or "").strip().lower()
    room_raw = (params.get("Тип помещения") or "").strip().lower()
    if "повышенной" in room_raw or "для всех" in room_raw:
        room = "any"
    elif "умеренной" in room_raw:
        room = "kitchen"
    elif "сухое" in room_raw:
        room = "dry"
    else:
        room = None
    purpose = (params.get("Назначение") or "").strip().lower()
    suitable = ("стен" in purpose or "потолк" in purpose or "универсальн" in purpose)
    return {
        "package_area": None,
        "quantity_in_package": volume,  # литры банки — то, что ждёт calc_router
        "price_per_m2": round(price / coverage, 2) if price and coverage else None,
        "derived": {
            "coverage_m2": coverage,
            "moisture": "yes" if moisture == "да" else
                        "no" if moisture == "нет" else None,
            "room": room,
            "suitable": 1 if suitable else 0,
        },
    }


ENRICHERS = {100: enrich_paint, 101: enrich_wallpaper,
             102: enrich_tile, 103: enrich_laminate}


def run(db_path: Path = DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    n_updated = 0
    stats = {}
    for cat, enrich in ENRICHERS.items():
        rows = cur.execute(
            "SELECT id, result_price, package_area, raw_json "
            "FROM products WHERE source='maxidom' AND category_id=?", (cat,)
        ).fetchall()
        cat_stats = {"total": len(rows), "with_ppm2": 0, "with_qty": 0,
                     "with_area": 0}
        for pid, price, old_area, raw_json in rows:
            raw = json.loads(raw_json)
            params = raw.get("params", {})
            res = enrich(params, price, raw)
            new_area = res["package_area"] if res["package_area"] else old_area
            # derived может не существовать у свежезагруженных товаров
            raw.setdefault("derived", {}).update(res["derived"])
            raw["derived"]["price_per_m2"] = res["price_per_m2"]
            cur.execute(
                "UPDATE products SET package_area=?, quantity_in_package=?, "
                "price_per_m2=?, raw_json=? WHERE id=?",
                (new_area, res["quantity_in_package"], res["price_per_m2"],
                 json.dumps(raw, ensure_ascii=False), pid),
            )
            n_updated += 1
            if res["price_per_m2"]:
                cat_stats["with_ppm2"] += 1
            if res["quantity_in_package"]:
                cat_stats["with_qty"] += 1
            if new_area:
                cat_stats["with_area"] += 1
        stats[cat] = cat_stats

    # ценовые тертили (после вычисления price_per_m2)
    tier_updates = 0
    for cat in ENRICHERS:
        rows = cur.execute(
            "SELECT id, price_per_m2, raw_json FROM products "
            "WHERE source='maxidom' AND category_id=?", (cat,)
        ).fetchall()
        prices = sorted(p for _, p, _ in rows if p is not None)
        if not prices:
            continue
        t1 = prices[len(prices) // 3]
        t2 = prices[2 * len(prices) // 3]
        for pid, p, raw_json in rows:
            raw = json.loads(raw_json)
            tier = None
            if p is not None:
                tier = "budget" if p <= t1 else "standard" if p <= t2 else "premium"
            raw.setdefault("derived", {})["price_tier"] = tier
            cur.execute("UPDATE products SET raw_json=? WHERE id=?",
                        (json.dumps(raw, ensure_ascii=False), pid))
            tier_updates += 1
    conn.commit()
    conn.close()
    return n_updated, stats, tier_updates


def main():
    n, stats, tier_updates = run()
    print(f"Обновлено товаров: {n}")
    for cat, s in sorted(stats.items()):
        print(f"  категория {cat}: {s}")
    print(f"Записей с price_tier: {tier_updates}")


if __name__ == "__main__":
    main()
