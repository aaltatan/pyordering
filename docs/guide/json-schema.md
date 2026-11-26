# JSON Schema

`get_ordering_json_schema` describes exactly what an [`OrderingCompiler`](compiling.md)
accepts, generated from the key signatures and docstrings. Hand it to a form builder, an
OpenAPI spec, or an LLM that writes sort orders.

```python
from pyordering import OrderingRegistry, get_ordering_json_schema

registry = OrderingRegistry[dict[str, int]]()


@registry.key()
def price(item: dict[str, int]) -> int:
    """Sort by price."""
    return item["price"]


@registry.key()
def closest_to(item: dict[str, int], budget: int, *, penalty_over: int = 1) -> int:
    """Sort by distance from a budget; going over it can cost more."""
    difference = item["price"] - budget

    return difference * penalty_over if difference > 0 else -difference


schema = get_ordering_json_schema(registry.keys)
```

## What it contains

The schema is an array whose items are `oneOf` the registered keys, each pinned by a
`const` name:

```python
assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
assert schema["type"] == "array"
assert [item["properties"]["name"]["const"] for item in schema["items"]["oneOf"]] == [
    "price",
    "closest_to",
]
```

Each key carries its description (the docstring, or the registry's `description=`), the
`descending` and `nulls` options, and its arguments typed from the signature:

```python
closest = schema["items"]["oneOf"][1]

assert closest["description"] == "Sort by distance from a budget; going over it can cost more."
assert closest["properties"]["descending"] == {"type": "boolean", "default": False}
assert closest["properties"]["nulls"] == {
    "enum": ["first", "last"],
    "type": "string",
    "default": "last",
}
assert closest["properties"]["args"]["prefixItems"] == [{"type": "integer"}]
assert closest["properties"]["kwargs"]["properties"] == {
    "budget": {"type": "integer"},
    "penalty_over": {"type": "integer", "default": 1},
}
```

Hidden keys and anything you did not register are left out, so the schema and the compiler
always agree on the whitelist.

## Validating before compiling

The compiler already rejects anything the schema would, with JSON paths in its errors. A
schema validator is still useful at the edge of a system that validates every request the
same way, such as an OpenAPI layer:

```python
from jsonschema import Draft202012Validator

validator = Draft202012Validator(schema)

assert validator.is_valid([{"name": "price", "descending": True}])
assert validator.is_valid([{"name": "closest_to", "args": [28]}])
assert not validator.is_valid([{"name": "rating"}])
assert not validator.is_valid([{"name": "price", "nulls": "middle"}])
```

`jsonschema` is not a dependency of pyordering; install it if you want this step.
