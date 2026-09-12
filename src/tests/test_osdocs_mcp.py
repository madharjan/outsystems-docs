"""Tests for the osdocs_mcp CLI dispatcher (src/osdocs_mcp.py): main()'s argv handling."""

import sys
from unittest.mock import MagicMock

import osdocs_mcp


def test_bare_invocation_runs_server_and_returns_its_result(monkeypatch):
    """server_main is imported lazily inside main() so --sync etc. don't pay for MCP
    server init; patch the source it's imported from rather than a module attribute."""
    sentinel = object()
    monkeypatch.setattr("osdocs.server.main", lambda: sentinel)
    monkeypatch.setattr(sys, "argv", ["osdocs-mcp"])

    assert osdocs_mcp.main() is sentinel


def test_version_returns_zero_and_prints_version(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["osdocs-mcp", "--version"])

    result = osdocs_mcp.main()

    assert result == 0
    assert "osdocs-mcp" in capsys.readouterr().out


def test_help_returns_zero_and_prints_usage(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["osdocs-mcp", "--help"])

    result = osdocs_mcp.main()

    assert result == 0
    assert "Usage:" in capsys.readouterr().out


def test_unknown_command_returns_one(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["osdocs-mcp", "--bogus"])

    result = osdocs_mcp.main()

    assert result == 1
    assert "Unknown command" in capsys.readouterr().out


def test_sync_returns_zero_not_the_sync_report(monkeypatch):
    """Regression: main() must not forward sync_main()'s return value to sys.exit().

    sync_main() returns a SyncReport dataclass, not an int. main() used to do
    `return sync_main(...)`, so `sys.exit(main())` treated the truthy SyncReport object as a
    failure -- printing its repr and exiting 1 even though the sync succeeded.
    """
    fake_report = MagicMock(name="SyncReport")
    monkeypatch.setattr(osdocs_mcp, "sync_main", lambda argv: fake_report)
    monkeypatch.setattr(sys, "argv", ["osdocs-mcp", "--sync"])

    result = osdocs_mcp.main()

    assert result == 0
    assert result is not fake_report


def test_sync_forwards_remaining_args_to_sync_main(monkeypatch):
    captured = {}

    def fake_sync_main(argv):
        captured["argv"] = argv
        return MagicMock()

    monkeypatch.setattr(osdocs_mcp, "sync_main", fake_sync_main)
    monkeypatch.setattr(sys, "argv", ["osdocs-mcp", "--sync", "--source", "odc", "--no-links"])

    osdocs_mcp.main()

    assert captured["argv"] == ["--source", "odc", "--no-links"]


def test_agent_status_returns_zero_and_prints_status(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["osdocs-mcp", "--agent-status"])

    result = osdocs_mcp.main()

    assert result == 0
    assert "Agent Configuration Status" in capsys.readouterr().out


def test_agent_interactive_quits_immediately(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt="": "quit")
    monkeypatch.setattr(sys, "argv", ["osdocs-mcp", "--agent-interactive"])

    assert osdocs_mcp.main() == 0


def test_agent_add_success_returns_zero(monkeypatch):
    monkeypatch.setattr(osdocs_mcp, "add_agent", lambda key: True)
    monkeypatch.setattr(sys, "argv", ["osdocs-mcp", "--agent-add", "claude_code"])

    assert osdocs_mcp.main() == 0


def test_agent_add_failure_returns_one(monkeypatch):
    monkeypatch.setattr(osdocs_mcp, "add_agent", lambda key: False)
    monkeypatch.setattr(sys, "argv", ["osdocs-mcp", "--agent-add", "claude_code"])

    assert osdocs_mcp.main() == 1


def test_agent_add_without_agent_arg_falls_through_to_unknown_command(monkeypatch, capsys):
    # main() requires len(sys.argv) > 2 for --agent-add; without it, nothing matches.
    monkeypatch.setattr(sys, "argv", ["osdocs-mcp", "--agent-add"])

    result = osdocs_mcp.main()

    assert result == 1
    assert "Unknown command" in capsys.readouterr().out


def test_agent_remove_success_returns_zero(monkeypatch):
    monkeypatch.setattr(osdocs_mcp, "remove_agent", lambda key: True)
    monkeypatch.setattr(sys, "argv", ["osdocs-mcp", "--agent-remove", "claude_code"])

    assert osdocs_mcp.main() == 0


def test_agent_remove_failure_returns_one(monkeypatch):
    monkeypatch.setattr(osdocs_mcp, "remove_agent", lambda key: False)
    monkeypatch.setattr(sys, "argv", ["osdocs-mcp", "--agent-remove", "claude_code"])

    assert osdocs_mcp.main() == 1


def test_agent_remove_all_success_returns_zero(monkeypatch):
    monkeypatch.setattr("osdocs.config.remove_all_agents", lambda: True)
    monkeypatch.setattr(sys, "argv", ["osdocs-mcp", "--agent-remove-all"])

    assert osdocs_mcp.main() == 0


def test_agent_remove_all_failure_returns_one(monkeypatch):
    monkeypatch.setattr("osdocs.config.remove_all_agents", lambda: False)
    monkeypatch.setattr(sys, "argv", ["osdocs-mcp", "--agent-remove-all"])

    assert osdocs_mcp.main() == 1


def test_agent_backup_success_returns_zero(monkeypatch):
    monkeypatch.setattr(osdocs_mcp, "backup_agent", lambda key: True)
    monkeypatch.setattr(sys, "argv", ["osdocs-mcp", "--agent-backup", "claude_code"])

    assert osdocs_mcp.main() == 0


def test_agent_restore_success_returns_zero(monkeypatch):
    monkeypatch.setattr(osdocs_mcp, "restore_agent", lambda key: True)
    monkeypatch.setattr(sys, "argv", ["osdocs-mcp", "--agent-restore", "claude_code"])

    assert osdocs_mcp.main() == 0


def test_agent_restore_failure_returns_one(monkeypatch):
    monkeypatch.setattr(osdocs_mcp, "restore_agent", lambda key: False)
    monkeypatch.setattr(sys, "argv", ["osdocs-mcp", "--agent-restore", "claude_code"])

    assert osdocs_mcp.main() == 1
