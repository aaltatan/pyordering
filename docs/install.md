# Installation

pyordering needs **Python 3.12 or newer**.

=== "uv"

    ```bash
    uv add pyordering
    ```

=== "pip"

    ```bash
    pip install pyordering
    ```

Its only dependency is [pyvocabulary](https://pypi.org/project/pyvocabulary/), a small
package by the same author that provides the registry and JSON Schema helpers.

SQLAlchemy and Django are optional. pyordering never imports them: you install the ORM you
already use and write a short render function (see [SQLAlchemy and Django](guide/orms.md)).

## Check it works

```python
from pyordering import key


@key
def length(word: str) -> int:
    return len(word)


assert (~length())(["fig", "apple", "kiwi"]) == ["apple", "kiwi", "fig"]
```
