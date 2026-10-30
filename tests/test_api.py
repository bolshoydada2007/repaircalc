# Тесты эндпоинта сметы. Запуск: .venv\Scripts\python.exe -m pytest tests -v

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_calculate_tile():
    # санузел 6 м2: контракт — 200, варианты рассчитаны, первый — самый дешёвый
    r = client.post("/api/v1/calculate", json={
        "works": [{"type": "tile", "area_m2": 6.0}]
    })
    assert r.status_code == 200
    body = r.json()
    assert body["works"][0]["type"] == "tile"
    options = body["works"][0]["options"]
    assert 1 <= len(options) <= 3
    cheapest = options[0]
    assert cheapest["packages"] >= 1
    assert cheapest["total_price"] > 0
    # арифметическая согласованность: total = packages * package_price
    assert cheapest["total_price"] == round(
        cheapest["packages"] * cheapest["package_price"], 2)
    # первый в списке — гарантированно самый дешёвый
    assert cheapest["total_price"] == min(o["total_price"] for o in options)


def test_calculate_paint():
    # 6 м2, 2 слоя: контракт — 200, есть вариант, банки рассчитаны по литражу
    r = client.post("/api/v1/calculate", json={
        "works": [{"type": "paint", "area_m2": 6.0}]
    })
    assert r.status_code == 200
    cheapest = r.json()["works"][0]["options"][0]
    assert cheapest["packages"] >= 1
    assert cheapest["package_price"] > 0
    assert cheapest["total_price"] == round(
        cheapest["packages"] * cheapest["package_price"], 2)



def test_calculate_wallpaper_requires_height():
    r = client.post("/api/v1/calculate", json={
        "works": [{"type": "wallpaper", "area_m2": 20.0}]
    })
    assert r.status_code == 422


def test_calculate_wallpaper_full():
    r = client.post("/api/v1/calculate", json={
        "works": [{"type": "wallpaper", "area_m2": 20.0, "height_m": 2.7}]
    })
    assert r.status_code == 200
    assert r.json()["works"][0]["options"]


def test_calculate_rejects_bad_type():
    r = client.post("/api/v1/calculate", json={
        "works": [{"type": "кирпич", "area_m2": 6.0}]
    })
    assert r.status_code == 422


def test_calculate_rejects_zero_area():
    r = client.post("/api/v1/calculate", json={
        "works": [{"type": "tile", "area_m2": 0}]
    })
    assert r.status_code == 422


def test_calculate_multi_work_grand_total():
    # две работы сразу: плитка 6 м2 (9450) + ламинат 18 м2
    r = client.post("/api/v1/calculate", json={
        "works": [
            {"type": "tile", "area_m2": 6.0},
            {"type": "laminate", "area_m2": 18.0},
        ]
    })
    assert r.status_code == 200
    body = r.json()
    assert len(body["works"]) == 2
    assert body["grand_total"] > 9450.0
