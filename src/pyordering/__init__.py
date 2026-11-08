"""pyordering: Sort orders as composable values.

`~stars() >> price() >> name()` is an `Ordering`: a key per field, applied left
to right, that sorts in memory and can render ORM `order_by` clauses.

Nothing is implemented yet; see PHASES.md for the plan.
"""

__all__: list[str] = []
