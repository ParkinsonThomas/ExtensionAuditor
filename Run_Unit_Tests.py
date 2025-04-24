import unittest
import sys
import os
import io
import contextlib

unit_test_path = os.path.join(os.path.dirname(__file__), "unit_tests")
sys.path.insert(0, os.path.abspath(unit_test_path))

unit_tests = [
    ("GUID_ListCreator", "test_GUID_ListCreator"),
    ("Extension_Scraper", "test_Extension_Scraper"),
    ("API_Auditor", "test_API_Auditor"),
    ("Extension_Analysis_Gitleaks", "test_Extension_Analysis_Gitleaks"),
    ("Extension_Analysis_Esprima", "test_Extension_Analysis_Esprima"),
]

def run_test_module(label, module_name):
    print(f"\nRunning {label} unit tests...")
    try:
        module = __import__(module_name)
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = unittest.TextTestRunner(verbosity=0).run(suite)

        total = result.testsRun
        passed = total - len(result.failures) - len(result.errors)
        print(f"Ran {total} tests, {passed} passed")
    except ModuleNotFoundError as e:
        print(f"ERROR: {e}")
def main():
    for label, module_name in unit_tests:
        run_test_module(label, module_name)

if __name__ == '__main__':
    main()