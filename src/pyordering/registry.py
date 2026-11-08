"""A registry of named keys: the whitelist of fields a JSON ordering may sort by."""

from collections.abc import Callable, Iterator, Mapping
from types import MappingProxyType

from pyvocabulary import Vocabulary

from .exceptions import InvalidKeyNameError, KeyAlreadyRegisteredError, KeyDoesNotExistError
from .ordering import KeyFactory, KeyFn, key


class OrderingRegistry[T]:
    """Collect named keys for subjects of type `T`.

    Its visible keys are what an `OrderingCompiler` accepts and what
    `get_ordering_json_schema` describes; anything else fails at compile time.
    Hidden keys stay usable from Python but are invisible to both.

    Example:
    ```python
    >>> registry = OrderingRegistry[dict[str, int]]()
    >>> @registry.key()
    ... def price(item: dict[str, int]) -> int:
    ...     return item["price"]
    >>> list(registry.keys)
    ['price']
    >>> (~registry["price"]())([{"price": 1}, {"price": 3}])
    [{'price': 3}, {'price': 1}]

    ```

    """

    __slots__ = ("_keys",)

    def __init__(self) -> None:
        self._keys: Vocabulary[KeyFactory[T, ...]] = Vocabulary(
            "key",
            does_not_exist=KeyDoesNotExistError,
            already_registered=KeyAlreadyRegisteredError,
            invalid_name=InvalidKeyNameError,
        )

    @property
    def keys(self) -> Mapping[str, KeyFactory[T, ...]]:
        """A read-only mapping of every visible key factory, by name."""
        return MappingProxyType(dict(self._keys))

    def __getitem__(self, name: str, /) -> KeyFactory[T, ...]:
        return self._keys[name]

    def __contains__(self, name: object, /) -> bool:
        return name in self._keys

    def __iter__(self) -> Iterator[str]:
        return iter(self._keys)

    def __len__(self) -> int:
        return len(self._keys)

    def key[**P](
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        hidden: bool = False,
    ) -> Callable[[KeyFn[T, P]], KeyFactory[T, P]]:
        """Return a decorator registering a key function. See `register`."""

        def decorator(fn: KeyFn[T, P]) -> KeyFactory[T, P]:
            return self.register(fn, name=name, description=description, hidden=hidden)

        return decorator

    def register[**P](
        self,
        fn: KeyFn[T, P],
        /,
        *,
        name: str | None = None,
        description: str | None = None,
        hidden: bool = False,
    ) -> KeyFactory[T, P]:
        """Register `fn` as a key and return its factory.

        Args:
            fn: The key function; its first positional parameter receives the subject.
            name: The key name used in JSON and `repr`; defaults to the function name.
            description: Overrides the function docstring (shown in the JSON Schema).
            hidden: Keep the key out of lookups, the compiler and the JSON Schema.

        Raises:
            InvalidKeyNameError: If the name is not a valid Python identifier.
            KeyAlreadyRegisteredError: If the name is taken.
            InvalidKeyError: If `fn` does not accept the subject positionally.

        """
        key_name = name or getattr(fn, "__name__", "")
        factory = key(fn, name=key_name)
        factory.__doc__ = description or fn.__doc__
        return self._keys.add(key_name, factory, hidden=hidden)
