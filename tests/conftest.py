from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest

from pyordering import Ordering, OrderingRegistry


@dataclass(frozen=True, slots=True)
class Product:
    id: int
    name: str
    price: Decimal
    stars: int | None
    released: date


PRODUCTS = (
    Product(1, "kettle", Decimal("30.00"), 4, date(2024, 3, 1)),
    Product(2, "toaster", Decimal("25.00"), None, date(2023, 6, 1)),
    Product(3, "blender", Decimal("30.00"), 5, date(2025, 1, 1)),
    Product(4, "mixer", Decimal("25.00"), 4, date(2022, 9, 1)),
    Product(5, "grill", Decimal("80.00"), None, date(2025, 5, 1)),
)


@pytest.fixture
def products() -> tuple[Product, ...]:
    return PRODUCTS


@pytest.fixture
def registry() -> OrderingRegistry[Product]:
    registry = OrderingRegistry[Product]()

    @registry.key()
    def price(product: Product) -> Decimal:
        """Sort by price."""
        return product.price

    @registry.key()
    def stars(product: Product) -> int | None:
        return product.stars

    @registry.key()
    def name(product: Product) -> str:
        return product.name

    @registry.key()
    def released(product: Product) -> date:
        return product.released

    @registry.key(name="id")
    def product_id(product: Product) -> int:
        return product.id

    @registry.key()
    def distance(product: Product, target: int, *, scale: int = 1) -> int:
        """Sort by how far the price is from a target."""
        return abs(int(product.price) - target) * scale

    return registry


def ids(products: list[Product]) -> list[int]:
    return [product.id for product in products]


def by(registry: OrderingRegistry[Product], name: str) -> Ordering[Product]:
    return registry[name]()
