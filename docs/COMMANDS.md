# Commands

Every command you can run in this project, in one place.

## 1. App CLI (`osdocs-mcp`)

Run via `scripts\run.cmd` (Windows) / `./scripts/run.sh` (macOS/Linux) from a source checkout —
see [Wrapper scripts](#2-wrapper-scripts-scripts) below — or the installed `osdocs-mcp.exe` once
packaged. The flags below are the same either way.

| Command                                                               | Purpose                                            |
| --------------------------------------------------------------------- | -------------------------------------------------- |
| `osdocs-mcp`                                                          | Run the MCP server (stdio mode) — default, no args |
| `osdocs-mcp --sync [--data-dir DIR] [--source odc\|o11] [--no-links]` | Sync docs into the local index                     |
| `osdocs-mcp --agent-status`                                           | Show agent configuration status                    |
| `osdocs-mcp --agent-add AGENT`                                        | Configure a specific agent                         |
| `osdocs-mcp --agent-remove AGENT`                                     | Remove from a specific agent                       |
| `osdocs-mcp --agent-remove-all`                                       | Remove from all agents                             |
| `osdocs-mcp --agent-backup AGENT`                                     | Backup an agent's config                           |
| `osdocs-mcp --agent-restore AGENT`                                    | Restore an agent's config from backup              |
| `osdocs-mcp --agent-interactive`                                      | Interactive agent configuration menu               |
| `osdocs-mcp --version`                                                | Show version                                       |
| `osdocs-mcp --help`                                                   | Show help                                          |

See [Agent Configuration](AGENT_CONFIG.md) for the list of supported `AGENT` values and details.

`--sync`'s `--data-dir` defaults to `data`, resolved against the app/repo root (not the current
directory) — this matches where the MCP server itself looks, regardless of what launched it.

## 2. Wrapper scripts (`scripts/`)

Create the project-local `.venv` on first run (via `uv sync`), then forward all arguments
straight to `osdocs_mcp.py`:

```bash
scripts\run.cmd [args...]      # Windows
./scripts/run.sh [args...]     # macOS/Linux
```

Examples:

```bash
scripts\run.cmd --sync
scripts\run.cmd --sync --source odc
scripts\run.cmd --agent-interactive
scripts\run.cmd --directml --sync   # swap dev .venv to onnxruntime-directml first (AMD/Intel/NVIDIA GPU on Windows)
```

`--directml` swaps the dev `.venv`'s `onnxruntime` for `onnxruntime-directml`, then runs the
remaining args as usual; a later `uv sync` reverts it. Windows-only — `run.sh` rejects the flag
with an error pointing back to `run.cmd`, since DirectML doesn't exist on macOS/Linux.

## 3. Build / release scripts (`installer/`)

| Command                               | Purpose                                                                                                          |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `installer\build.cmd all`             | Build `osdocs-mcp.exe` (Nuitka, CPU-only onnxruntime) + Windows installer                                        |
| `installer\build.cmd all --directml`  | Same, but swaps in `onnxruntime-directml` first for GPU embedding (AMD/Intel/NVIDIA on Windows)                  |
| `installer\build.cmd installer`       | Build the installer only (exe must already exist)                                                                |
| `installer\clean.cmd`                 | Remove build artifacts, caches, logs, `dist/`, hash-gate files                                                   |
| `python installer\sync-version.py`    | Sync `pyproject.toml`'s version into `installer\outsystems-docs.iss` (also run automatically by `build.cmd all`) |

See [Installer](INSTALLER.md) and [Versioning](VERSIONING.md) for details.

## 4. Package manager / test commands (`uv`)

Use these directly only for the dev-only actions that have no wrapper equivalent. To run the
app itself, use the [wrapper scripts](#2-wrapper-scripts-scripts), not `uv run osdocs-mcp`.

| Command                                                                            | Purpose                                                      |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| `uv sync`                                                                          | Install/update dependencies into `.venv`                     |
| `uv run pytest src/tests/`                                                         | Run the test suite                                           |
| `uv run pytest src/tests/ --cov=osdocs --cov=osdocs_mcp --cov-report=term-missing` | Run tests with coverage, missing lines in terminal           |
| `uv run pytest src/tests/ --cov=osdocs --cov=osdocs_mcp --cov-report=html`         | Run tests with coverage, HTML report at `htmlcov/index.html` |

## Scheduling a daily sync

See the "Keep Docs Fresh" section in [Getting Started](GETTING_STARTED.md) for Windows Task
Scheduler, cron, and launchd examples — all of them call `scripts\run.cmd --sync` /
`./scripts/run.sh --sync`.
