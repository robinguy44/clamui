# ClamUI Privileged Preferences Apply Helper
"""
Helper command for applying configuration files with elevated privileges.

This CLI is intended to be invoked via pkexec by the GUI layer. It copies
staged config files to their destination paths and normalizes permissions.
"""

import os
import shutil
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
        for source, destination in pairs:
            _apply_config_file(source, destination)
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
