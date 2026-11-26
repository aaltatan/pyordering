# Compiling orderings from JSON

A sort order often arrives as data: a `?sort=` query parameter, a saved view, a column a user
clicked. `OrderingCompiler` turns that data into an `Ordering`, using only the keys of a
[registry](registries.md).

```python
from dataclasses import dataclass
from decimal import Decimal

from pyordering import OrderingCompiler, OrderingRegistry


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
def price(product: Product) -> Decimal:
    return product.price


@registry.key()
def stars(product: Product) -> int | None:
    return product.stars


@registry.key(name="id")
def product_id(product: Product) -> int:
    return product.id


@registry.key()
def closest_to(product: Product, budget: int, *, penalty_over: int = 1) -> Decimal:
    """Sort by distance from a budget; going over it can cost more."""
    difference = product.price - budget

    return difference * penalty_over if difference > 0 else -difference


compiler = OrderingCompiler(registry.keys)
```

## The JSON shape

A JSON ordering is a list of key objects. Only `name` is required:

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `name` | string | — | a registered key |
| `descending` | boolean | `false` | sort this key in reverse |
| `nulls` | `"first"` or `"last"` | `"last"` | where `None` values go |
| `args` | list | `[]` | positional arguments of the key function |
| `kwargs` | object | `{}` | keyword arguments of the key function |

```python
ordering = compiler.compile(
    [
        {"name": "stars", "descending": True, "nulls": "first"},
        {"name": "closest_to", "args": [28], "kwargs": {"penalty_over": 3}},
        {"name": "id"},
    ]
)

assert repr(ordering) == "Ordering(~stars nulls first >> closest_to >> id)"
assert [p.name for p in ordering(products)] == ["toaster", "grill", "blender", "mixer", "kettle"]
```

The compiled ordering is an ordinary `Ordering`: you can extend it with `>>`, flip it with `~`,
or [render it for an ORM](orms.md).

```python
assert repr(compiler.compile([{"name": "price"}]) >> product_id()) == "Ordering(price >> id)"
```

## Errors point at the JSON path

Every problem is reported while compiling, before anything is sorted. The error keeps its
type and gets a note with the JSON path of the mistake, so an API can send it back to the
client as it is.

```python
from pyordering import KeyArgumentError, KeyDoesNotExistError

try:
    compiler.compile([{"name": "price"}, {"name": "rating"}])
except KeyDoesNotExistError as error:
    assert str(error) == "Key 'rating' does not exist. Available keys: price, stars, id, closest_to"
    assert error.__notes__ == ["at $[1].name"]

try:
    compiler.compile([{"name": "closest_to"}])
except KeyArgumentError as error:
    assert str(error) == (
        "Key 'closest_to' got invalid arguments: missing a required argument: 'budget'"
    )
    assert error.__notes__ == ["at $[0]"]
```

A definition of the wrong shape raises `InvalidOrderingDefinitionError`, with the path in the
message:

```python
from pyordering import InvalidOrderingDefinitionError

try:
    compiler.compile([{"name": "price", "direction": "desc"}])
except InvalidOrderingDefinitionError as error:
    assert str(error) == (
        "Invalid ordering at $[0]: unknown 'direction'. "
        "Allowed keys: args, descending, kwargs, name, nulls"
    )

try:
    compiler.compile({"name": "price"})
except InvalidOrderingDefinitionError as error:
    assert str(error).startswith("Invalid ordering at $: expected a list")
```

All of them derive from `PyorderingError`, so one `except` catches every client mistake. See
[Exceptions](../reference/exceptions.md) for the full list.

## A `?sort=` query parameter

pyordering does not parse query strings, but a common shape (`?sort=-stars,price`) maps onto
the JSON in one comprehension, and the registry still decides what is allowed:

```python
def parse_sort(value: str) -> list[dict[str, object]]:
    return [
        {"name": field.removeprefix("-"), "descending": field.startswith("-")}
        for field in value.split(",")
        if field
    ]


ordering = compiler.compile(parse_sort("-stars,price") + [{"name": "id"}])

assert repr(ordering) == "Ordering(~stars >> price >> id)"
```

Appending `{"name": "id"}` on the server makes every page stable, whatever the client asked
for (see [pagination](orderings.md#pagination-needs-a-unique-last-key)).
