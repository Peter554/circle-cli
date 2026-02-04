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

# Create a new version tag
tag tag message="":
    #!/bin/bash
    VERSION=$(uv version --short)
    if [[ "{{ tag }}" != "v$VERSION" ]]; then
        echo "Error: tag '{{ tag }}' doesn't match pyproject.toml version 'v$VERSION'"
        exit 1
    fi
    MSG="{{ message }}"
    MSG="${MSG:-Tag {{ tag }}}"
    git tag -a "{{ tag }}" -m "$MSG"
    echo "Tagged {{ tag }}"
