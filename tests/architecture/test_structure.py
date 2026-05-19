"""
Architecture structure tests.
Validates file naming conventions and ensures that critical layers have corresponding tests.
"""

import pathlib

SRC_DIR = pathlib.Path("src/app")
TESTS_DIR = pathlib.Path("tests")


def test_every_domain_file_has_a_unit_test() -> None:
    """Enforces that every file in the domain layer has a matching unit test."""
    domain_dir = SRC_DIR / "domain"

    missing_tests = []
    for py_file in domain_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        # e.g., src/app/domain/models/item.py -> tests/unit/domain/models/test_item.py
        rel_path = py_file.relative_to(SRC_DIR)
        test_file = TESTS_DIR / "unit" / rel_path.parent / f"test_{py_file.name}"

        if not test_file.exists():
            missing_tests.append(f"{py_file} (expected test at {test_file})")

    assert not missing_tests, (
        "Architecture Violation: Domain files must have corresponding unit tests!\n"
        + "\n".join(missing_tests)
    )


def test_every_application_file_has_a_unit_test() -> None:
    """Enforces that every file in the application layer has a matching unit test."""
    app_dir = SRC_DIR / "application"

    missing_tests = []
    for py_file in app_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        # Exclude ports from requiring unit tests (they are ABCs and are tested via Contract tests)
        if "ports" in py_file.parts:
            continue

        rel_path = py_file.relative_to(SRC_DIR)
        test_file = TESTS_DIR / "unit" / rel_path.parent / f"test_{py_file.name}"

        if not test_file.exists():
            missing_tests.append(f"{py_file} (expected test at {test_file})")

    assert not missing_tests, (
        "Architecture Violation: Application files (Use Cases) must have corresponding unit tests!\n"
        + "\n".join(missing_tests)
    )


def test_use_cases_naming_convention() -> None:
    """Enforces that all files in the use_cases folder end with _use_case.py"""
    use_cases_dir = SRC_DIR / "application" / "use_cases"

    violations = []
    for py_file in use_cases_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        if not py_file.name.endswith("_use_case.py"):
            violations.append(str(py_file))

    assert not violations, (
        "Architecture Violation: Use Cases must be named `*_use_case.py`!\n"
        + "\n".join(violations)
    )


def test_ports_naming_convention() -> None:
    """Enforces that all files in the ports folders end with _port.py"""
    ports_dir = SRC_DIR / "application" / "ports"

    violations = []
    for py_file in ports_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        if not py_file.name.endswith("_port.py"):
            violations.append(str(py_file))

    assert not violations, (
        "Architecture Violation: Ports must be named `*_port.py`!\n"
        + "\n".join(violations)
    )
