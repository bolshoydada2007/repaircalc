# Схемы запросов и ответов API.
# Pydantic проверяет данные автоматически: если вместо числа придёт
# строка "шесть", клиент получит понятную ошибку 422 без нашего участия.

from pydantic import BaseModel, Field, field_validator


class WorkItem(BaseModel):
    """Одна работа в запросе: какой тип покрытия и какая площадь."""
    type: str = Field(
        description="Тип работы: tile | paint | wallpaper | laminate"
    )
    area_m2: float = Field(gt=0, description="Площадь поверхности, м2")
    height_m: float | None = Field(
        default=None, gt=0,
        description="Высота стены, м. Нужна только для обоев",
    )
    pattern_repeat_m: float | None = Field(
        default=None, ge=0,
        description="Раппорт обоев (высота рисунка), м. Только для обоев",
    )
    coats: int | None = Field(
        default=None, ge=1,
        description="Число слоёв краски. Только для покраски",
    )

    @field_validator("type")
    @classmethod
    def check_type(cls, v: str) -> str:
        allowed = {"tile", "paint", "wallpaper", "laminate"}
        if v not in allowed:
            raise ValueError(f"type должен быть одним из {sorted(allowed)}")
        return v


class CalculationRequest(BaseModel):
    """Тело POST-запроса: список работ по помещению."""
    works: list[WorkItem] = Field(min_length=1, max_length=20)


class ProductOffer(BaseModel):
    """Один товар-вариант для работы."""
    product_id: int
    name: str
    brand_hint: str | None = None      # появится после ML-матчинга
    packages: int                      # сколько упаковок купить
    package_price: float               # цена одной упаковки
    total_price: float                 # packages * package_price
    rating: float | None = None
    in_stock: bool


class WorkResult(BaseModel):
    """Результат расчёта по одной работе."""
    type: str
    area_m2: float
    options: list[ProductOffer]        # 3 варианта: дешёвый, средний, топ по рейтингу


class CalculationResponse(BaseModel):
    """Ответ: смета по всем работам + итог."""
    works: list[WorkResult]
    grand_total: float                 # сумма по самым дешёвым вариантам
