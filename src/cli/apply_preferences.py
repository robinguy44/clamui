# ClamUI Privileged Preferences Apply Helper
"""
Helper command for applying configuration files with elevated privileges.

This CLI is intended to be invoked via pkexec by the GUI layer. It copies
staged config files to their destination paths and normalizes permissions.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def _parse_path_pairs(args: list[str]) -> list[tuple[Path, Path]]:
    """
    Parse command arguments into (source, destination) path pairs.

    Args:
        args: Flat list of alternating source and destination paths

    Returns:
        List of (source, destination) Path tuples

    Raises:
        ValueError: If args are empty or not provided as pairs
    """
    if not args:
        raise ValueError("No staged configuration files were provided.")
    if len(args) % 2 != 0:
        raise ValueError("Invalid arguments: expected source/destination path pairs.")

    pairs = []
    for idx in range(0, len(args), 2):
        pairs.append((Path(args[idx]), Path(args[idx + 1])))
    return pairs


_ALLOWED_DEST_DIRS: tuple[Path, ...] = (
    Path("/etc/clamav"),
    Path("/etc/clamd.d"),
    Path("/etc/clamav-unofficial-sigs"),
)

_FRESHCLAM_UNITS: tuple[str, ...] = (
    "clamav-freshclam.service",
    "freshclam.service",
)

_CLAMD_UNITS: tuple[str, ...] = (
    "clamav-daemon.service",
    "clamd.service",
    "clamd@scan.service",
    "clamav-clamonacc.service",
)


def _validate_destination(destination: Path) -> None:
    """
    Validate that a destination path is within the ClamAV config allowlist.

    The resolved path must:
    - Have a parent directory that exactly matches one of the allowed directories
    - End with a ``.conf`` extension

    Args:
        destination: Proposed destination file path

    Raises:
        ValueError: If the destination is outside the allowlist or has a
            disallowed extension
    """
    resolved = destination.resolve()

    if resolved.suffix != ".conf":
        raise ValueError(f"Destination must have a .conf extension: {resolved}")

    if resolved.parent not in _ALLOWED_DEST_DIRS:
        raise ValueError(f"Destination is not in allowed config directories: {resolved}")


def _apply_config_file(source: Path, destination: Path) -> None:
    """
    Copy one staged config file to destination and set expected permissions.

    Args:
        source: Staged temporary file path
        destination: Final config file destination path
    """
    if not source.exists():
        raise FileNotFoundError(f"Staged file not found: {source}")
    if not source.is_file():
        raise OSError(f"Staged path is not a file: {source}")

    _validate_destination(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    os.chmod(destination, 0o644)


def _restart_units_for_destinations(destinations: list[Path]) -> None:
    """
    Restart active ClamAV services affected by the written config files.

    Only active services are restarted so distro-specific or disabled units
    are skipped without failing the save operation.

    Args:
        destinations: Final config destinations that were updated
    """
    if shutil.which("systemctl") is None:
        return

    units_to_restart: list[str] = []
    for destination in destinations:
        if destination.name == "freshclam.conf":
            units_to_restart.extend(_FRESHCLAM_UNITS)
        elif destination.name == "clamd.conf" or destination.parent == Path("/etc/clamd.d"):
            units_to_restart.extend(_CLAMD_UNITS)

    seen_units: set[str] = set()
    for unit in units_to_restart:
        if unit in seen_units:
            continue
        seen_units.add(unit)

        active_result = subprocess.run(
            ["systemctl", "is-active", "--quiet", unit],
            capture_output=True,
            text=True,
        )
        if active_result.returncode != 0:
            continue

        restart_result = subprocess.run(
            ["systemctl", "restart", unit],
            capture_output=True,
            text=True,
        )
        if restart_result.returncode != 0:
            error = restart_result.stderr.strip() or restart_result.stdout.strip() or "unknown error"
            raise RuntimeError(f"Failed to restart {unit}: {error}")


def main(argv: list[str] | None = None) -> int:
    """
    Entry point for privileged preferences apply helper.

    Args:
        argv: Optional argument list (defaults to sys.argv[1:])

    Returns:
        Exit status code (0 success, non-zero on failure)
    """
    args = list(sys.argv[1:] if argv is None else argv)

    try:
        pairs = _parse_path_pairs(args)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    try:
        destinations: list[Path] = []
        for source, destination in pairs:
            _apply_config_file(source, destination)
            destinations.append(destination)
        _restart_units_for_destinations(destinations)
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
