# AGENTS.md — ClamUI Project Knowledge Base

**Commit:** 8ae29a6 | **Branch:** master

## Overview

GTK4/libadwaita ClamAV GUI for Linux. Python 3.10+, PyGObject, Adwaita. Packages as Flatpak, Debian, AppImage.

Full architecture reference: [`CLAUDE.md`](./CLAUDE.md) (1000+ lines).

## Structure

```
src/
├── main.py              # Entry point — CLI args, GTK init, i18n setup
├── app.py               # Adw.Application — lifecycle, views, tray (1478 lines)
├── core/                # Business logic (28 modules) → see core/AGENTS.md
│   ├── scanner.py       # Scan orchestration (auto/daemon/clamscan backends)
│   ├── quarantine/      # SQLite quarantine subsystem → see quarantine/AGENTS.md
│   ├── sanitize.py      # Input sanitization (ANSI, bidi, control chars)
│   ├── path_validation.py # Path + symlink safety
│   ├── flatpak.py       # Flatpak detection, host command wrapping
│   └── i18n.py          # Gettext setup
├── ui/                  # GTK4/Adwaita widgets (29 modules) → see ui/AGENTS.md
│   ├── scan/            # Scan workflow (coordinator pattern) → see scan/AGENTS.md
│   ├── preferences/     # Modular settings (13 pages) → see preferences/AGENTS.md
│   ├── tray_manager.py  # Subprocess tray (GIO D-Bus/SNI)
│   └── view_helpers.py  # Shared UI utilities
├── profiles/            # ScanProfile dataclass + CRUD + JSON persistence
├── cli/                 # scheduled_scan.py — headless scan for cron/systemd
└── locale/              # Gettext translations (de/)
```

## Where to Look

| Task | Location | Notes |
|------|----------|-------|
| Add a view | `ui/` + `app.py` | Register in `_setup_actions()`, add nav button in `window.py` |
| Add core feature | `core/` | Dataclass results, enum statuses, sync+async methods |
| Add preference page | `ui/preferences/` | Static factory pattern, see `scanner_page.py` as template |
| Add scan profile | `profiles/` | Modify `ProfileManager.DEFAULT_PROFILES` |
| Modify packaging | `debian/`, `flathub/`, `appimage/` | Update ALL three when adding deps |
| Security review | `core/sanitize.py`, `core/path_validation.py` | Defense-in-depth required |
| Tray integration | `ui/tray_*.py` | Subprocess architecture, see `docs/architecture/tray-subprocess.md` |
| Translations | `po/`, `core/i18n.py` | Run `./scripts/update-pot.sh` after changes |
| Flatpak-specific | `core/flatpak.py` | `wrap_host_command()`, `is_flatpak()`, DB path helpers |

## Required Setup

```bash
uv sync --dev
./scripts/hooks/install-hooks.sh   # REQUIRED — blocks absolute src.* imports
```

## Commands

```bash
# Run
uv run clamui

# Test
pytest --cov=src --cov-report=term-missing

# Lint
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/

# Build
./debian/build-deb.sh              # Debian package
./appimage/build-appimage.sh       # AppImage (bundles Python+GTK4)
```

## Anti-Patterns (THIS PROJECT)

### Import Restriction (CRITICAL)
**NEVER** use `from src.` or `import src.` inside `src/`. Package installs as `clamui`, not `src`.
- Enforced by: pre-commit hook, CI lint, AppImage build script
- Use: `from ..core.module import X` (relative imports)

### libadwaita Version Ceiling (CRITICAL)
Target: **libadwaita 1.0+** (Ubuntu 22.04 baseline = 1.1.x)

| Forbidden (1.2+) | Use Instead (1.0+) |
|---|---|
| `Adw.Dialog`, `Adw.AlertDialog` (1.5+) | `Adw.Window` |
| `Adw.PasswordEntryRow` (1.2+) | `create_password_entry_row()` from `ui/preferences/base.py` |
| `Adw.SpinRow` (1.2+) | `create_spin_row()` — returns `(row, spin_button)` tuple |
| `Adw.EntryRow` (1.2+) | `create_entry_row()` from `ui/compat.py` |
| `Adw.SwitchRow` (1.4+) | `create_switch_row()` from `ui/compat.py` |
| `Adw.ToolbarView` (1.4+) | `create_toolbar_view()` from `ui/compat.py` |

### Thread Safety
- **NEVER** update UI from background threads — always `GLib.idle_add(callback)`
- **ALWAYS** use `threading.Lock()` for shared state in manager classes
- **ALWAYS** reset loading state in `finally` blocks (prevents stuck spinners)

### Security
- **ALWAYS** sanitize before logging: `sanitize_log_line()` / `sanitize_log_text()`
- **ALWAYS** validate paths: `validate_path()`, `check_symlink_safety()`
- **ALWAYS** quote shell args: `shlex.quote()` for user paths in subprocess commands
- **ALWAYS** restrict permissions: `chmod(0o600)` for files with sensitive data

### i18n
- **NEVER** `_(f"...")` — f-strings in gettext break extraction. Use `_("text {v}").format(v=val)`
- **NEVER** translate: logger messages, exception messages, CSS classes, settings keys
- **ALWAYS** `ngettext()` for count-dependent strings
- After changes: `./scripts/update-pot.sh`

### Icons
- **ONLY** standard Adwaita symbolic icons — no app-specific or KDE icons
- **ALWAYS** use `resolve_icon_name()` wrapper from `ui/utils.py` for fallback support

### Flatpak
- **ALWAYS** `wrap_host_command()` for commands executing on host
- **ALWAYS** check `is_flatpak()` when behavior differs
- Database paths differ — use `get_clamav_database_dir()`

## Conventions

- **Error returns**: `(success: bool, error_or_value: Optional[str])` tuples
- **Structured data**: `@dataclass` with `@property` for computed values
- **Type hints**: Required throughout
- **GI imports**: `gi.require_version()` BEFORE `from gi.repository import ...`
- **Ruff**: Line length 100, double quotes, 4-space indent, isort enabled
- **Coverage**: 50% minimum (enforced), 80%+ target for core, 70%+ for ui
- **Test structure**: mirrors source — `src/core/foo.py` → `tests/core/test_foo.py`
- **UI tests**: use `mock_gi_modules` fixture from `tests/conftest.py`

## Packaging Checklist

When adding a Python dependency:
1. Update `pyproject.toml`
2. Update `flathub/requirements-runtime.txt`
3. Update `debian/DEBIAN/control`
4. Regenerate `flathub/python3-runtime-deps.json` via `req2flatpak`
5. Test on Ubuntu 22.04 baseline

## Agent Workflows

### Bug Fix
1. Read code → check existing tests → write failing test → fix → run suite → check for similar issues

### New Feature
1. Check `CLAUDE.md` for patterns → review similar features → implement with thread safety → test → update docs

### Security Change
1. Review `sanitize.py` + `path_validation.py` → apply defense-in-depth → test with malicious inputs → verify permissions → check subprocess calls

## Hierarchy

```
./AGENTS.md                      ← you are here (project root)
├── src/core/AGENTS.md           ← business logic conventions
│   └── src/core/quarantine/AGENTS.md ← quarantine subsystem
└── src/ui/AGENTS.md             ← UI layer patterns
    ├── src/ui/preferences/AGENTS.md  ← preferences page recipe
    └── src/ui/scan/AGENTS.md         ← scan workflow coordination
```
