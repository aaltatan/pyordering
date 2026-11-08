"""Sort orders as values: `~stars() >> price() >> name()`.

A *key function* takes the subject first, then its own arguments, and returns
what to sort by. `@key` turns it into a *key factory*: calling the factory binds
the arguments and returns a one-key `Ordering`, ready to compose.

```python
@key
def price(product: Product) -> Decimal:
    return product.price

ordering = ~stars() >> price()  # stars descending, then price ascending
ordering(products)  # a new, sorted list
```

The same key function works for ORMs when the subject is the model class:
`price(Product)` returns the `Product.price` column, and `Ordering.clauses`
hands it to a render function that builds the `order_by` clause.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from functools import reduce, wraps
from inspect import Parameter, Signature, signature
from operator import itemgetter
from typing import Any, Concatenate, Literal, cast, get_args

from .exceptions import InvalidKeyError, KeyArgumentError

type Nulls = Literal["first", "last"]
type KeyFn[T, **P] = Callable[Concatenate[T, P], Any]
type KeyFactory[T, **P] = Callable[P, Ordering[T]]
type Render[C] = Callable[[Any, bool, Nulls], C | tuple[C, ...]]

NULLS: tuple[Nulls, ...] = get_args(Nulls.__value__)


@dataclass(frozen=True, slots=True)
class Key[T]:
    """One sort key: what to sort by, the direction, and where `None` values go."""

    name: str
    value: Callable[[T], Any]
    descending: bool = False
    nulls: Nulls = "last"

    def __post_init__(self) -> None:
        if self.nulls not in NULLS:
            msg = f"Invalid nulls {self.nulls!r}. Valid values: {', '.join(NULLS)}"
            raise InvalidKeyError(msg)

    def __str__(self) -> str:
        direction = "~" if self.descending else ""
        nulls = " nulls first" if self.nulls == "first" else ""
        return f"{direction}{self.name}{nulls}"


@dataclass(frozen=True, slots=True)
class Ordering[T]:
    """Keys applied left to right. Calling it returns a new sorted list.

    Each key is a stable sort pass, run from the last key to the first, so
    directions can be mixed for any comparable type, strings and dates included.

    Example:
    ```python
    >>> @key
    ... def length(word: str) -> int:
    ...     return len(word)
    >>> @key
    ... def alphabetical(word: str) -> str:
    ...     return word
    >>> ordering = ~length() >> alphabetical()
    >>> ordering
    Ordering(~length >> alphabetical)
    >>> ordering(["fig", "apple", "kiwi", "plum", "date"])
    ['apple', 'date', 'kiwi', 'plum', 'fig']
    >>> (~ordering)(["fig", "apple", "kiwi", "plum", "date"])
    ['fig', 'plum', 'kiwi', 'date', 'apple']

    ```

    """

    keys: tuple[Key[T], ...]

    def __call__(self, items: Iterable[T], /) -> list[T]:
        return reduce(_sort_by, reversed(self.keys), list(items))

    def __rshift__(self, other: "Ordering[T]", /) -> "Ordering[T]":
        match other:
            case Ordering(keys=keys):
                return Ordering((*self.keys, *keys))
            case _:
                return NotImplemented

    def __invert__(self) -> "Ordering[T]":
        # `nulls` is kept: whoever set it chose where nulls go on purpose.
        return Ordering(tuple(replace(k, descending=not k.descending) for k in self.keys))

    def nulls(self, where: Nulls, /) -> "Ordering[T]":
        """Return a copy where `None` values of every key sort `"first"` or `"last"`.

        Example:
        ```python
        >>> @key
        ... def rank(item: dict[str, int | None]) -> int | None:
        ...     return item["rank"]
        >>> items = [{"rank": 2}, {"rank": None}, {"rank": 1}]
        >>> rank()(items)
        [{'rank': 1}, {'rank': 2}, {'rank': None}]
        >>> rank().nulls("first")(items)
        [{'rank': None}, {'rank': 1}, {'rank': 2}]

        ```

        """
        return Ordering(tuple(replace(k, nulls=where) for k in self.keys))

    def clauses[C](self, subject: object, render: Render[C], /) -> tuple[C, ...]:
        """Return ORM `order_by` clauses, one or more per key.

        Each key function is called with `subject` (usually the model class, so
        it returns a column) and the result goes to `render(expression,
        descending, nulls)`. A tuple returned by `render` is flattened, for
        databases without `NULLS FIRST/LAST` that need two clauses per key.

        Example:
        ```python
        >>> class Table:
        ...     name = "name_column"
        >>> @key
        ... def name(subject) -> str:
        ...     return subject.name
        >>> render = lambda column, descending, nulls: f"{column} {'DESC' if descending else 'ASC'}"
        >>> (~name()).clauses(Table, render)
        ('name_column DESC',)

        ```

        """
        rendered = [
            # The key function is typed for instances; here it is given the model class.
            render(cast("Callable[[object], Any]", k.value)(subject), k.descending, k.nulls)
            for k in self.keys
        ]
        return tuple(
            clause
            for item in rendered
            for clause in (cast("tuple[C, ...]", item) if isinstance(item, tuple) else (item,))
        )

    def __repr__(self) -> str:
        return f"Ordering({' >> '.join(map(str, self.keys))})"


def key[T, **P](fn: KeyFn[T, P], /, *, name: str | None = None) -> KeyFactory[T, P]:
    """Turn a `(subject, *args, **kwargs) -> sort value` function into a key factory.

    Arguments are checked against the function signature when the factory is
    called, so a mistake fails while the ordering is built, not while it sorts.

    Args:
        fn: The key function; its first positional parameter receives the subject.
        name: The key name shown in `repr`; defaults to the function name.

    Raises:
        InvalidKeyError: If `fn` does not accept the subject positionally.
        KeyArgumentError: Raised by the factory for arguments `fn` does not accept.

    Example:
    ```python
    >>> @key
    ... def distance(n: int, target: int) -> int:
    ...     return abs(n - target)
    >>> distance(10)([3, 12, 9, 20])
    [9, 12, 3, 20]
    >>> distance()
    Traceback (most recent call last):
    ...
    pyordering.exceptions.KeyArgumentError: Key 'distance' got invalid arguments: missing ...

    ```

    """
    key_name = name or getattr(fn, "__name__", repr(fn))
    arguments = _arguments_signature(fn, key_name)

    @wraps(fn)
    def factory(*args: P.args, **kwargs: P.kwargs) -> Ordering[T]:
        try:
            bound = arguments.bind(*args, **kwargs)
        except TypeError as error:
            msg = f"Key '{key_name}' got invalid arguments: {error}"
            raise KeyArgumentError(msg) from error
        return Ordering((Key(key_name, lambda subject: fn(subject, *bound.args, **bound.kwargs)),))

    factory.__signature__ = arguments  # type: ignore[attr-defined]
    return factory


# ---


def _sort_by[T](items: list[T], key: Key[T]) -> list[T]:
    # Nulls are split off first: `None` does not compare with other values.
    pairs = [(key.value(item), item) for item in items]
    present = sorted(
        (pair for pair in pairs if pair[0] is not None),
        key=itemgetter(0),
        reverse=key.descending,  # `reverse` keeps the sort stable
    )
    ordered = [item for _, item in present]
    missing = [item for value, item in pairs if value is None]
    return [*missing, *ordered] if key.nulls == "first" else [*ordered, *missing]


def _arguments_signature(fn: Callable[..., Any], name: str) -> Signature:
    """Return the signature of `fn` without its leading subject parameter."""
    try:
        subject, *parameters = signature(fn).parameters.values()
    except ValueError as error:
        msg = f"Key '{name}' must accept the subject as its first positional parameter"
        raise InvalidKeyError(msg) from error

    if subject.kind not in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD):
        msg = (
            f"Key '{name}' must accept the subject as its first positional parameter, "
            f"got {subject.kind.description} parameter '{subject.name}'"
        )
        raise InvalidKeyError(msg)

    return Signature(parameters)
