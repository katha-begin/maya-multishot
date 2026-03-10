# -*- coding: utf-8 -*-
"""Tests for core/logging_config.py.

Covers:
- Headless setup (no Maya available)
- Log level filtering
- Namespace prefix for get_logger()
- File handler creation and writing
- No print() calls remaining in core/ or tools/ modules
"""

from __future__ import absolute_import

import logging
import os
import sys

import pytest

# Ensure repo root is on path
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.logging_config import setup_logging, get_logger, CTX_LOGGER_ROOT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_ctx_root():
    """Remove all handlers from the ctx_tools root logger so tests are isolated."""
    root = logging.getLogger(CTX_LOGGER_ROOT)
    for handler in list(root.handlers):
        root.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSetupLoggingHeadless:
    """setup_logging() must not raise when Maya is unavailable."""

    def test_setup_logging_headless(self):
        """Calling setup_logging() without Maya must not raise any exception."""
        _reset_ctx_root()
        try:
            setup_logging(level='INFO', maya_mode=False)
        except Exception as exc:
            pytest.fail("setup_logging() raised unexpectedly: %s" % exc)

    def test_setup_logging_no_handlers_crash(self):
        """After setup_logging(), root ctx_tools logger has at least one handler."""
        _reset_ctx_root()
        setup_logging(level='INFO', maya_mode=False)
        root = logging.getLogger(CTX_LOGGER_ROOT)
        assert len(root.handlers) >= 1


class TestSetupLoggingLevel:
    """Log level filtering behaviour."""

    def test_setup_logging_debug_level(self, capsys):
        """When level=DEBUG, debug messages must be emitted to stderr."""
        _reset_ctx_root()
        setup_logging(level='DEBUG', maya_mode=False)
        log = get_logger('test_debug')
        log.debug("debug message sentinel")
        captured = capsys.readouterr()
        assert 'debug message sentinel' in captured.err

    def test_setup_logging_info_suppresses_debug(self, capsys):
        """When level=INFO, debug messages must NOT appear in output."""
        _reset_ctx_root()
        setup_logging(level='INFO', maya_mode=False)
        log = get_logger('test_suppress_debug')
        log.debug("should be suppressed")
        captured = capsys.readouterr()
        assert 'should be suppressed' not in captured.err

    def test_setup_logging_warning_level(self, capsys):
        """warning() messages appear at WARNING level or below."""
        _reset_ctx_root()
        setup_logging(level='WARNING', maya_mode=False)
        log = get_logger('test_warning')
        log.warning("warning sentinel text")
        captured = capsys.readouterr()
        assert 'warning sentinel text' in captured.err

    def test_setup_logging_info_suppressed_at_warning(self, capsys):
        """info() messages do not appear when level=WARNING."""
        _reset_ctx_root()
        setup_logging(level='WARNING', maya_mode=False)
        log = get_logger('test_info_suppressed')
        log.info("info should not appear")
        captured = capsys.readouterr()
        assert 'info should not appear' not in captured.err


class TestGetLoggerNamespace:
    """get_logger() must produce loggers under the ctx_tools namespace."""

    def test_get_logger_namespace(self):
        """Logger name must start with 'ctx_tools.'."""
        log = get_logger('some.module')
        assert log.name.startswith('ctx_tools.')

    def test_get_logger_full_name(self):
        """Full logger name must be 'ctx_tools.<name>'."""
        log = get_logger('core.gaffer.manager')
        assert log.name == 'ctx_tools.core.gaffer.manager'

    def test_get_logger_child_of_root(self):
        """Returned logger must be a descendant of the ctx_tools root logger."""
        log = get_logger('my_tool')
        root = logging.getLogger(CTX_LOGGER_ROOT)
        # A child logger propagates to the root logger
        assert log.name.startswith(root.name)


class TestSetupLoggingFile:
    """File handler creates a file and writes to it."""

    def test_setup_logging_file_created(self, tmp_path):
        """When log_file is specified, the file is created."""
        _reset_ctx_root()
        log_path = str(tmp_path / 'ctx_tools_test.log')
        setup_logging(level='DEBUG', log_file=log_path, maya_mode=False)
        log = get_logger('test_file')
        log.info("file creation test sentinel")
        # Flush handlers
        for handler in logging.getLogger(CTX_LOGGER_ROOT).handlers:
            try:
                handler.flush()
            except Exception:
                pass
        assert os.path.isfile(log_path), "Log file was not created"

    def test_setup_logging_file_written(self, tmp_path):
        """Written log messages appear in the log file."""
        _reset_ctx_root()
        log_path = str(tmp_path / 'ctx_tools_written.log')
        setup_logging(level='DEBUG', log_file=log_path, maya_mode=False)
        log = get_logger('test_file_content')
        log.info("unique_sentinel_value_12345")
        # Flush handlers
        for handler in logging.getLogger(CTX_LOGGER_ROOT).handlers:
            try:
                handler.flush()
            except Exception:
                pass
        with open(log_path, 'r') as fh:
            content = fh.read()
        assert 'unique_sentinel_value_12345' in content


class TestNoPrintInCoreModules:
    """Ensure no print() calls remain in core/*.py or tools/*.py modules."""

    # Directories to scan (relative to repo root)
    _SCAN_DIRS = ['core', 'tools']

    # Files explicitly excluded from the check (outside the tool boundary)
    _EXCLUDE_FILES = set()

    @staticmethod
    def _collect_py_files(base_dir):
        """Yield absolute paths of all .py files under base_dir (recursive)."""
        for dirpath, dirnames, filenames in os.walk(base_dir):
            # Skip __pycache__ and vendor directories
            dirnames[:] = [
                d for d in dirnames
                if d not in ('__pycache__', 'vendor', '.git')
            ]
            for filename in filenames:
                if filename.endswith('.py'):
                    yield os.path.join(dirpath, filename)

    def _check_no_print(self, scan_dir_name):
        """Assert that no .py file in scan_dir_name contains a bare print( call."""
        base_dir = os.path.join(_REPO_ROOT, scan_dir_name)
        if not os.path.isdir(base_dir):
            pytest.skip("Directory not found: %s" % base_dir)

        violations = []
        for filepath in self._collect_py_files(base_dir):
            rel_path = os.path.relpath(filepath, _REPO_ROOT)
            if rel_path in self._EXCLUDE_FILES:
                continue
            try:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as fh:
                    for lineno, line in enumerate(fh, start=1):
                        stripped = line.strip()
                        # Skip comment lines
                        if stripped.startswith('#'):
                            continue
                        # Skip docstring-only lines (heuristic: starts with """)
                        if stripped.startswith('"""') or stripped.startswith("'''"):
                            continue
                        # Skip doctest-style example lines (>>> ...) and
                        # doctest continuation lines (... print(...))
                        if stripped.startswith('>>>') or stripped.startswith('...'):
                            continue
                        if 'print(' in line:
                            violations.append("%s:%d: %s" % (rel_path, lineno, line.rstrip()))
            except (IOError, OSError):
                pass

        if violations:
            msg = "print() calls found in the following files:\n" + "\n".join(violations)
            pytest.fail(msg)

    def test_no_print_in_core(self):
        """No print() in core/ modules."""
        self._check_no_print('core')

    def test_no_print_in_tools(self):
        """No print() in tools/ modules."""
        self._check_no_print('tools')
