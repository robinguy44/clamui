# ClamUI Logging Configuration Tests
"""Unit tests for the logging_config module."""

import logging
import os
import zipfile
from unittest.mock import patch

from src.core.logging_config import (
    DEFAULT_BACKUP_COUNT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_BYTES,
    LOG_FORMAT,
    PRIVACY_STATE_FILENAME,
    LoggingConfig,
    PrivacyFormatter,
    configure_logging,
    get_logging_config,
)
from src.core.sanitize import REDACTED_PATH


class TestPrivacyFormatter:
    """Tests for the PrivacyFormatter class."""

    def test_format_replaces_home_directory(self):
        """Test that home directory paths are fully redacted."""
        formatter = PrivacyFormatter(LOG_FORMAT)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=f"Processing file at {os.path.expanduser('~')}/Documents/test.txt",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert REDACTED_PATH in formatted
        assert os.path.expanduser("~") not in formatted

    def test_format_preserves_non_home_paths(self):
        """Test that non-home filesystem paths are also redacted."""
        formatter = PrivacyFormatter(LOG_FORMAT)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Processing file at /etc/clamav/clamd.conf",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert REDACTED_PATH in formatted

    def test_format_handles_message_without_path(self):
        """Test that messages without paths are formatted normally."""
        formatter = PrivacyFormatter(LOG_FORMAT)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Simple message without any path",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert "Simple message without any path" in formatted


class TestLoggingConfigSingleton:
    """Tests for the LoggingConfig singleton pattern."""

    def setup_method(self):
        """Reset the singleton before each test."""
        LoggingConfig._instance = None

    def test_singleton_returns_same_instance(self):
        """Test that LoggingConfig returns the same instance."""
        config1 = LoggingConfig()
        config2 = LoggingConfig()
        assert config1 is config2

    def test_get_logging_config_returns_singleton(self):
        """Test that get_logging_config returns the singleton."""
        config1 = get_logging_config()
        config2 = get_logging_config()
        assert config1 is config2


class TestLoggingConfigConfiguration:
    """Tests for LoggingConfig.configure() method."""

    def setup_method(self):
        """Reset the singleton before each test."""
        LoggingConfig._instance = None

    def test_configure_creates_log_directory(self, tmp_path):
        """Test that configure creates the log directory."""
        log_dir = tmp_path / "debug"
        assert not log_dir.exists()

        config = LoggingConfig()
        result = config.configure(log_dir=log_dir)

        assert result is True
        assert log_dir.exists()

    def test_configure_creates_log_file(self, tmp_path):
        """Test that configure creates the log file."""
        log_dir = tmp_path / "debug"
        config = LoggingConfig()
        config.configure(log_dir=log_dir)

        # Log file might not exist until first log message
        # But handler should be configured
        assert config._file_handler is not None

    def test_configure_sets_log_level(self, tmp_path):
        """Test that configure sets the correct log level."""
        log_dir = tmp_path / "debug"
        config = LoggingConfig()
        config.configure(log_dir=log_dir, log_level="DEBUG")

        assert config._file_handler.level == logging.DEBUG

    def test_configure_with_invalid_directory_fails_gracefully(self):
        """Test that configure handles permission errors gracefully."""
        config = LoggingConfig()
        # Try to create log in a directory we can't write to
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("No permission")):
            result = config.configure(log_dir="/root/cannot_create")
            assert result is False

    def test_configure_with_custom_max_bytes(self, tmp_path):
        """Test that configure respects custom max_bytes."""
        log_dir = tmp_path / "debug"
        config = LoggingConfig()
        custom_max = 1024 * 1024  # 1 MB
        config.configure(log_dir=log_dir, max_bytes=custom_max)

        assert config._file_handler.maxBytes == custom_max

    def test_configure_with_custom_backup_count(self, tmp_path):
        """Test that configure respects custom backup_count."""
        log_dir = tmp_path / "debug"
        config = LoggingConfig()
        custom_count = 5
        config.configure(log_dir=log_dir, backup_count=custom_count)

        assert config._file_handler.backupCount == custom_count


class TestLoggingConfigSetLogLevel:
    """Tests for LoggingConfig.set_log_level() method."""

    def setup_method(self):
        """Reset the singleton before each test."""
        LoggingConfig._instance = None

    def test_set_log_level_changes_level(self, tmp_path):
        """Test that set_log_level changes the log level."""
        log_dir = tmp_path / "debug"
        config = LoggingConfig()
        config.configure(log_dir=log_dir, log_level="WARNING")

        assert config._file_handler.level == logging.WARNING

        result = config.set_log_level("DEBUG")
        assert result is True
        assert config._file_handler.level == logging.DEBUG

    def test_set_log_level_case_insensitive(self, tmp_path):
        """Test that set_log_level is case insensitive."""
        log_dir = tmp_path / "debug"
        config = LoggingConfig()
        config.configure(log_dir=log_dir)

        assert config.set_log_level("debug") is True
        assert config._file_handler.level == logging.DEBUG

        assert config.set_log_level("INFO") is True
        assert config._file_handler.level == logging.INFO

    def test_set_log_level_invalid_level_returns_false(self, tmp_path):
        """Test that set_log_level returns False for invalid levels."""
        log_dir = tmp_path / "debug"
        config = LoggingConfig()
        config.configure(log_dir=log_dir)

        result = config.set_log_level("INVALID")
        assert result is False

    def test_get_log_level_returns_current_level(self, tmp_path):
        """Test that get_log_level returns the current level name."""
        log_dir = tmp_path / "debug"
        config = LoggingConfig()
        config.configure(log_dir=log_dir, log_level="INFO")

        assert config.get_log_level() == "INFO"


class TestLoggingConfigLogFiles:
    """Tests for LoggingConfig log file management methods."""

    def setup_method(self):
        """Reset the singleton before each test."""
        LoggingConfig._instance = None

    def test_get_log_files_returns_empty_list_initially(self, tmp_path):
        """Test that get_log_files returns empty list when no logs exist."""
        log_dir = tmp_path / "debug"
        config = LoggingConfig()
        config.configure(log_dir=log_dir)

        # Before any logging, no files
        files = config.get_log_files()
        # May or may not have the main log file depending on implementation
        assert isinstance(files, list)

    def test_get_log_files_finds_log_files(self, tmp_path):
        """Test that get_log_files finds existing log files."""
        log_dir = tmp_path / "debug"
        log_dir.mkdir(parents=True)

        # Create some fake log files
        (log_dir / "clamui.log").write_text("main log")
        (log_dir / "clamui.log.1").write_text("backup 1")
        (log_dir / "clamui.log.2").write_text("backup 2")

        config = LoggingConfig()
        config._log_dir = log_dir
        config._initialized = True

        files = config.get_log_files()
        assert len(files) == 3
        assert any("clamui.log" in str(f) for f in files)

    def test_get_total_log_size_calculates_correctly(self, tmp_path):
        """Test that get_total_log_size returns correct total."""
        log_dir = tmp_path / "debug"
        log_dir.mkdir(parents=True)

        # Create files with known sizes
        (log_dir / "clamui.log").write_text("A" * 100)
        (log_dir / "clamui.log.1").write_text("B" * 200)

        config = LoggingConfig()
        config._log_dir = log_dir
        config._initialized = True

        total = config.get_total_log_size()
        assert total == 300

    def test_get_log_dir_returns_configured_dir(self, tmp_path):
        """Test that get_log_dir returns the configured directory."""
        log_dir = tmp_path / "debug"
        config = LoggingConfig()
        config.configure(log_dir=log_dir)

        assert config.get_log_dir() == log_dir


class TestLoggingConfigClearLogs:
    """Tests for LoggingConfig.clear_logs() method."""

    def setup_method(self):
        """Reset the singleton before each test."""
        LoggingConfig._instance = None

    def test_clear_logs_removes_all_log_files(self, tmp_path):
        """Test that clear_logs removes all log files."""
        log_dir = tmp_path / "debug"
        log_dir.mkdir(parents=True)

        # Create some log files
        main_log = log_dir / "clamui.log"
        backup1 = log_dir / "clamui.log.1"
        main_log.write_text("main log content")
        backup1.write_text("backup content")

        config = LoggingConfig()
        config.configure(log_dir=log_dir)

        result = config.clear_logs()
        assert result is True

        # Check files are removed (new main log may be recreated)
        remaining = list(log_dir.glob("clamui.log*"))
        # Only the new empty main log should exist
        assert len(remaining) <= 1

    def test_clear_logs_returns_true_when_no_files(self, tmp_path):
        """Test that clear_logs returns True when no files exist."""
        log_dir = tmp_path / "debug"
        config = LoggingConfig()
        config.configure(log_dir=log_dir)

        result = config.clear_logs()
        assert result is True


class TestLoggingConfigExport:
    """Tests for LoggingConfig.export_logs_zip() method."""

    def setup_method(self):
        """Reset the singleton before each test."""
        LoggingConfig._instance = None

    def test_export_logs_zip_creates_zip_file(self, tmp_path):
        """Test that export_logs_zip creates a valid ZIP file."""
        log_dir = tmp_path / "debug"
        log_dir.mkdir(parents=True)

        # Create some log files
        (log_dir / "clamui.log").write_text("main log content")
        (log_dir / "clamui.log.1").write_text("backup content")

        config = LoggingConfig()
        config._log_dir = log_dir
        config._log_file = log_dir / "clamui.log"
        config._initialized = True

        output_path = tmp_path / "export.zip"
        result = config.export_logs_zip(output_path)

        assert result is True
        assert output_path.exists()

        # Verify ZIP contents
        with zipfile.ZipFile(output_path, "r") as zf:
            names = zf.namelist()
            assert "clamui.log" in names
            assert "clamui.log.1" in names

    def test_export_logs_zip_returns_false_when_no_files(self, tmp_path):
        """Test that export_logs_zip returns False when no log files exist."""
        log_dir = tmp_path / "debug"
        log_dir.mkdir(parents=True)

        config = LoggingConfig()
        config._log_dir = log_dir
        config._initialized = True

        output_path = tmp_path / "export.zip"
        result = config.export_logs_zip(output_path)

        assert result is False
        assert not output_path.exists()

    def test_generate_export_filename_format(self):
        """Test that generate_export_filename returns correctly formatted name."""
        config = LoggingConfig()
        filename = config.generate_export_filename()

        assert filename.startswith("clamui-logs-")
        assert filename.endswith(".zip")
        # Should contain date pattern
        assert "-" in filename


class TestConfigureLoggingFunction:
    """Tests for the configure_logging convenience function."""

    def setup_method(self):
        """Reset the singleton before each test."""
        LoggingConfig._instance = None

    def test_configure_logging_with_defaults(self, tmp_path):
        """Test configure_logging with default parameters."""
        result = configure_logging(log_dir=tmp_path / "debug")
        assert result is True

    def test_configure_logging_with_custom_level(self, tmp_path):
        """Test configure_logging with custom log level."""
        log_dir = tmp_path / "debug"
        result = configure_logging(log_level="DEBUG", log_dir=log_dir)

        assert result is True
        config = get_logging_config()
        assert config.get_log_level() == "DEBUG"


class TestSanitizePathForLogging:
    """Tests for the sanitize_path_for_logging function imported by logging_config."""

    def test_sanitize_path_replaces_home(self):
        """Test that home directory paths are redacted."""
        from src.core.sanitize import sanitize_path_for_logging

        home = os.path.expanduser("~")
        path = f"{home}/Documents/file.txt"
        result = sanitize_path_for_logging(path)

        assert result == REDACTED_PATH
        assert home not in result

    def test_sanitize_path_preserves_non_home_paths(self):
        """Test that non-home paths are also redacted."""
        from src.core.sanitize import sanitize_path_for_logging

        path = "/etc/clamav/clamd.conf"
        result = sanitize_path_for_logging(path)

        assert result == REDACTED_PATH

    def test_sanitize_path_handles_none(self):
        """Test that None input returns empty string."""
        from src.core.sanitize import sanitize_path_for_logging

        result = sanitize_path_for_logging(None)
        assert result == ""

    def test_sanitize_path_handles_empty_string(self):
        """Test that empty string returns empty string."""
        from src.core.sanitize import sanitize_path_for_logging

        result = sanitize_path_for_logging("")
        assert result == ""


class TestDefaultConstants:
    """Tests for default constant values."""

    def test_default_log_level(self):
        """Test default log level is WARNING."""
        assert DEFAULT_LOG_LEVEL == "WARNING"

    def test_default_max_bytes(self):
        """Test default max bytes is 5 MB."""
        assert DEFAULT_MAX_BYTES == 5 * 1024 * 1024

    def test_default_backup_count(self):
        """Test default backup count is 3."""
        assert DEFAULT_BACKUP_COUNT == 3

    def test_log_format_contains_required_fields(self):
        """Test log format contains timestamp, level, name, message."""
        assert "%(asctime)s" in LOG_FORMAT
        assert "%(levelname)s" in LOG_FORMAT
        assert "%(name)s" in LOG_FORMAT
        assert "%(message)s" in LOG_FORMAT


class TestLoggingIntegration:
    """Integration tests for the logging system."""

    def setup_method(self):
        """Reset the singleton before each test."""
        LoggingConfig._instance = None

    def test_logging_writes_to_file(self, tmp_path):
        """Test that logging actually writes to the log file."""
        log_dir = tmp_path / "debug"
        configure_logging(log_level="DEBUG", log_dir=log_dir)

        # Get a logger and write a message
        test_logger = logging.getLogger("src.test")
        test_logger.info("Test message from integration test")

        # Check file was written
        log_file = log_dir / "clamui.log"
        assert log_file.exists()

        content = log_file.read_text()
        assert "Test message from integration test" in content

    def test_logging_privacy_in_file(self, tmp_path):
        """Test that privacy formatting works in actual log file."""
        log_dir = tmp_path / "debug"
        configure_logging(log_level="DEBUG", log_dir=log_dir)

        home = os.path.expanduser("~")
        test_logger = logging.getLogger("src.test")
        test_logger.info(f"Processing {home}/Documents/secret.txt")

        log_file = log_dir / "clamui.log"
        content = log_file.read_text()

        # File paths should be fully redacted
        assert REDACTED_PATH in content
        assert home not in content

    def test_configure_redacts_existing_debug_logs(self, tmp_path):
        """Test that configuring logging redacts existing debug logs in the background."""
        log_dir = tmp_path / "debug"
        log_dir.mkdir(parents=True)
        log_file = log_dir / "clamui.log"
        original_path = "/home/user/Documents/private/file.txt"
        log_file.write_text(f"Existing debug entry for {original_path}\n", encoding="utf-8")

        configure_logging(log_level="DEBUG", log_dir=log_dir)
        config = get_logging_config()
        if config._sanitization_thread is not None:
            config._sanitization_thread.join(timeout=2)

        contents = [
            path.read_text(encoding="utf-8")
            for path in sorted(log_dir.glob("clamui.log*"))
            if path.is_file()
        ]
        assert any(REDACTED_PATH in content for content in contents)
        assert all(original_path not in content for content in contents)

    def test_configure_marks_legacy_debug_logs_as_migrated(self, tmp_path):
        """Test that the one-time legacy debug-log migration writes a state marker."""
        log_dir = tmp_path / "debug"
        log_dir.mkdir(parents=True)
        original_path = "/home/user/Documents/private/file.txt"
        (log_dir / "clamui.log").write_text(
            f"Existing debug entry for {original_path}\n",
            encoding="utf-8",
        )

        configure_logging(log_level="DEBUG", log_dir=log_dir)
        config = get_logging_config()
        if config._sanitization_thread is not None:
            config._sanitization_thread.join(timeout=2)

        marker = log_dir / PRIVACY_STATE_FILENAME
        archived_logs = sorted(log_dir.glob("clamui.log.archived-*"))

        assert marker.exists()
        assert archived_logs
        assert not list(log_dir.glob("clamui.log.pending-redaction-*"))

    def test_configure_skips_reprocessing_already_migrated_debug_logs(self, tmp_path):
        """Test startup does not create another cleanup pass once logs are migrated."""
        log_dir = tmp_path / "debug"
        log_dir.mkdir(parents=True)
        original_path = "/home/user/Documents/private/file.txt"
        (log_dir / "clamui.log").write_text(
            f"Existing debug entry for {original_path}\n",
            encoding="utf-8",
        )

        configure_logging(log_level="DEBUG", log_dir=log_dir)
        config = get_logging_config()
        if config._sanitization_thread is not None:
            config._sanitization_thread.join(timeout=2)

        archived_before = sorted(path.name for path in log_dir.glob("clamui.log.archived-*"))

        with patch.object(config, "_sanitize_existing_log_files_background") as mock_background:
            config.configure(log_dir=log_dir, log_level="DEBUG")
            assert not mock_background.called

        archived_after = sorted(path.name for path in log_dir.glob("clamui.log.archived-*"))
        assert archived_after == archived_before
        assert not list(log_dir.glob("clamui.log.pending-redaction-*"))

    def test_configure_processes_stale_pending_redaction_files_without_full_rescan(self, tmp_path):
        """Test startup only finalizes pending files when migration already completed."""
        log_dir = tmp_path / "debug"
        log_dir.mkdir(parents=True)
        marker = log_dir / PRIVACY_STATE_FILENAME
        marker.write_text("1", encoding="utf-8")
        pending_file = log_dir / "clamui.log.pending-redaction-legacy"
        original_path = "/home/user/Documents/private/file.txt"
        pending_file.write_text(f"Existing debug entry for {original_path}\n", encoding="utf-8")
        clean_backup = log_dir / "clamui.log.1"
        clean_backup.write_text(f"Existing debug entry for {REDACTED_PATH}\n", encoding="utf-8")

        configure_logging(log_level="DEBUG", log_dir=log_dir)
        config = get_logging_config()
        if config._sanitization_thread is not None:
            config._sanitization_thread.join(timeout=2)

        archived_pending = sorted(log_dir.glob("clamui.log.archived-*"))
        assert archived_pending
        assert REDACTED_PATH in archived_pending[0].read_text(encoding="utf-8")
        assert (
            clean_backup.read_text(encoding="utf-8")
            == f"Existing debug entry for {REDACTED_PATH}\n"
        )
