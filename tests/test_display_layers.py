# -*- coding: utf-8 -*-
"""Tests for core/display_layers.py"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import unittest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.display_layers import DisplayLayerManager


class MockCmds(object):
    """Enhanced mock Maya commands for testing."""
    
    def __init__(self):
        self.layers = {}  # layer_name -> [members]
        self.layer_visibility = {}  # layer_name -> visibility
        self.nodes = set()  # existing nodes
    
    def createDisplayLayer(self, name=None, empty=True, noRecurse=False):
        """Mock createDisplayLayer."""
        if name:
            self.layers[name] = []
            self.layer_visibility[name] = 1
            return name
        return "displayLayer1"
    
    def objExists(self, name):
        """Mock objExists."""
        return name in self.layers or name in self.nodes
    
    def editDisplayLayerMembers(self, layer, *nodes, **kwargs):
        """Mock editDisplayLayerMembers."""
        if kwargs.get('query'):
            return self.layers.get(layer, [])
        
        # Add nodes to layer
        if layer in self.layers:
            for node in nodes:
                if node not in self.layers[layer]:
                    self.layers[layer].append(node)
    
    def setAttr(self, attr, value):
        """Mock setAttr."""
        # Extract layer name from attr
        layer_name = attr.split('.')[0]
        if layer_name in self.layer_visibility:
            self.layer_visibility[layer_name] = value
    
    def getAttr(self, attr):
        """Mock getAttr."""
        # Extract layer name from attr
        parts = attr.split('.')
        layer_name = parts[0]
        
        if len(parts) > 1 and parts[1] == 'visibility':
            return self.layer_visibility.get(layer_name, 1)
        
        # For shot node attributes
        if 'ep' in attr:
            return 'Ep04'
        elif 'seq' in attr:
            return 'sq0070'
        elif 'shot' in attr:
            return 'SH0170'
        
        return None
    
    def ls(self, *args, **kwargs):
        """Mock ls."""
        if kwargs.get('type') == 'displayLayer':
            return list(self.layers.keys())
        return []
    
    def delete(self, *nodes):
        """Mock delete."""
        for node in nodes:
            if node in self.layers:
                del self.layers[node]
            if node in self.layer_visibility:
                del self.layer_visibility[node]
    
    def listConnections(self, node, **kwargs):
        """Mock listConnections."""
        return []


class TestDisplayLayerManager(unittest.TestCase):
    """Test DisplayLayerManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Replace cmds with mock
        import core.display_layers as dl_module
        self.original_cmds = dl_module.cmds
        self.mock_cmds = MockCmds()
        dl_module.cmds = self.mock_cmds
        
        # Create manager
        self.manager = DisplayLayerManager()
        
        # Add some test nodes
        self.mock_cmds.nodes.add('pCube1')
        self.mock_cmds.nodes.add('pSphere1')
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Restore original cmds
        import core.display_layers as dl_module
        dl_module.cmds = self.original_cmds
    
    def test_create_display_layer(self):
        """Test creating display layer."""
        layer = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0170')
        
        self.assertEqual(layer, 'CTX_Ep04_sq0070_SH0170')
        self.assertIn(layer, self.mock_cmds.layers)
        self.assertEqual(self.mock_cmds.layer_visibility[layer], 1)
    
    def test_create_display_layer_existing(self):
        """Test creating layer that already exists."""
        layer1 = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0170')
        layer2 = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0170')
        
        self.assertEqual(layer1, layer2)
        self.assertEqual(len(self.mock_cmds.layers), 1)
    
    def test_assign_to_layer(self):
        """Test assigning node to layer."""
        layer = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0170')
        self.manager.assign_to_layer('pCube1', layer)
        
        self.assertIn('pCube1', self.mock_cmds.layers[layer])
    
    def test_assign_to_layer_invalid_layer(self):
        """Test assigning to non-existent layer."""
        with self.assertRaises(ValueError):
            self.manager.assign_to_layer('pCube1', 'invalid_layer')
    
    def test_assign_to_layer_invalid_node(self):
        """Test assigning non-existent node."""
        layer = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0170')

        with self.assertRaises(ValueError):
            self.manager.assign_to_layer('invalid_node', layer)

    def test_assign_batch(self):
        """Test batch assignment."""
        layer = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0170')
        self.manager.assign_batch(['pCube1', 'pSphere1'], layer)

        self.assertIn('pCube1', self.mock_cmds.layers[layer])
        self.assertIn('pSphere1', self.mock_cmds.layers[layer])

    def test_set_layer_visibility(self):
        """Test setting layer visibility."""
        layer = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0170')

        self.manager.set_layer_visibility(layer, False)
        self.assertEqual(self.mock_cmds.layer_visibility[layer], 0)

        self.manager.set_layer_visibility(layer, True)
        self.assertEqual(self.mock_cmds.layer_visibility[layer], 1)

    def test_show_layer(self):
        """Test showing layer."""
        layer = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0170')
        self.manager.hide_layer(layer)
        self.manager.show_layer(layer)

        self.assertEqual(self.mock_cmds.layer_visibility[layer], 1)

    def test_hide_layer(self):
        """Test hiding layer."""
        layer = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0170')
        self.manager.hide_layer(layer)

        self.assertEqual(self.mock_cmds.layer_visibility[layer], 0)

    def test_get_layer_for_shot(self):
        """Test getting layer for shot."""
        layer = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0170')

        result = self.manager.get_layer_for_shot('Ep04', 'sq0070', 'SH0170')
        self.assertEqual(result, layer)

    def test_get_layer_for_shot_not_found(self):
        """Test getting layer that doesn't exist."""
        result = self.manager.get_layer_for_shot('Ep99', 'sq9999', 'SH9999')
        self.assertIsNone(result)

    def test_get_layer_members(self):
        """Test getting layer members."""
        layer = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0170')
        self.manager.assign_to_layer('pCube1', layer)
        self.manager.assign_to_layer('pSphere1', layer)

        members = self.manager.get_layer_members(layer)
        self.assertEqual(len(members), 2)
        self.assertIn('pCube1', members)
        self.assertIn('pSphere1', members)

    def test_get_layer_members_empty(self):
        """Test getting members of empty layer."""
        layer = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0170')

        members = self.manager.get_layer_members(layer)
        self.assertEqual(members, [])

    def test_get_layer_members_invalid(self):
        """Test getting members of non-existent layer."""
        members = self.manager.get_layer_members('invalid_layer')
        self.assertEqual(members, [])

    def test_get_all_ctx_layers(self):
        """Test getting all CTX layers."""
        layer1 = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0170')
        layer2 = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0180')

        # Create non-CTX layer
        self.mock_cmds.createDisplayLayer(name='other_layer')

        ctx_layers = self.manager.get_all_ctx_layers()
        self.assertEqual(len(ctx_layers), 2)
        self.assertIn(layer1, ctx_layers)
        self.assertIn(layer2, ctx_layers)
        self.assertNotIn('other_layer', ctx_layers)

    def test_is_in_layer(self):
        """Test checking if node is in layer."""
        layer = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0170')
        self.manager.assign_to_layer('pCube1', layer)

        self.assertTrue(self.manager.is_in_layer('pCube1', layer))
        self.assertFalse(self.manager.is_in_layer('pSphere1', layer))

    def test_cleanup_empty_layers(self):
        """Test cleaning up empty layers."""
        layer1 = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0170')
        layer2 = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0180')

        # Add node to layer1
        self.manager.assign_to_layer('pCube1', layer1)

        # Cleanup
        deleted = self.manager.cleanup_empty_layers()

        self.assertEqual(len(deleted), 1)
        self.assertIn(layer2, deleted)
        self.assertNotIn(layer2, self.mock_cmds.layers)
        self.assertIn(layer1, self.mock_cmds.layers)

    def test_cleanup_empty_layers_dry_run(self):
        """Test dry run of cleanup."""
        layer1 = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0170')
        layer2 = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0180')

        # Dry run
        deleted = self.manager.cleanup_empty_layers(dry_run=True)

        self.assertEqual(len(deleted), 2)
        # Layers should still exist
        self.assertIn(layer1, self.mock_cmds.layers)
        self.assertIn(layer2, self.mock_cmds.layers)

    def test_cleanup_orphaned_layers(self):
        """Test cleaning up orphaned layers."""
        layer1 = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0170')
        layer2 = self.manager.create_display_layer('Ep04', 'sq0070', 'SH0180')

        # Create mock shot node
        self.mock_cmds.nodes.add('CTX_Shot_SH0170')

        # Cleanup (only layer1 is valid)
        deleted = self.manager.cleanup_orphaned_layers(['CTX_Shot_SH0170'])

        self.assertEqual(len(deleted), 1)
        self.assertIn(layer2, deleted)


if __name__ == '__main__':
    unittest.main()

