"""Configuration loading from CLI args, env vars, and config file."""

from __future__ import annotations

import functools
import os
import tomllib
import typing
from pathlib import Path

import pydantic

from . import flags


class ConfigError(Exception): ...


def _get_home_config_file() -> Path | None:
    """Get the home directory config file if it exists."""
    home_config = Path.home() / ".circle-cli.toml"
    if home_config.exists():
        return home_config
    return None


@functools.cache
def _get_home_config() -> dict | None:
    if home_config_path := _get_home_config_file():
        with open(home_config_path, "rb") as f:
            return tomllib.load(f)
    return None


def _get_project_config_file() -> Path | None:
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


@functools.cache
def _get_project_config() -> dict | None:
    if project_config_path := _get_project_config_file():
        with open(project_config_path, "rb") as f:
            return tomllib.load(f)
    return None


class _Config(typing.TypedDict):
    token: object
    vcs: object
    org: object
    repo: object


class _PartialConfig(typing.TypedDict, total=False):
    token: object
    vcs: object
    org: object
    repo: object


# Note: Do not @functools.cache here, since it messes up the type checking.
def _load_config(
    **flags_: typing.Unpack[_PartialConfig],
) -> _Config:
    """
    Load configuration from CLI args, env vars, project config, and home config.

    Priority: CLI flags > env vars > project config > home config
    """
    home_config = _get_home_config() or {}
    project_config = _get_project_config() or {}

    # Merge: project config overrides home config
    file_config = {**home_config, **project_config}

    # Resolve each field: CLI > env > file
    config: _Config = {
        # Token
        "token": flags_.get("token")
        or os.environ.get("CIRCLE_TOKEN")
        or file_config.get("token"),
        # VCS
        "vcs": flags_.get("vcs")
        or os.environ.get("CIRCLE_VCS")
        or file_config.get("vcs")
        or flags.VCS.github,
        # Org
        "org": flags_.get("org")
        or os.environ.get("CIRCLE_ORG")
        or file_config.get("org"),
        # Repo
        "repo": flags_.get("repo")
        or os.environ.get("CIRCLE_REPO")
        or file_config.get("repo"),
    }

    return config


def get_token(
    token_flag: str | None,
) -> str:
    config = _load_config(token=token_flag)
    token = config["token"]
    ta = pydantic.TypeAdapter(str)
    try:
        return ta.validate_python(token)
    except pydantic.ValidationError as e:
        raise ConfigError(str(e)) from e


def get_project_slug(flags_: flags.ProjectSlugFlags) -> ProjectSlug:
    config = _load_config(vcs=flags_.vcs, org=flags_.org, repo=flags_.repo)
    try:
        return ProjectSlug(**config)  # ty: ignore
    except pydantic.ValidationError as e:
        raise ConfigError(str(e)) from e


class ProjectSlug(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="ignore", frozen=True)

    vcs: flags.VCS
    org: str
    repo: str

    @property
    def project_slug(self) -> str:
        """The CircleCI project slug."""
        return f"{self.vcs}/{self.org}/{self.repo}"
