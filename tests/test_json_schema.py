import pytest
from jsonschema import Draft202012Validator

from pyordering import get_ordering_json_schema


@pytest.fixture
def validator(registry):
    schema = get_ordering_json_schema(registry.keys)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


class TestOrderingJsonSchema:
    def test_describes_each_key_with_direction_and_nulls(self, registry):
        schema = get_ordering_json_schema(registry.keys)
        price = schema["items"]["oneOf"][0]
        assert price["properties"]["name"] == {"const": "price"}
        assert price["properties"]["descending"] == {"type": "boolean", "default": False}
        assert price["properties"]["nulls"] == {
            "enum": ["first", "last"],
            "type": "string",
            "default": "last",
        }
        assert price["description"] == "Sort by price."

    def test_describes_key_arguments(self, registry):
        distance = get_ordering_json_schema(registry.keys)["items"]["oneOf"][-1]
        assert distance["properties"]["args"]["prefixItems"] == [{"type": "integer"}]
        assert distance["properties"]["kwargs"]["properties"]["scale"] == {
            "type": "integer",
            "default": 1,
        }

    @pytest.mark.parametrize(
        "definition",
        [
            [],
            [{"name": "stars", "descending": True, "nulls": "first"}, {"name": "id"}],
            [{"name": "distance", "args": [10], "kwargs": {"scale": 2}}],
        ],
    )
    def test_accepts_what_the_compiler_accepts(self, validator, definition):
        assert validator.is_valid(definition)

    @pytest.mark.parametrize(
        "definition",
        [
            [{"name": "rating"}],
            [{"name": "price", "nulls": "middle"}],
            [{"name": "price", "direction": "desc"}],
        ],
    )
    def test_rejects_what_the_compiler_rejects(self, validator, definition):
        assert not validator.is_valid(definition)
