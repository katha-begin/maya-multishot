# -*- coding: utf-8 -*-
"""Launch script for Multishot Manager in Maya with docking support.

Run this in Maya Script Editor:
    import sys
    sys.path.insert(0, r'E:/dev/maya-multishot')
    exec(open(r'E:/dev/maya-multishot/launch_multishot_dockable.py').read())
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import os
import logging

# Add repository root to path if not already there
try:
    repo_root = os.path.dirname(os.path.abspath(__file__))
except NameError:
    # __file__ not defined when using exec(), use current directory
    repo_root = r'E:/dev/maya-multishot'

if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
    print("Added to sys.path: {}".format(repo_root))

# Clear cached modules
modules_to_remove = [key for key in list(sys.modules.keys()) 
                     if key.startswith(('ui', 'core', 'config', 'tools'))]
for module in modules_to_remove:
    del sys.modules[module]

if modules_to_remove:
    print("Cleared {} cached modules".format(len(modules_to_remove)))

# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s: %(message)s'
)

# Import Maya modules
try:
    import maya.cmds as cmds
    from maya import OpenMayaUI as omui
except ImportError:
    print("✗ ERROR: This script must be run inside Maya!")
    raise

# Import Qt
try:
    from PySide6 import QtWidgets, QtCore
    from shiboken6 import wrapInstance
except ImportError:
    from PySide2 import QtWidgets, QtCore
    from shiboken2 import wrapInstance

# Verify imports work
try:
    from ui.dockable_window import DockableMainWindow
    print("✓ DockableMainWindow imported successfully")
except ImportError as e:
    print("✗ Import error: {}".format(e))
    raise


def get_maya_main_window():
    """Get Maya main window as a Qt widget."""
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)


def launch_dockable():
    """Launch Multishot Manager with Maya docking using dockControl (simpler approach)."""

    from ui.main_window import MainWindow

    # Close existing window if it exists
    if MainWindow._instance is not None:
        try:
            MainWindow._instance.close()
            MainWindow._instance.deleteLater()
        except:
            pass

    # Create main window with Maya main window as parent
    main_window = MainWindow(parent=get_maya_main_window())

    # Get the window's pointer for Maya
    window_ptr = omui.MQtUtil.findWindow(main_window.objectName())

    if window_ptr:
        # Try to create a dockControl for it (Maya 2016 and earlier style)
        dock_control_name = "MultishotManagerDockControl"

        # Delete existing dock control if it exists
        if cmds.dockControl(dock_control_name, exists=True):
            cmds.deleteUI(dock_control_name)

        try:
            # Create dock control
            cmds.dockControl(
                dock_control_name,
                label="Multishot Manager",
                area="right",
                content=main_window.objectName(),
                allowedArea=["left", "right"],
                floating=True,
                width=900
            )
            print("\n✓ Multishot Manager launched with dockControl!")
            print("  - Drag to left or right edge to dock")
        except Exception as e:
            # If dockControl fails, just show as regular window
            print("Note: dockControl not available, showing as regular window")
            print("  Error: {}".format(e))
            main_window.show()
    else:
        # Fallback: show as regular window
        main_window.show()
        print("\n✓ Multishot Manager launched as floating window!")

    return main_window


# Launch dockable window
try:
    window = launch_dockable()
except Exception as e:
    print("✗ Failed to launch dockable window: {}".format(e))
    import traceback
    traceback.print_exc()
    raise

