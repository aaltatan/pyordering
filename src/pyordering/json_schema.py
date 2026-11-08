"""The JSON Schema of an ordering definition, as accepted by `OrderingCompiler.compile`.

It is generated from the registered key signatures, so it can be handed to a
form builder, an API spec, or an LLM that writes sort orders as JSON.
"""

from collections.abc import Callable, Mapping
from typing import Any

from pyvocabulary import JSON_SCHEMA_DIALECT, call_json_schema, json_schema_of

from .ordering import Nulls

_OPTIONS = {
    "descending": {"type": "boolean", "default": False},
    "nulls": {**json_schema_of(Nulls), "default": "last"},
}


def get_ordering_json_schema(keys: Mapping[str, Callable[..., Any]], /) -> dict[str, Any]:
    """Return the JSON Schema of a list of key objects. Pass `registry.keys`.

    Example:
    ```python
    >>> from pyordering import key
    >>> @key
    ... def length(word: str) -> int:
    ...     '''By number of characters.'''
    ...     return len(word)
    >>> schema = get_ordering_json_schema({"length": length})
    >>> item = schema["items"]["oneOf"][0]
    >>> schema["type"], item["properties"]["name"], item["description"]
    ('array', {'const': 'length'}, 'By number of characters.')
    >>> item["properties"]["nulls"]
    {'enum': ['first', 'last'], 'type': 'string', 'default': 'last'}

    ```

    """
    return {
        "$schema": JSON_SCHEMA_DIALECT,
        "type": "array",
        "items": {
            "oneOf": [
                _without_empty_prefix_items(
                    call_json_schema(name, factory, extra_properties=_OPTIONS)
                )
                for name, factory in keys.items()
            ]
        },
    }


def _without_empty_prefix_items(schema: dict[str, Any]) -> dict[str, Any]:
    # shortcut: pyvocabulary emits `"prefixItems": []`, which draft 2020-12 forbids;
    # drop this once pyvocabulary omits it (`"items": false` alone already means no args).
    args = schema["properties"]["args"]
    if args.get("prefixItems") == []:
        del args["prefixItems"]
    return schema
