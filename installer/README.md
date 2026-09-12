# OutSystems-Docs MCP - Windows Installer

Standalone Windows installer for OutSystems-Docs MCP with integrated agent configuration.

## What's Included

- `osdocs-mcp.exe` - Unified CLI for MCP server, agent configuration, and documentation sync
- Python 3.10 Runtime - Fully bundled, no system Python required
- Dependencies - All required packages included (fastembed, numpy, mcp, etc.)
- Configuration - Interactive setup wizard with agent selection
- Start Menu Shortcuts:
  - Configure Agents - Interactive agent configuration
  - Sync Documentation - Refresh documentation index
  - Documentation - View README and help

## System Requirements

- Windows 10 / Windows 11
- No Python installation required (bundled)
- ~200 MB disk space
- Network connection (for initial documentation sync)

## Installation

1. Run Installer

   ```txt
   OutSystems-Docs-Setup.exe
   ```

2. Follow Setup Wizard
   - Accept license
   - Choose installation folder (default: `%APPDATA%\OutSystems-Docs\` for non-admin, or `%PROGRAMFILES%\OutSystems-Docs\` for admin)
   - Select AI agents to configure
   - Wait for agent configuration to complete

3. Post-Install Configuration
   - Installer automatically backs up existing agent configurations
   - Agent configuration happens during installation if selected
   - Configure additional agents anytime with Start Menu shortcuts

## First Run

### 1. Sync Documentation (First Time)

```cmd
REM Use %APPDATA% for non-admin, %PROGRAMFILES% for admin
cd "%APPDATA%\OutSystems-Docs"
osdocs-mcp.exe --sync
```

This downloads ~100 MB embedding model and builds local search index. Happens once.

### 2. Start MCP Server

```cmd
REM Use %APPDATA% for non-admin, %PROGRAMFILES% for admin
cd "%APPDATA%\OutSystems-Docs"
osdocs-mcp.exe
```

Server runs on stdio (used by your AI agent).

### 3. Verify Configuration

```cmd
REM Use %APPDATA% for non-admin, %PROGRAMFILES% for admin
cd "%APPDATA%\OutSystems-Docs"
osdocs-mcp.exe --agent-status
```

Shows configured agents and paths.

## Configure Agents

### Interactive Menu (Recommended)

```cmd
osdocs-mcp.exe --agent-interactive
```

Walk through agent setup step-by-step.

### Command Line

```cmd
REM Add specific agent
osdocs-mcp.exe --agent-add claude_code
osdocs-mcp.exe --agent-add claude_desktop

REM Check status
osdocs-mcp.exe --agent-status

REM Backup and restore
osdocs-mcp.exe --agent-backup claude_code
osdocs-mcp.exe --agent-restore claude_code
```

## Supported Agents

| Agent                    | Status    |
| ------------------------ | --------- |
| Claude Code              | Supported |
| Claude Desktop           | Supported |
| Cursor IDE               | Supported |
| Gemini CLI               | Supported |
| GitHub Copilot (CLI)     | Supported |
| GitHub Copilot (VS Code) | Supported |
| JetBrains IDEs           | Supported |
| Continue (VS Code)       | Supported |
| Cline (VS Code)          | Supported |
| Windsurf (Codeium)       | Supported |
| OpenCode                 | Supported |
| OpenAI Codex             | Supported |

## Backup & Restore

Existing agent configurations are automatically backed up before installer makes changes.

```powershell
# Backup specific agent
osdocs-mcp.exe --agent-backup claude_code

# Restore from backup
osdocs-mcp.exe --agent-restore claude_code
```

Backups stored in: `%USERPROFILE%\.osdocs-mcp-backups\`

## Troubleshooting

### "MCP server not found in agent"

1. Run `osmcp-config.exe --agent-status` to verify configuration
2. Restart your AI agent application
3. Check installation folder: `%APPDATA%\OutSystems-Docs\` (non-admin) or `%PROGRAMFILES%\OutSystems-Docs\` (admin)

### "Documentation search returns no results"

1. Run `osmcp-sync.exe` to download latest docs
2. Check that `data/` folder exists in installation directory
3. Verify at least 50 MB free disk space

### Agent configuration not working

1. Ensure agent's config directory exists
2. Run `osmcp-config.exe --agent-interactive` to reconfigure
3. Check agent logs for MCP connection errors

## Uninstallation

1. Go to Control Panel > Programs > Programs and Features
2. Find "OutSystems-Docs MCP"
3. Click "Uninstall"
4. Follow prompts

Uninstall removes:

- Start menu shortcuts
- Agent MCP server registrations (via --agent-remove-all)

Preserved (manual cleanup required):

- `~/.osdocs-mcp-backups/` (backup configs for restoring if needed)

Note: Agent configuration files (`.claude.json`, etc.) are preserved with MCP entries removed.

## Customization

Edit `config.yaml` in installation folder to customize:

- Documentation sources (ODC, O11)
- Search result limits
- Embedding model
- Log levels
- Performance tuning

Restart your AI agent application for changes to take effect.

## License & Legal

IMPORTANT: This software uses a three-tier license structure. Please review carefully:

### This Tool

Licensed under Community Terms (see LICENSE.txt)

- Use: Personal and internal business purposes only
- You may install and use locally
- You must not redistribute without attribution
- Community project, not affiliated with OutSystems

### OutSystems Documentation

Licensed under CC BY-NC-ND 4.0

- Copyright (c) OutSystems
- Local use only (kept on your machine)
- Non-commercial use only
- No redistribution allowed
- No derivative works allowed

This tool COMPLIES with CC BY-NC-ND 4.0 by:

- Keeping all documentation LOCAL to your machine
- Never redistributing documentation
- Never hosting documentation on shared/public servers
- NOT providing any export or redistribution capabilities
- Respecting OutSystems' intellectual property

### Dependencies

- fastembed - Apache License 2.0
- numpy - BSD License
- mcp[cli] - MIT License
- pyyaml - MIT License
- Python - Python Software Foundation License

See LICENSE.txt for full attribution and license details.

---

COMPLIANCE NOTICE:
By using this software, you agree to:

1. Use OutSystems documentation for non-commercial purposes only
2. Keep documentation local to your machine
3. NOT redistribute or republish OutSystems documentation
4. NOT host documentation on shared servers
5. Respect all license terms in LICENSE.txt and TERMS.txt

Version: 1.0.0  
Python: 3.10+  
Status: Community Project (not affiliated with OutSystems)
