"""Configuration loading from CLI args, env vars, and config file."""

import enum
import os
import tomllib
from pathlib import Path

import pydantic

from . import flags


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
        """The full CircleCI project slug."""
        return f"{self.vcs}/{self.org}/{self.repo}"


def _find_config_file() -> Path | None:
    """Search upward from cwd for .circle-cli.toml."""
    current = Path.cwd()
    for directory in [current, *current.parents]:
        config_path = directory / ".circle-cli.toml"
        if config_path.exists():
            return config_path
    return None


def load_config(common_flags: flags.CommonFlags) -> AppConfig:
    """
    Load configuration from CLI args, env vars, config file, and git.
    """
    file_config = {}
    if config_path := _find_config_file():
        with open(config_path, "rb") as f:
            file_config = tomllib.load(f)

    # Resolve each field: CLI > env > file
    resolved_token = (
        common_flags.token or os.environ.get("CIRCLE_TOKEN") or file_config.get("token")
    )
    resolved_vcs = (
        common_flags.vcs or os.environ.get("CIRCLE_VCS") or file_config.get("vcs")
    )
    resolved_org = (
        common_flags.org or os.environ.get("CIRCLE_ORG") or file_config.get("org")
    )
    resolved_repo = (
        common_flags.repo or os.environ.get("CIRCLE_REPO") or file_config.get("repo")
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
