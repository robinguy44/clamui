# ClamUI Device Scan Page Tests
"""
Tests for the DeviceScanPage preferences component.
"""

import sys
from unittest.mock import MagicMock


def _clear_src_modules():
    """Clear all cached src.* modules to prevent test pollution."""
    modules_to_remove = [mod for mod in sys.modules if mod.startswith("src.")]
    for mod in modules_to_remove:
        del sys.modules[mod]


class TestDeviceScanPageImport:
    """Test that DeviceScanPage can be imported correctly."""

    def test_import_device_scan_page(self, mock_gi_modules):
        """Test that DeviceScanPage can be imported."""
        from src.ui.preferences.device_scan_page import DeviceScanPage

        assert DeviceScanPage is not None
        _clear_src_modules()


class TestDeviceScanPageInit:
    """Test DeviceScanPage initialization."""

    def test_init_with_settings_manager(self, mock_gi_modules):
        """Test initialization with settings manager."""
        settings_manager = MagicMock()

        from src.ui.preferences.device_scan_page import DeviceScanPage

        page = DeviceScanPage(settings_manager=settings_manager)

        assert page._settings_manager is settings_manager
        _clear_src_modules()

    def test_init_without_settings_manager(self, mock_gi_modules):
        """Test initialization without settings manager."""
        from src.ui.preferences.device_scan_page import DeviceScanPage

        page = DeviceScanPage()

        assert page._settings_manager is None
        _clear_src_modules()

    def test_init_widget_references_none(self, mock_gi_modules):
        """Test that widget references start as None."""
        from src.ui.preferences.device_scan_page import DeviceScanPage

        page = DeviceScanPage()

        assert page._enable_row is None
        assert page._max_size_spin is None
        assert page._delay_spin is None
        assert page._quarantine_row is None
        assert page._notify_row is None
        assert page._battery_row is None
        _clear_src_modules()


class TestCreatePage:
    """Test page creation."""

    def test_create_page_returns_preferences_page(self, mock_gi_modules):
        """Test that create_page returns an Adw.PreferencesPage."""
        adw = mock_gi_modules["adw"]
        mock_page = MagicMock()
        adw.PreferencesPage.return_value = mock_page

        settings_manager = MagicMock()
        settings_manager.get.side_effect = lambda key, default=None: {
            "device_auto_scan_enabled": False,
            "device_auto_scan_types": ["removable", "external"],
            "device_auto_scan_max_size_gb": 32,
            "device_auto_scan_delay_seconds": 3,
            "device_auto_scan_auto_quarantine": False,
            "device_auto_scan_notify": True,
            "device_auto_scan_skip_on_battery": True,
        }.get(key, default)

        from src.ui.preferences.device_scan_page import DeviceScanPage

        instance = DeviceScanPage(settings_manager=settings_manager)
        instance.create_page()

        # PreferencesPage was called to create the page
        adw.PreferencesPage.assert_called_once()
        # Groups were added to the page (general, device types, options)
        assert mock_page.add.call_count == 3
        _clear_src_modules()

    def test_create_page_creates_three_device_type_rows(self, mock_gi_modules):
        """Test that three device type switch rows are created."""
        settings_manager = MagicMock()
        settings_manager.get.side_effect = lambda key, default=None: {
            "device_auto_scan_enabled": False,
            "device_auto_scan_types": ["removable"],
            "device_auto_scan_max_size_gb": 32,
            "device_auto_scan_delay_seconds": 3,
            "device_auto_scan_auto_quarantine": False,
            "device_auto_scan_notify": True,
            "device_auto_scan_skip_on_battery": True,
        }.get(key, default)

        from src.ui.preferences.device_scan_page import DeviceScanPage

        instance = DeviceScanPage(settings_manager=settings_manager)
        instance.create_page()

        # Should have 3 device type rows
        assert len(instance._type_rows) == 3
        assert "removable" in instance._type_rows
        assert "external" in instance._type_rows
        assert "network" in instance._type_rows
        _clear_src_modules()


class TestSettingsPersistence:
    """Test that settings are saved when widgets change."""

    def test_enable_toggle_saves(self, mock_gi_modules):
        """Test that toggling enable saves the setting."""
        settings_manager = MagicMock()
        settings_manager.get.side_effect = lambda key, default=None: {
            "device_auto_scan_enabled": False,
            "device_auto_scan_types": ["removable", "external"],
            "device_auto_scan_max_size_gb": 32,
            "device_auto_scan_delay_seconds": 3,
            "device_auto_scan_auto_quarantine": False,
            "device_auto_scan_notify": True,
            "device_auto_scan_skip_on_battery": True,
        }.get(key, default)

        from src.ui.preferences.device_scan_page import DeviceScanPage

        instance = DeviceScanPage(settings_manager=settings_manager)
        instance.create_page()

        # Simulate toggle
        mock_row = MagicMock()
        mock_row.get_active.return_value = True
        instance._on_enable_changed(mock_row, None)

        settings_manager.set.assert_called_with("device_auto_scan_enabled", True)
        _clear_src_modules()

    def test_max_size_change_saves(self, mock_gi_modules):
        """Test that changing max size saves the setting."""
        settings_manager = MagicMock()
        settings_manager.get.return_value = 32

        from src.ui.preferences.device_scan_page import DeviceScanPage

        instance = DeviceScanPage(settings_manager=settings_manager)

        mock_spin = MagicMock()
        mock_spin.get_value.return_value = 64
        instance._on_max_size_changed(mock_spin)

        settings_manager.set.assert_called_with("device_auto_scan_max_size_gb", 64)
        _clear_src_modules()

    def test_delay_change_saves(self, mock_gi_modules):
        """Test that changing delay saves the setting."""
        settings_manager = MagicMock()
        settings_manager.get.return_value = 3

        from src.ui.preferences.device_scan_page import DeviceScanPage

        instance = DeviceScanPage(settings_manager=settings_manager)

        mock_spin = MagicMock()
        mock_spin.get_value.return_value = 10
        instance._on_delay_changed(mock_spin)

        settings_manager.set.assert_called_with("device_auto_scan_delay_seconds", 10)
        _clear_src_modules()

    def test_quarantine_toggle_saves(self, mock_gi_modules):
        """Test that toggling auto-quarantine saves the setting."""
        settings_manager = MagicMock()
        settings_manager.get.return_value = False

        from src.ui.preferences.device_scan_page import DeviceScanPage

        instance = DeviceScanPage(settings_manager=settings_manager)

        mock_row = MagicMock()
        mock_row.get_active.return_value = True
        instance._on_quarantine_changed(mock_row, None)

        settings_manager.set.assert_called_with("device_auto_scan_auto_quarantine", True)
        _clear_src_modules()

    def test_no_save_without_settings_manager(self, mock_gi_modules):
        """Test that handlers are safe when no settings manager is set."""
        from src.ui.preferences.device_scan_page import DeviceScanPage

        instance = DeviceScanPage()  # No settings_manager

        # These should not raise
        mock_row = MagicMock()
        mock_row.get_active.return_value = True
        instance._on_enable_changed(mock_row, None)
        instance._on_quarantine_changed(mock_row, None)
        instance._on_notify_changed(mock_row, None)
        instance._on_battery_changed(mock_row, None)

        mock_spin = MagicMock()
        mock_spin.get_value.return_value = 5
        instance._on_max_size_changed(mock_spin)
        instance._on_delay_changed(mock_spin)
        _clear_src_modules()
