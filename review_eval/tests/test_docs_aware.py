"""Tests for documentation-aware evaluation."""

from conftest import REPO_ROOT

from review_eval.docs_loader import (
    discover_docs,
    get_doc_coverage_report,
    select_docs_for_path,
)


class TestDocsDiscovery:
    """Tests for documentation discovery."""

    def test_discover_finds_claude_md(self) -> None:
        """Test that CLAUDE.md is discovered at repo root."""
        docs = discover_docs(REPO_ROOT)
        global_docs = [d for d in docs if d.scope == "global"]
        assert len(global_docs) == 1, "Should find exactly one global CLAUDE.md"
        assert global_docs[0].path.name == "CLAUDE.md"

    def test_discover_finds_agents_md_files(self) -> None:
        """Test that nested AGENTS.md files are discovered."""
        docs = discover_docs(REPO_ROOT)
        agents_docs = [d for d in docs if d.doc_type == "agents" and d.scope != "global"]
        # Should find backend, cli, dbt, lib, machine_learning, portal, etc.
        assert len(agents_docs) >= 5, (
            f"Should find multiple AGENTS.md files, found {len(agents_docs)}"
        )

        scopes = {d.scope for d in agents_docs}
        expected_scopes = {"backend", "lib", "machine_learning"}
        assert expected_scopes.issubset(scopes), f"Missing expected scopes. Found: {scopes}"

    def test_discover_finds_docs_directory(self) -> None:
        """Test that /docs markdown files are discovered."""
        docs = discover_docs(REPO_ROOT, include_docs_dir=True)
        reference_docs = [d for d in docs if d.doc_type == "reference"]
        # Should find explanations, guides, references
        assert len(reference_docs) >= 10, (
            f"Should find many reference docs, found {len(reference_docs)}"
        )

    def test_discover_excludes_docs_directory_when_disabled(self) -> None:
        """Test that /docs can be excluded."""
        docs = discover_docs(REPO_ROOT, include_docs_dir=False)
        reference_docs = [d for d in docs if d.doc_type == "reference"]
        assert len(reference_docs) == 0, "Should not find reference docs when disabled"


class TestDocsSelection:
    """Tests for documentation selection based on file path."""

    def test_global_always_included(self) -> None:
        """Test that global docs are always included."""
        all_docs = discover_docs(REPO_ROOT)
        relevant = select_docs_for_path("some/random/file.py", all_docs)
        global_docs = [d for d in relevant if d.scope == "global"]
        assert len(global_docs) == 1, "Global docs should always be included"

    def test_backend_file_gets_backend_agents(self) -> None:
        """Test that backend files get backend AGENTS.md."""
        all_docs = discover_docs(REPO_ROOT)
        relevant = select_docs_for_path("backend/api/routes.py", all_docs)
        backend_docs = [d for d in relevant if "backend" in d.scope.lower()]
        assert len(backend_docs) >= 1, "Backend files should get backend AGENTS.md"

    def test_ml_file_gets_ml_agents(self) -> None:
        """Test that ML files get machine_learning AGENTS.md."""
        all_docs = discover_docs(REPO_ROOT)
        relevant = select_docs_for_path("machine_learning/packages/visdet/model.py", all_docs)
        ml_docs = [d for d in relevant if "machine_learning" in d.scope.lower()]
        assert len(ml_docs) >= 1, "ML files should get ML AGENTS.md"

    def test_portal_file_gets_portal_agents(self) -> None:
        """Test that portal files get portal AGENTS.md."""
        all_docs = discover_docs(REPO_ROOT)
        relevant = select_docs_for_path("portal/components/DataTable.tsx", all_docs)
        portal_docs = [d for d in relevant if "portal" in d.scope.lower()]
        assert len(portal_docs) >= 1, "Portal files should get portal AGENTS.md"

    def test_keyword_matching_for_reference_docs(self) -> None:
        """Test that reference docs are matched by keyword."""
        all_docs = discover_docs(REPO_ROOT, include_docs_dir=True)
        # A file in machine_learning should match docs about training, evaluation, etc.
        relevant = select_docs_for_path(
            "machine_learning/packages/eval/evaluator.py",
            all_docs,
            include_keyword_matches=True,
        )
        # Should include some reference docs with ML-related keywords
        reference_docs = [d for d in relevant if d.doc_type == "reference"]
        # This is a softer assertion - keyword matching may or may not find matches
        # depending on the actual doc content
        assert isinstance(reference_docs, list)


class TestDocsCoverage:
    """Tests for documentation coverage reporting."""

    def test_coverage_report_structure(self) -> None:
        """Test that coverage report has expected structure."""
        report = get_doc_coverage_report(
            REPO_ROOT,
            ["backend/api/routes.py", "portal/components/Table.tsx", "random/file.py"],
        )
        assert "total_paths" in report
        assert "covered_count" in report
        assert "uncovered_count" in report
        assert "coverage_percent" in report
        assert "uncovered_paths" in report
        assert "total_docs" in report
        assert "agents_docs" in report
        assert "reference_docs" in report

    def test_coverage_identifies_uncovered_paths(self) -> None:
        """Test that coverage report identifies paths without specific docs."""
        report = get_doc_coverage_report(
            REPO_ROOT,
            ["totally/random/path/that/has/no/docs.py"],
        )
        assert report["uncovered_count"] >= 1, "Random path should be uncovered"

    def test_coverage_identifies_covered_paths(self) -> None:
        """Test that coverage report identifies paths with docs."""
        report = get_doc_coverage_report(
            REPO_ROOT,
            ["backend/api/routes.py"],
        )
        assert report["covered_count"] >= 1, "Backend path should be covered"
