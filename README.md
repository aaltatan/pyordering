# pyordering

**Planned.** Sort orders as composable values, definable as JSON and renderable to
SQLAlchemy or Django `order_by` clauses.

```python
best_first = stars(descending=True, nulls="last") >> price() >> name()
best_first(products)                      # a new sorted tuple
~best_first                               # Ordering(stars >> ~price >> ~name)
Product.objects.order_by(*best_first.clauses(Product, django_clause))
```

See `PHASES.md` for the plan.
