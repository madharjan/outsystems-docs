"""Tests for agent configuration management."""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import osdocs.config as config_module
from osdocs.config import (
    _AGENTS,
    add_agent,
    agent_status,
    backup_agent,
    expand_path,
    get_agent,
    get_executable_path,
    list_agents,
    load_config,
    remove_agent,
    remove_all_agents,
    restore_agent,
    save_config,
)


class TestAgentListing:
    """Tests for listing and fetching agents."""

    def test_list_agents_returns_all_agents_sorted_by_name(self):
        agents = list_agents()
        assert len(agents) == len(_AGENTS)
        # Verify sorted by display name
        display_names = [name for _, _, name in agents]
        assert display_names == sorted(display_names)

    def test_list_agents_format(self):
        agents = list_agents()
        for idx, key, name in agents:
            assert isinstance(idx, int)
            assert isinstance(key, str)
            assert isinstance(name, str)
            assert 1 <= idx <= len(_AGENTS)

    def test_get_agent_returns_known_agent(self):
        agent = get_agent("claude_code")
        assert agent is not None
        assert agent["display_name"] == "Claude Code"
        assert agent["config_path"] == "~/.claude.json"

    def test_get_agent_returns_none_for_unknown_agent(self):
        assert get_agent("unknown_agent") is None

    def test_all_agents_have_required_fields(self):
        for key, agent in _AGENTS.items():
            assert "display_name" in agent
            assert "config_path" in agent
            assert "config_key" in agent
            assert "command" in agent
            assert agent["command"] == "osdocs-mcp"


class TestPathOperations:
    """Tests for path expansion and directory handling."""

    def test_expand_path_handles_home_directory(self):
        path = expand_path("~/.claude.json")
        assert "~" not in str(path)
        assert path.is_absolute()

    def test_expand_path_preserves_absolute_paths(self, tmp_path):
        abs_path = str(tmp_path / "app")
        path = expand_path(abs_path)
        assert path.is_absolute()
        assert "app" in str(path)


class TestConfigIO:
    """Tests for loading and saving configurations."""

    def test_load_config_from_json(self, tmp_path):
        config_file = tmp_path / "config.json"
        data = {"mcpServers": {"outsystems-docs": {"command": "osdocs-mcp"}}}
        config_file.write_text(json.dumps(data))

        loaded = load_config(config_file)
        assert loaded == data

    def test_load_config_nonexistent_file_returns_empty_dict(self, tmp_path):
        config_file = tmp_path / "nonexistent.json"
        assert load_config(config_file) == {}

    def test_load_config_empty_file_returns_empty_dict(self, tmp_path):
        config_file = tmp_path / "empty.json"
        config_file.write_text("")
        assert load_config(config_file) == {}

    def test_load_config_invalid_json_returns_empty_dict(self, tmp_path):
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{invalid json}")
        assert load_config(config_file) == {}

    def test_save_config_creates_parent_directories(self, tmp_path):
        config_file = tmp_path / "a" / "b" / "config.json"
        data = {"key": "value"}

        save_config(config_file, data)

        assert config_file.exists()
        assert json.loads(config_file.read_text()) == data

    def test_save_and_load_round_trip(self, tmp_path):
        config_file = tmp_path / "config.json"
        original = {"mcpServers": {"outsystems-docs": {"command": "test"}}}

        save_config(config_file, original)
        loaded = load_config(config_file)

        assert loaded == original


class TestAgentConfiguration:
    """Tests for adding and removing agent configurations."""

    def test_add_agent_creates_config(self, tmp_path, monkeypatch):
        config_path = tmp_path / ".claude.json"
        monkeypatch.setattr(
            "osdocs.config.expand_path",
            lambda p: config_path if "claude" in p else expand_path(p)
        )

        add_agent("claude_code")

        assert config_path.exists()
        config = load_config(config_path)
        assert "mcpServers" in config
        assert "outsystems-docs" in config["mcpServers"]

    def test_add_agent_unknown_returns_false(self, capsys):
        result = add_agent("unknown_agent")
        assert result is False
        captured = capsys.readouterr()
        assert "Unknown agent" in captured.out

    def test_add_agent_modifies_existing_config(self, tmp_path, monkeypatch):
        config_path = tmp_path / ".claude.json"
        monkeypatch.setattr(
            "osdocs.config.expand_path",
            lambda p: config_path if "claude" in p else expand_path(p)
        )
        existing = {"mcpServers": {"other-tool": {"command": "other"}}}
        save_config(config_path, existing)

        add_agent("claude_code")

        config = load_config(config_path)
        assert "other-tool" in config["mcpServers"]
        assert "outsystems-docs" in config["mcpServers"]

    def test_remove_agent_deletes_from_config(self, tmp_path, monkeypatch):
        config_path = tmp_path / ".claude.json"
        monkeypatch.setattr(
            "osdocs.config.expand_path",
            lambda p: config_path if "claude" in p else expand_path(p)
        )
        config = {
            "mcpServers": {
                "outsystems-docs": {"command": "osdocs-mcp"},
                "other-tool": {"command": "other"},
            }
        }
        save_config(config_path, config)

        remove_agent("claude_code")

        loaded = load_config(config_path)
        assert "outsystems-docs" not in loaded["mcpServers"]
        assert "other-tool" in loaded["mcpServers"]

    def test_remove_agent_not_configured_returns_false(self, tmp_path, monkeypatch, capsys):
        config_path = tmp_path / ".claude.json"
        monkeypatch.setattr(
            "osdocs.config.expand_path",
            lambda p: config_path if "claude" in p else expand_path(p)
        )
        result = remove_agent("claude_code")
        assert result is False
        captured = capsys.readouterr()
        assert "not configured" in captured.out

    def test_remove_agent_unknown_returns_false(self, capsys):
        result = remove_agent("unknown_agent")
        assert result is False
        captured = capsys.readouterr()
        assert "Unknown agent" in captured.out

    def test_remove_all_agents_removes_from_all(self, tmp_path, monkeypatch):
        claude_code_config = tmp_path / ".claude.json"

        def mock_expand(p):
            if "claude_code" in p or ".claude.json" in p:
                return claude_code_config
            return expand_path(p)

        monkeypatch.setattr("osdocs.config.expand_path", mock_expand)

        config = {"mcpServers": {"outsystems-docs": {"command": "osdocs-mcp"}}}
        save_config(claude_code_config, config)

        remove_all_agents()

        # Verify agent removed
        claude_config = load_config(claude_code_config)
        assert "outsystems-docs" not in claude_config.get("mcpServers", {})


class TestAgentStatus:
    """Tests for checking agent configuration status."""

    def test_agent_status_returns_true_when_configured(self, tmp_path, monkeypatch):
        config_path = tmp_path / ".claude.json"
        monkeypatch.setattr(
            "osdocs.config.expand_path",
            lambda p: config_path if "claude" in p else expand_path(p)
        )
        config = {"mcpServers": {"outsystems-docs": {"command": "osdocs-mcp"}}}
        save_config(config_path, config)

        status = agent_status("claude_code")
        assert status is True

    def test_agent_status_returns_false_when_not_configured(self, tmp_path, monkeypatch):
        config_path = tmp_path / ".claude.json"
        monkeypatch.setattr(
            "osdocs.config.expand_path",
            lambda p: config_path if "claude" in p else expand_path(p)
        )
        status = agent_status("claude_code")
        assert status is False

    def test_agent_status_returns_false_when_tool_missing(self, tmp_path, monkeypatch):
        config_path = tmp_path / ".claude.json"
        monkeypatch.setattr(
            "osdocs.config.expand_path",
            lambda p: config_path if "claude" in p else expand_path(p)
        )
        config = {"mcpServers": {"other-tool": {"command": "other"}}}
        save_config(config_path, config)

        status = agent_status("claude_code")
        assert status is False

    def test_agent_status_unknown_agent_returns_false(self):
        status = agent_status("unknown_agent")
        assert status is False


class TestBackupRestore:
    """Tests for backing up and restoring configurations."""

    def test_backup_agent_creates_backup_file(self, tmp_path, monkeypatch):
        config_path = tmp_path / ".claude.json"
        monkeypatch.setattr(
            "osdocs.config.expand_path",
            lambda p: config_path if "claude" in p else expand_path(p)
        )
        config = {"mcpServers": {"outsystems-docs": {"command": "osdocs-mcp"}}}
        save_config(config_path, config)
        backup_dir = tmp_path / ".osdocs-mcp-backups"

        backup_agent("claude_code", backup_dir)

        backup_file = backup_dir / "claude_code.json.bak"
        assert backup_file.exists()
        assert json.loads(backup_file.read_text()) == config

    def test_backup_agent_nonexistent_config_returns_false(self, tmp_path, monkeypatch, capsys):
        config_path = tmp_path / ".claude.json"
        monkeypatch.setattr(
            "osdocs.config.expand_path",
            lambda p: config_path if "claude" in p else expand_path(p)
        )
        backup_dir = tmp_path / ".osdocs-mcp-backups"

        result = backup_agent("claude_code", backup_dir)
        assert result is False
        captured = capsys.readouterr()
        assert "not configured" in captured.out

    def test_restore_agent_recovers_from_backup(self, tmp_path, monkeypatch):
        config_path = tmp_path / ".claude.json"
        monkeypatch.setattr(
            "osdocs.config.expand_path",
            lambda p: config_path if "claude" in p else expand_path(p)
        )
        backup_dir = tmp_path / ".osdocs-mcp-backups"
        backup_dir.mkdir(parents=True)

        original = {"mcpServers": {"test": {"command": "test"}}}
        backup_file = backup_dir / "claude_code.json.bak"
        backup_file.write_text(json.dumps(original))

        restore_agent("claude_code", backup_dir)

        assert config_path.exists()
        restored = load_config(config_path)
        assert restored == original

    def test_restore_agent_no_backup_returns_false(self, tmp_path, monkeypatch, capsys):
        config_path = tmp_path / ".claude.json"
        monkeypatch.setattr(
            "osdocs.config.expand_path",
            lambda p: config_path if "claude" in p else expand_path(p)
        )
        backup_dir = tmp_path / ".osdocs-mcp-backups"
        backup_dir.mkdir(parents=True)

        result = restore_agent("claude_code", backup_dir)
        assert result is False
        captured = capsys.readouterr()
        assert "No backup found" in captured.out

    def test_restore_agent_unknown_agent_returns_false(self, capsys):
        result = restore_agent("unknown_agent")
        assert result is False
        captured = capsys.readouterr()
        assert "Unknown agent" in captured.out


class TestGetExecutablePath:
    """Tests for resolving the command written into agent configs."""

    def test_returns_sys_executable_when_frozen(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        assert get_executable_path() == sys.executable

    def test_returns_sys_executable_when_compiled(self, monkeypatch):
        monkeypatch.setattr(config_module, "__compiled__", True, raising=False)
        assert get_executable_path() == sys.executable

    def test_returns_run_cmd_path_on_windows(self):
        # This suite runs on Windows, so os.name is already "nt".
        path = get_executable_path()
        assert path.endswith("run.cmd")

    def test_returns_run_sh_path_on_posix(self, monkeypatch):
        # Only the ternary's os.name check needs faking here - swapping the
        # real os module out from under pathlib would break Path() itself.
        monkeypatch.setattr(config_module, "os", SimpleNamespace(name="posix"))
        path = get_executable_path()
        assert path.endswith("run.sh")

    def test_run_script_lives_in_repo_scripts_dir(self):
        path = Path(get_executable_path())
        expected_dir = Path(config_module.__file__).resolve().parent.parent.parent / "scripts"
        assert path.parent.resolve() == expected_dir.resolve()

    def test_frozen_check_takes_priority_over_source_checkout(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(os, "name", "nt")
        assert get_executable_path() == sys.executable


class TestDifferentConfigFormats:
    """Tests for handling different agent config formats."""

    def test_agent_github_copilot_cli_uses_different_config_key(self):
        agent = get_agent("copilot_cli")
        assert agent["config_key"] == "servers"

    def test_agent_github_copilot_vscode_uses_different_config_key(self):
        agent = get_agent("copilot_vscode")
        assert agent["config_key"] == "servers"

    def test_agent_jetbrains_has_correct_config_path(self):
        agent = get_agent("jetbrains")
        assert agent["config_path"] == "~/.jetbrains.ai/mcp.json"

    def test_agent_continue_yaml_support(self):
        agent = get_agent("continue")
        assert agent["config_path"] == "~/.continue/config.yaml"
