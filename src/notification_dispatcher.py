# ClamUI Notification Dispatcher
"""
Notification management for ClamUI.

This module handles desktop notifications, scan result notifications,
and notification-related UI interactions.
"""

import logging

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Manages desktop notifications and notification-related actions."""

    def __init__(self, app):
        """Initialize the notification dispatcher."""
        self._app = app

    def show_scan_result_notification(self, result):
        """Show a desktop notification for scan results."""
        if not self._app.settings_manager.get("enable_notifications", True):
            return

        summary = ""
        body = ""

        if result.status == "completed":
            if result.infected_count > 0:
                summary = f"Scan Complete: {result.infected_count} threats found"
                body = f"Scanned {result.files_scanned} files. Action taken on threats."
            else:
                summary = "Scan Complete: No threats found"
                body = f"Scanned {result.files_scanned} files. System appears clean."
        elif result.status == "cancelled":
            summary = "Scan Cancelled"
            body = "The scan was cancelled by the user."
        elif result.status == "error":
            summary = "Scan Error"
            body = result.error_message or "An error occurred during the scan."

        if summary:
            self._app._notification_manager.show_notification(summary, body)

    def show_threat_quarantined_notification(self, threat_name, file_path):
        """Show notification when a threat is quarantined."""
        if not self._app.settings_manager.get("enable_notifications", True):
            return

        summary = "Threat Quarantined"
        body = f"Removed and quarantined: {threat_name}\nLocation: {file_path}"
        self._app._notification_manager.show_notification(summary, body)

    def show_scan_started_notification(self, scan_type, target):
        """Show notification when a scan starts."""
        if not self._app.settings_manager.get("enable_notifications", True):
            return

        summary = f"{scan_type} Scan Started"
        body = f"Scanning: {target}"
        self._app._notification_manager.show_notification(summary, body)

    def show_update_available_notification(self, version):
        """Show notification when an update is available."""
        if not self._app.settings_manager.get("enable_notifications", True):
            return

        summary = "Update Available"
        body = f"ClamAV database update available. Version: {version}"
        self._app._notification_manager.show_notification(summary, body)

    def show_virustotal_scan_complete(self, result):
        """Show notification when VirusTotal scan completes."""
        if not self._app.settings_manager.get("enable_notifications", True):
            return

        summary = "VirusTotal Analysis Complete"
        if result.positives > 0:
            body = f"{result.positives}/{result.total} engines detected threats"
        else:
            body = "No threats detected by VirusTotal"
        self._app._notification_manager.show_notification(summary, body)
