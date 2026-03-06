# -*- coding: utf-8 -*-
"""Base dialog module for Context Variables Pipeline UI.

Provides shared Qt boilerplate used by all dialogs:
- PySide6 / PySide2 import with automatic fallback
- BaseDialog base class with common setup/teardown pattern
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

try:
    from PySide6 import QtWidgets, QtCore, QtGui
    PYSIDE_VERSION = 6
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
    PYSIDE_VERSION = 2


class BaseDialog(QtWidgets.QDialog):
    """Base class for all pipeline UI dialogs.

    Subclasses should implement:
        _setup_ui()     - build the widget layout
        _connect_signals() - connect Qt signals to slots

    Usage:
        class MyDialog(BaseDialog):
            def _setup_ui(self):
                self._label = QtWidgets.QLabel("Hello")
                layout = QtWidgets.QVBoxLayout(self)
                layout.addWidget(self._label)

            def _connect_signals(self):
                pass
    """

    def __init__(self, parent=None, title=""):
        super(BaseDialog, self).__init__(parent)
        if title:
            self.setWindowTitle(title)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Build the dialog's widget layout. Override in subclass."""
        pass

    def _connect_signals(self):
        """Connect Qt signals to slots. Override in subclass."""
        pass

