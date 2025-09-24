#!/usr/bin/env python3
"""
Test runner for the webserver package.
"""

import sys
import subprocess
import os


def run_tests():
    """Run all tests with coverage reporting."""

    # Change to webserver directory
    webserver_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(webserver_dir)

    print("Running webserver tests...")
    print("=" * 50)

    # Add src to Python path
    src_path = os.path.join(webserver_dir, "src")
    env = os.environ.copy()
    env["PYTHONPATH"] = src_path + ":" + env.get("PYTHONPATH", "")

    # Run pytest with coverage
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "-v",
        "--cov=webserver",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--tb=short",
    ]

    try:
        result = subprocess.run(cmd, check=False, env=env)

        if result.returncode == 0:
            print("\n" + "=" * 50)
            print("✅ All tests passed!")
            print("📊 Coverage report generated in htmlcov/")
        else:
            print("\n" + "=" * 50)
            print("❌ Some tests failed!")
            return False

    except FileNotFoundError:
        print("❌ pytest not found. Please install test requirements:")
        print("   pip install -r requirements-test.txt")
        return False

    return result.returncode == 0


def run_specific_test(test_file):
    """Run a specific test file."""

    webserver_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(webserver_dir)

    cmd = [sys.executable, "-m", "pytest", f"tests/{test_file}", "-v", "--tb=short"]

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ pytest not found. Please install test requirements:")
        print("   pip install -r requirements-test.txt")
        return False


def main():
    """Main entry point."""

    if len(sys.argv) > 1:
        # Run specific test file
        test_file = sys.argv[1]
        if not test_file.startswith("test_"):
            test_file = f"test_{test_file}"
        if not test_file.endswith(".py"):
            test_file = f"{test_file}.py"

        print(f"Running specific test: {test_file}")
        success = run_specific_test(test_file)
    else:
        # Run all tests
        success = run_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
