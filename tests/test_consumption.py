# Тесты модуля расхода.
# Запуск: .venv\Scripts\python.exe -m pytest tests -v

import math
from decimal import Decimal

import pytest

from app.calc import consumption as c


class TestAreaWithWaste:
    def test_tile_waste_10_percent(self):
        # 6 м2 плитки с запасом 10% = 6.6 м2
        assert c.area_with_waste(6.0, c.TILE_WASTE_SHARE) == pytest.approx(6.6)

    def test_laminate_waste_7_percent(self):
        # 18 м2 ламината с запасом 7% = 19.26 м2
        assert c.area_with_waste(18.0, c.LAMINATE_WASTE_SHARE) == pytest.approx(19.26)

    def test_zero_area_raises(self):
        with pytest.raises(ValueError):
            c.area_with_waste(0.0, 0.10)


class TestPackagesByArea:
    def test_tile_packages_ceil(self):
        # 6 м2 * 1.10 = 6.6 м2; в упаковке 1.44 м2 -> 6.6/1.44 = 4.58 -> 5 упаковок
        assert c.packages_by_area(6.0, 1.44, c.TILE_WASTE_SHARE) == 5

    def test_laminate_packages_ceil(self):
        # 18 м2 * 1.07 = 19.26 м2; в упаковке 2.22 м2 -> 19.26/2.22 = 8.67 -> 9
        assert c.packages_by_area(18.0, 2.22, c.LAMINATE_WASTE_SHARE) == 9

    def test_exact_fit_still_ceil(self):
        # 2 м2 ровно делятся на упаковку 2 м2 — всё равно 1 упаковка, не 0
        assert c.packages_by_area(2.0, 2.0, 0.0) == 1

    def test_zero_package_area_raises(self):
        with pytest.raises(ValueError):
            c.packages_by_area(6.0, 0.0, 0.10)


class TestPaint:
    def test_liters_two_coats(self):
        # 6 м2, 2 слоя, норма 10 м2/л -> 1.2 литра
        assert c.paint_liters(6.0) == pytest.approx(1.2)

    def test_one_coat(self):
        assert c.paint_liters(10.0, coats=1) == pytest.approx(1.0)

    def test_packages_round_up(self):
        # нужно 1.2 л, банка 1 л -> 2 банки
        assert c.packages_for_liters(1.2, 1.0) == 2

    def test_packages_exact_fit(self):
        # нужно ровно 2 л, банка 1 л -> ровно 2 банки (ceil не добавляет лишнюю)
        assert c.packages_for_liters(2.0, 1.0) == 2

    def test_zero_coats_raises(self):
        with pytest.raises(ValueError):
            c.paint_liters(6.0, coats=0)


class TestWallpaper:
    def test_cut_length_no_repeat(self):
        # без раппорта полотно режем по высоте стены
        assert c.wallpaper_cut_length_m(2.7, 0.0) == pytest.approx(2.7)

    def test_cut_length_with_repeat(self):
        # высота 2.7, раппорт 0.5 -> режем по 3.0 м, чтобы рисунок сошёлся
        assert c.wallpaper_cut_length_m(2.7, 0.5) == pytest.approx(3.0)

    def test_cut_length_exact_repeat(self):
        # высота 2.5, раппорт 0.5 -> 2.5 кратно, запас не нужен
        assert c.wallpaper_cut_length_m(2.5, 0.5) == pytest.approx(2.5)

    def test_rolls_no_repeat(self):
        # стены 20 м2, высота 2.7, рулон 10.05 x 1.06
        # полоса = 1.06 * 2.7 = 2.862 м2 -> полос нужно ceil(20/2.862) = 7
        # из рулона выходит floor(10.05/2.7) = 3 полосы -> ceil(7/3) = 3 рулона
        assert c.wallpaper_rolls(20.0, 2.7) == 3

    def test_rolls_with_repeat(self):
        # то же, но с раппортом 0.5: полотно 3.0 м, из рулона floor(10.05/3.0) = 3
        # полос всё ещё 7 -> ceil(7/3) = 3 рулона (раппорт маленький, не влияет)
        assert c.wallpaper_rolls(20.0, 2.7, pattern_repeat_m=0.5) == 3

    def test_rolls_when_strip_longer_than_roll_raises(self):
        # высота стены 12 м при рулоне 10.05 м — полотно не помещается
        with pytest.raises(ValueError):
            c.wallpaper_rolls(20.0, 12.0)


class TestMoney:
    def test_total_cost_decimal(self):
        result = c.total_cost(5, 1650.0)
        assert result == Decimal("8250.0")
        assert isinstance(result, Decimal)

    def test_no_float_drift(self):
        # классическая ошибка float: 0.1 * 3 != 0.3.
        # Decimal не должен дать 0.30000000000000004
        assert c.total_cost(3, 0.1) == Decimal("0.3")

    def test_negative_packages_raises(self):
        with pytest.raises(ValueError):
            c.total_cost(-1, 100)
