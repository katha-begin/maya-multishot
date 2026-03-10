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
    from maya import OpenMayaUI as omui
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False
    cmds = None
    mel = None
    omui = None

# Import Qt
try:
    from PySide6 import QtWidgets, QtCore
    from shiboken6 import wrapInstance
except ImportError:
    try:
        from PySide2 import QtWidgets, QtCore
        from shiboken2 import wrapInstance
    except ImportError:
        QtWidgets = None
        QtCore = None
        wrapInstance = None

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

        # Add Nodes submenu
        nodes_submenu = cmds.menuItem(
            label="Nodes",
            subMenu=True,
            tearOff=True,
            annotation="Create CTX nodes manually",
            parent=menu
        )

        # Add node creation menu items
        cmds.menuItem(
            label="Create CTX_Sequence",
            command=lambda *args: create_sequence_node(),
            annotation="Create a new CTX_Sequence node manually",
            parent=nodes_submenu
        )

        cmds.menuItem(
            label="Create CTX_LightGaffer",
            command=lambda *args: create_gaffer_node(),
            annotation="Create a new CTX_LightGaffer node manually",
            parent=nodes_submenu
        )

        cmds.menuItem(
            label="Create CTX_LightContext",
            command=lambda *args: create_light_context_node(),
            annotation="Create a new CTX_LightContext node manually",
            parent=nodes_submenu
        )

        cmds.menuItem(
            label="Create CTX_Shot",
            command=lambda *args: create_shot_node(),
            annotation="Create a new CTX_Shot node manually",
            parent=nodes_submenu
        )

        cmds.menuItem(
            label="Create CTX_Asset",
            command=lambda *args: create_asset_node(),
            annotation="Create a new CTX_Asset node manually",
            parent=nodes_submenu
        )

        cmds.menuItem(
            label="Create CTX_Manager",
            command=lambda *args: create_manager_node(),
            annotation="Create a new CTX_Manager node (singleton)",
            parent=nodes_submenu
        )

        cmds.menuItem(divider=True, parent=nodes_submenu)

        cmds.menuItem(
            label="List All Sequences",
            command=lambda *args: list_all_sequences(),
            annotation="List all CTX_Sequence nodes in scene",
            parent=nodes_submenu
        )

        cmds.menuItem(
            label="List All Gaffers",
            command=lambda *args: list_all_gaffers(),
            annotation="List all CTX_LightGaffer nodes in scene",
            parent=nodes_submenu
        )

        cmds.menuItem(
            label="List All Light Contexts",
            command=lambda *args: list_all_light_contexts(),
            annotation="List all CTX_LightContext nodes in scene",
            parent=nodes_submenu
        )

        cmds.menuItem(
            label="List All Shots",
            command=lambda *args: list_all_shots(),
            annotation="List all CTX_Shot nodes in scene",
            parent=nodes_submenu
        )

        cmds.menuItem(
            label="List All Assets",
            command=lambda *args: list_all_assets(),
            annotation="List all CTX_Asset nodes in scene",
            parent=nodes_submenu
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
    """Reload the CTX Tools menu and all Python modules.

    Useful for development when menu items or code changes.
    This will:
    1. Reload all Python modules in the project
    2. Remove and recreate the menu
    """
    if not MAYA_AVAILABLE:
        return

    try:
        logger.info("Reloading CTX Tools menu and modules...")

        # Step 0: Clear __pycache__ so stale .pyc files cannot shadow fixed .py files
        import os
        import shutil
        try:
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            for dirpath, dirnames, _ in os.walk(repo_root):
                if '__pycache__' in dirnames:
                    cache_dir = os.path.join(dirpath, '__pycache__')
                    shutil.rmtree(cache_dir, ignore_errors=True)
            logger.info("Cleared __pycache__ directories")
        except Exception as cache_err:
            logger.warning("Could not clear __pycache__: {}".format(cache_err))

        # Step 1: Reload Python modules
        import sys

        # List of module prefixes to reload
        module_prefixes = [
            'core.',
            'ui.',
            'tools.',
            'utils.',
        ]

        # Find all loaded modules that match our prefixes
        modules_to_reload = []
        for module_name in list(sys.modules.keys()):
            for prefix in module_prefixes:
                if module_name.startswith(prefix) or module_name in ['core', 'ui', 'tools', 'utils']:
                    if sys.modules[module_name] is not None:
                        modules_to_reload.append(module_name)
                    break

        # Reload modules in reverse order (to handle dependencies)
        logger.info("Reloading {} modules...".format(len(modules_to_reload)))
        for module_name in reversed(modules_to_reload):
            try:
                if sys.modules[module_name] is not None:
                    import importlib
                    importlib.reload(sys.modules[module_name])
                    logger.debug("Reloaded: {}".format(module_name))
            except Exception as e:
                logger.warning("Failed to reload {}: {}".format(module_name, e))

        # Step 2: Remove old menu first
        remove_ctx_menu()

        # Step 3: Reload this module itself
        try:
            import importlib
            import tools.maya_menu as menu_module
            importlib.reload(menu_module)
            logger.info("Reloaded tools.maya_menu")

            # Step 4: Call create_ctx_menu from the RELOADED module
            menu_module.create_ctx_menu()

        except Exception as e:
            logger.warning("Failed to reload tools.maya_menu: {}".format(e))
            # Fallback: create menu with current module
            create_ctx_menu()

        logger.info("CTX Tools menu reloaded successfully!")

        cmds.confirmDialog(
            title="Reload Complete",
            message="CTX Tools menu and modules reloaded successfully!\n\n"
                    "Reloaded {} modules.".format(len(modules_to_reload)),
            button=["OK"],
            defaultButton="OK"
        )

    except Exception as e:
        logger.error("Failed to reload menu: {}".format(e))
        import traceback
        traceback.print_exc()
        cmds.confirmDialog(
            title="Reload Error",
            message="Failed to reload menu:\n{}".format(e),
            button=["OK"],
            defaultButton="OK"
        )


def get_maya_main_window():
    """Get Maya main window as a Qt widget."""
    if not MAYA_AVAILABLE or not omui or not wrapInstance:
        return None
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)


def open_context_manager():
    """Open the Context Manager (Shot Manager) dialog.

    This uses the same approach as launch_multishot_dockable.py to ensure consistency.
    """
    if not MAYA_AVAILABLE:
        logger.error("Maya is not available")
        return

    try:
        from ui.main_window import MainWindow

        # Close existing window if it exists
        if MainWindow._instance is not None:
            try:
                MainWindow._instance.close()
                MainWindow._instance.deleteLater()
            except:
                pass

        # Create main window with Maya main window as parent
        main_window = MainWindow(parent=get_maya_main_window())

        # Get the window's pointer for Maya
        window_ptr = omui.MQtUtil.findWindow(main_window.objectName())

        if window_ptr:
            # Try to create a dockControl for it
            dock_control_name = "MultishotManagerDockControl"

            # Delete existing dock control if it exists
            if cmds.dockControl(dock_control_name, exists=True):
                cmds.deleteUI(dock_control_name)

            try:
                # Create dock control with calculated width
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
                logger.info("Context Manager launched with dockControl")
            except Exception as e:
                # If dockControl fails, just show as regular window
                logger.info("dockControl not available, showing as regular window: {}".format(e))
                main_window.show()
        else:
            # Fallback: show as regular window
            main_window.show()
            logger.info("Context Manager launched as floating window")

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


# Global reference to keep dialogs alive (prevent garbage collection)
_gaffer_manager_dialog = None


def open_gaffer_manager():
    """Open the Gaffer Manager dialog."""
    global _gaffer_manager_dialog

    if not MAYA_AVAILABLE:
        logger.error("Maya is not available")
        return

    try:
        from ui.gaffer_manager_dialog import GafferManagerDialog
        from ui.main_window import MainWindow

        # Prefer Multishot Manager as parent so the Z-order chain is:
        # Gaffer (Tool) -> Multishot Manager (Tool) -> Maya main window.
        # Fall back to Maya main window when Multishot Manager is not open.
        parent = MainWindow._instance if MainWindow._instance is not None else get_maya_main_window()

        _gaffer_manager_dialog = GafferManagerDialog.open_or_raise(parent=parent)

        logger.info("Gaffer Manager opened")

    except Exception as e:
        logger.error("Failed to open Gaffer Manager: {}".format(e))
        import traceback
        traceback.print_exc()
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


# ============================================================================
# Node Creation Functions
# ============================================================================

def create_sequence_node():
    """Create a new CTX_Sequence node."""
    if not MAYA_AVAILABLE:
        logger.error("Maya is not available")
        return

    try:
        # Create the sequence node with default values
        from core.nodes.wrappers import CTXSequenceNode

        seq = CTXSequenceNode.create(
            sequenceCode='',
            sequenceName='',
            frameStart=1001,
            frameEnd=2000
        )

        # Select the created node
        cmds.select(seq.node_name)

        # Print to Script Editor
        print("\n" + "="*60)
        print("CREATED CTX_SEQUENCE NODE")
        print("="*60)
        print("Node: {}".format(seq.node_name))
        print("Edit attributes in Attribute Editor")
        print("="*60)

        logger.info("Created CTX_Sequence: {}".format(seq.node_name))

    except Exception as e:
        logger.error("Failed to create CTX_Sequence: {}".format(e))
        import traceback
        traceback.print_exc()
        cmds.warning("Failed to create CTX_Sequence: {}".format(e))


def create_gaffer_node():
    """Create a new CTX_LightGaffer node."""
    if not MAYA_AVAILABLE:
        logger.error("Maya is not available")
        return

    try:
        # Create the gaffer node with default values
        from core.nodes.wrappers import CTXLightGafferNode

        gaffer = CTXLightGafferNode.create(
            gafferName='',
            gafferType='custom',
            scopeCode='',
            enabled=True
        )

        # Select the created node
        cmds.select(gaffer.node_name)

        # Print to Script Editor
        print("\n" + "="*60)
        print("CREATED CTX_LIGHTGAFFER NODE")
        print("="*60)
        print("Node: {}".format(gaffer.node_name))
        print("Edit attributes in Attribute Editor")
        print("="*60)

        logger.info("Created CTX_LightGaffer: {}".format(gaffer.node_name))

    except Exception as e:
        logger.error("Failed to create CTX_LightGaffer: {}".format(e))
        import traceback
        traceback.print_exc()
        cmds.warning("Failed to create CTX_LightGaffer: {}".format(e))


def create_light_context_node():
    """Create a new CTX_LightContext node."""
    if not MAYA_AVAILABLE:
        logger.error("Maya is not available")
        return

    try:
        # Create the light context node with default values
        from core.nodes.wrappers import CTXLightContextNode

        light_ctx = CTXLightContextNode.create(
            lightName=''
        )

        # Select the created node
        cmds.select(light_ctx.node_name)

        # Print to Script Editor
        print("\n" + "="*60)
        print("CREATED CTX_LIGHTCONTEXT NODE")
        print("="*60)
        print("Node: {}".format(light_ctx.node_name))
        print("Edit attributes in Attribute Editor")
        print("="*60)

        logger.info("Created CTX_LightContext: {}".format(light_ctx.node_name))

    except Exception as e:
        logger.error("Failed to create CTX_LightContext: {}".format(e))
        import traceback
        traceback.print_exc()
        cmds.warning("Failed to create CTX_LightContext: {}".format(e))


def list_all_sequences():
    """List all CTX_Sequence nodes in the scene."""
    if not MAYA_AVAILABLE:
        logger.error("Maya is not available")
        return

    try:
        from core.nodes.wrappers import CTXSequenceNode

        sequences = CTXSequenceNode.list_all()

        if not sequences:
            cmds.confirmDialog(
                title="No Sequences Found",
                message="No CTX_Sequence nodes found in the scene.\n\n"
                        "Create one using: CTX Tools → Nodes → Create CTX_Sequence",
                button=["OK"],
                defaultButton="OK"
            )
            return

        # Build message
        message = "Found {} CTX_Sequence node(s):\n\n".format(len(sequences))

        for seq in sequences:
            code = seq.get_sequence_code()
            name = seq.get_sequence_name()
            frame_range = seq.get_frame_range()
            gaffer = seq.get_gaffer()

            message += "• {} ({})\n".format(code, name)
            message += "  Node: {}\n".format(seq.node_name)
            message += "  Frames: {}-{}\n".format(frame_range[0], frame_range[1])
            message += "  Gaffer: {}\n\n".format(gaffer or "(none)")

        cmds.confirmDialog(
            title="CTX_Sequence Nodes",
            message=message,
            button=["OK"],
            defaultButton="OK"
        )

        # Also print to Script Editor
        print("\n" + "="*60)
        print("CTX_SEQUENCE NODES")
        print("="*60)
        print(message)

    except Exception as e:
        logger.error("Failed to list sequences: {}".format(e))
        import traceback
        traceback.print_exc()
        cmds.confirmDialog(
            title="Error",
            message="Failed to list sequences:\n{}".format(e),
            button=["OK"],
            defaultButton="OK"
        )


def list_all_gaffers():
    """List all CTX_LightGaffer nodes in the scene."""
    if not MAYA_AVAILABLE:
        logger.error("Maya is not available")
        return

    try:
        from core.nodes.wrappers import CTXLightGafferNode

        gaffers = CTXLightGafferNode.list_all()

        if not gaffers:
            cmds.confirmDialog(
                title="No Gaffers Found",
                message="No CTX_LightGaffer nodes found in the scene.\n\n"
                        "Create one using: CTX Tools → Nodes → Create CTX_LightGaffer",
                button=["OK"],
                defaultButton="OK"
            )
            return

        # Build message
        message = "Found {} CTX_LightGaffer node(s):\n\n".format(len(gaffers))

        for gaffer in gaffers:
            name = gaffer.get_gaffer_name()
            gaffer_type = gaffer.get_gaffer_type()
            enabled = gaffer.is_enabled()
            parent = gaffer.get_parent_gaffer()
            lights = gaffer.get_lights()

            message += "• {} ({})\n".format(name, gaffer_type)
            message += "  Node: {}\n".format(gaffer.node_name)
            message += "  Enabled: {}\n".format(enabled)
            message += "  Parent: {}\n".format(parent.node_name if parent else "(none)")
            message += "  Lights: {}\n\n".format(len(lights))

        cmds.confirmDialog(
            title="CTX_LightGaffer Nodes",
            message=message,
            button=["OK"],
            defaultButton="OK"
        )

        # Also print to Script Editor
        print("\n" + "="*60)
        print("CTX_LIGHTGAFFER NODES")
        print("="*60)
        print(message)

    except Exception as e:
        logger.error("Failed to list gaffers: {}".format(e))
        import traceback
        traceback.print_exc()
        cmds.confirmDialog(
            title="Error",
            message="Failed to list gaffers:\n{}".format(e),
            button=["OK"],
            defaultButton="OK"
        )


def list_all_light_contexts():
    """List all CTX_LightContext nodes in the scene."""
    if not MAYA_AVAILABLE:
        logger.error("Maya is not available")
        return

    try:
        from core.nodes.wrappers import CTXLightContextNode

        light_contexts = CTXLightContextNode.list_all()

        if not light_contexts:
            cmds.confirmDialog(
                title="No Light Contexts Found",
                message="No CTX_LightContext nodes found in the scene.\n\n"
                        "Create one using: CTX Tools → Nodes → Create CTX_LightContext",
                button=["OK"],
                defaultButton="OK"
            )
            return

        # Build message
        message = "Found {} CTX_LightContext node(s):\n\n".format(len(light_contexts))

        for light_ctx in light_contexts:
            light_name = light_ctx.get_light_name()
            target_light = light_ctx.get_target_light()

            message += "• {}\n".format(light_name)
            message += "  Node: {}\n".format(light_ctx.node_name)
            message += "  Target: {}\n\n".format(target_light or "(none)")

        cmds.confirmDialog(
            title="CTX_LightContext Nodes",
            message=message,
            button=["OK"],
            defaultButton="OK"
        )

        # Also print to Script Editor
        print("\n" + "="*60)
        print("CTX_LIGHTCONTEXT NODES")
        print("="*60)
        print(message)

    except Exception as e:
        logger.error("Failed to list light contexts: {}".format(e))
        import traceback
        traceback.print_exc()
        cmds.confirmDialog(
            title="Error",
            message="Failed to list light contexts:\n{}".format(e),
            button=["OK"],
            defaultButton="OK"
        )


def create_shot_node():
    """Create a new CTX_Shot node."""
    if not MAYA_AVAILABLE:
        logger.error("Maya is not available")
        return

    try:
        # Create the shot node with default values
        from core.nodes.wrappers import CTXShotNode

        shot = CTXShotNode.create(
            ep_code='',
            seq_code='',
            shot_code='',
            display_layer_name='',
            is_active=False,
            start_frame=1001,
            end_frame=1100,
            frame_offset=0,
            fps=24.0,
            handles=10
        )

        # Select the created node
        cmds.select(shot.node_name)

        # Print to Script Editor
        print("\n" + "="*60)
        print("CREATED CTX_SHOT NODE")
        print("="*60)
        print("Node: {}".format(shot.node_name))
        print("Edit attributes in Attribute Editor")
        print("="*60)

        logger.info("Created CTX_Shot: {}".format(shot.node_name))

    except Exception as e:
        logger.error("Failed to create CTX_Shot: {}".format(e))
        import traceback
        traceback.print_exc()
        cmds.warning("Failed to create CTX_Shot: {}".format(e))


def create_asset_node():
    """Create a new CTX_Asset node."""
    if not MAYA_AVAILABLE:
        logger.error("Maya is not available")
        return

    try:
        # Create the asset node with default values
        from core.nodes.wrappers import CTXAssetNode

        asset = CTXAssetNode.create(
            asset_type='',
            asset_name='',
            variant='001',
            namespace='',
            file_path='',
            version='',
            is_loaded=False
        )

        # Select the created node
        cmds.select(asset.node_name)

        # Print to Script Editor
        print("\n" + "="*60)
        print("CREATED CTX_ASSET NODE")
        print("="*60)
        print("Node: {}".format(asset.node_name))
        print("Edit attributes in Attribute Editor")
        print("="*60)

        logger.info("Created CTX_Asset: {}".format(asset.node_name))

    except Exception as e:
        logger.error("Failed to create CTX_Asset: {}".format(e))
        import traceback
        traceback.print_exc()
        cmds.warning("Failed to create CTX_Asset: {}".format(e))


def create_manager_node():
    """Create a new CTX_Manager node (singleton)."""
    if not MAYA_AVAILABLE:
        logger.error("Maya is not available")
        return

    try:
        # Check if manager already exists
        from core.nodes.wrappers import CTXManagerNode

        existing = CTXManagerNode.get_manager()
        if existing is not None:
            cmds.warning("CTX_Manager already exists: {}".format(existing.node_name))
            cmds.select(existing.node_name)
            print("\n" + "="*60)
            print("CTX_MANAGER ALREADY EXISTS")
            print("="*60)
            print("Node: {}".format(existing.node_name))
            print("Only one CTX_Manager allowed per scene")
            print("="*60)
            return

        # Create the manager node with default values
        manager = CTXManagerNode.create(
            config_path='',
            project_root='',
            active_shot_id=''
        )

        # Select the created node
        cmds.select(manager.node_name)

        # Print to Script Editor
        print("\n" + "="*60)
        print("CREATED CTX_MANAGER NODE")
        print("="*60)
        print("Node: {}".format(manager.node_name))
        print("Edit attributes in Attribute Editor")
        print("WARNING: Only one CTX_Manager allowed per scene")
        print("="*60)

        logger.info("Created CTX_Manager: {}".format(manager.node_name))

    except Exception as e:
        logger.error("Failed to create CTX_Manager: {}".format(e))
        import traceback
        traceback.print_exc()
        cmds.warning("Failed to create CTX_Manager: {}".format(e))


def list_all_shots():
    """List all CTX_Shot nodes in the scene."""
    if not MAYA_AVAILABLE:
        logger.error("Maya is not available")
        return

    try:
        from core.nodes.wrappers import CTXShotNode

        shots = CTXShotNode.list_all()

        if not shots:
            cmds.confirmDialog(
                title="No Shots Found",
                message="No CTX_Shot nodes found in the scene.\n\n"
                        "Create one using: CTX Tools → Nodes → Create CTX_Shot",
                button=["OK"],
                defaultButton="OK"
            )
            return

        # Build message
        message = "Found {} CTX_Shot node(s):\n\n".format(len(shots))

        for shot in shots:
            shot_id = shot.get_shot_id()
            frame_range = shot.get_attribute('start_frame'), shot.get_attribute('end_frame')
            is_active = shot.get_attribute('is_active')

            message += "• {}\n".format(shot_id)
            message += "  Node: {}\n".format(shot.node_name)
            message += "  Frames: {}-{}\n".format(frame_range[0], frame_range[1])
            message += "  Active: {}\n\n".format("Yes" if is_active else "No")

        cmds.confirmDialog(
            title="CTX_Shot Nodes",
            message=message,
            button=["OK"],
            defaultButton="OK"
        )

        # Also print to Script Editor
        print("\n" + "="*60)
        print("CTX_SHOT NODES")
        print("="*60)
        print(message)

    except Exception as e:
        logger.error("Failed to list shots: {}".format(e))
        import traceback
        traceback.print_exc()
        cmds.confirmDialog(
            title="Error",
            message="Failed to list shots:\n{}".format(e),
            button=["OK"],
            defaultButton="OK"
        )


def list_all_assets():
    """List all CTX_Asset nodes in the scene."""
    if not MAYA_AVAILABLE:
        logger.error("Maya is not available")
        return

    try:
        from core.nodes.wrappers import CTXAssetNode

        assets = CTXAssetNode.list_all()

        if not assets:
            cmds.confirmDialog(
                title="No Assets Found",
                message="No CTX_Asset nodes found in the scene.\n\n"
                        "Create one using: CTX Tools → Nodes → Create CTX_Asset",
                button=["OK"],
                defaultButton="OK"
            )
            return

        # Build message
        message = "Found {} CTX_Asset node(s):\n\n".format(len(assets))

        for asset in assets:
            asset_id = asset.get_asset_id()
            file_path = asset.get_attribute('file_path')
            version = asset.get_attribute('version')
            is_loaded = asset.get_attribute('is_loaded')

            message += "• {}\n".format(asset_id)
            message += "  Node: {}\n".format(asset.node_name)
            message += "  Version: {}\n".format(version or "(none)")
            message += "  Loaded: {}\n\n".format("Yes" if is_loaded else "No")

        cmds.confirmDialog(
            title="CTX_Asset Nodes",
            message=message,
            button=["OK"],
            defaultButton="OK"
        )

        # Also print to Script Editor
        print("\n" + "="*60)
        print("CTX_ASSET NODES")
        print("="*60)
        print(message)

    except Exception as e:
        logger.error("Failed to list assets: {}".format(e))
        import traceback
        traceback.print_exc()
        cmds.confirmDialog(
            title="Error",
            message="Failed to list assets:\n{}".format(e),
            button=["OK"],
            defaultButton="OK"
        )


# ============================================================================
# Installation
# ============================================================================

# Convenience function for userSetup.py
def install():
    """Install the CTX Tools menu.

    This is a convenience function that can be called from userSetup.py
    to automatically create the menu when Maya starts.

    Example userSetup.py:
        import sys
        sys.path.append(r'T:\pipeline\development\maya\maya-multishot')

        from tools import maya_menu
        maya_menu.install()
    """
    if MAYA_AVAILABLE:
        # Use evalDeferred to ensure Maya's UI is fully initialized before
        # creating the menu. Without this, $gMainWindow is not yet available
        # and the menu silently fails to appear.
        cmds.evalDeferred(lambda: create_ctx_menu(), lowestPriority=True)
        logger.info("CTX Tools menu will be created when Maya is ready")
    else:
        logger.warning("Maya is not available, menu will not be created")


def reload_all_modules():
    """Reload all project modules without recreating menu.

    This is useful for development when you want to reload code changes
    without recreating the menu UI.

    Usage in Maya Script Editor:
        from tools import maya_menu
        maya_menu.reload_all_modules()
    """
    import sys
    import importlib

    # List of module prefixes to reload
    module_prefixes = [
        'core.',
        'ui.',
        'tools.',
        'utils.',
    ]

    # Find all loaded modules that match our prefixes
    modules_to_reload = []
    for module_name in list(sys.modules.keys()):
        for prefix in module_prefixes:
            if module_name.startswith(prefix) or module_name in ['core', 'ui', 'tools', 'utils']:
                if sys.modules[module_name] is not None:
                    modules_to_reload.append(module_name)
                break

    # Reload modules in reverse order (to handle dependencies)
    print("\n" + "="*60)
    print("RELOADING {} MODULES".format(len(modules_to_reload)))
    print("="*60)

    reloaded_count = 0
    failed_count = 0

    for module_name in reversed(modules_to_reload):
        try:
            if sys.modules[module_name] is not None:
                importlib.reload(sys.modules[module_name])
                print("✓ Reloaded: {}".format(module_name))
                reloaded_count += 1
        except Exception as e:
            print("✗ Failed: {} - {}".format(module_name, e))
            failed_count += 1

    print("="*60)
    print("RELOAD COMPLETE: {} succeeded, {} failed".format(reloaded_count, failed_count))
    print("="*60)

    return reloaded_count, failed_count

