"""Git helpers for getting current branch."""

import subprocess


def get_current_branch() -> str | None:
    """
    Get the current git branch, or None if not in a repo.

    Does not raise — returns None on any error.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()
        if branch and branch != "HEAD":  # Detached HEAD
            return branch
        return None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
