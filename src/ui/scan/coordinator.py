# Scan Coordinator
"""
Scan coordination for ClamUI.

This module handles scan-related callbacks and orchestration,
extracting scan logic from ClamUIApp to reduce complexity.

Key Responsibilities:
    - Tray scan callbacks (quick scan, full scan, profile selection)
    - VirusTotal scan handling
    - Scan state tracking for tray indicator
    - Scan state changes and notifications

Design Pattern:
    ScanCoordinator encapsulates all scan-related callbacks and state,
    separating concerns from the main application class.
"""

import logging
import os
from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, cast

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import GLib

if TYPE_CHECKING:
    from ...core.app_context import AppContext
    from ..coordinator import ViewCoordinator

logger = logging.getLogger(__name__)


class MainViewHost(Protocol):
    """Protocol for windows that can host main UI views."""

    def set_content_view(self, view) -> None: ...
    def set_active_view(self, view_name: str) -> None: ...


class ScanCoordinator:
    """
    Coordinates scan operations and callbacks.

    Manages tray scan callbacks, VirusTotal integration, and scan
    state tracking for the tray indicator.

    Attributes:
        is_scan_active: Whether a scan is currently running.
    """

    def __init__(
        self,
        app_context: "AppContext",
        view_coordinator: "ViewCoordinator",
    ):
        """
        Initialize the scan coordinator.

        Args:
            app_context: Application context with shared services.
            view_coordinator: View coordinator for navigation.
        """
        self._context = app_context
        self._views = view_coordinator

        self._scan_state_changed_callback: Callable | None = None

    @property
    def is_scan_active(self) -> bool:
        """Check if a scan is currently in progress."""
        return self._context.is_scan_active

    def set_scan_state_changed_callback(self, callback: Callable) -> None:
        """
        Set callback for scan state changes.

        Args:
            callback: Function(is_scanning: bool, result=None)
        """
        self._scan_state_changed_callback = callback

    def connect_scan_view_callbacks(self) -> None:
        """Connect scan view to scan state callback."""
        scan_view = self._views.scan_view
        if hasattr(scan_view, "set_scan_state_changed_callback"):
            scan_view.set_scan_state_changed_callback(self._on_scan_state_changed)

    def _on_scan_state_changed(self, is_scanning: bool, result=None) -> None:
        """
        Handle scan state changes for tray indicator updates.

        Args:
            is_scanning: True when scan starts, False when scan ends.
            result: ScanResult when scan completes.
        """
        self._context.is_scan_active = is_scanning

        if self._scan_state_changed_callback:
            self._scan_state_changed_callback(is_scanning, result)

        tray = self._context.tray_indicator
        if tray is None:
            return

        if is_scanning:
            tray.update_status("scanning")
            tray.update_scan_progress(0)
        else:
            tray.update_scan_progress(0)
            if result is not None:
                if result.has_threats:
                    tray.update_status("threat")
                elif result.is_clean:
                    tray.update_status("protected")
                else:
                    tray.update_status("warning")
            else:
                tray.update_status("protected")

    def get_quick_scan_profile(self):
        """
        Retrieve the Quick Scan profile by name.

        Returns:
            The Quick Scan profile if found, None otherwise.
        """
        return self._context.profile_manager.get_profile_by_name("Quick Scan")

    def start_quick_scan(self, window: MainViewHost) -> None:
        """
        Start a quick scan with the Quick Scan profile.

        Falls back to home directory if profile not found.

        Args:
            window: Main window for UI updates.
        """
        self._views.switch_to("scan", window)

        quick_profile = self.get_quick_scan_profile()
        scan_view = self._views.scan_view

        if quick_profile:
            scan_view.refresh_profiles()
            scan_view.set_selected_profile(quick_profile.id)
            scan_view._start_scan()
            logger.info("Quick scan started with Quick Scan profile")
        else:
            home_dir = os.path.expanduser("~")
            scan_view._set_selected_path(home_dir)
            scan_view._start_scan()
            logger.warning("Quick Scan profile not found, using home directory")

    def configure_quick_scan(self, window: MainViewHost) -> None:
        """
        Configure a quick scan without starting it.

        Args:
            window: Main window for UI updates.
        """
        self._views.switch_to("scan", window)

        quick_profile = self.get_quick_scan_profile()
        scan_view = self._views.scan_view

        if quick_profile:
            scan_view.refresh_profiles()
            scan_view.set_selected_profile(quick_profile.id)
        else:
            home_dir = os.path.expanduser("~")
            scan_view._set_selected_path(home_dir)

    def start_system_scan(self, window: MainViewHost) -> None:
        """
        Start system scan from header bar.

        Args:
            window: Main window for UI updates.
        """
        self.start_quick_scan(window)
        logger.info("System scan started from header bar")

    def open_file_picker(self, window: MainViewHost) -> None:
        """
        Open file picker for scan target selection.

        Args:
            window: Main window for UI updates.
        """
        self._views.switch_to("scan", window)
        self._views.scan_view.show_file_picker()

    def _get_view_host(self) -> MainViewHost | None:
        """Get active window as MainViewHost."""
        from gi.repository import Gio

        app = Gio.Application.get_default()
        if app:
            win = app.props.active_window
            if win:
                return cast(MainViewHost, win)
        return None

    def handle_tray_quick_scan(self) -> None:
        """Handle Quick Scan action from tray menu."""
        GLib.idle_add(self._do_tray_quick_scan)

    def _do_tray_quick_scan(self) -> bool:
        """Execute quick scan on main thread."""
        from gi.repository import Gio

        app = Gio.Application.get_default()
        if app:
            app.activate()
            win = self._get_view_host()
            if win:
                self.start_quick_scan(win)
        return False

    def handle_tray_full_scan(self) -> None:
        """Handle Full Scan action from tray menu."""
        GLib.idle_add(self._do_tray_full_scan)

    def _do_tray_full_scan(self) -> bool:
        """Execute full scan setup on main thread."""
        from gi.repository import Gio

        app = Gio.Application.get_default()
        if app:
            app.activate()
            win = self._get_view_host()
            if win:
                self._views.switch_to("scan", win)
                self._views.scan_view._on_select_folder_clicked(None)
                logger.info("Full scan folder selection opened from tray")
        return False

    def handle_tray_profile_select(self, profile_id: str) -> None:
        """Handle profile selection from tray menu."""
        GLib.idle_add(self._do_tray_profile_select, profile_id)

    def _do_tray_profile_select(self, profile_id: str) -> bool:
        """Execute profile selection on main thread."""
        from gi.repository import Gio

        app = Gio.Application.get_default()
        if app:
            app.activate()
            win = self._get_view_host()
            if win:
                self._views.switch_to("scan", win)
                scan_view = self._views.scan_view
                scan_view.refresh_profiles()
                if scan_view.set_selected_profile(profile_id):
                    logger.info("Profile selected from tray: %s", profile_id)
                else:
                    logger.warning("Failed to select profile from tray: %s", profile_id)
        return False

    def sync_profiles_to_tray(self) -> None:
        """Sync profile list to tray menu."""
        tray = self._context.tray_indicator
        if tray is None:
            return

        profiles = self._context.profile_manager.list_profiles()
        profile_data = [{"id": p.id, "name": p.name, "is_default": p.is_default} for p in profiles]

        current_id = None
        if self._views._scan_view is not None:
            selected = self._views.scan_view.get_selected_profile()
            if selected:
                current_id = selected.id

        tray.update_profiles(profile_data, current_id)

    def handle_virustotal_scan(self, file_path: str, settings_manager) -> None:
        """
        Handle a VirusTotal scan request.

        Args:
            file_path: Path to file to scan.
            settings_manager: Settings manager for API key lookup.
        """
        from ...core import keyring_manager

        api_key = keyring_manager.get_api_key(settings_manager)

        if api_key:
            self._trigger_virustotal_scan(file_path, api_key, settings_manager)
        else:
            action = settings_manager.get("virustotal_remember_no_key_action", "none")
            if action == "open_website":
                self._open_virustotal_website()
            elif action == "prompt":
                self._context.notification_manager.notify_virustotal_no_key()
            else:
                self._show_virustotal_setup_dialog(file_path, settings_manager)

    def _trigger_virustotal_scan(
        self,
        file_path: str,
        api_key: str,
        settings_manager,
    ) -> None:
        """Start a VirusTotal scan for a file."""
        from ...core.log_manager import LogEntry, LogManager

        vt_client = self._context.get_or_create_vt_client(api_key)

        logger.info("Starting VirusTotal scan for: %s", file_path)

        def on_scan_complete(result):
            logger.info(
                "VirusTotal scan complete: status=%s, detections=%d/%d",
                result.status.value,
                result.detections,
                result.total_engines,
            )

            try:
                log_manager = LogManager()
                log_entry = LogEntry.from_virustotal_result_data(
                    vt_status=result.status.value,
                    file_path=result.file_path,
                    duration=result.duration,
                    sha256=result.sha256,
                    detections=result.detections,
                    total_engines=result.total_engines,
                    detection_details=[
                        {
                            "engine_name": d.engine_name,
                            "category": d.category,
                            "result": d.result,
                        }
                        for d in result.detection_details
                    ],
                    permalink=result.permalink,
                    error_message=result.error_message,
                )
                log_manager.save_log(log_entry)
            except Exception as e:
                logger.error("Failed to save VirusTotal log: %s", e)

            GLib.idle_add(self._show_virustotal_results_dialog, result)

            if not result.is_error:
                self._context.notification_manager.notify_virustotal_scan_complete(
                    is_clean=result.is_clean,
                    detections=result.detections,
                    total_engines=result.total_engines,
                    permalink=result.permalink,
                )
            elif result.status.value == "rate_limited":
                self._context.notification_manager.notify_virustotal_rate_limit()

        vt_client.scan_file_async(file_path, on_scan_complete)

    def _show_virustotal_setup_dialog(
        self,
        file_path: str,
        settings_manager,
    ) -> None:
        """Show the VirusTotal setup dialog."""
        from gi.repository import Gio

        from ..virustotal_setup_dialog import VirusTotalSetupDialog

        app = Gio.Application.get_default()
        win = app.props.active_window if app else None

        if not win:
            if app:
                app.activate()
                win = app.props.active_window

        if win:
            dialog = VirusTotalSetupDialog(
                settings_manager=settings_manager,
                on_key_saved=lambda key: self._trigger_virustotal_scan(
                    file_path, key, settings_manager
                ),
            )
            dialog.set_transient_for(win)
            dialog.present()

    def _show_virustotal_results_dialog(self, result) -> None:
        """Show the VirusTotal results dialog."""
        from gi.repository import Gio

        from ..virustotal_results_dialog import VirusTotalResultsDialog

        app = Gio.Application.get_default()
        win = app.props.active_window if app else None

        if not win:
            if app:
                app.activate()
                win = app.props.active_window

        if win:
            dialog = VirusTotalResultsDialog(vt_result=result)
            dialog.set_transient_for(win)
            dialog.present()

    def _open_virustotal_website(self) -> None:
        """Open the VirusTotal website for manual file upload."""
        from gi.repository import Gio

        url = "https://www.virustotal.com/gui/home/upload"
        try:
            Gio.AppInfo.launch_default_for_uri(url, None)
            logger.info("Opened VirusTotal website")
        except Exception as e:
            logger.error("Failed to open VirusTotal website: %s", e)
