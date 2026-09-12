# Version Management

Single source of truth for all version information in the project.

## Version Source

File: `pyproject.toml`

```toml
[project]
version = "1.0.0"
```

## Automatic Synchronization

The build process automatically syncs the version to all places where it's used:

### Build Command

```bash
installer\build.cmd all
```

This runs `installer/sync-version.py` which:

1. Extracts version from `pyproject.toml`
2. Updates `installer/outsystems-docs.iss`:
   - `#define VERSION`
   - `AppVersion`
   - `VersionInfoVersion`

### Manual Sync

```bash
python installer/sync-version.py
```

## Version Display

### CLI

```bash
osdocs-mcp --version
# Output: osdocs-mcp 1.0.0

osdocs-mcp --help
# Output header: OutSystems-Docs MCP v1.0.0
```

### Installer

- Control Panel shows: `OutSystems-Docs MCP 1.0.0`
- File properties show version: `1.0.0.0`

### GitHub Releases

Version comes from git tag (e.g., `v1.0.0`), which should match `pyproject.toml`.

## Release Workflow

1. Update version in `pyproject.toml`
2. Run `installer\build.cmd all` (version auto-syncs to installer)
3. Commit changes
4. Tag release: `git tag v1.0.0`
5. Push tag: `git push origin v1.0.0`
6. GitHub Actions automatically builds and releases

## Version Mismatch Detection

All versions should be consistent:

| Location               | Command                                                | Expected |
| ---------------------- | ------------------------------------------------------ | -------- |
| Python package         | `scripts\run.cmd --version`                            | 1.0.0    |
| Help text              | `scripts\run.cmd --help`                               | v1.0.0   |
| Installer (AppVersion) | Check installer                                        | 1.0.0    |
| Git tag                | `git describe --tags`                                  | v1.0.0   |
| GitHub Release         | https://github.com/OutSystems/outsystems-docs/releases | v1.0.0   |

If any mismatch occurs, run `installer\build.cmd all` to resync.

## Implementation Details

- Package version: Read from `importlib.metadata.version()` at runtime
- Installer version: Hardcoded during build (synced from pyproject.toml)
- GitHub release version: Manual tag (should match pyproject.toml)

No manual version updates needed anywhere except `pyproject.toml`.
