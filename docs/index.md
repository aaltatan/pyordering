# pyordering

**Sort orders as small, composable values.**

Name each thing you sort by once (`price`, `stars`, `name`) and combine them with `>>` and `~`.
The result is an `Ordering`: it sorts lists in memory, compiles from JSON a client sent, is
described by JSON Schema, and renders to SQLAlchemy or Django `order_by` clauses.

```py
best_first = ~stars() >> price() >> name()
```

## A first taste

A shop lists products by rating, best first, then by price, then by name.

```python
from dataclasses import dataclass
from decimal import Decimal

from pyordering import key


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
]


@key
def stars(product: Product) -> int | None:
    return product.stars


@key
def price(product: Product) -> Decimal:
    return product.price


@key
def name(product: Product) -> str:
    return product.name


best_first = ~stars() >> price() >> name()

assert repr(best_first) == "Ordering(~stars >> price >> name)"
assert [p.name for p in best_first(products)] == ["blender", "mixer", "kettle", "toaster"]
```

Each decorated function became a **key factory**: calling it returns a one-key `Ordering`.
`~` sorts descending, `>>` adds a tie-breaker, and `None` ratings go last unless you say
otherwise.

## Why pyordering

- **Mixed directions for any type.** Each key is its own stable sort pass, so "newest first,
  then alphabetical" works for dates and strings without negating anything.
- **`None` has a place.** Every key decides whether missing values go first or last.
- **A whitelist for client input.** A registry holds the keys a JSON ordering may use; a
  `?sort=rating` for a field you never registered fails with the JSON path of the mistake.
- **One ordering, three targets.** The same keys sort dataclasses, loaded rows and SQL
  queries. pyordering imports no ORM: you pass a small render function.
- **Fails early.** Wrong arguments and bad JSON are reported when the ordering is built,
  not halfway through a sort.

## Where next

- [Installation](install.md)
- [User guide](guide/index.md): every piece, with examples you can run.
- [Reference](reference/index.md): the API, the JSON format and the exceptions.

pyordering is part of a family of packages that wrap a callable in an immutable value with an
algebra: [pyspecification](https://github.com/aaltatan/pyspecification) (`T -> bool`),
[pyformula](https://github.com/aaltatan/pyformula) (`T -> number`),
[pyflowstep](https://github.com/aaltatan/pyflowstep) (`T -> T`), and pyordering
(`T -> sort key`).
