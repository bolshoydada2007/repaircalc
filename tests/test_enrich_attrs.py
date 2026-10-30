"""Тесты шага 13: парсеры признаков (обои, плитка, ламинат, краска)."""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "loader"))

from enrich_attrs import (enrich_paint, enrich_tile, enrich_wallpaper,
                          parse_num, parse_paint_consumption_lm2,
                          parse_pack_area_tile)


def test_parse_num():
    assert parse_num("10.05") == 10.05
    assert parse_num("1,06") == 1.06
    assert parse_num("abc") is None


def test_parse_pack_area_tile():
    assert parse_pack_area_tile("1,79 м2 (9 шт.)") == (1.79, 9)
    assert parse_pack_area_tile("1.2") == (None, None)  # без 'м2' не берём
    assert parse_pack_area_tile("") == (None, None)



def test_paint_consumption():
    assert parse_paint_consumption_lm2("0,12") == 0.12
    # г/м2 -> л/м2 при плотности 1.2: 150/1200 = 0.125
    assert abs(parse_paint_consumption_lm2("150") - 0.125) < 0.001
    assert abs(parse_paint_consumption_lm2("100-166") - 0.1108) < 0.01
    assert abs(parse_paint_consumption_lm2("0,08 - 0,12") - 0.10) < 0.001


def test_wallpaper():
    res = enrich_wallpaper({"Длина": "10.05", "Ширина": "1,06",
                            "Влагостойкость обоев": "моющиеся"}, 589.5, {})
    assert res["package_area"] == 10.653
    assert res["price_per_m2"] == round(589.5 / 10.653, 2)
    assert res["derived"]["moisture_level"] == "mid"


def test_tile():
    res = enrich_tile({"В упаковке": "1,44 м2 (8 шт)"}, 1153.2, {})
    assert res["package_area"] == 1.44
    assert res["price_per_m2"] == round(1153.2 / 1.44, 2)
    assert res["derived"]["moisture"] == "yes"


def test_paint():
    res = enrich_paint({"Литраж банки": "9", "Расход материала": "0,12",
                        "Влагостойкость": "да",
                        "Тип помещения": "с повышенной влажностью",
                        "Назначение": "для стен и потолков"}, 2605.5, {})
    assert res["derived"]["coverage_m2"] == 75.0
    assert res["derived"]["moisture"] == "yes"
    assert res["derived"]["room"] == "any"
    assert res["derived"]["suitable"] == 1
    assert res["price_per_m2"] == round(2605.5 / 75.0, 2)
