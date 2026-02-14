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

