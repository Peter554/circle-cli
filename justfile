[default]
_default:
    @just --list

# Run all checks
check *args:
    @just test {{ args }}
    @just lint

# Format the code
fmt:
    @uv run ruff format

# Run the tests
test *args:
    @uv run pytest {{ args }}

# Run the linters
lint:
    @uv run ty check
    @uv run ruff check
    @uv run ruff format --check
    @uv run deptry .
    @typos

# Auto-fix issues
fix:
    @uv run ruff check --fix
    @just fmt

# Create a new version tag based on the version in the pyproject.toml
tag:
    #!/bin/bash
    VERSION=$(uv version --short)
    read -p "Tag v$VERSION? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] && git tag -a "v$VERSION" -m "Release $VERSION" && echo "Tagged v$VERSION" || echo "Aborted"
