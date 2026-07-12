import subprocess
import re
import ast
import os
import platform

def detect_test_framework(test_target):
    """
    Returns 'unittest' if the test file imports unittest / uses TestCase,
    otherwise defaults to 'pytest'.
    """
    path = test_target
    if os.path.isdir(path):
        candidates = [f for f in os.listdir(path) if f.startswith("test_") and f.endswith(".py")]
        if not candidates:
            return "pytest"
        path = os.path.join(path, candidates[0])

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return "pytest"

    if "unittest.TestCase" in content or re.search(r"^\s*import unittest\b", content, re.MULTILINE):
        return "unittest"
    return "pytest"


def run_tests(test_target, project_dir=None, language="python", framework="pytest"):
    if language == "javascript":
        use_shell = platform.system() == "Windows"
        result = subprocess.run(
            ["npx", "jest", test_target, "--no-coverage", "--colors=false"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=project_dir, shell=use_shell
        )
    elif framework == "unittest":
        module_name = os.path.splitext(os.path.basename(test_target))[0]
        result = subprocess.run(
            ["python", "-m", "unittest", "-v", module_name],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=project_dir or os.path.dirname(os.path.abspath(test_target))
        )
    else:
        result = subprocess.run(
            ["pytest", test_target, "--tb=short", "-q"],
            capture_output=True, text=True
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

def get_related_files(code_file, project_dir, max_files=3):
    """
    Finds other project source files that `code_file` imports, so the LLM
    sees cross-file context instead of just one isolated file.
    Returns a dict {filename: content}.
    """
    try:
        with open(code_file, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=code_file)
    except (SyntaxError, OSError):
        return {}

    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module.split(".")[-1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.name.split(".")[0])

    related = {}
    for name in imported_names:
        candidate = os.path.join(project_dir, name + ".py")
        if os.path.exists(candidate) and os.path.abspath(candidate) != os.path.abspath(code_file):
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    related[name + ".py"] = f.read()[:1500]  # capped so prompts stay manageable
            except OSError:
                continue
        if len(related) >= max_files:
            break

    return related

def detect_project_language(project_dir):
    """
    Returns 'javascript' if the folder looks like a Node project, else defaults to 'python'.
    """
    if os.path.exists(os.path.join(project_dir, "package.json")):
        return "javascript"
    return "python"


def run_tests(test_target, project_dir=None, language="python", framework="pytest"):
    if language == "javascript":
        use_shell = platform.system() == "Windows"
        result = subprocess.run(
            ["npx", "jest", test_target, "--no-coverage", "--colors=false"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=project_dir, shell=use_shell
        )
    elif framework == "unittest":
        module_name = os.path.splitext(os.path.basename(test_target))[0]
        result = subprocess.run(
            ["python", "-m", "unittest", "-v", module_name],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=project_dir or os.path.dirname(os.path.abspath(test_target))
        )
    else:
        result = subprocess.run(
            ["pytest", test_target, "--tb=short", "-q"],
            capture_output=True, text=True
        )

    return {
        "passed": result.returncode == 0,
        "output": result.stdout + result.stderr,
        "returncode": result.returncode
    }

def _resolve_js_import_path(module_path, test_dir):
    """Only chases local relative imports (./something) -- skips npm packages."""
    if not module_path.startswith("."):
        return None
    resolved = os.path.normpath(os.path.join(test_dir, module_path))
    if not resolved.endswith(".js"):
        resolved += ".js"
    return resolved


def _build_js_import_map(test_file_path):
    """
    Regex-based equivalent of Python's ast-based import map.
    JS has no built-in equivalent to Python's `ast` module for this,
    so we pattern-match the common require()/import styles instead.
    """
    import_map = {}
    test_dir = os.path.dirname(test_file_path)
    try:
        with open(test_file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return {}

    # const { add, sub } = require('./math')
    for m in re.finditer(r"(?:const|let|var)\s*\{([^}]+)\}\s*=\s*require\(['\"](.+?)['\"]\)", content):
        names = [n.strip().split(":")[0].strip() for n in m.group(1).split(",")]
        resolved = _resolve_js_import_path(m.group(2), test_dir)
        if resolved:
            for name in names:
                import_map[name] = resolved

    # const math = require('./math')
    for m in re.finditer(r"(?:const|let|var)\s+(\w+)\s*=\s*require\(['\"](.+?)['\"]\)", content):
        resolved = _resolve_js_import_path(m.group(2), test_dir)
        if resolved:
            import_map[m.group(1)] = resolved

    # import { add } from './math'
    for m in re.finditer(r"import\s*\{([^}]+)\}\s*from\s*['\"](.+?)['\"]", content):
        names = [n.strip().split(" as ")[0].strip() for n in m.group(1).split(",")]
        resolved = _resolve_js_import_path(m.group(2), test_dir)
        if resolved:
            for name in names:
                import_map[name] = resolved

    # import math from './math'
    for m in re.finditer(r"import\s+(\w+)\s+from\s*['\"](.+?)['\"]", content):
        resolved = _resolve_js_import_path(m.group(2), test_dir)
        if resolved:
            import_map[m.group(1)] = resolved

    return import_map


def _get_failed_jest_files(jest_output):
    """Extracts test file paths from Jest's 'FAIL <path>' summary lines."""
    return re.findall(r"^FAIL\s+(.+)$", jest_output, re.MULTILINE)


def find_failing_files_js(jest_output, project_dir):
    """
    JS equivalent of find_failing_files(). Since Jest assertion failures
    don't leave a traceback into the source file (same issue as pytest),
    we check which imported names actually appear in the failing test file.
    """
    implicated = []
    seen = set()

    for test_file in _get_failed_jest_files(jest_output):
        test_file_abs = test_file if os.path.isabs(test_file) else os.path.join(project_dir, test_file)
        import_map = _build_js_import_map(test_file_abs)

        try:
            with open(test_file_abs, "r", encoding="utf-8") as f:
                test_content = f.read()
        except (OSError, UnicodeDecodeError):
            continue

        for name, file_path in import_map.items():
            if re.search(rf"\b{re.escape(name)}\b", test_content) and os.path.exists(file_path):
                abs_path = os.path.abspath(file_path)
                if abs_path not in seen:
                    seen.add(abs_path)
                    implicated.append(abs_path)

    return implicated


def get_related_files_js(code_file, project_dir, max_files=3):
    """JS equivalent of get_related_files() -- reuses the same import map builder."""
    import_map = _build_js_import_map(code_file)
    related = {}
    for name, path in import_map.items():
        if os.path.abspath(path) == os.path.abspath(code_file):
            continue
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    related[os.path.basename(path)] = f.read()[:1500]
            except OSError:
                continue
        if len(related) >= max_files:
            break
    return related

def _get_failed_unittest_tests(output):
    """Extracts (test_name, module.ClassName) from unittest's 'FAIL: test_name (module.Class)' lines."""
    return re.findall(r"^FAIL: (\w+) \(([\w.]+)\)", output, re.MULTILINE)


def find_failing_files_unittest(pytest_output, project_dir, test_file_path):
    """
    unittest failure lines include the module name directly:
    'FAIL: test_greet (test_greeter.TestGreeter)' -- the 'test_greeter' part
    tells us exactly which file to look in, so we resolve it instead of guessing.
    """
    implicated = []
    seen = set()

    for test_name, class_path in _get_failed_unittest_tests(pytest_output):
        module_name = class_path.split(".")[0]
        resolved_test_file = os.path.join(project_dir, module_name + ".py")

        if not os.path.exists(resolved_test_file):
            resolved_test_file = test_file_path  # fallback to the original assumption

        import_map = _build_import_map(resolved_test_file)
        used_names = _find_used_names(resolved_test_file, test_name)

        for name in used_names:
            if name in import_map:
                candidate = os.path.abspath(os.path.join(project_dir, import_map[name]))
                if os.path.exists(candidate) and candidate not in seen:
                    seen.add(candidate)
                    implicated.append(candidate)

    return implicated