"""Диагностика шага 13: какие <param> есть у товаров Максидома в базе.

Считает по каждой нашей категории:
- покрытие данными: сколько товаров с ценой, с package_area, с price_per_m2;
- топ-20 имён параметров;
- топ-15 значений ключевых параметров (Назначение, Материал, Помещение,
  Тип, Влагостойкость и похожие) — чтобы выбрать признаки для подбора.
"""

import json
import sqlite3
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "repaircalc.db"

CAT_NAMES = {
    100: "Краска",
    101: "Обои",
    102: "Плитка",
    103: "Ламинат",
}

# имена параметров, значения которых интересно посмотреть целиком
KEY_PARAMS = ["Назначение", "Помещение", "Тип", "Материал", "Область применения",
              "Влагостойкость", "Класс износостойкости", "Вид материала",
              "Тип помещения", "Основа"]

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

for cat_id, cat_label in CAT_NAMES.items():
    rows = cur.execute(
        "SELECT name, package_area, price_per_m2, result_price, raw_json "
        "FROM products WHERE source='maxidom' AND category_id=?",
        (cat_id,),
    ).fetchall()
    print(f"\n{'='*60}\nКатегория {cat_id} ({cat_label}): товаров {len(rows)}")

    with_price = sum(1 for r in rows if r[3])
    with_area = sum(1 for r in rows if r[1])
    with_ppm2 = sum(1 for r in rows if r[2])
    print(f"  с ценой: {with_price}, с package_area: {with_area}, "
          f"с price_per_m2: {with_ppm2}")

    param_counter: Counter = Counter()
    key_values: dict[str, Counter] = {k: Counter() for k in KEY_PARAMS}
    for r in rows:
        raw = json.loads(r[4] or "{}")
        params = raw.get("params", {})
        param_counter.update(params.keys())
        for k in KEY_PARAMS:
            v = params.get(k)
            if v:
                key_values[k][v] += 1

    print("  Топ-20 параметров:")
    for name, cnt in param_counter.most_common(20):
        print(f"    {name}: {cnt}")

    print("  Значения ключевых параметров:")
    for k, cnt in key_values.items():
        if cnt:
            print(f"    [{k}]")
            for v, c in cnt.most_common(15):
                print(f"      '{v}': {c}")

conn.close()
