# Рекомендательный слой: скоринг предложений.
#
# Скоринг — число от 0 до 1. Складывается из трёх компонент:
#   цена      (дешевле — лучше)      вес 0.50
#   рейтинг   (выше — лучше)         вес 0.35
#   наличие   (in_stock — лучше)     вес 0.15
#
# Каждая компонента нормируется в [0, 1] внутри одной категории товаров,
# чтобы краска за 480 и плитка за 1890 сравнивались честно — каждая
# внутри своей группы.
#
# Когда организаторы дадут поле маржинальности, добавим четвёртую
# компоненту с весом W_MARGIN — структура функции это позволяет.

from app.schemas import ProductOffer

W_PRICE = 0.50
W_RATING = 0.35
W_STOCK = 0.15
W_MARGIN = 0.0  # включим, когда появится поле в данных


def _norm_lower_better(value: float, lo: float, hi: float) -> float:
    """Нормировка «чем меньше, тем лучше»: min -> 1.0, max -> 0.0."""
    if hi - lo <= 1e-9:
        return 1.0
    return (hi - value) / (hi - lo)


def _norm_higher_better(value: float, lo: float, hi: float) -> float:
    """Нормировка «чем больше, тем лучше»: min -> 0.0, max -> 1.0."""
    if hi - lo <= 1e-9:
        return 1.0
    return (value - lo) / (hi - lo)


def score_offer(offer: ProductOffer,
                price_lo: float, price_hi: float,
                rating_lo: float, rating_hi: float) -> float:
    """Скоринг одного предложения в диапазоне цен/рейтингов своей категории."""
    price_score = _norm_lower_better(offer.total_price, price_lo, price_hi)
    if offer.rating is None:
        rating_score = 0.0
    else:
        rating_score = _norm_higher_better(offer.rating, rating_lo, rating_hi)
    stock_score = 1.0 if offer.in_stock else 0.0
    return (W_PRICE * price_score
            + W_RATING * rating_score
            + W_STOCK * stock_score
            + W_MARGIN * 0.0)


def rank_offers(offers: list[ProductOffer]) -> list[tuple[float, ProductOffer]]:
    """Сортирует предложения по скорингу (лучшие — первые).

    Границы для нормировки берём внутри самого списка — это и есть
    «сравнение внутри одной категории».
    """
    if not offers:
        return []
    prices = [o.total_price for o in offers]
    ratings = [o.rating for o in offers if o.rating is not None]
    price_lo, price_hi = min(prices), max(prices)
    rating_lo = min(ratings) if ratings else 0.0
    rating_hi = max(ratings) if ratings else 0.0
    scored = [(score_offer(o, price_lo, price_hi, rating_lo, rating_hi), o)
              for o in offers]
    scored.sort(key=lambda pair: (-pair[0], pair[1].total_price))
    return scored
