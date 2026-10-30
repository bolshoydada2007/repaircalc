"""Импорт реальных цен из CSV-файла ручной выгрузки.

Формат файла (первая строка — заголовок, разделитель ;):
category;name;price;rating;in_stock;url
Пример строки:
wallpaper;Обои виниловые Nova 10x0.53 м;1490;4.6;1;https://petrovich.ru/...
"""

import csv
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from db_setup import ensure_products_table

DB_PATH = Path(__file__).resolve().parents[1] / "repaircalc.db"

REQUIRED = {"category", "name", "price", "rating", "in_stock", "url"}


def import_csv(csv_path: Path, source: str, db_path: Path = DB_PATH) -> int:
    """Обновляет цены существующих товаров (по имени и категории)
    и добавляет новые. Возвращает число обработанных строк."""
    ensure_products_table(db_path)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    count = 0
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        fields = set(reader.fieldnames or [])
        if not REQUIRED.issubset(fields):
            missing = sorted(REQUIRED - fields)
            raise ValueError(f"В CSV нет колонок: {missing}")
        for row in reader:
            name = row["name"].strip()
            category = row["category"].strip()
            if not name or not category:
                continue
            cur.execute(
                """UPDATE products
                   SET price=?, rating=?, in_stock=?, url=?, source=?, updated_at=?
                   WHERE lower(name)=lower(?) AND category=?""",
                (float(row["price"]), float(row["rating"]),
                 int(row["in_stock"]), row["url"], source, now,
                 name.lower(), category),
            )
            if cur.rowcount == 0:
                cur.execute(
                    """INSERT INTO products
                       (category, name, price, rating, in_stock, source, url, updated_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (category, name, float(row["price"]), float(row["rating"]),
                     int(row["in_stock"]), source, row["url"], now),
                )
            count += 1
    con.commit()
    con.close()
    return count


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("prices.csv")
    n = import_csv(path, source=path.stem)
    print(f"OK: импортировано/обновлено товаров: {n}")
