# -*- coding: utf-8 -*-
"""Tests for tools/shot_manager.py"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import unittest
import os
import sys
import tempfile
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.shot_manager import ShotManager


class MockCmds(object):
    """Enhanced mock Maya commands for testing."""
    
    def __init__(self):
        self.nodes = {}  # node_name -> {attr: value}
        self.connections = {}  # src_attr -> [dst_attrs]
        self.node_counter = 0
    
    def objExists(self, name):
        """Mock objExists."""
        return name in self.nodes
    
    def createNode(self, node_type, name=None):
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
    
    def listConnections(self, attr, **kwargs):
        """Mock listConnections."""
        # Find connections
        results = []
        
        # Check if this is a source
        if attr in self.connections:
            for dst in self.connections[attr]:
                node_name = dst.split('.')[0]
                results.append(node_name)
        
        # Check if this is a destination
        for src, dsts in self.connections.items():
            if attr in dsts:
                node_name = src.split('.')[0]
                results.append(node_name)
        
        return results if results else None
    
    def ls(self, *args, **kwargs):
        """Mock ls."""
        node_type = kwargs.get('type')
        if node_type:
            return [name for name, data in self.nodes.items() if data.get('type') == node_type]
        return list(self.nodes.keys())
    
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


class TestShotManager(unittest.TestCase):
    """Test ShotManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Replace cmds with mock
        import tools.shot_manager as sm_module
        self.original_cmds = sm_module.cmds
        self.mock_cmds = MockCmds()
        sm_module.cmds = self.mock_cmds
        
        # Create manager
        self.shot_mgr = ShotManager()
        
        # Create mock CTX_Manager node
        self.manager_node = self.mock_cmds.createNode('network', name='CTX_Manager')
        self.mock_cmds.addAttr(self.manager_node, longName='shots', attributeType='message', multi=True)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Restore original cmds
        import tools.shot_manager as sm_module
        sm_module.cmds = self.original_cmds
    
    def test_validate_shot_code_valid(self):
        """Test validating valid shot codes."""
        is_valid, error = self.shot_mgr.validate_shot_code('Ep04', 'sq0070', 'SH0170')

        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_shot_code_invalid_ep(self):
        """Test validating invalid episode code."""
        is_valid, error = self.shot_mgr.validate_shot_code('EP04', 'sq0070', 'SH0170')

        self.assertFalse(is_valid)
        self.assertIn('episode', error.lower())

    def test_validate_shot_code_invalid_seq(self):
        """Test validating invalid sequence code."""
        is_valid, error = self.shot_mgr.validate_shot_code('Ep04', 'SQ0070', 'SH0170')

        self.assertFalse(is_valid)
        self.assertIn('sequence', error.lower())

    def test_validate_shot_code_invalid_shot(self):
        """Test validating invalid shot code."""
        is_valid, error = self.shot_mgr.validate_shot_code('Ep04', 'sq0070', 'sh0170')

        self.assertFalse(is_valid)
        self.assertIn('shot', error.lower())

    def test_create_shot(self):
        """Test creating a shot."""
        shot_node = self.shot_mgr.create_shot('Ep04', 'sq0070', 'SH0170', self.manager_node)

        self.assertEqual(shot_node, 'CTX_Shot_SH0170')
        self.assertTrue(self.mock_cmds.objExists(shot_node))

        # Check attributes
        self.assertEqual(self.mock_cmds.getAttr("{}.ep".format(shot_node)), 'Ep04')
        self.assertEqual(self.mock_cmds.getAttr("{}.seq".format(shot_node)), 'sq0070')
        self.assertEqual(self.mock_cmds.getAttr("{}.shot".format(shot_node)), 'SH0170')

    def test_create_shot_invalid_code(self):
        """Test creating shot with invalid code."""
        with self.assertRaises(ValueError):
            self.shot_mgr.create_shot('EP04', 'sq0070', 'SH0170', self.manager_node)

    def test_create_shot_invalid_manager(self):
        """Test creating shot with invalid manager."""
        with self.assertRaises(ValueError):
            self.shot_mgr.create_shot('Ep04', 'sq0070', 'SH0170', 'invalid_manager')

    def test_create_shot_duplicate(self):
        """Test creating duplicate shot."""
        self.shot_mgr.create_shot('Ep04', 'sq0070', 'SH0170', self.manager_node)

        with self.assertRaises(ValueError):
            self.shot_mgr.create_shot('Ep04', 'sq0070', 'SH0170', self.manager_node)

    def test_delete_shot(self):
        """Test deleting a shot."""
        shot_node = self.shot_mgr.create_shot('Ep04', 'sq0070', 'SH0170', self.manager_node)

        result = self.shot_mgr.delete_shot(shot_node)

        self.assertTrue(result)
        self.assertFalse(self.mock_cmds.objExists(shot_node))

    def test_delete_shot_invalid(self):
        """Test deleting invalid shot."""
        with self.assertRaises(ValueError):
            self.shot_mgr.delete_shot('invalid_shot')

    def test_get_shot_info(self):
        """Test getting shot info."""
        shot_node = self.shot_mgr.create_shot('Ep04', 'sq0070', 'SH0170', self.manager_node)

        info = self.shot_mgr.get_shot_info(shot_node)

        self.assertEqual(info['node'], shot_node)
        self.assertEqual(info['ep'], 'Ep04')
        self.assertEqual(info['seq'], 'sq0070')
        self.assertEqual(info['shot'], 'SH0170')
        self.assertEqual(info['asset_count'], 0)

    def test_list_all_shots(self):
        """Test listing all shots."""
        shot1 = self.shot_mgr.create_shot('Ep04', 'sq0070', 'SH0170', self.manager_node)
        shot2 = self.shot_mgr.create_shot('Ep04', 'sq0070', 'SH0180', self.manager_node)

        shots = self.shot_mgr.list_all_shots()

        self.assertEqual(len(shots), 2)
        self.assertIn(shot1, shots)
        self.assertIn(shot2, shots)

    def test_export_import_shot(self):
        """Test exporting and importing shot."""
        # Create shot
        shot_node = self.shot_mgr.create_shot('Ep04', 'sq0070', 'SH0170', self.manager_node)

        # Export
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        temp_file.close()

        try:
            self.shot_mgr.export_shot(shot_node, temp_file.name)

            # Check file exists
            self.assertTrue(os.path.exists(temp_file.name))

            # Read and validate
            with open(temp_file.name, 'r') as f:
                data = json.load(f)

            self.assertIn('shot', data)
            self.assertEqual(data['shot']['ep'], 'Ep04')
            self.assertEqual(data['shot']['seq'], 'sq0070')
            self.assertEqual(data['shot']['shot'], 'SH0170')

            # Delete original shot
            self.shot_mgr.delete_shot(shot_node)

            # Import
            imported_shot = self.shot_mgr.import_shot(temp_file.name, self.manager_node)

            self.assertEqual(imported_shot, shot_node)
            self.assertTrue(self.mock_cmds.objExists(imported_shot))

        finally:
            os.unlink(temp_file.name)

    def test_validate_shot(self):
        """Test validating shot."""
        shot_node = self.shot_mgr.create_shot('Ep04', 'sq0070', 'SH0170', self.manager_node)

        report = self.shot_mgr.validate_shot(shot_node)

        self.assertTrue(report['valid'])
        self.assertEqual(len(report['errors']), 0)

    def test_get_shot_stats(self):
        """Test getting shot statistics."""
        shot_node = self.shot_mgr.create_shot('Ep04', 'sq0070', 'SH0170', self.manager_node)

        stats = self.shot_mgr.get_shot_stats(shot_node)

        self.assertEqual(stats['total_assets'], 0)
        self.assertIsInstance(stats['assets_by_type'], dict)
        self.assertEqual(stats['total_size_bytes'], 0)


if __name__ == '__main__':
    unittest.main()

