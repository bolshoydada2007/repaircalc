"""Диагностика YML-фида Максидома: категории, сэмплы товаров, параметры.

Парсит потоково (iterparse), чтобы не держать весь XML в памяти.
Вывод: дата фида, число категорий и офферов, примеры категорий,
2 сэмпла оффера целиком и топ-40 названий характеристик <param>.
"""

import itertools
import xml.etree.ElementTree as ET
from pathlib import Path

XML_PATH = Path(__file__).resolve().parents[1] / "maxidom_yml.xml"

root_date = None
cat_by_id, parent_of = {}, {}
param_counter: dict[str, int] = {}
sample_offers: list[dict] = []
n_offers = n_unavailable = 0

for event, elem in ET.iterparse(XML_PATH, events=("start", "end")):
    tag = elem.tag.split("}")[-1]
    if event == "start" and tag == "yml_catalog":
        root_date = elem.get("date")
    if event != "end":
        continue
    if tag == "category":
        cat_by_id[elem.get("id")] = (elem.text or "").strip()
        parent_of[elem.get("id")] = elem.get("parentId")
    elif tag == "offer":
        n_offers += 1
        if elem.get("available", "") in ("false", "0"):
            n_unavailable += 1
        if len(sample_offers) < 2:
            offer = {"attrs": dict(elem.attrib), "children": {}, "params": {}}
            for child in elem:
                ctag = child.tag.split("}")[-1]
                text = (child.text or "").strip()[:120]
                if ctag == "param":
                    offer["params"][child.get("name")] = text
                else:
                    offer["children"][ctag] = text
            sample_offers.append(offer)
        for child in elem.iter():
            ctag = child.tag.split("}")[-1]
            if ctag == "param" and child.get("name"):
                param_counter[child.get("name")] = (
                    param_counter.get(child.get("name"), 0) + 1
                )
        elem.clear()

print("Дата фида:", root_date)
print("Категорий:", len(cat_by_id))
print("Офферов:", n_offers, "| нет в наличии:", n_unavailable)

print("\nПримеры категорий (первые 20):")
for cid, name in itertools.islice(cat_by_id.items(), 20):
    print("  ", cid, "| parent:", parent_of[cid], "|", name)

print("\nСэмплы офферов:")
for o in sample_offers:
    print(" attrs:", o["attrs"])
    for k, v in o["children"].items():
        print("   ", k, "=", v)
    for k, v in o["params"].items():
        print("   param:", k, "=", v)

print("\nТоп-40 параметров (имя: у скольких офферов встречается):")
for name, cnt in sorted(param_counter.items(), key=lambda kv: -kv[1])[:40]:
    print(f"  {name}: {cnt}")
