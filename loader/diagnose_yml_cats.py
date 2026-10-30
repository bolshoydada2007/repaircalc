"""Поиск наших категорий в YML-фиде Максидома (v2).

Исправление v1: categoryId берём из ДОЧЕРНЕГО тега <offer>, а не из атрибутов.
Расширен поиск краски: 'эмаль', 'лакокрасочн', 'интерьер' (+ производные).

Вывод: найденные категории с веткой, числом офферов и 5 примерами товаров.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

XML_PATH = Path(__file__).resolve().parents[1] / "maxidom_yml.xml"

KEYWORDS = {
    "обои": "Обои",
    "краска": "Краска",
    "эмаль": "Краска",
    "лакокрасочн": "Краска",
    "плитка": "Плитка",
    "ламинат": "Ламинат",
}

cat_name, cat_parent = {}, {}
matched: dict[str, set[str]] = {kw: set() for kw in KEYWORDS}
offer_count: dict[str, int] = {}
offer_samples: dict[str, list[str]] = {}

for event, elem in ET.iterparse(XML_PATH, events=("end",)):
    tag = elem.tag.split("}")[-1]
    if tag == "category":
        name = (elem.text or "").strip()
        cid = elem.get("id")
        cat_name[cid] = name
        cat_parent[cid] = elem.get("parentId")
        low = name.lower()
        for kw in KEYWORDS:
            if kw in low:
                matched[kw].add(cid)
        elem.clear()
    elif tag == "offer":
        cid = nm = price = None
        for child in elem:
            ctag = child.tag.split("}")[-1]
            text = (child.text or "").strip()
            if ctag == "categoryId":
                cid = text
            elif ctag == "name":
                nm = text
            elif ctag == "price":
                price = text
        if cid is not None and cid in cat_name:
            offer_count[cid] = offer_count.get(cid, 0) + 1
            bucket = offer_samples.setdefault(cid, [])
            if len(bucket) < 5:
                bucket.append(f"{nm} | {price} руб.")
        elem.clear()

for kw, label in KEYWORDS.items():
    print(f"\n=== '{kw}' -> целевая категория: {label} ===")
    for cid in sorted(matched[kw], key=lambda x: int(x) if x.isdigit() else 0):
        parent = cat_parent.get(cid)
        chain = []
        cur = parent
        while cur is not None and cur in cat_name:
            chain.append(cat_name[cur])
            cur = cat_parent.get(cur)
        print(f"  id={cid} | '{cat_name[cid]}' | ветка: {' -> '.join(reversed(chain))}")
        print(f"    офферов: {offer_count.get(cid, 0)}")
        for s in offer_samples.get(cid, []):
            print(f"      - {s}")
