# -----------------------------------------------------------------------------
# run_tests.py
# MicroPython-friendly test runner entry point.
# -----------------------------------------------------------------------------

"""Run the CPython unit test suite from the project root.

Usage:
    python -m unittest discover -s tests
or:
    python tests/run_tests.py
"""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
# Check this condition so only the matching signal/data case is handled here.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Check this condition so only the matching signal/data case is handled here.
if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
