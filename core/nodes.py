# -*- coding: utf-8 -*-
"""Node manager for proxy/reference operations.

This module handles operations on Arnold StandIns, Redshift Proxies,
and Maya References with a unified API.

Author: Context Variables Pipeline
Date: 2026-02-14
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False
    from core.custom_nodes import cmds  # Use mock cmds


# Supported node types
NODE_TYPE_AI_STANDIN = 'aiStandIn'
NODE_TYPE_RS_PROXY = 'RedshiftProxyMesh'
NODE_TYPE_REFERENCE = 'reference'

# Attribute names for file paths
PATH_ATTRS = {
    NODE_TYPE_AI_STANDIN: 'dso',
    NODE_TYPE_RS_PROXY: 'fileName',
    NODE_TYPE_REFERENCE: 'ftn'  # file texture name
}


class NodeManager(object):
    """Manager for proxy and reference node operations.
    
    Provides unified API for working with Arnold StandIns, Redshift Proxies,
    and Maya References.
    
    Example:
        >>> nm = NodeManager()
        >>> node_type = nm.get_node_type('my_standin')
        >>> path = nm.get_path('my_standin')
        >>> nm.set_path('my_standin', '/new/path.abc')
    """
    
    def __init__(self):
        """Initialize node manager."""
        pass
    
    def get_node_type(self, node):
        """Detect node type.
        
        Args:
            node (str): Node name
        
        Returns:
            str: Node type (aiStandIn, RedshiftProxyMesh, reference), or None
        """
        if not cmds.objExists(node):
            return None
        
        # Check if it's a reference node
        if cmds.objExists(node) and MAYA_AVAILABLE:
            try:
                if cmds.referenceQuery(node, isNodeReferenced=True):
                    return NODE_TYPE_REFERENCE
            except:
                pass
        
        # Check node type
        if MAYA_AVAILABLE:
            node_type = cmds.nodeType(node)
        else:
            # In mock mode, check if node has type attribute
            if hasattr(cmds, '_nodes') and node in cmds._nodes:
                node_type = cmds._nodes[node].get('type')
            else:
                return None
        
        if node_type == NODE_TYPE_AI_STANDIN:
            return NODE_TYPE_AI_STANDIN
        elif node_type == NODE_TYPE_RS_PROXY:
            return NODE_TYPE_RS_PROXY
        
        return None
    
    def get_path(self, node):
        """Get current file path from node.
        
        Args:
            node (str): Node name
        
        Returns:
            str: File path, or None if not found
        """
        node_type = self.get_node_type(node)
        if node_type is None:
            return None
        
        # Get attribute name for this node type
        attr_name = PATH_ATTRS.get(node_type)
        if attr_name is None:
            return None
        
        # Get attribute value
        attr_path = "{}.{}".format(node, attr_name)
        if not cmds.objExists(attr_path):
            return None
        
        return cmds.getAttr(attr_path)
    
    def set_path(self, node, path):
        """Update file path on node.
        
        Args:
            node (str): Node name
            path (str): New file path
        
        Returns:
            bool: True if successful, False otherwise
        """
        node_type = self.get_node_type(node)
        if node_type is None:
            return False
        
        # Get attribute name for this node type
        attr_name = PATH_ATTRS.get(node_type)
        if attr_name is None:
            return False
        
        # Set attribute value
        attr_path = "{}.{}".format(node, attr_name)
        if not cmds.objExists(attr_path):
            return False
        
        try:
            cmds.setAttr(attr_path, path, type='string')
            return True
        except:
            return False
    
    def is_valid_node(self, node):
        """Check if node exists and is a supported type.

        Args:
            node (str): Node name

        Returns:
            bool: True if valid
        """
        return self.get_node_type(node) is not None

    def register_asset(self, shot_node, maya_node, asset_type, asset_name, variant):
        """Register a Maya node as a CTX asset.

        Args:
            shot_node: CTXShotNode instance
            maya_node (str): Maya node name
            asset_type (str): Asset type (e.g., 'CHAR')
            asset_name (str): Asset name (e.g., 'CatStompie')
            variant (str): Asset variant (e.g., '001')

        Returns:
            CTXAssetNode: Created asset node, or None if failed
        """
        from core.custom_nodes import CTXAssetNode

        # Validate Maya node exists
        if not cmds.objExists(maya_node):
            return None

        # Validate it's a supported node type
        if not self.is_valid_node(maya_node):
            return None

        # Create CTX_Asset node
        asset_node = CTXAssetNode.create_asset(asset_type, asset_name, variant, shot_node)

        # Store Maya node path
        path = self.get_path(maya_node)
        if path:
            asset_node.set_file_path(path)

        return asset_node

    def get_assets_for_shot(self, shot_node):
        """Get all assets for a shot.

        Args:
            shot_node: CTXShotNode instance

        Returns:
            list: List of CTXAssetNode instances
        """
        # This would query connected nodes in real Maya
        # For now, return empty list
        return []

    def get_asset_by_maya_node(self, maya_node):
        """Find CTX_Asset for a Maya node.

        Args:
            maya_node (str): Maya node name

        Returns:
            CTXAssetNode: Asset node, or None if not found
        """
        # This would query scene for matching asset
        # For now, return None
        return None

    def get_assets_by_type(self, shot_node, asset_type):
        """Get assets filtered by type.

        Args:
            shot_node: CTXShotNode instance
            asset_type (str): Asset type to filter

        Returns:
            list: List of CTXAssetNode instances
        """
        all_assets = self.get_assets_for_shot(shot_node)
        return [a for a in all_assets if a.get_asset_type() == asset_type]

    def find_asset(self, shot_node, asset_name, variant):
        """Find specific asset by name and variant.

        Args:
            shot_node: CTXShotNode instance
            asset_name (str): Asset name
            variant (str): Asset variant

        Returns:
            CTXAssetNode: Asset node, or None if not found
        """
        all_assets = self.get_assets_for_shot(shot_node)
        for asset in all_assets:
            if asset.get_asset_name() == asset_name and asset.get_variant() == variant:
                return asset
        return None

    def update_asset_path(self, asset_node):
        """Update path on asset's Maya node.

        Args:
            asset_node: CTXAssetNode instance

        Returns:
            bool: True if successful
        """
        # Get file path from asset node
        path = asset_node.get_file_path()
        if not path:
            return False

        # This would find and update the Maya node
        # For now, return True
        return True

    def update_shot_paths(self, shot_node):
        """Update paths for all assets in a shot.

        Args:
            shot_node: CTXShotNode instance

        Returns:
            int: Number of assets updated
        """
        assets = self.get_assets_for_shot(shot_node)
        count = 0
        for asset in assets:
            if self.update_asset_path(asset):
                count += 1
        return count

    def update_all_paths(self):
        """Update paths for all assets in scene.

        Returns:
            int: Number of assets updated
        """
        # This would query all shots and update their assets
        # For now, return 0
        return 0

