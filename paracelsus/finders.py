import fnmatch
import importlib
import os
import pkgutil
import re
import types
from typing import List, Set, Optional


def _get_package_paths(package: types.ModuleType) -> List[str]:
    """Get all paths for a package, handling namespace packages.
    Namespace packages (PEP 420) can have multiple paths in __path__.
    """
    if not hasattr(package, "__path__"):
        return []

    paths = package.__path__

    # Handle _NamespacePath and other iterable path objects
    try:
        if hasattr(paths, "__iter__") and not isinstance(paths, (str, bytes)):
            return [str(p) for p in paths]
    except (TypeError, ValueError):
        pass

    return [str(paths)]


def _match_pattern(name: str, pattern: str) -> bool:
    """Match a name against a glob pattern.

    Supports standard fnmatch patterns plus character classes with prefix (e.g., "v[12]").
    """
    # Handle character classes with prefix (e.g., "v[12]")
    # fnmatch doesn't support this directly, so we need custom handling
    char_class_match = re.search(r"\[([!]?)([^\]]+)\]", pattern)
    if char_class_match and not pattern.startswith("["):
        # Pattern has a prefix before the character class
        prefix = pattern[: char_class_match.start()]
        char_class_content = char_class_match.group(2)
        negation = char_class_match.group(1) == "!"

        # Check prefix first
        if not name.startswith(prefix):
            return False

        # Check character class - must match exactly one character
        remaining = name[len(prefix) :]
        if len(remaining) != 1:
            return False

        char = remaining[0]

        # Handle ranges like [0-9]
        if "-" in char_class_content and len(char_class_content) == 3:
            start, end = char_class_content[0], char_class_content[2]
            if negation:
                return not (start <= char <= end)
            return start <= char <= end

        # Handle character sets like [12] or [abc]
        if negation:
            return char not in char_class_content
        return char in char_class_content

    # Use fnmatch for standard patterns (*, ?, [abc], etc.)
    return fnmatch.fnmatch(name, pattern)


def _get_modules_in_path(path: str, package_name: str) -> Set[tuple[str, bool]]:
    """Get all modules and packages in a given path."""

    items = set()

    # Use pkgutil for standard modules/packages
    try:
        for importer, modname, ispkg in pkgutil.iter_modules([path]):
            items.add((modname, ispkg))
    except (OSError, TypeError):
        pass

    # Also check directories for namespace packages (without __init__.py)
    try:
        for item in os.listdir(path):
            if item.startswith(".") or item == "__pycache__":
                continue
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path) and item not in [name for name, _ in items]:
                # Try to import to verify it's a valid package
                try:
                    full_name = f"{package_name}.{item}" if package_name else item
                    test_module = importlib.import_module(full_name)
                    is_package = hasattr(test_module, "__path__")
                    items.add((item, is_package))
                except (ImportError, ValueError):
                    pass
    except (OSError, PermissionError):
        pass

    return items


def _find_modules_recursive(
    package_name: str,
    package_paths: List[str],
    pattern_segments: List[str],
    found_modules: Optional[Set[str]] = None,
) -> Set[str]:
    """Recursively find modules matching pattern segments."""

    if found_modules is None:
        found_modules = set()

    # Base case: no more segments to match
    if not pattern_segments:
        found_modules.add(package_name)
        return found_modules

    current_pattern = pattern_segments[0]
    remaining_patterns = pattern_segments[1:]

    # Handle recursive pattern (**)
    if current_pattern == "**":
        # ** matches zero or more levels
        # First, try matching remaining segments at current level (zero levels)
        if remaining_patterns:
            _find_modules_recursive(
                package_name,
                package_paths,
                remaining_patterns,
                found_modules,
            )

        # Then, recursively search all subpackages (one or more levels)
        for path in package_paths:
            path_str = str(path) if not isinstance(path, str) else path
            items = _get_modules_in_path(path_str, package_name)

            for modname, ispkg in items:
                subpackage_name = f"{package_name}.{modname}" if package_name else modname
                try:
                    subpackage = importlib.import_module(subpackage_name)
                    subpackage_paths = _get_package_paths(subpackage)

                    if subpackage_paths:
                        # Continue recursive search with ** pattern
                        _find_modules_recursive(
                            subpackage_name,
                            subpackage_paths,
                            pattern_segments,
                            found_modules,
                        )
                except (ImportError, AttributeError):
                    continue

    # Handle normal segments
    else:
        for path in package_paths:
            path_str = str(path) if not isinstance(path, str) else path
            items = _get_modules_in_path(path_str, package_name)

            for modname, ispkg in items:
                # Check if name matches current pattern
                if not _match_pattern(modname, current_pattern):
                    continue

                subpackage_name = f"{package_name}.{modname}" if package_name else modname

                # If this is the last segment, add it
                if not remaining_patterns:
                    found_modules.add(subpackage_name)
                else:
                    # Continue searching in subpackage
                    try:
                        subpackage = importlib.import_module(subpackage_name)
                        subpackage_paths = _get_package_paths(subpackage)

                        if subpackage_paths:
                            _find_modules_recursive(
                                subpackage_name,
                                subpackage_paths,
                                remaining_patterns,
                                found_modules,
                            )
                    except (ImportError, AttributeError):
                        continue

    return found_modules


def find_modules_by_pattern(pattern: str) -> List[str]:
    """Finds all modules that match the glob-like pattern for Python modules.

    Supports patterns like:
        - example.*.models
        - example.fo?.models
        - example.*.*.models
        - example.**.api.*.models
        - example.api.v[12].models
        - example.api.v[0-9].models
        - example.api.v[!1].models
    """
    # Validate pattern
    if ".." in pattern:
        raise ValueError(f"Invalid pattern '{pattern}': consecutive dots are not allowed")

    if "," in pattern:
        raise ValueError(f"Invalid pattern '{pattern}': invalid delimiter, commas are not valid delimiters, use dots")

    # Split pattern into segments
    segments = [s for s in pattern.split(".") if s]

    if not segments:
        raise ValueError(f"Invalid pattern '{pattern}': pattern cannot be empty")

    # Find base package (all literal segments before first wildcard)
    base_parts = []
    for seg in segments:
        # Check if segment contains any wildcard characters
        if any(c in seg for c in "*?["):
            break
        base_parts.append(seg)

    if not base_parts:
        raise ValueError(f"Invalid pattern '{pattern}': pattern must start with at least one literal package name")

    # Import base package
    base_name = ".".join(base_parts)
    try:
        base_package = importlib.import_module(base_name)
    except ImportError as e:
        raise ValueError(f"Cannot import base package '{base_name}': {e}")

    base_paths = _get_package_paths(base_package)
    if not base_paths:
        raise ValueError(f"Package '{base_name}' is not a package (no __path__)")

    # Remaining pattern segments
    remaining_segments = segments[len(base_parts) :]

    # Start recursive search
    found_modules = _find_modules_recursive(
        base_name,
        base_paths,
        remaining_segments,
    )

    return sorted(list(found_modules))
