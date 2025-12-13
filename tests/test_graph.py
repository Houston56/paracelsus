import sys
import pytest

from paracelsus.config import Layouts
from paracelsus.graph import get_graph_string, find_modules_by_pattern

from .utils import mermaid_assert


@pytest.mark.parametrize("column_sort_arg", ["key-based", "preserve-order"])
def test_get_graph_string(column_sort_arg, package_path):
    graph_string = get_graph_string(
        base_class_path="example.base:Base",
        import_module=["example.models"],
        include_tables=set(),
        exclude_tables=set(),
        python_dir=[package_path],
        format="mermaid",
        column_sort=column_sort_arg,
    )
    mermaid_assert(graph_string)


def test_get_graph_string_with_exclude(package_path):
    """Excluding tables removes them from the graph string."""
    graph_string = get_graph_string(
        base_class_path="example.base:Base",
        import_module=["example.models"],
        include_tables=set(),
        exclude_tables={"comments"},
        python_dir=[package_path],
        column_sort="key-based",
        format="mermaid",
    )
    assert "comments {" not in graph_string
    assert "posts {" in graph_string
    assert "users {" in graph_string
    assert "users ||--o{ posts" in graph_string

    # Excluding a table to which another table holds a foreign key will raise an error.
    graph_string = get_graph_string(
        base_class_path="example.base:Base",
        import_module=["example.models"],
        include_tables=set(),
        exclude_tables={"users", "comments"},
        python_dir=[package_path],
        format="mermaid",
        column_sort="key-based",
    )
    assert "posts {" in graph_string
    assert "users ||--o{ posts" not in graph_string


def test_get_graph_string_with_include(package_path):
    """Excluding tables keeps them in the graph string."""
    graph_string = get_graph_string(
        base_class_path="example.base:Base",
        import_module=["example.models"],
        include_tables={"users", "posts"},
        exclude_tables=set(),
        python_dir=[package_path],
        column_sort="key-based",
        format="mermaid",
    )
    assert "comments {" not in graph_string
    assert "posts {" in graph_string
    assert "users {" in graph_string
    assert "users ||--o{ posts" in graph_string

    # Including a table that holds a foreign key to a non-existing table will keep
    # the table but skip the connection.
    graph_string = get_graph_string(
        base_class_path="example.base:Base",
        import_module=["example.models"],
        include_tables={"posts"},
        exclude_tables=set(),
        python_dir=[package_path],
        column_sort="key-based",
        format="mermaid",
    )
    assert "posts {" in graph_string
    assert "users ||--o{ posts" not in graph_string


@pytest.mark.parametrize("layout_arg", ["dagre", "elk"])
def test_get_graph_string_with_layout(layout_arg, package_path):
    graph_string = get_graph_string(
        base_class_path="example.base:Base",
        import_module=["example.models"],
        include_tables=set(),
        exclude_tables=set(),
        python_dir=[package_path],
        format="mermaid",
        column_sort="key-based",
        layout=Layouts(layout_arg),
    )
    mermaid_assert(graph_string)


def test_find_modules_by_pattern_single_level(single_level_package_path):
    """Test basic glob pattern matching with single-level subpackages."""
    
    if str(single_level_package_path) not in sys.path:
        sys.path.insert(0, str(single_level_package_path))
    
    found = find_modules_by_pattern("example.*.models")
    expected_modules = {
        "example.foo.models",
        "example.bar.models",
    }
    
    assert len(found) == len(expected_modules)
    assert set(found) == expected_modules


def test_find_modules_by_pattern_nested_levels(nested_package_path):
    """Test glob pattern with nested levels (example.*.*.models).
    
    Should find:
    - example.domain.users.models
    - example.domain.products.models
    - example.api.v1.models
    """
    
    if str(nested_package_path) not in sys.path:
        sys.path.insert(0, str(nested_package_path))
    
    found = find_modules_by_pattern("example.*.*.models")
    expected_modules = {
        "example.domain.users.models",
        "example.domain.products.models",
        "example.api.v1.models",
    }
        
    assert len(found) == len(expected_modules)
    assert set(found) == expected_modules


def test_find_modules_by_pattern_multiple_stars(multi_star_package_path):
    """Test glob pattern with multiple stars (example.*.api.*.models).
    
    Should find:
    - example.v1.api.users.models
    - example.v2.api.products.models
    """
    
    if str(multi_star_package_path) not in sys.path:
        sys.path.insert(0, str(multi_star_package_path))
    
    found = find_modules_by_pattern("example.*.api.*.models")
    expected_modules = {
        "example.v1.api.users.models",
        "example.v2.api.products.models",
    }
        
    assert len(found) == len(expected_modules)
    assert set(found) == expected_modules


def test_get_graph_string_with_nested_glob_pattern(nested_package_path):
    """Integration test: get_graph_string with nested glob pattern."""
    
    if str(nested_package_path) not in sys.path:
        sys.path.insert(0, str(nested_package_path))
    
    graph_string = get_graph_string(
        base_class_path="example.base:Base",
        import_module=["example.*.*.models"],
        include_tables=set(),
        exclude_tables=set(),
        python_dir=[nested_package_path],
        format="mermaid",
        column_sort="key-based",
    )
        
    assert "users {" in graph_string or "products {" in graph_string or "api_resources {" in graph_string


def test_find_modules_by_pattern_namespace_package(namespace_package_path):
    """Test glob pattern with namespace packages (PEP 420).
    
    Should handle namespace packages where __path__ is a list of paths.
    """
    import example
    

    assert hasattr(example, '__path__')

    found = find_modules_by_pattern("example.*.models")
    expected_modules = {
        "example.subpackage_a.models",
        "example.subpackage_b.models",
    }
        
    assert len(found) == len(expected_modules)
    assert set(found) == expected_modules
