# Эндпоинт расчёта сметы.
#
# Шаг 5: варианты на каждую работу формирует рекомендательный слой.
# Первым в списке всегда идёт самый дешёвый вариант (гарантия бюджета),
# дальше — лучшие по скорингу (цена + рейтинг + наличие).

import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.calc import consumption as c
from app.calc.scoring import rank_offers
from app.schemas import (
    CalculationRequest,
    CalculationResponse,
    ProductOffer,
    WorkResult,
)

router = APIRouter(prefix="/api/v1")

DB_PATH = Path("repaircalc.db")
OPTIONS_LIMIT = 3

TYPE_TO_CATEGORY = {
    "paint": 100,
    "wallpaper": 101,
    "tile": 102,
    "laminate": 103,
}


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _offer_from_row(row: sqlite3.Row, packages: int) -> ProductOffer:
    price = row["result_price"] or 0.0
    return ProductOffer(
        product_id=row["id"],
        name=row["name"],
        packages=packages,
        package_price=price,
        total_price=round(packages * price, 2),
        rating=row["rating"],
        in_stock=bool(row["in_stock"]),
    )


def _calc_one_work(conn: sqlite3.Connection, work) -> WorkResult:
    cat_id = TYPE_TO_CATEGORY[work.type]
    rows = conn.execute(
        "SELECT * FROM products WHERE category_id = ?", (cat_id,)
    ).fetchall()
    if not rows:
        raise HTTPException(status_code=503, detail=f"Каталог для типа {work.type} пуст")

    offers: list[ProductOffer] = []
    for row in rows:
        if work.type in ("tile", "laminate"):
            package_area = row["package_area"]
            if not package_area or package_area <= 0:
                continue
            waste = c.TILE_WASTE_SHARE if work.type == "tile" else c.LAMINATE_WASTE_SHARE
            packages = c.packages_by_area(work.area_m2, package_area, waste)
        elif work.type == "paint":
            liters = c.paint_liters(work.area_m2, coats=work.coats or c.PAINT_COATS)
            volume = row["quantity_in_package"]
            if not volume or volume <= 0:
                continue
            packages = c.packages_for_liters(liters, volume)
        else:  # wallpaper
            if not work.height_m:
                raise HTTPException(
                    status_code=422,
                    detail="Для работы wallpaper обязательно поле height_m",
                )
            try:
                packages = c.wallpaper_rolls(
                    work.area_m2,
                    work.height_m,
                    pattern_repeat_m=work.pattern_repeat_m or 0.0,
                )
            except ValueError:
                continue

        offers.append(_offer_from_row(row, packages))

    if not offers:
        raise HTTPException(status_code=503, detail=f"Нет подходящих товаров для {work.type}")

    # первый вариант — гарантированно самый дешёвый (гарантия бюджета),
    # остальные — лучшие по скорингу рекомендательного слоя
    by_price = sorted(offers, key=lambda o: o.total_price)
    picked: list[ProductOffer] = [by_price[0]]
    seen: set[int] = {by_price[0].product_id}
    for _score, offer in rank_offers(offers):
        if len(picked) >= OPTIONS_LIMIT:
            break
        if offer.product_id not in seen:
            picked.append(offer)
            seen.add(offer.product_id)

    return WorkResult(type=work.type, area_m2=work.area_m2, options=picked)


@router.post("/calculate", response_model=CalculationResponse)
def calculate(request: CalculationRequest) -> CalculationResponse:
    try:
        conn = _get_db()
    except sqlite3.Error:
        raise HTTPException(status_code=503, detail="База каталога недоступна")

    works: list[WorkResult] = []
    grand_total = 0.0
    try:
        for work in request.works:
            result = _calc_one_work(conn, work)
            works.append(result)
            grand_total += min(o.total_price for o in result.options)
    finally:
        conn.close()

    return CalculationResponse(works=works, grand_total=round(grand_total, 2))
