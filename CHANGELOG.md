# Changelog

All notable changes to this project, in plain language.

## v1.0.1 2026-09-13

- Windows builds now trust Zscaler and Cloudflare corporate proxies automatically, so syncing docs and downloading the AI model works on locked-down company networks.
- GPU acceleration (DirectML) is now included in every Windows build by default — no separate `--directml` flag or separate download needed.
- Fixed OpenCode and 8 other agents (Claude Code, Claude Desktop, Cursor, Gemini CLI, GitHub Copilot CLI/VS Code, JetBrains, Windsurf) writing an invalid MCP config entry that some agents rejected.
- Fixed `--agent-add openai_codex` silently failing (missing `tomli_w` dependency in the lockfile).
- Fixed Claude Desktop not finding its config file on Microsoft Store/MSIX installs.
- Installer now auto-installs uv, MSVC Build Tools, and Inno Setup if they're missing.
- README now links to the Windows installer release.

## v1.0.0 - 2026-09-13

- First release: OutSystems Documentation MCP server.
- Windows installer with optional GPU acceleration.
- Config and agent setup management (Claude Code, Claude Desktop, Cursor, and others).
- Cache recovery for the local embedding model.
- General stability fixes.
