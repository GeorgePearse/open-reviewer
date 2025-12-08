"""Shared data models for semantic code analysis."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class FunctionSignature:
    """Represents a function or method signature extracted from code."""

    name: str
    parameters: list[str]
    return_type: str | None
    decorators: list[str]
    line_number: int
    is_method: bool = False
    class_name: str | None = None
    docstring: str | None = None

    def format(self) -> str:
        """Format signature as a single line for display."""
        params = ", ".join(self.parameters)
        ret = f" -> {self.return_type}" if self.return_type else ""
        prefix = f"{self.class_name}." if self.class_name else ""
        decorators = "".join(f"@{d}\n" for d in self.decorators) if self.decorators else ""
        return f"{decorators}{prefix}{self.name}({params}){ret}"


@dataclass
class ClassInfo:
    """Represents a class definition extracted from code."""

    name: str
    bases: list[str]
    methods: list[FunctionSignature]
    line_number: int
    docstring: str | None = None

    def format(self) -> str:
        """Format class as a summary for display."""
        bases_str = f"({', '.join(self.bases)})" if self.bases else ""
        return f"class {self.name}{bases_str}"


@dataclass
class ImportInfo:
    """Represents an import statement."""

    module: str
    names: list[str]  # Empty for "import x", ["*"] for "from x import *"
    alias: str | None = None
    line_number: int = 0

    def format(self) -> str:
        """Format import for display."""
        if not self.names:
            alias_str = f" as {self.alias}" if self.alias else ""
            return f"import {self.module}{alias_str}"
        names_str = ", ".join(self.names)
        return f"from {self.module} import {names_str}"


@dataclass
class ASTContext:
    """Complete AST context extracted from a code file."""

    language: str
    file_path: str
    functions: list[FunctionSignature] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    imports: list[ImportInfo] = field(default_factory=list)
    call_sites: dict[str, int] = field(default_factory=dict)  # callee -> count
    global_variables: list[str] = field(default_factory=list)
    token_estimate: int = 0

    def format_for_prompt(self, max_tokens: int = 3000) -> str:
        """Format AST context as markdown for LLM prompt."""
        sections: list[str] = []

        # Imports section
        if self.imports:
            import_lines = [imp.format() for imp in self.imports[:20]]  # Limit imports
            sections.append("### Imports\n```python\n" + "\n".join(import_lines) + "\n```")

        # Classes section
        if self.classes:
            class_lines: list[str] = []
            for cls in self.classes:
                class_lines.append(f"**{cls.format()}** (line {cls.line_number})")
                for method in cls.methods[:10]:  # Limit methods per class
                    class_lines.append(f"  - `{method.name}({', '.join(method.parameters[:5])})`")
            sections.append("### Classes\n" + "\n".join(class_lines))

        # Functions section (top-level only)
        top_level_funcs = [f for f in self.functions if not f.is_method]
        if top_level_funcs:
            func_lines = [f"- `{f.format()}`" for f in top_level_funcs[:15]]
            sections.append("### Functions\n" + "\n".join(func_lines))

        # Call sites (most frequent)
        if self.call_sites:
            sorted_calls = sorted(self.call_sites.items(), key=lambda x: x[1], reverse=True)[:10]
            call_lines = [f"- `{name}` ({count}x)" for name, count in sorted_calls]
            sections.append("### Frequent Calls\n" + "\n".join(call_lines))

        result = "\n\n".join(sections)

        # Simple token estimation (4 chars ~ 1 token)
        self.token_estimate = len(result) // 4
        if self.token_estimate > max_tokens:
            # Truncate by reducing sections
            result = result[: max_tokens * 4]
            self.token_estimate = max_tokens

        return result


@dataclass
class Symbol:
    """A code symbol (class, function, method, type alias) for repository mapping."""

    name: str
    kind: Literal["class", "function", "method", "type_alias", "constant"]
    signature: str
    file_path: Path
    line_number: int
    references: int = 0  # Number of times this symbol is referenced

    def format(self) -> str:
        """Format symbol for display."""
        return f"{self.kind}: {self.signature}"


@dataclass
class RepoMap:
    """Repository map showing key symbols and their relationships."""

    focus_file: Path
    key_symbols: list[Symbol] = field(default_factory=list)
    import_tree: dict[str, list[str]] = field(default_factory=dict)  # file -> imported modules
    token_estimate: int = 0

    def render(self, max_tokens: int = 2000) -> str:
        """Render repository map as markdown."""
        sections: list[str] = []

        # Group symbols by file
        symbols_by_file: dict[str, list[Symbol]] = {}
        for sym in self.key_symbols:
            file_key = str(sym.file_path)
            if file_key not in symbols_by_file:
                symbols_by_file[file_key] = []
            symbols_by_file[file_key].append(sym)

        # Focus file first
        focus_key = str(self.focus_file)
        if focus_key in symbols_by_file:
            sections.append(f"### {self.focus_file.name} (focus)")
            for sym in symbols_by_file[focus_key]:
                sections.append(f"- {sym.format()}")
            del symbols_by_file[focus_key]

        # Related files
        for file_path, symbols in sorted(symbols_by_file.items()):
            # Shorten path for display
            short_path = Path(file_path).name
            sections.append(f"\n### {short_path}")
            for sym in symbols[:5]:  # Limit symbols per file
                sections.append(f"- {sym.format()}")

        result = "\n".join(sections)

        # Token estimation
        self.token_estimate = len(result) // 4
        if self.token_estimate > max_tokens:
            result = result[: max_tokens * 4]
            self.token_estimate = max_tokens

        return result


@dataclass
class CodeChunk:
    """A chunk of code for embedding."""

    id: str
    file_path: str
    chunk_type: Literal["function", "class", "method", "file"]
    name: str
    code: str
    language: str
    start_line: int
    end_line: int
    token_count: int = 0

    def __post_init__(self) -> None:
        """Estimate token count if not provided."""
        if self.token_count == 0:
            self.token_count = len(self.code) // 4


@dataclass
class SearchResult:
    """Result from semantic similarity search."""

    chunk: CodeChunk
    similarity: float
    rank: int

    def format(self, include_code: bool = True) -> str:
        """Format search result for display."""
        header = f"### {self.chunk.name} ({self.chunk.file_path}:{self.chunk.start_line})"
        header += f"\nSimilarity: {self.similarity:.2f}"
        if include_code:
            header += f"\n```{self.chunk.language}\n{self.chunk.code}\n```"
        return header


@dataclass
class SemanticSearchResults:
    """Collection of semantic search results."""

    query: str
    results: list[SearchResult] = field(default_factory=list)
    token_estimate: int = 0

    def format(self, max_tokens: int = 8000) -> str:
        """Format all results as markdown."""
        if not self.results:
            return "_No similar code found._"

        sections = [f"Query: `{self.query[:100]}`\n"]
        current_tokens = 0

        for result in self.results:
            formatted = result.format(include_code=True)
            result_tokens = len(formatted) // 4

            if current_tokens + result_tokens > max_tokens:
                # Include without code if over budget
                formatted = result.format(include_code=False)
                result_tokens = len(formatted) // 4

            if current_tokens + result_tokens <= max_tokens:
                sections.append(formatted)
                current_tokens += result_tokens

        self.token_estimate = current_tokens
        return "\n\n".join(sections)
