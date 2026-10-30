"""Подготовка базы каталога: недостающие колонки для источников данных."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "repaircalc.db"

REQUIRED_COLUMNS = {
    "source": "TEXT DEFAULT 'stub'",
    "url": "TEXT",
    "updated_at": "TEXT",
}


def ensure_products_table(db_path: Path = DB_PATH) -> None:
    """Создаёт таблицу products, если её нет, и добавляет
    недостающие колонки (безопасно для существующей базы)."""
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS products (
               id INTEGER PRIMARY KEY,
               category TEXT NOT NULL,
               name TEXT NOT NULL,
               price REAL NOT NULL,
               rating REAL NOT NULL DEFAULT 0,
               in_stock INTEGER NOT NULL DEFAULT 1,
               source TEXT DEFAULT 'stub',
               url TEXT,
               updated_at TEXT
           )"""
    )
    existing = {row[1] for row in cur.execute("PRAGMA table_info(products)")}
    for column, ddl in REQUIRED_COLUMNS.items():
        if column not in existing:
            cur.execute(f"ALTER TABLE products ADD COLUMN {column} {ddl}")
    con.commit()
    con.close()


if __name__ == "__main__":
    ensure_products_table()
    print("OK: таблица products готова к источникам данных")
