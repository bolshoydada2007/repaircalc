"""Тесты шага 12: парсер YML-фида Максидома на мини-фикстуре."""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "loader"))

from fetch_maxidom import extract_area_m2, parse_feed  # noqa: E402

MINI_YML = """<?xml version="1.0" encoding="utf-8"?>
<yml_catalog date="2026-10-29 06:49">
  <shop>
    <categories>
      <category id="31151">Краски для стен и потолков</category>
      <category id="29228">Ламинат 32 класса</category>
      <category id="99999">Садовая техника</category>
    </categories>
    <offers>
      <offer id="111" available="true">
        <name>краска акриловая PARADE W1 для потолков белая 2,5л</name>
        <price>809.10</price>
        <categoryId>31151</categoryId>
        <picture>https://www.maxidom.ru/img/1.jpg</picture>
        <param name="Артикул">0005843</param>
      </offer>
      <offer id="222" available="true">
        <name>ламинат Expert Choice 32кл/8мм Дуб орегон 1285х192мм 2,221м2</name>
        <price>1360.80</price>
        <categoryId>29228</categoryId>
        <param name="Материал">ЛДСП</param>
      </offer>
      <offer id="333" available="false">
        <name>газонокосилка тестовая</name>
        <price>100.00</price>
        <categoryId>99999</categoryId>
      </offer>
    </offers>
  </shop>
</yml_catalog>
"""


def test_extract_area_m2():
    assert extract_area_m2("ламинат ... 2,221м2") == 2.221
    assert extract_area_m2("краска белая 2,5л") is None


def test_parse_feed(tmp_path):
    f = tmp_path / "mini.xml"
    f.write_text(MINI_YML, encoding="utf-8")
    feed_date, offers = parse_feed(f)
    assert feed_date == "2026-10-29 06:49"
    # чужая категория отфильтрована
    assert len(offers) == 2
    by_sku = {o["sku"]: o for o in offers}
    paint = by_sku["maxidom_111"]
    assert paint["category_id"] == 100
    assert paint["price"] == 809.10
    # у краски нет м2 в названии -> price_per_m2 None
    assert paint["price_per_m2"] is None
    assert paint["raw"]["params"]["Артикул"] == "0005843"
    lam = by_sku["maxidom_222"]
    assert lam["category_id"] == 103
    # 1360.80 / 2.221 = 612.6...
    assert abs(lam["price_per_m2"] - 1360.80 / 2.221) < 0.01
    assert lam["subcat"] == "32 класс"
    assert lam["in_stock"] == 1
