"""PHASE0 §7.3: module import boundary enforcement.

Covers:
- affect must not import planner, loop, or cli
- planner must not import github_ingest, bootstrap, loop, or cli
- planner must not read files, environment variables, or GitHub
- github_ingest must not import planner, bootstrap, loop, or cli
- schema must not import any project module
"""

from __future__ import annotations

import ast
import pathlib

SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "ubu_phase0"

_PROJECT_MODULES = frozenset(
    {"schema", "affect", "github_ingest", "planner", "bootstrap", "loop", "cli"}
)


def _imported_project_modules(filename: str) -> set[str]:
    """Return project-module names imported by a source file, via AST."""
    source = (SRC / filename).read_text()
    tree = ast.parse(source)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # e.g. "import ubu_phase0.planner"
                for part in alias.name.split("."):
                    if part in _PROJECT_MODULES:
                        found.add(part)
        elif isinstance(node, ast.ImportFrom):
            # e.g. "from ubu_phase0.planner import ..."
            if node.module:
                for part in node.module.split("."):
                    if part in _PROJECT_MODULES:
                        found.add(part)
            # e.g. "from ubu_phase0 import affect as _affect"
            for alias in node.names:
                if alias.name in _PROJECT_MODULES:
                    found.add(alias.name)
    return found


# ---------------------------------------------------------------------------
# affect
# ---------------------------------------------------------------------------


def test_affect_does_not_import_planner():
    imports = _imported_project_modules("affect.py")
    assert "planner" not in imports, "affect.py must not import planner"


def test_affect_does_not_import_loop():
    imports = _imported_project_modules("affect.py")
    assert "loop" not in imports, "affect.py must not import loop"


def test_affect_does_not_import_cli():
    imports = _imported_project_modules("affect.py")
    assert "cli" not in imports, "affect.py must not import cli"


# ---------------------------------------------------------------------------
# planner
# ---------------------------------------------------------------------------


def test_planner_does_not_import_github_ingest():
    imports = _imported_project_modules("planner.py")
    assert "github_ingest" not in imports, "planner.py must not import github_ingest"


def test_planner_does_not_import_bootstrap():
    imports = _imported_project_modules("planner.py")
    assert "bootstrap" not in imports, "planner.py must not import bootstrap"


def test_planner_does_not_import_loop():
    imports = _imported_project_modules("planner.py")
    assert "loop" not in imports, "planner.py must not import loop"


def test_planner_does_not_import_cli():
    imports = _imported_project_modules("planner.py")
    assert "cli" not in imports, "planner.py must not import cli"


# ---------------------------------------------------------------------------
# planner purity: no file I/O, environment variables, or GitHub
# ---------------------------------------------------------------------------


def test_planner_does_not_call_open():
    source = (SRC / "planner.py").read_text()
    assert "open(" not in source, "planner.py must not use open()"


def test_planner_does_not_read_os_environ():
    source = (SRC / "planner.py").read_text()
    assert "os.environ" not in source, "planner.py must not read os.environ"


def test_planner_does_not_call_os_getenv():
    source = (SRC / "planner.py").read_text()
    assert "os.getenv" not in source, "planner.py must not call os.getenv"


def test_planner_does_not_import_github_library():
    source = (SRC / "planner.py").read_text()
    tree = ast.parse(source)
    github_imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "github" in alias.name.lower():
                    github_imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and "github" in node.module.lower():
                github_imports.append(node.module)
    assert not github_imports, (
        f"planner.py must not import a GitHub library; found: {github_imports}"
    )


# ---------------------------------------------------------------------------
# github_ingest
# ---------------------------------------------------------------------------


def test_github_ingest_does_not_import_planner():
    imports = _imported_project_modules("github_ingest.py")
    assert "planner" not in imports, "github_ingest.py must not import planner"


def test_github_ingest_does_not_import_bootstrap():
    imports = _imported_project_modules("github_ingest.py")
    assert "bootstrap" not in imports, "github_ingest.py must not import bootstrap"


def test_github_ingest_does_not_import_loop():
    imports = _imported_project_modules("github_ingest.py")
    assert "loop" not in imports, "github_ingest.py must not import loop"


def test_github_ingest_does_not_import_cli():
    imports = _imported_project_modules("github_ingest.py")
    assert "cli" not in imports, "github_ingest.py must not import cli"


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------


def test_schema_does_not_import_any_project_module():
    imports = _imported_project_modules("schema.py")
    violations = imports & (_PROJECT_MODULES)
    assert not violations, (
        f"schema.py must not import any project module; found: {violations}"
    )
