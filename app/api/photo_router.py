# Эндпоинт подбора товаров по фотографии.

import sqlite3
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.match import matcher

router = APIRouter(prefix="/api/v1")

DB_PATH = Path("repaircalc.db")

PHOTO_CATEGORIES = {
    "paint": 100,
    "wallpaper": 101,
    "tile": 102,
    "laminate": 103,
}



@router.post("/match-photo")
def match_photo(
    photo: UploadFile = File(...),
    category: str = Form(...),
):
    if category not in PHOTO_CATEGORIES:
        raise HTTPException(status_code=422, detail="category: wallpaper или tile")

    data = photo.file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Файл пуст")
    try:
        photo_vec = matcher.photo_vector(data)
    except Exception:
        raise HTTPException(status_code=422, detail="Не удалось прочитать изображение")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM products WHERE category_id = ?",
            (PHOTO_CATEGORIES[category],),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        raise HTTPException(status_code=503, detail="Каталог категории пуст")

    scored = matcher.match_products(rows, photo_vec, limit=3)
    return {
        "matches": [
            {
                "product_id": row["id"],
                "name": row["name"],
                "price": row["result_price"],
                "rating": row["rating"],
                "score": round(score, 4),
            }
            for score, row in scored
        ]
    }
@router.post("/room-photo")
def room_photo(photo: UploadFile = File(...), work_type: str = Form(...)):
    """Фото комнаты -> материалы, чей цвет ближе всего к палитре помещения."""
    if work_type not in PHOTO_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail="work_type: paint, wallpaper, tile или laminate",
        )

    data = photo.file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Файл пуст")
    try:
        photo_vec = matcher.photo_vector(data)
    except Exception:
        raise HTTPException(status_code=422, detail="Не удалось прочитать изображение")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM products WHERE category_id = ?",
            (PHOTO_CATEGORIES[work_type],),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        raise HTTPException(status_code=503, detail="Каталог категории пуст")

    scored = matcher.match_products(rows, photo_vec, limit=3)
    return {
        "work_type": work_type,
        "matches": [
            {
                "product_id": row["id"],
                "name": row["name"],
                "price": row["result_price"],
                "rating": row["rating"],
                "match_percent": round(score * 100, 1),
            }
            for score, row in scored
        ],
    }
