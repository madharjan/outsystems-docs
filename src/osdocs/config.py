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


_AGENTS = {
    "claude_code": {
        "display_name": "Claude Code",
        "config_path": "~/.claude.json",
        "config_key": "mcpServers",
        "command": "osdocs-mcp",
    },
    "claude_desktop": {
        "display_name": "Claude Desktop",
        "config_path": "~/AppData/Roaming/Claude/claude_desktop_config.json",
        "config_key": "mcpServers",
        "command": "osdocs-mcp",
    },
    "cursor": {
        "display_name": "Cursor IDE",
        "config_path": "~/.cursor/mcp.json",
        "config_key": "mcpServers",
        "command": "osdocs-mcp",
    },
    "gemini_cli": {
        "display_name": "Gemini CLI",
        "config_path": "~/.gemini/config.json",
        "config_key": "mcpServers",
        "command": "osdocs-mcp",
    },
    "copilot_cli": {
        "display_name": "GitHub Copilot CLI",
        "config_path": "~/.copilot/mcp-config.json",
        "config_key": "servers",
        "command": "osdocs-mcp",
    },
    "copilot_vscode": {
        "display_name": "GitHub Copilot (VS Code)",
        "config_path": "~/AppData/Roaming/Code/User/mcp.json",
        "config_key": "servers",
        "command": "osdocs-mcp",
    },
    "jetbrains": {
        "display_name": "JetBrains IDEs",
        "config_path": "~/.jetbrains.ai/mcp.json",
        "config_key": "mcpServers",
        "command": "osdocs-mcp",
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
    },
    "continue": {
        "display_name": "Continue (VS Code)",
        "config_path": "~/.continue/config.yaml",
        "config_key": "mcpServers",
        "command": "osdocs-mcp",
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


def ensure_config_dir(config_path: Path) -> Path:
    """Ensure config directory exists."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    return config_path


def load_config(config_path: Path) -> dict:
    """Load JSON or YAML configuration file."""
    if not config_path.exists():
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


def save_config(config_path: Path, data: dict) -> None:
    """Save JSON or YAML configuration file."""
    ensure_config_dir(config_path)
    with open(config_path, "w") as f:
        if config_path.suffix == ".yaml" or config_path.suffix == ".yml":
            if yaml:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            else:
                json.dump(data, f, indent=2)
        else:
            json.dump(data, f, indent=2)


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

    config_path = expand_path(agent["config_path"])
    if not config_path.exists():
        return False

    config = load_config(config_path)
    config_key = agent["config_key"]
    return config_key in config and "outsystems-docs" in config.get(config_key, {})


def add_agent(agent_key: str) -> bool:
    """Configure an agent for OutSystems MCP."""
    agent = get_agent(agent_key)
    if not agent:
        print(f"Unknown agent: {agent_key}")
        return False

    config_path = expand_path(agent["config_path"])
    ensure_config_dir(config_path)

    config = load_config(config_path)

    if agent["config_key"] not in config:
        config[agent["config_key"]] = {}

    config[agent["config_key"]]["outsystems-docs"] = {
        "command": get_executable_path(),
    }

    save_config(config_path, config)
    print(f"✓ Configured {agent['display_name']}")
    return True


def remove_agent(agent_key: str) -> bool:
    """Remove OutSystems MCP from an agent configuration."""
    agent = get_agent(agent_key)
    if not agent:
        print(f"Unknown agent: {agent_key}")
        return False

    config_path = expand_path(agent["config_path"])
    if not config_path.exists():
        print(f"✗ {agent['display_name']} not configured")
        return False

    config = load_config(config_path)
    config_key = agent["config_key"]

    if config_key in config and "outsystems-docs" in config[config_key]:
        del config[config_key]["outsystems-docs"]
        save_config(config_path, config)
        print(f"✓ Removed from {agent['display_name']}")
        return True

    print(f"✗ OutSystems MCP not found in {agent['display_name']}")
    return False


def backup_agent(agent_key: str, backup_dir: Optional[Path] = None) -> bool:
    """Backup an agent's configuration."""
    agent = get_agent(agent_key)
    if not agent:
        print(f"Unknown agent: {agent_key}")
        return False

    config_path = expand_path(agent["config_path"])
    if not config_path.exists():
        print(f"✗ {agent['display_name']} not configured")
        return False

    if backup_dir is None:
        backup_dir = Path.home() / ".osdocs-mcp-backups"

    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_file = backup_dir / f"{agent_key}.json.bak"

    shutil.copy2(config_path, backup_file)
    print(f"✓ Backed up {agent['display_name']} to {backup_file}")
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
        print(f"✗ No backup found for {agent['display_name']}")
        return False

    config_path = expand_path(agent["config_path"])
    ensure_config_dir(config_path)
    shutil.copy2(backup_file, config_path)
    print(f"✓ Restored {agent['display_name']} from backup")
    return True


def remove_all_agents() -> bool:
    """Remove OutSystems MCP from all agent configurations."""
    success_count = 0
    for key, _ in _AGENTS.items():
        if remove_agent(key):
            success_count += 1
    return success_count > 0
