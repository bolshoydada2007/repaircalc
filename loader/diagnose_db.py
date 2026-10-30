"""Диагностика базы: какие таблицы и колонки реально есть."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "repaircalc.db"

con = sqlite3.connect(DB_PATH)
cur = con.cursor()
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print("Таблицы:", tables)
for t in tables:
    print(f"\nТаблица {t}:")
    for row in cur.execute(f"PRAGMA table_info({t})"):
        print("   ", row[1], row[2])
con.close()
