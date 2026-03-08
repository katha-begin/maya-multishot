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
3. Update the CTX_TOOLS_PATH to point to your maya-multishot directory
4. Restart Maya

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

# Path to maya-multishot repository
# Update this to match your installation location
CTX_TOOLS_PATH = r"E:/dev/maya-multishot"

# Alternative: Use environment variable
# CTX_TOOLS_PATH = os.environ.get('CTX_TOOLS_PATH', r"E:/dev/maya-multishot")

# ============================================================================
# DO NOT MODIFY BELOW THIS LINE
# ============================================================================

def setup_ctx_tools():
    """Set up CTX Tools in Maya."""
    
    # Add CTX Tools to Python path
    if CTX_TOOLS_PATH not in sys.path:
        sys.path.insert(0, CTX_TOOLS_PATH)
        print("CTX Tools: Added {} to Python path".format(CTX_TOOLS_PATH))
    
    # Verify path exists
    if not os.path.exists(CTX_TOOLS_PATH):
        print("CTX Tools: WARNING - Path does not exist: {}".format(CTX_TOOLS_PATH))
        return
    
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

