"""Compile an ordering from JSON: `[{"name": "stars", "descending": true}, {"name": "id"}]`.

Only registered keys compile, so a definition sent by a client (a `?sort=`
parameter, a saved view) can sort by nothing but the fields you allowed.
"""

from collections.abc import Mapping
from typing import Any, NotRequired, TypedDict, cast

from pyvocabulary import index_path, key_path, located

from .exceptions import InvalidOrderingDefinitionError, KeyDoesNotExistError, PyorderingError
from .ordering import KeyFactory, Nulls, Ordering

_ALLOWED_KEYS = {"name", "args", "kwargs", "descending", "nulls"}


class KeyDict(TypedDict):
    name: str
    args: NotRequired[list[Any]]
    kwargs: NotRequired[dict[str, Any]]
    descending: NotRequired[bool]
    nulls: NotRequired[Nulls]


class OrderingCompiler[T]:
    """Compile JSON ordering definitions using a mapping of key factories.

    Every problem is reported here, before anything is sorted, with a note
    giving its JSON path.

    Example:
    ```python
    >>> from pyordering import OrderingRegistry
    >>> registry = OrderingRegistry[str]()
    >>> @registry.key()
    ... def length(word: str) -> int:
    ...     return len(word)
    >>> compiler = OrderingCompiler(registry.keys)
    >>> ordering = compiler.compile([{"name": "length", "descending": True}])
    >>> ordering, ordering(["fig", "apple", "kiwi"])
    (Ordering(~length), ['apple', 'kiwi', 'fig'])
    >>> compiler.compile([{"name": "size"}])
    Traceback (most recent call last):
    ...
    pyordering.exceptions.KeyDoesNotExistError: Key 'size' does not exist. Available keys: length
    at $[0].name

    ```

    """

    __slots__ = ("_keys",)

    def __init__(self, keys: Mapping[str, KeyFactory[T, ...]], /) -> None:
        self._keys = keys

    def compile(self, definition: list[KeyDict] | Any, /) -> Ordering[T]:
        """Compile `definition`, a list of key objects, into an `Ordering`.

        Raises:
            InvalidOrderingDefinitionError: If the definition has the wrong shape.
            KeyDoesNotExistError: If a name is not a registered key.
            KeyArgumentError: If `args` or `kwargs` do not fit the key function.
            InvalidKeyError: If `nulls` is not `"first"` or `"last"`.

        """
        if not isinstance(definition, list):
            msg = f"Invalid ordering at $: expected a list, received {definition!r}"

            raise InvalidOrderingDefinitionError(msg)

        orderings = [
            self._compile_key(item, index_path("$", index))
            for index, item in enumerate(cast("list[Any]", definition))
        ]

        return Ordering(tuple(k for ordering in orderings for k in ordering.keys))

    def _compile_key(self, item: Any, path: str) -> Ordering[T]:
        _check_shape(item, path)

        with located(key_path(path, "name"), PyorderingError):
            if (factory := self._keys.get(item["name"])) is None:
                raise KeyDoesNotExistError(item["name"], self._keys)

        with located(path, PyorderingError):
            ordering = factory(*item.get("args", []), **item.get("kwargs", {}))

        if item.get("descending", False):
            ordering = ~ordering

        with located(key_path(path, "nulls"), PyorderingError):
            return ordering.nulls(item.get("nulls", "last"))


# ---


_TYPES: dict[str, tuple[type, str]] = {
    "name": (str, "a string"),
    "args": (list, "a list"),
    "kwargs": (dict, "an object"),
    "descending": (bool, "a boolean"),
}


def _check_shape(item: Any, path: str) -> None:
    if not isinstance(item, Mapping):
        msg = f"Invalid ordering at {path}: expected an object, received {item!r}"

        raise InvalidOrderingDefinitionError(msg)

    mapping = cast("Mapping[str, Any]", item)

    keys = set(mapping)

    if "name" not in keys:
        msg = f"Invalid ordering at {path}: missing 'name'"

        raise InvalidOrderingDefinitionError(msg)

    if unknown := sorted(keys - _ALLOWED_KEYS):
        msg = (
            f"Invalid ordering at {path}: unknown {', '.join(map(repr, unknown))}. "
            f"Allowed keys: {', '.join(sorted(_ALLOWED_KEYS))}"
        )

        raise InvalidOrderingDefinitionError(msg)

    for field, (expected, label) in _TYPES.items():
        if field in keys and not isinstance(value := mapping[field], expected):
            msg = f"Invalid ordering at {path}.{field}: expected {label}, received {value!r}"

            raise InvalidOrderingDefinitionError(msg)
