#!/usr/bin/env python3
"""Parse AGENTS.md files into structured chunks for PR review."""

import json
import re
from pathlib import Path


def slugify(text: str) -> str:
    """Convert section title to slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def extract_rules(content: str) -> tuple[list[str], list[str]]:
    """Extract rules and anti-patterns from markdown content."""
    rules = []
    anti_patterns = []

    for line in content.split("\n"):
        if line.strip().startswith("- "):
            rule = line.strip()[2:].strip()
            # Clean markdown formatting
            rule = re.sub(r"\*\*([^*]+)\*\*", r"\1", rule)
            rule = re.sub(r"`([^`]+)`", r"\1", rule)

            if any(neg in rule.lower() for neg in ["never", "don't", "avoid", "not "]):
                anti_patterns.append(rule)
            else:
                rules.append(rule)

    return rules, anti_patterns


def infer_applicable_paths(file_path: str, content: str) -> list[str]:
    """Infer which file patterns this chunk applies to."""
    # Check for explicit scope comment
    scope_match = re.search(r"<!--\s*scope:\s*(.+?)\s*-->", content)
    if scope_match:
        return [p.strip() for p in scope_match.group(1).split(",")]

    if file_path == "AGENTS.md" or file_path == "CLAUDE.md":
        lower_content = content.lower()
        paths = []
        if "python" in lower_content:
            paths.append("**/*.py")
        if "typescript" in lower_content or "javascript" in lower_content:
            paths.extend(["**/*.ts", "**/*.tsx"])
        if "sql" in lower_content:
            paths.append("**/*.sql")
        if "terraform" in lower_content:
            paths.append("**/*.tf")
        return paths or ["**/*"]

    domain_paths = {
        "backend": ["backend/**/*.py"],
        "cli": ["cli/**/*.py"],
        "portal": ["portal/**/*.ts", "portal/**/*.tsx"],
        "dbt": ["dbt/**/*.sql"],
        "lib": ["lib/**/*.py"],
        "machine_learning": ["machine_learning/**/*.py"],
        "infrastructure": ["infrastructure/**/*.tf"],
    }

    for domain, paths in domain_paths.items():
        if domain in file_path:
            return paths

    return ["**/*"]


def parse_markdown_file(file_path: Path, base_path: Path) -> list[dict]:
    """Parse a single AGENTS.md file into chunks."""
    chunks = []
    relative_path = str(file_path.relative_to(base_path))
    domain = relative_path.split("/")[0] if "/" in relative_path else "root"

    content = file_path.read_text()

    # Split by H2 headers
    sections = re.split(r"^## ", content, flags=re.MULTILINE)

    for section in sections[1:]:
        lines = section.strip().split("\n", 1)
        section_title = lines[0].strip()
        section_content = lines[1] if len(lines) > 1 else ""

        # Check for H3 subsections
        h3_sections = re.split(r"^### ", section_content, flags=re.MULTILINE)

        if len(h3_sections) > 1:
            for h3 in h3_sections[1:]:
                h3_lines = h3.strip().split("\n", 1)
                h3_title = h3_lines[0].strip()
                h3_content = h3_lines[1] if len(h3_lines) > 1 else ""

                rules, anti_patterns = extract_rules(h3)
                if rules or anti_patterns:  # Only include chunks with rules
                    chunks.append(
                        {
                            "id": f"{domain}-{slugify(section_title)}-{slugify(h3_title)}",
                            "file_path": relative_path,
                            "section": f"{section_title} > {h3_title}",
                            "content": h3_content.strip()[:2000],
                            "rules": rules[:10],
                            "anti_patterns": anti_patterns[:10],
                            "applicable_paths": infer_applicable_paths(relative_path, h3_content),
                            "domain": domain,
                        }
                    )
        else:
            rules, anti_patterns = extract_rules(section_content)
            if rules or anti_patterns:
                chunks.append(
                    {
                        "id": f"{domain}-{slugify(section_title)}",
                        "file_path": relative_path,
                        "section": section_title,
                        "content": section_content.strip()[:2000],
                        "rules": rules[:10],
                        "anti_patterns": anti_patterns[:10],
                        "applicable_paths": infer_applicable_paths(relative_path, section_content),
                        "domain": domain,
                    }
                )

    return chunks


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--base-path", default=".")
    parser.add_argument("--output", "-o")
    args = parser.parse_args()

    base_path = Path(args.base_path).resolve()
    agents_files = sorted(base_path.rglob("AGENTS.md"))
    claude_files = sorted(base_path.rglob("CLAUDE.md"))

    all_chunks = []
    for file_path in agents_files + claude_files:
        all_chunks.extend(parse_markdown_file(file_path, base_path))

    output = {
        "chunks": all_chunks,
        "total_chunks": len(all_chunks),
        "files_parsed": [str(f.relative_to(base_path)) for f in agents_files + claude_files],
    }

    result = json.dumps(output, indent=2)
    if args.output:
        Path(args.output).write_text(result)
    else:
        print(result)


if __name__ == "__main__":
    main()
