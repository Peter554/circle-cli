# circle

A CLI for viewing CircleCI pipelines, workflows, jobs, and output.

## Features

- View pipelines with workflow status
- List workflows and jobs with status filtering
- View detailed job information including steps
- Display job output with ANSI color support
- Smart caching and concurrent API requests for faster responses
- Integration with Claude Code (via skill)

## Installation

```bash
uv tool install --from git+https://github.com/Peter554/circle-cli circle
# or (suggested to create an alias)
uvx --from git+https://github.com/Peter554/circle-cli circle  

# pinning to a specific version (see published tags)
uv tool install --from git+https://github.com/Peter554/circle-cli@v0.1.0 circle
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

## Commands

### pipelines

**Aliases:** `pipeline`, `p`

#### list (default)

Show latest pipelines for a branch. This is the default command for the CLI.

**Flags:**
- `--branch` - The branch to show pipelines for (defaults to current branch)
- `--number`, `-n` - Number of pipelines to show (default: 3)

```bash
# These are all equivalent (default command)
circle pipelines list
circle pipelines
circle p
circle

# Show pipelines for a specific branch
circle pipelines --branch main

# Show more pipelines
circle pipelines -n 10
```

### workflows

**Aliases:** `workflow`, `w`

#### list (default)

Show workflows for a pipeline.

**Flags:**
- `--pipeline`, `-p` - Pipeline ID (defaults to latest pipeline for current branch)

```bash
# These are all equivalent
circle workflows list
circle workflows
circle w

# Show workflows for a specific pipeline
circle workflows --pipeline abc123
```

### jobs

**Aliases:** `job`, `j`

#### list (default)

Show jobs for workflows.

**Flags:**
- `--pipeline`, `-p` - Pipeline ID (defaults to latest pipeline for current branch)
- `--workflow`, `-w` - Filter by workflow ID (can be specified multiple times)
- `--status`, `-s` - Filter by job status (can be specified multiple times)

```bash
# These are all equivalent
circle jobs list
circle jobs
circle j

# Show only failed jobs
circle jobs --status failed

# Filter by pipeline
circle jobs --pipeline abc123


# Filter by workflow
circle jobs --workflow abc123 --workflow def456
```

#### details

Show detailed information about a job, including its steps.

**Aliases:** `detail`

**Flags:**
- `--step-status`, `-s` - Filter steps by status (can be specified multiple times)

```bash
# Show job details
circle jobs details 12345

# Show only failed steps
circle jobs details 12345 --step-status failed
```

#### output

Show the output of a job step.

**Flags:**
- `--step` (required) - The step number to show output for
- `--parallel-index` - The parallel run index (required if there are multiple parallel runs)
- `--try-extract-summary` - Try to extract a summary from the output (e.g., pytest summary)

```bash
# Show output for step 5
circle jobs output 12345 --step 5

# Extract summary (useful for test output)
circle jobs output 12345 --step 5 --try-extract-summary

# For parallel runs
circle jobs output 12345 --step 5 --parallel-index 2
```

### cache

Manage the local cache. Cache is stored per-project based on the project slug.

#### size

Show total cache size.

```bash
circle cache size
```

#### prune

Proactively remove expired items from the cache. Note that expired items are also cleared automatically on access.

```bash
circle cache prune
```

#### clear

Clear all items from the cache.

```bash
circle cache clear
```

## Global Flags

These flags are available on all commands:

- `--token` - CircleCI API token
- `--vcs` - Version control system (`gh` or `bb`)
- `--org` - Organization name
- `--repo` - Repository name
- `--output-format`, `-f` - Output format (`pretty` or `json`)
- `--no-cache` - Disable caching
- `--log-level` - Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Claude Code Integration

A skill is available for [Claude Code](https://claude.com/claude-code) that teaches Claude how to use this CLI. Install it with:

```bash
circle install-claude-skill
```

This installs the skill to `~/.claude/skills/circle-cli/`. Use `--skills-dir` to specify a different location.

Once installed, Claude can automatically use the CLI to investigate CI failures, check pipeline status, and view job output.
