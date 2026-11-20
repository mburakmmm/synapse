"""AST verification of strict package import DAG across packages/ and apps/."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGES_DIR = REPO_ROOT / "packages"
APPS_DIR = REPO_ROOT / "apps"

ALLOWED_INTERNAL_IMPORTS: dict[str, set[str]] = {
    "synapse_core": {"synapse_core"},
    "synapse_data": {"synapse_data"},
    "synapse_experiments": {"synapse_experiments", "synapse_core", "synapse_data"},
    "synapse_analysis": {"synapse_analysis"},
    "synapse_publication": {"synapse_publication", "synapse_analysis"},
    "synapse_cli": {
        "synapse_cli",
        "synapse_core",
        "synapse_data",
        "synapse_experiments",
        "synapse_analysis",
        "synapse_publication",
    },
}

FORBIDDEN_FRAMEWORK_IMPORTS_IN_CORE_PACKAGES = frozenset(
    {
        "fastapi",
        "starlette",
        "uvicorn",
        "sqlalchemy",
        "alembic",
        "psycopg",
        "synapse_api",
        "synapse_worker",
    }
)

FORBIDDEN_WEB_IMPORTS_IN_WORKER = frozenset({"fastapi", "starlette", "uvicorn"})


def _extract_top_level_imports(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    return imported


@pytest.mark.unit
def test_strict_import_direction() -> None:
    all_internal = set(ALLOWED_INTERNAL_IMPORTS) | {"synapse_api", "synapse_worker"}
    for pkg_name, allowed in ALLOWED_INTERNAL_IMPORTS.items():
        pkg_dir = PACKAGES_DIR / pkg_name
        assert pkg_dir.is_dir(), f"Missing package directory {pkg_dir}"
        for py_file in pkg_dir.rglob("*.py"):
            imports = _extract_top_level_imports(py_file)
            disallowed_internal = (imports & all_internal) - allowed
            assert not disallowed_internal, (
                f"{py_file.relative_to(REPO_ROOT)} imports disallowed internal package(s): "
                f"{sorted(disallowed_internal)} (allowed: {sorted(allowed)})"
            )
            disallowed_fw = imports & FORBIDDEN_FRAMEWORK_IMPORTS_IN_CORE_PACKAGES
            assert not disallowed_fw, (
                f"{py_file.relative_to(REPO_ROOT)} must stay framework-independent, "
                f"found forbidden import(s): {sorted(disallowed_fw)}"
            )

    api_dir = APPS_DIR / "api" / "synapse_api"
    assert api_dir.is_dir()
    for py_file in api_dir.rglob("*.py"):
        imports = _extract_top_level_imports(py_file)
        assert "synapse_worker" not in imports, (
            f"{py_file.relative_to(REPO_ROOT)} must not import synapse_worker"
        )

    worker_dir = APPS_DIR / "worker" / "synapse_worker"
    assert worker_dir.is_dir()
    for py_file in worker_dir.rglob("*.py"):
        imports = _extract_top_level_imports(py_file)
        disallowed_web = imports & FORBIDDEN_WEB_IMPORTS_IN_WORKER
        assert not disallowed_web, (
            f"{py_file.relative_to(REPO_ROOT)} must not import web frameworks: "
            f"{sorted(disallowed_web)}"
        )
