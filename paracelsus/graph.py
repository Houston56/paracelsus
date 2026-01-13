import importlib
import logging
import os
import re
import sys
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Dict, List, Optional, Set, Union

from sqlalchemy.schema import MetaData

from paracelsus.models.pattern import Pattern

from .config import Layouts
from .finders import ModuleFinder
from .transformers.dot import Dot
from .transformers.mermaid import Mermaid

transformers: Dict[str, type[Union[Mermaid, Dot]]] = {
    "mmd": Mermaid,
    "mermaid": Mermaid,
    "dot": Dot,
    "gv": Dot,
}

logger = logging.getLogger(__name__)


def to_module_name(root: Path, path: Path) -> str:
    """
    Converts a filesystem path to a Python dotted module string.
    Example: /root/app/models.py -> app.models
    """
    try:
        relative_path = path.resolve().relative_to(root)
    except ValueError:
        # Fallback if path is not relative to root (should not happen in normal usage)
        return path.name

    if path.is_file():
        clean_path = relative_path.with_suffix("")
    else:
        clean_path = relative_path

    return ".".join(clean_path.parts)


def consume_import_tasks(queue: Queue[dict], sentinel: object):
    while True:
        item = queue.get()

        if item is sentinel:
            break

        needs_wildcards_import, module_name = item.values()
        try:
            # Check if already loaded to save time
            if module_name in sys.modules:
                continue

            if needs_wildcards_import:
                exec(f"from {module_name} import *")
            else:
                importlib.import_module(module_name)

        except ImportError as e:
            logger.error(f"Failed to load {module_name}: {e}")
            raise e
        finally:
            queue.task_done()


def get_graph_string(
    *,
    base_class_path: str,
    import_module: List[str],
    include_tables: Set[str],
    exclude_tables: Set[str],
    python_dir: List[Path],
    format: str,
    column_sort: str,
    omit_comments: bool = False,
    max_enum_members: int = 0,
    layout: Optional[Layouts] = None,
    type_parameter_delimiter: str = "-",
) -> str:
    # Update the PYTHON_PATH to allow more module imports.
    sys.path.append(str(os.getcwd()))
    for dir in python_dir:
        sys.path.append(str(dir))

    # Import the base class so the metadata class can be extracted from it.
    # The metadata class is passed to the transformer.
    module_path, class_name = base_class_path.split(":", 2)
    base_module = importlib.import_module(module_path)
    base_class = getattr(base_module, class_name)
    metadata = base_class.metadata

    import_queue_sentinel = object()
    import_queue: Queue[Union[Dict[str, str], object]] = Queue()
    import_worker = Thread(target=consume_import_tasks, args=(import_queue, import_queue_sentinel), daemon=True)
    import_worker.start()
    # The modules holding the model classes have to be imported to get put in the metaclass model registry.
    # These modules aren't actually used in any way, so they are discarded.
    # They are also imported in scope of this function to prevent namespace pollution.
    for module_lookup_mask in import_module:
        module_path, import_modifier = module_lookup_mask, None

        if module_path.endswith(":*"):
            module_path, import_modifier = module_path.split(":", 1)

        pattern = Pattern(mask=module_path)

        if any(pattern.errors):
            raise ValueError(pattern.serialized_errors)

        current_root = Path.cwd()
        finder = ModuleFinder(current_root, pattern.tokens)
        needs_wildcards_import = import_modifier == "*"

        for file_path in finder.find():
            module_path = to_module_name(current_root, file_path)
            import_queue.put({"needs_wildcards_import": needs_wildcards_import, "module_name": module_path})

    import_queue.put(import_queue_sentinel)
    import_worker.join()

    # Grab a transformer.
    if format not in transformers:
        raise ValueError(f"Unknown Format: {format}")

    # Keep only the tables which were included / not-excluded
    include_tables = resolve_included_tables(
        include_tables=include_tables, exclude_tables=exclude_tables, all_tables=set(metadata.tables.keys())
    )
    filtered_metadata = filter_metadata(metadata=metadata, include_tables=include_tables)

    # Save the graph structure to string.
    # Note: type_parameter_delimiter only applies to Mermaid transformer
    if format in ["mermaid", "mmd"]:
        return str(
            Mermaid(
                filtered_metadata,
                column_sort,
                omit_comments=omit_comments,
                layout=layout,
                type_parameter_delimiter=type_parameter_delimiter,
            )
        )
    else:
        return str(Dot(filtered_metadata, column_sort, omit_comments=omit_comments))


def resolve_included_tables(
    include_tables: Set[str],
    exclude_tables: Set[str],
    all_tables: Set[str],
) -> Set[str]:
    """Resolves the final set of tables to include in the graph.

    Given sets of inclusions and exclusions and the set of all tables we define
    the following cases are:
    - Empty inclusion and empty exclusion -> include all tables.
    - Empty inclusion and some exclusions -> include all tables except the ones in the exclusion set.
    - Some inclusions and empty exclusion -> make sure tables in the inclusion set are present in
        all tables then include the tables in the inclusion set.
    - Some inclusions and some exclusions -> not resolvable, an error is raised.
    """
    match len(include_tables), len(exclude_tables):
        case 0, 0:
            return all_tables
        case 0, int():
            excluded = {table for table in all_tables if any(re.match(pattern, table) for pattern in exclude_tables)}
            return all_tables - excluded
        case int(), 0:
            included = {table for table in all_tables if any(re.match(pattern, table) for pattern in include_tables)}

            if not included:
                non_existent_tables = include_tables - all_tables
                raise ValueError(
                    f"Some tables to include ({non_existent_tables}) don't exist "
                    f"within the found tables ({all_tables})."
                )
            return included
        case _:
            raise ValueError(
                f"Only one or none of include_tables ({include_tables}) or exclude_tables"
                f"({exclude_tables}) can contain values."
            )


def filter_metadata(
    metadata: MetaData,
    include_tables: Set[str],
) -> MetaData:
    """Create a subset of the metadata based on the tables to include."""
    filtered_metadata = MetaData()
    for tablename, table in metadata.tables.items():
        if tablename in include_tables:
            if hasattr(table, "to_metadata"):
                # to_metadata is the new way to do this, but it's only available in newer versions of SQLAlchemy.
                table = table.to_metadata(filtered_metadata)
            else:
                # tometadata is deprecated, but we still need to support it for older versions of SQLAlchemy.
                table = table.tometadata(filtered_metadata)

    return filtered_metadata
