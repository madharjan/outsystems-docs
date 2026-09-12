# Why This Exists - Technical Design

OutSystems-Docs MCP is a local semantic search server for OutSystems ODC and O11 docs. This page explains what it does, why it's designed this way, and what's deliberately out of scope.

## The Problem

Coding agents need accurate, up-to-date OutSystems documentation to write correct code. General web search and training data are unreliable, unverified, and quickly become stale. A local, verified search over the official docs fills that gap.

## Core Design

### What it does

Sync pipeline (`scripts\run.cmd --sync` / `./scripts/run.sh --sync`)

- Clones the official OutSystems doc repos from GitHub (shallow, fast)
- Parses Markdown and builds a searchable index
- Downloads a local embedding model (~100 MB, one-time)
- Generates a vector index for semantic search
- Records a timestamp so you know how fresh the docs are

MCP server (`scripts\run.cmd` / `./scripts/run.sh`, no args)

- Exposes three tools to your AI agent:
  - `search_docs(query)` - semantic search; each result includes its `url` and `last_updated`
  - `get_doc(source, path)` - `{content, url, last_updated}` for a single doc
  - `last_updated()` - timestamp of your last sync
- Supports filtering by platform: ODC, O11, or both
- Runs fully offline (no API calls, no cloud)

Agent configuration (`scripts\run.cmd --agent-*` / `./scripts/run.sh --agent-*`)

- Supports 12 AI coding agents out of the box
- One-command setup for each agent
- Backup/restore of previous configurations
- Interactive menu for easy management

### Why this design

Fully local - Embeddings and search happen on your machine. No docs ever leave your computer; no API keys needed.

Verified links - Every URL is resolved against the official OutSystems sitemap, so links never break.

Freshness-transparent - Every search result includes a timestamp. You always know if your docs are stale and should re-sync.

License-compliant - OutSystems docs are CC BY-NC-ND. We fetch and cache them locally for your own agent only; nothing is redistributed or hosted.

## Architecture

```
Sync (one-time + periodic refresh):
  GitHub repos > Parse >> Embed (local) > Vector index + timestamps

Query (real-time):
  User query > Local embedding > Vector search >> Ranked results with source URLs

Configuration (per-agent):
  osdocs-mcp --agent-add > Agent JSON config >> Added MCP server definition
```

Tools used: Python 3.10+, `uv`, `fastembed` (offline embeddings), `numpy` (search), `mcp[cli]` (protocol), `pyyaml` (config).

## Out of Scope

- Hosted / remote servers - Everything runs on your machine
- Automatic syncing - You schedule it (cron, launchd); no CI/hosted sync to respect the license
- Redistribution - Docs stay local to you

## Next Steps

- [Getting Started](GETTING_STARTED.md) - Setup and automation
- [Agent Configuration](AGENT_CONFIG.md) - Configure your agents
- [Windows Installer](INSTALLER.md) - Build a standalone .exe
- [GitHub Actions](GITHUB_ACTIONS.md) - Automated release builds
