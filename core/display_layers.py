# -*- coding: utf-8 -*-
"""Display Layer Management - Manage shot-specific visibility using display layers.

This module provides display layer management functionality:
- Create display layers for shots
- Assign assets to layers
- Control layer visibility
- Query layer contents
- Cleanup empty/orphaned layers

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
        
        def createDisplayLayer(self, name=None, empty=True, noRecurse=False):
            """Mock createDisplayLayer."""
            return name if name else "displayLayer1"
        
        def objExists(self, name):
            """Mock objExists."""
            return False
        
        def editDisplayLayerMembers(self, layer, *nodes, **kwargs):
            """Mock editDisplayLayerMembers."""
            pass
        
        def setAttr(self, attr, value):
            """Mock setAttr."""
            pass
        
        def getAttr(self, attr):
            """Mock getAttr."""
            return 1
        
        def listConnections(self, node, **kwargs):
            """Mock listConnections."""
            return []
        
        def ls(self, *args, **kwargs):
            """Mock ls."""
            return []
        
        def delete(self, *nodes):
            """Mock delete."""
            pass
    
    cmds = MockCmds()
    MAYA_AVAILABLE = False


class DisplayLayerManager(object):
    """Manage display layers for shot-specific visibility.
    
    Display layers are named: CTX_{ep}_{seq}_{shot}
    Example: CTX_Ep04_sq0070_SH0170
    
    Example:
        >>> from core.display_layers import DisplayLayerManager
        >>> 
        >>> layer_mgr = DisplayLayerManager()
        >>> 
        >>> # Create layer for shot
        >>> layer = layer_mgr.create_display_layer('Ep04', 'sq0070', 'SH0170')
        >>> print(layer)
        'CTX_Ep04_sq0070_SH0170'
        >>> 
        >>> # Assign nodes to layer
        >>> layer_mgr.assign_to_layer('pCube1', layer)
        >>> 
        >>> # Control visibility
        >>> layer_mgr.hide_layer(layer)
        >>> layer_mgr.show_layer(layer)
    """
    
    LAYER_PREFIX = "CTX_"
    
    def __init__(self):
        """Initialize display layer manager."""
        pass
    
    def create_display_layer(self, ep_code, seq_code, shot_code):
        """Create display layer for shot.
        
        Args:
            ep_code (str): Episode code (e.g., 'Ep04')
            seq_code (str): Sequence code (e.g., 'sq0070')
            shot_code (str): Shot code (e.g., 'SH0170')
        
        Returns:
            str: Layer name
        """
        # Build layer name
        layer_name = "{}{}_{}_{}".format(self.LAYER_PREFIX, ep_code, seq_code, shot_code)
        
        # Check if layer already exists
        if cmds.objExists(layer_name):
            return layer_name
        
        # Create new layer
        cmds.createDisplayLayer(name=layer_name, empty=True, noRecurse=True)
        
        # Set visible by default
        self.show_layer(layer_name)
        
        return layer_name
    
    def assign_to_layer(self, maya_node, layer_name):
        """Assign Maya node to display layer.
        
        Args:
            maya_node (str): Maya node name
            layer_name (str): Display layer name
        """
        if not cmds.objExists(layer_name):
            raise ValueError("Layer '{}' does not exist".format(layer_name))
        
        if not cmds.objExists(maya_node):
            raise ValueError("Node '{}' does not exist".format(maya_node))
        
        # Add node to layer
        cmds.editDisplayLayerMembers(layer_name, maya_node, noRecurse=True)
    
    def assign_batch(self, maya_nodes, layer_name):
        """Assign multiple nodes to display layer.
        
        Args:
            maya_nodes (list): List of Maya node names
            layer_name (str): Display layer name
        """
        for node in maya_nodes:
            self.assign_to_layer(node, layer_name)
    
    def set_layer_visibility(self, layer_name, visible):
        """Set display layer visibility.

        Args:
            layer_name (str): Display layer name
            visible (bool): True to show, False to hide
        """
        if not cmds.objExists(layer_name):
            raise ValueError("Layer '{}' does not exist".format(layer_name))

        # Set visibility attribute
        cmds.setAttr("{}.visibility".format(layer_name), 1 if visible else 0)

    def show_layer(self, layer_name):
        """Show display layer.

        Args:
            layer_name (str): Display layer name
        """
        self.set_layer_visibility(layer_name, True)

    def hide_layer(self, layer_name):
        """Hide display layer.

        Args:
            layer_name (str): Display layer name
        """
        self.set_layer_visibility(layer_name, False)

    def get_layer_for_shot(self, ep_code, seq_code, shot_code):
        """Get layer name for shot.

        Args:
            ep_code (str): Episode code
            seq_code (str): Sequence code
            shot_code (str): Shot code

        Returns:
            str: Layer name, or None if not found
        """
        layer_name = "{}{}_{}_{}".format(self.LAYER_PREFIX, ep_code, seq_code, shot_code)

        if cmds.objExists(layer_name):
            return layer_name

        return None

    def get_layer_members(self, layer_name):
        """Get nodes in display layer.

        Args:
            layer_name (str): Display layer name

        Returns:
            list: List of node names in layer
        """
        if not cmds.objExists(layer_name):
            return []

        # Query layer members
        members = cmds.editDisplayLayerMembers(layer_name, query=True, fullNames=True)

        return members if members else []

    def get_all_ctx_layers(self):
        """Get all CTX display layers.

        Returns:
            list: List of CTX layer names
        """
        # Get all display layers
        all_layers = cmds.ls(type='displayLayer')

        # Filter for CTX layers
        ctx_layers = [layer for layer in all_layers if layer.startswith(self.LAYER_PREFIX)]

        return ctx_layers

    def is_in_layer(self, maya_node, layer_name):
        """Check if node is in display layer.

        Args:
            maya_node (str): Maya node name
            layer_name (str): Display layer name

        Returns:
            bool: True if node is in layer
        """
        members = self.get_layer_members(layer_name)
        return maya_node in members

    def cleanup_empty_layers(self, dry_run=False):
        """Remove display layers with no members.

        Args:
            dry_run (bool): If True, only return layers that would be deleted

        Returns:
            list: List of deleted (or would-be-deleted) layer names
        """
        empty_layers = []

        # Get all CTX layers
        ctx_layers = self.get_all_ctx_layers()

        # Find empty layers
        for layer in ctx_layers:
            members = self.get_layer_members(layer)
            if not members:
                empty_layers.append(layer)

        # Delete if not dry run
        if not dry_run and empty_layers:
            for layer in empty_layers:
                cmds.delete(layer)

        return empty_layers

    def cleanup_orphaned_layers(self, shot_nodes, dry_run=False):
        """Remove layers not linked to any shot nodes.

        Args:
            shot_nodes (list): List of CTX_Shot node names
            dry_run (bool): If True, only return layers that would be deleted

        Returns:
            list: List of deleted (or would-be-deleted) layer names
        """
        orphaned_layers = []

        # Get all CTX layers
        ctx_layers = self.get_all_ctx_layers()

        # Build set of valid layer names from shot nodes
        valid_layers = set()
        for shot_node in shot_nodes:
            # Extract ep, seq, shot from node attributes
            if cmds.objExists(shot_node):
                try:
                    ep = cmds.getAttr("{}.ep".format(shot_node))
                    seq = cmds.getAttr("{}.seq".format(shot_node))
                    shot = cmds.getAttr("{}.shot".format(shot_node))
                    layer_name = "{}{}_{}_{}".format(self.LAYER_PREFIX, ep, seq, shot)
                    valid_layers.add(layer_name)
                except:
                    pass

        # Find orphaned layers
        for layer in ctx_layers:
            if layer not in valid_layers:
                orphaned_layers.append(layer)

        # Delete if not dry run
        if not dry_run and orphaned_layers:
            for layer in orphaned_layers:
                cmds.delete(layer)

        return orphaned_layers

