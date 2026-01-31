# circle

A focused CLI for viewing CircleCI pipeline status and investigating failures.

## Installation

```bash
uv tool install .
```

## Configuration

Configure via environment variables, config file, or CLI flags.

### Environment Variables

```bash
export CIRCLE_TOKEN=your-circleci-api-token
export CIRCLE_VCS=gh  # "gh" for GitHub, "bb" for Bitbucket
export CIRCLE_ORG=your-org
export CIRCLE_REPO=your-repo
```

### Config File

Create `.circle-cli.toml` in your project root:

```toml
token = "your-circleci-api-token"
vcs = "gh"
org = "your-org"
repo = "your-repo"
```

> **⚠️ Security Warning:** If you store your token in `.circle-cli.toml`, add it to `.gitignore` or `.git/info/exclude` to prevent accidentally committing secrets to version control. For better security, use environment variables instead of storing tokens in files.

## Usage

### View Recent Pipelines

```bash
circle                    # default command, uses current git branch
circle pipes              # alias
circle pipes -b main      # specify branch
```

### View Failures

```bash
circle fails                    # most recent pipeline
circle fails -p abc123          # specific pipeline (by alias)
circle fails -w xyz789          # specific workflow
circle fails -j 12345           # specific job output
circle fails --with-job-outputs # show full outputs inline
```

## Features

- 🚀 Fast caching with intelligent TTL
- 🔗 Short aliases for long UUIDs
- 📊 Rich terminal output
- 🔍 Pytest failure extraction
- ⚡ Shows failures from running pipelines
