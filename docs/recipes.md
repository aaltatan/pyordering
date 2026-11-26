# Recipes

Complete, runnable programs for common jobs. Each one is self-contained.

## A sortable table behind an API

A list endpoint takes `?sort=-stars,price`, sorts only by fields it allows, always ends
with the id so pages are stable, and answers a bad request with the JSON path of the
mistake.

```python
from dataclasses import dataclass
from decimal import Decimal

from pyordering import OrderingCompiler, OrderingRegistry, PyorderingError


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    price: Decimal
    stars: int | None


products = [
    Product(1, "kettle", Decimal("30.00"), 4),
    Product(2, "toaster", Decimal("25.00"), None),
    Product(3, "blender", Decimal("30.00"), 5),
    Product(4, "mixer", Decimal("25.00"), 4),
    Product(5, "grill", Decimal("80.00"), None),
]

registry = OrderingRegistry[Product]()


@registry.key()
def name(product: Product) -> str:
    return product.name


@registry.key()
def price(product: Product) -> Decimal:
    return product.price


@registry.key()
def stars(product: Product) -> int | None:
    return product.stars


@registry.key(name="id")
def product_id(product: Product) -> int:
    return product.id


compiler = OrderingCompiler(registry.keys)


def parse_sort(value: str) -> list[dict[str, object]]:
    return [
        {"name": field.removeprefix("-"), "descending": field.startswith("-")}
        for field in value.split(",")
        if field
    ]


def list_products(sort: str, page: int, size: int = 2) -> dict[str, object]:
    try:
        ordering = compiler.compile(parse_sort(sort) + [{"name": "id"}])
    except PyorderingError as error:
        return {"status": 400, "error": str(error), "notes": getattr(error, "__notes__", [])}

    rows = ordering(products)[page * size : (page + 1) * size]

    return {"status": 200, "ids": [p.id for p in rows]}


assert list_products("-stars,price", page=0) == {"status": 200, "ids": [3, 4]}
assert list_products("-stars,price", page=1) == {"status": 200, "ids": [1, 2]}
assert list_products("-stars,price", page=2) == {"status": 200, "ids": [5]}

assert list_products("-rating", page=0) == {
    "status": 400,
    "error": "Key 'rating' does not exist. Available keys: name, price, stars, id",
    "notes": ["at $[0].name"],
}
```

## Clicking a column header

A table UI keeps the current ordering and changes it when a header is clicked: the same
column again flips it, another column becomes the primary sort and the old one the
tie-breaker. The UI state is just the JSON list, so it can live in a URL or a saved view.

```python
from pyordering import OrderingRegistry, OrderingCompiler

registry = OrderingRegistry[dict[str, object]]()


@registry.key()
def title(row: dict[str, object]) -> str:
    return str(row["title"])


@registry.key()
def year(row: dict[str, object]) -> int:
    return int(row["year"])


compiler = OrderingCompiler(registry.keys)

books = [
    {"title": "Dune", "year": 1965},
    {"title": "Emma", "year": 1815},
    {"title": "Ubik", "year": 1969},
    {"title": "Beloved", "year": 1987},
]


def click(state: list[dict[str, object]], column: str) -> list[dict[str, object]]:
    if state and state[0]["name"] == column:
        return [{**state[0], "descending": not state[0].get("descending", False)}, *state[1:]]

    rest = [item for item in state if item["name"] != column]

    return [{"name": column}, *rest]


state: list[dict[str, object]] = []

state = click(state, "year")
assert [b["title"] for b in compiler.compile(state)(books)] == ["Emma", "Dune", "Ubik", "Beloved"]

state = click(state, "year")
assert repr(compiler.compile(state)) == "Ordering(~year)"

state = click(state, "title")
assert repr(compiler.compile(state)) == "Ordering(title >> ~year)"
assert [b["title"] for b in compiler.compile(state)(books)] == ["Beloved", "Dune", "Emma", "Ubik"]
```

The keys of a compiled ordering say how to draw the arrows in the headers:

```python
arrows = {k.name: "▼" if k.descending else "▲" for k in compiler.compile(state).keys}

assert arrows == {"title": "▲", "year": "▼"}
```

## Case-insensitive and computed keys

A key returns anything comparable, so normalising text or sorting by a computed value is
an ordinary key function. Parameters make one key serve many sorts.

```python
from datetime import date

from pyordering import key


@key
def surname(person: dict[str, str]) -> str:
    return person["name"].split()[-1].casefold()


@key
def days_until_birthday(person: dict[str, str], today: date) -> int:
    born = date.fromisoformat(person["born"])

    upcoming = born.replace(year=today.year)

    if upcoming < today:
        upcoming = upcoming.replace(year=today.year + 1)

    return (upcoming - today).days


people = [
    {"name": "ada lovelace", "born": "1815-12-10"},
    {"name": "Alan Turing", "born": "1912-06-23"},
    {"name": "grace Hopper", "born": "1906-12-09"},
]

assert [p["name"] for p in surname()(people)] == ["grace Hopper", "ada lovelace", "Alan Turing"]

soonest = days_until_birthday(date(2026, 11, 26)) >> surname()

assert [p["name"] for p in soonest(people)] == ["grace Hopper", "ada lovelace", "Alan Turing"]
```

## One registry for memory and SQL

Key functions that only read attributes work on instances and on SQLAlchemy model classes,
so a single registry serves both. See [SQLAlchemy and Django](guide/orms.md) for the full
setup, including MySQL and Django render functions.

```python
from decimal import Decimal

from sqlalchemy import Numeric, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from pyordering import OrderingRegistry


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))


items = OrderingRegistry[Item]()


@items.key()
def price(item: Item) -> Decimal:
    return item.price


@items.key(name="id")
def item_id(item: Item) -> int:
    return item.id


def render(column, descending, nulls):
    clause = column.desc() if descending else column.asc()

    return clause.nulls_first() if nulls == "first" else clause.nulls_last()


cheapest = price() >> item_id()

in_memory = cheapest([Item(id=2, name="b", price=Decimal(5)), Item(id=1, name="a", price=Decimal(5))])

assert [i.id for i in in_memory] == [1, 2]
assert str(select(Item).order_by(*cheapest.clauses(Item, render))).endswith(
    "ORDER BY items.price ASC NULLS LAST, items.id ASC NULLS LAST"
)
```
