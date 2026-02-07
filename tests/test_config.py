import copy
import os

from circle.config import get_project_slug, get_token
from circle.flags import VCS, ProjectSlugFlags

HOME_CONFIG = {
    "token": "home-token",
    "vcs": "bb",
    "org": "home-org",
    "repo": "home-repo",
}

PROJECT_CONFIG = {
    "token": "proj-token",
    "vcs": "gh",
    "org": "proj-org",
    "repo": "proj-repo",
}

ENV_CONFIG = {
    "CIRCLE_TOKEN": "env-token",
    "CIRCLE_VCS": "bb",
    "CIRCLE_ORG": "env-org",
    "CIRCLE_REPO": "env-repo",
}


def _patch_config_sources(monkeypatch, *, home=None, project=None, env=None):
    """Clear all config sources, then set the ones provided."""
    monkeypatch.setattr("circle.config._get_home_config", lambda: home)
    monkeypatch.setattr("circle.config._get_project_config", lambda: project)
    for var in list(os.environ):
        if var.startswith("CIRCLE_"):
            monkeypatch.delenv(var)
    for var, val in (env or {}).items():
        monkeypatch.setenv(var, val)


class TestConfigHierarchy:
    def test_flags_override_everything(self, monkeypatch):
        _patch_config_sources(
            monkeypatch,
            home=HOME_CONFIG,
            project=PROJECT_CONFIG,
            env=ENV_CONFIG,
        )

        assert get_token("flag-token") == "flag-token"

        slug = get_project_slug(
            ProjectSlugFlags(vcs=VCS.github, org="flag-org", repo="flag-repo")
        )
        assert slug.project_slug == "gh/flag-org/flag-repo"

    def test_env_overrides_file_config(self, monkeypatch):
        _patch_config_sources(
            monkeypatch,
            home=HOME_CONFIG,
            project=PROJECT_CONFIG,
            env=ENV_CONFIG,
        )

        assert get_token(None) == "env-token"

        slug = get_project_slug(ProjectSlugFlags())
        assert slug.project_slug == "bb/env-org/env-repo"

    def test_project_config_overrides_home_config(self, monkeypatch):
        _patch_config_sources(
            monkeypatch,
            home=HOME_CONFIG,
            project=PROJECT_CONFIG,
        )

        assert get_token(None) == "proj-token"

        slug = get_project_slug(ProjectSlugFlags())
        assert slug.project_slug == "gh/proj-org/proj-repo"

    def test_home_config_as_fallback(self, monkeypatch):
        _patch_config_sources(
            monkeypatch,
            home=HOME_CONFIG,
            project={},
        )

        assert get_token(None) == "home-token"

        slug = get_project_slug(ProjectSlugFlags())
        assert slug.project_slug == "bb/home-org/home-repo"

    def test_default_config(self, monkeypatch):
        home_config = copy.deepcopy(HOME_CONFIG)
        # Delete fields with defaults
        del home_config["vcs"]

        _patch_config_sources(
            monkeypatch,
            home=home_config,
            project={},
        )

        _ = get_token(None)
        slug = get_project_slug(ProjectSlugFlags())

        assert slug.vcs == VCS.github
