# -*- coding: utf-8 -*-
"""Dockable wrapper for Multishot Manager in Maya."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

try:
    from PySide6 import QtWidgets, QtCore
except ImportError:
    from PySide2 import QtWidgets, QtCore


class DockableMainWindow(QtWidgets.QWidget):
    """Dockable wrapper for MainWindow that works with Maya's workspaceControl.

    This creates a simple QWidget and embeds the MainWindow inside it.
    """

    def __init__(self, parent=None):
        super(DockableMainWindow, self).__init__(parent)

        # Set object name for Maya
        self.setObjectName("MultishotManagerDockableWidget")

        # Import here to avoid circular imports
        from ui.main_window import MainWindow

        # Create layout for this widget
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create the main window WITHOUT parent (important!)
        # This prevents it from being a top-level window
        self._main_window = MainWindow(parent=None)

        # Remove window flags to make it embeddable
        self._main_window.setWindowFlags(QtCore.Qt.Widget)

        # Add main window to layout
        layout.addWidget(self._main_window)

        # Show the main window (as a widget, not a window)
        self._main_window.show()

    def get_main_window(self):
        """Get the underlying MainWindow instance."""
        return self._main_window

