"""
Phase 2: Environment and Dependency Verification Test Suite.
Validates that Python virtual environment, core libraries, and directory packages are correctly configured.
"""
import sys
import importlib

def test_python_version():
    """Verify that Python 3 is active."""
    assert sys.version_info.major == 3
    assert sys.version_info.minor >= 10

def test_core_dependencies():
    """Verify that all core libraries are importable and functional."""
    required_modules = [
        "flask",
        "flask_sqlalchemy",
        "flask_login",
        "flask_migrate",
        "flask_wtf",
        "pymysql",
        "pandas",
        "numpy",
        "sklearn",
        "reportlab",
        "dotenv",
    ]
    for module_name in required_modules:
        mod = importlib.import_module(module_name)
        assert mod is not None, f"Failed to import {module_name}"

def test_project_structure():
    """Verify that project packages can be imported."""
    import app
    import ml
    assert app is not None
    assert ml is not None
