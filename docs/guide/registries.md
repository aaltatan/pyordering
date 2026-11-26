# Registries

An `OrderingRegistry` collects named keys. Its visible keys are exactly what the
[compiler](compiling.md) and the [JSON Schema](json-schema.md) accept, so a client can never
sort by a field you did not register.

```python
from dataclasses import dataclass
from decimal import Decimal

from pyordering import OrderingRegistry


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
]

registry = OrderingRegistry[Product]()


@registry.key()
def price(product: Product) -> Decimal:
    """Sort by price."""
    return product.price


@registry.key()
def stars(product: Product) -> int | None:
    """Sort by average rating."""
    return product.stars


@registry.key(name="id")
def product_id(product: Product) -> int:
    """The unique tie-breaker for pagination."""
    return product.id


assert list(registry) == ["price", "stars", "id"]
```

`@registry.key()` returns the key factory, so the decorated name works like any `@key`
factory, and the registry hands out the same factory by name:

```python
best_first = ~stars() >> registry["price"]() >> registry["id"]()

assert repr(best_first) == "Ordering(~stars >> price >> id)"
assert [p.id for p in best_first(products)] == [3, 1, 2]
```

## Options

`@registry.key()` and `registry.register()` take the same keyword arguments:

| Option | Default | Effect |
| --- | --- | --- |
| `name` | the function name | the name used in JSON, in `repr` and in lookups |
| `description` | the docstring | the description shown in the JSON Schema |
| `hidden` | `False` | usable from Python, invisible to lookups, the compiler and the schema |

`register()` is the plain-call form, handy for functions defined elsewhere:

```python
def name(product: Product) -> str:
    return product.name


registry.register(name, description="Sort alphabetically.")

assert "name" in registry
assert len(registry) == 4
```

A hidden key is for orderings you build in Python but do not want clients to request:

```python
@registry.key(hidden=True)
def internal_score(product: Product) -> int:
    return product.id * 7 % 5


assert "internal_score" not in registry
assert "internal_score" not in registry.keys
assert repr(internal_score()) == "Ordering(internal_score)"
```

## Mistakes fail when you register or look up

Names must be ASCII Python identifiers, and each one can be registered once. Looking up an
unknown name lists the names that do exist:

```python
from pyordering import InvalidKeyNameError, KeyAlreadyRegisteredError, KeyDoesNotExistError

try:
    registry["rating"]
except KeyDoesNotExistError as error:
    assert str(error) == "Key 'rating' does not exist. Available keys: price, stars, id, name"

try:
    registry.register(name)
except KeyAlreadyRegisteredError:
    pass
else:
    raise AssertionError("expected KeyAlreadyRegisteredError")

try:
    registry.register(name, name="sort-by")
except InvalidKeyNameError:
    pass
else:
    raise AssertionError("expected InvalidKeyNameError")
```

## `registry.keys`

`registry.keys` is a read-only mapping of every visible key factory by name. It is what you
pass to `OrderingCompiler` and `get_ordering_json_schema`, so both see the same whitelist:

```python
from pyordering import OrderingCompiler, get_ordering_json_schema

compiler = OrderingCompiler(registry.keys)
schema = get_ordering_json_schema(registry.keys)

assert list(registry.keys) == ["price", "stars", "id", "name"]
```

A plain `dict` of factories works too, if you would rather not use a registry:

```python
compiler = OrderingCompiler({"price": price, "id": product_id})
```
