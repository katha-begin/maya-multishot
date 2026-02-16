# -*- coding: utf-8 -*-
"""Launch script for Multishot Manager in Maya.

Run this in Maya Script Editor:
    import sys
    sys.path.insert(0, r'E:/dev/maya-multishot')
    exec(open(r'E:/dev/maya-multishot/launch_multishot_manager.py').read())
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import os
import logging

# Add repository root to path if not already there
# When using exec(), __file__ is not defined, so we need to find the repo root differently
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

# Verify imports work
try:
    from config.project_config import ProjectConfig
    print("✓ ProjectConfig imported successfully")
    
    # Verify method exists
    config = ProjectConfig()
    if hasattr(config, 'get_token_values'):
        print("✓ ProjectConfig.get_token_values() method exists")
    else:
        print("✗ WARNING: ProjectConfig.get_token_values() method NOT found!")
    
    from core.context import ContextManager
    print("✓ ContextManager imported successfully")
    
    from core.asset_scanner import AssetScanner
    print("✓ AssetScanner imported successfully")
    
    from ui.main_window import MainWindow
    print("✓ MainWindow imported successfully")
    
except ImportError as e:
    print("✗ Import error: {}".format(e))
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
    print("\n✓ Multishot Manager launched successfully!")
    print("  - Only one window instance allowed at a time")
    print("  - Window stays on top of Maya")
    print("\nTo dock the window:")
    print("  1. Drag the window title bar to Maya's left or right edge")
    print("  2. Or use: Window > Saved Layouts > Edit Layouts")
    print("  3. Window will resize automatically based on table content")

except Exception as e:
    print("✗ Failed to launch window: {}".format(e))
    import traceback
    traceback.print_exc()
    raise

