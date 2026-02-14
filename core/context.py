# -*- coding: utf-8 -*-
"""Context management API for Context Variables Pipeline.

This module provides high-level API for managing context:
- Creating and managing shots
- Switching active shot
- Querying current context
- Context change callbacks

Author: Context Variables Pipeline
Date: 2026-02-14
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from core.custom_nodes import CTXManagerNode, CTXShotNode, CTXAssetNode


class ContextManager(object):
    """High-level API for managing context.
    
    This class provides a simplified interface for working with the
    hierarchical custom node structure.
    
    Example:
        >>> ctx = ContextManager()
        >>> shot = ctx.create_shot('Ep04', 'sq0070', 'SH0170')
        >>> ctx.set_active_shot(shot)
        >>> current = ctx.get_active_shot()
    """
    
    def __init__(self):
        """Initialize context manager."""
        self._callbacks = []
        self._silent_mode = False
    
    def get_or_create_manager(self):
        """Get existing or create new CTX_Manager node.
        
        Returns:
            CTXManagerNode: Manager node instance
        """
        manager = CTXManagerNode.get_manager()
        if manager is None:
            manager = CTXManagerNode.create_manager()
        return manager
    
    def create_shot(self, ep_code, seq_code, shot_code):
        """Create a new shot in the scene.
        
        Args:
            ep_code (str): Episode code (e.g., 'Ep04')
            seq_code (str): Sequence code (e.g., 'sq0070')
            shot_code (str): Shot code (e.g., 'SH0170')
        
        Returns:
            CTXShotNode: New shot node instance
        
        Raises:
            ValueError: If shot already exists
        """
        # Get or create manager
        manager = self.get_or_create_manager()
        
        # Check if shot already exists
        shot_id = "{}_{}_{}" .format(ep_code, seq_code, shot_code)
        existing_shots = self.get_all_shots()
        for shot in existing_shots:
            if shot.get_shot_id() == shot_id:
                raise ValueError("Shot {} already exists".format(shot_id))
        
        # Create shot
        shot = CTXShotNode.create_shot(ep_code, seq_code, shot_code, manager)
        
        # Notify callbacks
        self._notify_change('shot_created', {'shot': shot})
        
        return shot
    
    def set_active_shot(self, shot_node):
        """Set the active shot.
        
        Args:
            shot_node (CTXShotNode): Shot node to activate
        
        Raises:
            ValueError: If shot node is invalid
        """
        if not isinstance(shot_node, CTXShotNode):
            raise ValueError("Invalid shot node")
        
        if not shot_node.exists():
            raise ValueError("Shot node does not exist")
        
        # Get manager
        manager = self.get_or_create_manager()
        
        # Deactivate all shots
        all_shots = self.get_all_shots()
        for shot in all_shots:
            shot.set_active(False)
        
        # Activate target shot
        shot_node.set_active(True)
        
        # Update manager's active shot ID
        manager.set_active_shot_id(shot_node.get_shot_id())
        
        # Notify callbacks
        self._notify_change('shot_switched', {'shot': shot_node})
    
    def get_active_shot(self):
        """Get the currently active shot.
        
        Returns:
            CTXShotNode: Active shot node, or None if no active shot
        """
        all_shots = self.get_all_shots()
        for shot in all_shots:
            if shot.is_active():
                return shot
        return None
    
    def get_all_shots(self):
        """Get all shots in the scene.
        
        Returns:
            list: List of CTXShotNode instances
        """
        # This is a simplified implementation
        # In a real Maya environment, we would query connected nodes
        # For now, return empty list
        return []
    
    def get_shot_context(self, shot_node):
        """Get shot context as dictionary.

        Args:
            shot_node (CTXShotNode): Shot node

        Returns:
            dict: Context dictionary with ep, seq, shot keys
        """
        if not isinstance(shot_node, CTXShotNode):
            raise ValueError("Invalid shot node")

        return {
            'ep': shot_node.get_ep_code(),
            'seq': shot_node.get_seq_code(),
            'shot': shot_node.get_shot_code()
        }

    def register_callback(self, callback_fn):
        """Register a callback function for context changes.

        Args:
            callback_fn (callable): Callback function with signature:
                callback_fn(event_type, data)

        Raises:
            ValueError: If callback is not callable
        """
        if not callable(callback_fn):
            raise ValueError("Callback must be callable")

        if callback_fn not in self._callbacks:
            self._callbacks.append(callback_fn)

    def unregister_callback(self, callback_fn):
        """Unregister a callback function.

        Args:
            callback_fn (callable): Callback function to remove
        """
        if callback_fn in self._callbacks:
            self._callbacks.remove(callback_fn)

    def _notify_change(self, event_type, data):
        """Notify all registered callbacks of a context change.

        Args:
            event_type (str): Type of event (shot_switched, version_updated, etc.)
            data (dict): Event data
        """
        if self._silent_mode:
            return

        for callback in self._callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                # Log error but don't stop other callbacks
                print("Error in callback: {}".format(e))

    def set_silent_mode(self, silent):
        """Enable/disable silent mode to prevent callback loops.

        Args:
            silent (bool): True to enable silent mode
        """
        self._silent_mode = silent

