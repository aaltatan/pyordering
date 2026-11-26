# Exceptions

Every error is raised while an ordering is **built**, from Python or from JSON, never while it
sorts. All of them derive from `PyorderingError`, and each also derives from the built-in
exception it resembles, so existing `except ValueError` code keeps working.

```text
PyorderingError
├── InvalidKeyError                 (ValueError)
├── KeyArgumentError                (TypeError)
├── InvalidOrderingDefinitionError  (ValueError)
├── KeyDoesNotExistError            (pyvocabulary.NameDoesNotExistError)
├── KeyAlreadyRegisteredError       (pyvocabulary.NameAlreadyRegisteredError)
└── InvalidKeyNameError             (pyvocabulary.InvalidNameError)
```

| Exception | Raised when |
| --- | --- |
| `InvalidKeyError` | a key function does not take the subject as its first positional parameter, or `nulls` is not `"first"` or `"last"` |
| `KeyArgumentError` | a key factory is called with arguments its function does not accept |
| `InvalidOrderingDefinitionError` | a JSON ordering does not have the expected shape |
| `KeyDoesNotExistError` | a name is not a visible key of the registry |
| `KeyAlreadyRegisteredError` | a name is registered twice |
| `InvalidKeyNameError` | a name is not an ASCII Python identifier |

Errors raised by `OrderingCompiler.compile` carry an exception note with the JSON path, such
as `at $[1].name`. The error keeps its type: the path is added with `add_note`, not by
wrapping. Read it from `error.__notes__`; Python prints it under the traceback.

```python
from pyordering import (
    InvalidKeyError,
    InvalidKeyNameError,
    InvalidOrderingDefinitionError,
    KeyAlreadyRegisteredError,
    KeyArgumentError,
    KeyDoesNotExistError,
    PyorderingError,
)

assert issubclass(InvalidKeyError, ValueError)
assert issubclass(KeyArgumentError, TypeError)
assert issubclass(InvalidOrderingDefinitionError, ValueError)

for error in (
    InvalidKeyError,
    KeyArgumentError,
    InvalidOrderingDefinitionError,
    KeyDoesNotExistError,
    KeyAlreadyRegisteredError,
    InvalidKeyNameError,
):
    assert issubclass(error, PyorderingError)
```
