"""AST parsing for extracting semantic code structure.

Uses Python's built-in ast module for Python code analysis.
Tree-sitter can be added as an optional enhancement for multi-language support.
"""

import ast
from pathlib import Path

from review_eval.semantic.models import (
    ASTContext,
    ClassInfo,
    FunctionSignature,
    ImportInfo,
)


class ASTParser:
    """Parser for extracting semantic structure from source code."""

    def parse(self, code: str, language: str = "python", file_path: str = "") -> ASTContext:
        """Parse code and extract semantic structure.

        Args:
            code: Source code to parse.
            language: Programming language (currently only "python" supported).
            file_path: Path to the source file (for context).

        Returns:
            ASTContext with extracted functions, classes, imports, and call sites.
        """
        if language != "python":
            return ASTContext(language=language, file_path=file_path)

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return ASTContext(language=language, file_path=file_path)

        context = ASTContext(language=language, file_path=file_path)

        # Extract all elements in a single pass
        visitor = _ASTVisitor()
        visitor.visit(tree)

        context.functions = visitor.functions
        context.classes = visitor.classes
        context.imports = visitor.imports
        context.call_sites = visitor.call_sites
        context.global_variables = visitor.global_variables

        return context

    def parse_file(self, file_path: Path) -> ASTContext:
        """Parse a Python file and extract semantic structure.

        Args:
            file_path: Path to the Python file.

        Returns:
            ASTContext with extracted structure.
        """
        try:
            code = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ASTContext(language="python", file_path=str(file_path))

        return self.parse(code, language="python", file_path=str(file_path))


class _ASTVisitor(ast.NodeVisitor):
    """AST visitor that extracts functions, classes, imports, and call sites."""

    def __init__(self) -> None:
        self.functions: list[FunctionSignature] = []
        self.classes: list[ClassInfo] = []
        self.imports: list[ImportInfo] = []
        self.call_sites: dict[str, int] = {}
        self.global_variables: list[str] = []
        self._current_class: str | None = None

    def visit_Import(self, node: ast.Import) -> None:
        """Handle 'import x' statements."""
        for alias in node.names:
            self.imports.append(
                ImportInfo(
                    module=alias.name,
                    names=[],
                    alias=alias.asname,
                    line_number=node.lineno,
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle 'from x import y' statements."""
        module = node.module or ""
        names = [alias.name for alias in node.names]
        self.imports.append(
            ImportInfo(
                module=module,
                names=names,
                line_number=node.lineno,
            )
        )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Handle class definitions."""
        bases = [_get_name(base) for base in node.bases]
        docstring = ast.get_docstring(node)

        # Extract methods
        methods: list[FunctionSignature] = []
        old_class = self._current_class
        self._current_class = node.name

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                sig = self._extract_function(item, is_method=True, class_name=node.name)
                methods.append(sig)

        self._current_class = old_class

        self.classes.append(
            ClassInfo(
                name=node.name,
                bases=bases,
                methods=methods,
                line_number=node.lineno,
                docstring=docstring,
            )
        )

        # Add methods to functions list as well
        self.functions.extend(methods)

        # Continue visiting for call sites
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Handle function definitions."""
        if self._current_class is None:
            sig = self._extract_function(node, is_method=False)
            self.functions.append(sig)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Handle async function definitions."""
        if self._current_class is None:
            sig = self._extract_function(node, is_method=False)
            sig.decorators.insert(0, "async")
            self.functions.append(sig)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Track function/method calls."""
        name = _get_call_name(node)
        if name:
            self.call_sites[name] = self.call_sites.get(name, 0) + 1
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Track module-level variable assignments."""
        if self._current_class is None:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    # Check if it looks like a constant (UPPER_CASE)
                    if target.id.isupper() or target.id[0].isupper():
                        self.global_variables.append(target.id)
        self.generic_visit(node)

    def _extract_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        is_method: bool = False,
        class_name: str | None = None,
    ) -> FunctionSignature:
        """Extract function signature from a function definition node."""
        # Get parameters
        params: list[str] = []
        for arg in node.args.args:
            param = arg.arg
            if arg.annotation:
                param += f": {_get_annotation(arg.annotation)}"
            params.append(param)

        # Handle *args and **kwargs
        if node.args.vararg:
            params.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            params.append(f"**{node.args.kwarg.arg}")

        # Get return type
        return_type = None
        if node.returns:
            return_type = _get_annotation(node.returns)

        # Get decorators
        decorators = [_get_name(d) for d in node.decorator_list]

        # Get docstring
        docstring = ast.get_docstring(node)

        return FunctionSignature(
            name=node.name,
            parameters=params,
            return_type=return_type,
            decorators=decorators,
            line_number=node.lineno,
            is_method=is_method,
            class_name=class_name,
            docstring=docstring,
        )


def _get_name(node: ast.expr) -> str:
    """Get the name from an AST node (handles Name, Attribute, Call)."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{_get_name(node.value)}.{node.attr}"
    elif isinstance(node, ast.Call):
        return _get_name(node.func)
    elif isinstance(node, ast.Subscript):
        return f"{_get_name(node.value)}[...]"
    elif isinstance(node, ast.Constant):
        return repr(node.value)
    else:
        return "<complex>"


def _get_annotation(node: ast.expr) -> str:
    """Get type annotation as a string."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return _get_name(node)
    elif isinstance(node, ast.Subscript):
        base = _get_name(node.value)
        if isinstance(node.slice, ast.Tuple):
            args = ", ".join(_get_annotation(elt) for elt in node.slice.elts)
        else:
            args = _get_annotation(node.slice)
        return f"{base}[{args}]"
    elif isinstance(node, ast.Constant):
        if node.value is None:
            return "None"
        return repr(node.value)
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        # Union type: X | Y
        left = _get_annotation(node.left)
        right = _get_annotation(node.right)
        return f"{left} | {right}"
    elif isinstance(node, ast.Tuple):
        return ", ".join(_get_annotation(elt) for elt in node.elts)
    else:
        return "<complex>"


def _get_call_name(node: ast.Call) -> str | None:
    """Get the name of a function/method being called."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    elif isinstance(node.func, ast.Attribute):
        # For method calls like obj.method(), just return method name
        return node.func.attr
    return None
