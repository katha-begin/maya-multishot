# -*- coding: utf-8 -*-
"""Unit tests for NodeManager class.

Author: Context Variables Pipeline
Date: 2026-02-14
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.nodes import NodeManager, NODE_TYPE_AI_STANDIN, NODE_TYPE_RS_PROXY, NODE_TYPE_REFERENCE
from core.custom_nodes import cmds, MAYA_AVAILABLE


class TestNodeManager(unittest.TestCase):
    """Test cases for NodeManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.nm = NodeManager()
        
        # Create test nodes in mock mode
        if not MAYA_AVAILABLE:
            # Create aiStandIn node
            self.standin_node = cmds.createNode(NODE_TYPE_AI_STANDIN, name='test_standin')
            cmds.addAttr(self.standin_node, longName='dso', dataType='string')
            cmds.setAttr(self.standin_node + '.dso', '/path/to/standin.abc', type='string')
            
            # Create RedshiftProxyMesh node
            self.proxy_node = cmds.createNode(NODE_TYPE_RS_PROXY, name='test_proxy')
            cmds.addAttr(self.proxy_node, longName='fileName', dataType='string')
            cmds.setAttr(self.proxy_node + '.fileName', '/path/to/proxy.rs', type='string')
    
    def tearDown(self):
        """Clean up test fixtures."""
        if not MAYA_AVAILABLE:
            if hasattr(self, 'standin_node') and cmds.objExists(self.standin_node):
                cmds.delete(self.standin_node)
            if hasattr(self, 'proxy_node') and cmds.objExists(self.proxy_node):
                cmds.delete(self.proxy_node)
    
    def test_get_node_type_standin(self):
        """Test getting node type for aiStandIn."""
        if not MAYA_AVAILABLE:
            node_type = self.nm.get_node_type(self.standin_node)
            self.assertEqual(node_type, NODE_TYPE_AI_STANDIN)
    
    def test_get_node_type_proxy(self):
        """Test getting node type for RedshiftProxyMesh."""
        if not MAYA_AVAILABLE:
            node_type = self.nm.get_node_type(self.proxy_node)
            self.assertEqual(node_type, NODE_TYPE_RS_PROXY)
    
    def test_get_node_type_invalid(self):
        """Test getting node type for non-existent node."""
        node_type = self.nm.get_node_type('nonexistent_node')
        self.assertIsNone(node_type)
    
    def test_get_path_standin(self):
        """Test getting path from aiStandIn."""
        if not MAYA_AVAILABLE:
            path = self.nm.get_path(self.standin_node)
            self.assertEqual(path, '/path/to/standin.abc')
    
    def test_get_path_proxy(self):
        """Test getting path from RedshiftProxyMesh."""
        if not MAYA_AVAILABLE:
            path = self.nm.get_path(self.proxy_node)
            self.assertEqual(path, '/path/to/proxy.rs')
    
    def test_get_path_invalid(self):
        """Test getting path from invalid node."""
        path = self.nm.get_path('nonexistent_node')
        self.assertIsNone(path)
    
    def test_set_path_standin(self):
        """Test setting path on aiStandIn."""
        if not MAYA_AVAILABLE:
            result = self.nm.set_path(self.standin_node, '/new/path.abc')
            self.assertTrue(result)
            
            path = self.nm.get_path(self.standin_node)
            self.assertEqual(path, '/new/path.abc')
    
    def test_set_path_proxy(self):
        """Test setting path on RedshiftProxyMesh."""
        if not MAYA_AVAILABLE:
            result = self.nm.set_path(self.proxy_node, '/new/path.rs')
            self.assertTrue(result)
            
            path = self.nm.get_path(self.proxy_node)
            self.assertEqual(path, '/new/path.rs')
    
    def test_set_path_invalid(self):
        """Test setting path on invalid node."""
        result = self.nm.set_path('nonexistent_node', '/path.abc')
        self.assertFalse(result)
    
    def test_is_valid_node_standin(self):
        """Test validating aiStandIn node."""
        if not MAYA_AVAILABLE:
            is_valid = self.nm.is_valid_node(self.standin_node)
            self.assertTrue(is_valid)
    
    def test_is_valid_node_proxy(self):
        """Test validating RedshiftProxyMesh node."""
        if not MAYA_AVAILABLE:
            is_valid = self.nm.is_valid_node(self.proxy_node)
            self.assertTrue(is_valid)
    
    def test_is_valid_node_invalid(self):
        """Test validating invalid node."""
        is_valid = self.nm.is_valid_node('nonexistent_node')
        self.assertFalse(is_valid)

    def test_register_asset(self):
        """Test registering an asset."""
        if not MAYA_AVAILABLE:
            from core.custom_nodes import CTXManagerNode, CTXShotNode

            # Create manager and shot
            manager = CTXManagerNode.create_manager()
            shot = CTXShotNode.create_shot('Ep04', 'sq0070', 'SH0170', manager)

            # Register asset
            asset = self.nm.register_asset(shot, self.standin_node, 'CHAR', 'CatStompie', '001')

            self.assertIsNotNone(asset)
            self.assertEqual(asset.get_asset_type(), 'CHAR')
            self.assertEqual(asset.get_asset_name(), 'CatStompie')
            self.assertEqual(asset.get_variant(), '001')

            # Clean up
            manager.delete()

    def test_register_asset_invalid_node(self):
        """Test registering invalid node."""
        if not MAYA_AVAILABLE:
            from core.custom_nodes import CTXManagerNode, CTXShotNode

            manager = CTXManagerNode.create_manager()
            shot = CTXShotNode.create_shot('Ep04', 'sq0070', 'SH0170', manager)

            asset = self.nm.register_asset(shot, 'nonexistent', 'CHAR', 'Test', '001')

            self.assertIsNone(asset)

            manager.delete()

    def test_get_assets_for_shot(self):
        """Test getting assets for shot."""
        if not MAYA_AVAILABLE:
            from core.custom_nodes import CTXManagerNode, CTXShotNode

            manager = CTXManagerNode.create_manager()
            shot = CTXShotNode.create_shot('Ep04', 'sq0070', 'SH0170', manager)

            assets = self.nm.get_assets_for_shot(shot)

            self.assertIsInstance(assets, list)

            manager.delete()

    def test_update_asset_path(self):
        """Test updating asset path."""
        if not MAYA_AVAILABLE:
            from core.custom_nodes import CTXManagerNode, CTXShotNode, CTXAssetNode

            manager = CTXManagerNode.create_manager()
            shot = CTXShotNode.create_shot('Ep04', 'sq0070', 'SH0170', manager)
            asset = CTXAssetNode.create_asset('CHAR', 'CatStompie', '001', shot)
            asset.set_file_path('/path/to/asset.abc')

            result = self.nm.update_asset_path(asset)

            self.assertTrue(result)

            manager.delete()

    def test_update_shot_paths(self):
        """Test updating shot paths."""
        if not MAYA_AVAILABLE:
            from core.custom_nodes import CTXManagerNode, CTXShotNode

            manager = CTXManagerNode.create_manager()
            shot = CTXShotNode.create_shot('Ep04', 'sq0070', 'SH0170', manager)

            count = self.nm.update_shot_paths(shot)

            self.assertIsInstance(count, int)

            manager.delete()


if __name__ == '__main__':
    unittest.main()

