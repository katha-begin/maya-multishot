# -*- coding: utf-8 -*-
"""Launch script for Multishot Manager in Maya.

Works wherever the repo is installed. In the Maya Script Editor:
    import sys
    sys.path.insert(0, r'<path to maya-multishot>')
    exec(open(r'<path to maya-multishot>/launch_multishot_manager.py').read())
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
_purged = ctx_bootstrap.prepare(repo_root)
if _purged:
    print("Cleared {} cached modules".format(len(_purged)))

# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s: %(message)s'
)

# Verify imports work
try:
    from config.project_config import ProjectConfig
    print("[OK] ProjectConfig imported successfully")
    
    # Verify method exists
    config = ProjectConfig()
    if hasattr(config, 'get_token_values'):
        print("[OK] ProjectConfig.get_token_values() method exists")
    else:
        print("[FAIL] WARNING: ProjectConfig.get_token_values() method NOT found!")
    
    from core.context import ContextManager
    print("[OK] ContextManager imported successfully")
    
    from core.asset_scanner import AssetScanner
    print("[OK] AssetScanner imported successfully")
    
    from ui.main_window import MainWindow
    print("[OK] MainWindow imported successfully")
    
except ImportError as e:
    print("[FAIL] Import error: {}".format(e))
    raise

# Launch window
try:
    # Import Qt for finding existing windows
    try:
        from PySide6 import QtWidgets
    except ImportError:
        from PySide2 import QtWidgets

    # Find and close any existing Multishot Manager windows by object name
    app = QtWidgets.QApplication.instance()
    if app:
        for widget in app.allWidgets():
            if widget.objectName() == "MultishotManagerWindow":
                print("Found existing window, closing it...")
                widget.close()
                widget.deleteLater()
        QtWidgets.QApplication.processEvents()

    # The MainWindow class has a singleton pattern built-in
    # It will automatically close any existing instance
    window = MainWindow()
    window.show()
    print("\n[OK] Multishot Manager launched successfully!")
    print("  - Only one window instance allowed at a time")
    print("  - Window stays on top of Maya")
    print("\nTo dock the window:")
    print("  1. Drag the window title bar to Maya's left or right edge")
    print("  2. Or use: Window > Saved Layouts > Edit Layouts")
    print("  3. Window will resize automatically based on table content")

except Exception as e:
    print("[FAIL] Failed to launch window: {}".format(e))
    import traceback
    traceback.print_exc()
    raise

