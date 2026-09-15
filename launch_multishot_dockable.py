# -*- coding: utf-8 -*-
"""Launch script for Multishot Manager in Maya with docking support.

Works wherever the repo is installed. Run it from the CTX Tools menu, or in
the Maya Script Editor:
    import sys
    sys.path.insert(0, r'<path to maya-multishot>')
    exec(open(r'<path to maya-multishot>/launch_multishot_dockable.py').read())
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import os
import logging

def _find_repo_root():
    """Return the maya-multishot folder this launcher belongs to.

    Uses this file's folder when __file__ is set, otherwise the first sys.path
    entry holding the repo: exec() from the Script Editor defines no __file__,
    and Maya can leave a stale one behind from userSetup.py.
    """
    candidates = []
    try:
        candidates.append(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        pass
    candidates.extend(sys.path)
    for path in candidates:
        if path and os.path.isfile(os.path.join(path, 'ctx_bootstrap.py')):
            return os.path.abspath(path)
    raise RuntimeError(
        "Cannot find the maya-multishot folder. Add it to sys.path first:\n"
        "    import sys; sys.path.insert(0, r'<path to maya-multishot>')")


# Put this checkout first on sys.path so its packages win over any other copy
repo_root = _find_repo_root()
sys.path[:] = [p for p in sys.path
               if os.path.normcase(os.path.abspath(p)) != os.path.normcase(repo_root)]
sys.path.insert(0, repo_root)

# Clear stale bytecode and this tool's loaded modules so the code on disk runs.
# Only modules loaded from a CTX Tools checkout are touched -- other tools that
# also have "core"/"ui"/"config" packages keep theirs.
sys.modules.pop('ctx_bootstrap', None)
import ctx_bootstrap  # noqa: E402
_purged = ctx_bootstrap.prepare(repo_root)
if _purged:
    print("Cleared {} cached modules".format(len(_purged)))

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
    print("[FAIL] ERROR: This script must be run inside Maya!")
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
    print("[OK] DockableMainWindow imported successfully")
except ImportError as e:
    print("[FAIL] Import error: {}".format(e))
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
            print("\n[OK] Multishot Manager launched with dockControl!")
            print("  - Drag to left or right edge to dock")
        except Exception as e:
            # If dockControl fails, just show as regular window
            print("Note: dockControl not available, showing as regular window")
            print("  Error: {}".format(e))
            main_window.show()
    else:
        # Fallback: show as regular window
        main_window.show()
        print("\n[OK] Multishot Manager launched as floating window!")

    return main_window


# Launch dockable window
try:
    window = launch_dockable()
except Exception as e:
    print("[FAIL] Failed to launch dockable window: {}".format(e))
    import traceback
    traceback.print_exc()
    raise

