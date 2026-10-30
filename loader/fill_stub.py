# Заглушка каталога: наполняет repaircalc.db тестовыми товарами.
#
# Схемы таблиц совпадают с loader/fetch_catalog.py, поэтому код шагов 4+
# работает одинаково и с заглушкой, и с реальными данными.
# Когда появится адрес стенда: python loader\fill_stub.py --drop
# (очистит базу), затем настоящий fetch_catalog.py tree / products.

import argparse
import json
import sqlite3
from pathlib import Path

DB_PATH = Path("repaircalc.db")


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id            INTEGER PRIMARY KEY,
            parent_id     INTEGER,
            name          TEXT,
            depth_level   INTEGER,
            product_count INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id                  INTEGER PRIMARY KEY,
            sku                 TEXT,
            cod_good            TEXT,
            name                TEXT,
            category_id         INTEGER,
            description         TEXT,
            marketing_description TEXT,
            unit                TEXT,
            quantity_in_package REAL,
            package_area        REAL,
            result_price        REAL,
            price_per_m2        REAL,
            in_stock            INTEGER,
            rating              REAL,
            recsys_rating       REAL,
            raw_json            TEXT
        )
    """)
    conn.commit()


def clear(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM categories")
    conn.execute("DELETE FROM products")
    conn.commit()


# id категорий начинаем с 100, чтобы не путаться с реальными категориями,
# которые потом придут с живого стенда.
CATEGORIES = [
    (100, None, "Краска для стен и потолков", 2, 6),
    (101, None, "Обои", 2, 6),
    (102, None, "Плитка керамическая", 2, 4),
    (103, None, "Ламинат", 2, 4),
]

# id товаров начинаем с 1000.
# unit/quantity_in_package/package_area — то, что читают формулы шага 2.
PRODUCTS = [
    # Краска (id категории 100). Расход ~10 м2/л на слой, продаём банки по литрам.
    (1000, "1000", "KR-001", "Краска интерьерная белая матовая, 9 л", 100,
     "Краска для стен и потолков, матовая, белая. Расход 10 м2/л на слой.",
     None, "л", 9.0, None, 2890.0, None, 1, 4.6, 0.82),
    (1001, "1001", "KR-002", "Краска для стен моющаяся, 3 л", 100,
     "Моющаяся краска, подходит для кухни. Расход 11 м2/л на слой.",
     None, "л", 3.0, None, 1150.0, None, 1, 4.3, 0.74),
    (1002, "1002", "KR-003", "Краска для ванных комнат влагостойкая, 2.5 л", 100,
     "Влагостойкая краска для влажных помещений. Расход 9 м2/л на слой.",
     None, "л", 2.5, None, 1290.0, None, 1, 4.7, 0.79),
    (1003, "1003", "KR-004", "Краска фасадная, 14 л", 100,
     "Для наружных работ. Расход 8 м2/л на слой.",
     None, "л", 14.0, None, 4200.0, None, 1, 4.1, 0.61),
    (1004, "1004", "KR-005", "Краска-грунт 2 в 1, 5 л", 100,
     "Грунт и краска в одном флаконе. Расход 12 м2/л на слой.",
     None, "л", 5.0, None, 1890.0, None, 1, 4.4, 0.77),
    (1005, "1005", "KR-006", "Колерованная краска синяя, 1 л", 100,
     "Готовая колеровка, синий цвет. Расход 10 м2/л на слой.",
     None, "л", 1.0, None, 480.0, None, 0, 3.9, 0.55),
    # Обои (id категории 101). Рулон 10.05 x 1.06 м, раппорт в описании.
    (1010, "1010", "OB-001", "Обои флизелиновые однотонные, серые", 101,
     "Флизелиновые обои, раппорт 0 см (без подгона рисунка).",
     None, "шт", None, None, 1290.0, None, 1, 4.5, 0.80),
    (1011, "1011", "OB-002", "Обои виниловые с рисунком, классические", 101,
     "Виниловые обои на флизелине, раппорт 53 см.",
     None, "шт", None, None, 1690.0, None, 1, 4.2, 0.68),
    (1012, "1012", "OB-003", "Обои под покраску, белые", 101,
     "Обои под дальнейшую покраску, раппорт 0 см.",
     None, "шт", None, None, 990.0, None, 1, 4.6, 0.83),
    (1013, "1013", "OB-004", "Обои для ванной влагостойкие", 101,
     "Влагостойкие моющиеся обои, раппорт 26 см.",
     None, "шт", None, None, 1490.0, None, 1, 4.0, 0.64),
    (1014, "1014", "OB-005", "Обои бумажные, светлые", 101,
     "Бумажные обои, раппорт 0 см.",
     None, "шт", None, None, 690.0, None, 1, 3.8, 0.5),
    (1015, "1015", "OB-006", "Обои дизайнерские, крупный рисунок", 101,
     "Дизайнерские обои, раппорт 64 см.",
     None, "шт", None, None, 3290.0, None, 1, 4.8, 0.9),
    # Плитка (id категории 102). Продаём упаковками м2.
    (1020, "1020", "PL-001", "Плитка керамическая белая 20x60, 1.44 м2", 102,
     "Для стен, влагостойкая. В упаковке 1.44 м2.",
     None, "шт", 12.0, 1.44, 1890.0, 1312.5, 1, 4.7, 0.85),
    (1021, "1021", "PL-002", "Плитка серая матовая 30x30, 1.35 м2", 102,
     "Для пола и стен. В упаковке 1.35 м2.",
     None, "шт", 15.0, 1.35, 1650.0, 1222.2, 1, 4.3, 0.72),
    (1022, "1022", "PL-003", "Керамогранит под дерево 20x120, 2.16 м2", 102,
     "Керамогранит, в упаковке 2.16 м2.",
     None, "шт", 9.0, 2.16, 3490.0, 1615.7, 1, 4.6, 0.88),
    (1023, "1023", "PL-004", "Плитка мозаика, 1.0 м2", 102,
     "Мозаика для ванной. В упаковке 1.0 м2.",
     None, "шт", 20.0, 1.0, 2450.0, 2450.0, 1, 4.4, 0.76),
    # Ламинат (id категории 103). Продаём упаковками м2.
    (1030, "1030", "LM-001", "Ламинат дуб светлый 32 класс, 2.22 м2", 103,
     "Класс 32, толщина 8 мм. В упаковке 2.22 м2.",
     None, "шт", 10.0, 2.22, 1350.0, 608.1, 1, 4.5, 0.81),
    (1031, "1031", "LM-002", "Ламинат тёмный орех 33 класс, 2.4 м2", 103,
     "Класс 33, влагостойкий. В упаковке 2.4 м2.",
     None, "шт", 8.0, 2.4, 1890.0, 787.5, 1, 4.7, 0.89),
    (1032, "1032", "LM-003", "Ламинат белый дуб, 1.86 м2", 103,
     "Класс 31, бюджетный. В упаковке 1.86 м2.",
     None, "шт", 8.0, 1.86, 990.0, 532.3, 1, 4.1, 0.62),
    (1033, "1033", "LM-004", "Ламинат под бетон, 2.13 м2", 103,
     "Класс 32, под бетон. В упаковке 2.13 м2.",
     None, "шт", 7.0, 2.13, 1590.0, 746.5, 0, 4.0, 0.58),
]


def fill(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT OR REPLACE INTO categories VALUES (?, ?, ?, ?, ?)", CATEGORIES
    )
    conn.executemany(
        """
        INSERT OR REPLACE INTO products
        (id, sku, cod_good, name, category_id, description, marketing_description,
         unit, quantity_in_package, package_area, result_price, price_per_m2,
         in_stock, rating, recsys_rating, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (i, sku, cod, name, cat, desc, mkt, unit, qip, pa, price, ppm,
             instock, rating, rec, json.dumps({"id": i, "name": name},
                                               ensure_ascii=False))
            for (i, sku, cod, name, cat, desc, mkt, unit, qip, pa, price,
                 ppm, instock, rating, rec) in PRODUCTS
        ],
    )
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Заполнение базы заглушкой")
    parser.add_argument("--drop", action="store_true",
                        help="очистить таблицы перед заполнением")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    if args.drop:
        clear(conn)
        print("Таблицы очищены.")
    fill(conn)

    n_cat = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    n_prd = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    print(f"Готово: категорий {n_cat}, товаров {n_prd} в {DB_PATH}")


if __name__ == "__main__":
    main()
