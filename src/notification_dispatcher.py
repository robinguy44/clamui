# ClamUI Notification Dispatcher
"""
Notification management for ClamUI.

This module handles desktop notifications, scan result notifications,
and notification-related UI interactions.
"""

import logging

from .core.i18n import _

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
                summary = _("Scan Complete: {count} threats found").format(
                    count=result.infected_count
                )
                body = _("Scanned {count} files. Action taken on threats.").format(
                    count=result.files_scanned
                )
            else:
                summary = _("Scan Complete: No threats found")
                body = _("Scanned {count} files. System appears clean.").format(
                    count=result.files_scanned
                )
        elif result.status == "cancelled":
            summary = _("Scan Cancelled")
            body = _("The scan was cancelled by the user.")
        elif result.status == "error":
            summary = _("Scan Error")
            body = result.error_message or _("An error occurred during the scan.")

        if summary:
            self._app._notification_manager.show_notification(summary, body)

    def show_threat_quarantined_notification(self, threat_name, file_path):
        """Show notification when a threat is quarantined."""
        if not self._app.settings_manager.get("enable_notifications", True):
            return

        summary = _("Threat Quarantined")
        body = _("Removed and quarantined: {threat}\nLocation: {path}").format(
            threat=threat_name, path=file_path
        )
        self._app._notification_manager.show_notification(summary, body)

    def show_scan_started_notification(self, scan_type, target):
        """Show notification when a scan starts."""
        if not self._app.settings_manager.get("enable_notifications", True):
            return

        summary = _("{scan_type} Scan Started").format(scan_type=scan_type)
        body = _("Scanning: {target}").format(target=target)
        self._app._notification_manager.show_notification(summary, body)

    def show_update_available_notification(self, version):
        """Show notification when an update is available."""
        if not self._app.settings_manager.get("enable_notifications", True):
            return

        summary = _("Update Available")
        body = _("ClamAV database update available. Version: {version}").format(version=version)
        self._app._notification_manager.show_notification(summary, body)

    def show_virustotal_scan_complete(self, result):
        """Show notification when VirusTotal scan completes."""
        if not self._app.settings_manager.get("enable_notifications", True):
            return

        summary = _("VirusTotal Analysis Complete")
        if result.positives > 0:
            body = _("{positives}/{total} engines detected threats").format(
                positives=result.positives, total=result.total
            )
        else:
            body = _("No threats detected by VirusTotal")
        self._app._notification_manager.show_notification(summary, body)
