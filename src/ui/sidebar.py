# ClamUI Navigation Sidebar
"""
GNOME Settings-style navigation sidebar for ClamUI.

This module provides the navigation sidebar component used in the main window
layout. It follows the GNOME Settings pattern with icons and labels for
each view, using libadwaita's navigation-sidebar CSS class.
"""

import logging
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk

from ..core.i18n import N_, _
from .utils import resolve_icon_name

logger = logging.getLogger(__name__)

# Navigation items configuration
# (view_id, icon_name, display_label)
NAVIGATION_ITEMS = [
    ("scan", "folder-symbolic", N_("Scan")),
    ("update", "software-update-available-symbolic", N_("Database")),
    ("logs", "document-open-recent-symbolic", N_("Logs")),
    ("components", "applications-system-symbolic", N_("Components")),
    ("quarantine", "security-medium-symbolic", N_("Quarantine")),
    ("statistics", "applications-science-symbolic", N_("Statistics")),
    ("audit", "security-high-symbolic", N_("Audit")),
]


class SidebarRow(Gtk.ListBoxRow):
    """
    A navigation sidebar row with icon and label.

    Each row represents a navigation destination with a consistent
    GNOME Settings-style appearance.
    """

    def __init__(self, view_id: str, icon_name: str, label: str):
        """
        Initialize a sidebar row.

        Args:
            view_id: Identifier for the view (e.g., "scan", "logs")
            icon_name: Icon name for the row
            label: Display label for the row
        """
        super().__init__()

        self._view_id = view_id

        # Create horizontal box for icon + label
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        # Icon
        icon = Gtk.Image.new_from_icon_name(resolve_icon_name(icon_name))
        icon.set_icon_size(Gtk.IconSize.NORMAL)
        box.append(icon)

        # Label - translate at display time (labels use N_() for deferred translation)
        label_widget = Gtk.Label(label=_(label))
        label_widget.set_xalign(0)
        label_widget.set_hexpand(True)
        box.append(label_widget)

        self.set_child(box)

    @property
    def view_id(self) -> str:
        """Get the view identifier for this row."""
        return self._view_id


class NavigationSidebar(Gtk.Box):
    """
    Navigation sidebar containing the list of views.

    This component uses the libadwaita navigation-sidebar CSS class
    for proper styling and provides callbacks for view selection.
    """

    def __init__(
        self,
        on_view_selected: Callable[[str], None] | None = None,
    ):
        """
        Initialize the navigation sidebar.

        Args:
            on_view_selected: Callback when a view is selected, receives view_id
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self._on_view_selected = on_view_selected
        self._rows: dict[str, SidebarRow] = {}

        # Set sidebar width
        self.set_size_request(200, -1)

        # Create scrollable container for the list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        self.append(scrolled)

        # Create the list box
        self._list_box = Gtk.ListBox()
        self._list_box.add_css_class("navigation-sidebar")
        self._list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._list_box.connect("row-selected", self._on_row_selected)
        scrolled.set_child(self._list_box)

        # Populate with navigation items
        self._populate_items()

        # Select the first item by default
        first_row = self._list_box.get_row_at_index(0)
        if first_row:
            self._list_box.select_row(first_row)

    def _populate_items(self) -> None:
        """Populate the sidebar with navigation items."""
        for view_id, icon_name, label in NAVIGATION_ITEMS:
            row = SidebarRow(view_id, icon_name, label)
            self._rows[view_id] = row
            self._list_box.append(row)

    def _on_row_selected(self, list_box: Gtk.ListBox, row: SidebarRow | None) -> None:
        """Handle row selection."""
        if row is None:
            return

        view_id = row.view_id
        logger.debug(f"Sidebar: selected view '{view_id}'")

        if self._on_view_selected:
            self._on_view_selected(view_id)

    def select_view(self, view_id: str) -> None:
        """
        Programmatically select a view in the sidebar.

        This updates the visual selection without triggering the callback,
        useful for syncing sidebar state when navigation happens elsewhere.

        Args:
            view_id: The view identifier to select
        """
        if view_id not in self._rows:
            logger.warning(f"Unknown view_id: {view_id}")
            return

        row = self._rows[view_id]

        # Block signal to prevent callback loop
        self._list_box.handler_block_by_func(self._on_row_selected)
        self._list_box.select_row(row)
        self._list_box.handler_unblock_by_func(self._on_row_selected)

    def get_selected_view(self) -> str | None:
        """
        Get the currently selected view identifier.

        Returns:
            The view_id of the selected row, or None if nothing selected
        """
        row = self._list_box.get_selected_row()
        if row and isinstance(row, SidebarRow):
            return row.view_id
        return None

    def get_view_label(self, view_id: str) -> str:
        """
        Get the display label for a view.

        Args:
            view_id: The view identifier

        Returns:
            The display label, or the view_id if not found
        """
        for item in NAVIGATION_ITEMS:
            if item[0] == view_id:
                return _(item[2])
        return view_id.capitalize()
