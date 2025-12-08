"""Tests for semantic code analysis module."""

import tempfile
from pathlib import Path

import pytest
from review_eval.semantic import (
    ASTParser,
    CodeChunk,
    RepoMapGenerator,
    SemanticSearch,
)
from review_eval.semantic.embeddings.chunker import chunk_code
from review_eval.semantic.embeddings.client import MockEmbeddingClient
from review_eval.semantic.embeddings.vector_store import VectorStore


class TestASTParser:
    """Tests for AST parsing."""

    def test_parse_function(self) -> None:
        """Test parsing a simple function."""
        code = '''
def greet(name: str) -> str:
    """Return a greeting."""
    return f"Hello, {name}!"
'''
        parser = ASTParser()
        context = parser.parse(code)

        assert len(context.functions) == 1
        func = context.functions[0]
        assert func.name == "greet"
        assert func.parameters == ["name: str"]
        assert func.return_type == "str"
        assert func.docstring == "Return a greeting."

    def test_parse_class(self) -> None:
        """Test parsing a class with methods."""
        code = '''
class Calculator:
    """A simple calculator."""

    def add(self, a: int, b: int) -> int:
        return a + b

    def subtract(self, a: int, b: int) -> int:
        return a - b
'''
        parser = ASTParser()
        context = parser.parse(code)

        assert len(context.classes) == 1
        cls = context.classes[0]
        assert cls.name == "Calculator"
        assert cls.docstring == "A simple calculator."
        assert len(cls.methods) == 2
        assert cls.methods[0].name == "add"
        assert cls.methods[1].name == "subtract"

    def test_parse_imports(self) -> None:
        """Test parsing import statements."""
        code = """
import os
from pathlib import Path
from typing import Optional, List
"""
        parser = ASTParser()
        context = parser.parse(code)

        assert len(context.imports) == 3
        assert context.imports[0].module == "os"
        assert context.imports[1].module == "pathlib"
        assert context.imports[1].names == ["Path"]
        assert context.imports[2].names == ["Optional", "List"]

    def test_parse_call_sites(self) -> None:
        """Test tracking function calls."""
        code = """
def process():
    print("Hello")
    print("World")
    format_data()
    print("Done")
"""
        parser = ASTParser()
        context = parser.parse(code)

        assert "print" in context.call_sites
        assert context.call_sites["print"] == 3
        assert context.call_sites["format_data"] == 1

    def test_format_for_prompt(self) -> None:
        """Test formatting AST context for LLM prompt."""
        code = """
from typing import List

def process_items(items: List[str]) -> int:
    return len(items)
"""
        parser = ASTParser()
        context = parser.parse(code)
        formatted = context.format_for_prompt(max_tokens=1000)

        assert "### Imports" in formatted
        assert "### Functions" in formatted
        assert "process_items" in formatted

    def test_parse_syntax_error(self) -> None:
        """Test handling of syntax errors."""
        code = "def invalid(:"
        parser = ASTParser()
        context = parser.parse(code)

        assert context.language == "python"
        assert len(context.functions) == 0


class TestCodeChunker:
    """Tests for code chunking."""

    def test_chunk_function(self) -> None:
        """Test chunking a function."""
        code = '''
def greet(name: str) -> str:
    """Return a greeting."""
    return f"Hello, {name}!"

def farewell(name: str) -> str:
    return f"Goodbye, {name}!"
'''
        chunks = chunk_code(code, "test.py", "python")

        assert len(chunks) == 2
        assert chunks[0].name == "greet"
        assert chunks[0].chunk_type == "function"
        assert chunks[1].name == "farewell"

    def test_chunk_class(self) -> None:
        """Test chunking a class and its methods."""
        code = """
class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b

    def subtract(self, a: int, b: int) -> int:
        return a - b
"""
        chunks = chunk_code(code, "test.py", "python")

        # Should have class chunk + 2 method chunks
        assert len(chunks) >= 3
        class_chunks = [c for c in chunks if c.chunk_type == "class"]
        method_chunks = [c for c in chunks if c.chunk_type == "method"]
        assert len(class_chunks) == 1
        assert len(method_chunks) == 2

    def test_chunk_with_decorators(self) -> None:
        """Test that decorators are included in chunks."""
        code = """
@property
def value(self) -> int:
    return self._value
"""
        chunks = chunk_code(code, "test.py", "python")

        assert len(chunks) == 1
        assert "@property" in chunks[0].code


class TestVectorStore:
    """Tests for Qdrant vector storage.

    Requires QDRANT_URL and QDRANT_API_KEY environment variables to be set.
    Uses a dedicated test collection with cleanup between tests.
    """

    TEST_COLLECTION = "test_code_chunks"

    def setup_method(self) -> None:
        """Set up test collection before each test."""
        self.store = VectorStore(dimension=4, collection_name=self.TEST_COLLECTION)
        self.store.clear()

    def teardown_method(self) -> None:
        """Clean up test collection after each test."""
        self.store.clear()

    def test_add_and_search(self) -> None:
        """Test adding chunks and searching."""
        chunks = [
            CodeChunk(
                id="test_add_1",
                file_path="a.py",
                chunk_type="function",
                name="add",
                code="def add(a, b): return a + b",
                language="python",
                start_line=1,
                end_line=1,
            ),
            CodeChunk(
                id="test_add_2",
                file_path="b.py",
                chunk_type="function",
                name="subtract",
                code="def subtract(a, b): return a - b",
                language="python",
                start_line=1,
                end_line=1,
            ),
        ]

        embeddings = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
        ]

        self.store.add(chunks, embeddings)
        assert self.store.size == 2

        # Search for similar to first chunk
        results = self.store.search([0.9, 0.1, 0.0, 0.0], top_k=2)
        assert len(results) == 2
        assert results[0].chunk.name == "add"  # Most similar to query

    def test_save_and_load(self) -> None:
        """Test persistence (load checks collection exists in Qdrant)."""
        chunks = [
            CodeChunk(
                id="test_save_1",
                file_path="test.py",
                chunk_type="function",
                name="test",
                code="def test(): pass",
                language="python",
                start_line=1,
                end_line=1,
            ),
        ]
        embeddings = [[1.0, 0.0, 0.0, 0.0]]
        self.store.add(chunks, embeddings)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "store"
            self.store.save(path)  # No-op for cloud Qdrant

            # Load checks collection exists
            new_store = VectorStore(dimension=4, collection_name=self.TEST_COLLECTION)
            assert new_store.load(path)
            assert new_store.size == 1

    def test_remove_by_file(self) -> None:
        """Test removing chunks by file path."""
        chunks = [
            CodeChunk(id="test_rm_1", file_path="a.py", chunk_type="function", name="f1", code="", language="python", start_line=1, end_line=1),
            CodeChunk(id="test_rm_2", file_path="a.py", chunk_type="function", name="f2", code="", language="python", start_line=1, end_line=1),
            CodeChunk(id="test_rm_3", file_path="b.py", chunk_type="function", name="f3", code="", language="python", start_line=1, end_line=1),
        ]
        embeddings = [[1.0, 0.0, 0.0, 0.0]] * 3
        self.store.add(chunks, embeddings)

        removed = self.store.remove_by_file("a.py")
        assert removed == 2
        assert self.store.size == 1

    def test_get_chunk_by_id(self) -> None:
        """Test retrieving a chunk by its ID."""
        chunk = CodeChunk(
            id="test_get_1",
            file_path="test.py",
            chunk_type="function",
            name="my_func",
            code="def my_func(): pass",
            language="python",
            start_line=1,
            end_line=1,
        )
        self.store.add([chunk], [[1.0, 0.0, 0.0, 0.0]])

        retrieved = self.store.get_chunk_by_id("test_get_1")
        assert retrieved is not None
        assert retrieved.name == "my_func"

        not_found = self.store.get_chunk_by_id("nonexistent")
        assert not_found is None


class TestMockEmbeddingClient:
    """Tests for mock embedding client."""

    @pytest.mark.asyncio
    async def test_embed_chunks(self) -> None:
        """Test generating mock embeddings."""
        client = MockEmbeddingClient(dimension=128)

        chunks = [
            CodeChunk(
                id="1",
                file_path="test.py",
                chunk_type="function",
                name="test",
                code="def test(): pass",
                language="python",
                start_line=1,
                end_line=1,
            ),
        ]

        results = await client.embed_chunks(chunks)
        assert len(results) == 1
        assert len(results[0].embedding) == 128
        # Check normalization
        norm = sum(x * x for x in results[0].embedding) ** 0.5
        assert abs(norm - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_deterministic_embeddings(self) -> None:
        """Test that mock embeddings are deterministic."""
        client = MockEmbeddingClient(dimension=64)

        text = "def hello(): pass"
        emb1 = await client.embed_text(text)
        emb2 = await client.embed_text(text)

        assert emb1 == emb2


class TestRepoMapGenerator:
    """Tests for repository map generation."""

    def test_generate_from_file(self) -> None:
        """Test generating repo map from a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)

            # Create test file
            test_file = repo_root / "main.py"
            test_file.write_text("""
class App:
    def run(self):
        pass

def main():
    app = App()
    app.run()
""")

            generator = RepoMapGenerator(repo_root)
            repo_map = generator.generate(test_file, max_tokens=1000)

            assert repo_map.focus_file == test_file
            assert len(repo_map.key_symbols) > 0

            rendered = repo_map.render()
            assert "App" in rendered or "main" in rendered


class TestSemanticSearch:
    """Tests for semantic search with mock embeddings."""

    @pytest.mark.asyncio
    async def test_index_and_search(self) -> None:
        """Test indexing and searching with mock embeddings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)

            # Create test files
            (repo_root / "math_ops.py").write_text('''
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b
''')

            (repo_root / "string_ops.py").write_text('''
def concat(a: str, b: str) -> str:
    """Concatenate two strings."""
    return a + b

def reverse(s: str) -> str:
    """Reverse a string."""
    return s[::-1]
''')

            search = SemanticSearch(repo_root, use_mock=True)
            count = await search.index_repository()
            assert count > 0

            # Search for math-related code (use low threshold for mock embeddings)
            results = await search.find_similar(
                "def subtract(a, b): return a - b",
                top_k=3,
                min_similarity=0.0,  # Mock embeddings have low similarity
            )
            assert len(results.results) > 0
