# ScanCoordinator Tests
"""
Unit tests for the ScanCoordinator component.

Tests cover:
- Scan state tracking (is_scan_active)
- Scan state change callback wiring
- Tray indicator updates on state changes
- Quick scan profile lookup
- Quick scan start (with and without profile)
- Configure quick scan (no auto-start)
- Profile sync to tray
- VirusTotal scan dispatch (key found, key missing)
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from src.core.scanner_types import ScanResult, ScanStatus


def _make_scan_result(
    status=ScanStatus.CLEAN,
    infected_count=0,
    infected_files=None,
):
    """Helper to create a ScanResult with sensible defaults."""
    return ScanResult(
        status=status,
        path="/test",
        stdout="",
        stderr="",
        exit_code=0 if status == ScanStatus.CLEAN else 1,
        infected_files=infected_files or [],
        scanned_files=10,
        scanned_dirs=2,
        infected_count=infected_count,
        error_message=None,
        threat_details=[],
    )


@pytest.fixture
def mock_gi_for_coordinator():
    """Minimal GLib/Gio mock needed by coordinator."""
    mock_glib = MagicMock()
    mock_glib.idle_add = MagicMock(side_effect=lambda fn, *a: fn(*a))

    mock_gio = MagicMock()
    mock_gtk = MagicMock()
    mock_adw = MagicMock()

    mock_gi = MagicMock()
    mock_gi.require_version = MagicMock()
    mock_repository = MagicMock()
    mock_repository.GLib = mock_glib
    mock_repository.Gio = mock_gio
    mock_repository.Gtk = mock_gtk
    mock_repository.Adw = mock_adw

    with patch.dict(
        sys.modules,
        {
            "gi": mock_gi,
            "gi.repository": mock_repository,
            "gi.repository.GLib": mock_glib,
            "gi.repository.Gio": mock_gio,
            "gi.repository.Gtk": mock_gtk,
            "gi.repository.Adw": mock_adw,
        },
    ):
        yield {
            "glib": mock_glib,
            "gio": mock_gio,
            "gtk": mock_gtk,
            "adw": mock_adw,
        }


@pytest.fixture
def app_context():
    """Create a mock AppContext."""
    ctx = MagicMock()
    ctx.is_scan_active = False
    ctx.tray_indicator = None  # No tray by default
    ctx.profile_manager = MagicMock()
    ctx.notification_manager = MagicMock()
    return ctx


@pytest.fixture
def view_coordinator():
    """Create a mock ViewCoordinator."""
    vc = MagicMock()
    vc.scan_view = MagicMock()
    vc._scan_view = MagicMock()  # For sync_profiles_to_tray check
    return vc


@pytest.fixture
def coordinator(mock_gi_for_coordinator, app_context, view_coordinator):
    """Create a ScanCoordinator with mocked dependencies."""
    # Clear cached module
    for mod_name in list(sys.modules.keys()):
        if "src.ui.scan.coordinator" in mod_name:
            del sys.modules[mod_name]

    from src.ui.scan.coordinator import ScanCoordinator

    return ScanCoordinator(app_context, view_coordinator)


# =============================================================================
# Scan State Tracking
# =============================================================================


class TestScanStateTracking:
    """Tests for is_scan_active property delegation."""

    def test_is_scan_active_delegates_to_context(self, coordinator, app_context):
        """is_scan_active should read from app_context."""
        app_context.is_scan_active = False
        assert coordinator.is_scan_active is False

        app_context.is_scan_active = True
        assert coordinator.is_scan_active is True


# =============================================================================
# Scan State Changed Callback
# =============================================================================


class TestScanStateChangedCallback:
    """Tests for scan state change handling."""

    def test_set_scan_state_changed_callback(self, coordinator):
        """Should store the callback."""
        cb = MagicMock()
        coordinator.set_scan_state_changed_callback(cb)
        assert coordinator._scan_state_changed_callback is cb

    def test_on_scan_state_changed_updates_context(self, coordinator, app_context):
        """State change should update app_context.is_scan_active."""
        coordinator._on_scan_state_changed(True)
        assert app_context.is_scan_active is True

        coordinator._on_scan_state_changed(False)
        assert app_context.is_scan_active is False

    def test_on_scan_state_changed_fires_callback(self, coordinator):
        """State change should fire the registered callback."""
        cb = MagicMock()
        coordinator.set_scan_state_changed_callback(cb)

        result = _make_scan_result()
        coordinator._on_scan_state_changed(False, result)

        cb.assert_called_once_with(False, result)

    def test_on_scan_state_changed_no_callback_no_error(self, coordinator):
        """State change without callback should not error."""
        coordinator._on_scan_state_changed(True)
        coordinator._on_scan_state_changed(False)
        # No exception means pass


# =============================================================================
# Tray Indicator Updates
# =============================================================================


class TestTrayIndicatorUpdates:
    """Tests for tray indicator updates on scan state changes."""

    def test_scanning_updates_tray_to_scanning(self, coordinator, app_context):
        """Starting a scan should update tray to 'scanning' status."""
        tray = MagicMock()
        app_context.tray_indicator = tray

        coordinator._on_scan_state_changed(True)

        tray.update_status.assert_called_with("scanning")
        tray.update_scan_progress.assert_called_with(0)

    def test_scan_complete_clean_updates_tray_to_protected(self, coordinator, app_context):
        """Clean scan result should update tray to 'protected'."""
        tray = MagicMock()
        app_context.tray_indicator = tray

        result = _make_scan_result(status=ScanStatus.CLEAN)
        coordinator._on_scan_state_changed(False, result)

        tray.update_status.assert_called_with("protected")

    def test_scan_complete_infected_updates_tray_to_threat(self, coordinator, app_context):
        """Infected scan result should update tray to 'threat'."""
        tray = MagicMock()
        app_context.tray_indicator = tray

        result = _make_scan_result(
            status=ScanStatus.INFECTED,
            infected_count=1,
            infected_files=["/bad"],
        )
        coordinator._on_scan_state_changed(False, result)

        tray.update_status.assert_called_with("threat")

    def test_scan_complete_error_updates_tray_to_warning(self, coordinator, app_context):
        """Error scan result should update tray to 'warning'."""
        tray = MagicMock()
        app_context.tray_indicator = tray

        result = _make_scan_result(status=ScanStatus.ERROR)
        coordinator._on_scan_state_changed(False, result)

        tray.update_status.assert_called_with("warning")

    def test_scan_complete_no_result_defaults_to_protected(self, coordinator, app_context):
        """Finishing without a result should default to 'protected'."""
        tray = MagicMock()
        app_context.tray_indicator = tray

        coordinator._on_scan_state_changed(False, None)

        tray.update_status.assert_called_with("protected")

    def test_no_tray_no_error(self, coordinator, app_context):
        """State change without tray indicator should not error."""
        app_context.tray_indicator = None
        coordinator._on_scan_state_changed(True)
        coordinator._on_scan_state_changed(False)
        # No exception means pass


# =============================================================================
# Quick Scan Profile
# =============================================================================


class TestQuickScanProfile:
    """Tests for quick scan profile lookup."""

    def test_get_quick_scan_profile_found(self, coordinator, app_context):
        """Should return profile when 'Quick Scan' exists."""
        profile = MagicMock()
        profile.name = "Quick Scan"
        app_context.profile_manager.get_profile_by_name.return_value = profile

        result = coordinator.get_quick_scan_profile()

        assert result is profile
        app_context.profile_manager.get_profile_by_name.assert_called_with("Quick Scan")

    def test_get_quick_scan_profile_not_found(self, coordinator, app_context):
        """Should return None when 'Quick Scan' does not exist."""
        app_context.profile_manager.get_profile_by_name.return_value = None

        result = coordinator.get_quick_scan_profile()

        assert result is None


# =============================================================================
# Start Quick Scan
# =============================================================================


class TestStartQuickScan:
    """Tests for starting quick scans."""

    def test_start_quick_scan_with_profile(self, coordinator, app_context, view_coordinator):
        """Quick scan with profile should select profile and start scan."""
        profile = MagicMock()
        profile.id = "qscan-123"
        app_context.profile_manager.get_profile_by_name.return_value = profile

        window = MagicMock()
        coordinator.start_quick_scan(window)

        view_coordinator.switch_to.assert_called_with("scan", window)
        view_coordinator.scan_view.refresh_profiles.assert_called_once()
        view_coordinator.scan_view.set_selected_profile.assert_called_with("qscan-123")
        view_coordinator.scan_view._start_scan.assert_called_once()

    def test_start_quick_scan_without_profile_falls_back_to_home(
        self, coordinator, app_context, view_coordinator
    ):
        """Quick scan without profile should use home directory."""
        app_context.profile_manager.get_profile_by_name.return_value = None

        window = MagicMock()
        coordinator.start_quick_scan(window)

        view_coordinator.switch_to.assert_called_with("scan", window)
        # Should set home directory as path
        home = os.path.expanduser("~")
        view_coordinator.scan_view._set_selected_path.assert_called_with(home)
        view_coordinator.scan_view._start_scan.assert_called_once()


# =============================================================================
# Configure Quick Scan (No Auto-Start)
# =============================================================================


class TestConfigureQuickScan:
    """Tests for configuring quick scan without starting."""

    def test_configure_with_profile(self, coordinator, app_context, view_coordinator):
        """configure_quick_scan with profile should select profile but not start."""
        profile = MagicMock()
        profile.id = "qscan-456"
        app_context.profile_manager.get_profile_by_name.return_value = profile

        window = MagicMock()
        coordinator.configure_quick_scan(window)

        view_coordinator.switch_to.assert_called_with("scan", window)
        view_coordinator.scan_view.refresh_profiles.assert_called_once()
        view_coordinator.scan_view.set_selected_profile.assert_called_with("qscan-456")
        # Should NOT start scan
        view_coordinator.scan_view._start_scan.assert_not_called()

    def test_configure_without_profile(self, coordinator, app_context, view_coordinator):
        """configure_quick_scan without profile should set home dir but not start."""
        app_context.profile_manager.get_profile_by_name.return_value = None

        window = MagicMock()
        coordinator.configure_quick_scan(window)

        view_coordinator.switch_to.assert_called_with("scan", window)
        home = os.path.expanduser("~")
        view_coordinator.scan_view._set_selected_path.assert_called_with(home)
        view_coordinator.scan_view._start_scan.assert_not_called()


# =============================================================================
# System Scan
# =============================================================================


class TestSystemScan:
    """Tests for system scan from header bar."""

    def test_start_system_scan_delegates_to_quick_scan(
        self, coordinator, app_context, view_coordinator
    ):
        """start_system_scan should delegate to start_quick_scan."""
        profile = MagicMock()
        profile.id = "qscan-789"
        app_context.profile_manager.get_profile_by_name.return_value = profile

        window = MagicMock()
        coordinator.start_system_scan(window)

        # Should have done everything start_quick_scan does
        view_coordinator.switch_to.assert_called_with("scan", window)
        view_coordinator.scan_view._start_scan.assert_called_once()


# =============================================================================
# Open File Picker
# =============================================================================


class TestOpenFilePicker:
    """Tests for file picker opening."""

    def test_open_file_picker_switches_to_scan(self, coordinator, view_coordinator):
        """open_file_picker should switch to scan view first."""
        window = MagicMock()
        coordinator.open_file_picker(window)

        view_coordinator.switch_to.assert_called_with("scan", window)
        view_coordinator.scan_view.show_file_picker.assert_called_once()


# =============================================================================
# Connect Scan View Callbacks
# =============================================================================


class TestConnectScanViewCallbacks:
    """Tests for connecting scan view to state callbacks."""

    def test_connect_when_scan_view_has_method(self, coordinator, view_coordinator):
        """Should connect callback when scan_view has set_scan_state_changed_callback."""
        scan_view = MagicMock()
        scan_view.set_scan_state_changed_callback = MagicMock()
        view_coordinator.scan_view = scan_view

        coordinator.connect_scan_view_callbacks()

        scan_view.set_scan_state_changed_callback.assert_called_once_with(
            coordinator._on_scan_state_changed
        )

    def test_connect_when_scan_view_lacks_method(self, coordinator, view_coordinator):
        """Should not error when scan_view lacks the method."""
        scan_view = MagicMock(spec=[])  # Empty spec - no attributes
        view_coordinator.scan_view = scan_view

        # hasattr will return False since spec is empty
        coordinator.connect_scan_view_callbacks()
        # No exception means pass


# =============================================================================
# Profile Sync to Tray
# =============================================================================


class TestProfileSyncToTray:
    """Tests for syncing profiles to tray menu."""

    def test_sync_profiles_no_tray(self, coordinator, app_context):
        """sync_profiles_to_tray should be a no-op without tray."""
        app_context.tray_indicator = None
        coordinator.sync_profiles_to_tray()
        # No exception means pass

    def test_sync_profiles_to_tray(self, coordinator, app_context, view_coordinator):
        """Should send profile data to tray indicator."""
        tray = MagicMock()
        app_context.tray_indicator = tray

        profile1 = MagicMock()
        profile1.id = "p1"
        profile1.name = "Quick Scan"
        profile1.is_default = True
        profile2 = MagicMock()
        profile2.id = "p2"
        profile2.name = "Full Scan"
        profile2.is_default = False

        app_context.profile_manager.list_profiles.return_value = [profile1, profile2]

        selected = MagicMock()
        selected.id = "p1"
        view_coordinator.scan_view.get_selected_profile.return_value = selected

        coordinator.sync_profiles_to_tray()

        tray.update_profiles.assert_called_once()
        profile_data, current_id = tray.update_profiles.call_args[0]
        assert len(profile_data) == 2
        assert profile_data[0]["id"] == "p1"
        assert profile_data[0]["name"] == "Quick Scan"
        assert profile_data[0]["is_default"] is True
        assert current_id == "p1"


# =============================================================================
# VirusTotal Scan Handling
# =============================================================================


class TestVirusTotalScan:
    """Tests for VirusTotal scan dispatch."""

    def test_handle_virustotal_with_api_key(self, coordinator, mock_gi_for_coordinator):
        """Should trigger VT scan when API key is available."""
        settings = MagicMock()

        mock_km = MagicMock()
        mock_km.get_api_key.return_value = "vt-key-123"

        with patch.dict(sys.modules, {"src.core.keyring_manager": mock_km}):
            with patch.object(coordinator, "_trigger_virustotal_scan") as mock_trigger:
                coordinator.handle_virustotal_scan("/test/file.exe", settings)

                mock_trigger.assert_called_once_with("/test/file.exe", "vt-key-123", settings)

    def test_handle_virustotal_no_key_prompt(self, coordinator, mock_gi_for_coordinator):
        """Should show setup dialog when no API key and no remembered action."""
        settings = MagicMock()
        settings.get.return_value = "none"

        mock_km = MagicMock()
        mock_km.get_api_key.return_value = None

        with patch.dict(sys.modules, {"src.core.keyring_manager": mock_km}):
            with patch.object(coordinator, "_show_virustotal_setup_dialog") as mock_dialog:
                coordinator.handle_virustotal_scan("/test/file.exe", settings)

                mock_dialog.assert_called_once_with("/test/file.exe", settings)

    def test_handle_virustotal_no_key_open_website(self, coordinator, mock_gi_for_coordinator):
        """Should open VT website when remembered action is 'open_website'."""
        settings = MagicMock()
        settings.get.return_value = "open_website"

        mock_km = MagicMock()
        mock_km.get_api_key.return_value = None

        with patch.dict(sys.modules, {"src.core.keyring_manager": mock_km}):
            with patch.object(coordinator, "_open_virustotal_website") as mock_open:
                coordinator.handle_virustotal_scan("/test/file.exe", settings)

                mock_open.assert_called_once()

    def test_handle_virustotal_no_key_remembered_prompt(
        self, coordinator, mock_gi_for_coordinator, app_context
    ):
        """Should notify when remembered action is 'prompt'."""
        settings = MagicMock()
        settings.get.return_value = "prompt"

        mock_km = MagicMock()
        mock_km.get_api_key.return_value = None

        with patch.dict(sys.modules, {"src.core.keyring_manager": mock_km}):
            coordinator.handle_virustotal_scan("/test/file.exe", settings)

            app_context.notification_manager.notify_virustotal_no_key.assert_called_once()
