import pytest
from conftest import ids

from pyordering import (
    InvalidKeyError,
    InvalidOrderingDefinitionError,
    KeyArgumentError,
    KeyDoesNotExistError,
    OrderingCompiler,
)


@pytest.fixture
def compiler(registry):
    return OrderingCompiler(registry.keys)


class TestOrderingCompiler:
    def test_compiles_names_directions_and_nulls(self, compiler, products):
        ordering = compiler.compile(
            [{"name": "stars", "descending": True, "nulls": "first"}, {"name": "name"}]
        )
        assert repr(ordering) == "Ordering(~stars nulls first >> name)"
        assert ids(ordering(products)) == [5, 2, 3, 1, 4]

    def test_passes_args_and_kwargs(self, compiler, products):
        ordering = compiler.compile(
            [{"name": "distance", "args": [26], "kwargs": {"scale": 2}}, {"name": "id"}]
        )
        assert ids(ordering(products)) == [2, 4, 1, 3, 5]

    def test_empty_list_is_an_empty_ordering(self, compiler):
        assert compiler.compile([]).keys == ()

    def test_unknown_key_reports_its_path(self, compiler):
        with pytest.raises(KeyDoesNotExistError, match="Key 'rating' does not exist") as error:
            compiler.compile([{"name": "price"}, {"name": "rating"}])
        assert error.value.__notes__ == ["at $[1].name"]

    def test_bad_arguments_report_their_path(self, compiler):
        with pytest.raises(KeyArgumentError, match="missing") as error:
            compiler.compile([{"name": "distance"}])
        assert error.value.__notes__ == ["at $[0]"]

    def test_bad_nulls_report_their_path(self, compiler):
        with pytest.raises(InvalidKeyError, match="Invalid nulls 'middle'") as error:
            compiler.compile([{"name": "price", "nulls": "middle"}])
        assert error.value.__notes__ == ["at $[0].nulls"]

    @pytest.mark.parametrize(
        ("definition", "message"),
        [
            ({"name": "price"}, r"Invalid ordering at \$: expected a list"),
            (["price"], r"Invalid ordering at \$\[0\]: expected an object, received 'price'"),
            ([{}], r"Invalid ordering at \$\[0\]: missing 'name'"),
            (
                [{"name": "price", "direction": "desc"}],
                r"unknown 'direction'. Allowed keys: args, descending, kwargs, name, nulls",
            ),
            ([{"name": 1}], r"at \$\[0\].name: expected a string, received 1"),
            ([{"name": "price", "descending": "yes"}], r"\$\[0\].descending: expected a boolean"),
            ([{"name": "price", "args": {}}], r"\$\[0\].args: expected a list"),
            ([{"name": "price", "kwargs": []}], r"\$\[0\].kwargs: expected an object"),
        ],
    )
    def test_wrong_shape_is_rejected(self, compiler, definition, message):
        with pytest.raises(InvalidOrderingDefinitionError, match=message):
            compiler.compile(definition)
