# Tests for ClamUI Navigation Sidebar
"""
Unit tests for the navigation sidebar component.
"""


class TestSidebarRow:
    """Tests for SidebarRow class."""

    def test_sidebar_row_creation(self, mock_gi_modules):
        """Test creating a SidebarRow with correct properties."""
        from src.ui.sidebar import SidebarRow

        row = SidebarRow("scan", "folder-symbolic", "Scan")

        assert row.view_id == "scan"

    def test_sidebar_row_view_id_property(self, mock_gi_modules):
        """Test that view_id property returns correct identifier."""
        from src.ui.sidebar import SidebarRow

        row = SidebarRow("logs", "document-open-recent-symbolic", "Logs")

        assert row.view_id == "logs"


class TestNavigationSidebar:
    """Tests for NavigationSidebar class."""

    def test_navigation_sidebar_creation(self, mock_gi_modules):
        """Test creating NavigationSidebar without callback."""
        from src.ui.sidebar import NavigationSidebar

        sidebar = NavigationSidebar()

        # Should create without errors
        assert sidebar is not None

    def test_navigation_sidebar_with_callback(self, mock_gi_modules):
        """Test creating NavigationSidebar with callback."""
        from src.ui.sidebar import NavigationSidebar

        callback_called = []

        def on_select(view_id):
            callback_called.append(view_id)

        sidebar = NavigationSidebar(on_view_selected=on_select)

        assert sidebar is not None

    def test_navigation_sidebar_has_all_views(self, mock_gi_modules):
        """Test that sidebar has all expected navigation items."""
        from src.ui.sidebar import NAVIGATION_ITEMS, NavigationSidebar

        sidebar = NavigationSidebar()

        # Should have rows for all navigation items
        assert len(sidebar._rows) == len(NAVIGATION_ITEMS)

        # Check all expected views are present
        expected_views = [
            "scan",
            "update",
            "logs",
            "components",
            "quarantine",
            "statistics",
        ]
        for view_id in expected_views:
            assert view_id in sidebar._rows

    def test_select_view_updates_selection(self, mock_gi_modules):
        """Test that select_view updates the sidebar selection."""
        from src.ui.sidebar import NavigationSidebar

        sidebar = NavigationSidebar()

        # Select a different view
        sidebar.select_view("logs")

        # The method should complete without error
        # (actual selection state is mocked)

    def test_select_view_with_unknown_view(self, mock_gi_modules):
        """Test that select_view handles unknown view_id gracefully."""
        from src.ui.sidebar import NavigationSidebar

        sidebar = NavigationSidebar()

        # Should not raise exception for unknown view
        sidebar.select_view("unknown_view")

    def test_get_view_label_returns_correct_label(self, mock_gi_modules):
        """Test that get_view_label returns correct display labels."""
        from src.ui.sidebar import NavigationSidebar

        sidebar = NavigationSidebar()

        assert sidebar.get_view_label("scan") == "Scan"
        assert sidebar.get_view_label("update") == "Database"
        assert sidebar.get_view_label("logs") == "Logs"
        assert sidebar.get_view_label("components") == "Components"
        assert sidebar.get_view_label("quarantine") == "Quarantine"
        assert sidebar.get_view_label("statistics") == "Statistics"

    def test_get_view_label_unknown_view(self, mock_gi_modules):
        """Test that get_view_label returns capitalized id for unknown views."""
        from src.ui.sidebar import NavigationSidebar

        sidebar = NavigationSidebar()

        # Unknown view should return capitalized view_id
        assert sidebar.get_view_label("unknown") == "Unknown"


class TestNavigationItems:
    """Tests for NAVIGATION_ITEMS configuration."""

    def test_navigation_items_format(self, mock_gi_modules):
        """Test that NAVIGATION_ITEMS has correct format."""
        from src.ui.sidebar import NAVIGATION_ITEMS

        # Should be a list of tuples
        assert isinstance(NAVIGATION_ITEMS, list)

        # Each item should be (view_id, icon_name, label)
        for item in NAVIGATION_ITEMS:
            assert len(item) == 3
            view_id, icon_name, label = item
            assert isinstance(view_id, str)
            assert isinstance(icon_name, str)
            assert isinstance(label, str)
            assert icon_name.endswith("-symbolic")

    def test_navigation_items_count(self, mock_gi_modules):
        """Test that all expected views are in NAVIGATION_ITEMS."""
        from src.ui.sidebar import NAVIGATION_ITEMS

        # Should have 7 navigation items (including Audit)
        assert len(NAVIGATION_ITEMS) == 7

    def test_navigation_items_order(self, mock_gi_modules):
        """Test that navigation items are in expected order."""
        from src.ui.sidebar import NAVIGATION_ITEMS

        view_ids = [item[0] for item in NAVIGATION_ITEMS]

        expected_order = [
            "scan",
            "update",
            "logs",
            "components",
            "quarantine",
            "statistics",
            "audit",
        ]
        assert view_ids == expected_order
