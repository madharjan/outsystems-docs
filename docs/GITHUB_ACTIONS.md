# GitHub Actions Configuration

Windows installer CI/CD pipeline via GitHub Actions.

## Workflow

File: `.github/workflows/windows-installer.yml`

Trigger: Git tags matching `v*` (e.g., `v1.0.0`)

Runtime: `windows-latest`, matrix build (`standard`, `directml`)

Output: two installers uploaded to GitHub Releases:
- `OutSystems-Docs-Setup.exe` - CPU-only (standard)
- `OutSystems-Docs-Setup-DirectML.exe` - AMD/Intel/NVIDIA GPU acceleration via DirectML (built with `--directml`, see [Installer](INSTALLER.md))

## Pipeline

1. Checkout + Python 3.10 setup
2. Dependencies: `uv sync`
3. Build tools: MSVC, Nuitka, Inno Setup (via Chocolatey)
4. Compilation: `installer\build.cmd all` (standard leg) / `installer\build.cmd all --directml` (directml leg)
5. Installer build (`iscc`), DirectML leg's exe renamed to `OutSystems-Docs-Setup-DirectML.exe`
6. Each leg uploads its installer as a build artifact
7. A final `release` job downloads both artifacts and attaches them to the GitHub Release

See `.github/workflows/windows-installer.yml` for full configuration.
