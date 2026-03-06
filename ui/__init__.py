# -*- coding: utf-8 -*-
"""UI package for Context Variables Pipeline.

This package contains all user interface components including:
- Main window with dockable interface
- Dialogs for various operations

The UI is built with PySide2/PySide6 for Maya compatibility.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

__version__ = '1.0.0'
__all__ = [
    'main_window',
    'base_dialog',
    'add_shot_dialog',
    'settings_dialog',
    'show',
]


def show():
    """Show the Multishot Manager window.

    Returns:
        MainWindow: The main window instance
    """
    from ui.main_window import MainWindow

    window = MainWindow()
    window.show()
    return window

