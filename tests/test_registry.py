import pytest

from pyordering import (
    InvalidKeyNameError,
    KeyAlreadyRegisteredError,
    KeyDoesNotExistError,
    OrderingRegistry,
)


class TestOrderingRegistry:
    def test_lists_visible_keys(self, registry):
        assert list(registry.keys) == ["price", "stars", "name", "released", "id", "distance"]
        assert len(registry) == 6
        assert "price" in registry

    def test_iterates_over_key_names(self, registry):
        assert list(registry) == list(registry.keys)

    def test_name_overrides_function_name(self, registry):
        assert repr(registry["id"]()) == "Ordering(id)"

    def test_unknown_key_lists_available_keys(self, registry):
        with pytest.raises(
            KeyDoesNotExistError, match=r"Key 'rating' does not exist. Available keys: price"
        ):
            registry["rating"]

    def test_duplicate_name_is_rejected(self, registry):
        with pytest.raises(KeyAlreadyRegisteredError, match="Key 'price' is already registered"):
            registry.register(lambda product: product.price, name="price")

    def test_invalid_name_is_rejected(self, registry):
        with pytest.raises(InvalidKeyNameError, match="Invalid key name: 'unit-price'"):
            registry.register(lambda product: product.price, name="unit-price")

    def test_hidden_keys_stay_usable_from_python(self, registry, products):
        secret = registry.register(lambda product: -product.id, name="newest", hidden=True)
        assert "newest" not in registry
        assert [product.id for product in secret()(products)] == [5, 4, 3, 2, 1]

    def test_description_overrides_docstring(self):
        registry = OrderingRegistry[int]()
        factory = registry.register(abs, name="size", description="By magnitude.")
        assert factory.__doc__ == "By magnitude."
