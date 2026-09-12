#!/usr/bin/env python3
"""Sync version number across build files and installer script."""

import re
import sys
from pathlib import Path

def get_version_from_pyproject():
    """Extract version from pyproject.toml."""
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject) as f:
        content = f.read()
        match = re.search(r'version\s*=\s*"([^"]+)"', content)
        if match:
            return match.group(1)
    raise ValueError("Could not find version in pyproject.toml")

def update_installer_version(version):
    """Update version in Inno Setup script."""
    installer_script = Path(__file__).parent / "outsystems-docs.iss"
    with open(installer_script) as f:
        content = f.read()

    # Update #define VERSION
    content = re.sub(
        r'#define VERSION "[^"]+"',
        f'#define VERSION "{version}"',
        content
    )

    # Update AppVersion
    content = re.sub(
        r'AppVersion=[\d.]+',
        f'AppVersion={version}',
        content
    )

    # Update VersionInfoVersion (must be in format X.Y.Z.0)
    content = re.sub(
        r'VersionInfoVersion=[\d.]+',
        f'VersionInfoVersion={version}.0',
        content
    )

    with open(installer_script, 'w') as f:
        f.write(content)

    print(f"Updated installer version to {version}")

def update_build_version(version):
    """Update version in build.cmd (for future use)."""
    build_script = Path(__file__).parent / "build.cmd"
    if not build_script.exists():
        return

    with open(build_script) as f:
        content = f.read()

    # Update REM VERSION if present
    content = re.sub(
        r'REM VERSION: [\d.]+',
        f'REM VERSION: {version}',
        content
    )

    with open(build_script, 'w') as f:
        f.write(content)

def main():
    """Sync versions across all files."""
    version = get_version_from_pyproject()
    print(f"Syncing version: {version}")

    update_installer_version(version)
    update_build_version(version)

    print("Version sync complete")

if __name__ == "__main__":
    main()
