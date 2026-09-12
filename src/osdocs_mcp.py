#!/usr/bin/env python3
"""OutSystems-Docs MCP - Consolidated entry point."""

import sys
from importlib.metadata import version, PackageNotFoundError
from osdocs.config import load_app_config
from osdocs.logging_util import get_logger
from osdocs.sync import main as sync_main
from osdocs.config import (
    _AGENTS,
    add_agent,
    agent_status,
    backup_agent,
    get_agent,
    list_agents,
    remove_agent,
    remove_all_agents,
    restore_agent,
)

# Initialize config and logging
load_app_config()
logger = get_logger(__name__)

# Set HF_TOKEN from config if available
import os
from osdocs.config import get_app_config
hf_token = get_app_config().get("secrets.hf_token", "")
if hf_token:
    os.environ["HF_TOKEN"] = hf_token
    logger.debug(f"HF_TOKEN set from config (length: {len(hf_token)})")


def get_version():
    """Get package version from metadata."""
    try:
        return version("outsystems-docs")
    except PackageNotFoundError:
        return "unknown"


def print_help():
    """Print help message."""
    print(f"""
OutSystems-Docs MCP v{get_version()}

Usage:
  osdocs-mcp                        Run MCP server (stdio mode)
  osdocs-mcp --sync                 Sync documents
  osdocs-mcp --agent-status         Display agent configuration status
  osdocs-mcp --agent-add AGENT      Configure specific agent
  osdocs-mcp --agent-remove AGENT   Remove from specific agent
  osdocs-mcp --agent-remove-all     Remove from all agents
  osdocs-mcp --agent-backup AGENT   Backup agent configuration
  osdocs-mcp --agent-restore AGENT  Restore agent configuration
  osdocs-mcp --agent-interactive    Interactive agent configuration menu
  osdocs-mcp --version              Show version
  osdocs-mcp --help                 Show this help message

Supported Agents:
""")
    for idx, key, display_name in list_agents():
        print(f"  {idx:2d}. {display_name:25s} ({key})")

    print("""
Examples:
  osdocs-mcp                      # Start MCP server
  osdocs-mcp --sync               # Sync documents
  osdocs-mcp --agent-add claude_code
  osdocs-mcp --agent-status
  osdocs-mcp --agent-interactive
""")


def print_status():
    """Print agent status."""
    print("\nAgent Configuration Status:\n")
    for idx, key, display_name in list_agents():
        status = "OK" if agent_status(key) else "--"
        agent = get_agent(key)
        config_path = agent["config_path"] if agent else "unknown"
        print(f"  {idx:2d}. [{status}] {display_name:25s} - {config_path}")
    print()


def interactive_menu():
    """Interactive configuration menu."""
    print("\nAgent Configuration Menu")
    print("=" * 50)

    while True:
        print_status()
        print("Options:")
        print("  'add N' or 'add all'      - Configure agent(s)")
        print("  'remove N' or 'remove all'- Remove from agent(s)")
        print("  'backup N' or 'backup all'- Backup agent config(s)")
        print("  'restore N' or 'restore all'- Restore agent config(s)")
        print("  'status'                  - Show status")
        print("  'quit'                    - Exit\n")

        command = input("Enter command: ").strip().lower()

        if command == "quit":
            break

        if command == "status":
            continue

        parts = command.split()
        if len(parts) != 2:
            print("Invalid command. Use 'add 1', 'add all', etc.")
            continue

        action, target = parts
        agents_to_process = []

        if target == "all":
            agents_to_process = [key for key, _ in _AGENTS.items()]
        else:
            try:
                idx = int(target) - 1
                agents_list = list_agents()
                if 0 <= idx < len(agents_list):
                    agents_to_process = [agents_list[idx][1]]
                else:
                    print(f"Invalid agent number: {target}")
                    continue
            except ValueError:
                print(f"Invalid agent number: {target}")
                continue

        if action == "add":
            for agent_key in agents_to_process:
                add_agent(agent_key)
        elif action == "remove":
            for agent_key in agents_to_process:
                remove_agent(agent_key)
        elif action == "backup":
            for agent_key in agents_to_process:
                backup_agent(agent_key)
        elif action == "restore":
            for agent_key in agents_to_process:
                restore_agent(agent_key)
        else:
            print(f"Unknown action: {action}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        # Default: run MCP server in stdio mode (import here so it isn't constructed
        # for every other command, e.g. --sync, --agent-status)
        from osdocs.server import main as server_main
        return server_main()

    command = sys.argv[1].lower()

    if command == "--version":
        print(f"osdocs-mcp {get_version()}")
        return 0

    if command == "--help":
        print_help()
        return 0

    if command == "--sync":
        # Pass remaining args to sync_main (skip program name and --sync flag)
        sync_main(argv=sys.argv[2:])
        return 0

    if command == "--agent-status":
        print_status()
        return 0

    if command == "--agent-interactive":
        interactive_menu()
        return 0

    if command == "--agent-add" and len(sys.argv) > 2:
        agent_key = sys.argv[2]
        return 0 if add_agent(agent_key) else 1

    if command == "--agent-remove" and len(sys.argv) > 2:
        agent_key = sys.argv[2]
        return 0 if remove_agent(agent_key) else 1

    if command == "--agent-remove-all":
        from osdocs.config import remove_all_agents
        return 0 if remove_all_agents() else 1

    if command == "--agent-backup" and len(sys.argv) > 2:
        agent_key = sys.argv[2]
        return 0 if backup_agent(agent_key) else 1

    if command == "--agent-restore" and len(sys.argv) > 2:
        agent_key = sys.argv[2]
        return 0 if restore_agent(agent_key) else 1

    print(f"Unknown command: {command}")
    print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
