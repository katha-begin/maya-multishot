# -*- coding: utf-8 -*-
"""Launch script for Batch Render dialog in Maya with docking support.

Run this in Maya Script Editor:
    import sys
    sys.path.insert(0, r'E:/dev/maya-multishot')
    exec(open(r'E:/dev/maya-multishot/launch_batch_render_dockable.py').read())
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import os
import logging

try:
    repo_root = os.path.dirname(os.path.abspath(__file__))
except NameError:
    repo_root = r'E:/dev/maya-multishot'

if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

modules_to_remove = [key for key in list(sys.modules.keys())
                     if key.startswith(('ui', 'core', 'config', 'tools'))]
for module in modules_to_remove:
    del sys.modules[module]

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
