# -*- coding: utf-8 -*-
"""Tests for tools/asset_manager.py"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import unittest
import os
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.asset_manager import AssetManager


class MockCmds(object):
    """Enhanced mock Maya commands for testing."""
    
    def __init__(self):
        self.nodes = {}  # node_name -> {attr: value}
        self.connections = {}  # src_attr -> [dst_attrs]
        self.node_counter = 0
    
    def objExists(self, name):
        """Mock objExists."""
        return name in self.nodes
    
    def createNode(self, node_type, name=None, **kwargs):
        """Mock createNode."""
        if name and name in self.nodes:
            raise RuntimeError("Node '{}' already exists".format(name))
        
        if not name:
            self.node_counter += 1
            name = "node{}".format(self.node_counter)
        
        self.nodes[name] = {'type': node_type}
        return name
    
    def addAttr(self, node, **kwargs):
        """Mock addAttr."""
        if node not in self.nodes:
            raise RuntimeError("Node '{}' does not exist".format(node))
        
        attr_name = kwargs.get('longName')
        if attr_name:
            self.nodes[node][attr_name] = None
    
    def setAttr(self, attr, value, **kwargs):
        """Mock setAttr."""
        node_name = attr.split('.')[0]
        attr_name = attr.split('.')[1] if '.' in attr else None
        
        if node_name in self.nodes and attr_name:
            self.nodes[node_name][attr_name] = value
    
    def getAttr(self, attr):
        """Mock getAttr."""
        node_name = attr.split('.')[0]
        attr_name = attr.split('.')[1] if '.' in attr else None
        
        if node_name in self.nodes and attr_name:
            return self.nodes[node_name].get(attr_name)
        
        return None
    
    def connectAttr(self, src, dst, **kwargs):
        """Mock connectAttr."""
        if src not in self.connections:
            self.connections[src] = []
        self.connections[src].append(dst)

        # Also create reverse connection for message attributes
        # asset.message -> shot.assets means asset.shot should return shot
        if '.message' in src:
            src_node = src.split('.')[0]
            dst_node = dst.split('.')[0]

            # Create reverse lookup: asset.shot -> shot
            reverse_key = "{}.shot".format(src_node)
            if reverse_key not in self.connections:
                self.connections[reverse_key] = []
            self.connections[reverse_key].append("{}.message".format(dst_node))
    
    def listConnections(self, attr, **kwargs):
        """Mock listConnections."""
        # Find connections
        results = []
        source = kwargs.get('source', True)
        destination = kwargs.get('destination', True)

        # Check if this is a source (looking for destinations)
        if destination and attr in self.connections:
            for dst in self.connections[attr]:
                node_name = dst.split('.')[0]
                if node_name not in results:
                    results.append(node_name)

        # Check if this is a destination (looking for sources)
        if source:
            for src, dsts in self.connections.items():
                if attr in dsts:
                    node_name = src.split('.')[0]
                    if node_name not in results:
                        results.append(node_name)

        return results if results else None
    
    def delete(self, *nodes):
        """Mock delete."""
        for node in nodes:
            if node in self.nodes:
                del self.nodes[node]
            
            # Remove connections
            to_remove = []
            for src, dsts in self.connections.items():
                if node in src:
                    to_remove.append(src)
                else:
                    self.connections[src] = [dst for dst in dsts if node not in dst]
            
            for src in to_remove:
                del self.connections[src]


class TestAssetManager(unittest.TestCase):
    """Test AssetManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Replace cmds with mock
        import tools.asset_manager as am_module
        self.original_cmds = am_module.cmds
        self.mock_cmds = MockCmds()
        am_module.cmds = self.mock_cmds
        
        # Create manager
        self.asset_mgr = AssetManager()
        
        # Create mock shot node
        self.shot_node = self.mock_cmds.createNode('network', name='CTX_Shot_SH0170')
        self.mock_cmds.addAttr(self.shot_node, longName='ep')
        self.mock_cmds.addAttr(self.shot_node, longName='seq')
        self.mock_cmds.addAttr(self.shot_node, longName='shot')
        self.mock_cmds.addAttr(self.shot_node, longName='dept')
        self.mock_cmds.addAttr(self.shot_node, longName='assets', attributeType='message', multi=True)
        
        self.mock_cmds.setAttr("{}.ep".format(self.shot_node), 'Ep04')
        self.mock_cmds.setAttr("{}.seq".format(self.shot_node), 'sq0070')
        self.mock_cmds.setAttr("{}.shot".format(self.shot_node), 'SH0170')
        self.mock_cmds.setAttr("{}.dept".format(self.shot_node), 'layout')
        
        # Create temp file for testing
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.abc', delete=False)
        self.temp_file.write("test")
        self.temp_file.close()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Restore original cmds
        import tools.asset_manager as am_module
        am_module.cmds = self.original_cmds

        # Remove temp file
        os.unlink(self.temp_file.name)

    def test_add_asset(self):
        """Test adding asset to shot."""
        asset_node = self.asset_mgr.add_asset(
            self.shot_node,
            'CHAR', 'CatStompie', '002', 'v003',
            self.temp_file.name
        )

        self.assertEqual(asset_node, 'CTX_Asset_CHAR_CatStompie_002_v003')
        self.assertTrue(self.mock_cmds.objExists(asset_node))

        # Check attributes
        self.assertEqual(self.mock_cmds.getAttr("{}.assetType".format(asset_node)), 'CHAR')
        self.assertEqual(self.mock_cmds.getAttr("{}.assetName".format(asset_node)), 'CatStompie')
        self.assertEqual(self.mock_cmds.getAttr("{}.variant".format(asset_node)), '002')
        self.assertEqual(self.mock_cmds.getAttr("{}.version".format(asset_node)), 'v003')

    def test_add_asset_invalid_shot(self):
        """Test adding asset with invalid shot."""
        with self.assertRaises(ValueError):
            self.asset_mgr.add_asset(
                'invalid_shot',
                'CHAR', 'CatStompie', '002', 'v003',
                self.temp_file.name
            )

    def test_add_asset_invalid_file(self):
        """Test adding asset with invalid file."""
        with self.assertRaises(ValueError):
            self.asset_mgr.add_asset(
                self.shot_node,
                'CHAR', 'CatStompie', '002', 'v003',
                '/invalid/path.abc'
            )

    def test_add_asset_duplicate(self):
        """Test adding duplicate asset."""
        self.asset_mgr.add_asset(
            self.shot_node,
            'CHAR', 'CatStompie', '002', 'v003',
            self.temp_file.name
        )

        with self.assertRaises(ValueError):
            self.asset_mgr.add_asset(
                self.shot_node,
                'CHAR', 'CatStompie', '002', 'v003',
                self.temp_file.name
            )

    def test_remove_asset(self):
        """Test removing asset."""
        asset_node = self.asset_mgr.add_asset(
            self.shot_node,
            'CHAR', 'CatStompie', '002', 'v003',
            self.temp_file.name
        )

        result = self.asset_mgr.remove_asset(asset_node)

        self.assertTrue(result)
        self.assertFalse(self.mock_cmds.objExists(asset_node))

    def test_remove_asset_invalid(self):
        """Test removing invalid asset."""
        with self.assertRaises(ValueError):
            self.asset_mgr.remove_asset('invalid_asset')

    def test_get_asset_info(self):
        """Test getting asset info."""
        asset_node = self.asset_mgr.add_asset(
            self.shot_node,
            'CHAR', 'CatStompie', '002', 'v003',
            self.temp_file.name
        )

        info = self.asset_mgr.get_asset_info(asset_node)

        self.assertEqual(info['node'], asset_node)
        self.assertEqual(info['assetType'], 'CHAR')
        self.assertEqual(info['assetName'], 'CatStompie')
        self.assertEqual(info['variant'], '002')
        self.assertEqual(info['version'], 'v003')
        self.assertTrue(info['file_exists'])

    def test_list_assets_for_shot(self):
        """Test listing assets for shot."""
        asset1 = self.asset_mgr.add_asset(
            self.shot_node,
            'CHAR', 'CatStompie', '002', 'v003',
            self.temp_file.name
        )

        # Create second temp file
        temp_file2 = tempfile.NamedTemporaryFile(mode='w', suffix='.abc', delete=False)
        temp_file2.write("test")
        temp_file2.close()

        try:
            asset2 = self.asset_mgr.add_asset(
                self.shot_node,
                'PROP', 'Table', '001', 'v001',
                temp_file2.name
            )

            assets = self.asset_mgr.list_assets_for_shot(self.shot_node)

            self.assertEqual(len(assets), 2)
            self.assertIn(asset1, assets)
            self.assertIn(asset2, assets)

        finally:
            os.unlink(temp_file2.name)

    def test_duplicate_asset(self):
        """Test duplicating asset."""
        asset_node = self.asset_mgr.add_asset(
            self.shot_node,
            'CHAR', 'CatStompie', '002', 'v003',
            self.temp_file.name
        )

        new_asset = self.asset_mgr.duplicate_asset(asset_node, '003')

        self.assertEqual(new_asset, 'CTX_Asset_CHAR_CatStompie_003_v003')
        self.assertTrue(self.mock_cmds.objExists(new_asset))

        # Check both assets exist
        self.assertTrue(self.mock_cmds.objExists(asset_node))
        self.assertTrue(self.mock_cmds.objExists(new_asset))

    def test_validate_asset(self):
        """Test validating asset."""
        asset_node = self.asset_mgr.add_asset(
            self.shot_node,
            'CHAR', 'CatStompie', '002', 'v003',
            self.temp_file.name
        )

        report = self.asset_mgr.validate_asset(asset_node)

        self.assertTrue(report['valid'])
        self.assertEqual(len(report['errors']), 0)

    def test_validate_asset_invalid_path(self):
        """Test validating asset with invalid path."""
        asset_node = self.asset_mgr.add_asset(
            self.shot_node,
            'CHAR', 'CatStompie', '002', 'v003',
            self.temp_file.name
        )

        # Change path to invalid
        self.mock_cmds.setAttr("{}.path".format(asset_node), '/invalid/path.abc')

        report = self.asset_mgr.validate_asset(asset_node)

        self.assertFalse(report['valid'])
        self.assertGreater(len(report['errors']), 0)


if __name__ == '__main__':
    unittest.main()


