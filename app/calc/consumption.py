# Формулы расхода материалов.
#
# Модуль знает только про числа: на вход площадь/высота/параметры
# упаковки, на выход — количество упаковок или литров.
# Никакого доступа к базе и API здесь нет и быть не должно:
# это позволяет проверять формулы простыми тестами.
#
# Все деньги считаем в Decimal (см. комментарий в total_cost).

import math
from decimal import Decimal

# Нормативные запасы на подрезку/отходы (доли от 1).
# Значения из кейса: плитка ~10%, ламинат ~7%.
TILE_WASTE_SHARE = 0.10
LAMINATE_WASTE_SHARE = 0.07

# Стандартные параметры рулона обоев (типовые значения производителей).
WALLPAPER_ROLL_LENGTH_M = 10.05
WALLPAPER_ROLL_WIDTH_M = 1.06

# Стандартная норма покраски: сколько м2 покрывает 1 литр краски
# в один слой. Реальную норму потом берём из характеристики товара,
# пока это дефолт для расчёта.
PAINT_COVERAGE_M2_PER_LITER = 10.0
PAINT_COATS = 2  # стандарт: красим в два слоя


def _check_positive(value: float, name: str) -> None:
    """Защита от бессмысленных входных данных (0 или отрицательные)."""
    if value <= 0:
        raise ValueError(f"{name} должен быть положительным числом, получено: {value}")


def area_with_waste(area_m2: float, waste_share: float) -> float:
    """Площадь с запасом на подрезку и отходы.

    Пример: 6 м2 плитки с запасом 10% -> 6 * 1.10 = 6.6 м2.
    """
    _check_positive(area_m2, "area_m2")
    if waste_share < 0:
        raise ValueError("waste_share не может быть отрицательным")
    return area_m2 * (1.0 + waste_share)


def packages_by_area(area_m2: float, package_area_m2: float, waste_share: float) -> int:
    """Сколько упаковок площадного материала (плитка, ламинат) нужно купить.

    area_m2         — чистая площадь поверхности, м2
    package_area_m2 — сколько м2 в одной упаковке (поле package_area каталога)
    waste_share     — запас на подрезку (0.10 для плитки, 0.07 для ламината)

    Округление всегда вверх до целых упаковок.
    """
    _check_positive(package_area_m2, "package_area_m2")
    needed = area_with_waste(area_m2, waste_share)
    return math.ceil(needed / package_area_m2)


def paint_liters(area_m2: float, coats: int = PAINT_COATS,
                 coverage_m2_per_liter: float = PAINT_COVERAGE_M2_PER_LITER) -> float:
    """Сколько литров краски нужно на площадь.

    Формула: литры = площадь * число_слоёв / норма_расхода(м2 на литр).
    """
    _check_positive(area_m2, "area_m2")
    if coats < 1:
        raise ValueError("coats должен быть >= 1")
    _check_positive(coverage_m2_per_liter, "coverage_m2_per_liter")
    return area_m2 * coats / coverage_m2_per_liter


def packages_for_liters(liters: float, liters_per_package: float) -> int:
    """Сколько упаковок краски купить.

    liters_per_package — объём краски в одной упаковке (обычно это
    quantity_in_package из каталога, когда unit равен 'л' или 'шт' банок).
    """
    _check_positive(liters, "liters")
    _check_positive(liters_per_package, "liters_per_package")
    return math.ceil(liters / liters_per_package)


def wallpaper_cut_length_m(wall_height_m: float, pattern_repeat_m: float = 0.0) -> float:
    """Длина одного полотнища обоев с учётом подгона рисунка.

    Если у обоев есть раппорт (pattern_repeat_m — высота повторяющегося
    рисунка), каждое полотнище приходится отрезать с запасом так, чтобы
    длина полотна была кратна раппорту. Иначе рисунок на стыке не совпадёт.

    Пример: высота стены 2.7 м, раппорт 0.5 м.
    2.7 не кратно 0.5, поэтому режем на 3.0 м (2.7 + 0.3 запаса).
    """
    _check_positive(wall_height_m, "wall_height_m")
    if pattern_repeat_m <= 0:
        return wall_height_m
    # округляем высоту вверх до ближайшего кратного раппорта
    remainder = wall_height_m % pattern_repeat_m
    if remainder == 0:
        return wall_height_m
    return wall_height_m + (pattern_repeat_m - remainder)


def wallpaper_rolls(wall_area_m2: float, wall_height_m: float,
                    roll_length_m: float = WALLPAPER_ROLL_LENGTH_M,
                    roll_width_m: float = WALLPAPER_ROLL_WIDTH_M,
                    pattern_repeat_m: float = 0.0) -> int:
    """Сколько рулонов обоев нужно на площадь стен.

    Логика «по полосам» (стандартная у мастеров):
    1) считаем длину одного полотнища с учётом раппорта;
    2) считаем, сколько целых полотнищ выйдет из одного рулона;
    3) считаем, сколько полос нужно закрыть всю площадь стен;
    4) делим и округляем вверх.
    """
    _check_positive(wall_area_m2, "wall_area_m2")
    _check_positive(roll_length_m, "roll_length_m")
    _check_positive(roll_width_m, "roll_width_m")

    cut_length = wallpaper_cut_length_m(wall_height_m, pattern_repeat_m)
    strips_per_roll = math.floor(roll_length_m / cut_length)
    if strips_per_roll == 0:
        # полотнище длиннее рулона — такие обои в этой формуле не считаем
        raise ValueError(
            f"Полотнище {cut_length:.2f} м не помещается в рулон {roll_length_m} м"
        )

    # площадь одной полосы = ширина рулона * высота полотнища,
    # полосы считаем по чистой высоте стены (стык сверху прячется плинтусом)
    strips_needed = math.ceil(wall_area_m2 / (roll_width_m * wall_height_m))
    return math.ceil(strips_needed / strips_per_roll)


def total_cost(packages_count: int, package_price: float | int | str) -> Decimal:
    """Итоговая стоимость = число упаковок * цена упаковки.

    package_price — цена ОДНОЙ упаковки (поле result_price из каталога).
    Не путать с price_per_m2: это цена за квадратный метр, она для
    сметы не подходит, потому что продаём мы упаковки, а не метры.

    Decimal(str(...)) — потому что float нельзя напрямую превратить
    в Decimal без потери точности: Decimal(0.1) даст 0.1000000000000000055,
    а Decimal(str(0.1)) даст ровно 0.1.
    """
    if packages_count < 0:
        raise ValueError("packages_count не может быть отрицательным")
    price = Decimal(str(package_price))
    return price * packages_count
