"""pyordering: sort orders as composable values.

`~stars() >> price() >> name()` is an `Ordering`: keys applied left to right,
sorting in memory with stable passes, compilable from JSON, and renderable to
ORM `order_by` clauses.
"""

from .compilers import KeyDict, OrderingCompiler
from .exceptions import (
    InvalidKeyError,
    InvalidKeyNameError,
    InvalidOrderingDefinitionError,
    KeyAlreadyRegisteredError,
    KeyArgumentError,
    KeyDoesNotExistError,
    PyorderingError,
)
from .json_schema import get_ordering_json_schema
from .ordering import Key, KeyFactory, KeyFn, Nulls, Ordering, Render, key
from .registry import OrderingRegistry

__all__ = [
    "InvalidKeyError",
    "InvalidKeyNameError",
    "InvalidOrderingDefinitionError",
    "Key",
    "KeyAlreadyRegisteredError",
    "KeyArgumentError",
    "KeyDict",
    "KeyDoesNotExistError",
    "KeyFactory",
    "KeyFn",
    "Nulls",
    "Ordering",
    "OrderingCompiler",
    "OrderingRegistry",
    "PyorderingError",
    "Render",
    "get_ordering_json_schema",
    "key",
]
