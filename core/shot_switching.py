# -*- coding: utf-8 -*-
"""Shot Switching - Switch between shots and manage visibility.

This module provides shot switching functionality:
- Switch active shot
- Update display layer visibility
- Trigger context change callbacks
- Track switching history
- Performance optimization

Author: Pipeline TD
Date: 2024
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging

logger = logging.getLogger(__name__)

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    # Mock Maya commands for testing outside Maya
    class MockCmds(object):
        """Mock Maya commands for testing."""
        
        def objExists(self, name):
            """Mock objExists."""
            return False
        
        def getAttr(self, attr):
            """Mock getAttr."""
            return None
        
        def setAttr(self, attr, value, **kwargs):
            """Mock setAttr."""
            pass
        
        def listConnections(self, node, **kwargs):
            """Mock listConnections."""
            return []
    
    cmds = MockCmds()
    MAYA_AVAILABLE = False


class ShotSwitcher(object):
    """Manage shot switching and visibility updates.
    
    This class handles:
    - Switching active shot
    - Updating layer visibility
    - Triggering callbacks
    - Tracking history
    
    Example:
        >>> from core.shot_switching import ShotSwitcher
        >>> from core.display_layers import DisplayLayerManager
        >>> 
        >>> switcher = ShotSwitcher(layer_manager)
        >>> 
        >>> # Switch to shot
        >>> switcher.switch_to_shot('CTX_Shot_SH0170', 'CTX_Manager')
        >>> 
        >>> # Get active shot
        >>> active = switcher.get_active_shot('CTX_Manager')
        >>> print(active)
        'CTX_Shot_SH0170'
    """
    
    def __init__(self, layer_manager, context_manager=None):
        """Initialize shot switcher.
        
        Args:
            layer_manager (DisplayLayerManager): Display layer manager instance
            context_manager (ContextManager, optional): Context manager for callbacks
        """
        self.layer_manager = layer_manager
        self.context_manager = context_manager
        self.history = []  # List of shot nodes in switch order
        self.max_history = 20  # Maximum history entries
    
    def switch_to_shot(self, shot_node, manager_node, hide_others=True):
        """Switch to a different shot.

        Args:
            shot_node (str): CTX_Shot node name to switch to
            manager_node (str): CTX_Manager node name
            hide_others (bool): If True, hide other shots' layers

        Returns:
            bool: True if switch successful
        """
        logger.info("=" * 60)
        logger.info("SWITCHING TO SHOT: {}".format(shot_node))

        # Validate nodes exist
        if not cmds.objExists(shot_node):
            raise ValueError("Shot node '{}' does not exist".format(shot_node))

        if not cmds.objExists(manager_node):
            raise ValueError("Manager node '{}' does not exist".format(manager_node))

        # Get shot info
        ep = cmds.getAttr("{}.ep_code".format(shot_node))
        seq = cmds.getAttr("{}.seq_code".format(shot_node))
        shot = cmds.getAttr("{}.shot_code".format(shot_node))
        logger.info("Shot info: ep={}, seq={}, shot={}".format(ep, seq, shot))

        # Ensure global display layers exist (CTX_Active and CTX_Inactive)
        self.layer_manager.ensure_global_layers()
        logger.info("Ensured global display layers exist")

        # Update manager's active shot
        cmds.setAttr("{}.active_shot_id".format(manager_node), shot_node, type="string")
        logger.info("Updated manager active_shot_id to: {}".format(shot_node))

        # Deactivate other shots FIRST (before activating the new one)
        if hide_others:
            logger.info("Deactivating other shots...")
            self._deactivate_other_shots(shot_node, manager_node)

        # Set this shot as active (this will automatically show its layer via connection)
        cmds.setAttr("{}.is_active".format(shot_node), True)
        logger.info("Set {}.is_active = True".format(shot_node))

        # Add to history
        self._add_to_history(shot_node)

        # Refresh the Layer Editor UI to show visibility changes
        try:
            cmds.refresh(force=True)
            logger.info("Forced viewport refresh")
        except Exception as e:
            logger.warning("Failed to refresh viewport: {}".format(e))

        logger.info("Shot switch complete!")
        logger.info("=" * 60)
        return True
    
    def get_active_shot(self, manager_node):
        """Get currently active shot.

        Args:
            manager_node (str): CTX_Manager node name

        Returns:
            str: Active shot node name, or None if not set
        """
        if not cmds.objExists(manager_node):
            return None

        try:
            active_shot = cmds.getAttr("{}.active_shot_id".format(manager_node))
            return active_shot if active_shot else None
        except:
            return None

    def switch_to_previous_shot(self, manager_node):
        """Switch to previous shot in history.

        Args:
            manager_node (str): CTX_Manager node name

        Returns:
            bool: True if switch successful
        """
        if len(self.history) < 2:
            return False

        # Get current shot
        current = self.get_active_shot(manager_node)

        # Find previous shot in history
        try:
            current_idx = self.history.index(current)
            if current_idx > 0:
                previous_shot = self.history[current_idx - 1]
                return self.switch_to_shot(previous_shot, manager_node)
        except ValueError:
            pass

        return False

    def switch_to_next_shot(self, manager_node):
        """Switch to next shot in history.

        Args:
            manager_node (str): CTX_Manager node name

        Returns:
            bool: True if switch successful
        """
        if len(self.history) < 2:
            return False

        # Get current shot
        current = self.get_active_shot(manager_node)

        # Find next shot in history
        try:
            current_idx = self.history.index(current)
            if current_idx < len(self.history) - 1:
                next_shot = self.history[current_idx + 1]
                return self.switch_to_shot(next_shot, manager_node)
        except ValueError:
            pass

        return False

    def get_history(self):
        """Get shot switching history.

        Returns:
            list: List of shot node names in switch order
        """
        return list(self.history)

    def clear_history(self):
        """Clear shot switching history."""
        self.history = []

    def _deactivate_other_shots(self, active_shot_node, manager_node):
        """Deactivate all other CTX_Shot nodes.

        This will automatically hide their display layers via the is_active connection.

        Args:
            active_shot_node (str): Active shot node name to keep active
            manager_node (str): CTX_Manager node name
        """
        # Get all shot nodes connected to manager
        all_shots = cmds.listConnections("{}.shots".format(manager_node), source=True, destination=False) or []

        # Deactivate all except the active one
        for shot in all_shots:
            if shot != active_shot_node:
                if cmds.objExists("{}.is_active".format(shot)):
                    cmds.setAttr("{}.is_active".format(shot), False)
                    logger.info("Set {}.is_active = False".format(shot))

    def _add_to_history(self, shot_node):
        """Add shot to history.

        Args:
            shot_node (str): Shot node name
        """
        # Remove if already in history
        if shot_node in self.history:
            self.history.remove(shot_node)

        # Add to end
        self.history.append(shot_node)

        # Trim if too long
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def show_all_shots(self):
        """Show all shot layers."""
        all_layers = self.layer_manager.get_all_ctx_layers()

        for layer in all_layers:
            self.layer_manager.show_layer(layer)

    def hide_all_shots(self):
        """Hide all shot layers."""
        all_layers = self.layer_manager.get_all_ctx_layers()

        for layer in all_layers:
            self.layer_manager.hide_layer(layer)

    def isolate_shot(self, shot_node, manager_node):
        """Isolate a single shot (show only this shot).

        Args:
            shot_node (str): Shot node to isolate
            manager_node (str): CTX_Manager node name

        Returns:
            bool: True if successful
        """
        return self.switch_to_shot(shot_node, manager_node, hide_others=True)

    def unisolate_all(self):
        """Show all shots (exit isolation mode)."""
        self.show_all_shots()

