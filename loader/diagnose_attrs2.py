"""Диагностика шага 13 (часть 2): значения параметров, пропущенных в ч.1.

Обои: 'Влагостойкость обоев', 'Вид обоев', форматы Длина/Ширина.
Плитка: 'В упаковке', 'Размер', 'Тип поверхности', 'Износостойкость'.
Ламинат: 'Износостойкость', 'Площадь покрытия упаковкой' (сверка с колонкой).
Краска: 'Расход материала', 'Литраж банки', 'Тип поверхности'.
"""

import json
import sqlite3
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "repaircalc.db"

WATCH = {
    101: ["Влагостойкость обоев", "Вид обоев", "Длина", "Ширина", "Тип рисунка"],
    102: ["В упаковке", "Размер", "Тип поверхности", "Износостойкость", "Морозостойкость"],
    103: ["Износостойкость", "Площадь покрытия упаковкой"],
    100: ["Расход материала", "Литраж банки", "Тип поверхности", "Объем"],
}

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

for cat_id, keys in WATCH.items():
    rows = cur.execute(
        "SELECT name, package_area, raw_json FROM products "
        "WHERE source='maxidom' AND category_id=?",
        (cat_id,),
    ).fetchall()
    print(f"\n{'='*60}\nКатегория {cat_id}: товаров {len(rows)}")
    for k in keys:
        vals: Counter = Counter()
        for name, pkg_area, raw_json in rows:
            params = json.loads(raw_json or "{}").get("params", {})
            v = params.get(k)
            if v:
                vals[v] += 1
        print(f"  [{k}] уникальных значений: {len(vals)}")
        for v, c in vals.most_common(12):
            print(f"    '{v}': {c}")

# сверка: у ламината колонка package_area vs параметр 'Площадь покрытия упаковкой'
print(f"\n{'='*60}\nСверка ламината: package_area (колонка) vs параметр")
mismatch = 0
for name, pkg_area, raw_json in cur.execute(
    "SELECT name, package_area, raw_json FROM products "
    "WHERE source='maxidom' AND category_id=103"
):
    params = json.loads(raw_json or "{}").get("params", {})
    p = params.get("Площадь покрытия упаковкой", "").replace(",", ".")
    try:
        pv = float(p)
    except ValueError:
        pv = None
    if pkg_area is None or (pv is not None and abs(pv - pkg_area) > 0.01):
        mismatch += 1
        if mismatch <= 5:
            print(f"  РАСХОЖДЕНИЕ: {name} | колонка={pkg_area} | параметр={pv}")
print(f"Итого расхождений: {mismatch} из 155")

conn.close()
