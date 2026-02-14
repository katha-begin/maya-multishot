# -*- coding: utf-8 -*-
"""Tests for core/shot_switching.py"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import unittest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.shot_switching import ShotSwitcher
from core.display_layers import DisplayLayerManager


class MockCmds(object):
    """Enhanced mock Maya commands for testing."""
    
    def __init__(self):
        self.layers = {}  # layer_name -> [members]
        self.layer_visibility = {}  # layer_name -> visibility
        self.nodes = {}  # node_name -> {attr: value}
    
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
    
    def setAttr(self, attr, value, **kwargs):
        """Mock setAttr."""
        # Extract node name from attr
        node_name = attr.split('.')[0]
        attr_name = attr.split('.')[1] if '.' in attr else None
        
        # Handle layer visibility
        if node_name in self.layer_visibility and attr_name == 'visibility':
            self.layer_visibility[node_name] = value
        
        # Handle node attributes
        if node_name in self.nodes and attr_name:
            self.nodes[node_name][attr_name] = value
    
    def getAttr(self, attr):
        """Mock getAttr."""
        # Extract node name from attr
        node_name = attr.split('.')[0]
        attr_name = attr.split('.')[1] if '.' in attr else None
        
        # Handle layer visibility
        if node_name in self.layer_visibility and attr_name == 'visibility':
            return self.layer_visibility[node_name]
        
        # Handle node attributes
        if node_name in self.nodes and attr_name:
            return self.nodes[node_name].get(attr_name)
        
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


class TestShotSwitcher(unittest.TestCase):
    """Test ShotSwitcher class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Replace cmds with mock
        import core.shot_switching as ss_module
        import core.display_layers as dl_module
        
        self.original_ss_cmds = ss_module.cmds
        self.original_dl_cmds = dl_module.cmds
        
        self.mock_cmds = MockCmds()
        ss_module.cmds = self.mock_cmds
        dl_module.cmds = self.mock_cmds
        
        # Create managers
        self.layer_manager = DisplayLayerManager()
        self.switcher = ShotSwitcher(self.layer_manager)
        
        # Create mock nodes
        self.mock_cmds.nodes['CTX_Manager'] = {
            'active_shot_id': ''
        }
        self.mock_cmds.nodes['CTX_Shot_SH0170'] = {
            'ep': 'Ep04',
            'seq': 'sq0070',
            'shot': 'SH0170'
        }
        self.mock_cmds.nodes['CTX_Shot_SH0180'] = {
            'ep': 'Ep04',
            'seq': 'sq0070',
            'shot': 'SH0180'
        }
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Restore original cmds
        import core.shot_switching as ss_module
        import core.display_layers as dl_module
        
        ss_module.cmds = self.original_ss_cmds
        dl_module.cmds = self.original_dl_cmds
    
    def test_switch_to_shot(self):
        """Test switching to a shot."""
        result = self.switcher.switch_to_shot('CTX_Shot_SH0170', 'CTX_Manager')

        self.assertTrue(result)

        # Check active shot was set
        active = self.mock_cmds.nodes['CTX_Manager']['active_shot_id']
        self.assertEqual(active, 'CTX_Shot_SH0170')

        # Check layer was created and shown
        layer = self.layer_manager.get_layer_for_shot('Ep04', 'sq0070', 'SH0170')
        self.assertIsNotNone(layer)
        self.assertEqual(self.mock_cmds.layer_visibility[layer], 1)

    def test_switch_to_shot_hide_others(self):
        """Test switching hides other shots."""
        # Switch to first shot
        self.switcher.switch_to_shot('CTX_Shot_SH0170', 'CTX_Manager')

        # Switch to second shot
        self.switcher.switch_to_shot('CTX_Shot_SH0180', 'CTX_Manager', hide_others=True)

        # Check first shot's layer is hidden
        layer1 = self.layer_manager.get_layer_for_shot('Ep04', 'sq0070', 'SH0170')
        layer2 = self.layer_manager.get_layer_for_shot('Ep04', 'sq0070', 'SH0180')

        self.assertEqual(self.mock_cmds.layer_visibility[layer1], 0)
        self.assertEqual(self.mock_cmds.layer_visibility[layer2], 1)

    def test_switch_to_shot_invalid_shot(self):
        """Test switching to invalid shot."""
        with self.assertRaises(ValueError):
            self.switcher.switch_to_shot('invalid_shot', 'CTX_Manager')

    def test_switch_to_shot_invalid_manager(self):
        """Test switching with invalid manager."""
        with self.assertRaises(ValueError):
            self.switcher.switch_to_shot('CTX_Shot_SH0170', 'invalid_manager')

    def test_get_active_shot(self):
        """Test getting active shot."""
        self.switcher.switch_to_shot('CTX_Shot_SH0170', 'CTX_Manager')

        active = self.switcher.get_active_shot('CTX_Manager')
        self.assertEqual(active, 'CTX_Shot_SH0170')

    def test_get_active_shot_none(self):
        """Test getting active shot when none set."""
        active = self.switcher.get_active_shot('CTX_Manager')
        # Empty string is returned as None by get_active_shot
        self.assertIsNone(active)

    def test_get_active_shot_invalid_manager(self):
        """Test getting active shot with invalid manager."""
        active = self.switcher.get_active_shot('invalid_manager')
        self.assertIsNone(active)

    def test_history_tracking(self):
        """Test shot switching history."""
        self.switcher.switch_to_shot('CTX_Shot_SH0170', 'CTX_Manager')
        self.switcher.switch_to_shot('CTX_Shot_SH0180', 'CTX_Manager')

        history = self.switcher.get_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0], 'CTX_Shot_SH0170')
        self.assertEqual(history[1], 'CTX_Shot_SH0180')

    def test_clear_history(self):
        """Test clearing history."""
        self.switcher.switch_to_shot('CTX_Shot_SH0170', 'CTX_Manager')
        self.switcher.switch_to_shot('CTX_Shot_SH0180', 'CTX_Manager')

        self.switcher.clear_history()

        history = self.switcher.get_history()
        self.assertEqual(len(history), 0)

    def test_show_all_shots(self):
        """Test showing all shots."""
        # Create layers
        self.switcher.switch_to_shot('CTX_Shot_SH0170', 'CTX_Manager')
        self.switcher.switch_to_shot('CTX_Shot_SH0180', 'CTX_Manager', hide_others=True)

        # Show all
        self.switcher.show_all_shots()

        # Check all layers visible
        layer1 = self.layer_manager.get_layer_for_shot('Ep04', 'sq0070', 'SH0170')
        layer2 = self.layer_manager.get_layer_for_shot('Ep04', 'sq0070', 'SH0180')

        self.assertEqual(self.mock_cmds.layer_visibility[layer1], 1)
        self.assertEqual(self.mock_cmds.layer_visibility[layer2], 1)

    def test_hide_all_shots(self):
        """Test hiding all shots."""
        # Create layers
        self.switcher.switch_to_shot('CTX_Shot_SH0170', 'CTX_Manager')
        self.switcher.switch_to_shot('CTX_Shot_SH0180', 'CTX_Manager')

        # Hide all
        self.switcher.hide_all_shots()

        # Check all layers hidden
        layer1 = self.layer_manager.get_layer_for_shot('Ep04', 'sq0070', 'SH0170')
        layer2 = self.layer_manager.get_layer_for_shot('Ep04', 'sq0070', 'SH0180')

        self.assertEqual(self.mock_cmds.layer_visibility[layer1], 0)
        self.assertEqual(self.mock_cmds.layer_visibility[layer2], 0)

    def test_isolate_shot(self):
        """Test isolating a shot."""
        # Create layers
        self.switcher.switch_to_shot('CTX_Shot_SH0170', 'CTX_Manager')
        self.switcher.switch_to_shot('CTX_Shot_SH0180', 'CTX_Manager')

        # Isolate first shot
        self.switcher.isolate_shot('CTX_Shot_SH0170', 'CTX_Manager')

        # Check only first shot visible
        layer1 = self.layer_manager.get_layer_for_shot('Ep04', 'sq0070', 'SH0170')
        layer2 = self.layer_manager.get_layer_for_shot('Ep04', 'sq0070', 'SH0180')

        self.assertEqual(self.mock_cmds.layer_visibility[layer1], 1)
        self.assertEqual(self.mock_cmds.layer_visibility[layer2], 0)

    def test_unisolate_all(self):
        """Test unisolating all shots."""
        # Isolate a shot
        self.switcher.switch_to_shot('CTX_Shot_SH0170', 'CTX_Manager')
        self.switcher.switch_to_shot('CTX_Shot_SH0180', 'CTX_Manager', hide_others=True)

        # Unisolate
        self.switcher.unisolate_all()

        # Check all visible
        layer1 = self.layer_manager.get_layer_for_shot('Ep04', 'sq0070', 'SH0170')
        layer2 = self.layer_manager.get_layer_for_shot('Ep04', 'sq0070', 'SH0180')

        self.assertEqual(self.mock_cmds.layer_visibility[layer1], 1)
        self.assertEqual(self.mock_cmds.layer_visibility[layer2], 1)


if __name__ == '__main__':
    unittest.main()

