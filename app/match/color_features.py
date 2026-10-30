# Извлечение цветового профиля из фото.
# Вектор: средние [оттенок, насыщенность, яркость] + гистограмма
# оттенков (12 корзин, пиксели с низкой насыщенностью не учитываем —
# серые не должны размывать основной цвет).

import io

import numpy as np
from PIL import Image

HUE_BINS = 12


def photo_features(data: bytes) -> np.ndarray:
    """Фото (bytes) -> вектор длиной 3 + HUE_BINS."""
    img = Image.open(io.BytesIO(data)).convert("RGB").resize((64, 64))
    hsv = np.asarray(img.convert("HSV"), dtype=np.float64)
    h = hsv[:, :, 0] / 179.0   # в PIL оттенок 0..179
    s = hsv[:, :, 1] / 255.0
    v = hsv[:, :, 2] / 255.0

    hist, _ = np.histogram(h, bins=HUE_BINS, range=(0.0, 1.0),
                           weights=(s > 0.15).astype(np.float64))
    total = hist.sum()
    if total > 0:
        hist = hist / total
    return np.concatenate([[h.mean(), s.mean(), v.mean()], hist])
