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

# Clear __pycache__ directories so stale .pyc files never shadow new .py files.
# This is critical on remote/network machines where deployment copies new .py files
# but leaves old compiled bytecode in place.
import shutil
_pycache_cleared = 0
for _root, _dirs, _files in os.walk(repo_root):
    for _d in list(_dirs):
        if _d == '__pycache__':
            _pycache_path = os.path.join(_root, _d)
            try:
                shutil.rmtree(_pycache_path)
                _pycache_cleared += 1
            except Exception as _e:
                print("Warning: could not remove {}: {}".format(_pycache_path, _e))
            _dirs.remove(_d)  # don't recurse into it
if _pycache_cleared:
    print("Cleared {} __pycache__ directories".format(_pycache_cleared))

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

    dock_control_name = "MultishotManagerDockControl"

    # Remove any existing dockControl FIRST so there is no embedded window
    # with the same objectName when we create the new one. If we delete it
    # after creating the new window, MQtUtil.findWindow() can return the
    # stale embedded widget's pointer instead of the new window's pointer,
    # which causes dockControl to silently fail on the second launch.
    if cmds.dockControl(dock_control_name, exists=True):
        cmds.deleteUI(dock_control_name)

    # Close existing instance if it survived module clearing
    if MainWindow._instance is not None:
        try:
            MainWindow._instance.close()
            MainWindow._instance.deleteLater()
        except:
            pass
        MainWindow._instance = None

    # Flush any pending deleteLater() events before creating new window
    QtWidgets.QApplication.processEvents()

    # Create main window with Maya main window as parent
    main_window = MainWindow(parent=get_maya_main_window())

    # Allow Qt to register the new window with Maya's window manager
    QtWidgets.QApplication.processEvents()

    # Get the window's pointer for Maya
    window_ptr = omui.MQtUtil.findWindow(main_window.objectName())

    if window_ptr:
        try:
            # Create dock control with calculated width
            # Get recommended width from MainWindow class
            recommended_width = MainWindow.get_recommended_width()

            cmds.dockControl(
                dock_control_name,
                label="Multishot Manager",
                area="right",
                content=main_window.objectName(),
                allowedArea=["left", "right"],
                floating=True,
                width=recommended_width
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

