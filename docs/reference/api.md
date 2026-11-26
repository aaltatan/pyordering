# API

`T` is the type of the subject a key reads: the object being sorted, or the model class
when rendering ORM clauses.

## Orderings

### `Ordering[T]`

```py
Ordering(keys: tuple[Key[T], ...])
```

Keys applied left to right. A frozen dataclass; every operator returns a new ordering.

| Member | Description |
| --- | --- |
| `ordering(items) -> list[T]` | a new sorted list; `items` is any iterable and is not changed |
| `a >> b` | the keys of `a`, then the keys of `b` |
| `~a` | every direction flipped; `nulls` kept |
| `a.nulls("first" \| "last")` | `nulls` set on every key; raises `InvalidKeyError` for other values |
| `a.clauses(subject, render) -> tuple[C, ...]` | ORM `order_by` clauses: `render(key(subject), descending, nulls)` per key, tuples flattened |
| `a.keys` | the `tuple[Key[T], ...]` |
| `repr(a)` | e.g. `Ordering(~stars nulls first >> price)` |

Each key is a separate stable sort pass, run from the last key to the first. `None` values
are split off before each pass, so they never need to compare with other values.

Guide: [Keys and orderings](../guide/orderings.md), [SQLAlchemy and Django](../guide/orms.md).

### `Key[T]`

```py
Key(name: str, value: Callable[[T], Any], descending: bool = False, nulls: Nulls = "last")
```

One sort key. A frozen dataclass; raises `InvalidKeyError` if `nulls` is not `"first"` or
`"last"`. `str(key)` is `~name nulls first` style, as shown in `Ordering`'s `repr`.

### `key`

```py
key(fn: KeyFn[T, P], /, *, name: str | None = None) -> KeyFactory[T, P]
```

Turns a `(subject, *args, **kwargs) -> sort value` function into a key factory. The factory
binds its arguments against the signature of `fn` (minus the subject) and returns a one-key
`Ordering`. `name` defaults to the function name.

Raises `InvalidKeyError` if `fn` does not take the subject as its first positional
parameter. The factory raises `KeyArgumentError` for arguments `fn` does not accept.

The factory keeps `fn` as `__wrapped__` and exposes the signature without the subject.

## Registries

### `OrderingRegistry[T]`

```py
OrderingRegistry[T]()
```

| Member | Description |
| --- | --- |
| `@registry.key(*, name=None, description=None, hidden=False)` | decorator form of `register`; returns the factory |
| `registry.register(fn, /, *, name=None, description=None, hidden=False)` | registers `fn` and returns its factory |
| `registry.keys` | read-only `Mapping[str, KeyFactory]` of visible keys |
| `registry[name]` | the factory; raises `KeyDoesNotExistError` |
| `name in registry`, `iter(registry)`, `len(registry)` | over visible keys |

`register` raises `InvalidKeyNameError` for a name that is not an ASCII identifier,
`KeyAlreadyRegisteredError` for a taken name, and `InvalidKeyError` for a bad key function.

Guide: [Registries](../guide/registries.md).

## Compiling and schema

### `OrderingCompiler[T]`

```py
OrderingCompiler(keys: Mapping[str, KeyFactory[T, ...]], /)
compiler.compile(definition: list[KeyDict] | Any, /) -> Ordering[T]
```

Builds an `Ordering` from a [JSON ordering](json-format.md). Raises
`InvalidOrderingDefinitionError`, `KeyDoesNotExistError`, `KeyArgumentError` or
`InvalidKeyError`, each with a JSON-path note (or the path in the message, for shape errors).

Guide: [Compiling orderings from JSON](../guide/compiling.md).

### `get_ordering_json_schema`

```py
get_ordering_json_schema(keys: Mapping[str, Callable[..., Any]], /) -> dict[str, Any]
```

The JSON Schema (draft 2020-12) of the definitions `OrderingCompiler(keys)` accepts.

Guide: [JSON Schema](../guide/json-schema.md).

## Types

| Name | Definition |
| --- | --- |
| `Nulls` | `Literal["first", "last"]` |
| `KeyFn[T, **P]` | `Callable[Concatenate[T, P], Any]`, a key function |
| `KeyFactory[T, **P]` | `Callable[P, Ordering[T]]`, what `@key` returns |
| `Render[C]` | `Callable[[Any, bool, Nulls], C \| tuple[C, ...]]`, the render function of `clauses` |
| `KeyDict` | `TypedDict` of one JSON key object: `name`, and optional `args`, `kwargs`, `descending`, `nulls` |
