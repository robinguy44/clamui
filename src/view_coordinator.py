# ClamUI View Coordinator
"""
View coordination for ClamUI.

This module handles view switching, navigation, and view management
for the main application window.
"""

import logging

logger = logging.getLogger(__name__)


class ViewCoordinator:
    """Coordinates view switching and navigation in the main window."""

    def __init__(self, app, logger=None):
        """Initialize the view coordinator."""
        self._app = app

    def setup_actions(self):
        """Set up application-level actions for view switching."""
        actions = [
            ("quit", "app.quit", ["<Control>q"], self._app._on_quit),
            ("about", "app.about", [], self._app._on_about),
            ("preferences", "app.preferences", ["<Control>comma"], self._app._on_preferences),
            ("show-scan", "app.show-scan", ["<Control>1"], self._app._on_show_scan),
            ("show-update", "app.show-update", ["<Control>2"], self._app._on_show_update),
            ("show-logs", "app.show-logs", ["<Control>3"], self._app._on_show_logs),
            (
                "show-components",
                "app.show-components",
                ["<Control>4"],
                self._app._on_show_components,
            ),
            (
                "show-quarantine",
                "app.show-quarantine",
                ["<Control>5"],
                self._app._on_show_quarantine,
            ),
            (
                "show-statistics",
                "app.show-statistics",
                ["<Control>6"],
                self._app._on_show_statistics,
            ),
            (
                "show-audit",
                "app.show-audit",
                ["<Control>7"],
                self._app._on_show_audit,
            ),
            ("start-scan", "app.start-scan", ["<Control>s"], self._app._on_start_scan),
            ("start-update", "app.start-update", ["<Control>u"], self._app._on_start_update),
            ("scan-file", "app.scan-file", [], self._app._on_scan_file),
            ("scan-system", "app.scan-system", [], self._app._on_scan_system),
        ]

        for name, action_name, accels, callback in actions:
            action = self._create_action(name, callback)
            self._app.add_action(action)
            if accels:
                self._app.set_accels_for_action(action_name, accels)

    def _create_action(self, name, callback):
        """Create a simple action with the given callback."""
        from gi.repository import Gio

        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        return action

    def switch_to_view(self, view_name, view_widget):
        """Switch the active view to the specified view."""
        win = self._app.props.active_window
        if win is None:
            logger.warning("Cannot switch view: no active window")
            return

        win.set_content_view(view_widget)
        win.set_active_view(view_name)
        self._app._current_view = view_name

    def get_current_view(self):
        """Get the name of the currently active view."""
        return self._app._current_view

    def trigger_statistics_quick_scan(self):
        """Trigger a quick scan from the statistics view."""
        win = self._app.props.active_window
        if win is None:
            return

        quick_scan_profile = self._app._get_quick_scan_profile()

        if quick_scan_profile:
            self._app.scan_view.refresh_profiles()
            self._app.scan_view.set_selected_profile(quick_scan_profile.id)
            self.switch_to_view("scan", self._app.scan_view)
        else:
            import os

            home_dir = os.path.expanduser("~")
            self._app.scan_view._set_selected_path(home_dir)
            self.switch_to_view("scan", self._app.scan_view)
            logger.warning("Quick Scan profile not found, falling back to home directory")
