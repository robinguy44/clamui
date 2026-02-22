# preferences/ — Modular Preferences System

13 modules. Static factory pattern with lazy page loading.

Parent: [`../AGENTS.md`](../AGENTS.md)

## Structure

```
preferences/
├── window.py          # PreferencesWindow — sidebar nav, lazy page creation
├── base.py            # PreferencesPageMixin + widget helper functions
├── scanner_page.py    # Scanner backend settings (TEMPLATE for new pages)
├── database_page.py   # Freshclam database settings
├── behavior_page.py   # Close behavior, notifications, tray
├── exclusions_page.py # Exclusion pattern management
├── scheduled_page.py  # Scheduled scan configuration
├── onaccess_page.py   # On-access scanning settings
├── device_scan_page.py# Device scanning settings
├── virustotal_page.py # VirusTotal API configuration
├── save_page.py       # Save & apply with pkexec elevation
└── debug_page.py      # Debug/logging options
```

## Recipe: Adding a New Preferences Page

### 1. Create the page module
Use `scanner_page.py` as template:

```python
from ..compat import create_switch_row, create_entry_row
from .base import PreferencesPageMixin, create_spin_row, populate_bool_field

class MyPage(PreferencesPageMixin):
    @staticmethod
    def create_page(widgets_dict: dict, settings_manager, parent_window) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(
            title=_("My Settings"),
            icon_name=resolve_icon_name("preferences-system-symbolic"),
        )
        group = Adw.PreferencesGroup(title=_("Group Title"))
        # Add rows to group, store widgets in widgets_dict
        page.add(group)
        return page

    @staticmethod
    def populate_fields(config: dict, widgets_dict: dict):
        populate_bool_field(config, widgets_dict, "my_key", default=True)

    @staticmethod
    def collect_data(widgets_dict: dict) -> dict:
        return {"my_key": widgets_dict["my_key"].get_active()}
```

### 2. Register in window.py
```python
# In NAVIGATION_ITEMS list:
("my_page", "preferences-system-symbolic", N_("My Settings")),

# Add factory method:
def _create_my_page(self):
    page = MyPage.create_page(self._my_widgets, self._settings_manager, self)
    self._stack.add_titled(page, "my_page", _("My Settings"))
```

### 3. Write tests
`tests/ui/preferences/test_my_page.py` — use `mock_gi_modules` fixture.

## Key APIs from base.py

| Function | Purpose |
|----------|---------|
| `create_spin_row(title, subtitle, min, max, step)` | Returns `(row, spin_button)` tuple |
| `create_password_entry_row(title)` | Password entry with visibility toggle |
| `populate_bool_field(config, widgets, key, default)` | Load bool into switch |
| `populate_int_field(config, widgets, key)` | Load int into spin button |
| `populate_text_field(config, widgets, key)` | Load text into entry |
| `create_status_row(title, ok, ok_msg, err_msg)` | Returns `(row, icon)` for status display |
| `styled_prefix_icon(icon_name)` | 12px-margin dim icon for row prefix |

## Anti-Patterns (preferences-specific)

- **Eager page creation**: Only `behavior_page` loads eagerly — all others use lazy factory pattern
- **`Adw.SpinRow` / `Adw.PasswordEntryRow`**: Use `create_spin_row()` / `create_password_entry_row()` from base.py
- **Direct widget value access**: Use `populate_*` helpers for loading, `collect_data()` for saving
- **Storing row instead of spin_button**: `create_spin_row()` returns `(row, spin_button)` — store the `spin_button` in `widgets_dict` for `get_value()`/`set_value()`
