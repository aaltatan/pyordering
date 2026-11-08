# pyordering

Sort orders as composable values. `~stars() >> price() >> name()` is an `Ordering`: keys
applied left to right that sort lists in memory, compile from JSON, and render to
SQLAlchemy or Django `order_by` clauses.

```python
best_first = ~stars() >> price() >> name()

best_first(products)  # a new sorted list

select(Product).order_by(*best_first.clauses(Product, render))  # SQLAlchemy

Product.objects.order_by(*best_first.clauses(Product, render))  # Django

compiler.compile([{"name": "stars", "descending": True}, {"name": "price"}])  # from JSON
```

| Piece | What it does |
| --- | --- |
| [`key`](#quick-start) | Turns a `(subject, ...) -> sort value` function into a factory of one-key orderings |
| [`Ordering`](#composing-orderings) | Callable: returns a new sorted list. Composes with `>>`, flips with `~`, sets `nulls` |
| [`OrderingRegistry`](#a-registry-is-the-whitelist) | The named keys a JSON ordering may use, and nothing else |
| [`OrderingCompiler`](#from-json) | Builds an `Ordering` from JSON, with errors that point at the JSON path |
| [`get_ordering_json_schema`](#json-schema) | The JSON Schema of that JSON, generated from the key signatures |
| [`Ordering.clauses`](#sqlalchemy) | ORM `order_by` clauses through a render function you choose; no ORM is imported |

It is part of a family of packages that wrap a callable in an immutable value with an
algebra: [pyspecification](https://github.com/aaltatan/pyspecification) (`T -> bool`),
[pyformula](https://github.com/aaltatan/pyformula) (`T -> number`),
[pyflowstep](https://github.com/aaltatan/pyflowstep) (`T -> T`), and pyordering (`T -> sort key`).

## Installation

```bash
pip install pyordering
```

or with uv:

```bash
uv add pyordering
```

Python 3.12+. The only runtime dependency is
[pyvocabulary](https://github.com/aaltatan/pyvocabulary). SQLAlchemy and Django are optional:
pyordering never imports them.

## Quick start

The examples build on each other. A comment under a line shows its result.

A *key function* takes the subject and returns what to sort by. `@key` turns it into a factory:
calling the factory returns a one-key `Ordering`.

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


@key
def price(product: Product) -> Decimal:
    return product.price


@key
def name(product: Product) -> str:
    return product.name


by_price = price() >> name()

by_price
# Ordering(price >> name)

[p.name for p in by_price(products)]
# ['mixer', 'toaster', 'blender', 'kettle', 'grill']
```

Calling an ordering never changes its input: it takes any iterable and returns a new list.

## Composing orderings

`>>` appends keys: later keys break ties left by earlier ones. `~` flips the direction of every
key. Directions can be mixed freely, for strings and dates too, because each key is a separate
stable sort pass, run from the last key to the first.

```python
@key
def released(product: Product) -> date:
    return product.released


newest = ~released()

[p.name for p in newest(products)]
# ['grill', 'blender', 'kettle', 'toaster', 'mixer']

expensive_then_alphabetical = ~price() >> name()

[p.name for p in expensive_then_alphabetical(products)]
# ['grill', 'blender', 'kettle', 'mixer', 'toaster']

~expensive_then_alphabetical
# Ordering(price >> ~name)
```

Orderings are frozen dataclasses: every operator returns a new value, so a base ordering can be
shared and extended safely.

### Nulls

`None` values do not compare with anything, so each key decides where they go: `"last"` by
default, in both directions, or `"first"`. `~` keeps that choice, because whoever set it chose
where nulls go on purpose.

```python
@key
def stars(product: Product) -> int | None:
    return product.stars


[(p.name, p.stars) for p in (~stars() >> name())(products)]
# [('blender', 5), ('kettle', 4), ('mixer', 4), ('grill', None), ('toaster', None)]

unrated_first = stars().nulls("first") >> name()

unrated_first
# Ordering(stars nulls first >> name)

[(p.name, p.stars) for p in unrated_first(products)]
# [('grill', None), ('toaster', None), ('kettle', 4), ('mixer', 4), ('blender', 5)]

~unrated_first
# Ordering(~stars nulls first >> ~name)
```

`nulls()` applies to every key of the ordering it is called on, so call it on the single key
you mean, before composing. An invalid value fails right away:

```python
stars().nulls("middle")
# raises InvalidKeyError: Invalid nulls 'middle'. Valid values: first, last
```

### Keys with arguments

Parameters after the subject become arguments of the factory. They are bound when the ordering
is built, so a wrong argument fails then, not halfway through a sort.

```python
@key
def closest_to(product: Product, budget: int, *, penalty_over: int = 1) -> Decimal:
    """Sort by distance from a budget; going over it can cost more."""
    difference = product.price - budget

    return difference * penalty_over if difference > 0 else -difference


[p.name for p in (closest_to(28, penalty_over=3) >> name())(products)]
# ['mixer', 'toaster', 'blender', 'kettle', 'grill']

closest_to(budget="28", unknown=1)
# raises KeyArgumentError: Key 'closest_to' got invalid arguments: got an unexpected keyword argument 'unknown'
```

### Pagination needs a unique last key

Pages are only stable when no two rows tie on the whole ordering. Otherwise the database (or
the input order) decides ties, and rows can repeat or vanish between pages. End every paginated
ordering with a unique key, usually the id:

```python
@key
def product_id(product: Product) -> int:
    return product.id


paginated = ~stars() >> price() >> product_id()

pages = [paginated(products)[start : start + 2] for start in (0, 2, 4)]

[[p.id for p in page] for page in pages]
# [[3, 4], [1, 2], [5]]
```

## A registry is the whitelist

An `OrderingRegistry` collects named keys. Its visible keys are exactly what the compiler and the
JSON Schema accept, so a client can never sort by a field you did not register.

```python
from pyordering import OrderingRegistry

registry = OrderingRegistry[Product]()

for function in (price, name, stars, released):
    registry.register(function.__wrapped__)


@registry.key(name="id")
def product_id(product: Product) -> int:
    """The unique tie-breaker for pagination."""
    return product.id


registry.register(closest_to.__wrapped__)

list(registry)
# ['price', 'name', 'stars', 'released', 'id', 'closest_to']

registry["stars"]() >> registry["id"]()
# Ordering(stars >> id)
```

`@registry.key()` takes `name`, `description` (overrides the docstring in the JSON Schema) and
`hidden=True` (usable from Python, invisible to the compiler and the schema). Names must be
Python identifiers, and each one can be registered once:

```python
registry["rating"]
# raises KeyDoesNotExistError: Key 'rating' does not exist. Available keys: price, name, stars, released, id, closest_to
```

## From JSON

A JSON ordering is a list of key objects: `name`, and optionally `descending`, `nulls`, `args`
and `kwargs`.

```python
from pyordering import OrderingCompiler

compiler = OrderingCompiler(registry.keys)

ordering = compiler.compile(
    [
        {"name": "stars", "descending": True, "nulls": "first"},
        {"name": "closest_to", "args": [28], "kwargs": {"penalty_over": 3}},
        {"name": "id"},
    ]
)

ordering
# Ordering(~stars nulls first >> closest_to >> id)

[p.name for p in ordering(products)]
# ['toaster', 'grill', 'blender', 'mixer', 'kettle']
```

Every problem is reported while compiling, before anything is sorted. The error keeps its type
and gets a note with the JSON path:

```python
compiler.compile([{"name": "price"}, {"name": "rating"}])
# raises KeyDoesNotExistError: Key 'rating' does not exist. Available keys: price, name, stars, released, id, closest_to
# at $[1].name

compiler.compile([{"name": "price", "direction": "desc"}])
# raises InvalidOrderingDefinitionError: Invalid ordering at $[0]: unknown 'direction'. Allowed keys: args, descending, kwargs, name, nulls

compiler.compile([{"name": "closest_to"}])
# raises KeyArgumentError: Key 'closest_to' got invalid arguments: missing a required argument: 'budget'
# at $[0]
```

All of them derive from `PyorderingError`.

### A `?sort=` query parameter

pyordering does not parse query strings, but a common shape (`?sort=-stars,price`) maps onto the
JSON in one comprehension, and the registry still decides what is allowed:

```python
def parse_sort(value: str) -> list[dict[str, object]]:
    return [
        {"name": field.removeprefix("-"), "descending": field.startswith("-")}
        for field in value.split(",")
        if field
    ]


compiler.compile(parse_sort("-stars,price") + [{"name": "id"}])
# Ordering(~stars >> price >> id)
```

## JSON Schema

`get_ordering_json_schema` describes exactly what the compiler accepts, generated from the key
signatures and docstrings. Hand it to a form builder, an OpenAPI spec, or an LLM that writes sort
orders.

```python
from pyordering import get_ordering_json_schema

schema = get_ordering_json_schema(registry.keys)

schema["type"], [item["properties"]["name"]["const"] for item in schema["items"]["oneOf"]]
# ('array', ['price', 'name', 'stars', 'released', 'id', 'closest_to'])

closest = schema["items"]["oneOf"][-1]

closest["description"]
# 'Sort by distance from a budget; going over it can cost more.'

closest["properties"]["args"]["prefixItems"]
# [{'type': 'integer'}]

closest["properties"]["kwargs"]["properties"]
# {'budget': {'type': 'integer'}, 'penalty_over': {'type': 'integer', 'default': 1}}

closest["properties"]["descending"], closest["properties"]["nulls"]
# ({'type': 'boolean', 'default': False}, {'enum': ['first', 'last'], 'type': 'string', 'default': 'last'})
```

## SQLAlchemy

`ordering.clauses(subject, render)` calls each key function with `subject` and passes the result
to `render(expression, descending, nulls)`. With the model *class* as the subject, a key like
`product.price` returns the `Product.price` column, so **the same registry sorts dataclasses,
loaded rows, and SQL queries**. pyordering imports no ORM; the render function is yours.

```python
from sqlalchemy import Date, Numeric, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class ProductRow(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    stars: Mapped[int | None]
    released: Mapped[date] = mapped_column(Date)


def sqlalchemy_render(column, descending, nulls):
    clause = column.desc() if descending else column.asc()

    return clause.nulls_first() if nulls == "first" else clause.nulls_last()


engine = create_engine("sqlite://")

Base.metadata.create_all(engine)

with Session(engine) as session:
    session.add_all(ProductRow(**vars(p)) for p in products)

    session.commit()

best_first = compiler.compile(
    [{"name": "stars", "descending": True}, {"name": "price"}, {"name": "id"}]
)

query = select(ProductRow).order_by(*best_first.clauses(ProductRow, sqlalchemy_render))

print(query)
# SELECT products.id, products.name, products.price, products.stars, products.released
# FROM products ORDER BY products.stars DESC NULLS LAST, products.price ASC NULLS LAST, products.id ASC NULLS LAST

with Session(engine) as session:
    rows = session.scalars(query).all()

[row.name for row in rows]
# ['blender', 'mixer', 'kettle', 'toaster', 'grill']
```

The database and memory agree, and the same ordering sorts the loaded rows too:

```python
[row.name for row in best_first(rows)] == [p.name for p in best_first(products)] == [
    row.name for row in rows
]
# True
```

A key can return any column expression, such as `func.lower(subject.name)`, as long as the
expression also works on an instance when you sort in memory, or you only use it for queries.

### MySQL

MySQL has no `NULLS FIRST/LAST`. It sorts `NULL` as the smallest value, so the render function
returns two clauses per key, the first one sorting by "is null", and `clauses` flattens them:

```python
from sqlalchemy.dialects import mysql


def mysql_render(column, descending, nulls):
    is_null = column.is_(None) if nulls == "last" else column.is_not(None)

    return is_null, column.desc() if descending else column.asc()


query = select(ProductRow.id).order_by(*best_first.clauses(ProductRow, mysql_render))

print(query.compile(dialect=mysql.dialect()))
# SELECT products.id
# FROM products ORDER BY products.stars IS NULL, products.stars DESC, products.price IS NULL, products.price ASC, products.id IS NULL, products.id ASC
```

## Django

The same idea with Django: on the model class, `product.price` is a field descriptor, which the
render function turns into an `F` expression. Expressions you return yourself, like
`Lower("name")`, pass through unchanged.

The settings and table creation below stand in for a Django project, so the example runs on its
own. In a project, the model lives in your app's `models.py`.

```python
import django
from django.conf import settings

settings.configure(
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
)

django.setup()

from django.db import connection, models


class ProductModel(models.Model):
    name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stars = models.IntegerField(null=True)
    released = models.DateField()

    class Meta:
        app_label = "shop"


with connection.schema_editor() as editor:
    editor.create_model(ProductModel)

ProductModel.objects.bulk_create(ProductModel(**vars(p)) for p in products)
```

The render function:

```python
from django.db.models import F
from django.db.models.query_utils import DeferredAttribute


def django_render(expression, descending, nulls):
    if isinstance(expression, DeferredAttribute):  # `Product.price` on the class
        expression = F(expression.field.name)

    order = expression.desc if descending else expression.asc

    return order(nulls_first=nulls == "first" or None, nulls_last=nulls == "last" or None)


unrated_first = compiler.compile([{"name": "stars", "nulls": "first"}, {"name": "id"}])

queryset = ProductModel.objects.order_by(*unrated_first.clauses(ProductModel, django_render))

print(queryset.query)
# SELECT ... FROM "shop_productmodel" ORDER BY "shop_productmodel"."stars" ASC NULLS FIRST, "shop_productmodel"."id" ASC NULLS LAST

[product.name for product in queryset]
# ['toaster', 'grill', 'kettle', 'mixer', 'blender']

[p.name for p in unrated_first(products)]
# ['toaster', 'grill', 'kettle', 'mixer', 'blender']
```

Django emulates `NULLS FIRST/LAST` on MySQL by itself, so this render function works there
unchanged.

In a view, the whitelist and the JSON paths do the validation:

```python
from django.http import HttpRequest, JsonResponse

from pyordering import PyorderingError


def products(request: HttpRequest) -> JsonResponse:
    try:
        ordering = compiler.compile(parse_sort(request.GET.get("sort", "")) + [{"name": "id"}])
    except PyorderingError as error:
        return JsonResponse(
            {"error": str(error), "notes": getattr(error, "__notes__", [])}, status=400
        )

    queryset = ProductModel.objects.order_by(*ordering.clauses(ProductModel, django_render))

    return JsonResponse({"products": list(queryset.values("id", "name"))})
```

## Reference

```python
Ordering(keys: tuple[Key[T], ...])
    ordering(items)                  # -> list[T], a new sorted list
    ordering >> other                # -> Ordering[T], keys of both
    ~ordering                        # -> Ordering[T], every direction flipped, nulls kept
    ordering.nulls("first" | "last") # -> Ordering[T], nulls set on every key
    ordering.clauses(subject, render) # -> tuple of clauses; render(expression, descending, nulls)

Key(name, value, descending=False, nulls="last")

key(fn, /, *, name=None)            # -> factory(*args, **kwargs) -> Ordering[T]
OrderingRegistry[T]()               # .key(name=, description=, hidden=), .register(fn, ...), .keys
OrderingCompiler(keys).compile([...])
get_ordering_json_schema(keys)
```

Exceptions, all subclasses of `PyorderingError`: `InvalidKeyError` (bad key function or `nulls`),
`KeyArgumentError` (arguments the key function does not accept), `InvalidOrderingDefinitionError`
(wrong JSON shape), `KeyDoesNotExistError`, `KeyAlreadyRegisteredError`, `InvalidKeyNameError`.

## License

GPL-3.0-only.
