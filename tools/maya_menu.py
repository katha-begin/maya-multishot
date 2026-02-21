# -*- coding: utf-8 -*-
"""Maya Menu Integration - CTX Tools Menu

This module creates and manages the CTX Tools menu in Maya's main menu bar.

Features:
- Creates "CTX Tools" menu in Maya's main menu bar
- Adds Context Manager (Shot Manager) menu item
- Adds Gaffer Manager menu item
- Extensible for future tools
- Handles menu cleanup on reload

Usage:
    # In Maya Script Editor or userSetup.py
    from tools import maya_menu
    maya_menu.create_ctx_menu()
    
    # To remove menu
    maya_menu.remove_ctx_menu()

Author: Pipeline TD
Date: 2026-02-21
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging

try:
    import maya.cmds as cmds
    import maya.mel as mel
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False
    cmds = None
    mel = None

logger = logging.getLogger(__name__)

# Menu name constant
CTX_MENU_NAME = "CTXToolsMenu"
CTX_MENU_LABEL = "CTX Tools"


def create_ctx_menu():
    """Create the CTX Tools menu in Maya's main menu bar.
    
    Creates a menu with the following items:
    - Context Manager (Shot Manager)
    - Gaffer Manager
    - Separator
    - About
    
    Returns:
        str: Menu name if created successfully, None otherwise
    """
    if not MAYA_AVAILABLE:
        logger.error("Maya is not available, cannot create menu")
        return None
    
    try:
        # Remove existing menu if it exists
        remove_ctx_menu()
        
        # Get Maya's main window
        main_window = mel.eval('$tmpVar=$gMainWindow')
        
        # Create the menu
        menu = cmds.menu(
            CTX_MENU_NAME,
            label=CTX_MENU_LABEL,
            parent=main_window,
            tearOff=True
        )
        
        # Add Context Manager menu item
        cmds.menuItem(
            label="Context Manager",
            command=lambda *args: open_context_manager(),
            annotation="Open Context Manager (Shot Manager)",
            parent=menu
        )
        
        # Add Gaffer Manager menu item
        cmds.menuItem(
            label="Gaffer Manager",
            command=lambda *args: open_gaffer_manager(),
            annotation="Open Light Gaffer Manager",
            parent=menu
        )
        
        # Add separator
        cmds.menuItem(divider=True, parent=menu)
        
        # Add Asset Manager menu item (if available)
        cmds.menuItem(
            label="Asset Manager",
            command=lambda *args: open_asset_manager(),
            annotation="Open Asset Manager",
            parent=menu
        )
        
        # Add separator
        cmds.menuItem(divider=True, parent=menu)
        
        # Add Reload Menu item
        cmds.menuItem(
            label="Reload Menu",
            command=lambda *args: reload_menu(),
            annotation="Reload CTX Tools menu",
            parent=menu
        )
        
        # Add About menu item
        cmds.menuItem(
            label="About",
            command=lambda *args: show_about(),
            annotation="About CTX Tools",
            parent=menu
        )
        
        logger.info("CTX Tools menu created successfully")
        return menu
    
    except Exception as e:
        logger.error("Failed to create CTX Tools menu: {}".format(e))
        return None


def remove_ctx_menu():
    """Remove the CTX Tools menu from Maya's main menu bar.
    
    Returns:
        bool: True if menu was removed, False otherwise
    """
    if not MAYA_AVAILABLE:
        return False
    
    try:
        if cmds.menu(CTX_MENU_NAME, exists=True):
            cmds.deleteUI(CTX_MENU_NAME, menu=True)
            logger.info("CTX Tools menu removed")
            return True
        return False
    
    except Exception as e:
        logger.error("Failed to remove CTX Tools menu: {}".format(e))
        return False


def reload_menu():
    """Reload the CTX Tools menu.

    Useful for development when menu items change.
    """
    logger.info("Reloading CTX Tools menu...")
    remove_ctx_menu()
    create_ctx_menu()


def open_context_manager():
    """Open the Context Manager (Shot Manager) dialog.

    This opens the main window which includes the shot manager functionality.
    """
    if not MAYA_AVAILABLE:
        logger.error("Maya is not available")
        return

    try:
        from ui.main_window import MainWindow

        # Create and show main window
        # Check if window already exists
        for widget in QtWidgets.QApplication.topLevelWidgets():
            if isinstance(widget, MainWindow):
                widget.show()
                widget.raise_()
                widget.activateWindow()
                logger.info("Context Manager window already exists, bringing to front")
                return

        # Create new window
        window = MainWindow()
        window.show()

        logger.info("Context Manager opened")

    except Exception as e:
        logger.error("Failed to open Context Manager: {}".format(e))
        import traceback
        traceback.print_exc()
        cmds.confirmDialog(
            title="Error",
            message="Failed to open Context Manager:\n{}".format(e),
            button=["OK"],
            defaultButton="OK"
        )


def open_gaffer_manager():
    """Open the Gaffer Manager dialog."""
    if not MAYA_AVAILABLE:
        logger.error("Maya is not available")
        return

    try:
        from ui.gaffer_manager_dialog import GafferManagerDialog

        # Create and show gaffer manager
        dialog = GafferManagerDialog()
        dialog.show()

        logger.info("Gaffer Manager opened")

    except Exception as e:
        logger.error("Failed to open Gaffer Manager: {}".format(e))
        cmds.confirmDialog(
            title="Error",
            message="Failed to open Gaffer Manager:\n{}".format(e),
            button=["OK"],
            defaultButton="OK"
        )


def open_asset_manager():
    """Open the Asset Manager dialog.

    Note: Asset Manager requires a shot to be selected. This will show
    a message if no shot is available.
    """
    if not MAYA_AVAILABLE:
        logger.error("Maya is not available")
        return

    try:
        # Asset Manager requires shot data and config
        # For now, show a message that it needs to be opened from Context Manager
        cmds.confirmDialog(
            title="Asset Manager",
            message="Asset Manager must be opened from the Context Manager.\n\n"
                    "Steps:\n"
                    "1. Open Context Manager (CTX Tools → Context Manager)\n"
                    "2. Select a shot in the table\n"
                    "3. Click 'Manage Assets' button\n\n"
                    "The Asset Manager will open for the selected shot.",
            button=["OK"],
            defaultButton="OK"
        )

        logger.info("Asset Manager info shown")

    except Exception as e:
        logger.error("Failed to show Asset Manager info: {}".format(e))
        cmds.confirmDialog(
            title="Error",
            message="Failed to show Asset Manager info:\n{}".format(e),
            button=["OK"],
            defaultButton="OK"
        )


def show_about():
    """Show about dialog with CTX Tools information."""
    if not MAYA_AVAILABLE:
        return

    about_text = """CTX Tools - Maya Multi-Shot Pipeline

Version: 1.0
Date: 2026-02-21

Tools:
- Context Manager: Multi-shot context management
- Gaffer Manager: Hierarchical light management
- Asset Manager: Asset reference management

Features:
- Multi-shot support in single scene
- Token-based path resolution
- Hierarchical light gaffer system
- Display layer management
- Cross-platform support

Repository:
https://github.com/katha-begin/maya-multishot.git

Documentation:
See docs/ folder for complete documentation
"""

    cmds.confirmDialog(
        title="About CTX Tools",
        message=about_text,
        button=["OK"],
        defaultButton="OK"
    )


# Convenience function for userSetup.py
def install():
    """Install the CTX Tools menu.

    This is a convenience function that can be called from userSetup.py
    to automatically create the menu when Maya starts.

    Example userSetup.py:
        import sys
        sys.path.append('E:/dev/maya-multishot')

        from tools import maya_menu
        maya_menu.install()
    """
    if MAYA_AVAILABLE:
        # Use evalDeferred to ensure Maya is fully initialized
        cmds.evalDeferred(create_ctx_menu)
        logger.info("CTX Tools menu will be created when Maya is ready")
    else:
        logger.warning("Maya is not available, menu will not be created")

