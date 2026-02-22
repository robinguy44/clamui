# Scan Progress Widget
"""
Progress display widget for scan operations.

Single responsibility:
- Display progress bar with pulse animation
- Show live file being scanned
- Display stats (files scanned, threats found)
"""

import time
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk, Pango

from ...core.i18n import _
from ...core.scanner import ScanProgress


class ScanProgressWidget(Gtk.Box):
    """
    Widget showing scan progress with bar and stats.
    """

    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6, **kwargs)
        self.add_css_class("progress-section")
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_visible(False)

        self._pulse_id = None
        self._paused = False

        self._build_ui()

    def _build_ui(self):
        self._bar = Gtk.ProgressBar()
        self._bar.add_css_class("progress-bar-compact")
        self.append(self._bar)

        self._status_label = Gtk.Label()
        self._status_label.set_label(_("Scanning..."))
        self._status_label.add_css_class("progress-status")
        self._status_label.add_css_class("dim-label")
        self._status_label.set_xalign(0)
        self.append(self._status_label)

        self._file_label = Gtk.Label()
        self._file_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self._file_label.add_css_class("dim-label")
        self._file_label.add_css_class("caption")
        self._file_label.set_xalign(0)
        self._file_label.set_visible(False)
        self.append(self._file_label)

        stats_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        self._stats_label = Gtk.Label()
        self._stats_label.add_css_class("caption")
        self._stats_label.add_css_class("dim-label")
        self._stats_label.set_xalign(0)
        self._stats_label.set_hexpand(True)
        self._stats_label.set_visible(False)
        stats_box.append(self._stats_label)

        self._threat_label = Gtk.Label()
        self._threat_label.add_css_class("caption")
        self._threat_label.add_css_class("error")
        self._threat_label.set_xalign(1)
        self._threat_label.set_visible(False)
        stats_box.append(self._threat_label)

        self.append(stats_box)

    def start(self) -> None:
        """Show widget and start pulsing."""
        self.set_visible(True)
        self._start_pulse()

    def stop(self) -> None:
        """Hide widget and stop pulsing."""
        self._stop_pulse()
        self.set_visible(False)
        self._file_label.set_visible(False)
        self._stats_label.set_visible(False)
        self._threat_label.set_visible(False)
        self._threat_label.remove_css_class("error")

    def update(
        self,
        progress: ScanProgress,
        cumulative_files: int = 0,
        multi_target: bool = False,
        current_target: int = 1,
        total_targets: int = 1,
    ) -> None:
        """Update progress display."""
        if self._paused:
            return

        if progress.percentage is not None:
            self._stop_pulse()
            self._bar.set_fraction(progress.percentage / 100)

            pct = int(progress.percentage)
            if multi_target:
                self._status_label.set_text(
                    _("Target {current} of {total} — {pct}%").format(
                        current=current_target, total=total_targets, pct=pct
                    )
                )
            else:
                self._status_label.set_text(_("Scanning... {pct}%").format(pct=pct))

        if progress.current_file:
            self._file_label.set_text(self._truncate_path(progress.current_file))
            self._file_label.set_visible(True)

        total = cumulative_files + progress.files_scanned
        if progress.files_total:
            self._stats_label.set_text(
                _("Scanned {scanned:,} / {total:,} files").format(
                    scanned=progress.files_scanned, total=progress.files_total
                )
            )
        else:
            self._stats_label.set_text(_("Scanned {count:,} files").format(count=total))
        self._stats_label.set_visible(True)

        if progress.infected_count > 0:
            self._threat_label.set_text(_("Found {n} threat(s)").format(n=progress.infected_count))
            self._threat_label.add_css_class("error")
            self._threat_label.set_visible(True)

    def set_status(self, text: str) -> None:
        """Set status label text."""
        self._status_label.set_text(text)

    def _start_pulse(self):
        if self._pulse_id:
            return
        self._pulse_id = GLib.timeout_add(100, self._do_pulse)

    def _stop_pulse(self):
        if self._pulse_id:
            GLib.source_remove(self._pulse_id)
            self._pulse_id = None

    def _do_pulse(self) -> bool:
        self._bar.pulse()
        return True

    def _truncate_path(self, path: str, max_len: int = 60) -> str:
        if len(path) <= max_len:
            return path
        p = Path(path)
        if p.parent.name:
            return f".../{p.parent.name}/{p.name}"
        return "..." + path[-(max_len - 3) :]

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False
