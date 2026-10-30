# Матчинг фото -> товары по цвету.
# Эталон цвета товара строим по ключевым словам в названии
# («белая», «зелёный»...). Когда появятся изображения товаров,
# заменим эталоны на эмбеддинги реальных фото — сигнатура не меняется.

import numpy as np

from app.match.color_features import HUE_BINS, photo_features

# ключ -> (оттенок 0..1, насыщенность, яркость); оттенки в шкале PIL
COLOR_KEYWORDS = {
    "красн": (0.00, 0.80, 0.55),
    "оранж": (0.08, 0.90, 0.85),
    "коричн": (0.07, 0.50, 0.40),
    "дуб": (0.09, 0.45, 0.50),
    "венге": (0.05, 0.40, 0.20),
    "беж": (0.10, 0.35, 0.85),
    "кремов": (0.12, 0.30, 0.90),
    "жёлт": (0.17, 0.80, 0.90),
    "желт": (0.17, 0.80, 0.90),
    "зелён": (0.33, 0.60, 0.55),
    "зелен": (0.33, 0.60, 0.55),
    "голуб": (0.54, 0.50, 0.85),
    "син": (0.61, 0.75, 0.55),
    "фиолет": (0.78, 0.60, 0.50),
    "розов": (0.92, 0.50, 0.90),
    "бел": (0.00, 0.00, 1.00),
    "сер": (0.00, 0.00, 0.55),
    "чёрн": (0.00, 0.00, 0.15),
    "черн": (0.00, 0.00, 0.15),
}

NEUTRAL = (0.0, 0.0, 0.6)   # в названии нет цвета — нейтральный эталон

W_COLOR = 0.8               # вес совпадения цвета
W_RATING = 0.2              # вес рейтинга


def product_vector(name: str) -> np.ndarray:
    h, s, v = NEUTRAL
    low = name.lower()
    for key, (kh, ks, kv) in COLOR_KEYWORDS.items():
        if key in low:
            h, s, v = kh, ks, kv
            break
    hist = np.zeros(HUE_BINS)
    if s > 0.1:
        hist[int(h * HUE_BINS) % HUE_BINS] = 1.0
    return np.array([h, s, v, *hist])


def _get(row, key):
    """Работает и со строками sqlite3.Row, и с обычными объектами."""
    try:
        return row[key]
    except (TypeError, KeyError, IndexError):
        return getattr(row, key, None)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na <= 1e-9 or nb <= 1e-9:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def match_products(rows, photo_vec: np.ndarray, limit: int = 3):
    """[(score, row)] — лучшие первыми; при равенстве дешевле выше."""
    scored = []
    for row in rows:
        color_sim = _cosine(photo_vec, product_vector(_get(row, "name")))
        rating = _get(row, "rating") or 0.0
        score = W_COLOR * color_sim + W_RATING * (rating / 5.0)
        scored.append((score, row))
    scored.sort(key=lambda pair: (-pair[0], _get(pair[1], "result_price") or 0.0))
    return scored[:limit]


def photo_vector(data: bytes) -> np.ndarray:
    return photo_features(data)
