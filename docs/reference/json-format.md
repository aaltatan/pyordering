# JSON format

A JSON ordering is a **list of key objects**, applied left to right. An empty list is the
ordering with no keys, which keeps the input order.

```json
[
  {"name": "stars", "descending": true, "nulls": "first"},
  {"name": "closest_to", "args": [28], "kwargs": {"penalty_over": 3}},
  {"name": "id"}
]
```

| Field | Type | Required | Default | Meaning |
| --- | --- | --- | --- | --- |
| `name` | string | yes | — | a visible key of the registry |
| `descending` | boolean | no | `false` | sort this key in reverse |
| `nulls` | `"first"` or `"last"` | no | `"last"` | where `None` values go, in either direction |
| `args` | list | no | `[]` | positional arguments after the subject |
| `kwargs` | object | no | `{}` | keyword arguments |

Any other field is an error. `args` and `kwargs` are checked against the key function's
signature when compiling.

## Errors and paths

| Problem | Exception | Where the path is |
| --- | --- | --- |
| not a list, item not an object, missing `name`, unknown field, wrong field type | `InvalidOrderingDefinitionError` | in the message: `Invalid ordering at $[0]: ...` |
| `name` not registered | `KeyDoesNotExistError` | note: `at $[0].name` |
| `args` / `kwargs` do not fit | `KeyArgumentError` | note: `at $[0]` |
| `nulls` not `"first"` or `"last"` | `InvalidKeyError` | note: `at $[0].nulls` |

```python
from pyordering import InvalidKeyError, OrderingCompiler, key


@key
def length(word: str) -> int:
    return len(word)


compiler = OrderingCompiler({"length": length})

assert compiler.compile([])(["b", "a"]) == ["b", "a"]

try:
    compiler.compile([{"name": "length"}, {"name": "length", "nulls": "middle"}])
except InvalidKeyError as error:
    assert error.__notes__ == ["at $[1].nulls"]
```

The JSON Schema of this format, restricted to your keys, comes from
[`get_ordering_json_schema`](../guide/json-schema.md).
