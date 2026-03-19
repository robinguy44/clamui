# ProfileSelector Tests
"""
Unit tests for the ProfileSelector component.

Tests cover:
- Profile list refresh from ProfileManager
- Profile selection by ID (found/not found)
- Dropdown index mapping (0 = No Profile, 1+ = profiles)
- Profile exclusions extraction
- Selected profile property
- Dropdown change handling (profile selection, deselection)
- Profile not found returns False
- Empty profile list handling
"""

import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_gi_for_selector(mock_gi_modules):
    """Extended GTK mock for ProfileSelector which uses GObject signals."""
    adw = mock_gi_modules["adw"]

    # ProfileSelector inherits Adw.PreferencesGroup
    # We need a real-ish class for it
    adw.PreferencesGroup = type(
        "MockPreferencesGroup",
        (),
        {
            "__init__": lambda self, *a, **kw: None,
            "set_title": MagicMock(),
            "add": MagicMock(),
            "set_header_suffix": MagicMock(),
        },
    )

    # GObject for signal registration
    mock_gobject = MagicMock()
    mock_gobject.type_register = MagicMock()
    mock_gobject.signal_new = MagicMock()
    mock_gobject.SignalFlags = MagicMock()
    mock_gobject.SignalFlags.RUN_FIRST = 1

    mock_gi_modules["repository"].GObject = mock_gobject

    with patch.dict(
        sys.modules,
        {
            "gi.repository.GObject": mock_gobject,
        },
    ):
        yield mock_gi_modules


def _make_profile(profile_id, name, targets=None, exclusions=None, is_default=False):
    """Create a mock ScanProfile."""
    profile = MagicMock()
    profile.id = profile_id
    profile.name = name
    profile.targets = targets or []
    profile.exclusions = exclusions or {}
    profile.is_default = is_default
    return profile


@pytest.fixture
def profile_manager():
    """Create a mock ProfileManager."""
    pm = MagicMock()
    pm.list_profiles.return_value = []
    return pm


@pytest.fixture
def selector_instance(mock_gi_for_selector, profile_manager):
    """Create a ProfileSelector instance with mocked GTK.

    Uses object.__new__ to bypass GTK widget __init__, then manually
    sets the attributes that would be created by _setup_ui.
    """
    # Clear cached module
    for mod_name in list(sys.modules.keys()):
        if "src.ui.scan.profile_selector" in mod_name:
            del sys.modules[mod_name]

    # Also clear parent module dependencies
    for mod_name in list(sys.modules.keys()):
        if "src.ui.profile_dialogs" in mod_name or "src.ui.utils" in mod_name:
            del sys.modules[mod_name]

    # Mock the imports that profile_selector.py uses
    with patch.dict(
        sys.modules,
        {
            "src.ui.profile_dialogs": MagicMock(),
            "src.ui.utils": MagicMock(),
        },
    ):
        from src.ui.scan.profile_selector import ProfileSelector

        # Create instance bypassing GTK widget init
        instance = object.__new__(ProfileSelector)

        # Set up attributes that _setup_ui would create
        instance._get_profile_manager = lambda: profile_manager
        instance._profile_list = []
        instance._selected_profile = None
        instance._string_list = MagicMock()
        instance._dropdown = MagicMock()
        instance._dropdown.get_selected.return_value = 0

        # Mock emit for signal testing
        instance.emit = MagicMock()

        yield instance


# =============================================================================
# Profile Selection by ID
# =============================================================================


class TestSetSelectedProfile:
    """Tests for set_selected_profile method."""

    def test_select_existing_profile(self, selector_instance):
        """Should select profile by ID and return True."""
        p1 = _make_profile("p1", "Quick Scan")
        p2 = _make_profile("p2", "Full Scan")
        selector_instance._profile_list = [p1, p2]

        result = selector_instance.set_selected_profile("p2")

        assert result is True
        assert selector_instance._selected_profile is p2
        # Dropdown index should be 2 (index 0 = "No Profile", 1 = p1, 2 = p2)
        selector_instance._dropdown.set_selected.assert_called_with(2)

    def test_select_first_profile(self, selector_instance):
        """Should correctly select the first profile (index 1)."""
        p1 = _make_profile("p1", "Quick Scan")
        selector_instance._profile_list = [p1]

        result = selector_instance.set_selected_profile("p1")

        assert result is True
        selector_instance._dropdown.set_selected.assert_called_with(1)

    def test_select_nonexistent_profile(self, selector_instance):
        """Should return False when profile ID not found."""
        p1 = _make_profile("p1", "Quick Scan")
        selector_instance._profile_list = [p1]

        result = selector_instance.set_selected_profile("nonexistent")

        assert result is False

    def test_select_from_empty_list(self, selector_instance):
        """Should return False when profile list is empty."""
        selector_instance._profile_list = []

        result = selector_instance.set_selected_profile("any-id")

        assert result is False


# =============================================================================
# Selected Profile Property
# =============================================================================


class TestSelectedProfileProperty:
    """Tests for the selected_profile property."""

    def test_initially_none(self, selector_instance):
        """selected_profile should be None initially."""
        assert selector_instance.selected_profile is None

    def test_after_selection(self, selector_instance):
        """selected_profile should return the selected profile."""
        p1 = _make_profile("p1", "Quick Scan")
        selector_instance._profile_list = [p1]
        selector_instance.set_selected_profile("p1")

        assert selector_instance.selected_profile is p1


# =============================================================================
# Exclusions
# =============================================================================


class TestGetExclusions:
    """Tests for get_exclusions method."""

    def test_no_profile_returns_none(self, selector_instance):
        """Should return None when no profile is selected."""
        selector_instance._selected_profile = None
        assert selector_instance.get_exclusions() is None

    def test_profile_with_exclusions(self, selector_instance):
        """Should return exclusion paths and patterns from profile."""
        profile = _make_profile(
            "p1",
            "Custom",
            exclusions={
                "paths": ["/skip/this"],
                "patterns": ["*.log", "*.tmp"],
            },
        )
        selector_instance._selected_profile = profile

        result = selector_instance.get_exclusions()

        assert result == {
            "paths": ["/skip/this"],
            "patterns": ["*.log", "*.tmp"],
        }

    def test_profile_with_empty_exclusions(self, selector_instance):
        """Should return empty lists when profile has no exclusions."""
        profile = _make_profile("p1", "Custom", exclusions={})
        selector_instance._selected_profile = profile

        result = selector_instance.get_exclusions()

        assert result == {"paths": [], "patterns": []}

    def test_profile_with_partial_exclusions(self, selector_instance):
        """Should handle profiles with only paths or only patterns."""
        profile = _make_profile(
            "p1",
            "Custom",
            exclusions={"paths": ["/skip"]},
        )
        selector_instance._selected_profile = profile

        result = selector_instance.get_exclusions()

        assert result["paths"] == ["/skip"]
        assert result["patterns"] == []


# =============================================================================
# Dropdown Change Handling
# =============================================================================


class TestDropdownChangeHandling:
    """Tests for _on_dropdown_changed method."""

    def test_selecting_no_profile_index_0(self, selector_instance):
        """Index 0 means 'No Profile (Manual)' - should clear selection."""
        p1 = _make_profile("p1", "Quick Scan")
        selector_instance._profile_list = [p1]
        selector_instance._selected_profile = p1  # Was selected

        dropdown_mock = MagicMock()
        dropdown_mock.get_selected.return_value = 0

        selector_instance._on_dropdown_changed(dropdown_mock, None)

        assert selector_instance._selected_profile is None
        selector_instance.emit.assert_any_call("profile-selected", None)

    def test_selecting_profile_index_1(self, selector_instance):
        """Index 1 means first profile in list."""
        p1 = _make_profile("p1", "Quick Scan", targets=["/home"])
        selector_instance._profile_list = [p1]

        dropdown_mock = MagicMock()
        dropdown_mock.get_selected.return_value = 1

        selector_instance._on_dropdown_changed(dropdown_mock, None)

        assert selector_instance._selected_profile is p1
        selector_instance.emit.assert_any_call("profile-selected", p1)
        # Profile has targets, so targets-changed should fire
        selector_instance.emit.assert_any_call("targets-changed", ["/home"])

    def test_selecting_profile_without_targets(self, selector_instance):
        """Profile without targets should not emit targets-changed."""
        p1 = _make_profile("p1", "Custom", targets=[])
        selector_instance._profile_list = [p1]

        dropdown_mock = MagicMock()
        dropdown_mock.get_selected.return_value = 1

        selector_instance._on_dropdown_changed(dropdown_mock, None)

        # Should emit profile-selected but NOT targets-changed
        calls = [c[0][0] for c in selector_instance.emit.call_args_list]
        assert "profile-selected" in calls
        assert "targets-changed" not in calls

    def test_selecting_out_of_range_index(self, selector_instance):
        """Out-of-range index should be silently ignored."""
        p1 = _make_profile("p1", "Quick Scan")
        selector_instance._profile_list = [p1]

        dropdown_mock = MagicMock()
        dropdown_mock.get_selected.return_value = 99  # Way out of range

        # Should not raise
        selector_instance._on_dropdown_changed(dropdown_mock, None)

    def test_selecting_second_profile(self, selector_instance):
        """Index 2 should select the second profile."""
        p1 = _make_profile("p1", "Quick Scan")
        p2 = _make_profile("p2", "Full Scan", targets=["/"])
        selector_instance._profile_list = [p1, p2]

        dropdown_mock = MagicMock()
        dropdown_mock.get_selected.return_value = 2

        selector_instance._on_dropdown_changed(dropdown_mock, None)

        assert selector_instance._selected_profile is p2


# =============================================================================
# Refresh
# =============================================================================


class TestRefresh:
    """Tests for profile list refresh."""

    def test_refresh_loads_profiles(self, selector_instance, profile_manager):
        """refresh should load profiles from ProfileManager."""
        p1 = _make_profile("p1", "Quick Scan")
        p2 = _make_profile("p2", "Full Scan")
        profile_manager.list_profiles.return_value = [p1, p2]

        # Mock string_list to support the while loop (get_n_items > 0)
        selector_instance._string_list.get_n_items.side_effect = [0]

        selector_instance.refresh()

        assert selector_instance._profile_list == [p1, p2]
        profile_manager.list_profiles.assert_called_once()

    def test_refresh_clears_and_repopulates_string_list(self, selector_instance, profile_manager):
        """refresh should rebuild the dropdown items."""
        p1 = _make_profile("p1", "Quick Scan")
        profile_manager.list_profiles.return_value = [p1]

        # Set up string_list mock to track calls
        string_list = MagicMock()
        # Simulate the while loop: first call returns 1, second returns 0
        string_list.get_n_items.side_effect = [1, 0]
        selector_instance._string_list = string_list

        selector_instance.refresh()

        # Should have removed old items and added "No Profile" + profile names
        string_list.remove.assert_called()
        append_calls = [c[0][0] for c in string_list.append.call_args_list]
        assert "No Profile (Manual)" in append_calls
        assert "Quick Scan" in append_calls

    def test_refresh_preserves_selection(self, selector_instance, profile_manager):
        """refresh should re-select the previously selected profile."""
        p1 = _make_profile("p1", "Quick Scan")
        selector_instance._selected_profile = p1  # Currently selected
        profile_manager.list_profiles.return_value = [p1]

        # Mock set_selected_profile to verify it gets called with correct ID
        with patch.object(selector_instance, "set_selected_profile") as mock_set:
            selector_instance._string_list.get_n_items.side_effect = [0]
            selector_instance.refresh()

            mock_set.assert_called_with("p1")

    def test_refresh_no_profile_manager(self, selector_instance):
        """refresh should handle None ProfileManager gracefully."""
        selector_instance._get_profile_manager = lambda: None

        # Should not raise
        selector_instance.refresh()

    def test_refresh_resets_to_no_profile_when_not_selected(
        self, selector_instance, profile_manager
    ):
        """refresh without previous selection should default to index 0."""
        p1 = _make_profile("p1", "Quick Scan")
        profile_manager.list_profiles.return_value = [p1]
        selector_instance._selected_profile = None

        selector_instance._string_list.get_n_items.side_effect = [0]
        selector_instance.refresh()

        selector_instance._dropdown.set_selected.assert_called_with(0)
