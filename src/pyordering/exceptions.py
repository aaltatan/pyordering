"""Exceptions raised by pyordering.

Every error is raised while an ordering is *built* (from Python or from JSON),
never while it sorts. Compiler errors carry a note with their JSON path, e.g.
`at $[1].name`.
"""

from collections.abc import Iterable

from pyvocabulary import InvalidNameError, NameAlreadyRegisteredError, NameDoesNotExistError


class PyorderingError(Exception):
    """Base class for every exception raised by pyordering."""


class InvalidKeyError(PyorderingError, ValueError):
    """Raised when a key function or a key option (such as `nulls`) is invalid."""


class KeyArgumentError(PyorderingError, TypeError):
    """Raised when a key factory is called with arguments its function does not accept."""


class InvalidOrderingDefinitionError(PyorderingError, ValueError):
    """Raised when a JSON ordering definition does not have the expected shape."""


class KeyDoesNotExistError(PyorderingError, NameDoesNotExistError):
    """Raised when a key name is not in the registry.

    Example:
    ```python
    >>> str(KeyDoesNotExistError("rating", ["price", "name"]))
    "Key 'rating' does not exist. Available keys: price, name"

    ```

    """

    def __init__(self, name: str, available: Iterable[str], /) -> None:
        super().__init__(name, available, kind="key")


class KeyAlreadyRegisteredError(PyorderingError, NameAlreadyRegisteredError):
    """Raised when a key name is registered twice."""

    def __init__(self, name: str, /) -> None:
        super().__init__(name, kind="key")


class InvalidKeyNameError(PyorderingError, InvalidNameError):
    """Raised when a key name is not a valid ASCII Python identifier."""

    def __init__(self, name: object, /) -> None:
        super().__init__(name, kind="key")
