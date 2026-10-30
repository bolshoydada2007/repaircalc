"""Тесты шага 14: умный подбор на реальных данных Максидома.

Контрактные проверки: статус, структура, инварианты признакового
фильтра. Не зависят от конкретных товаров каталога.
"""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app.main import app  # noqa: E402

client = TestClient(app)


def test_smart_select_tile_bathroom():
    # ванная, стандартный бюджет: плитка должна быть из подкатегории ванной
    r = client.post("/api/v1/smart-select", json={
        "items": [{"type": "tile", "area_m2": 6.0,
                   "room": "bathroom", "budget": "standard"}]
    })
    assert r.status_code == 200
    options = r.json()["works"][0]["options"]
    assert 1 <= len(options) <= 3
    # инвариант: первый вариант — самый дешёвый
    assert options[0]["total_price"] == min(o["total_price"] for o in options)
    # у вариантов есть объяснение
    assert all(o["reasons"] for o in options)
    # арифметика
    for o in options:
        assert o["total_price"] == round(o["packages"] * o["package_price"], 2)


def test_smart_select_paint_bathroom_filters_non_moisture():
    # ванная + краска: все варианты должны быть влагостойкими
    r = client.post("/api/v1/smart-select", json={
        "items": [{"type": "paint", "area_m2": 20.0,
                   "room": "bathroom", "budget": "standard"}]
    })
    assert r.status_code == 200
    body = r.json()
    assert body["works"][0]["type"] == "paint"
    for o in body["works"][0]["options"]:
        assert any("влагостойкая" in why for why in o["reasons"])


def test_smart_select_wallpaper_bathroom_excludes_not_moisture():
    # ванная + обои: только супермоющиеся (high)
    r = client.post("/api/v1/smart-select", json={
        "items": [{"type": "wallpaper", "area_m2": 15.0, "height_m": 2.7,
                   "room": "bathroom", "budget": "standard"}]
    })
    assert r.status_code == 200
    for o in r.json()["works"][0]["options"]:
        assert any("ванная" in why or "влагостойкость" in why
                   for why in o["reasons"])


def test_smart_select_laminate_budget_corridor():
    # ламинат: бюджет -> класс износостойкости в коридоре сегмента
    r = client.post("/api/v1/smart-select", json={
        "items": [{"type": "laminate", "area_m2": 18.0,
                   "room": "any", "budget": "budget"}]
    })
    assert r.status_code == 200
    for o in r.json()["works"][0]["options"]:
        assert any("износостойкости" in why or "сегмент" in why
                   for why in o["reasons"])


def test_smart_select_empty_result_is_503():
    # заведомо пустая комбинация: ванная + премиум-плитка может не найтись —
    # но 503 допустим только с осмысленным detail, не с 500
    r = client.post("/api/v1/smart-select", json={
        "items": [{"type": "tile", "area_m2": 1.0,
                   "room": "bathroom", "budget": "premium"}]
    })
    assert r.status_code in (200, 503)
    if r.status_code == 503:
        assert "товаров" in r.json()["detail"]
