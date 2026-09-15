# -*- coding: utf-8 -*-
"""Launch script for Batch Render dialog in Maya with docking support.

Works wherever the repo is installed. Run it from the CTX Tools menu, or in
the Maya Script Editor:
    import sys
    sys.path.insert(0, r'<path to maya-multishot>')
    exec(open(r'<path to maya-multishot>/launch_batch_render_dockable.py').read())
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
# Only modules loaded from a CTX Tools checkout are touched.
sys.modules.pop('ctx_bootstrap', None)
import ctx_bootstrap  # noqa: E402
ctx_bootstrap.prepare(repo_root)

logging.basicConfig(level=logging.INFO,
                    format='%(name)s - %(levelname)s: %(message)s')

try:
    import maya.cmds as cmds
    from maya import OpenMayaUI as omui
except ImportError:
    print("ERROR: This script must be run inside Maya!")
    raise

try:
    from PySide6 import QtWidgets, QtCore
    from shiboken6 import wrapInstance
except ImportError:
    from PySide2 import QtWidgets, QtCore
    from shiboken2 import wrapInstance


def get_maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)


def launch_dockable():
    from ui.batch_render_dialog import BatchRenderDialog

    dock_control_name = 'BatchRenderDockControl'

    # Remove old dockControl FIRST to avoid objectName collision with the new window
    if cmds.dockControl(dock_control_name, exists=True):
        cmds.deleteUI(dock_control_name)

    # Close existing instance if it survived module clearing
    if BatchRenderDialog._instance is not None:
        try:
            BatchRenderDialog._instance.close()
            BatchRenderDialog._instance.deleteLater()
        except Exception:
            pass
        BatchRenderDialog._instance = None

    # Flush pending deleteLater() events before creating new window
    QtWidgets.QApplication.processEvents()

    dlg = BatchRenderDialog(parent=get_maya_main_window())
    BatchRenderDialog._instance = dlg

    # Allow Qt to register the new window with Maya's window manager
    QtWidgets.QApplication.processEvents()

    window_ptr = omui.MQtUtil.findWindow(dlg.objectName())

    if window_ptr:
        try:
            cmds.dockControl(
                dock_control_name,
                label='Batch Render',
                area='right',
                content=dlg.objectName(),
                allowedArea=['left', 'right'],
                floating=True,
                width=460,
            )
            print("Batch Render launched with dockControl")
        except Exception as e:
            print("dockControl not available, showing as floating window: {}".format(e))
            dlg.show()
    else:
        dlg.show()

    return dlg


try:
    window = launch_dockable()
except Exception as e:
    print("Failed to launch Batch Render: {}".format(e))
    import traceback
    traceback.print_exc()
    raise
