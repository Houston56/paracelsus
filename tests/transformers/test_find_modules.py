import pytest
from paracelsus.finders import find_modules_by_pattern


def test_find_modules_by_pattern_single_level(single_level_package_path):
    """Test basic glob pattern matching with single-level subpackages."""

    found = find_modules_by_pattern("example.*.models")
    expected_modules = {
        "example.foo.models",
        "example.bar.models",
    }

    assert len(found) == len(expected_modules)
    assert set(found) == expected_modules


def test_find_modules_by_pattern_nested_levels(nested_package_path):
    """Test glob pattern with nested levels (example.*.*.models)."""

    found = find_modules_by_pattern("example.*.*.models")
    expected_modules = {
        "example.domain.users.models",
        "example.domain.products.models",
        "example.api.v1.models",
    }

    assert len(found) == len(expected_modules)
    assert set(found) == expected_modules


def test_find_modules_by_pattern_multiple_stars(multi_star_package_path):
    """Test glob pattern with multiple stars (example.*.api.*.models)."""

    found = find_modules_by_pattern("example.*.api.*.models")
    expected_modules = {
        "example.v1.api.users.models",
        "example.v2.api.products.models",
    }

    assert len(found) == len(expected_modules)
    assert set(found) == expected_modules


def test_find_modules_by_pattern_namespace_package(namespace_package_path):
    """Test glob pattern with namespace packages (PEP 420).

    Should handle namespace packages where __path__ is a list of paths.
    """

    found = find_modules_by_pattern("example.*.models")
    expected_modules = {
        "example.subpackage_a.models",
        "example.subpackage_b.models",
    }

    assert len(found) == len(expected_modules)
    assert set(found) == expected_modules


def test_find_modules_by_pattern_single_character(single_level_package_path):
    """Test glob pattern with single character matching (example.fo?.models)."""

    found = find_modules_by_pattern("example.fo?.models")
    expected_modules = {
        "example.foo.models",
    }

    assert len(found) == len(expected_modules)
    assert set(found) == expected_modules
    assert "example.bar.models" not in found


def test_find_modules_by_pattern_character_class(character_classes_package_path):
    """Test glob pattern with character class (example.api.v[12].models).

    Character class [12] matches exactly one character: '1' or '2'.
    """
    found = find_modules_by_pattern("example.api.v[12].models")
    expected_modules = {
        "example.api.v1.models",
        "example.api.v2.models",
    }
    assert len(found) == len(expected_modules)
    assert set(found) == expected_modules
    assert "example.api.v3.models" not in found


def test_find_modules_by_pattern_character_range(character_classes_package_path):
    """Test glob pattern with character range (example.api.v[0-9].models).

    Character range [0-9] matches exactly one digit from 0 to 9.
    """
    found = find_modules_by_pattern("example.api.v[0-9].models")
    expected_modules = {
        "example.api.v0.models",
        "example.api.v1.models",
        "example.api.v2.models",
        "example.api.v3.models",
        "example.api.v4.models",
        "example.api.v5.models",
        "example.api.v6.models",
        "example.api.v7.models",
        "example.api.v8.models",
        "example.api.v9.models",
    }
    assert len(found) == len(expected_modules)
    assert set(found) == expected_modules
    assert "example.api.v10.models" not in found
    assert "example.api.va.models" not in found


def test_find_modules_by_pattern_complementation_character_class(character_classes_package_path):
    """Test glob pattern with complementation character class (example.api.v[!1].models).

    Complementation [!1] matches any single character except '1'.
    """
    found = find_modules_by_pattern("example.api.v[!1].models")

    assert "example.api.v0.models" in found
    assert "example.api.v2.models" in found
    assert "example.api.va.models" in found
    assert "example.api.v1.models" not in found


def test_find_modules_by_pattern_complementation_character_range(character_classes_package_path):
    """Test glob pattern with complementation range (example.api.v[!0-9].models).

    Complementation [!0-9] matches any single character except digits 0-9.
    """
    found = find_modules_by_pattern("example.api.v[!0-9].models")

    assert "example.api.va.models" in found
    assert "example.api.vb.models" in found

    for i in range(10):
        assert f"example.api.v{i}.models" not in found


def test_find_modules_by_pattern_mixed_wildcards(multi_star_package_path):
    """Test glob pattern with mixed wildcards (example.v?.*.*.models).

    Pattern combines single character match (v?) with any string matches (*).
    v? matches one char (v1, v2, va, etc.), then *.* matches two package levels.
    Example: example.v1.api.users.models, example.v2.api.products.models
    """
    found = find_modules_by_pattern("example.v?.*.*.models")
    expected_modules = {
        "example.v1.api.users.models",
        "example.v2.api.products.models",
    }

    assert len(found) == len(expected_modules)
    assert set(found) == expected_modules


def test_find_modules_by_pattern_recursive_lookup(recursive_package_path):
    """Test glob pattern with recursive lookup (example.**.api.*.models).

    Recursive lookup (**) matches any number of package levels (0 or more).
    Should find modules at different depths:
    - example.api.v1.models (0 levels between example and api)
    - example.something.api.v2.models (1 level deep)
    - example.level1.level2.api.v3.models (2 levels deep)
    """
    found = find_modules_by_pattern("example.**.api.*.models")
    expected_modules = {
        "example.api.v1.models",
        "example.something.api.v2.models",
        "example.level1.level2.api.v3.models",
    }

    assert len(found) == len(expected_modules)
    assert set(found) == expected_modules

    # Should not find modules that don't have 'api' in their path
    assert "example.domain.users.models" not in found


# Error Cases
def test_find_modules_by_pattern_missing_rule_error():
    """Test that missing rule (example.v?..models) raises ValueError.

    Pattern 'v?..models' has two consecutive dots, which is invalid.
    Should raise ValueError with descriptive message.
    """
    with pytest.raises(ValueError, match=".*missing.*rule.*|.*invalid.*pattern.*|.*consecutive.*"):
        find_modules_by_pattern("example.v?..models")


def test_find_modules_by_pattern_invalid_delimiter_error():
    """Test that invalid delimiter (example.v?,,models) raises ValueError.

    Pattern 'v?,,models' uses comma instead of dot as delimiter, which is invalid.
    Should raise ValueError with descriptive message.
    """
    with pytest.raises(ValueError, match=".*invalid.*delimiter.*|.*invalid.*pattern.*"):
        find_modules_by_pattern("example.v?,,models")
