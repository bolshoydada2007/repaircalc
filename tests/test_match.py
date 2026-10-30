# Тесты подбора по фото. Запуск: pytest tests -v

import io
from types import SimpleNamespace

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.match import matcher
from app.match.color_features import photo_features

client = TestClient(app)


def solid_image(r: int, g: int, b: int) -> bytes:
    img = Image.new("RGB", (64, 64), (r, g, b))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def row(pid, name, rating=4.0, price=1000.0):
    return SimpleNamespace(id=pid, name=name, rating=rating, result_price=price)


class TestFeatures:
    def test_red_photo_is_saturated_red(self):
        f = photo_features(solid_image(255, 0, 0))
        assert abs(f[1] - 1.0) < 0.01          # насыщенность ~ 1
        assert f[3] > 0.9                      # гистограмма: bin оттенка 0

    def test_white_photo_has_no_hue(self):
        f = photo_features(solid_image(255, 255, 255))
        assert abs(f[1]) < 0.01                # насыщенность ~ 0
        assert f[3:].sum() < 0.01              # гистограмма пустая


class TestMatcher:
    def test_red_photo_prefers_red_product(self):
        red = row(1, "Плитка красная глянец")
        white = row(2, "Плитка белая матовая")
        vec = matcher.photo_vector(solid_image(255, 0, 0))
        scored = matcher.match_products([white, red], vec)
        assert scored[0][1].id == 1

    def test_white_photo_prefers_white_product(self):
        red = row(1, "Плитка красная глянец")
        white = row(2, "Плитка белая матовая")
        vec = matcher.photo_vector(solid_image(255, 255, 255))
        scored = matcher.match_products([white, red], vec)
        assert scored[0][1].id == 2

    def test_unknown_color_gets_neutral_reference(self):
        # товар без цвета в названии не ломает матчинг
        plain = row(1, "Обои дизайнерские, крупный рисунок")
        vec = matcher.photo_vector(solid_image(0, 128, 0))
        scored = matcher.match_products([plain], vec)
        assert scored[0][1].id == 1


class TestApi:
    def test_match_photo_ok(self):
        r = client.post(
            "/api/v1/match-photo",
            files={"photo": ("p.png", solid_image(255, 0, 0), "image/png")},
            data={"category": "tile"},
        )
        assert r.status_code == 200
        assert len(r.json()["matches"]) == 3

    def test_match_photo_bad_category(self):
        r = client.post(
            "/api/v1/match-photo",
            files={"photo": ("p.png", solid_image(255, 0, 0), "image/png")},
            data={"category": "parquet"},
        )
        assert r.status_code == 422
