# ClamUI Version Consistency Tests
"""
Tests for version synchronization across project files.

Tests cover:
- pyproject.toml version format (semantic versioning)
- Metainfo release version matches pyproject.toml
- App ID consistency across files

These tests prevent version mismatches between packaging formats.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestVersionFormat:
    """Tests for version format validation."""

    def test_pyproject_version_exists(self):
        """Test pyproject.toml has version field."""
        pyproject = PROJECT_ROOT / "pyproject.toml"
        content = pyproject.read_text()

        assert re.search(r'^version\s*=\s*["\']', content, re.MULTILINE), (
            "version not defined in pyproject.toml"
        )

    def test_version_is_semantic(self):
        """Test version follows semantic versioning (X.Y.Z)."""
        pyproject = PROJECT_ROOT / "pyproject.toml"
        content = pyproject.read_text()

        match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        assert match, "Could not extract version from pyproject.toml"

        version = match.group(1)
        # Semantic versioning: MAJOR.MINOR.PATCH with optional pre-release
        assert re.match(r"^\d+\.\d+\.\d+", version), (
            f"Version '{version}' doesn't follow semantic versioning"
        )

    def test_version_not_zero(self):
        """Test version is not 0.0.0 (placeholder)."""
        pyproject = PROJECT_ROOT / "pyproject.toml"
        content = pyproject.read_text()

        match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        version = match.group(1) if match else "0.0.0"

        assert version != "0.0.0", "Version should not be placeholder 0.0.0"


class TestMetainfoVersion:
    """Tests for metainfo.xml version consistency."""

    def test_metainfo_exists(self):
        """Test metainfo.xml file exists."""
        metainfo = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.metainfo.xml"
        assert metainfo.exists(), "metainfo.xml not found"

    def test_metainfo_is_valid_xml(self):
        """Test metainfo is valid XML."""
        metainfo = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.metainfo.xml"

        try:
            ET.parse(metainfo)
        except ET.ParseError as e:
            pytest.fail(f"Invalid XML: {e}")

    def test_metainfo_has_releases(self):
        """Test metainfo has releases section."""
        metainfo = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.metainfo.xml"
        tree = ET.parse(metainfo)
        root = tree.getroot()

        releases = root.find("releases")
        assert releases is not None, "Missing releases section in metainfo"

        release_list = releases.findall("release")
        assert len(release_list) > 0, "No releases found in metainfo"

    def test_latest_release_matches_pyproject(self):
        """Test latest metainfo release matches pyproject.toml version."""
        # Get pyproject version
        pyproject = PROJECT_ROOT / "pyproject.toml"
        pyproject_content = pyproject.read_text()

        pyproject_match = re.search(
            r'^version\s*=\s*["\']([^"\']+)["\']', pyproject_content, re.MULTILINE
        )
        assert pyproject_match, "Could not extract version from pyproject.toml"
        pyproject_version = pyproject_match.group(1)

        # Get metainfo latest release
        metainfo = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.metainfo.xml"
        tree = ET.parse(metainfo)
        root = tree.getroot()

        releases = root.find("releases")
        if releases is None:
            pytest.fail("No releases section in metainfo")

        # First release is the latest
        first_release = releases.find("release")
        if first_release is None:
            pytest.fail("No release entries in metainfo")

        metainfo_version = first_release.get("version")

        assert metainfo_version == pyproject_version, (
            f"Version mismatch: pyproject.toml={pyproject_version}, metainfo.xml={metainfo_version}"
        )

    def test_releases_have_dates(self):
        """Test all releases have date attributes."""
        metainfo = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.metainfo.xml"
        tree = ET.parse(metainfo)
        root = tree.getroot()

        releases = root.find("releases")
        if releases is None:
            pytest.skip("No releases section")

        for release in releases.findall("release"):
            version = release.get("version", "unknown")
            date = release.get("date")
            assert date is not None, f"Release {version} missing date attribute"

            # Validate date format (YYYY-MM-DD)
            assert re.match(r"^\d{4}-\d{2}-\d{2}$", date), (
                f"Release {version} has invalid date format: {date}"
            )


class TestAppIdConsistency:
    """Tests for app ID consistency across files."""

    def test_metainfo_app_id(self):
        """Test metainfo has correct app ID."""
        metainfo = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.metainfo.xml"
        tree = ET.parse(metainfo)
        root = tree.getroot()

        app_id = root.find("id")
        assert app_id is not None, "Missing id element in metainfo"
        assert app_id.text == "io.github.linx_systems.ClamUI", f"Unexpected app ID: {app_id.text}"

    def test_metainfo_launchable_matches_desktop(self):
        """Test metainfo launchable matches desktop file name."""
        metainfo = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.metainfo.xml"
        tree = ET.parse(metainfo)
        root = tree.getroot()

        launchable = root.find("launchable")
        assert launchable is not None, "Missing launchable element"

        desktop_id = launchable.text
        assert desktop_id == "io.github.linx_systems.ClamUI.desktop", (
            f"Launchable should match desktop file: {desktop_id}"
        )

    def test_metainfo_provides_binary(self):
        """Test metainfo provides correct binary name."""
        metainfo = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.metainfo.xml"
        tree = ET.parse(metainfo)
        root = tree.getroot()

        provides = root.find("provides")
        if provides is None:
            pytest.skip("No provides section")

        binary = provides.find("binary")
        assert binary is not None, "Missing binary element in provides"
        assert binary.text == "clamui", f"Binary should be 'clamui': {binary.text}"

    def test_desktop_file_name_matches_app_id(self):
        """Test desktop file name matches app ID pattern."""
        desktop = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.desktop"

        # File name should be app_id.desktop
        expected_name = "io.github.linx_systems.ClamUI.desktop"
        assert desktop.name == expected_name, f"Desktop file name mismatch: {desktop.name}"


class TestProjectNameConsistency:
    """Tests for project name consistency."""

    def test_pyproject_name(self):
        """Test pyproject.toml has correct project name."""
        pyproject = PROJECT_ROOT / "pyproject.toml"
        content = pyproject.read_text()

        assert 'name = "clamui"' in content, "Project name should be 'clamui'"

    def test_metainfo_name(self):
        """Test metainfo has correct display name."""
        metainfo = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.metainfo.xml"
        tree = ET.parse(metainfo)
        root = tree.getroot()

        name = root.find("name")
        assert name is not None, "Missing name element in metainfo"
        assert name.text == "ClamUI", f"Display name should be 'ClamUI': {name.text}"

    def test_desktop_name(self):
        """Test desktop file has correct Name field."""
        desktop = PROJECT_ROOT / "data" / "io.github.linx_systems.ClamUI.desktop"
        content = desktop.read_text()

        assert "Name=ClamUI" in content, "Desktop Name should be 'ClamUI'"
