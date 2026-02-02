# circle

A CLI for viewing CircleCI pipelines, workflows, jobs, and output.

## Features

- View recent pipelines with workflow status
- List workflows and jobs with filtering
- View detailed job information including steps
- Display job output with ANSI color support
- Smart caching for faster responses
- Concurrent API requests for performance

## Installation

```bash
uv tool install circle --from git+https://github.com/Peter554/circle-cli
```

## Configuration

Create `.circle-cli.toml` in your project root:

```toml
token = "your-circleci-token"
vcs = "gh"  # or "bb" for Bitbucket
org = "your-organization"
repo = "your-repository"
```

**Important:** Add `.circle-cli.toml` to your `.gitignore` or `.git/info/exclude` to keep your token secure.

Configuration can also be set via environment variables (`CIRCLE_TOKEN`, `CIRCLE_VCS`, `CIRCLE_ORG`, `CIRCLE_REPO`) or CLI flags. Priority: CLI flags > environment variables > config file.

## Usage

```bash
# View help
circle --help

# View recent pipelines
circle pipelines

# View workflows for latest pipeline
circle workflows 

# View jobs for latest pipeline
circle jobs

# View job details (includes steps)
circle job details <job-number>

# View job output
circle job output <job-number> --step <step-number>

# Try to extract summary from output
circle job output <job-number> --step <step-number> --try-extract-summary
```

## Claude Code Integration

A skill is available for [Claude Code](https://claude.com/claude-code) that teaches Claude how to use this CLI. Install it with:

```bash
circle install-claude-skill
```

This installs the skill to `~/.claude/skills/circle-cli/`. Use `--skills-dir` to specify a different location.

Once installed, Claude can automatically use the CLI to investigate CI failures, check pipeline status, and view job output.
