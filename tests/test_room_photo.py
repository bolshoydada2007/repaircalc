import io
import sqlite3

import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.api import photo_router
from app.main import app

client = TestClient(app)

PRODUCTS = [
    (1, 101, "обои зелёные листья пальмы 10,05x1,06м", 2500.0, 4.8),
    (2, 101, "обои синие геометрия 10,05x1,06м", 1800.0, 4.5),
    (3, 101, "обои красные терракота 10,05x1,06м", 2100.0, 4.6),
    (4, 101, "обои бежевые классические 10,05x1,06м", 1900.0, 4.7),
    (5, 102, "плитка зелёная мозаика 30х60", 1200.0, 4.4),
    (6, 102, "плитка серая бетон 60х60", 1400.0, 4.6),
]


@pytest.fixture
def catalog(tmp_path, monkeypatch):
    db = tmp_path / "test_catalog.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE products (id INTEGER PRIMARY KEY, category_id INTEGER, "
        "name TEXT, result_price REAL, rating REAL)"
    )
    conn.executemany("INSERT INTO products VALUES (?,?,?,?,?)", PRODUCTS)
    conn.commit()
    conn.close()
    monkeypatch.setattr(photo_router, "DB_PATH", db)
    return db


def _photo(rgb, fmt="PNG"):
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), rgb).save(buf, fmt)
    buf.seek(0)
    return buf.getvalue()


def test_green_wall_returns_three_sorted_matches(catalog):
    r = client.post(
        "/api/v1/room-photo",
        files={"photo": ("room.png", _photo((60, 140, 60)), "image/png")},
        data={"work_type": "wallpaper"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["work_type"] == "wallpaper"
    assert len(body["matches"]) == 3
    percents = [m["match_percent"] for m in body["matches"]]
    assert percents == sorted(percents, reverse=True)
    for m in body["matches"]:
        assert m["name"] and m["price"] > 0 and 0 <= m["match_percent"] <= 100


def test_paint_category_works(catalog):
    r = client.post(
        "/api/v1/room-photo",
        files={"photo": ("room.png", _photo((230, 225, 210)), "image/png")},
        data={"work_type": "paint"},
    )
    # В тестовом каталоге красок нет - должна быть честная 503, а не падение.
    assert r.status_code == 503


def test_unknown_work_type_is_422(catalog):
    r = client.post(
        "/api/v1/room-photo",
        files={"photo": ("room.png", _photo((60, 140, 60)), "image/png")},
        data={"work_type": "parquet"},
    )
    assert r.status_code == 422


def test_black_room_does_not_crash(catalog):
    # Чёрная комната: насыщенных пикселей нет, гистограмма пустая -
    # сервис не должен падать с 500.
    r = client.post(
        "/api/v1/room-photo",
        files={"photo": ("dark.png", _photo((0, 0, 0)), "image/png")},
        data={"work_type": "wallpaper"},
    )
    assert r.status_code == 200, r.text
