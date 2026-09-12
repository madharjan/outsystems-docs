# Agent Configuration

Configure OutSystems-Docs MCP for 12 AI coding agents using `osdocs-mcp`.

## Supported Agents

| Agent                    | Platform       | Config Path                                                             |
| ------------------------ | -------------- | ----------------------------------------------------------------------- |
| Claude Code              | Cross-platform | `~/.claude.json`                                                        |
| Claude Desktop           | Cross-platform | `~/AppData/Roaming/Claude/claude_desktop_config.json`                   |
| Cursor IDE               | Cross-platform | `~/.cursor/mcp.json`                                                    |
| Gemini CLI               | Cross-platform | `~/.gemini/config.json`                                                 |
| GitHub Copilot CLI       | Cross-platform | `~/.copilot/mcp-config.json`                                            |
| GitHub Copilot (VS Code) | Cross-platform | `~/AppData/Roaming/Code/User/mcp.json`                                  |
| JetBrains IDEs           | Cross-platform | `~/.jetbrains.ai/mcp.json`                                              |
| Continue (VS Code)       | Cross-platform | `~/.continue/config.yaml`                                               |
| Cline (VS Code)          | Cross-platform | `~/AppData/Roaming/Code/User/globalStorage/.../cline_mcp_settings.json` |
| Windsurf (Codeium)       | Cross-platform | `~/.codeium/windsurf/mcp_config.json`                                   |
| OpenCode                 | Cross-platform | `~/.config/opencode/opencode.json`                                      |
| OpenAI Codex             | Cross-platform | `~/.codex/config.toml`                                                  |

## Quick Start

Windows (cmd):

```cmd
:: Interactive configuration menu (recommended)
scripts\run.cmd --agent-interactive

:: Add specific agent
scripts\run.cmd --agent-add claude_code

:: Check configuration status
scripts\run.cmd --agent-status

:: Remove from agent
scripts\run.cmd --agent-remove claude_code

:: Backup configuration
scripts\run.cmd --agent-backup claude_code

:: Restore from backup
scripts\run.cmd --agent-restore claude_code
```

macOS / Linux:

```bash
# Interactive configuration menu (recommended)
./scripts/run.sh --agent-interactive

# Add specific agent
./scripts/run.sh --agent-add claude_code

# Check configuration status
./scripts/run.sh --agent-status

# Remove from agent
./scripts/run.sh --agent-remove claude_code

# Backup configuration
./scripts/run.sh --agent-backup claude_code

# Restore from backup
./scripts/run.sh --agent-restore claude_code
```

Once installed, the same flags work directly on `osdocs-mcp` / `osdocs-mcp.exe` too.

## Manual Configuration

If you prefer to configure manually, add `outsystems-docs` to your agent's MCP configuration:

Point each agent at the wrapper script, no args (it runs the MCP server in stdio mode).

### Claude Code

Windows (cmd):

```cmd
claude mcp add outsystems-docs -- C:\path\to\outsystems-docs\scripts\run.cmd
```

macOS / Linux:

```bash
claude mcp add outsystems-docs -- /path/to/outsystems-docs/scripts/run.sh
```

### Claude Desktop

Edit `~/AppData/Roaming/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "outsystems-docs": {
      "command": "C:\\path\\to\\outsystems-docs\\scripts\\run.cmd"
    }
  }
}
```

(macOS/Linux: `"command": "/path/to/outsystems-docs/scripts/run.sh"`.)

### Cursor IDE

Edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "outsystems-docs": {
      "command": "/path/to/outsystems-docs/scripts/run.sh"
    }
  }
}
```

(Windows: `"command": "C:\\path\\to\\outsystems-docs\\scripts\\run.cmd"`.)

### GitHub Copilot (VS Code)

Edit `~/AppData/Roaming/Code/User/mcp.json`:

```json
{
  "servers": {
    "outsystems-docs": {
      "type": "stdio",
      "command": "C:\\path\\to\\outsystems-docs\\scripts\\run.cmd"
    }
  }
}
```

(macOS/Linux: `"command": "/path/to/outsystems-docs/scripts/run.sh"`.)

### JetBrains IDEs

Edit `~/.jetbrains.ai/mcp.json`:

```json
{
  "mcpServers": {
    "outsystems-docs": {
      "command": "/path/to/outsystems-docs/scripts/run.sh"
    }
  }
}
```

(Windows: `"command": "C:\\path\\to\\outsystems-docs\\scripts\\run.cmd"`.)

## Backups

Configurations are automatically backed up before changes. Backups are stored in `~/.osdocs-mcp-backups/`.

To restore a previous configuration:

Windows (cmd):

```cmd
scripts\run.cmd --agent-restore claude_code
```

macOS / Linux:

```bash
./scripts/run.sh --agent-restore claude_code
```

## Troubleshooting

Agent not found after configuration:

- Run `scripts\run.cmd --agent-status` (`./scripts/run.sh --agent-status` on macOS/Linux) to verify
- Check the config file exists at the expected path
- Restart your agent application

Configuration not applied:

- Ensure the agent looks for MCP servers in the correct location
- Try manual configuration as a fallback
- Check agent logs for MCP server connection errors

Import or dependency errors:

- Run `uv sync` to install dependencies
- Check Python version is 3.10 or higher: `python --version`
