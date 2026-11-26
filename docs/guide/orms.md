# SQLAlchemy and Django

`ordering.clauses(subject, render)` calls each key function with `subject` and hands the
result to `render(expression, descending, nulls)`. With the model **class** as the subject, a
key like `product.price` returns the `Product.price` column, so the same keys sort
dataclasses, loaded rows and SQL queries.

pyordering imports no ORM. The render function is yours, and it is a few lines long.

```python
from pyordering import key


class Table:
    name = "name_column"


@key
def name(subject) -> str:
    return subject.name


def render(column, descending, nulls):
    return f"{column} {'DESC' if descending else 'ASC'} NULLS {nulls.upper()}"


assert (~name()).clauses(Table, render) == ("name_column DESC NULLS LAST",)
```

`render` may return one clause or a tuple of clauses; tuples are flattened, for databases
that need two clauses per key (see [MySQL](#mysql)).

## SQLAlchemy

The examples below share these products and keys:

```python
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from pyordering import OrderingCompiler, OrderingRegistry


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


compiler = OrderingCompiler(registry.keys)
```

A model with the same attribute names, and a render function:

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
```

Compile an ordering once and use it for the query:

```python
best_first = compiler.compile(
    [{"name": "stars", "descending": True}, {"name": "price"}, {"name": "id"}]
)

query = select(ProductRow).order_by(*best_first.clauses(ProductRow, sqlalchemy_render))

assert str(query).endswith(
    "ORDER BY products.stars DESC NULLS LAST, products.price ASC NULLS LAST, "
    "products.id ASC NULLS LAST"
)

with Session(engine) as session:
    rows = session.scalars(query).all()

assert [row.name for row in rows] == ["blender", "mixer", "kettle", "toaster", "grill"]
```

The database and memory agree, and the same ordering sorts the loaded rows too:

```python
assert [p.name for p in best_first(products)] == [row.name for row in rows]
assert [row.name for row in best_first(rows)] == [row.name for row in rows]
```

A key can return any column expression, such as `func.lower(subject.name)`, as long as the
expression also works on an instance when you sort in memory, or you only use it for
queries.

### MySQL

MySQL has no `NULLS FIRST/LAST`. It sorts `NULL` as the smallest value, so the render
function returns two clauses per key, the first one sorting by "is null", and `clauses`
flattens them:

```python
from sqlalchemy.dialects import mysql


def mysql_render(column, descending, nulls):
    is_null = column.is_(None) if nulls == "last" else column.is_not(None)

    return is_null, column.desc() if descending else column.asc()


query = select(ProductRow.id).order_by(*best_first.clauses(ProductRow, mysql_render))

assert str(query.compile(dialect=mysql.dialect())).endswith(
    "ORDER BY products.stars IS NULL, products.stars DESC, "
    "products.price IS NULL, products.price ASC, products.id IS NULL, products.id ASC"
)
```

## Django

The same idea with Django: on the model class, `product.price` is a field descriptor, which
the render function turns into an `F` expression. Expressions you return yourself, like
`Lower("name")`, pass through unchanged.

The settings and table creation below stand in for a Django project, so the example runs
on its own. In a project, the model lives in your app's `models.py`.

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

assert str(queryset.query).endswith(
    'ORDER BY "shop_productmodel"."stars" ASC NULLS FIRST, "shop_productmodel"."id" ASC NULLS LAST'
)

assert [product.name for product in queryset] == ["toaster", "grill", "kettle", "mixer", "blender"]
assert [p.name for p in unrated_first(products)] == [p.name for p in queryset]
```

Django emulates `NULLS FIRST/LAST` on MySQL by itself, so this render function works there
unchanged.

In a view, the whitelist and the JSON paths do the validation (`parse_sort` is the helper
from [Compiling](compiling.md#a-sort-query-parameter)):

```py
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
