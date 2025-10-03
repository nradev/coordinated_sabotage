#!/usr/bin/env python3
"""
Test runner script for the webserver.
"""

import subprocess
import sys
import os


def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{'=' * 60}")
    print(f"🔍 {description}")
    print(f"{'=' * 60}")

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.stdout:
            print(result.stdout)

        if result.stderr:
            print("STDERR:", result.stderr)

        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED (exit code: {result.returncode})")
            return False

    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False


def main():
    """Run all tests and checks."""
    print("🚀 Running Webserver Test Suite")
    print("=" * 60)

    # Change to webserver directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    results = []

    # 1. Run unit tests
    results.append(run_command("uv run pytest tests/ -v", "Unit Tests"))

    # 2. Run tests with coverage
    results.append(
        run_command(
            "uv run pytest tests/ --cov=webserver --cov-report=term-missing",
            "Test Coverage",
        )
    )

    # 3. Code formatting check
    results.append(run_command("uv run ruff format --check .", "Code Formatting Check"))

    # 4. Linting
    results.append(run_command("uv run ruff check .", "Code Linting"))

    # 5. Type checking
    results.append(
        run_command(
            "uv run mypy src/webserver --ignore-missing-imports", "Type Checking"
        )
    )

    # 6. Import test
    results.append(
        run_command(
            "uv run python -c 'from webserver import WebServer, Response; print(\"✅ Import test passed\")'",
            "Import Test",
        )
    )

    # 7. Basic functionality test
    results.append(
        run_command(
            "uv run python -c 'from demo import create_demo_server; app = create_demo_server(); print(\"✅ Demo creation test passed\")'",
            "Demo Creation Test",
        )
    )

    # Summary
    print(f"\n{'=' * 60}")
    print("📊 TEST SUMMARY")
    print(f"{'=' * 60}")

    passed = sum(results)
    total = len(results)

    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {total - passed}")
    print(f"📈 Success Rate: {passed / total * 100:.1f}%")

    if passed == total:
        print("\n🎉 All tests passed! The webserver is ready for use.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
