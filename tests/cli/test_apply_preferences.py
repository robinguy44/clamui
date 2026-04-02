# ClamUI Privileged Apply Helper Tests
"""Tests for the privileged configuration apply helper CLI."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.cli.apply_preferences import _validate_destination, main

_BYPASS_VALIDATION = patch("src.cli.apply_preferences._validate_destination")


class TestApplyPreferencesCli:
    """Tests for src.cli.apply_preferences.main."""

    def test_main_applies_single_config_pair(self, tmp_path):
        """Helper should copy a staged file and set destination permissions."""
        source = tmp_path / "source.conf"
        destination = tmp_path / "dest.conf"
        source.write_text("LogVerbose yes\n", encoding="utf-8")

        with _BYPASS_VALIDATION:
            exit_code = main([str(source), str(destination)])

        assert exit_code == 0
        assert destination.read_text(encoding="utf-8") == "LogVerbose yes\n"
        assert (destination.stat().st_mode & 0o777) == 0o644

    def test_main_rejects_odd_argument_count(self):
        """Helper should fail when source/destination args are not paired."""
        exit_code = main(["/tmp/source.conf"])

        assert exit_code == 2

    def test_main_fails_for_missing_source(self, tmp_path):
        """Helper should fail when staged source file does not exist."""
        missing_source = tmp_path / "missing.conf"
        destination = tmp_path / "dest.conf"

        exit_code = main([str(missing_source), str(destination)])

        assert exit_code == 1

    def test_main_creates_destination_parent_directory(self, tmp_path):
        """Helper should create destination parent directories when needed."""
        source = tmp_path / "source.conf"
        destination = tmp_path / "nested" / "path" / "dest.conf"
        source.write_text("DatabaseDirectory /var/lib/clamav\n", encoding="utf-8")

        with _BYPASS_VALIDATION:
            exit_code = main([str(source), str(destination)])

        assert exit_code == 0
        assert destination.exists()


class TestValidateDestination:
    """Tests for destination path allowlist validation."""

    def test_accepts_debian_clamav_config_path(self):
        """Paths under /etc/clamav/ with .conf extension should be allowed."""
        _validate_destination(Path("/etc/clamav/clamd.conf"))

    def test_accepts_redhat_clamd_config_path(self):
        """Paths under /etc/clamd.d/ with .conf extension should be allowed."""
        _validate_destination(Path("/etc/clamd.d/scan.conf"))

    def test_accepts_unofficial_sigs_config_path(self):
        """Paths under /etc/clamav-unofficial-sigs/ should be allowed."""
        _validate_destination(Path("/etc/clamav-unofficial-sigs/user.conf"))

    def test_rejects_path_outside_allowlist(self):
        """Paths in non-allowed directories should be rejected."""
        with pytest.raises(ValueError, match="not in allowed"):
            _validate_destination(Path("/etc/nginx/nginx.conf"))

    def test_rejects_path_traversal_attack(self):
        """Paths using .. to escape allowed directories should be rejected."""
        with pytest.raises(ValueError, match="not in allowed"):
            _validate_destination(Path("/etc/clamav/../nginx/nginx.conf"))

    def test_rejects_non_conf_extension(self):
        """Files without .conf extension should be rejected."""
        with pytest.raises(ValueError, match=r"\.conf"):
            _validate_destination(Path("/etc/clamav/clamd.txt"))

    def test_rejects_no_extension(self):
        """Files with no extension should be rejected."""
        with pytest.raises(ValueError, match=r"\.conf"):
            _validate_destination(Path("/etc/clamav/clamd"))

    def test_rejects_tmp_directory(self):
        """Paths under /tmp should be rejected even with .conf extension."""
        with pytest.raises(ValueError, match="not in allowed"):
            _validate_destination(Path("/tmp/evil.conf"))

    def test_rejects_home_directory(self):
        """Paths under user home should be rejected."""
        with pytest.raises(ValueError, match="not in allowed"):
            _validate_destination(Path("/home/user/.config/clamav/clamd.conf"))

    def test_rejects_nested_subdirectory(self):
        """Paths in nested subdirectories beyond the allowlist should be rejected."""
        with pytest.raises(ValueError, match="not in allowed"):
            _validate_destination(Path("/etc/clamav/subdir/clamd.conf"))

    def test_main_rejects_destination_outside_allowlist(self, tmp_path):
        """The full main() flow should reject disallowed destinations."""
        source = tmp_path / "source.conf"
        source.write_text("LogVerbose yes\n", encoding="utf-8")

        exit_code = main([str(source), "/etc/shadow"])

        assert exit_code == 1
