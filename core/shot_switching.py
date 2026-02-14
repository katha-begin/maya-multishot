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
        # Validate nodes exist
        if not cmds.objExists(shot_node):
            raise ValueError("Shot node '{}' does not exist".format(shot_node))
        
        if not cmds.objExists(manager_node):
            raise ValueError("Manager node '{}' does not exist".format(manager_node))
        
        # Get shot info
        ep = cmds.getAttr("{}.ep".format(shot_node))
        seq = cmds.getAttr("{}.seq".format(shot_node))
        shot = cmds.getAttr("{}.shot".format(shot_node))
        
        # Get layer for this shot
        layer_name = self.layer_manager.get_layer_for_shot(ep, seq, shot)
        
        if not layer_name:
            # Create layer if it doesn't exist
            layer_name = self.layer_manager.create_display_layer(ep, seq, shot)
        
        # Update manager's active shot
        cmds.setAttr("{}.active_shot_id".format(manager_node), shot_node, type="string")
        
        # Show this shot's layer
        self.layer_manager.show_layer(layer_name)
        
        # Hide other shots' layers if requested
        if hide_others:
            self._hide_other_shots(layer_name)
        
        # Add to history
        self._add_to_history(shot_node)
        
        # Trigger callbacks if context manager available
        if self.context_manager:
            context = {
                'ep': ep,
                'seq': seq,
                'shot': shot
            }
            self.context_manager.set_context(context, silent=False)
        
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

    def _hide_other_shots(self, active_layer):
        """Hide all CTX layers except the active one.

        Args:
            active_layer (str): Active layer name to keep visible
        """
        # Get all CTX layers
        all_layers = self.layer_manager.get_all_ctx_layers()

        # Hide all except active
        for layer in all_layers:
            if layer != active_layer:
                self.layer_manager.hide_layer(layer)

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

