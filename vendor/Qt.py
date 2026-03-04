# -*- coding: utf-8 -*-
"""Qt compatibility module for NodeGraphQt.

This module provides a compatibility layer between PySide2 and PySide6.
It allows NodeGraphQt to work with either version.

This is a shim that NodeGraphQt uses to import Qt bindings.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys

# Try PySide6 first (Maya 2024+)
try:
    from PySide6 import QtCore, QtGui, QtWidgets, QtSvg
    from PySide6.QtCore import Qt
    from shiboken6 import wrapInstance
    __binding__ = 'PySide6'
    
except ImportError:
    # Fall back to PySide2 (Maya 2022-2023)
    try:
        from PySide2 import QtCore, QtGui, QtWidgets, QtSvg
        from PySide2.QtCore import Qt
        from shiboken2 import wrapInstance
        __binding__ = 'PySide2'
        
    except ImportError:
        raise ImportError(
            "Neither PySide6 nor PySide2 found. "
            "Please ensure you're running this in Maya or have PySide installed."
        )

# PySide6 API compatibility patches.
# Some classes were moved between modules in PySide6.
# NodeGraphQt was written for PySide2 which has these in QtWidgets.
if __binding__ == 'PySide6':
    # Several classes moved from QtWidgets to QtGui in PySide6.
    # Patch them back into QtWidgets so NodeGraphQt (written for PySide2) works.
    _moved_to_qtgui = [
        'QAction',
        'QActionGroup',
        'QShortcut',
        'QUndoCommand',
        'QUndoStack',
    ]
    for _cls in _moved_to_qtgui:
        if not hasattr(QtWidgets, _cls):
            setattr(QtWidgets, _cls, getattr(QtGui, _cls))

# QtCompat - compatibility bridge for Qt API differences across versions.
# NodeGraphQt uses QtCompat.QHeaderView.setSectionResizeMode(header, ...)
# which replaced setResizeMode() in Qt4. PySide2/PySide6 (Qt5/Qt6) already
# use setSectionResizeMode, so we simply delegate to the native method.
class _QHeaderViewCompat:
    @staticmethod
    def setSectionResizeMode(header, *args):
        header.setSectionResizeMode(*args)


class QtCompat:
    QHeaderView = _QHeaderViewCompat()


# Export all Qt modules
__all__ = [
    'QtCompat',
    'QtCore',
    'QtGui',
    'QtSvg',
    'QtWidgets',
    'Qt',
    'wrapInstance',
    '__binding__',
]

