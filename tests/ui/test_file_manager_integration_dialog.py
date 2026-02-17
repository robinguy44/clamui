# ClamUI File Manager Integration Dialog Tests
"""Unit tests for the FileManagerIntegrationDialog class."""

from unittest import mock


class TestFileManagerIntegrationDialog:
    """Tests for FileManagerIntegrationDialog class."""

    def test_dialog_initialization(self, mock_gi_modules):
        """Test dialog initializes correctly."""
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        mock_settings = mock.MagicMock()

        dialog = FileManagerIntegrationDialog(
            settings_manager=mock_settings,
            on_complete=lambda: None,
        )

        assert dialog._settings_manager == mock_settings
        assert dialog._on_complete is not None

    def test_dialog_title_set(self, mock_gi_modules):
        """Test dialog sets correct title."""
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        dialog = FileManagerIntegrationDialog()

        dialog.set_title.assert_called_with("File Manager Integration")

    def test_dialog_dimensions(self, mock_gi_modules):
        """Test dialog sets correct dimensions."""
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        dialog = FileManagerIntegrationDialog()

        # Adw.Window uses set_default_size instead of set_content_width/height
        dialog.set_default_size.assert_called_with(500, 450)

    def test_on_cancel_saves_preference(self, mock_gi_modules):
        """Test cancel button saves 'prompted' preference."""
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        mock_settings = mock.MagicMock()
        completed = []

        dialog = FileManagerIntegrationDialog(
            settings_manager=mock_settings,
            on_complete=lambda: completed.append(True),
        )

        dialog._on_cancel_clicked(mock.MagicMock())

        # Should set prompted to True
        mock_settings.set.assert_called_with("file_manager_integration_prompted", True)

    def test_on_apply_installs_new_integrations(self, mock_gi_modules):
        """Test apply button installs toggled-on integrations that were not installed."""
        from src.core.file_manager_integration import FileManager, IntegrationStatus
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        mock_settings = mock.MagicMock()

        with mock.patch(
            "src.ui.file_manager_integration_dialog.install_integration"
        ) as mock_install:
            mock_install.return_value = (True, None)

            dialog = FileManagerIntegrationDialog(settings_manager=mock_settings)

            # Create mock switch row that is active
            mock_row = mock.MagicMock()
            mock_row.get_active.return_value = True

            dialog._integration_rows = {FileManager.NEMO: mock_row}
            dialog._original_status = {FileManager.NEMO: IntegrationStatus.NOT_INSTALLED}

            dialog._on_apply_clicked(mock.MagicMock())

            mock_install.assert_called_once_with(FileManager.NEMO)

    def test_on_apply_removes_toggled_off_integrations(self, mock_gi_modules):
        """Test apply button removes integrations that were toggled off."""
        from src.core.file_manager_integration import FileManager, IntegrationStatus
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        mock_settings = mock.MagicMock()

        with mock.patch("src.ui.file_manager_integration_dialog.remove_integration") as mock_remove:
            mock_remove.return_value = (True, None)

            dialog = FileManagerIntegrationDialog(settings_manager=mock_settings)

            # Create mock switch row that is NOT active (toggled off)
            mock_row = mock.MagicMock()
            mock_row.get_active.return_value = False

            dialog._integration_rows = {FileManager.NEMO: mock_row}
            dialog._original_status = {FileManager.NEMO: IntegrationStatus.INSTALLED}

            dialog._on_apply_clicked(mock.MagicMock())

            mock_remove.assert_called_once_with(FileManager.NEMO)

    def test_on_apply_repairs_partial_integrations(self, mock_gi_modules):
        """Test apply button repairs partial integrations that are toggled on."""
        from src.core.file_manager_integration import FileManager, IntegrationStatus
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        mock_settings = mock.MagicMock()

        with mock.patch("src.ui.file_manager_integration_dialog.repair_integration") as mock_repair:
            mock_repair.return_value = (True, None)

            dialog = FileManagerIntegrationDialog(settings_manager=mock_settings)

            # Create mock switch row that is active
            mock_row = mock.MagicMock()
            mock_row.get_active.return_value = True

            dialog._integration_rows = {FileManager.NEMO: mock_row}
            dialog._original_status = {FileManager.NEMO: IntegrationStatus.PARTIAL}

            dialog._on_apply_clicked(mock.MagicMock())

            mock_repair.assert_called_once_with(FileManager.NEMO)

    def test_on_apply_removes_partial_when_toggled_off(self, mock_gi_modules):
        """Test apply removes partial integration when user toggles it off."""
        from src.core.file_manager_integration import FileManager, IntegrationStatus
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        mock_settings = mock.MagicMock()

        with mock.patch("src.ui.file_manager_integration_dialog.remove_integration") as mock_remove:
            mock_remove.return_value = (True, None)

            dialog = FileManagerIntegrationDialog(settings_manager=mock_settings)

            mock_row = mock.MagicMock()
            mock_row.get_active.return_value = False

            dialog._integration_rows = {FileManager.NEMO: mock_row}
            dialog._original_status = {FileManager.NEMO: IntegrationStatus.PARTIAL}

            dialog._on_apply_clicked(mock.MagicMock())

            mock_remove.assert_called_once_with(FileManager.NEMO)

    def test_on_apply_noop_for_installed_and_active(self, mock_gi_modules):
        """Test apply does nothing for already-installed integrations that stay on."""
        from src.core.file_manager_integration import FileManager, IntegrationStatus
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        mock_settings = mock.MagicMock()

        with (
            mock.patch(
                "src.ui.file_manager_integration_dialog.install_integration"
            ) as mock_install,
            mock.patch("src.ui.file_manager_integration_dialog.remove_integration") as mock_remove,
            mock.patch("src.ui.file_manager_integration_dialog.repair_integration") as mock_repair,
        ):
            dialog = FileManagerIntegrationDialog(settings_manager=mock_settings)

            mock_row = mock.MagicMock()
            mock_row.get_active.return_value = True

            dialog._integration_rows = {FileManager.NEMO: mock_row}
            dialog._original_status = {FileManager.NEMO: IntegrationStatus.INSTALLED}

            dialog._on_apply_clicked(mock.MagicMock())

            mock_install.assert_not_called()
            mock_remove.assert_not_called()
            mock_repair.assert_not_called()

    def test_on_apply_skips_unchecked_not_installed(self, mock_gi_modules):
        """Test apply does nothing for not-installed integrations that stay off."""
        from src.core.file_manager_integration import FileManager, IntegrationStatus
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        mock_settings = mock.MagicMock()

        with mock.patch(
            "src.ui.file_manager_integration_dialog.install_integration"
        ) as mock_install:
            dialog = FileManagerIntegrationDialog(settings_manager=mock_settings)

            mock_row = mock.MagicMock()
            mock_row.get_active.return_value = False

            dialog._integration_rows = {FileManager.NEMO: mock_row}
            dialog._original_status = {FileManager.NEMO: IntegrationStatus.NOT_INSTALLED}

            dialog._on_apply_clicked(mock.MagicMock())

            mock_install.assert_not_called()

    def test_installed_row_stays_sensitive(self, mock_gi_modules):
        """Test that installed integration rows remain interactive (no set_sensitive(False))."""
        from src.core.file_manager_integration import (
            FileManager,
            IntegrationInfo,
            IntegrationStatus,
        )
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        with mock.patch("src.ui.file_manager_integration_dialog.create_switch_row") as mock_create:
            mock_row = mock.MagicMock()
            mock_create.return_value = mock_row

            dialog = FileManagerIntegrationDialog()

            integration = IntegrationInfo(
                file_manager=FileManager.NEMO,
                display_name="Nemo",
                description="Linux Mint / Cinnamon file manager",
                source_files=[],
                status=IntegrationStatus.INSTALLED,
                is_available=True,
            )

            row = dialog._create_file_manager_row(integration)

            # Row should be active (toggled on)
            row.set_active.assert_called_with(True)
            # Row should NOT be set insensitive
            row.set_sensitive.assert_not_called()

    def test_partial_row_shows_repair_subtitle(self, mock_gi_modules):
        """Test that partial integration rows show repair-needed subtitle."""
        from src.core.file_manager_integration import (
            FileManager,
            IntegrationInfo,
            IntegrationStatus,
        )
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        dialog = FileManagerIntegrationDialog()

        integration = IntegrationInfo(
            file_manager=FileManager.NAUTILUS,
            display_name="Nautilus",
            description="GNOME Files",
            source_files=[],
            status=IntegrationStatus.PARTIAL,
            is_available=True,
            missing_files=["nautilus/scripts/Scan with ClamUI"],
        )

        row = dialog._create_file_manager_row(integration)

        # Check that set_subtitle was called with repair text
        subtitle_text = str(row.set_subtitle.call_args)
        assert "incomplete" in subtitle_text or "repair" in subtitle_text

    def test_get_file_manager_icon_nemo(self, mock_gi_modules):
        """Test returns correct icon for Nemo."""
        from src.core.file_manager_integration import FileManager
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        dialog = FileManagerIntegrationDialog()

        icon = dialog._get_file_manager_icon(FileManager.NEMO)
        assert icon == "folder-symbolic"

    def test_get_file_manager_icon_nautilus(self, mock_gi_modules):
        """Test returns correct icon for Nautilus."""
        from src.core.file_manager_integration import FileManager
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        dialog = FileManagerIntegrationDialog()

        icon = dialog._get_file_manager_icon(FileManager.NAUTILUS)
        assert icon == "folder-symbolic"

    def test_get_file_manager_icon_dolphin(self, mock_gi_modules):
        """Test returns correct icon for Dolphin."""
        from src.core.file_manager_integration import FileManager
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        dialog = FileManagerIntegrationDialog()

        icon = dialog._get_file_manager_icon(FileManager.DOLPHIN)
        assert icon == "folder-symbolic"

    def test_on_complete_callback_called(self, mock_gi_modules):
        """Test on_complete callback is called after dialog closes."""
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        mock_settings = mock.MagicMock()
        completed = []

        dialog = FileManagerIntegrationDialog(
            settings_manager=mock_settings,
            on_complete=lambda: completed.append(True),
        )

        dialog._save_preference_and_close()

        assert len(completed) == 1

    def test_show_toast(self, mock_gi_modules):
        """Test toast notification is shown."""
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        dialog = FileManagerIntegrationDialog()

        dialog._show_toast("Test message")

        # Verify add_toast was called on the toast overlay
        dialog._toast_overlay.add_toast.assert_called_once()

    def test_original_status_tracked(self, mock_gi_modules):
        """Test that _original_status dict is populated during init."""
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        dialog = FileManagerIntegrationDialog()

        # _original_status should be a dict (may be empty if no integrations available)
        assert isinstance(dialog._original_status, dict)
