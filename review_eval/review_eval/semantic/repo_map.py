"""Repository map generation for codebase context.

Inspired by Aider's repo map approach - creates a concise overview of the
codebase structure focused on a specific file, showing key symbols and
their relationships.
"""

from pathlib import Path
from typing import Literal

from review_eval.semantic.ast_parser import ASTParser
from review_eval.semantic.models import (
    ClassInfo,
    FunctionSignature,
    RepoMap,
    Symbol,
)


class RepoMapGenerator:
    """Generates repository maps focused on specific files."""

    def __init__(self, repo_root: Path) -> None:
        """Initialize the generator.

        Args:
            repo_root: Root directory of the repository.
        """
        self.repo_root = repo_root
        self._parser = ASTParser()
        self._symbol_cache: dict[Path, list[Symbol]] = {}
        self._import_cache: dict[Path, list[str]] = {}

    def generate(
        self,
        focus_file: Path,
        max_tokens: int = 2000,
        max_depth: int = 2,
    ) -> RepoMap:
        """Generate a repository map focused on a specific file.

        Args:
            focus_file: The file to focus the map on.
            max_tokens: Maximum token budget for the map.
            max_depth: Maximum depth to traverse imports.

        Returns:
            RepoMap with key symbols and import relationships.
        """
        focus_path = Path(focus_file)
        if not focus_path.is_absolute():
            focus_path = self.repo_root / focus_path

        # Extract symbols from focus file
        focus_symbols = self._get_symbols(focus_path)

        # Build import graph
        import_tree = self._build_import_tree(focus_path, max_depth)

        # Collect symbols from related files
        all_symbols: list[Symbol] = list(focus_symbols)
        related_files = self._find_related_files(focus_path, import_tree)

        for related_file in related_files:
            related_symbols = self._get_symbols(related_file)
            all_symbols.extend(related_symbols)

        # Rank symbols by reference count
        ranked_symbols = self._rank_symbols(all_symbols, focus_path)

        # Select top symbols within budget
        selected = self._select_within_budget(ranked_symbols, max_tokens)

        return RepoMap(
            focus_file=focus_path,
            key_symbols=selected,
            import_tree={str(k): v for k, v in import_tree.items()},
        )

    def _get_symbols(self, file_path: Path) -> list[Symbol]:
        """Extract symbols from a file, using cache if available."""
        if file_path in self._symbol_cache:
            return self._symbol_cache[file_path]

        if not file_path.exists() or not file_path.suffix == ".py":
            return []

        context = self._parser.parse_file(file_path)
        symbols: list[Symbol] = []

        # Add class symbols
        for cls in context.classes:
            symbols.append(
                Symbol(
                    name=cls.name,
                    kind="class",
                    signature=cls.format(),
                    file_path=file_path,
                    line_number=cls.line_number,
                )
            )
            # Add method symbols
            for method in cls.methods:
                symbols.append(
                    Symbol(
                        name=f"{cls.name}.{method.name}",
                        kind="method",
                        signature=self._format_method_signature(cls, method),
                        file_path=file_path,
                        line_number=method.line_number,
                    )
                )

        # Add function symbols (top-level only)
        for func in context.functions:
            if not func.is_method:
                symbols.append(
                    Symbol(
                        name=func.name,
                        kind="function",
                        signature=func.format(),
                        file_path=file_path,
                        line_number=func.line_number,
                    )
                )

        # Add constants/type aliases
        for var in context.global_variables:
            kind: Literal["class", "function", "method", "type_alias", "constant"]
            if var.endswith("Type") or var.endswith("Alias"):
                kind = "type_alias"
            else:
                kind = "constant"
            symbols.append(
                Symbol(
                    name=var,
                    kind=kind,
                    signature=var,
                    file_path=file_path,
                    line_number=0,
                )
            )

        self._symbol_cache[file_path] = symbols
        return symbols

    def _build_import_tree(
        self,
        focus_file: Path,
        max_depth: int,
    ) -> dict[Path, list[str]]:
        """Build a tree of imports starting from the focus file."""
        import_tree: dict[Path, list[str]] = {}
        visited: set[Path] = set()
        queue: list[tuple[Path, int]] = [(focus_file, 0)]

        while queue:
            current_file, depth = queue.pop(0)
            if current_file in visited or depth > max_depth:
                continue
            visited.add(current_file)

            if not current_file.exists() or not current_file.suffix == ".py":
                continue

            context = self._parser.parse_file(current_file)
            imports: list[str] = []

            for imp in context.imports:
                imports.append(imp.module)
                # Try to resolve to a file
                resolved = self._resolve_import(imp.module, current_file)
                if resolved and resolved not in visited:
                    queue.append((resolved, depth + 1))

            import_tree[current_file] = imports

        return import_tree

    def _resolve_import(self, module: str, from_file: Path) -> Path | None:
        """Try to resolve a module import to a file path."""
        # Convert module.name to module/name.py
        parts = module.split(".")
        possible_paths = [
            # Relative to repo root
            self.repo_root / Path(*parts).with_suffix(".py"),
            self.repo_root / Path(*parts) / "__init__.py",
            # Relative to current file's directory
            from_file.parent / Path(*parts).with_suffix(".py"),
            from_file.parent / Path(*parts) / "__init__.py",
        ]

        for path in possible_paths:
            if path.exists():
                return path

        return None

    def _find_related_files(
        self,
        focus_file: Path,
        import_tree: dict[Path, list[str]],
    ) -> list[Path]:
        """Find files related to the focus file through imports."""
        related: set[Path] = set()

        # Files that focus_file imports
        for file_path in import_tree:
            if file_path != focus_file:
                related.add(file_path)

        # Files in the same directory (siblings)
        if focus_file.parent.exists():
            for sibling in focus_file.parent.glob("*.py"):
                if sibling != focus_file and sibling.name != "__init__.py":
                    related.add(sibling)

        return list(related)[:10]  # Limit to 10 related files

    def _rank_symbols(
        self,
        symbols: list[Symbol],
        focus_file: Path,
    ) -> list[Symbol]:
        """Rank symbols by relevance to the focus file."""
        # Simple ranking based on:
        # 1. Symbols from focus file get highest priority
        # 2. Classes rank higher than functions
        # 3. Public symbols (no underscore prefix) rank higher

        def rank_key(sym: Symbol) -> tuple[int, int, int, str]:
            is_focus = 0 if sym.file_path == focus_file else 1
            kind_rank = {"class": 0, "type_alias": 1, "function": 2, "method": 3, "constant": 4}
            is_private = 1 if sym.name.startswith("_") else 0
            return (is_focus, kind_rank.get(sym.kind, 5), is_private, sym.name)

        return sorted(symbols, key=rank_key)

    def _select_within_budget(
        self,
        symbols: list[Symbol],
        max_tokens: int,
    ) -> list[Symbol]:
        """Select symbols that fit within the token budget."""
        selected: list[Symbol] = []
        current_tokens = 0

        for sym in symbols:
            # Estimate tokens for this symbol
            sym_tokens = len(sym.format()) // 4 + 2  # +2 for formatting overhead

            if current_tokens + sym_tokens <= max_tokens:
                selected.append(sym)
                current_tokens += sym_tokens

            if current_tokens >= max_tokens:
                break

        return selected

    def _format_method_signature(
        self,
        cls: ClassInfo,
        method: FunctionSignature,
    ) -> str:
        """Format a method signature with class context."""
        return f"{cls.name}.{method.format()}"


def generate_repo_map_for_diff(
    repo_root: Path,
    changed_files: list[str],
    max_tokens: int = 2000,
) -> str:
    """Generate a combined repo map for multiple changed files.

    Args:
        repo_root: Root directory of the repository.
        changed_files: List of file paths that were changed.
        max_tokens: Maximum token budget for the entire map.

    Returns:
        Formatted repository map as a string.
    """
    generator = RepoMapGenerator(repo_root)
    tokens_per_file = max_tokens // max(len(changed_files), 1)

    sections: list[str] = []
    total_tokens = 0

    for file_path in changed_files:
        if not file_path.endswith(".py"):
            continue

        remaining_tokens = max_tokens - total_tokens
        if remaining_tokens < 100:
            break

        repo_map = generator.generate(
            Path(file_path),
            max_tokens=min(tokens_per_file, remaining_tokens),
        )

        rendered = repo_map.render()
        total_tokens += repo_map.token_estimate
        sections.append(rendered)

    return "\n\n---\n\n".join(sections) if sections else "_No Python files in changeset._"
