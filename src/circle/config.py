"""Configuration loading from CLI args, env vars, and config file."""

import enum
import os
import tomllib
from pathlib import Path

import pydantic


class AppConfigError(Exception): ...


class VCS(enum.StrEnum):
    github = "gh"
    bitbucket = "bb"


class AppConfig(pydantic.BaseModel):
    token: str
    vcs: VCS
    org: str
    repo: str

    @property
    def project_slug(self) -> str:
        """The CircleCI project slug."""
        return f"{self.vcs}/{self.org}/{self.repo}"


def _find_project_config_file() -> Path | None:
    """Search upward from cwd for .circle-cli.toml, stopping at git root."""
    current = Path.cwd()
    for directory in [current, *current.parents]:
        config_path = directory / ".circle-cli.toml"
        if config_path.exists():
            return config_path
        # Stop at git repository root
        if (directory / ".git").exists():
            break
    return None


def _get_home_config_file() -> Path | None:
    """Get the home directory config file if it exists."""
    home_config = Path.home() / ".circle-cli.toml"
    if home_config.exists():
        return home_config
    return None


def load_config(
    token_flag: str | None,
    vcs_flag: str | None,
    org_flag: str | None,
    repo_flag: str | None,
) -> AppConfig:
    """
    Load configuration from CLI args, env vars, project config, and home config.

    Priority: CLI flags > env vars > project config > home config
    """
    # Load home config first (lowest priority)
    home_config: dict[str, str] = {}
    if home_config_path := _get_home_config_file():
        with open(home_config_path, "rb") as f:
            home_config = tomllib.load(f)

    # Load project config (overrides home config)
    project_config: dict[str, str] = {}
    if project_config_path := _find_project_config_file():
        with open(project_config_path, "rb") as f:
            project_config = tomllib.load(f)

    # Merge: project config overrides home config
    file_config = {**home_config, **project_config}

    # Resolve each field: CLI > env > file
    resolved_token = (
        token_flag or os.environ.get("CIRCLE_TOKEN") or file_config.get("token")
    )
    resolved_vcs = (
        vcs_flag or os.environ.get("CIRCLE_VCS") or file_config.get("vcs") or VCS.github
    )
    resolved_org = org_flag or os.environ.get("CIRCLE_ORG") or file_config.get("org")
    resolved_repo = (
        repo_flag or os.environ.get("CIRCLE_REPO") or file_config.get("repo")
    )

    try:
        return AppConfig(
            token=resolved_token,  # ty: ignore[invalid-argument-type]
            vcs=resolved_vcs,  # ty: ignore[invalid-argument-type]
            org=resolved_org,  # ty: ignore[invalid-argument-type]
            repo=resolved_repo,  # ty: ignore[invalid-argument-type]
        )
    except pydantic.ValidationError as e:
        raise AppConfigError(str(e)) from e
