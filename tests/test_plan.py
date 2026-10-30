import math

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _plan(renovation="capital", budget="standard", rooms=None):
    rooms = rooms or [
        {"name": "Комната", "type": "dry", "area_m2": 16},
        {"name": "Ванная", "type": "bathroom", "area_m2": 4},
    ]
    r = client.post("/api/v1/plan", json={
        "rooms": rooms, "renovation": renovation, "budget": budget,
    })
    assert r.status_code == 200, r.text
    return r.json()


def test_cosmetic_has_no_floor_or_tile_works():
    body = _plan(renovation="cosmetic")
    for room in body["rooms"]:
        types = [w["type"] for w in room["works"]]
        assert "tile" not in types
        assert "laminate" not in types


def test_capital_bathroom_has_tile_and_paint():
    body = _plan(renovation="capital")
    bath = next(r for r in body["rooms"] if r["type"] == "bathroom")
    types = [w["type"] for w in bath["works"]]
    assert "tile" in types
    assert "paint" in types


def test_grand_total_is_sum_of_room_totals():
    body = _plan(renovation="capital", budget="budget")
    total = round(sum(r["room_total"] for r in body["rooms"]), 2)
    assert math.isclose(body["grand_total"], total, abs_tol=0.01)


def test_every_work_cheapest_first_with_reasons():
    body = _plan(renovation="capital")
    for room in body["rooms"]:
        for w in room["works"]:
            prices = [o["total_price"] for o in w["options"]]
            assert prices == sorted(prices)
            assert w["options"][0]["reasons"]


def test_room_type_any_still_gets_plan():
    body = _plan(rooms=[{"name": "Зал", "type": "any", "area_m2": 20}],
                 renovation="cosmetic")
    assert body["rooms"][0]["works"]


def test_empty_options_do_not_break_plan():
    # Премиум-плитка в ванной может быть пустой на наших данных -
    # план всё равно должен вернуться с 200 и посчитать остальное.
    body = _plan(renovation="capital", budget="premium")
    assert body["grand_total"] >= 0
    assert body["rooms"]
