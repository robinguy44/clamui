# ClamUI Desktop Integration Tests
"""
Tests for desktop file validation and icon resources.

Tests cover:
- Desktop file required fields
- Desktop file syntax validity
- Icon files existence and naming
- Exec path correctness
- Desktop file consistency between root and flathub

These tests prevent broken desktop integration in packaging.
"""

import subprocess
from pathlib import Path

import pytest

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestDesktopFileSyntax:
    """Tests for desktop file syntax validity."""

    def test_desktop_file_exists(self):
        """Test that main desktop file exists."""
        desktop = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.desktop"
        assert desktop.exists(), "Main desktop file not found"

    def test_flathub_desktop_file_exists(self):
        """Test that flathub desktop file exists."""
        desktop = PROJECT_ROOT / "flathub" / "io.github.linx_systems.ClamUI.desktop"
        assert desktop.exists(), "Flathub desktop file not found"

    def test_desktop_file_has_required_fields(self):
        """Test desktop file has all required fields."""
        desktop = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.desktop"
        content = desktop.read_text()

        required_fields = [
            "[Desktop Entry]",
            "Type=",
            "Name=",
            "Exec=",
            "Icon=",
        ]

        for field in required_fields:
            assert field in content, f"Missing required field: {field}"

    def test_desktop_type_is_application(self):
        """Test desktop file type is Application."""
        desktop = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.desktop"
        content = desktop.read_text()

        assert "Type=Application" in content, "Type should be Application"

    def test_desktop_file_has_categories(self):
        """Test desktop file has Categories field."""
        desktop = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.desktop"
        content = desktop.read_text()

        assert "Categories=" in content, "Missing Categories field"
        # Should have at least one of: Utility, Security, GTK
        assert any(cat in content for cat in ["Utility", "Security", "GTK"]), (
            "Missing standard category"
        )

    @pytest.mark.skipif(
        subprocess.run(["which", "desktop-file-validate"], capture_output=True).returncode != 0,
        reason="desktop-file-validate not available",
    )
    def test_desktop_file_validates(self):
        """Test desktop file passes desktop-file-validate."""
        desktop = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.desktop"

        result = subprocess.run(
            ["desktop-file-validate", str(desktop)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Validation failed: {result.stderr}"


class TestExecPath:
    """Tests for desktop file Exec path."""

    def test_exec_uses_clamui_binary(self):
        """Test Exec line uses clamui binary."""
        desktop = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.desktop"
        content = desktop.read_text()

        # Should be 'clamui' not full path or python -m
        assert "Exec=clamui" in content, "Exec should be 'clamui' binary"

    def test_exec_handles_urls(self):
        """Test Exec line handles file URLs with %U."""
        desktop = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.desktop"
        content = desktop.read_text()

        # Check for %U or %F for file handling
        assert "%U" in content or "%F" in content or "Exec=clamui\n" in content, (
            "Exec should handle file arguments or be simple"
        )


class TestIconFiles:
    """Tests for icon file resources."""

    def test_svg_icon_exists(self):
        """Test SVG icon exists."""
        svg_icon = PROJECT_ROOT / "icons" / "io.github.linx_systems.ClamUI.svg"
        assert svg_icon.exists(), "SVG icon not found in icons/"

    def test_png_icon_exists(self):
        """Test PNG icon exists."""
        png_icon = PROJECT_ROOT / "icons" / "io.github.linx_systems.ClamUI.png"
        assert png_icon.exists(), "PNG icon not found in icons/"

    def test_icon_name_matches_app_id(self):
        """Test icon files use correct app ID."""
        icons_dir = PROJECT_ROOT / "icons"

        icon_files = list(icons_dir.glob("io.github.linx_systems.ClamUI.*"))
        assert len(icon_files) >= 2, "Should have at least SVG and PNG icons"

    def test_desktop_icon_reference_valid(self):
        """Test desktop file Icon field matches actual icon name."""
        desktop = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.desktop"
        content = desktop.read_text()

        # Extract icon name from desktop file
        icon_line = [line for line in content.split("\n") if line.startswith("Icon=")]
        assert len(icon_line) == 1, "Should have exactly one Icon= line"

        icon_name = icon_line[0].replace("Icon=", "").strip()
        assert icon_name == "io.github.linx_systems.ClamUI", f"Icon name mismatch: {icon_name}"

    def test_svg_icon_is_valid_svg(self):
        """Test SVG icon is valid XML."""
        svg_icon = PROJECT_ROOT / "icons" / "io.github.linx_systems.ClamUI.svg"
        content = svg_icon.read_text()

        assert content.startswith("<?xml") or content.startswith("<svg"), (
            "SVG should start with XML declaration or svg tag"
        )
        assert "</svg>" in content, "SVG should have closing svg tag"


class TestDesktopFileConsistency:
    """Tests for consistency between desktop files."""

    def test_root_and_flathub_desktop_match(self):
        """Test data/ and flathub desktop files are consistent."""
        root_desktop = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.desktop"
        flathub_desktop = PROJECT_ROOT / "flathub" / "io.github.linx_systems.ClamUI.desktop"

        root_content = root_desktop.read_text()
        flathub_content = flathub_desktop.read_text()

        # Parse key fields
        def parse_field(content, field):
            for line in content.split("\n"):
                if line.startswith(f"{field}="):
                    return line.split("=", 1)[1].strip()
            return None

        # Name and Icon should match
        assert parse_field(root_content, "Name") == parse_field(flathub_content, "Name"), (
            "Name should match between desktop files"
        )

        assert parse_field(root_content, "Icon") == parse_field(flathub_content, "Icon"), (
            "Icon should match between desktop files"
        )


class TestVirusTotalDesktop:
    """Tests for VirusTotal integration desktop file."""

    def test_virustotal_desktop_exists(self):
        """Test VirusTotal action desktop file exists."""
        desktop = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI-virustotal.desktop"
        assert desktop.exists(), "VirusTotal desktop file not found"

    def test_virustotal_desktop_has_mimetype(self):
        """Test VirusTotal desktop references file handling."""
        desktop = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI-virustotal.desktop"
        content = desktop.read_text()

        # Should have Type and Exec at minimum
        assert "Type=" in content, "Missing Type field"
        assert "Exec=" in content, "Missing Exec field"


class TestDolphinServiceMenus:
    """Tests for Dolphin/KDE service menu files."""

    def test_dolphin_scan_service_exists(self):
        """Test Dolphin scan service menu file exists."""
        desktop = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.service.desktop"
        assert desktop.exists(), "Dolphin scan service menu not found"

    def test_dolphin_service_uses_valid_all_files_mimetype(self):
        """Test Dolphin service menu uses the KDE-compatible all-files MIME type."""
        desktop = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.service.desktop"
        content = desktop.read_text()

        assert "MimeType=application/octet-stream;inode/directory;" in content
        assert "ServiceTypes=KonqPopupMenu/Plugin" in content

    def test_flathub_dolphin_service_exists(self):
        """Test Flatpak integration bundle includes the Dolphin scan service menu."""
        desktop = (
            PROJECT_ROOT
            / "flathub"
            / "integrations"
            / "io.github.linx_systems.ClamUI.service.desktop"
        )
        assert desktop.exists(), "Flatpak Dolphin scan service menu not found"
