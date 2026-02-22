# Profile Selector Component
"""
Profile selector widget for scan configuration.

Single responsibility:
- Display profile dropdown
- Manage profile selection
- Notify parent of profile changes
"""

import logging
from typing import TYPE_CHECKING, Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, GObject, Gtk

from ...core.i18n import _
from ..profile_dialogs import ProfileListDialog
from ..utils import add_row_icon, resolve_icon_name

if TYPE_CHECKING:
    from ...profiles.models import ScanProfile
    from ...profiles.profile_manager import ProfileManager

logger = logging.getLogger(__name__)


class ProfileSelector(Adw.PreferencesGroup):
    """
    Widget for selecting and managing scan profiles.

    Signals:
        profile-selected: Emitted when a profile is selected (profile: ScanProfile | None)
        targets-changed: Emitted when profile targets should be applied (targets: list[str])
        start-scan-requested: Emitted when user wants to start scan from profile dialog
    """

    def __init__(self, get_profile_manager: Callable[[], "ProfileManager | None"]):
        """
        Initialize the profile selector.

        Args:
            get_profile_manager: Callback to get ProfileManager (avoids tight coupling)
        """
        super().__init__()
        self.set_title(_("Scan Profile"))

        self._get_profile_manager = get_profile_manager
        self._profile_list: list[ScanProfile] = []
        self._selected_profile: ScanProfile | None = None

        self._setup_ui()

    def _setup_ui(self):
        """Build the profile selector UI."""
        profile_row = Adw.ActionRow()
        profile_row.set_title(_("Profile"))
        add_row_icon(profile_row, "document-properties-symbolic")

        self._string_list = Gtk.StringList()
        self._string_list.append(_("No Profile (Manual)"))

        self._dropdown = Gtk.DropDown()
        self._dropdown.set_model(self._string_list)
        self._dropdown.set_selected(0)
        self._dropdown.set_valign(Gtk.Align.CENTER)
        self._dropdown.connect("notify::selected", self._on_dropdown_changed)

        manage_btn = Gtk.Button()
        manage_btn.set_icon_name(resolve_icon_name("emblem-system-symbolic"))
        manage_btn.set_tooltip_text(_("Manage profiles"))
        manage_btn.add_css_class("flat")
        manage_btn.set_valign(Gtk.Align.CENTER)
        manage_btn.connect("clicked", self._on_manage_clicked)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_valign(Gtk.Align.CENTER)
        box.append(self._dropdown)
        box.append(manage_btn)

        profile_row.add_suffix(box)
        self.add(profile_row)

        self.connect("realize", lambda w: self.refresh())

    def refresh(self) -> None:
        """Refresh profile list from ProfileManager."""
        profile_manager = self._get_profile_manager()
        if profile_manager is None:
            logger.debug("ProfileManager not available")
            return

        current_id = self._selected_profile.id if self._selected_profile else None

        self._profile_list = profile_manager.list_profiles()

        while self._string_list.get_n_items() > 0:
            self._string_list.remove(0)
        self._string_list.append(_("No Profile (Manual)"))
        for profile in self._profile_list:
            self._string_list.append(profile.name)

        if current_id:
            self.set_selected_profile(current_id)
        else:
            self._dropdown.set_selected(0)

    def _on_dropdown_changed(self, dropdown, pspec):
        """Handle dropdown selection change."""
        idx = dropdown.get_selected()

        if idx == 0:
            self._selected_profile = None
            self.emit("profile-selected", None)
        elif 0 < idx <= len(self._profile_list):
            self._selected_profile = self._profile_list[idx - 1]
            self.emit("profile-selected", self._selected_profile)

            if self._selected_profile.targets:
                self.emit("targets-changed", self._selected_profile.targets)

    def _on_manage_clicked(self, button):
        """Open profile management dialog."""
        root = self.get_root()
        if not root or not isinstance(root, Gtk.Window):
            return

        profile_manager = self._get_profile_manager()
        dialog = ProfileListDialog(profile_manager=profile_manager)
        dialog.set_on_profile_selected(self._on_profile_run_from_dialog)
        dialog.connect("close-request", lambda d: self.refresh())
        dialog.set_transient_for(root)
        dialog.present()

    def _on_profile_run_from_dialog(self, profile: "ScanProfile"):
        """Handle profile selected for immediate scan from dialog."""
        self.refresh()
        self.set_selected_profile(profile.id)
        self.emit("start-scan-requested")

    @property
    def selected_profile(self) -> "ScanProfile | None":
        return self._selected_profile

    def set_selected_profile(self, profile_id: str) -> bool:
        """Select profile by ID. Returns True if found."""
        for i, profile in enumerate(self._profile_list):
            if profile.id == profile_id:
                self._dropdown.set_selected(i + 1)
                self._selected_profile = profile
                return True
        return False

    def get_exclusions(self) -> dict | None:
        """Get exclusions from selected profile."""
        if self._selected_profile is None:
            return None
        return {
            "paths": self._selected_profile.exclusions.get("paths", []),
            "patterns": self._selected_profile.exclusions.get("patterns", []),
        }


GObject.type_register(ProfileSelector)
GObject.signal_new(
    "profile-selected", ProfileSelector, GObject.SignalFlags.RUN_FIRST, None, (object,)
)
GObject.signal_new(
    "targets-changed", ProfileSelector, GObject.SignalFlags.RUN_FIRST, None, (object,)
)
GObject.signal_new("start-scan-requested", ProfileSelector, GObject.SignalFlags.RUN_FIRST, None, ())
