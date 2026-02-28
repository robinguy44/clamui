# ClamUI CLI Output Utilities
"""
Shared output formatting for ClamUI CLI commands.

Provides consistent text and JSON formatting for all CLI subcommands.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


def print_json(data: object) -> None:
    """
    Print data as formatted JSON to stdout.

    Args:
        data: Any JSON-serializable object.
    """
    print(json.dumps(data, indent=2, default=str))


def print_error(message: str) -> None:
    """
    Print error message to stderr.

    Args:
        message: Error description.
    """
    print(f"error: {message}", file=sys.stderr)


def print_warning(message: str) -> None:
    """
    Print warning message to stderr.

    Args:
        message: Warning description.
    """
    print(f"warning: {message}", file=sys.stderr)


def print_info(message: str) -> None:
    """
    Print informational message to stderr (for verbose output).

    Args:
        message: Info text.
    """
    print(message, file=sys.stderr)


def format_size(size_bytes: int) -> str:
    """
    Format byte count as human-readable size string.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Formatted string (e.g. "1.2 MB").
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def format_timestamp(iso_str: str | None) -> str:
    """
    Format ISO 8601 timestamp for terminal display.

    Args:
        iso_str: ISO format timestamp string, or None.

    Returns:
        Formatted date string or "N/A".
    """
    if not iso_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return iso_str


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    """
    Print a formatted table to stdout.

    Automatically sizes columns based on content width.

    Args:
        headers: Column header labels.
        rows: List of row data (each row is a list of cell strings).
    """
    if not rows:
        return

    # Calculate column widths from headers and data
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))

    # Print header row
    header_line = "  ".join(h.ljust(w) for h, w in zip(headers, widths, strict=False))
    print(header_line)
    print("─" * len(header_line))

    # Print data rows
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            if i < len(widths):
                cells.append(str(cell).ljust(widths[i]))
            else:
                cells.append(str(cell))
        print("  ".join(cells))


def get_config_dir() -> Path:
    """
    Return the ClamUI XDG config directory.

    Uses $XDG_CONFIG_HOME/clamui, defaulting to ~/.config/clamui.

    Returns:
        Path to the config directory.
    """
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME", "~/.config")
    return Path(xdg_config_home).expanduser() / "clamui"
