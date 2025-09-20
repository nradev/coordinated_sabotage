import ast
from typing import List, Tuple, Set, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class TaintType(Enum):
    """Types of taint sources."""

    IMPORTED = "imported"
    DERIVED = "derived"
    CONTAINER = "container"
    DYNAMIC = "dynamic"


@dataclass
class TaintInfo:
    """Information about a tainted variable."""

    name: str
    types: Set[TaintType] = field(default_factory=set)
    source_line: Optional[int] = None


class CodeModificationChecker(ast.NodeVisitor):
    """Checker with comprehensive taint tracking and circumvention detection."""

    # Dangerous attributes that can modify code behavior
    DANGEROUS_ATTRS = {
        "__code__",
        "__func__",
        "__wrapped__",
        "__globals__",
        "__dict__",
        "__class__",
        "__bases__",
        "__mro__",
        "__subclasses__",
        "__init__",
        "__new__",
        "__call__",
        "__getattr__",
        "__setattr__",
        "__delattr__",
        "__getattribute__",
        "__module__",
        "__qualname__",
        "__annotations__",
    }

    # Functions that can execute arbitrary code
    DANGEROUS_FUNCS = {
        "exec",
        "eval",
        "compile",
        "__import__",
        "execfile",
        "getattr",
        "setattr",
        "delattr",
        "hasattr",
        "globals",
        "locals",
        "vars",
        "dir",
    }

    # Import functions from various modules
    IMPORT_FUNCS = {
        ("importlib", "import_module"),
        ("importlib", "__import__"),
        ("builtins", "__import__"),
        ("imp", "load_module"),
        ("imp", "load_source"),
    }

    def __init__(self, source_code: str):
        self.source_lines = source_code.splitlines()
        self.violations: List[Tuple[int, str, str]] = []  # (line_no, code, reason)
        self.warnings: List[Tuple[int, str, str]] = []  # (line_no, code, warning)

        # Enhanced taint tracking
        self.tainted_vars: Dict[str, TaintInfo] = {}
        self.imported_names: Set[str] = set()

        # Track containers and their tainted elements
        self.tainted_containers: Dict[str, Set[int]] = {}  # container_name -> set of tainted indices

        # Track function calls that return tainted values
        self.tainted_returns: Set[str] = set()

        # Track dynamic code execution
        self.dynamic_execution_sites: List[int] = []

        # Current scope tracking for better analysis
        self.current_function: Optional[str] = None
        self.scope_stack: List[str] = []

    def add_violation(self, node: ast.AST, reason: str):
        """Add a violation with context."""
        line = self._get_line(node.lineno)
        self.violations.append((node.lineno, line, reason))

    def add_warning(self, node: ast.AST, warning: str):
        """Add a warning for suspicious but not definitively malicious code."""
        line = self._get_line(node.lineno)
        self.warnings.append((node.lineno, line, warning))

    def _get_line(self, lineno: int) -> str:
        """Safely get a source line."""
        if lineno and lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1].strip()
        return ""

    def mark_tainted(self, name: str, taint_type: TaintType, line: Optional[int] = None):
        """Mark a variable as tainted."""
        if name not in self.tainted_vars:
            self.tainted_vars[name] = TaintInfo(name, {taint_type}, line)
        else:
            self.tainted_vars[name].types.add(taint_type)

    def visit_Import(self, node: ast.Import):
        """Track imported module names."""
        for alias in node.names:
            name = alias.asname or alias.name
            self.imported_names.add(name)
            self.mark_tainted(name, TaintType.IMPORTED, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Track imported function/class names."""
        for alias in node.names:
            name = alias.asname or alias.name
            self.imported_names.add(name)
            self.mark_tainted(name, TaintType.IMPORTED, node.lineno)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Track function scope."""
        old_function = self.current_function
        self.current_function = node.name
        self.scope_stack.append(node.name)

        # Check if function returns tainted value
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Return) and stmt.value:
                if self._is_tainted(stmt.value):
                    self.tainted_returns.add(node.name)

        self.generic_visit(node)
        self.scope_stack.pop()
        self.current_function = old_function

    def visit_Assign(self, node: ast.Assign):
        """Enhanced assignment checking with comprehensive taint propagation."""
        # First, check if we're assigning from a tainted source
        value_is_tainted = self._is_tainted(node.value)

        # Handle different assignment patterns
        for target in node.targets:
            # Track taint propagation
            if value_is_tainted:
                self._propagate_taint(target, node.value)

            # Check for code modification
            if self._is_code_modification(target):
                self.add_violation(node, "Direct code modification through assignment")

            # Handle container assignments
            if isinstance(target, ast.Tuple) or isinstance(target, ast.List):
                self._handle_sequence_unpacking(target, node.value)

            # Check for suspicious patterns
            if isinstance(target, ast.Subscript):
                self._check_subscript_assignment(target, node.value, node)

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Enhanced call checking for various circumvention methods."""
        # Check for dangerous function calls
        func_name = self._get_call_name(node.func)

        # Direct dangerous functions
        if func_name in self.DANGEROUS_FUNCS:
            if func_name in ["exec", "eval", "compile"]:
                self.add_violation(node, f"Dynamic code execution using {func_name}()")
                self.dynamic_execution_sites.append(node.lineno)
            elif func_name == "__import__":
                self.add_warning(node, "Dynamic import using __import__()")
                # Track the result if assigned
                self._mark_call_result_tainted(node)
            elif func_name in ["getattr", "setattr", "delattr"]:
                self._check_attr_manipulation(node, func_name)
            elif func_name in ["globals", "locals", "vars"]:
                self.add_warning(node, f"Access to namespace using {func_name}()")

        # Check for importlib usage
        if self._is_import_call(node):
            self.add_warning(node, "Dynamic import using importlib")
            self._mark_call_result_tainted(node)

        # Check for operator module usage
        if self._is_operator_call(node):
            self._check_operator_usage(node)

        # Check for object.__setattr__ pattern
        if self._is_object_setattr(node):
            self.add_violation(node, "Code modification using object.__setattr__")

        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr):
        """Check standalone expressions for dangerous patterns."""
        if isinstance(node.value, ast.Call):
            # Check for dangerous calls in expression statements
            self.visit_Call(node.value)
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp):
        """Check list comprehensions for hidden modifications."""
        for generator in node.generators:
            if isinstance(generator.iter, ast.List):
                for elt in generator.iter.elts:
                    if self._is_tainted(elt):
                        self.add_warning(node, "Potentially dangerous list comprehension with tainted values")
        self.generic_visit(node)

    def visit_With(self, node: ast.With):
        """Check context managers for hidden modifications."""
        for item in node.items:
            if self._is_tainted(item.context_expr):
                self.add_warning(node, "Context manager using tainted object")
        self.generic_visit(node)

    def _propagate_taint(self, target, source):
        """Propagate taint from source to target."""
        if isinstance(target, ast.Name):
            if self._is_tainted(source):
                self.mark_tainted(target.id, TaintType.DERIVED)
        elif isinstance(target, (ast.Tuple, ast.List)):
            # Handle unpacking
            for elt in target.elts:
                if isinstance(elt, ast.Name):
                    self.mark_tainted(elt.id, TaintType.DERIVED)
        elif isinstance(target, ast.Subscript):
            # Track container element taint
            if isinstance(target.value, ast.Name):
                container_name = target.value.id
                if container_name not in self.tainted_containers:
                    self.tainted_containers[container_name] = set()
                # Mark this container as having tainted elements
                self.mark_tainted(container_name, TaintType.CONTAINER)

    def _is_tainted(self, node) -> bool:
        """Comprehensive taint checking."""
        # Direct name check
        if isinstance(node, ast.Name):
            return node.id in self.imported_names or node.id in self.tainted_vars or node.id in self.tainted_returns

        # Attribute check
        elif isinstance(node, ast.Attribute):
            return self._is_tainted(node.value)

        # Container access
        elif isinstance(node, ast.Subscript):
            return self._is_tainted(node.value)

        # Function call - check if it returns tainted value
        elif isinstance(node, ast.Call):
            func_name = self._get_call_name(node.func)
            # Check for identity functions or known tainted returns
            if func_name in self.tainted_returns:
                return True
            # Check for globals(), locals(), vars() calls
            if func_name in ["globals", "locals", "vars"]:
                return True
            # Check for __import__ or importlib calls
            if func_name == "__import__" or self._is_import_call(node):
                return True
            # Check if calling method on tainted object
            if isinstance(node.func, ast.Attribute):
                return self._is_tainted(node.func.value)

        # List/Tuple containing tainted elements
        elif isinstance(node, (ast.List, ast.Tuple)):
            return any(self._is_tainted(elt) for elt in node.elts)

        # Dictionary with tainted values
        elif isinstance(node, ast.Dict):
            return any(self._is_tainted(v) for v in node.values if v)

        # Lambda that might return tainted value
        elif isinstance(node, ast.Lambda):
            return self._is_tainted(node.body)

        return False

    def _is_code_modification(self, node) -> bool:
        """Check if a node represents code modification."""
        # Direct attribute modification
        if isinstance(node, ast.Attribute):
            if node.attr in self.DANGEROUS_ATTRS:
                return self._is_tainted(node.value)

        # Dictionary-based modification
        elif isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Attribute):
                if node.value.attr in ["__dict__", "__globals__"]:
                    return self._is_tainted(node.value.value)
            # Check for globals()['name'] pattern
            elif isinstance(node.value, ast.Call):
                func_name = self._get_call_name(node.value.func)
                if func_name in ["globals", "locals", "vars"]:
                    return True

        return False

    def _check_attr_manipulation(self, node: ast.Call, func_name: str):
        """Check getattr/setattr/delattr calls for dangerous patterns."""
        if len(node.args) >= 2:
            # Check if manipulating tainted object
            if self._is_tainted(node.args[0]):
                # Check for dangerous attribute name
                attr_name = self._extract_string_value(node.args[1])
                if attr_name in self.DANGEROUS_ATTRS:
                    self.add_violation(node, f"Code modification using {func_name}() with {attr_name}")
                elif attr_name:
                    self.add_warning(node, f"Attribute manipulation on tainted object using {func_name}()")
                else:
                    # Dynamic attribute name
                    self.add_warning(node, f"Dynamic attribute manipulation using {func_name}()")

    def _check_subscript_assignment(self, target: ast.Subscript, value, node):
        """Check subscript assignments for dangerous patterns."""
        # Check for __dict__['__code__'] pattern
        if isinstance(target.value, ast.Attribute):
            if target.value.attr in ["__dict__", "__globals__"]:
                if self._is_tainted(target.value.value):
                    key = self._extract_string_value(target.slice)
                    if key in self.DANGEROUS_ATTRS:
                        self.add_violation(node, f"Code modification through __dict__['{key}']")

    def _check_operator_usage(self, node: ast.Call):
        """Check operator module usage for setattr/getattr."""
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ["setattr", "attrgetter", "methodcaller"]:
                if len(node.args) >= 2 and self._is_tainted(node.args[0]):
                    self.add_warning(node, f"Potential code modification using operator.{node.func.attr}")

    def _is_object_setattr(self, node: ast.Call) -> bool:
        """Check for object.__setattr__ pattern."""
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "__setattr__":
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "object":
                    if len(node.args) >= 2:
                        attr_name = self._extract_string_value(node.args[1])
                        if attr_name in self.DANGEROUS_ATTRS:
                            return True
        return False

    def _is_import_call(self, node: ast.Call) -> bool:
        """Check if a call is an import through importlib or similar."""
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                module_name = node.func.value.id
                func_name = node.func.attr
                return (module_name, func_name) in self.IMPORT_FUNCS
        return False

    def _is_operator_call(self, node: ast.Call) -> bool:
        """Check if using operator module functions."""
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                return node.func.value.id == "operator"
        return False

    def _handle_sequence_unpacking(self, target, value):
        """Handle tuple/list unpacking patterns."""
        if isinstance(value, (ast.Tuple, ast.List)):
            for i, (tgt, val) in enumerate(zip(target.elts, value.elts)):
                if isinstance(tgt, ast.Name) and self._is_tainted(val):
                    self.mark_tainted(tgt.id, TaintType.DERIVED)

    def _mark_call_result_tainted(self, node: ast.Call):
        """Mark the result of a call as tainted (for tracking in parent visitor)."""
        # This would need to be handled by the parent visitor
        pass

    def _get_call_name(self, node) -> Optional[str]:
        """Extract the function name from a call node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _extract_string_value(self, node) -> Optional[str]:
        """Extract string value from a node if it's a constant."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        elif isinstance(node, ast.Str):  # Python < 3.8 compatibility
            return node.s
        return None

    def check(self) -> Tuple[List[Tuple[int, str, str]], List[Tuple[int, str, str]]]:
        """Run the checker and return violations and warnings."""
        try:
            tree = ast.parse("\n".join(self.source_lines))
            self.visit(tree)
        except SyntaxError as e:
            # Add syntax error as a violation
            line_no = e.lineno if e.lineno else 1
            code_line = self._get_line(line_no)
            reason = f"Syntax error: {e.msg}"
            self.violations.append((line_no, code_line, reason))
        return self.violations, self.warnings

    def report(self) -> str:
        """Generate a detailed report."""
        report = []

        if self.violations:
            report.append("=" * 60)
            report.append("CODE MODIFICATION VIOLATIONS FOUND")
            report.append("=" * 60)
            for line_no, code, reason in self.violations:
                report.append(f"Line {line_no}: {reason}")
                report.append(f"  Code: {code}")
                report.append("")

        if self.warnings:
            report.append("=" * 60)
            report.append("WARNINGS - POTENTIALLY DANGEROUS PATTERNS")
            report.append("=" * 60)
            for line_no, code, warning in self.warnings:
                report.append(f"Line {line_no}: {warning}")
                report.append(f"  Code: {code}")
                report.append("")

        if self.dynamic_execution_sites:
            report.append("=" * 60)
            report.append("DYNAMIC CODE EXECUTION DETECTED")
            report.append("=" * 60)
            report.append(f"Found {len(self.dynamic_execution_sites)} instances of dynamic execution")
            report.append(f"Lines: {', '.join(map(str, self.dynamic_execution_sites))}")
            report.append("")

        if self.tainted_vars:
            report.append("=" * 60)
            report.append("TAINTED VARIABLES TRACKED")
            report.append("=" * 60)
            for name, info in self.tainted_vars.items():
                taint_types = ", ".join(t.value for t in info.types)
                report.append(f"  {name}: {taint_types}")
            report.append("")

        if not self.violations and not self.warnings:
            report.append("No code modification attempts detected.")

        return "\n".join(report)


def check_code_safety(source_code: str) -> None:
    """Check code for modification attempts."""
    checker = CodeModificationChecker(source_code)
    violations, warnings = checker.check()
    return violations, warnings
