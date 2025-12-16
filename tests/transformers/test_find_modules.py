from paracelsus.graph import find_modules_by_pattern


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
