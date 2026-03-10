# -*- coding: utf-8 -*-
"""Logging configuration for CTX Tools.

Provides a single configuration point that routes log output correctly
in both Maya mode (Script Editor / Output Window) and headless mode
(stderr / file).

Usage:
    from core.logging_config import setup_logging, get_logger

    setup_logging(level='INFO', maya_mode=True)
    logger = get_logger(__name__)
    logger.info("Operation completed: %s", result)
"""

from __future__ import absolute_import
from __future__ import print_function

import logging
import logging.handlers
import sys

MAYA_HANDLER_NAME = 'maya_output'
CTX_LOGGER_ROOT = 'ctx_tools'
DEFAULT_FORMAT = '%(name)s [%(levelname)s] %(message)s'
VERBOSE_FORMAT = '%(asctime)s %(name)s [%(levelname)s] %(message)s'

# Internal flag — set to True after setup_logging() is called once
_logging_configured = False


class _MayaOutputHandler(logging.Handler):
    """Logging handler that routes messages to Maya's Output Window.

    Routes by level:
        DEBUG / INFO  -> MGlobal.displayInfo()
        WARNING       -> MGlobal.displayWarning()
        ERROR / ABOVE -> MGlobal.displayError()

    Silently falls back to a no-op if maya.OpenMaya is not importable.
    """

    def __init__(self):
        super(_MayaOutputHandler, self).__init__()
        self._mglobal = None
        self._available = False
        try:
            from maya import OpenMaya
            self._mglobal = OpenMaya.MGlobal
            self._available = True
        except ImportError:
            pass

    def emit(self, record):
        if not self._available:
            return
        try:
            msg = self.format(record)
            if record.levelno >= logging.ERROR:
                self._mglobal.displayError(msg)
            elif record.levelno >= logging.WARNING:
                self._mglobal.displayWarning(msg)
            else:
                self._mglobal.displayInfo(msg)
        except Exception:
            self.handleError(record)


def setup_logging(level='INFO', log_file=None, maya_mode=True, verbose=False):
    """Configure root logger for CTX Tools.

    Should be called once at tool startup (e.g. from maya_menu.install()).
    Subsequent calls reconfigure the existing handlers in place.

    Args:
        level (str): Logging level name ('DEBUG', 'INFO', 'WARNING', 'ERROR').
        log_file (str or None): Optional path to write a rotating log file.
        maya_mode (bool): If True, attempt to route output through
            MGlobal.displayInfo/Warning/Error when Maya is available.
            Falls back to stderr if Maya is not importable.
        verbose (bool): If True, use VERBOSE_FORMAT which includes timestamps.
    """
    global _logging_configured

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    fmt = VERBOSE_FORMAT if verbose else DEFAULT_FORMAT
    formatter = logging.Formatter(fmt)

    root_logger = logging.getLogger(CTX_LOGGER_ROOT)
    root_logger.setLevel(numeric_level)

    # Remove previously installed CTX handlers to avoid duplicates on reload
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass

    maya_handler_installed = False

    # Maya output handler — only when maya_mode is requested
    if maya_mode:
        maya_handler = _MayaOutputHandler()
        if maya_handler._available:
            maya_handler.setLevel(numeric_level)
            maya_handler.setFormatter(formatter)
            maya_handler.name = MAYA_HANDLER_NAME
            root_logger.addHandler(maya_handler)
            maya_handler_installed = True

    # Fallback stderr handler when Maya output is not available
    if not maya_handler_installed:
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setLevel(numeric_level)
        stream_handler.setFormatter(formatter)
        stream_handler.name = 'stderr_fallback'
        root_logger.addHandler(stream_handler)

    # Optional rotating file handler
    if log_file:
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=5 * 1024 * 1024,  # 5 MB
                backupCount=3,
                encoding='utf-8',
            )
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(logging.Formatter(VERBOSE_FORMAT))
            file_handler.name = 'rotating_file'
            root_logger.addHandler(file_handler)
        except Exception as exc:
            # Do not crash startup if the log file cannot be opened
            root_logger.warning("Could not open log file '%s': %s", log_file, exc)

    # Prevent messages from propagating to the root logging logger, which
    # could cause duplicate output in environments with existing handlers.
    root_logger.propagate = False

    _logging_configured = True


def get_logger(name):
    """Return a logger under the 'ctx_tools' namespace.

    The 'name' argument is typically __name__ of the calling module.
    The returned logger is a child of the 'ctx_tools' root logger, so
    all handlers configured via setup_logging() apply automatically.

    Args:
        name (str): Module name (e.g. 'core.gaffer.manager').

    Returns:
        logging.Logger: Logger named 'ctx_tools.<name>'.
    """
    return logging.getLogger('{}.{}'.format(CTX_LOGGER_ROOT, name))
