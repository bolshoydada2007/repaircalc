"""Шаг 14: эндпоинт умного подбора /api/v1/smart-select.

Вход: тип работы, помещение, ценовой сегмент.
Выход: до 3 вариантов с расчётом упаковок и человекочитаемыми
причинами подбора (reasons) — признаковое объяснение для UI и жюри.

Правила выведены из фактов шага 13 (диагностика атрибутов фида):
- плитка: помещение зашито в подкатегории фида (ванная/кухня/напольная);
- краска: Влагостойкость + Тип помещения + Назначение;
- обои: Влагостойкость обоев (4 уровня);
- ламинат: класс износостойкости + влагостойкость.

Первый вариант всегда самый дешёвый (гарантия бюджета),
остальные — лучшие по скорингу рекомендательного слоя.
"""

import json
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException
import pydantic

from app.calc import consumption as c
from app.calc.scoring import rank_offers
from app.schemas import ProductOffer, WorkResult

router = APIRouter(prefix="/api/v1")

DB_PATH = Path("repaircalc.db")

TYPE_TO_CATEGORY = {
    "paint": 100,
    "wallpaper": 101,
    "tile": 102,
    "laminate": 103,
}

# коридор классов ламината по сегменту (факт: в базе есть 31-34)
LAMINATE_WEAR = {
    "budget": ("31", "32"),
    "standard": ("32", "33"),
    "premium": ("33", "34"),
}

MOISTURE_LEVEL_RU = {
    "high": "супермоющиеся",
    "mid": "влагостойкие/моющиеся",
    "low": "не влагостойкие",
}


class SmartSelectItem(pydantic.BaseModel):
    type: str
    area_m2: float
    room: str = "any"          # bathroom / kitchen / dry / any
    budget: str = "standard"   # budget / standard / premium
    height_m: float | None = None
    coats: int | None = None
    pattern_repeat_m: float | None = None


class SmartSelectRequest(pydantic.BaseModel):
    items: list[SmartSelectItem]


class SmartOption(ProductOffer):
    reasons: list[str] = []


class SmartWorkResult(WorkResult):
    options: list[SmartOption]  # type: ignore[assignment]


class SmartSelectResponse(pydantic.BaseModel):
    works: list[SmartWorkResult]


def _matches_room(cat_id: int, room: str, derived: dict) -> tuple[bool, list[str]]:
    """Возвращает (подходит ли, список причин)."""
    if cat_id == 102:  # плитка: подкатегория фида сохранена в derived.room
        sub = derived.get("room", "any")
        if room == "bathroom":
            ok = sub in ("ванная", "any")
            return ok, (["плитка для ванной комнаты"] if ok else [])
        if room == "kitchen":
            ok = sub in ("кухня", "any")
            return ok, (["плитка для кухни"] if ok else [])
        return True, ["подходит для любых помещений"]

    if cat_id == 100:  # краска
        if derived.get("suitable") == 0:
            return False, []  # спецсоставы (для обоев, декор) не даём на стены
        moisture = derived.get("moisture")
        r = derived.get("room")
        if room == "bathroom":
            ok = moisture == "yes"
            return ok, (["влагостойкая — подходит для ванной"] if ok else [])
        if room == "kitchen":
            ok = r in ("kitchen", "any", None)
            return ok, (["подходит для кухни"] if ok else [])
        return True, ["подходит для жилых комнат"]

    if cat_id == 101:  # обои
        level = derived.get("moisture_level", "unknown")
        if room == "bathroom":
            # для ванной только супермоющиеся: это самая мокрая зона
            ok = level == "high"
            return ok, ([f"влагостойкость: {MOISTURE_LEVEL_RU.get(level, level)}"
                         " — выдержит ванную"] if ok else [])
        if room == "kitchen":
            ok = level in ("high", "mid")
            return ok, ([f"влагостойкость: {MOISTURE_LEVEL_RU.get(level, level)}"
                         " — можно на кухню"] if ok else [])
        return True, ["подходит для жилых комнат"]

    if cat_id == 103:  # ламинат: помещение не критично
        reasons = []
        if derived.get("moisture") == "yes":
            reasons.append("влагостойкий")
        return True, reasons or ["подходит для жилых комнат"]

    return False, []


def _matches_budget(cat_id: int, budget: str,
                    derived: dict) -> tuple[bool, list[str]]:
    tier = derived.get("price_tier")
    if tier is None:
        return True, []  # без цены за м2 не отсекаем — решит скоринг
    if cat_id == 103 and budget in LAMINATE_WEAR:
        wear = derived.get("wear_class")
        if wear is None:
            return True, []  # класс неизвестен — не отсекаем
        lo, hi = LAMINATE_WEAR[budget]
        if not (lo <= wear <= hi):
            return False, []
        return True, [f"класс износостойкости {wear} соответствует сегменту «{budget}»"]
    if tier != budget:
        return False, []
    return True, [f"ценовой сегмент: {tier}"]


def _calc_packages(work: SmartSelectItem, row) -> int | None:
    """Кол-во упаковок по тем же формулам, что в calc_router."""
    if work.type in ("tile", "laminate"):
        package_area = row["package_area"]
        if not package_area or package_area <= 0:
            return None
        waste = c.TILE_WASTE_SHARE if work.type == "tile" else c.LAMINATE_WASTE_SHARE
        return c.packages_by_area(work.area_m2, package_area, waste)
    if work.type == "paint":
        liters = c.paint_liters(work.area_m2, coats=work.coats or c.PAINT_COATS)
        volume = row["quantity_in_package"]
        if not volume or volume <= 0:
            return None
        return c.packages_for_liters(liters, volume)
    # wallpaper
    if not work.height_m:
        raise HTTPException(
            status_code=422,
            detail="Для работы wallpaper обязательно поле height_m",
        )
    try:
        return c.wallpaper_rolls(
            work.area_m2, work.height_m,
            pattern_repeat_m=work.pattern_repeat_m or 0.0,
        )
    except ValueError:
        return None


def _offer_from_row(row, packages: int, reasons: list[str]) -> SmartOption:
    price = row["result_price"] or 0.0
    return SmartOption(
        product_id=row["id"],
        name=row["name"],
        packages=packages,
        package_price=price,
        total_price=round(packages * price, 2),
        rating=row["rating"],
        in_stock=bool(row["in_stock"]),
        reasons=reasons,
    )


def _build_result(work: SmartSelectItem, rows_by_id: dict,
                  candidates: list[tuple[int, list[str]]]) -> SmartWorkResult:
    """Собирает до 3 вариантов: первый — самый дешёвый, остальные по скорингу."""
    offers: list[SmartOption] = []
    for pid, reasons in candidates:
        row = rows_by_id[pid]
        packages = _calc_packages(work, row)
        if packages is None:
            continue
        offers.append(_offer_from_row(row, packages, reasons))
    if not offers:
        raise HTTPException(
            status_code=503,
            detail=f"Нет подходящих товаров для {work.type}",
        )
    by_price = sorted(offers, key=lambda o: o.total_price)
    picked: list[SmartOption] = [by_price[0]]
    seen: set[int] = {by_price[0].product_id}
    for _score, offer in rank_offers(offers):
        if len(picked) >= 3:
            break
        if offer.product_id not in seen:
            picked.append(offer)
            seen.add(offer.product_id)
    return SmartWorkResult(type=work.type, area_m2=work.area_m2, options=picked)


@router.post("/smart-select", response_model=SmartSelectResponse)
def smart_select(request: SmartSelectRequest) -> SmartSelectResponse:
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        raise HTTPException(status_code=503, detail="База каталога недоступна")

    works: list[SmartWorkResult] = []
    try:
        for work in request.items:
            cat_id = TYPE_TO_CATEGORY[work.type]
            rows = conn.execute(
                "SELECT * FROM products WHERE category_id = ? AND in_stock = 1",
                (cat_id,),
            ).fetchall()
            rows_by_id = {row["id"]: row for row in rows}
            candidates: list[tuple[int, list[str]]] = []
            for row in rows:
                derived = json.loads(row["raw_json"] or "{}").get("derived", {})
                ok_room, why_room = _matches_room(cat_id, work.room, derived)
                if not ok_room:
                    continue
                ok_budget, why_budget = _matches_budget(cat_id, work.budget, derived)
                if not ok_budget:
                    continue
                # упаковки считаем при сборке оффера (нужен row)
                candidates.append((row["id"], why_room + why_budget))
            if not candidates:
                raise HTTPException(
                    status_code=503,
                    detail=f"Нет товаров под условия для {work.type}",
                )
            works.append(_build_result(work, rows_by_id, candidates))
    finally:
        conn.close()
    return SmartSelectResponse(works=works)
