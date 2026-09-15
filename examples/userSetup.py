# -*- coding: utf-8 -*-
"""Example userSetup.py for CTX Tools

This file should be placed in your Maya scripts directory to automatically
load CTX Tools when Maya starts.

Maya Scripts Directory Locations:
- Windows: C:/Users/<username>/Documents/maya/<version>/scripts/
- Linux: ~/maya/<version>/scripts/
- Mac: ~/Library/Preferences/Autodesk/maya/<version>/scripts/

Usage:
1. Copy this file to your Maya scripts directory
2. Rename it to "userSetup.py" (or append to existing userSetup.py)
3. Set CTX_TOOLS_PATH below to the folder you cloned maya-multishot into
   (or set the CTX_TOOLS_PATH environment variable, e.g. in Maya.env)
4. Restart Maya

The repo can live anywhere -- this path is the only place that needs it.
Works on Python 2.7 and 3.x Maya.

The CTX Tools menu will appear in Maya's main menu bar.

Author: Pipeline TD
Date: 2026-02-21
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import os

# ============================================================================
# CONFIGURATION - UPDATE THIS PATH
# ============================================================================

# Folder you cloned maya-multishot into. The CTX_TOOLS_PATH environment
# variable, when set, wins over the value written here.
CTX_TOOLS_PATH = os.environ.get('CTX_TOOLS_PATH', r"<path to maya-multishot>")

# ============================================================================
# DO NOT MODIFY BELOW THIS LINE
# ============================================================================

def setup_ctx_tools():
    """Set up CTX Tools in Maya."""

    # Verify path exists
    if not os.path.isdir(CTX_TOOLS_PATH):
        print("CTX Tools: WARNING - Path does not exist: {}".format(CTX_TOOLS_PATH))
        return

    # Put CTX Tools first on the Python path so its packages ("core", "ui",
    # "tools", "config") win over same-named packages from other tools
    if CTX_TOOLS_PATH in sys.path:
        sys.path.remove(CTX_TOOLS_PATH)
    sys.path.insert(0, CTX_TOOLS_PATH)
    print("CTX Tools: Added {} to Python path".format(CTX_TOOLS_PATH))

    try:
        # Import and install menu
        from tools import maya_menu
        maya_menu.install()

        print("CTX Tools: Menu will be created when Maya is ready")
        print("CTX Tools: Available tools:")
        print("  - Context Manager (Shot Manager)")
        print("  - Gaffer Manager (Light Management)")
        print("  - Asset Manager")

    except ImportError as e:
        print("CTX Tools: Failed to import maya_menu: {}".format(e))
        print("CTX Tools: Please check that CTX_TOOLS_PATH is correct")

    except Exception as e:
        print("CTX Tools: Failed to set up menu: {}".format(e))


# Run setup
setup_ctx_tools()

print("=" * 80)
print("CTX Tools userSetup.py loaded")
print("Path: {}".format(CTX_TOOLS_PATH))
print("=" * 80)
