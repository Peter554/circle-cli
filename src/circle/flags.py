import dataclasses
import enum
from typing import Annotated

import cyclopts


class OutputFormat(enum.StrEnum):
    pretty = "pretty"
    json = "json"


@cyclopts.Parameter(name="*")
@dataclasses.dataclass(frozen=True)
class ProjectSlugFlags:
    """Flags for identifying the project (vcs, org, repo)."""

    vcs: Annotated[
        str | None,
        cyclopts.Parameter(
            name=["--vcs"],
            help="Version control system. Set via the CIRCLE_VCS environment variable, the .circle-cli.toml config file or the --vcs flag",
        ),
    ] = None
    org: Annotated[
        str | None,
        cyclopts.Parameter(
            name=["--org"],
            help="The organisation. Set via the CIRCLE_ORG environment variable, the .circle-cli.toml config file or the --org flag",
        ),
    ] = None
    repo: Annotated[
        str | None,
        cyclopts.Parameter(
            name=["--repo"],
            help="The repository. Set via the CIRCLE_REPO environment variable, the .circle-cli.toml config file or the --repo flag",
        ),
    ] = None
    log_level: Annotated[
        str,
        cyclopts.Parameter(
            name=["--log-level"],
            help="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        ),
    ] = "WARNING"


@cyclopts.Parameter(name="*")
@dataclasses.dataclass(frozen=True)
class CommonFlags(ProjectSlugFlags):
    """All common flags including token and project slug."""

    token: Annotated[
        str | None,
        cyclopts.Parameter(
            name=["--token"],
            help="CircleCI API token. Set via the CIRCLE_TOKEN environment variable, the .circle-cli.toml config file or the --token flag",
        ),
    ] = None
    no_cache: Annotated[
        bool,
        cyclopts.Parameter(
            name=["--no-cache"],
            help="Disable caching",
            negative=(),
        ),
    ] = False
    output_format: Annotated[
        OutputFormat,
        cyclopts.Parameter(
            name=["--output-format"],
            help="Output format",
        ),
    ] = OutputFormat.pretty
