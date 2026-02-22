# Scan Results Widget
"""
Results handling widget after scan completion.

Single responsibility:
- Show "View Results" button
- Toggle between clean/infected styling
"""

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ...core.i18n import _


class ScanResultsWidget(Gtk.Box):
    """
    Widget showing View Results button after scan.
    """

    def __init__(self, on_view_results: Callable[[], None], **kwargs):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, **kwargs)
        self.set_halign(Gtk.Align.CENTER)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_visible(False)

        self._on_view_results = on_view_results

        self._button = Gtk.Button()
        self._button.add_css_class("suggested-action")
        self._button.add_css_class("pill")
        self._button.set_size_request(200, -1)
        self._button.connect("clicked", self._on_clicked)
        self.append(self._button)

    def show(self, threat_count: int = 0) -> None:
        """Show results button with appropriate label."""
        if threat_count > 0:
            self._button.set_label(_("View Results ({n})").format(n=threat_count))
            self._button.remove_css_class("suggested-action")
            self._button.add_css_class("destructive-action")
        else:
            self._button.set_label(_("View Results"))
            self._button.remove_css_class("destructive-action")
            self._button.add_css_class("suggested-action")

        self.set_visible(True)

    def hide(self) -> None:
        self.set_visible(False)

    def _on_clicked(self, button):
        if self._on_view_results:
            self._on_view_results()
