# circle

A CLI for viewing CircleCI pipelines, workflows, jobs, and output.

## Features

- View pipelines with workflow status
- List workflows and jobs with status filtering
- View detailed job information including steps
- Display job tests and output
- Smart caching and concurrent API requests for faster responses
- Token efficient integration with Claude Code (via skill)

## Installation

```bash
uv tool install --from git+https://github.com/Peter554/circle-cli circle
# or (suggested to create an alias)
uvx --from git+https://github.com/Peter554/circle-cli circle  
```

## Configuration

Configuration is loaded from multiple sources with the following priority:

**CLI flags > environment variables > project config > home config**

### Home config (shared across projects)

Create `~/.circle-cli.toml` for settings shared across all projects:

```toml
token = "your-circleci-token"
```

### Project config

Create `.circle-cli.toml` in your project root for project-specific settings:

```toml
org = "your-organization"
repo = "your-repository"
# vcs = "gh"  # optional, defaults to "gh" (GitHub). Use "bb" for Bitbucket.
```

The project config is searched upward from the current directory, stopping at the git repository root.

**Important:** Add `.circle-cli.toml` to your `.gitignore` or `.git/info/exclude` to keep your token secure.

### Environment variables and flags

Configuration can also be set via environment variables: `CIRCLE_TOKEN`, `CIRCLE_ORG`, `CIRCLE_REPO`, `CIRCLE_VCS` or CLI flags.

## Commands

### pipelines

**Aliases:** `pipeline`, `p`

#### list (default)

Show latest pipelines for a branch. This is the default command for the CLI.

**Flags:**
- `--branch`, `-b` - The branch to show pipelines for (defaults to current branch). Use `@any` to show your pipelines across all branches.
- `--number`, `-n` - Number of pipelines to show (default: 3)

```bash
# These are all equivalent (default command)
circle pipelines list
circle pipelines
circle p
circle

# Show pipelines for a specific branch
circle pipelines --branch main
circle pipelines -b main

# Show your pipelines across all branches
circle pipelines -b @any

# Show more pipelines
circle pipelines -n 10
```

#### details

Show details for a specific pipeline.

**Aliases:** `detail`

```bash
# By pipeline ID
circle pipelines details <pipeline-id>

# By pipeline number
circle pipelines details 123
```

### workflows

**Aliases:** `workflow`, `w`

#### list (default)

Show workflows for a pipeline.

**Flags:**
- `--pipeline`, `-p` - Pipeline ID or number (defaults to latest pipeline for current branch)

```bash
# These are all equivalent
circle workflows list
circle workflows
circle w

# Show workflows for a specific pipeline
circle workflows --pipeline abc123
circle workflows --pipeline 123
```

#### failed-tests

Show unique failed tests across all jobs in a workflow.

**Flags:**
- `--unique`, `-u` - Show unique files or classnames instead of individual tests (`file` or `classname`)
- `--include-jobs`, `-j` - Include which jobs each test failed in

```bash
# Show all failed tests for a workflow
circle workflows failed-tests <workflow-id>

# Include which jobs each test failed in
circle workflows failed-tests <workflow-id> --include-jobs

# Show only unique failing files
circle workflows failed-tests <workflow-id> --unique file

# Show only unique failing classnames (file + classname)
circle workflows failed-tests <workflow-id> --unique classname
```

### jobs

**Aliases:** `job`, `j`

#### list (default)

Show jobs for workflows.

**Flags:**
- `--pipeline`, `-p` - Pipeline ID or number (defaults to latest pipeline for current branch)
- `--workflow`, `-w` - Filter by workflow ID (can be specified multiple times)
- `--status`, `-s` - Filter by job status (can be specified multiple times). Prefix with `not:` to exclude a status.

```bash
# These are all equivalent
circle jobs list
circle jobs
circle j

# Show only failed jobs
circle jobs --status failed

# Show all jobs except successful ones
circle jobs --status not:success

# Filter by pipeline
circle jobs --pipeline abc123

# Filter by workflow
circle jobs --workflow abc123 --workflow def456
```

#### details

Show detailed information about a job, including its steps.

**Aliases:** `detail`

**Flags:**
- `--step-status`, `-s` - Filter steps by status (can be specified multiple times). Prefix with `not:` to exclude a status.

```bash
# Show job details
circle jobs details 12345

# Show only failed steps
circle jobs details 12345 --step-status failed

# Show all steps except successful ones
circle jobs details 12345 --step-status not:success
```

#### tests

Show test metadata for a job. Useful for identifying which tests failed before viewing full output.

**Flags:**
- `--status`, `-s` - Filter by test result (success, failure/failed, skipped). Can be specified multiple times. Prefix with `not:` to exclude a status.
- `--file`, `-f` - Filter tests by file path suffix
- `--include-messages`, `-m` - Show failure messages

```bash
# Show all tests for a job
circle jobs tests 12345

# Show only failed tests
circle jobs tests 12345 --status failed

# Show non-successful tests (failed + skipped)
circle jobs tests 12345 --status not:success

# Show failed tests with failure messages
circle jobs tests 12345 --status failed --include-messages

# Filter by file
circle jobs tests 12345 --file test_auth.py
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
- `--output-format`, `-o` - Output format (`pretty` or `markdown`)
- `--no-cache` - Disable caching
- `--log-level` - Log level (`debug`, `info`, `warning`, `error`, `critical`)

## Claude Code Integration

A skill is available for [Claude Code](https://claude.com/claude-code) that teaches Claude how to use this CLI. Install it with:

```bash
circle install-claude-skill
```

This installs the skill to `~/.claude/skills/circle-cli/`. Use `--skills-dir` to specify a different location.

Once installed, Claude can automatically use the CLI to investigate CI failures, check pipeline status, and view job output.
