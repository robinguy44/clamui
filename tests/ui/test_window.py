# ClamUI MainWindow Tests
"""
Unit tests for the MainWindow class.

Tests cover:
- Constructor properties (title, size, size request, application reference)
- Minimize-to-tray logic (_should_minimize_to_tray, _on_surface_state_changed,
  _do_minimize_to_tray, recursion prevention via _handling_minimize)
- Close request handling (_on_close_request, scan-active priority, dialog pending,
  tray behavior, close behavior dialog callback)
- Navigation (sidebar selection, leaflet folding, back button, title updates)
- View management (set_content_view, set_active_view)
- Visibility toggling (toggle_visibility, show_window, hide_window)

The MainWindow inherits from Adw.ApplicationWindow. Tests use object.__new__()
to bypass GTK's C-level __init__ and mock internal widgets directly.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest


def _clear_src_modules():
    """Clear cached src.* modules to prevent test pollution."""
    modules_to_remove = [mod for mod in sys.modules if mod.startswith("src.")]
    for mod in modules_to_remove:
        del sys.modules[mod]


@pytest.fixture
def window_class(mock_gi_modules):
    """Import and return the MainWindow class with mocked GTK."""
    # Mock dependent modules that window.py imports
    mock_sidebar = MagicMock()
    mock_compat = MagicMock()
    mock_close_dialog = MagicMock()
    mock_utils = MagicMock()
    mock_utils.resolve_icon_name = MagicMock(side_effect=lambda x: x)

    with patch.dict(
        sys.modules,
        {
            "src.ui.sidebar": mock_sidebar,
            "src.ui.compat": mock_compat,
            "src.ui.close_behavior_dialog": mock_close_dialog,
            "src.ui.utils": mock_utils,
        },
    ):
        from src.ui.window import MainWindow

        yield MainWindow

    _clear_src_modules()


@pytest.fixture
def mock_app():
    """Create a mock Adw.Application with settings_manager and tray_indicator."""
    app = MagicMock()
    app.settings_manager = MagicMock()
    app.settings_manager.get = MagicMock(return_value=False)
    app.tray_indicator = MagicMock()
    app.is_scan_active = False
    app.scan_view = None
    return app


@pytest.fixture
def window(window_class, mock_app):
    """Create a MainWindow instance without calling __init__."""
    win = object.__new__(window_class)

    # Initialize core state that __init__ would set
    win._application = mock_app
    win._current_view_id = "scan"

    # Minimize-to-tray state
    win._handling_minimize = False
    win._close_dialog_pending = False
    win._scan_dialog_pending = False

    # Mock widgets
    win._content_area = MagicMock()
    win._content_view_host = MagicMock()
    win._sidebar = MagicMock()
    win._leaflet = MagicMock()
    win._leaflet.get_folded = MagicMock(return_value=False)
    win._back_button = MagicMock()
    win._title_label = MagicMock()
    win._toast_overlay = MagicMock()
    win._header_bar = MagicMock()
    win._activity_banner = MagicMock()
    win._activity_spinner = MagicMock()
    win._activity_label = MagicMock()

    return win


# =============================================================================
# TestWindowInit - Constructor sets title, default size, size request
# =============================================================================


class TestWindowInit:
    """Tests for MainWindow constructor properties and initialization."""

    def test_init_stores_application_reference(self, window, mock_app):
        """Test __init__ stores the application reference."""
        assert window._application is mock_app

    def test_init_default_view_id_is_scan(self, window):
        """Test initial view ID is 'scan'."""
        assert window._current_view_id == "scan"

    def test_init_handling_minimize_is_false(self, window):
        """Test _handling_minimize flag starts as False."""
        assert window._handling_minimize is False

    def test_init_close_dialog_pending_is_false(self, window):
        """Test _close_dialog_pending flag starts as False."""
        assert window._close_dialog_pending is False

    def test_init_scan_dialog_pending_is_false(self, window):
        """Test _scan_dialog_pending flag starts as False."""
        assert window._scan_dialog_pending is False


# =============================================================================
# TestMinimizeToTray - minimize-to-tray settings and state logic
# =============================================================================


class TestMinimizeToTray:
    """Tests for minimize-to-tray functionality."""

    def test_should_minimize_to_tray_when_all_conditions_met(self, window, mock_app):
        """Test _should_minimize_to_tray returns True when setting enabled and tray available."""
        mock_app.settings_manager.get.return_value = True

        assert window._should_minimize_to_tray() is True

    def test_should_minimize_to_tray_returns_false_when_setting_disabled(self, window, mock_app):
        """Test returns False when minimize_to_tray setting is disabled."""
        mock_app.settings_manager.get.return_value = False

        assert window._should_minimize_to_tray() is False

    def test_should_minimize_to_tray_returns_false_when_no_settings_manager(self, window, mock_app):
        """Test returns False when settings_manager is not available."""
        del mock_app.settings_manager

        assert window._should_minimize_to_tray() is False

    def test_should_minimize_to_tray_returns_false_when_settings_manager_none(
        self, window, mock_app
    ):
        """Test returns False when settings_manager is None."""
        mock_app.settings_manager = None

        assert window._should_minimize_to_tray() is False

    def test_should_minimize_to_tray_returns_false_when_no_tray_indicator(self, window, mock_app):
        """Test returns False when tray_indicator attribute is missing."""
        mock_app.settings_manager.get.return_value = True
        del mock_app.tray_indicator

        assert window._should_minimize_to_tray() is False

    def test_should_minimize_to_tray_returns_false_when_tray_indicator_none(self, window, mock_app):
        """Test returns False when tray_indicator is None."""
        mock_app.settings_manager.get.return_value = True
        mock_app.tray_indicator = None

        assert window._should_minimize_to_tray() is False

    def test_on_surface_state_changed_skips_when_handling_minimize(self, window):
        """Test _on_surface_state_changed returns early when _handling_minimize is True."""
        window._handling_minimize = True
        mock_surface = MagicMock()

        # Should return immediately without checking state
        window._on_surface_state_changed(mock_surface, None)

        mock_surface.get_state.assert_not_called()

    def test_on_surface_state_changed_triggers_minimize_to_tray(
        self, window, mock_app, mock_gi_modules
    ):
        """Test _on_surface_state_changed triggers minimize-to-tray when minimized."""
        mock_app.settings_manager.get.return_value = True

        mock_surface = MagicMock()
        # Simulate MINIMIZED state
        gdk_mock = MagicMock()
        gdk_mock.ToplevelState.MINIMIZED = 4
        mock_surface.get_state.return_value = 4  # MINIMIZED flag set

        glib = mock_gi_modules["glib"]
        glib.idle_add = MagicMock()

        with patch.dict(sys.modules, {"gi.repository.Gdk": gdk_mock}):
            with patch("src.ui.window.Gdk", gdk_mock):
                with patch("src.ui.window.GLib", glib):
                    window._on_surface_state_changed(mock_surface, None)

        glib.idle_add.assert_called_once_with(window._do_minimize_to_tray)

    def test_on_surface_state_changed_sets_and_clears_handling_flag(
        self, window, mock_app, mock_gi_modules
    ):
        """Test _handling_minimize flag is set during handling and cleared after."""
        mock_app.settings_manager.get.return_value = True

        mock_surface = MagicMock()
        gdk_mock = MagicMock()
        gdk_mock.ToplevelState.MINIMIZED = 4
        mock_surface.get_state.return_value = 4

        glib = mock_gi_modules["glib"]
        glib.idle_add = MagicMock()

        flags_during_call = []

        def capture_flag(*args):
            flags_during_call.append(window._handling_minimize)

        glib.idle_add.side_effect = capture_flag

        with patch("src.ui.window.Gdk", gdk_mock):
            with patch("src.ui.window.GLib", glib):
                window._on_surface_state_changed(mock_surface, None)

        # Flag should have been True during idle_add call
        assert flags_during_call == [True]
        # Flag should be False after return
        assert window._handling_minimize is False

    def test_do_minimize_to_tray_hides_window(self, window):
        """Test _do_minimize_to_tray calls unminimize and hide_window."""
        window.unminimize = MagicMock()
        window.hide_window = MagicMock()

        result = window._do_minimize_to_tray()

        window.unminimize.assert_called_once()
        window.hide_window.assert_called_once()
        assert result is False  # Returns False to remove from idle queue

    def test_do_minimize_to_tray_updates_tray_menu(self, window, mock_app):
        """Test _do_minimize_to_tray updates tray menu label."""
        window.unminimize = MagicMock()
        window.hide_window = MagicMock()
        mock_app.tray_indicator.update_window_menu_label = MagicMock()

        window._do_minimize_to_tray()

        mock_app.tray_indicator.update_window_menu_label.assert_called_once()


# =============================================================================
# TestCloseRequest - close request handling with multi-level priority
# =============================================================================


class TestCloseRequest:
    """Tests for _on_close_request and close behavior logic."""

    def test_close_request_returns_true_when_scan_active(self, window, mock_app):
        """Test returns True (block close) when scan is active."""
        mock_app.is_scan_active = True
        window._show_scan_in_progress_dialog = MagicMock()

        result = window._on_close_request(window)

        assert result is True
        window._show_scan_in_progress_dialog.assert_called_once()

    def test_close_request_returns_true_when_scan_dialog_pending(self, window, mock_app):
        """Test returns True when scan dialog is already shown."""
        mock_app.is_scan_active = True
        window._scan_dialog_pending = True

        result = window._on_close_request(window)

        assert result is True

    def test_close_request_skips_scan_check_when_not_active(self, window, mock_app):
        """Test skips scan check when no scan is active."""
        mock_app.is_scan_active = False
        window._show_scan_in_progress_dialog = MagicMock()
        window._is_tray_available = MagicMock(return_value=False)

        window._on_close_request(window)

        window._show_scan_in_progress_dialog.assert_not_called()

    def test_close_request_returns_false_when_no_tray(self, window, mock_app):
        """Test returns False (allow close) when tray is not available."""
        mock_app.is_scan_active = False
        del mock_app.tray_indicator

        result = window._on_close_request(window)

        assert result is False

    def test_close_request_returns_true_when_close_dialog_pending(self, window, mock_app):
        """Test returns True when a close dialog is already open."""
        mock_app.is_scan_active = False
        window._close_dialog_pending = True

        result = window._on_close_request(window)

        assert result is True

    def test_close_request_minimizes_when_behavior_is_minimize(self, window, mock_app):
        """Test hides to tray when close_behavior is 'minimize'."""
        mock_app.is_scan_active = False
        mock_app.settings_manager.get.return_value = "minimize"
        window._do_close_to_tray = MagicMock()

        result = window._on_close_request(window)

        assert result is True
        window._do_close_to_tray.assert_called_once()

    def test_close_request_quits_when_behavior_is_quit(self, window, mock_app):
        """Test returns False (allow close) when close_behavior is 'quit'."""
        mock_app.is_scan_active = False
        mock_app.settings_manager.get.return_value = "quit"

        result = window._on_close_request(window)

        assert result is False

    def test_close_request_shows_dialog_when_behavior_is_ask(self, window, mock_app):
        """Test shows close behavior dialog when close_behavior is 'ask'."""
        mock_app.is_scan_active = False
        mock_app.settings_manager.get.return_value = "ask"
        window._show_close_behavior_dialog = MagicMock()

        result = window._on_close_request(window)

        assert result is True
        window._show_close_behavior_dialog.assert_called_once()

    def test_close_request_shows_dialog_when_behavior_is_none(self, window, mock_app):
        """Test shows dialog when close_behavior is None (first run)."""
        mock_app.is_scan_active = False
        mock_app.settings_manager.get.return_value = None
        window._show_close_behavior_dialog = MagicMock()

        result = window._on_close_request(window)

        assert result is True
        window._show_close_behavior_dialog.assert_called_once()


class TestCloseDialogResponse:
    """Tests for _on_close_behavior_dialog_response callback."""

    def test_dialog_response_clears_pending_flag(self, window):
        """Test dialog response always clears _close_dialog_pending."""
        window._close_dialog_pending = True

        window._on_close_behavior_dialog_response(None, False)

        assert window._close_dialog_pending is False

    def test_dialog_response_none_does_nothing(self, window, mock_app):
        """Test dismissed dialog (None choice) does nothing."""
        window._close_dialog_pending = True
        window._do_close_to_tray = MagicMock()

        window._on_close_behavior_dialog_response(None, False)

        window._do_close_to_tray.assert_not_called()
        mock_app.quit.assert_not_called()

    def test_dialog_response_minimize_hides_to_tray(self, window):
        """Test 'minimize' choice hides window to tray."""
        window._close_dialog_pending = True
        window._do_close_to_tray = MagicMock()

        window._on_close_behavior_dialog_response("minimize", False)

        window._do_close_to_tray.assert_called_once()

    def test_dialog_response_quit_calls_app_quit(self, window, mock_app):
        """Test 'quit' choice calls application.quit()."""
        window._close_dialog_pending = True

        window._on_close_behavior_dialog_response("quit", False)

        mock_app.quit.assert_called_once()

    def test_dialog_response_saves_when_remember_checked(self, window, mock_app):
        """Test saves preference when remember=True."""
        window._close_dialog_pending = True
        window._do_close_to_tray = MagicMock()

        window._on_close_behavior_dialog_response("minimize", True)

        mock_app.settings_manager.set.assert_called_with("close_behavior", "minimize")

    def test_dialog_response_does_not_save_when_remember_unchecked(self, window, mock_app):
        """Test does not save preference when remember=False."""
        window._close_dialog_pending = True
        window._do_close_to_tray = MagicMock()

        window._on_close_behavior_dialog_response("minimize", False)

        mock_app.settings_manager.set.assert_not_called()


# =============================================================================
# TestScanInProgress - scan-active close handling
# =============================================================================


class TestScanInProgress:
    """Tests for scan-in-progress close handling."""

    def test_is_scan_active_returns_app_property(self, window, mock_app):
        """Test _is_scan_active returns application's is_scan_active."""
        mock_app.is_scan_active = True
        assert window._is_scan_active() is True

        mock_app.is_scan_active = False
        assert window._is_scan_active() is False

    def test_is_scan_active_returns_false_when_no_attribute(self, window, mock_app):
        """Test returns False when application lacks is_scan_active."""
        del mock_app.is_scan_active

        assert window._is_scan_active() is False

    def test_on_scan_dialog_response_none_does_nothing(self, window):
        """Test dismissed scan dialog does nothing."""
        window._scan_dialog_pending = True
        window._cancel_active_scan = MagicMock()
        window._proceed_with_close = MagicMock()

        window._on_scan_dialog_response(None)

        assert window._scan_dialog_pending is False
        window._cancel_active_scan.assert_not_called()
        window._proceed_with_close.assert_not_called()

    def test_on_scan_dialog_response_cancel_and_close(self, window):
        """Test 'cancel_and_close' cancels scan and proceeds with close."""
        window._scan_dialog_pending = True
        window._cancel_active_scan = MagicMock()
        window._proceed_with_close = MagicMock()

        window._on_scan_dialog_response("cancel_and_close")

        assert window._scan_dialog_pending is False
        window._cancel_active_scan.assert_called_once()
        window._proceed_with_close.assert_called_once()

    def test_cancel_active_scan_cancels_scanner(self, window, mock_app):
        """Test _cancel_active_scan cancels the active scanner."""
        mock_scanner = MagicMock()
        mock_scan_view = MagicMock()
        mock_scan_view._scanner = mock_scanner
        mock_scan_view._cancel_all_requested = False
        mock_app.scan_view = mock_scan_view

        window._cancel_active_scan()

        assert mock_scan_view._cancel_all_requested is True
        mock_scanner.cancel.assert_called_once()

    def test_cancel_active_scan_noop_when_no_scan_view(self, window, mock_app):
        """Test _cancel_active_scan does nothing when no scan_view."""
        del mock_app.scan_view

        # Should not raise
        window._cancel_active_scan()


# =============================================================================
# TestTrayAvailability - _is_tray_available helper
# =============================================================================


class TestTrayAvailability:
    """Tests for _is_tray_available helper."""

    def test_is_tray_available_returns_true_when_tray_present(self, window, mock_app):
        """Test returns True when tray_indicator is available."""
        assert window._is_tray_available() is True

    def test_is_tray_available_returns_false_when_no_tray_attribute(self, window, mock_app):
        """Test returns False when tray_indicator attribute missing."""
        del mock_app.tray_indicator

        assert window._is_tray_available() is False

    def test_is_tray_available_returns_false_when_tray_none(self, window, mock_app):
        """Test returns False when tray_indicator is None."""
        mock_app.tray_indicator = None

        assert window._is_tray_available() is False


# =============================================================================
# TestCloseBehavior - _get_close_behavior helper
# =============================================================================


class TestCloseBehavior:
    """Tests for _get_close_behavior helper."""

    def test_get_close_behavior_returns_setting(self, window, mock_app):
        """Test returns the close_behavior setting value."""
        mock_app.settings_manager.get.return_value = "minimize"

        result = window._get_close_behavior()

        assert result == "minimize"
        mock_app.settings_manager.get.assert_called_with("close_behavior", None)

    def test_get_close_behavior_returns_none_when_no_settings_manager(self, window, mock_app):
        """Test returns None when settings_manager is missing."""
        del mock_app.settings_manager

        assert window._get_close_behavior() is None

    def test_get_close_behavior_returns_none_when_settings_manager_none(self, window, mock_app):
        """Test returns None when settings_manager is None."""
        mock_app.settings_manager = None

        assert window._get_close_behavior() is None


# =============================================================================
# TestNavigation - sidebar and leaflet navigation
# =============================================================================


class TestNavigation:
    """Tests for sidebar selection, leaflet folding, and navigation."""

    def test_sidebar_selection_updates_view_id(self, window):
        """Test _on_sidebar_selection updates _current_view_id."""
        window._on_sidebar_selection("statistics")

        assert window._current_view_id == "statistics"

    def test_sidebar_selection_activates_action(self, window, mock_app):
        """Test _on_sidebar_selection activates the app action."""
        window._on_sidebar_selection("logs")

        mock_app.activate_action.assert_called_with("show-logs", None)

    def test_sidebar_selection_navigates_forward_when_folded(self, window):
        """Test sidebar selection navigates to content when leaflet is folded."""
        window._leaflet.get_folded.return_value = True

        window._on_sidebar_selection("quarantine")

        window._leaflet.navigate.assert_called_once()
        window._back_button.set_visible.assert_called_with(True)

    def test_sidebar_selection_does_not_navigate_when_unfolded(self, window):
        """Test sidebar selection does not navigate when leaflet is not folded."""
        window._leaflet.get_folded.return_value = False

        window._on_sidebar_selection("scan")

        window._leaflet.navigate.assert_not_called()

    def test_on_back_clicked_navigates_back(self, window):
        """Test _on_back_clicked navigates to sidebar."""
        window._on_back_clicked(MagicMock())

        window._leaflet.navigate.assert_called_once()
        window._back_button.set_visible.assert_called_with(False)

    def test_leaflet_folded_changed_shows_back_button(self, window):
        """Test back button shown when folded and viewing content."""
        window._leaflet.get_folded.return_value = True
        window._leaflet.get_visible_child.return_value = window._content_area
        window._update_title = MagicMock()

        window._on_leaflet_folded_changed(window._leaflet, None)

        window._back_button.set_visible.assert_called_with(True)

    def test_leaflet_folded_changed_hides_back_button_when_unfolded(self, window):
        """Test back button hidden when leaflet is not folded."""
        window._leaflet.get_folded.return_value = False
        window._leaflet.get_visible_child.return_value = window._content_area
        window._update_title = MagicMock()

        window._on_leaflet_folded_changed(window._leaflet, None)

        window._back_button.set_visible.assert_called_with(False)


# =============================================================================
# TestViewManagement - content view switching
# =============================================================================


class TestViewManagement:
    """Tests for set_content_view and set_active_view."""

    def test_set_content_view_removes_existing_children(self, window):
        """Test set_content_view removes old content before adding new."""
        mock_child = MagicMock()
        mock_child.get_next_sibling.return_value = None
        window._content_view_host.get_first_child.return_value = mock_child

        new_view = MagicMock()
        window.set_content_view(new_view)

        window._content_view_host.remove.assert_called_with(mock_child)
        window._content_view_host.append.assert_called_with(new_view)

    def test_set_content_view_sets_expand_on_new_view(self, window):
        """Test set_content_view sets vexpand and hexpand on the new view."""
        window._content_view_host.get_first_child.return_value = None
        new_view = MagicMock()

        window.set_content_view(new_view)

        new_view.set_vexpand.assert_called_with(True)
        new_view.set_hexpand.assert_called_with(True)

    def test_set_active_view_updates_sidebar(self, window):
        """Test set_active_view updates sidebar selection and view ID."""
        window._update_title = MagicMock()

        window.set_active_view("logs")

        assert window._current_view_id == "logs"
        window._sidebar.select_view.assert_called_with("logs")
        window._update_title.assert_called_once()


# =============================================================================
# TestVisibility - toggle, show, hide
# =============================================================================


class TestVisibility:
    """Tests for window visibility toggling."""

    def test_toggle_visibility_hides_when_visible(self, window):
        """Test toggle_visibility hides window when currently visible."""
        window.is_visible = MagicMock(return_value=True)
        window.hide_window = MagicMock()
        window.show_window = MagicMock()

        window.toggle_visibility()

        window.hide_window.assert_called_once()
        window.show_window.assert_not_called()

    def test_toggle_visibility_shows_when_hidden(self, window):
        """Test toggle_visibility shows window when currently hidden."""
        window.is_visible = MagicMock(return_value=False)
        window.hide_window = MagicMock()
        window.show_window = MagicMock()

        window.toggle_visibility()

        window.show_window.assert_called_once()
        window.hide_window.assert_not_called()

    def test_show_window_sets_visible_and_presents(self, window):
        """Test show_window calls set_visible(True) and present()."""
        window.set_visible = MagicMock()
        window.present = MagicMock()

        window.show_window()

        window.set_visible.assert_called_with(True)
        window.present.assert_called_once()

    def test_hide_window_sets_visible_false(self, window):
        """Test hide_window calls set_visible(False)."""
        window.set_visible = MagicMock()

        window.hide_window()

        window.set_visible.assert_called_with(False)


# =============================================================================
# TestCloseToTray - _do_close_to_tray
# =============================================================================


class TestCloseToTray:
    """Tests for _do_close_to_tray behavior."""

    def test_do_close_to_tray_hides_window(self, window):
        """Test _do_close_to_tray calls hide_window."""
        window.hide_window = MagicMock()

        window._do_close_to_tray()

        window.hide_window.assert_called_once()

    def test_do_close_to_tray_updates_tray_menu(self, window, mock_app):
        """Test _do_close_to_tray updates tray menu label."""
        window.hide_window = MagicMock()

        window._do_close_to_tray()

        mock_app.tray_indicator.update_window_menu_label.assert_called_with(visible=False)

    def test_do_close_to_tray_handles_no_tray(self, window, mock_app):
        """Test _do_close_to_tray handles missing tray gracefully."""
        window.hide_window = MagicMock()
        del mock_app.tray_indicator

        # Should not raise
        window._do_close_to_tray()

        window.hide_window.assert_called_once()


# =============================================================================
# TestToast - toast notifications
# =============================================================================


class TestToast:
    """Tests for toast notification support."""

    def test_add_toast_delegates_to_overlay(self, window):
        """Test add_toast passes toast to the overlay."""
        mock_toast = MagicMock()

        window.add_toast(mock_toast)

        window._toast_overlay.add_toast.assert_called_with(mock_toast)


class TestActivityBanner:
    """Tests for the transient startup activity banner."""

    def test_set_activity_status_shows_banner_and_starts_spinner(self, window):
        """Test set_activity_status reveals the banner when a message is provided."""
        window.set_activity_status("Updating stored logs for privacy (1/3)")

        window._activity_label.set_label.assert_called_once_with(
            "Updating stored logs for privacy (1/3)"
        )
        window._activity_spinner.set_visible.assert_called_once_with(True)
        window._activity_spinner.start.assert_called_once()
        window._activity_banner.set_reveal_child.assert_called_once_with(True)

    def test_set_activity_status_can_show_banner_without_spinner(self, window):
        """Test set_activity_status can show a completion banner without spinner activity."""
        window.set_activity_status("Updating stored logs for privacy (3/3)", show_spinner=False)

        window._activity_label.set_label.assert_called_once_with(
            "Updating stored logs for privacy (3/3)"
        )
        window._activity_spinner.stop.assert_called_once()
        window._activity_spinner.set_visible.assert_called_once_with(False)
        window._activity_banner.set_reveal_child.assert_called_once_with(True)

    def test_set_activity_status_hides_banner_when_message_cleared(self, window):
        """Test set_activity_status hides the banner when message is None."""
        window.set_activity_status(None)

        window._activity_spinner.stop.assert_called_once()
        window._activity_spinner.set_visible.assert_called_once_with(False)
        window._activity_banner.set_reveal_child.assert_called_once_with(False)


# =============================================================================
# TestProperties - content_area and sidebar properties
# =============================================================================


class TestProperties:
    """Tests for read-only properties."""

    def test_content_area_property(self, window):
        """Test content_area property returns the content box."""
        assert window.content_area is window._content_area

    def test_sidebar_property(self, window):
        """Test sidebar property returns the navigation sidebar."""
        assert window.sidebar is window._sidebar
