# ClamUI Debug Page Tests
"""
Tests for the DebugPage preferences component.
"""

import sys
from unittest.mock import MagicMock, patch


def _clear_src_modules():
    """Clear all cached src.* modules to prevent test pollution."""
    modules_to_remove = [mod for mod in sys.modules if mod.startswith("src.")]
    for mod in modules_to_remove:
        del sys.modules[mod]


class TestDebugPageImport:
    """Test that DebugPage can be imported correctly."""

    def test_import_debug_page(self, mock_gi_modules):
        """Test that DebugPage can be imported."""
        from src.ui.preferences.debug_page import DebugPage

        assert DebugPage is not None
        _clear_src_modules()


class TestDebugPageInit:
    """Test DebugPage initialization."""

    def test_init_with_settings_manager(self, mock_gi_modules):
        """Test initialization with settings manager."""
        settings_manager = MagicMock()

        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage(settings_manager=settings_manager)

        assert page._settings_manager is settings_manager
        _clear_src_modules()

    def test_init_without_settings_manager(self, mock_gi_modules):
        """Test initialization without settings manager."""
        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()

        assert page._settings_manager is None
        _clear_src_modules()

    def test_init_with_parent_window(self, mock_gi_modules):
        """Test initialization with parent window."""
        settings_manager = MagicMock()
        parent_window = MagicMock()

        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage(settings_manager=settings_manager, parent_window=parent_window)

        assert page._parent_window is parent_window
        _clear_src_modules()


class TestDebugPageLogLevelOptions:
    """Test log level options definition."""

    def test_log_level_options_defined(self, mock_gi_modules):
        """Test that log level options are properly defined."""
        from src.ui.preferences.debug_page import DebugPage

        assert DebugPage.LOG_LEVEL_OPTIONS == ["DEBUG", "INFO", "WARNING", "ERROR"]
        _clear_src_modules()

    def test_log_level_descriptions_defined(self, mock_gi_modules):
        """Test that log level descriptions are properly defined."""
        from src.ui.preferences.debug_page import DebugPage

        assert len(DebugPage.LOG_LEVEL_DESCRIPTIONS) == 4
        assert "recommended" in DebugPage.LOG_LEVEL_DESCRIPTIONS[2].lower()
        _clear_src_modules()


class TestDebugPageCreatePage:
    """Test DebugPage.create_page() method."""

    def test_create_page_returns_preferences_page(self, mock_gi_modules):
        """Test create_page returns an Adw.PreferencesPage."""
        adw = mock_gi_modules["adw"]
        mock_page = MagicMock()
        adw.PreferencesPage.return_value = mock_page

        from src.ui.preferences.debug_page import DebugPage

        page_instance = DebugPage()
        page_instance.create_page()

        adw.PreferencesPage.assert_called()
        _clear_src_modules()

    def test_create_page_sets_title_and_icon(self, mock_gi_modules):
        """Test create_page sets appropriate title and icon."""
        adw = mock_gi_modules["adw"]

        from src.ui.preferences.debug_page import DebugPage

        page_instance = DebugPage()
        page_instance.create_page()

        # Check PreferencesPage was created with expected args
        call_kwargs = adw.PreferencesPage.call_args[1]
        assert call_kwargs["title"] == "Debug"
        assert "symbolic" in call_kwargs["icon_name"]
        _clear_src_modules()

    def test_create_page_adds_logging_settings_group(self, mock_gi_modules):
        """Test create_page creates logging settings group."""
        adw = mock_gi_modules["adw"]
        mock_page = MagicMock()
        mock_group = MagicMock()
        adw.PreferencesPage.return_value = mock_page
        adw.PreferencesGroup.return_value = mock_group

        from src.ui.preferences.debug_page import DebugPage

        page_instance = DebugPage()
        page_instance.create_page()

        # Should create preferences groups
        adw.PreferencesGroup.assert_called()
        mock_page.add.assert_called()
        _clear_src_modules()


class TestDebugPageLoadLogLevel:
    """Test log level loading functionality."""

    def test_load_log_level_from_settings(self, mock_gi_modules):
        """Test loading log level from settings manager."""
        adw = mock_gi_modules["adw"]
        _ = mock_gi_modules["gtk"]

        settings_manager = MagicMock()
        settings_manager.get.return_value = "DEBUG"

        mock_combo_row = MagicMock()
        adw.ComboRow.return_value = mock_combo_row

        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage(settings_manager=settings_manager)
        page.create_page()

        # Should have called set_selected with index 0 (DEBUG)
        settings_manager.get.assert_called()
        _clear_src_modules()

    def test_load_log_level_default_warning(self, mock_gi_modules):
        """Test default log level is WARNING when not set."""
        adw = mock_gi_modules["adw"]
        _ = mock_gi_modules["gtk"]

        settings_manager = MagicMock()
        settings_manager.get.return_value = "WARNING"

        mock_combo_row = MagicMock()
        adw.ComboRow.return_value = mock_combo_row

        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage(settings_manager=settings_manager)
        page.create_page()

        # Should use WARNING as default
        assert page._log_level_row is not None
        _clear_src_modules()


class TestDebugPageLogLocation:
    """Test log file location display."""

    def test_logging_settings_group_shows_actual_log_dir(self, mock_gi_modules):
        """Test the UI shows the real log directory path, not a redacted placeholder."""
        adw = mock_gi_modules["adw"]
        created_rows = []

        def action_row_factory(*args, **kwargs):
            row = MagicMock()
            created_rows.append(row)
            return row

        adw.ActionRow.side_effect = action_row_factory

        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()

        with patch("src.ui.preferences.debug_page.get_logging_config") as mock_config:
            mock_logging_config = MagicMock()
            mock_logging_config.get_log_dir.return_value = "/home/user/.local/share/clamui/debug"
            mock_config.return_value = mock_logging_config

            page._create_logging_settings_group()

        assert len(created_rows) == 1
        action_row = created_rows[0]
        action_row.set_subtitle.assert_called_with("/home/user/.local/share/clamui/debug")
        _clear_src_modules()


class TestDebugPageOnLogLevelChanged:
    """Test log level change handling."""

    def test_on_log_level_changed_saves_setting(self, mock_gi_modules):
        """Test that changing log level saves to settings."""
        settings_manager = MagicMock()
        settings_manager.get.return_value = "WARNING"

        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage(settings_manager=settings_manager)
        page.create_page()

        # Simulate combo row change
        mock_row = MagicMock()
        mock_row.get_selected.return_value = 0  # DEBUG

        with patch("src.ui.preferences.debug_page.get_logging_config") as mock_config:
            mock_logging_config = MagicMock()
            mock_config.return_value = mock_logging_config

            page._on_log_level_changed(mock_row, None)

            # Should save to settings
            settings_manager.set.assert_called_with("debug_log_level", "DEBUG")
            # Should apply to logging config
            mock_logging_config.set_log_level.assert_called_with("DEBUG")

        _clear_src_modules()


class TestDebugPageUpdateLogSizeDisplay:
    """Test log size display updates."""

    def test_update_log_size_display_formats_bytes(self, mock_gi_modules):
        """Test log size display formats bytes correctly."""
        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()
        page._log_size_row = MagicMock()

        with patch("src.ui.preferences.debug_page.get_logging_config") as mock_config:
            mock_logging_config = MagicMock()
            mock_logging_config.get_total_log_size.return_value = 500
            mock_logging_config.get_log_files.return_value = [MagicMock()]
            mock_config.return_value = mock_logging_config

            page._update_log_size_display()

            # Should set subtitle with byte format
            page._log_size_row.set_subtitle.assert_called()
            subtitle = page._log_size_row.set_subtitle.call_args[0][0]
            assert "bytes" in subtitle

        _clear_src_modules()

    def test_update_log_size_display_formats_kb(self, mock_gi_modules):
        """Test log size display formats KB correctly."""
        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()
        page._log_size_row = MagicMock()

        with patch("src.ui.preferences.debug_page.get_logging_config") as mock_config:
            mock_logging_config = MagicMock()
            mock_logging_config.get_total_log_size.return_value = 50 * 1024  # 50 KB
            mock_logging_config.get_log_files.return_value = [MagicMock(), MagicMock()]
            mock_config.return_value = mock_logging_config

            page._update_log_size_display()

            subtitle = page._log_size_row.set_subtitle.call_args[0][0]
            assert "KB" in subtitle

        _clear_src_modules()

    def test_update_log_size_display_formats_mb(self, mock_gi_modules):
        """Test log size display formats MB correctly."""
        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()
        page._log_size_row = MagicMock()

        with patch("src.ui.preferences.debug_page.get_logging_config") as mock_config:
            mock_logging_config = MagicMock()
            mock_logging_config.get_total_log_size.return_value = 5 * 1024 * 1024  # 5 MB
            mock_logging_config.get_log_files.return_value = [MagicMock()] * 3
            mock_config.return_value = mock_logging_config

            page._update_log_size_display()

            subtitle = page._log_size_row.set_subtitle.call_args[0][0]
            assert "MB" in subtitle

        _clear_src_modules()


class TestDebugPageExport:
    """Test log export functionality."""

    def test_export_clicked_no_logs_shows_dialog(self, mock_gi_modules):
        """Test export button shows dialog when no logs exist."""
        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()
        page._show_simple_dialog = MagicMock()

        with patch("src.ui.preferences.debug_page.get_logging_config") as mock_config:
            mock_logging_config = MagicMock()
            mock_logging_config.get_log_files.return_value = []
            mock_config.return_value = mock_logging_config

            page._on_export_clicked(None)

            page._show_simple_dialog.assert_called_once()
            args = page._show_simple_dialog.call_args[0]
            assert "No Logs" in args[0]

        _clear_src_modules()

    def test_show_save_dialog_uses_compat_helper(self, mock_gi_modules):
        """Test save dialog delegates to the shared compatibility helper."""
        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage(parent_window=MagicMock())

        with patch("src.ui.preferences.debug_page.save_path_dialog") as mock_save_path_dialog:
            page._show_save_dialog("logs.zip", MagicMock())

        mock_save_path_dialog.assert_called_once()
        call_kwargs = mock_save_path_dialog.call_args.kwargs
        assert call_kwargs["initial_name"] == "logs.zip"
        _clear_src_modules()


class TestDebugPageClear:
    """Test log clear functionality."""

    def test_clear_clicked_no_logs_shows_dialog(self, mock_gi_modules):
        """Test clear button shows dialog when no logs exist."""
        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()
        page._show_simple_dialog = MagicMock()

        with patch("src.ui.preferences.debug_page.get_logging_config") as mock_config:
            mock_logging_config = MagicMock()
            mock_logging_config.get_log_files.return_value = []
            mock_config.return_value = mock_logging_config

            page._on_clear_clicked(None)

            page._show_simple_dialog.assert_called_once()
            args = page._show_simple_dialog.call_args[0]
            assert "No Logs" in args[0]

        _clear_src_modules()

    def test_clear_clicked_with_logs_shows_confirmation(self, mock_gi_modules):
        """Test clear button shows confirmation when logs exist."""
        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()
        page._show_clear_confirmation_dialog = MagicMock()

        with patch("src.ui.preferences.debug_page.get_logging_config") as mock_config:
            mock_logging_config = MagicMock()
            mock_logging_config.get_log_files.return_value = [MagicMock()]
            mock_logging_config.get_total_log_size.return_value = 1000
            mock_config.return_value = mock_logging_config

            page._on_clear_clicked(None)

            # Should call the confirmation dialog method
            page._show_clear_confirmation_dialog.assert_called_once()

        _clear_src_modules()


class TestDebugPageDoClearLogs:
    """Test actual log clearing."""

    def test_do_clear_logs_success(self, mock_gi_modules):
        """Test successful log clearing."""
        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()
        page._show_toast = MagicMock()
        page._update_log_size_display = MagicMock()

        mock_dialog = MagicMock()

        with patch("src.ui.preferences.debug_page.get_logging_config") as mock_config:
            mock_logging_config = MagicMock()
            mock_logging_config.clear_logs.return_value = True
            mock_config.return_value = mock_logging_config

            page._do_clear_logs(mock_dialog)

            mock_dialog.close.assert_called_once()
            mock_logging_config.clear_logs.assert_called_once()
            page._update_log_size_display.assert_called_once()

        _clear_src_modules()

    def test_do_clear_logs_failure(self, mock_gi_modules):
        """Test failed log clearing."""
        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()
        page._show_simple_dialog = MagicMock()
        page._update_log_size_display = MagicMock()

        mock_dialog = MagicMock()

        with patch("src.ui.preferences.debug_page.get_logging_config") as mock_config:
            mock_logging_config = MagicMock()
            mock_logging_config.clear_logs.return_value = False
            mock_config.return_value = mock_logging_config

            page._do_clear_logs(mock_dialog)

            mock_dialog.close.assert_called_once()
            page._show_simple_dialog.assert_called_once()
            args = page._show_simple_dialog.call_args[0]
            assert "Failed" in args[0]

        _clear_src_modules()


class TestDebugPageSystemInfo:
    """Test system information functionality."""

    def test_get_installation_type_returns_string(self, mock_gi_modules):
        """Test that _get_installation_type returns a non-empty string."""
        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()
        install_type = page._get_installation_type()

        assert isinstance(install_type, str)
        assert len(install_type) > 0

        _clear_src_modules()

    def test_get_distro_info_returns_string(self, mock_gi_modules):
        """Test that _get_distro_info returns a non-empty string."""
        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()
        distro = page._get_distro_info()

        assert isinstance(distro, str)
        assert len(distro) > 0

        _clear_src_modules()

    def test_get_desktop_environment_returns_string(self, mock_gi_modules):
        """Test that _get_desktop_environment returns a string."""
        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()
        desktop = page._get_desktop_environment()

        assert isinstance(desktop, str)
        # May be "Unknown" but should never be empty
        assert len(desktop) > 0

        _clear_src_modules()

    def test_create_system_info_group(self, mock_gi_modules):
        """Test that _create_system_info_group creates a group with rows."""
        adw = mock_gi_modules["adw"]
        mock_group = MagicMock()
        adw.PreferencesGroup.return_value = mock_group

        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()
        with patch("src.ui.preferences.debug_page.threading"):
            page._create_system_info_group()

        # Should set title
        mock_group.set_title.assert_called_with("System Information")
        # Should add multiple rows
        assert mock_group.add.call_count >= 5

        _clear_src_modules()


class TestDebugPageAsyncInstallationType:
    """Tests for asynchronous installation type detection."""

    def test_create_system_info_group_does_not_call_get_installation_type_sync(
        self, mock_gi_modules
    ):
        """Test that _create_system_info_group does NOT call _get_installation_type synchronously."""
        adw = mock_gi_modules["adw"]
        mock_group = MagicMock()
        adw.PreferencesGroup.return_value = mock_group

        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()
        with patch.object(page, "_get_installation_type") as mock_get_install:
            with patch("src.ui.preferences.debug_page.threading"):
                page._create_system_info_group()

            # Should NOT be called synchronously during group creation
            mock_get_install.assert_not_called()

        _clear_src_modules()

    def test_create_system_info_group_starts_background_thread(self, mock_gi_modules):
        """Test that _create_system_info_group starts a background thread."""
        adw = mock_gi_modules["adw"]
        mock_group = MagicMock()
        adw.PreferencesGroup.return_value = mock_group

        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()
        with patch("src.ui.preferences.debug_page.threading") as mock_threading:
            mock_thread = MagicMock()
            mock_threading.Thread.return_value = mock_thread

            page._create_system_info_group()

            # Should have created and started a daemon thread
            mock_threading.Thread.assert_called_once()
            call_kwargs = mock_threading.Thread.call_args[1]
            assert call_kwargs.get("daemon") is True
            mock_thread.start.assert_called_once()

        _clear_src_modules()

    def test_create_system_info_group_shows_loading_initially(self, mock_gi_modules):
        """Test that install row shows a loading message initially."""
        adw = mock_gi_modules["adw"]
        mock_group = MagicMock()
        adw.PreferencesGroup.return_value = mock_group

        # Track ActionRow instances to find the install row
        action_rows = []

        def make_action_row():
            row = MagicMock()
            action_rows.append(row)
            return row

        adw.ActionRow.side_effect = make_action_row

        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()
        with patch("src.ui.preferences.debug_page.threading"):
            page._create_system_info_group()

        # The first ActionRow created should be the install row
        # Find the row that had set_title called with "Installation Type"
        install_row = None
        for row in action_rows:
            for call in row.set_title.call_args_list:
                if call[0][0] == "Installation Type":
                    install_row = row
                    break

        assert install_row is not None, "Installation Type row not found"
        install_row.set_subtitle.assert_called()
        initial_subtitle = install_row.set_subtitle.call_args_list[0][0][0]
        assert "Detecting" in initial_subtitle or "detecting" in initial_subtitle

        _clear_src_modules()

    def test_installation_type_background_updates_via_idle_add(self, mock_gi_modules):
        """Test that background installation type check updates via GLib.idle_add."""
        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()
        mock_install_row = MagicMock()
        page._install_type_row = mock_install_row

        with patch.object(page, "_get_installation_type", return_value="Debian/Ubuntu Package"):
            with patch("src.ui.preferences.debug_page.GLib.idle_add") as mock_idle_add:
                page._detect_installation_type_background()

                # Should schedule UI update via GLib.idle_add
                mock_idle_add.assert_called_once()

        _clear_src_modules()

    def test_installation_type_ui_update_sets_subtitle(self, mock_gi_modules):
        """Test that the UI update callback sets the correct subtitle."""
        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()
        mock_install_row = MagicMock()
        page._install_type_row = mock_install_row

        # Call the UI update method directly
        result = page._update_installation_type_ui("Flatpak")

        mock_install_row.set_subtitle.assert_called_with("Flatpak")
        assert result is False  # GLib.idle_add callback must return False

        _clear_src_modules()

    def test_installation_type_ui_update_handles_destroyed_widget(self, mock_gi_modules):
        """Test that UI update handles destroyed widget gracefully."""
        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()
        page._install_type_row = None  # Simulate destroyed widget

        # Should not raise
        result = page._update_installation_type_ui("Flatpak")
        assert result is False

        _clear_src_modules()


class TestDebugPageShowToast:
    """Test toast notification functionality."""

    def test_show_toast_with_toast_support(self, mock_gi_modules):
        """Test show_toast when parent supports toasts."""
        adw = mock_gi_modules["adw"]
        mock_toast = MagicMock()
        adw.Toast.new.return_value = mock_toast

        from src.ui.preferences.debug_page import DebugPage

        parent_window = MagicMock()
        parent_window.add_toast = MagicMock()

        page = DebugPage(parent_window=parent_window)
        page._show_toast("Test message")

        adw.Toast.new.assert_called_with("Test message")
        parent_window.add_toast.assert_called_with(mock_toast)

        _clear_src_modules()

    def test_show_toast_without_parent(self, mock_gi_modules):
        """Test show_toast when no parent window."""
        from src.ui.preferences.debug_page import DebugPage

        page = DebugPage()
        # Should not raise even without parent
        page._show_toast("Test message")

        _clear_src_modules()
