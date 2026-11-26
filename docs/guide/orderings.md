# Keys and orderings

The examples on this page build on each other. They all sort these products:

```python
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from pyordering import key


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    price: Decimal
    stars: int | None
    released: date


products = [
    Product(1, "kettle", Decimal("30.00"), 4, date(2024, 3, 1)),
    Product(2, "toaster", Decimal("25.00"), None, date(2023, 6, 1)),
    Product(3, "blender", Decimal("30.00"), 5, date(2025, 1, 1)),
    Product(4, "mixer", Decimal("25.00"), 4, date(2022, 9, 1)),
    Product(5, "grill", Decimal("80.00"), None, date(2025, 5, 1)),
]


def names(items: list[Product]) -> list[str]:
    return [p.name for p in items]
```

## Key functions and factories

A *key function* takes the subject and returns what to sort by. `@key` turns it into a
*key factory*: calling the factory returns a one-key `Ordering`.

```python
@key
def price(product: Product) -> Decimal:
    return product.price


@key
def name(product: Product) -> str:
    return product.name


by_price = price() >> name()

assert repr(by_price) == "Ordering(price >> name)"
assert names(by_price(products)) == ["mixer", "toaster", "blender", "kettle", "grill"]
```

Calling an ordering never changes its input: it takes any iterable and returns a new list.

```python
shelf = tuple(products)

assert names(by_price(shelf))[0] == "mixer"
assert shelf[0].name == "kettle"
```

The key name shown in `repr` (and used in JSON) is the function name. Pass `name=` to
change it:

```python
@key
def product_id(product: Product) -> int:
    return product.id


identifier = key(product_id.__wrapped__, name="id")

assert repr(identifier()) == "Ordering(id)"
```

The key function must accept the subject as its first positional parameter, otherwise
`@key` fails right away with `InvalidKeyError`.

## Composing with `>>` and `~`

`>>` appends keys: later keys break ties left by earlier ones. `~` flips the direction of
every key.

```python
@key
def released(product: Product) -> date:
    return product.released


newest = ~released()

assert names(newest(products)) == ["grill", "blender", "kettle", "toaster", "mixer"]

expensive_then_alphabetical = ~price() >> name()

assert names(expensive_then_alphabetical(products)) == [
    "grill",
    "blender",
    "kettle",
    "mixer",
    "toaster",
]

assert repr(~expensive_then_alphabetical) == "Ordering(price >> ~name)"
```

Directions mix freely, for strings and dates too, because each key is a separate stable
sort pass, run from the last key to the first. You never have to negate a value to sort it
descending.

!!! tip "Orderings are values"
    `Ordering` is a frozen dataclass. `>>`, `~` and `nulls()` all return new orderings, so
    a base ordering can be shared between views and extended in each one.

## Where `None` goes

`None` does not compare with anything, so each key decides where missing values go:
`"last"` by default, in both directions, or `"first"`.

```python
@key
def stars(product: Product) -> int | None:
    return product.stars


best_rated = ~stars() >> name()

assert [(p.name, p.stars) for p in best_rated(products)] == [
    ("blender", 5),
    ("kettle", 4),
    ("mixer", 4),
    ("grill", None),
    ("toaster", None),
]

unrated_first = stars().nulls("first") >> name()

assert repr(unrated_first) == "Ordering(stars nulls first >> name)"
assert names(unrated_first(products)) == ["grill", "toaster", "kettle", "mixer", "blender"]
```

`~` keeps the `nulls` choice, because whoever set it chose where nulls go on purpose:

```python
assert repr(~unrated_first) == "Ordering(~stars nulls first >> ~name)"
```

`nulls()` applies to **every** key of the ordering it is called on, so call it on the single
key you mean, before composing. An invalid value fails right away:

```python
from pyordering import InvalidKeyError

try:
    stars().nulls("middle")
except InvalidKeyError as error:
    assert str(error) == "Invalid nulls 'middle'. Valid values: first, last"
```

## Keys with arguments

Parameters after the subject become arguments of the factory. They are bound when the
ordering is built, so a wrong argument fails then, not halfway through a sort.

```python
@key
def closest_to(product: Product, budget: int, *, penalty_over: int = 1) -> Decimal:
    """Sort by distance from a budget; going over it can cost more."""
    difference = product.price - budget

    return difference * penalty_over if difference > 0 else -difference


near_28 = closest_to(28, penalty_over=3) >> name()

assert names(near_28(products)) == ["mixer", "toaster", "blender", "kettle", "grill"]
```

```python
from pyordering import KeyArgumentError

try:
    closest_to(budget=28, unknown=1)
except KeyArgumentError as error:
    assert str(error) == (
        "Key 'closest_to' got invalid arguments: got an unexpected keyword argument 'unknown'"
    )
```

The factory's signature is the key function's parameters without the subject, so
`inspect.signature` (and the [JSON Schema](json-schema.md)) shows what the factory takes:

```python
from inspect import signature

assert str(signature(closest_to)) == "(budget: int, *, penalty_over: int = 1)"
```

## Pagination needs a unique last key

Pages are only stable when no two items tie on the whole ordering. Otherwise the database
(or the input order) decides ties, and items can repeat or vanish between pages. End every
paginated ordering with a unique key, usually the id:

```python
paginated = ~stars() >> price() >> product_id()

pages = [paginated(products)[start : start + 2] for start in (0, 2, 4)]

assert [[p.id for p in page] for page in pages] == [[3, 4], [1, 2], [5]]
```

## Looking inside an ordering

An ordering is a tuple of `Key` values, each with its `name`, `descending` and `nulls`.
That is handy for showing the current sort in a UI:

```python
assert [(k.name, k.descending, k.nulls) for k in unrated_first.keys] == [
    ("stars", False, "first"),
    ("name", False, "last"),
]
```
