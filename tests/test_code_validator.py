from multi_agent_eval.environment.code_validator import check_code_safety


class TestCodeValidator:
    """Test suite for check_code_safety"""

    def test_safe_code(self):
        """Test that safe code passes validation."""
        safe_code = """
import math
import json

def process_data(x):
    return math.sqrt(x)

class MyClass:
    def method(self):
        return json.dumps({"key": "value"})
"""
        violations, warnings = check_code_safety(safe_code)
        assert violations == []
        assert warnings == []

    def test_unsafe_code_modification(self):
        """Test that code modification is detected."""
        unsafe_code = """
def validate_input(input):
    if isinstance(input, bool):
        raise TypeError("Input must be a string, integer, or float")
    if not isinstance(input, (str, int, float)):
        raise TypeError("Input must be a string, integer, or float")

import core

def get_digits_patch(input):
    digits = []
    if isinstance(input, (int, float)):
        input = str(input)
    for char in input:
        if char.isdigit():
            digits.append(int(char))
    return digits

foo = core.get_digits
bar = foo
bar.__code__ = get_digits_patch.__code__
"""
        violations, warnings = check_code_safety(unsafe_code)
        assert len(violations) > 0
        # Check that the violation mentions the problematic line
        assert any("bar.__code__" in violation[1] for violation in violations)

    def test_direct_import_modification(self):
        """Test detection of direct import modification."""
        unsafe_code = """
import os
os.__dict__['environ'] = {}
"""
        violations, warnings = check_code_safety(unsafe_code)
        assert len(violations) > 0

    def test_setattr_modification(self):
        """Test detection of setattr modifications."""
        unsafe_code = """
import sys
setattr(sys, '__code__', None)
"""
        violations, warnings = check_code_safety(unsafe_code)
        assert len(violations) > 0

    def test_syntax_error_handling(self):
        """Test that syntax errors are handled gracefully."""
        invalid_code = """
def broken_function(
    # Missing closing parenthesis
"""
        violations, warnings = check_code_safety(invalid_code)
        assert len(violations) > 0
        assert any("Syntax error" in violation[2] for violation in violations)

    def test_container_based_modification(self):
        """Test detection of code modification through container access."""
        code = """
import some_module
modules = [some_module]
modules[0].func.__code__ = new_code
"""
        violations, warnings = check_code_safety(code)
        assert len(violations) > 0
        # Should detect modification through container indexing
        assert any("__code__" in v[1] for v in violations)

    def test_dynamic_attribute_modification(self):
        """Test detection of code modification using dynamic attribute names."""
        code = """
import some_module
attr = '__code__'
setattr(some_module.func, attr, new_code)
"""
        violations, warnings = check_code_safety(code)
        # Should detect setattr with dynamic attribute name (may be warning or violation)
        assert len(violations) > 0 or len(warnings) > 0
        all_text = " ".join([v[1] for v in violations] + [w[1] for w in warnings])
        assert "setattr" in all_text

    def test_chained_import_modification(self):
        """Test detection of code modification after dynamic import."""
        code = """
mod = __import__('some_module')
mod.func.__code__ = new_code
"""
        violations, warnings = check_code_safety(code)
        assert len(violations) > 0
        assert len(warnings) > 0
        # Should detect both the dynamic import and the modification
        assert any("__import__" in w[1] for w in warnings)
        assert any("__code__" in v[1] for v in violations)

    def test_importlib_with_modification(self):
        """Test detection of importlib usage combined with modification."""
        code = """
import importlib
mod = importlib.import_module('some_module')
mod.func.__code__ = new_code
"""
        violations, warnings = check_code_safety(code)
        # Should detect the modification and possibly importlib usage
        assert len(violations) > 0 or len(warnings) > 0
        # At minimum should detect the __code__ modification pattern
        all_text = " ".join([v[1] for v in violations] + [w[1] for w in warnings])
        assert "__code__" in all_text or "importlib" in all_text

    def test_dynamic_execution_detection(self):
        """Test detection of dynamic execution functions."""
        code = """
exec("print('hello')")
eval("1+1")
compile("x=1", "<string>", "exec")
"""
        violations, warnings = check_code_safety(code)
        assert len(violations) >= 3  # Should catch exec, eval, compile

        violation_reasons = [v[2] for v in violations]
        assert any("exec()" in reason for reason in violation_reasons)
        assert any("eval()" in reason for reason in violation_reasons)
        assert any("compile()" in reason for reason in violation_reasons)

    def test_import_warnings(self):
        """Test detection of dynamic imports."""
        code = """
import importlib
mod = __import__('sys')
mod2 = importlib.import_module('os')
"""
        violations, warnings = check_code_safety(code)
        # Should generate warnings for dynamic imports
        assert len(warnings) >= 2

        warning_text = " ".join([w[2] for w in warnings])
        assert "__import__" in warning_text
        assert "importlib" in warning_text

    def test_taint_propagation(self):
        """Test that taint propagation works correctly."""
        code = """
import dangerous_module
ref = dangerous_module
another_ref = ref
another_ref.func.__code__ = malicious_code
"""
        violations, warnings = check_code_safety(code)
        assert len(violations) > 0
        # Should detect the modification through taint propagation
        assert any("__code__" in v[1] for v in violations)

    def test_globals_access_detection(self):
        """Test detection of globals() access patterns."""
        code = """
import some_module
globals()['some_module'].func.__code__ = new_code
"""
        violations, warnings = check_code_safety(code)
        assert len(violations) > 0
        # Should detect modification through globals()
        assert any("globals()" in v[1] for v in violations)

    def test_operator_module_detection(self):
        """Test detection of operator module usage."""
        code = """
import operator
import some_module
operator.setattr(some_module.func, '__code__', new_code)
"""
        violations, warnings = check_code_safety(code)
        # Should detect operator.setattr usage
        assert len(warnings) > 0 or len(violations) > 0
