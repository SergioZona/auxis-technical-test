"""
Architecture boundary enforcement tests.
Uses import-linter contracts defined in pyproject.toml.
Run: uv run lint-imports
These tests fail CI if any layer imports violate the hexagonal contract.
"""


def test_import_linter_contracts_pass() -> None:
    """
    Validates that all import-linter contracts defined in pyproject.toml pass.
    Enforces:
      - Domain has no upward imports
      - Application has no infrastructure imports
      - Layers are correctly ordered
    """
    from importlinter.cli import lint_imports

    result = lint_imports()
    assert result == 0, "Architecture boundary violation detected!"


def test_domain_does_not_import_application() -> None:
    """Spot-check: domain models must not reference application layer."""
    import ast
    import pathlib

    domain_dir = pathlib.Path("src/app/domain")
    violations = []

    for py_file in domain_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = (
                    node.module
                    if isinstance(node, ast.ImportFrom)
                    else ",".join(a.name for a in node.names)
                ) or ""
                if "app.application" in module or "app.infrastructure" in module:
                    violations.append(f"{py_file}: imports '{module}'")

    assert not violations, "Domain layer has forbidden imports:\n" + "\n".join(
        violations
    )
