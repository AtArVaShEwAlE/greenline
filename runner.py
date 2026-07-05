import subprocess
import re
import ast
import os


def run_tests(test_target):
    """
    test_target can be a single test file OR a folder (pytest auto-discovers tests inside it).
    """
    result = subprocess.run(
        ["pytest", test_target, "--tb=short", "-q"],
        capture_output=True,
        text=True
    )
    return {
        "passed": result.returncode == 0,
        "output": result.stdout + result.stderr,
        "returncode": result.returncode
    }


def _get_failed_test_locations(pytest_output):
    """
    Extracts (test_file_path, test_function_name) pairs from pytest's
    'FAILED path::test_name - ...' summary lines.
    """
    locations = []
    for line in pytest_output.splitlines():
        line = line.strip()
        if line.startswith("FAILED"):
            match = re.match(r"FAILED (.+?)::(\w+)", line)
            if match:
                locations.append((match.group(1), match.group(2)))
    return locations


def _build_import_map(test_file_path):
    """
    Parses a test file's import statements and maps every imported name
    (function, class, or module) to the .py filename it came from.
    e.g. "from inventory import Inventory" -> {"Inventory": "inventory.py"}
    """
    try:
        with open(test_file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=test_file_path)
    except (SyntaxError, FileNotFoundError, OSError):
        return {}

    import_map = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            file_name = node.module.split(".")[-1] + ".py"
            for alias in node.names:
                name = alias.asname or alias.name
                import_map[name] = file_name
        elif isinstance(node, ast.Import):
            for alias in node.names:
                base = alias.name.split(".")[0]
                name = alias.asname or base
                import_map[name] = base + ".py"
    return import_map


def _find_used_names(test_file_path, test_name):
    """
    Returns the set of identifier names referenced inside one specific
    test function's body (e.g. {"inv", "has_enough"} for a test that calls it).
    """
    try:
        with open(test_file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=test_file_path)
    except (SyntaxError, FileNotFoundError, OSError):
        return set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == test_name:
            return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
    return set()


def find_failing_files(pytest_output, project_dir):
    """
    Determines which source files are implicated in the failing tests by statically
    analyzing which imported names each failing test function actually references.

    This works even when a bug causes a wrong RETURN VALUE (no exception, no traceback
    into the source file) -- which regular traceback parsing cannot detect.
    """
    implicated = []
    seen = set()

    for test_file, test_name in _get_failed_test_locations(pytest_output):
        import_map = _build_import_map(test_file)
        used_names = _find_used_names(test_file, test_name)

        for name in used_names:
            if name in import_map:
                candidate = os.path.abspath(os.path.join(project_dir, import_map[name]))
                if os.path.exists(candidate) and candidate not in seen:
                    seen.add(candidate)
                    implicated.append(candidate)

    return implicated