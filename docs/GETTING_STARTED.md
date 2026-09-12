# Getting Started

Setup instructions for Windows, macOS, and Linux.

## Prerequisites

- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/) (Python package manager)
- Your preferred AI coding agent (Claude Code, Claude Desktop, Cursor, etc.)

## Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url> outsystems-docs
cd outsystems-docs
```

### 2. Build the Documentation Index

`scripts\run.cmd` / `scripts/run.sh` create the `.venv` (via `uv sync`) on first run
automatically, so there's no separate install step.

Windows (cmd):

```cmd
scripts\run.cmd --sync
```

macOS / Linux:

```bash
./scripts/run.sh --sync
```

This downloads a ~100 MB embedding model (one-time) and builds a local searchable index in `data/`. Run anytime to refresh docs.

## Configure Your Agent

Use the wrapper to automatically configure your agent:

Windows (cmd):

```cmd
scripts\run.cmd --agent-interactive
```

macOS / Linux:

```bash
./scripts/run.sh --agent-interactive
```

Or configure a specific agent:

Windows (cmd):

```cmd
scripts\run.cmd --agent-add claude_code
scripts\run.cmd --agent-add claude_desktop
```

macOS / Linux:

```bash
./scripts/run.sh --agent-add claude_code
./scripts/run.sh --agent-add claude_desktop
```

See [Agent Configuration](AGENT_CONFIG.md) for all supported agents and manual setup.

## Test the Setup

To verify the MCP server works:

Windows (cmd):

```cmd
scripts\run.cmd
```

macOS / Linux:

```bash
./scripts/run.sh
```

This starts the MCP server in stdio mode. Press `Ctrl+C` to stop.

## Keep Docs Fresh - Automate Syncing

### Windows (Task Scheduler)

Create a scheduled task to sync docs daily:

```powershell
$taskName = "OutSystems Docs Sync"
$taskPath = "\"
$action = New-ScheduledTaskAction -Execute "C:\path\to\outsystems-docs\scripts\run.cmd" -Argument "--sync"
$trigger = New-ScheduledTaskTrigger -Daily -At 7:00AM
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -RunLevel Highest
```

Or use `schtasks` from cmd:

```cmd
schtasks /create /tn "OutSystems Docs Sync" /tr "C:\path\to\outsystems-docs\scripts\run.cmd --sync" /sc daily /st 07:00
```

### macOS / Linux (cron)

Add to your crontab (`crontab -e`):

```cron
0 7 * * * cd /path/to/outsystems-docs && ./scripts/run.sh --sync >> sync.log 2>&1
```

This runs daily at 7 AM.

### macOS (launchd)

Create `~/Library/LaunchAgents/com.outsystems.docs.sync.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.outsystems.docs.sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/outsystems-docs/scripts/run.sh</string>
        <string>--sync</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>7</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
</dict>
</plist>
```

Then enable it:

```bash
launchctl load ~/Library/LaunchAgents/com.outsystems.docs.sync.plist
```

## Next Steps

- Search the docs: Use `search_docs(query)` in your agent
- Configure more agents: See [Agent Configuration](AGENT_CONFIG.md)
- Automate releases: See [GitHub Actions](GITHUB_ACTIONS.md)
- Build an installer: See [Windows Installer](INSTALLER.md)
