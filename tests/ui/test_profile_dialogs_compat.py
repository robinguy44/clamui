"""Compatibility-focused tests for profile dialog file chooser paths."""

import sys
from unittest.mock import MagicMock, patch

import pytest


def _clear_src_modules():
    modules_to_remove = [mod for mod in sys.modules if mod.startswith("src.")]
    for mod in modules_to_remove:
        del sys.modules[mod]


@pytest.fixture
def profile_dialog_class(mock_gi_modules):
    from src.ui.profile_dialogs import ProfileDialog

    yield ProfileDialog
    _clear_src_modules()


@pytest.fixture
def profile_list_dialog_class(mock_gi_modules):
    from src.ui.profile_dialogs import ProfileListDialog

    yield ProfileListDialog
    _clear_src_modules()


class TestProfileDialogCompatibility:
    def test_open_file_dialog_uses_compat_helper(self, profile_dialog_class):
        dialog = profile_dialog_class()
        dialog.get_root = MagicMock(return_value=MagicMock())

        with patch("src.ui.profile_dialogs.open_paths_dialog") as mock_open_paths_dialog:
            dialog._open_file_dialog(
                select_folder=True,
                multiple=True,
                callback=MagicMock(),
            )

        mock_open_paths_dialog.assert_called_once()
        call_kwargs = mock_open_paths_dialog.call_args.kwargs
        assert call_kwargs["select_folders"] is True
        assert call_kwargs["multiple"] is True

    def test_add_target_file_uses_multiple_selection(self, profile_dialog_class):
        dialog = profile_dialog_class()

        with patch.object(dialog, "_open_file_dialog") as mock_open:
            dialog._on_add_target_file_clicked(MagicMock())

        mock_open.assert_called_once()
        call_kwargs = mock_open.call_args.kwargs
        assert call_kwargs["select_folder"] is False
        assert call_kwargs["multiple"] is True

    def test_add_exclusion_path_uses_multiple_selection(self, profile_dialog_class):
        dialog = profile_dialog_class()

        with patch.object(dialog, "_open_file_dialog") as mock_open:
            dialog._on_add_exclusion_path_clicked(MagicMock())

        mock_open.assert_called_once()
        call_kwargs = mock_open.call_args.kwargs
        assert call_kwargs["select_folder"] is True
        assert call_kwargs["multiple"] is True


class TestProfileListDialogCompatibility:
    def test_export_profile_uses_compat_save_dialog(self, profile_list_dialog_class):
        dialog = profile_list_dialog_class(profile_manager=MagicMock())
        dialog.get_root = MagicMock(return_value=MagicMock())

        profile = MagicMock()
        profile.id = "profile-1"
        profile.name = "Quick Scan"

        with patch("src.ui.profile_dialogs.save_path_dialog") as mock_save_path_dialog:
            dialog._on_export_profile_clicked(profile)

        mock_save_path_dialog.assert_called_once()
        call_kwargs = mock_save_path_dialog.call_args.kwargs
        assert call_kwargs["initial_name"] == "Quick_Scan.json"

    def test_import_profile_uses_compat_open_dialog(self, profile_list_dialog_class):
        dialog = profile_list_dialog_class(profile_manager=MagicMock())
        dialog.get_root = MagicMock(return_value=MagicMock())

        with patch("src.ui.profile_dialogs.open_paths_dialog") as mock_open_paths_dialog:
            dialog.import_profile()

        mock_open_paths_dialog.assert_called_once()
