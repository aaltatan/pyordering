import pytest
from conftest import by, ids

from pyordering import (
    InvalidKeyError,
    KeyArgumentError,
    Ordering,
    key,
)


class TestSorting:
    def test_one_key_sorts_ascending(self, registry, products):
        assert ids(by(registry, "name")(products)) == [3, 5, 1, 4, 2]

    def test_invert_sorts_descending(self, registry, products):
        assert ids((~by(registry, "released"))(products)) == [5, 3, 1, 2, 4]

    def test_later_keys_break_ties_of_earlier_ones(self, registry, products):
        ordering = by(registry, "price") >> ~by(registry, "name")
        assert ids(ordering(products)) == [2, 4, 1, 3, 5]

    def test_mixed_directions_work_for_strings(self, registry, products):
        ordering = ~by(registry, "price") >> by(registry, "name")
        assert ids(ordering(products)) == [5, 3, 1, 4, 2]

    def test_equal_items_keep_their_input_order(self, registry, products):
        assert ids(by(registry, "price")(products)) == [2, 4, 1, 3, 5]
        assert ids((~by(registry, "price"))(products)) == [5, 1, 3, 2, 4]

    def test_nulls_go_last_by_default_in_both_directions(self, registry, products):
        assert ids(by(registry, "stars")(products)) == [1, 4, 3, 2, 5]
        assert ids((~by(registry, "stars"))(products)) == [3, 1, 4, 2, 5]

    def test_nulls_first(self, registry, products):
        assert ids(by(registry, "stars").nulls("first")(products)) == [2, 5, 1, 4, 3]

    def test_invert_keeps_nulls(self, registry, products):
        ordering = ~by(registry, "stars").nulls("first")
        assert ids(ordering(products)) == [2, 5, 3, 1, 4]

    def test_empty_ordering_keeps_input_order(self, products):
        assert ids(Ordering[object](())(products)) == [1, 2, 3, 4, 5]

    def test_accepts_any_iterable_and_returns_a_list(self, registry, products):
        assert ids(by(registry, "name")(iter(products))) == [3, 5, 1, 4, 2]

    def test_arguments_are_bound_when_built(self, registry, products):
        ordering = registry["distance"](26) >> by(registry, "id")
        assert ids(ordering(products)) == [2, 4, 1, 3, 5]


class TestComposition:
    def test_rshift_chains_keys(self, registry):
        ordering = ~by(registry, "stars") >> by(registry, "price") >> by(registry, "name")
        assert [k.name for k in ordering.keys] == ["stars", "price", "name"]

    def test_operators_return_new_values(self, registry):
        price = by(registry, "price")
        _ = ~price >> price
        assert price.keys[0].descending is False

    def test_invert_twice_is_the_original(self, registry):
        ordering = by(registry, "stars") >> ~by(registry, "name")
        assert ~~ordering == ordering

    def test_rshift_rejects_other_types(self, registry):
        with pytest.raises(TypeError):
            by(registry, "price") >> "name"  # type: ignore[operator]

    def test_repr(self, registry):
        ordering = ~by(registry, "stars").nulls("first") >> by(registry, "price")
        assert repr(ordering) == "Ordering(~stars nulls first >> price)"

    def test_invalid_nulls_fail_when_built(self, registry):
        with pytest.raises(
            InvalidKeyError, match=r"Invalid nulls 'middle'. Valid values: first, last"
        ):
            by(registry, "stars").nulls("middle")  # type: ignore[arg-type]


class TestKeyDecorator:
    def test_turns_a_function_into_a_factory(self, products):
        @key
        def name(product) -> str:
            return product.name

        assert repr(name()) == "Ordering(name)"
        assert ids(name()(products)) == [3, 5, 1, 4, 2]

    def test_missing_argument_fails_when_built(self, registry):
        with pytest.raises(KeyArgumentError, match="Key 'distance' got invalid arguments: missing"):
            registry["distance"]()

    def test_unexpected_argument_fails_when_built(self, registry):
        with pytest.raises(KeyArgumentError, match="unexpected keyword argument 'size'"):
            registry["distance"](10, size=2)

    def test_function_without_a_subject_parameter_is_rejected(self):
        with pytest.raises(InvalidKeyError, match="Key 'now' must accept the subject"):

            @key
            def now() -> int:
                return 0

    def test_keyword_only_subject_is_rejected(self):
        with pytest.raises(InvalidKeyError, match="got keyword-only parameter 'item'"):

            @key
            def odd(*, item) -> int:
                return item


class TestClauses:
    def test_render_receives_expression_direction_and_nulls(self, registry):
        ordering = ~by(registry, "stars").nulls("first") >> by(registry, "price")
        clauses = ordering.clauses(
            _Model, lambda expression, descending, nulls: [expression, descending, nulls]
        )
        assert clauses == (["stars-column", True, "first"], ["price-column", False, "last"])

    def test_tuples_returned_by_render_are_flattened(self, registry):
        clauses = by(registry, "stars").clauses(
            _Model, lambda expression, descending, nulls: (f"{expression} is null", expression)
        )
        assert clauses == ("stars-column is null", "stars-column")


class _Model:
    stars = "stars-column"
    price = "price-column"
