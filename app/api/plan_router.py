# Шаг 16: сценарный слой "квартира под ключ" поверх smart-select.
# Правила подбора не дублируем - переиспользуем готовый эндпоинт.

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Literal

from app.api.smart_router import (
    SmartSelectItem,
    SmartSelectRequest,
    SmartWorkResult,
    smart_select as _smart_select_endpoint,
)


router = APIRouter(prefix="/api/v1")

# Какой набор работ выполняем в помещении при каждом типе ремонта.
# Влажные (ванная, кухня): косметический - только краска;
# капитальный - плитка + краска. Сухие: косметический - обои;
# капитальный - обои + ламинат.
WORKS_BY_ROOM = {
    "wet": {"cosmetic": ["paint"], "capital": ["tile", "paint"]},
    "dry": {"cosmetic": ["wallpaper"], "capital": ["wallpaper", "laminate"]},
}


class PlanRoom(BaseModel):
    name: str = ""
    type: Literal["bathroom", "kitchen", "dry", "any"]
    area_m2: float = Field(gt=0)


class PlanRequest(BaseModel):
    rooms: List[PlanRoom] = Field(min_length=1)
    renovation: Literal["cosmetic", "capital"]
    budget: Literal["budget", "standard", "premium"] = "standard"


class PlanRoomResult(BaseModel):
    name: str
    type: str
    works: List[SmartWorkResult]
    room_total: float


class PlanResponse(BaseModel):
    rooms: List[PlanRoomResult]
    grand_total: float


def _works_for(room_type: str, renovation: str) -> List[str]:
    kind = "wet" if room_type in ("bathroom", "kitchen") else "dry"
    return WORKS_BY_ROOM[kind][renovation]


@router.post("/plan", response_model=PlanResponse)
def plan(req: PlanRequest):
    out_rooms: List[PlanRoomResult] = []
    grand = 0.0

    for room in req.rooms:
        items = []
        for work_type in _works_for(room.type, req.renovation):
            item = SmartSelectItem(
                type=work_type,
                area_m2=room.area_m2,
                room=room.type,
                budget=req.budget,
            )
            if work_type == "paint":
                item.coats = 2
            if work_type == "wallpaper":
                item.height_m = 2.7
            items.append(item)

        try:
            res = _smart_select_endpoint(SmartSelectRequest(items=items))
        except HTTPException:
            # В каком-то помещении подбор пуст (нет товаров под условия) -
            # это не повод рушить весь план: комната останется с пустыми работами.
            res = None

        room_total = 0.0
        works = res.works if res is not None else []
        for work in works:
            if work.options:
                room_total += min(o.total_price for o in work.options)

        out_rooms.append(PlanRoomResult(
            name=room.name or room.type,
            type=room.type,
            works=works,
            room_total=round(room_total, 2),
        ))
        grand += room_total

    return PlanResponse(rooms=out_rooms, grand_total=round(grand, 2))
