import pytest

from review_eval.semantic.embeddings.chunker import TREE_SITTER_AVAILABLE, chunk_code


@pytest.mark.skipif(not TREE_SITTER_AVAILABLE, reason="Tree-sitter not available")
class TestPolyglotChunker:
    def test_chunk_typescript(self) -> None:
        code = """
        function add(a: number, b: number): number {
            return a + b;
        }

        class Calculator {
            subtract(a: number, b: number): number {
                return a - b;
            }
        }
        
        interface User {
            name: string;
        }
        """
        chunks = chunk_code(code, "test.ts", "typescript")

        names = {c.name for c in chunks}
        print(f"Found chunks: {[c.name for c in chunks]}")

        assert "add" in names
        assert "Calculator" in names
        assert "subtract" in names
        assert "User" in names

        # Check types
        type_map = {c.name: c.chunk_type for c in chunks}
        assert type_map["add"] == "function"
        assert type_map["Calculator"] == "class"
        assert type_map["subtract"] == "method"
        assert type_map["User"] == "class"

    def test_chunk_go(self) -> None:
        code = """
        package main

        func Add(a int, b int) int {
            return a + b
        }

        type User struct {
            Name string
        }

        func (u *User) Greet() string {
            return "Hello " + u.Name
        }
        """
        chunks = chunk_code(code, "main.go", "go")

        names = {c.name for c in chunks}
        print(f"Found chunks: {[c.name for c in chunks]}")

        assert "Add" in names
        assert "User" in names
        assert "Greet" in names

        type_map = {c.name: c.chunk_type for c in chunks}
        assert type_map["Add"] == "function"
        assert type_map["User"] == "class"
        assert type_map["Greet"] == "method"

    def test_chunk_rust(self) -> None:
        code = """
        fn add(a: i32, b: i32) -> i32 {
            a + b
        }

        struct Point {
            x: i32,
            y: i32,
        }

        impl Point {
            fn new(x: i32, y: i32) -> Self {
                Self { x, y }
            }
        }
        """
        chunks = chunk_code(code, "lib.rs", "rust")

        names = {c.name for c in chunks}
        print(f"Found chunks: {[c.name for c in chunks]}")

        assert "add" in names
        assert "Point" in names
        assert "new" in names

        type_map = {c.name: c.chunk_type for c in chunks}
        assert type_map["add"] == "function"
        assert type_map["Point"] == "class"
        assert type_map["new"] == "function"

    def test_chunk_tsx_arrow_function(self) -> None:
        code = """
        export const MyComponent = () => {
            return <div>Hello</div>;
        };
        """
        chunks = chunk_code(code, "test.tsx", "tsx")

        names = {c.name for c in chunks}
        assert "MyComponent" in names
        assert chunks[0].chunk_type == "function"

    def test_chunk_java(self) -> None:
        code = """
        public class Calculator {
            public int add(int a, int b) {
                return a + b;
            }
        }
        
        public interface Operation {
            void execute();
        }
        """
        chunks = chunk_code(code, "Calculator.java", "java")

        names = {c.name for c in chunks}
        print(f"Found chunks: {[c.name for c in chunks]}")

        assert "Calculator" in names
        assert "add" in names
        assert "Operation" in names

        type_map = {c.name: c.chunk_type for c in chunks}
        assert type_map["Calculator"] == "class"
        assert type_map["add"] == "method"
        assert type_map["Operation"] == "class"
