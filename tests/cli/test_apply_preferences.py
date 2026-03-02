# ClamUI Privileged Apply Helper Tests
"""Tests for the privileged configuration apply helper CLI."""

from src.cli.apply_preferences import main


class TestApplyPreferencesCli:
    """Tests for src.cli.apply_preferences.main."""

    def test_main_applies_single_config_pair(self, tmp_path):
        """Helper should copy a staged file and set destination permissions."""
        source = tmp_path / "source.conf"
        destination = tmp_path / "dest.conf"
        source.write_text("LogVerbose yes\n", encoding="utf-8")

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

        exit_code = main([str(source), str(destination)])

        assert exit_code == 0
        assert destination.exists()
