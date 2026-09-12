# Windows Installer Guide

Build a standalone Windows installer for OutSystems-Docs MCP using Nuitka and Inno Setup.

## Prerequisites

- Windows 10/11
- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- [Nuitka](https://www.nuitka.net/) (installed via `uv sync`)
- [Inno Setup](https://jrsoftware.org/isdl.php) 6.0+
- Microsoft C++ Build Tools (MSVC)

## Setup

### 1. Install Dependencies

```bash
uv sync
```

### 2. Install Inno Setup

Any of these work — `build.cmd` resolves `iscc` from PATH first, then falls back to the
winget/choco default install locations, so no manual PATH setup is needed either way:

```bash
winget install --id JRSoftware.InnoSetup -e -s winget -i
choco install innosetup -y
```

Or download and install from [jrsoftware.org](https://jrsoftware.org/isdl.php).

### 3. Install MSVC Build Tools

Required for Nuitka compilation. Download from [Visual Studio](https://visualstudio.microsoft.com/visual-cpp-build-tools/).

## Building

### Build the Executable

```bash
installer\build.cmd all
```

`build.cmd all --directml` swaps the venv's `onnxruntime` for `onnxruntime-directml` before compiling, so the packaged exe gets GPU-accelerated embedding via DirectML (works on AMD, Intel and NVIDIA GPUs on Windows) instead of the plain CPU-only `onnxruntime` wheel fastembed pulls in by default. Without `--directml`, `build.cmd all` builds the plain CPU-only exe. This is a build-only step: it doesn't touch `pyproject.toml`/`uv.lock`. Both packages share the same top-level `onnxruntime` package directory, so swapping between them can leave stale `onnxruntime-*.dist-info` metadata behind with the actual files gone — a plain `uv sync` trusts that metadata and won't notice, so `build.cmd` always runs `uv sync --reinstall-package onnxruntime` first to guarantee a working `onnxruntime` regardless of what a previous build left behind. When built with `--directml`, keep `DmlExecutionProvider` in `installer/config.yaml`'s `embeddings.providers` list.

This creates:

- `dist/osdocs-mcp.exe` - Unified CLI for all operations (MCP server, agent configuration, documentation sync)

The unified executable handles:
- MCP server mode (default, stdio)
- Agent configuration (`--agent-add`, `--agent-remove`, `--agent-interactive`)
- Documentation synchronization (`--sync`)

## Building the Installer

### Prerequisites
Ensure Inno Setup is installed and accessible:

```bash
where iscc
```

If not found, add to PATH or update the build script.

### Build the Installer

```cmd
cd installer
iscc outsystems-docs.iss
```

Output: `dist/OutSystems-Docs-Setup.exe`

### Automated Builds (GitHub Actions)

The project uses GitHub Actions to automatically build and release the installer on git tags matching `v*`. See [GitHub Actions Configuration](GITHUB_ACTIONS.md) for setup details.

## Installer Features

- Single-file installation to `%ProgramFiles%\OutSystems-Docs\`
- Start menu shortcuts:
  - Configure Agents - Interactive agent configuration menu
  - Sync Documentation - Synchronize documentation index
  - Documentation - Open the README file
- Automatic agent configuration backup before setup
- Detailed installer logs at `%InstallDir%\logs\osdocs-mcp-installer.log`
- Support for uninstallation with configuration cleanup

## Customization

Edit `installer/outsystems-docs.iss` to customize:

- `AppVersion` - Version number
- `OutputBaseFilename` - Installer filename
- `DefaultDirName` - Installation directory
- `DefaultGroupName` - Start menu folder name

## Troubleshooting

"Nuitka not found":
```bash
uv pip install nuitka
```

"MSVC not found":
Install Visual Studio Build Tools with C++ workload.

"Inno Setup not found":
Install from [jrsoftware.org](https://jrsoftware.org/isdl.php) and add to PATH.

Compilation fails:
- Ensure all dependencies are installed: `uv sync`
- Check Python version: `python --version` (should be 3.10+)
- Try clean build: `installer\clean.cmd && installer\build.cmd all`

Installer creation fails:
- Verify `dist/OutSystems-Docs/` exists with all executables
- Check Inno Setup path in script
- Review `dist/OutSystems-Docs-Setup.iss` for errors

`ModuleNotFoundError: No module named 'onnxruntime'` when running the packaged exe:
Nuitka's `--follow-imports` didn't bundle `onnxruntime`'s code — it has a nontrivial
`__init__.py` (conditional native-backend loading) that trips up Nuitka's static import
analysis. `build.cmd` passes `--include-package=onnxruntime` explicitly to force it in; if
you're hitting this, make sure you're on a build with that flag (`installer\clean.cmd &&
installer\build.cmd all`).

## Distribution

The `.exe` installer can be distributed directly. It includes:
- All compiled executables
- Required Python runtime
- Dependencies (numpy, fastembed, etc.)
- README and license files

End users simply run the installer and follow the setup wizard.
