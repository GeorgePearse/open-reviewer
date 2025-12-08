"""Code chunking for embedding generation.

Extracts functions, classes, and methods as discrete chunks suitable
for embedding and semantic search. Supports Python, TypeScript, Rust, Go, and Java.
"""

import ast
import hashlib
from pathlib import Path

# Import tree-sitter related modules
try:
    from tree_sitter import Parser, Language, Query, QueryCursor
    import tree_sitter_typescript
    import tree_sitter_rust
    import tree_sitter_go
    import tree_sitter_java

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

from review_eval.semantic.models import CodeChunk

# Map extensions to languages
EXT_TO_LANG = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
}

# Queries for Tree-sitter
QUERIES = {
    "typescript": """
        (function_declaration) @function
        (method_definition) @method
        (class_declaration) @class
        (interface_declaration) @class
        (lexical_declaration (variable_declarator (arrow_function) @arrow))
    """,
    "tsx": """
        (function_declaration) @function
        (method_definition) @method
        (class_declaration) @class
        (interface_declaration) @class
        (lexical_declaration (variable_declarator (arrow_function) @arrow))
    """,
    "rust": """
        (function_item) @function
        (impl_item) @class
        (trait_item) @class
        (struct_item) @class
        (enum_item) @class
    """,
    "go": """
        (function_declaration) @function
        (method_declaration) @method
        (type_declaration) @class
    """,
    "java": """
        (class_declaration) @class
        (interface_declaration) @class
        (enum_declaration) @class
        (record_declaration) @class
        (method_declaration) @method
        (constructor_declaration) @method
    """,
}

# Initialize languages and queries
TS_LANGUAGES = {}
TS_QUERIES = {}

if TREE_SITTER_AVAILABLE:
    try:
        # For tree-sitter >= 0.22, we must wrap the language capsule in Language()
        TS_LANGUAGES = {
            "typescript": Language(tree_sitter_typescript.language_typescript()),
            "tsx": Language(tree_sitter_typescript.language_tsx()),
            "rust": Language(tree_sitter_rust.language()),
            "go": Language(tree_sitter_go.language()),
            "java": Language(tree_sitter_java.language()),
        }

        # Compile queries
        for lang_name, query_str in QUERIES.items():
            if lang_name in TS_LANGUAGES:
                TS_QUERIES[lang_name] = Query(TS_LANGUAGES[lang_name], query_str)

    except Exception as e:
        print(f"Warning: Failed to load tree-sitter languages: {e}")
        TREE_SITTER_AVAILABLE = False


def chunk_file(file_path: Path, repo_root: Path | None = None) -> list[CodeChunk]:
    """Extract semantic chunks from a file.

    Args:
        file_path: Path to the file.
        repo_root: Optional repository root for relative path calculation.

    Returns:
        List of CodeChunk objects.
    """
    try:
        code = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    rel_path = str(file_path.relative_to(repo_root)) if repo_root else str(file_path)
    language = EXT_TO_LANG.get(file_path.suffix, "unknown")

    # Handle unknown extensions or fallback
    if language == "unknown":
        return []

    return chunk_code(code, rel_path, language)


# Backward compatibility alias
chunk_python_file = chunk_file


def chunk_code(code: str, file_path: str, language: str = "python") -> list[CodeChunk]:
    """Extract semantic chunks from source code.

    Args:
        code: Source code to chunk.
        file_path: Path to the source file (for identification).
        language: Programming language.

    Returns:
        List of CodeChunk objects.
    """
    if language == "python":
        return _chunk_python(code, file_path)

    if TREE_SITTER_AVAILABLE and language in TS_LANGUAGES:
        return _chunk_with_tree_sitter(code, file_path, language)

    # Fallback for non-supported languages or if tree-sitter is missing
    return [
        CodeChunk(
            id=_make_chunk_id(file_path, "file", "file"),
            file_path=file_path,
            chunk_type="file",
            name=Path(file_path).name,
            code=code[:8000],  # Limit file chunks
            language=language,
            start_line=1,
            end_line=code.count("\n") + 1,
        )
    ]


def _chunk_python(code: str, file_path: str) -> list[CodeChunk]:
    """Extract Python chunks using AST."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    lines = code.split("\n")
    chunks: list[CodeChunk] = []
    extractor = _PythonChunkExtractor(lines, file_path)
    extractor.visit(tree)
    chunks.extend(extractor.chunks)

    return chunks


def _chunk_with_tree_sitter(code: str, file_path: str, language: str) -> list[CodeChunk]:
    """Extract chunks using Tree-sitter."""
    lang_obj = TS_LANGUAGES[language]
    parser = Parser(lang_obj)
    tree = parser.parse(bytes(code, "utf8"))

    # Use cached query
    query = TS_QUERIES.get(language)
    if not query:
        return []

    cursor = QueryCursor(query)
    matches = cursor.matches(tree.root_node)

    chunks = []

    # Iterate over matches
    for _, captures_dict in matches:
        for capture_name, nodes in captures_dict.items():
            for node in nodes:
                # Determine chunk type from capture name
                chunk_type = "function"
                if capture_name == "class":
                    chunk_type = "class"
                elif capture_name == "method":
                    chunk_type = "method"
                elif capture_name == "arrow":
                    chunk_type = "function"
                elif capture_name == "interface":
                    chunk_type = "class"

                start_line = node.start_point.row + 1
                end_line = node.end_point.row + 1

                # Heuristic to get name
                name = _get_node_name(node) or f"anonymous_{start_line}"

                # Get code text
                chunk_code_str = node.text.decode("utf8")

                # Create chunk
                chunks.append(
                    CodeChunk(
                        id=_make_chunk_id(file_path, chunk_type, name),
                        file_path=file_path,
                        chunk_type=chunk_type,  # type: ignore
                        name=name,
                        code=chunk_code_str,
                        language=language,
                        start_line=start_line,
                        end_line=end_line,
                    )
                )

    return chunks


def _get_node_name(node) -> str | None:
    """Extract name from a tree-sitter node."""
    # Standard 'name' field
    child = node.child_by_field_name("name")
    if child:
        return child.text.decode("utf8")

    # Go type specs
    if node.type == "type_declaration":
        for child in node.children:
            if child.type == "type_spec":
                name_node = child.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode("utf8")

    # Variable declarations (arrow functions)
    if node.type == "variable_declarator":
        name_node = node.child_by_field_name("name")
        if name_node:
            return name_node.text.decode("utf8")

    # Arrow function - look up to parent variable declarator
    if node.type == "arrow_function":
        parent = node.parent
        if parent and parent.type == "variable_declarator":
            name_node = parent.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf8")

    # Rust impl blocks - try to find the type name
    if node.type == "impl_item":
        # impl Foo { ... }
        # impl Bar for Foo { ... }
        for i, child in enumerate(node.children):
            if child.type == "type_identifier":
                return child.text.decode("utf8")

    # Java classes/methods often have 'name' field, handled by standard case

    return None


class _PythonChunkExtractor(ast.NodeVisitor):
    """AST visitor that extracts code chunks."""

    def __init__(self, lines: list[str], file_path: str) -> None:
        self.lines = lines
        self.file_path = file_path
        self.chunks: list[CodeChunk] = []
        self._current_class: str | None = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Extract class as a chunk."""
        start_line = node.lineno
        end_line = node.end_lineno or start_line

        # Include decorators
        if node.decorator_list:
            start_line = node.decorator_list[0].lineno

        code = "\n".join(self.lines[start_line - 1 : end_line])

        self.chunks.append(
            CodeChunk(
                id=_make_chunk_id(self.file_path, "class", node.name),
                file_path=self.file_path,
                chunk_type="class",
                name=node.name,
                code=code,
                language="python",
                start_line=start_line,
                end_line=end_line,
            )
        )

        # Also extract methods individually
        old_class = self._current_class
        self._current_class = node.name

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._extract_method(item)

        self._current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Extract top-level function as a chunk."""
        if self._current_class is None:
            self._extract_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Extract async function as a chunk."""
        if self._current_class is None:
            self._extract_function(node)

    def _extract_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Extract a function definition as a chunk."""
        start_line = node.lineno
        end_line = node.end_lineno or start_line

        # Include decorators
        if node.decorator_list:
            start_line = node.decorator_list[0].lineno

        code = "\n".join(self.lines[start_line - 1 : end_line])

        self.chunks.append(
            CodeChunk(
                id=_make_chunk_id(self.file_path, "function", node.name),
                file_path=self.file_path,
                chunk_type="function",
                name=node.name,
                code=code,
                language="python",
                start_line=start_line,
                end_line=end_line,
            )
        )

    def _extract_method(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Extract a method definition as a chunk."""
        start_line = node.lineno
        end_line = node.end_lineno or start_line

        # Include decorators
        if node.decorator_list:
            start_line = node.decorator_list[0].lineno

        code = "\n".join(self.lines[start_line - 1 : end_line])
        name = f"{self._current_class}.{node.name}" if self._current_class else node.name

        self.chunks.append(
            CodeChunk(
                id=_make_chunk_id(self.file_path, "method", name),
                file_path=self.file_path,
                chunk_type="method",
                name=name,
                code=code,
                language="python",
                start_line=start_line,
                end_line=end_line,
            )
        )


def _make_chunk_id(file_path: str, chunk_type: str, name: str) -> str:
    """Generate a unique ID for a code chunk."""
    content = f"{file_path}:{chunk_type}:{name}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def chunk_repository(
    repo_root: Path,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    max_chunks: int = 5000,
) -> list[CodeChunk]:
    """Chunk all supported files in a repository.

    Args:
        repo_root: Root directory of the repository.
        include_patterns: Glob patterns for files to include.
        exclude_patterns: Glob patterns for files to exclude.
        max_chunks: Maximum number of chunks to extract.

    Returns:
        List of CodeChunk objects from all files.
    """
    if include_patterns is None:
        include_patterns = ["**/*.py", "**/*.ts", "**/*.tsx", "**/*.rs", "**/*.go", "**/*.java"]

    if exclude_patterns is None:
        exclude_patterns = [
            "**/test_*.py",
            "**/*_test.py",
            "**/tests/**",
            "**/__pycache__/**",
            "**/venv/**",
            "**/.venv/**",
            "**/node_modules/**",
            "**/*.test.ts",
            "**/*.spec.ts",
            "**/dist/**",
            "**/target/**",
            "**/vendor/**",
        ]

    all_chunks: list[CodeChunk] = []
    processed_files: set[Path] = set()

    for pattern in include_patterns:
        for file_path in repo_root.glob(pattern):
            if file_path in processed_files:
                continue

            # Skip if extension not supported (unless explicitly asked)
            # But chunk_file will return empty anyway if not supported

            # Check exclusions
            should_exclude = False
            for exc_pattern in exclude_patterns:
                if file_path.match(exc_pattern):
                    should_exclude = True
                    break

            if should_exclude:
                continue

            processed_files.add(file_path)
            chunks = chunk_file(file_path, repo_root)
            all_chunks.extend(chunks)

            if len(all_chunks) >= max_chunks:
                break

        if len(all_chunks) >= max_chunks:
            break

    return all_chunks[:max_chunks]
