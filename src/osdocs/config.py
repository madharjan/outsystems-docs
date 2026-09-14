"""Agent and application configuration management for OutSystems-Docs MCP."""

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Optional, Any, Dict

try:
    import yaml
except ImportError:
    yaml = None

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

try:
    import tomli_w
except ImportError:
    tomli_w = None


def get_app_root() -> Path:
    """Base directory for resolving relative config paths (config.yaml, data dir, cache
    dir, log file) instead of the process's current working directory.

    An MCP client (Claude Code/Desktop, etc.) launches this server as a long-running
    process with its own, unrelated cwd -- a relative path like ``"data"`` would then
    resolve against wherever the client happens to run from, not the repo/install dir a
    manual ``--sync`` wrote it to.

    Frozen/Nuitka exe: the exe's own directory (matches the installer's config.yaml/data
    layout). Source checkout: the repository root.
    """
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


def resolve_path(path) -> Path:
    """Resolve a config path: an absolute path passes through; a relative one anchors to
    ``get_app_root()`` instead of the process cwd."""
    p = Path(path).expanduser()
    return p if p.is_absolute() else get_app_root() / p


# Application configuration defaults
DEFAULT_CONFIG = {
    "mcp": {
        "enabled": True,
        "sources": ["odc", "o11"],
        "search": {
            "max_results": 5,
            "min_score": 0.3,
        },
    },
    "embeddings": {
        "model": "BAAI/bge-small-en-v1.5",
        "cache_dir": ".cache/fastembed",
        "disable_hf_symlinks": False,
    },
    "index": {
        "data_dir": "data",
        "auto_refresh": False,
    },
    "logging": {
        "level": "INFO",
        "file": "",
    },
    "performance": {
        "worker_threads": 4,
        "cache_queries": True,
    },
    "secrets": {
        "hf_token": "",
    },
}


class AppConfig:
    """Application configuration loader and accessor."""

    _instance: Optional["AppConfig"] = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, config_path: Optional[Path] = None) -> None:
        """Load application configuration from YAML file."""
        if config_path is None:
            config_path = get_app_root() / "config.yaml"

        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    loaded = yaml.safe_load(f) if yaml else json.load(f)
                    self._config = {**DEFAULT_CONFIG}
                    self._merge_config(self._config, loaded or {})
            except Exception as e:
                print(f"Warning: Failed to load config from {config_path}: {e}")
                self._config = DEFAULT_CONFIG.copy()
        else:
            self._config = DEFAULT_CONFIG.copy()

        # Load HF_TOKEN from environment if not in config
        if not self._config.get("secrets", {}).get("hf_token"):
            self._config.setdefault("secrets", {})["hf_token"] = os.environ.get("HF_TOKEN", "")

    def _merge_config(self, base: Dict, updates: Dict) -> None:
        """Recursively merge configuration dictionaries."""
        for key, value in updates.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key (e.g., 'embeddings.model').

        Lazily loads the config on first access so callers don't need to race an explicit
        ``load_app_config()`` call against whichever module happens to import first.
        """
        if not self._config:
            self.load()
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration."""
        if not self._config:
            self.load()
        return self._config.copy()


# Global config instance
_app_config = AppConfig()


def load_app_config(config_path: Optional[Path] = None) -> AppConfig:
    """Load application configuration."""
    _app_config.load(config_path)
    return _app_config


def get_app_config() -> AppConfig:
    """Get loaded application configuration."""
    return _app_config


def _get_claude_desktop_config_path() -> Path:
    """Resolve claude_desktop_config.json, accounting for the Store/MSIX install.

    A packaged (MSIX/AppX) Claude Desktop install redirects ``%APPDATA%`` writes into
    a per-package virtualized folder (``Packages\\Claude_<id>\\LocalCache\\Roaming\\...``)
    instead of the real ``%APPDATA%\\Claude`` -- the app never reads a config written to
    the standard path in that case. Checked first, ahead of the standard path: an
    uninstalled/reinstalled Claude Desktop can leave a stale file behind at the standard
    path (empty ``mcpServers``) even while the active install is packaged, so a
    "does it exist" check alone picks the wrong one -- presence of the package directory
    itself means writes must go there. Falls back to the standard path when no packaged
    install is found (e.g. non-Windows, or a plain non-Store install).
    """
    fallback = Path("~/AppData/Roaming/Claude/claude_desktop_config.json").expanduser()

    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata:
        packages_path = Path(localappdata) / "Packages"
        if packages_path.exists():
            for entry in packages_path.iterdir():
                if entry.name.startswith("Claude_"):
                    return entry / "LocalCache" / "Roaming" / "Claude" / "claude_desktop_config.json"

    appdata = os.environ.get("APPDATA")
    return Path(appdata) / "Claude" / "claude_desktop_config.json" if appdata else fallback


_AGENTS = {
    "claude_code": {
        "display_name": "Claude Code",
        "config_path": "~/.claude.json",
        "config_key": "mcpServers",
        "command": "osdocs-mcp",
        "extra_fields": {"type": "stdio"},
    },
    "claude_desktop": {
        "display_name": "Claude Desktop",
        "config_path": _get_claude_desktop_config_path,
        "config_key": "mcpServers",
        "command": "osdocs-mcp",
        "extra_fields": {"type": "stdio"},
    },
    "cursor": {
        "display_name": "Cursor IDE",
        "config_path": "~/.cursor/mcp.json",
        "config_key": "mcpServers",
        "command": "osdocs-mcp",
        "extra_fields": {"type": "stdio"},
    },
    "gemini_cli": {
        "display_name": "Gemini CLI",
        "config_path": "~/.gemini/config.json",
        "config_key": "mcpServers",
        "command": "osdocs-mcp",
        "extra_fields": {"type": "stdio"},
    },
    "copilot_cli": {
        "display_name": "GitHub Copilot CLI",
        "config_path": "~/.copilot/mcp-config.json",
        "config_key": "servers",
        "command": "osdocs-mcp",
        "extra_fields": {"type": "stdio"},
    },
    "copilot_vscode": {
        "display_name": "GitHub Copilot (VS Code)",
        "config_path": "~/AppData/Roaming/Code/User/mcp.json",
        "config_key": "servers",
        "command": "osdocs-mcp",
        "extra_fields": {"type": "stdio"},
    },
    "jetbrains": {
        "display_name": "JetBrains IDEs",
        "config_path": "~/.jetbrains.ai/mcp.json",
        "config_key": "mcpServers",
        "command": "osdocs-mcp",
        "extra_fields": {"type": "stdio"},
    },
    "openai_codex": {
        "display_name": "OpenAI Codex",
        "config_path": "~/.codex/config.toml",
        "config_key": "mcp_servers",
        "command": "osdocs-mcp",
    },
    "opencode": {
        "display_name": "OpenCode",
        "config_path": "~/.config/opencode/opencode.json",
        "config_key": "mcp",
        "command": "osdocs-mcp",
        # OpenCode's schema wants an MCP entry shaped {"type": "local", "command": [argv...]}
        # -- a bare {"command": "<path>"} string (every other agent's shape) fails its
        # config validation.
        "command_as_list": True,
        "extra_fields": {"type": "local"},
    },
    "continue": {
        "display_name": "Continue (VS Code)",
        "config_path": "~/.continue/config.yaml",
        "config_key": "mcpServers",
        "command": "osdocs-mcp",
        "is_array": True,
    },
    "cline": {
        "display_name": "Cline (VS Code)",
        "config_path": "~/AppData/Roaming/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json",
        "config_key": "mcpServers",
        "command": "osdocs-mcp",
    },
    "windsurf": {
        "display_name": "Windsurf (Codeium)",
        "config_path": "~/.codeium/windsurf/mcp_config.json",
        "config_key": "servers",
        "command": "osdocs-mcp",
        "extra_fields": {"type": "stdio"},
    },
}


def get_agent(agent_key: str) -> Optional[dict]:
    """Get agent configuration by key."""
    return _AGENTS.get(agent_key)


def list_agents() -> list[tuple[int, str, str]]:
    """List all agents with index and display name."""
    agents = sorted(_AGENTS.items(), key=lambda x: x[1]["display_name"])
    return [(i + 1, key, agent["display_name"]) for i, (key, agent) in enumerate(agents)]


def expand_path(path: str) -> Path:
    """Expand ~ and environment variables in path."""
    return Path(path).expanduser()


def resolve_agent_config_path(agent: dict) -> Path:
    """Resolve an agent's config path, whether static string or a resolver callable."""
    config_path = agent["config_path"]
    return config_path() if callable(config_path) else expand_path(config_path)


def ensure_config_dir(config_path: Path) -> Path:
    """Ensure config directory exists."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    return config_path


def load_config(config_path: Path) -> dict:
    """Load JSON, YAML, or TOML configuration file (format inferred from extension)."""
    if not config_path.exists():
        return {}

    if config_path.suffix == ".toml":
        if not tomllib:
            print("Warning: tomli not installed (required for TOML config files)")
            return {}
        try:
            with open(config_path, "rb") as f:
                return tomllib.load(f)
        except Exception:
            return {}

    try:
        with open(config_path, "r") as f:
            content = f.read().strip()
            if not content:
                return {}

            if config_path.suffix == ".yaml" or config_path.suffix == ".yml":
                if yaml:
                    return yaml.safe_load(content) or {}
                else:
                    return {}
            else:
                return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return {}


def save_config(config_path: Path, data: dict) -> bool:
    """Save JSON, YAML, or TOML configuration file (format inferred from extension).

    Returns False (instead of raising) when the format needs an optional dependency
    that isn't installed -- callers writing agent configs need to surface that as a
    failed configure/remove rather than silently dropping the write.
    """
    ensure_config_dir(config_path)

    if config_path.suffix == ".toml":
        if not tomli_w:
            print("Warning: tomli_w not installed (required to write TOML config files)")
            return False
        with open(config_path, "wb") as f:
            tomli_w.dump(data, f)
        return True

    with open(config_path, "w") as f:
        if config_path.suffix == ".yaml" or config_path.suffix == ".yml":
            if yaml:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            else:
                json.dump(data, f, indent=2)
        else:
            json.dump(data, f, indent=2)
    return True


# Backwards compatibility
def load_json_config(config_path: Path) -> dict:
    """Load JSON configuration file (deprecated, use load_config)."""
    return load_config(config_path)


def save_json_config(config_path: Path, data: dict) -> None:
    """Save JSON configuration file (deprecated, use save_config)."""
    save_config(config_path, data)


def get_executable_path() -> str:
    """Get the command to launch osdocs-mcp for agent configs."""
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        # Running as the Nuitka-compiled/installed executable - it IS osdocs-mcp.
        # sys.executable can point to a synthetic "python.exe" shim Nuitka adds
        # for multiprocessing spawn support (not shipped in the installed dist
        # tree), so force the known exe name instead of trusting it verbatim.
        return str(Path(sys.executable).with_name("osdocs-mcp.exe"))

    # Running from a source checkout: use the run script that manages
    # the project-local .venv (created by scripts/run.cmd or run.sh).
    repo_root = Path(__file__).parent.parent.parent
    run_script = repo_root / "scripts" / ("run.cmd" if os.name == "nt" else "run.sh")
    return str(run_script)


def agent_status(agent_key: str) -> bool:
    """Check if agent is configured with OutSystems MCP."""
    agent = get_agent(agent_key)
    if not agent:
        return False

    config_path = resolve_agent_config_path(agent)
    if not config_path.exists():
        return False

    config = load_config(config_path)
    entries = config.get(agent["config_key"])

    if agent.get("is_array", False):
        return isinstance(entries, list) and any(
            isinstance(item, dict) and item.get("name") == "outsystems-docs" for item in entries
        )

    return isinstance(entries, dict) and "outsystems-docs" in entries


def add_agent(agent_key: str) -> bool:
    """Configure an agent for OutSystems MCP."""
    agent = get_agent(agent_key)
    if not agent:
        print(f"Unknown agent: {agent_key}")
        return False

    config_path = resolve_agent_config_path(agent)
    ensure_config_dir(config_path)

    config = load_config(config_path)
    config_key = agent["config_key"]
    exe_path = get_executable_path()
    entry = {"command": [exe_path] if agent.get("command_as_list", False) else exe_path}
    entry.update(agent.get("extra_fields", {}))

    if agent.get("is_array", False):
        items = config.get(config_key)
        if not isinstance(items, list):
            items = []
        existing = next((item for item in items if isinstance(item, dict) and item.get("name") == "outsystems-docs"), None)
        if existing:
            existing.update(entry)
        else:
            items.append({"name": "outsystems-docs", **entry})
        config[config_key] = items
    else:
        if not isinstance(config.get(config_key), dict):
            config[config_key] = {}
        config[config_key]["outsystems-docs"] = entry

    if not save_config(config_path, config):
        print(f"[ERR] Failed to configure {agent['display_name']}")
        return False

    print(f"[OK] Configured {agent['display_name']}")
    return True


def remove_agent(agent_key: str) -> bool:
    """Remove OutSystems MCP from an agent configuration."""
    agent = get_agent(agent_key)
    if not agent:
        print(f"Unknown agent: {agent_key}")
        return False

    config_path = resolve_agent_config_path(agent)
    if not config_path.exists():
        print(f"[--] {agent['display_name']} not configured")
        return False

    config = load_config(config_path)
    config_key = agent["config_key"]
    removed = False

    if agent.get("is_array", False):
        items = config.get(config_key)
        if isinstance(items, list):
            filtered = [item for item in items if not (isinstance(item, dict) and item.get("name") == "outsystems-docs")]
            removed = len(filtered) != len(items)
            config[config_key] = filtered
    else:
        if isinstance(config.get(config_key), dict) and "outsystems-docs" in config[config_key]:
            del config[config_key]["outsystems-docs"]
            removed = True

    if removed:
        if not save_config(config_path, config):
            print(f"[ERR] Failed to update {agent['display_name']}")
            return False
        print(f"[OK] Removed from {agent['display_name']}")
        return True

    print(f"[--] OutSystems MCP not found in {agent['display_name']}")
    return False


def agent_verify(agent_key: str) -> bool:
    """Verify an agent's config file: exists, parses, has the merge key and a servers
    entry, and the outsystems-docs command points at a path that exists on disk."""
    agent = get_agent(agent_key)
    if not agent:
        print(f"Unknown agent: {agent_key}")
        return False

    config_path = resolve_agent_config_path(agent)
    print(f"\nVerifying {agent['display_name']} configuration...")

    if not config_path.exists():
        print(f"  [ERR] Config file not found: {config_path}")
        return False
    print(f"  [OK] Config file exists")

    config = load_config(config_path)
    if not config:
        print(f"  [WARN] Config file is empty or invalid")
        return False
    print(f"  [OK] Config format valid")

    config_key = agent["config_key"]
    if config_key not in config:
        print(f"  [WARN] Key '{config_key}' not found in config")
        return False
    print(f"  [OK] Key '{config_key}' found")

    entries = config[config_key]
    is_array = agent.get("is_array", False)

    if is_array:
        if not isinstance(entries, list) or not entries:
            print(f"  [WARN] No servers configured in '{config_key}'")
            return False
        entry = next((item for item in entries if isinstance(item, dict) and item.get("name") == "outsystems-docs"), None)
    else:
        if not isinstance(entries, dict) or not entries:
            print(f"  [WARN] No servers configured in '{config_key}'")
            return False
        entry = entries.get("outsystems-docs")

    if not entry:
        print(f"  [WARN] outsystems-docs entry not found in '{config_key}'")
        return False

    command = entry.get("command", "")
    print(f"  [OK] outsystems-docs entry found: {command}")

    command_path = command[0] if isinstance(command, list) else command
    if command_path and Path(command_path).exists():
        print(f"  [OK] Command path accessible: {command_path}")
    elif command_path:
        print(f"  [WARN] Command path not accessible: {command_path}")

    print(f"{agent['display_name']} verification completed")
    return True


def backup_agent(agent_key: str, backup_dir: Optional[Path] = None) -> bool:
    """Backup an agent's configuration."""
    agent = get_agent(agent_key)
    if not agent:
        print(f"Unknown agent: {agent_key}")
        return False

    config_path = resolve_agent_config_path(agent)
    if not config_path.exists():
        print(f"[--] {agent['display_name']} not configured")
        return False

    if backup_dir is None:
        backup_dir = Path.home() / ".osdocs-mcp-backups"

    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_file = backup_dir / f"{agent_key}.json.bak"

    shutil.copy2(config_path, backup_file)
    print(f"[OK] Backed up {agent['display_name']} to {backup_file}")
    return True


def restore_agent(agent_key: str, backup_dir: Optional[Path] = None) -> bool:
    """Restore an agent's configuration from backup."""
    agent = get_agent(agent_key)
    if not agent:
        print(f"Unknown agent: {agent_key}")
        return False

    if backup_dir is None:
        backup_dir = Path.home() / ".osdocs-mcp-backups"

    backup_file = backup_dir / f"{agent_key}.json.bak"
    if not backup_file.exists():
        print(f"[--] No backup found for {agent['display_name']}")
        return False

    config_path = resolve_agent_config_path(agent)
    ensure_config_dir(config_path)
    shutil.copy2(backup_file, config_path)
    print(f"[OK] Restored {agent['display_name']} from backup")
    return True


def remove_all_agents() -> bool:
    """Remove OutSystems MCP from all agent configurations."""
    success_count = 0
    for key, _ in _AGENTS.items():
        if remove_agent(key):
            success_count += 1
    return success_count > 0
