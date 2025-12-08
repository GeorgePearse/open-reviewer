{ pkgs, lib, config, inputs, ... }:

{
  # Disable automatic cachix management (requires trusted-user)
  cachix.enable = false;

  # Python 3.12 environment
  languages.python = {
    enable = true;
    version = "3.12";
    uv = {
      enable = true;
      sync.enable = true;
    };
  };

  # Node.js 20 environment
  languages.javascript = {
    enable = true;
    package = pkgs.nodejs_20;
    npm.enable = true;
  };

  # System packages for native extensions and development
  packages = with pkgs; [
    # Build tools for native extensions (tree-sitter)
    gcc
    gnumake
    pkg-config

    # Tree-sitter for code parsing
    tree-sitter

    # Git operations
    git
    gh

    # Documentation
    python312Packages.mkdocs-material
  ];

  # Environment variables
  env = {
    PYTHONDONTWRITEBYTECODE = "1";
    UV_SYSTEM_PYTHON = "1";
  };

  # Scripts for common tasks
  scripts = {
    dev-setup.exec = ''
      cd review_eval && uv sync --all-extras
      echo "Development environment ready!"
    '';

    test.exec = ''
      cd review_eval && uv run pytest -v "$@"
    '';

    docs-serve.exec = ''
      mkdocs serve
    '';

    docs-build.exec = ''
      mkdocs build --strict
    '';

    index-repo.exec = ''
      cd review_eval && uv run python -m review_eval.index_repo "$@"
    '';

    lint.exec = ''
      cd review_eval && uv run ruff check .
    '';

    format.exec = ''
      cd review_eval && uv run ruff format .
    '';
  };

  # Git hooks (pre-commit)
  git-hooks.hooks = {
    ruff.enable = true;
    ruff-format.enable = true;
  };

  # Enter shell message
  enterShell = ''
    echo ""
    echo "open-reviewer development environment"
    echo "======================================"
    echo "Python: $(python --version)"
    echo "Node:   $(node --version)"
    echo "uv:     $(uv --version)"
    echo ""
    echo "Available commands:"
    echo "  dev-setup   - Install Python dependencies"
    echo "  test        - Run pytest"
    echo "  docs-serve  - Serve documentation locally"
    echo "  docs-build  - Build documentation"
    echo "  index-repo  - Index repository for semantic search"
    echo "  lint        - Run ruff linter"
    echo "  format      - Format code with ruff"
    echo ""
  '';
}
