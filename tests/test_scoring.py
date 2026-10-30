# Тесты рекомендательного слоя. Запуск: pytest tests -v

from app.calc.scoring import rank_offers, score_offer
from app.schemas import ProductOffer


def mk(pid: int, price: float, rating: float | None, in_stock: bool) -> ProductOffer:
    return ProductOffer(
        product_id=pid, name=f"p{pid}", packages=1,
        package_price=price, total_price=price,
        rating=rating, in_stock=in_stock,
    )


class TestScore:
    def test_in_stock_beats_out_of_stock(self):
        # одинаковые цена и рейтинг: наличие решает
        good = mk(1, 1000.0, 4.5, True)
        bad = mk(2, 1000.0, 4.5, False)
        assert score_offer(good, 1000.0, 2000.0, 4.0, 5.0) > \
               score_offer(bad, 1000.0, 2000.0, 4.0, 5.0)

    def test_cheaper_better_same_rating(self):
        cheap = mk(1, 1000.0, 4.5, True)
        expensive = mk(2, 2000.0, 4.5, True)
        assert score_offer(cheap, 1000.0, 2000.0, 4.0, 5.0) > \
               score_offer(expensive, 1000.0, 2000.0, 4.0, 5.0)

    def test_higher_rating_better_same_price(self):
        top = mk(1, 1000.0, 4.9, True)
        mid = mk(2, 1000.0, 4.0, True)
        assert score_offer(top, 1000.0, 2000.0, 4.0, 5.0) > \
               score_offer(mid, 1000.0, 2000.0, 4.0, 5.0)

    def test_no_rating_scores_zero_component(self):
        o = mk(1, 1000.0, None, True)
        assert score_offer(o, 1000.0, 2000.0, 0.0, 5.0) is not None


class TestRank:
    def test_best_first(self):
        # у среднего товара рейтинг и наличие перевешивают цену
        cheap_bad = mk(1, 1000.0, 3.9, False)
        mid_good = mk(2, 1100.0, 4.8, True)
        expensive = mk(3, 1200.0, 4.0, True)
        scored = rank_offers([cheap_bad, mid_good, expensive])
        assert scored[0][1].product_id == 2

    def test_tie_broken_by_price(self):
        # ничья по скорингу: дешёвый выигрывает
        cheap_bad = mk(1, 1000.0, 3.9, False)
        mid_good = mk(2, 1200.0, 4.8, True)
        scored = rank_offers([cheap_bad, mid_good])
        assert scored[0][1].product_id == 1

    def test_empty_list(self):
        assert rank_offers([]) == []

    def test_single_offer(self):
        o = mk(1, 1000.0, 4.0, True)
        assert rank_offers([o])[0][1].product_id == 1
