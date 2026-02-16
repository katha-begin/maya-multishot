#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Launch Context Manager UI in Maya.

This script can be:
1. Run directly in Maya Script Editor
2. Added to a Maya shelf button
3. Added to userSetup.py for auto-launch

Usage in Maya Script Editor:
    import launch_ui_maya
    launch_ui_maya.launch()

Or as a shelf button (copy this entire script to the shelf button command).
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import os


def launch():
    """Launch the Context Manager UI."""
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add to Python path if not already there
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
        print("Added to Python path: {}".format(script_dir))
    
    # Import and launch UI
    try:
        from ui import main_window
        
        # Close existing window if it exists
        try:
            if hasattr(main_window, '_context_manager_window'):
                if main_window._context_manager_window:
                    main_window._context_manager_window.close()
                    main_window._context_manager_window.deleteLater()
        except:
            pass
        
        # Launch new window
        window = main_window.show()
        
        # Store reference to prevent garbage collection
        main_window._context_manager_window = window
        
        print("Context Manager UI launched successfully!")
        return window
        
    except Exception as e:
        print("Error launching Context Manager UI:")
        print(str(e))
        import traceback
        traceback.print_exc()
        return None


# If run directly in Maya Script Editor
if __name__ == '__main__':
    launch()

