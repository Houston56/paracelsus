import pytest

from paracelsus.config import Layouts
from paracelsus.graph import get_graph_string

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


@pytest.mark.skip(reason="Update mermaid_assert function to dynamically detect required models for validation")
def test_get_graph_string_with_wildcard(single_level_package_path):
    get_graph_string(
        base_class_path="example.base:Base",
        import_module=["example.*.models"],
        include_tables=set(),
        exclude_tables=set(),
        python_dir=[single_level_package_path],
        format="mermaid",
        column_sort="key-based",
    )
    # mermaid_assert(graph_string)


@pytest.mark.skip(reason="Update mermaid_assert function to dynamically detect required models for validation")
def test_get_graph_with_wildcard_mask_in_namespace_package(namespace_package_path):
    get_graph_string(
        base_class_path="project1.example.base:Base",  # @TODO: How to resolve a base class within separate multiple packages
        import_module=["project*.example.*.models"],
        include_tables=set(),
        exclude_tables=set(),
        python_dir=[namespace_package_path],
        format="mermaid",
        column_sort="key-based",
    )
    # mermaid_assert(graph_string)


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


def test_get_graph_string_with_nested_glob_pattern(nested_package_path):
    """Integration test: get_graph_string with nested glob pattern."""

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
