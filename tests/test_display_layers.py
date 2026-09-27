# -*- coding: utf-8 -*-
"""Tests for core/display_layers.py -- the two global layer system.

Assets are not given a layer each and shots are not given a layer each.
There are exactly two, CTX_Active and CTX_Inactive, and an asset's top
transform is moved between them by connecting

    <layer>.drawInfo -> <transform>.drawOverride

These tests replaced an older suite written against the abandoned per-shot
scheme (CTX_<ep>_<seq>_<shot>, created by create_display_layer and cleaned up
by cleanup_empty_layers / cleanup_orphaned_layers).  Those functions relied on
a LAYER_PREFIX attribute that no longer existed, so every one of them raised
AttributeError; they have been removed rather than revived, because a "CTX_"
prefix would also match CTX_Active and CTX_Inactive themselves -- and the
cleanup functions would then delete them.

Runs without Maya.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.display_layers import DisplayLayerManager


class MockCmds(object):
    """Models display layers and drawInfo -> drawOverride connections."""

    def __init__(self):
        self.layers = {}            # layer -> [member transforms]
        self.layer_visibility = {}  # layer -> 0/1
        self.nodes = set()          # transforms that exist
        self.parents = {}           # child -> parent
        self.connections = {}       # '<node>.drawOverride' -> '<layer>.drawInfo'

    # -- existence -----------------------------------------------------
    def createDisplayLayer(self, name=None, empty=True, noRecurse=False):
        if name:
            self.layers[name] = []
            self.layer_visibility[name] = 1
            return name
        return 'displayLayer1'

    def objExists(self, name):
        base = name.split('.')[0]
        return base in self.layers or base in self.nodes

    def delete(self, *nodes):
        for node in nodes:
            self.layers.pop(node, None)
            self.layer_visibility.pop(node, None)

    # -- attributes ----------------------------------------------------
    def setAttr(self, plug, value, **kwargs):
        layer = plug.split('.')[0]
        if layer in self.layer_visibility:
            self.layer_visibility[layer] = value

    def getAttr(self, plug):
        parts = plug.split('.')
        if len(parts) > 1 and parts[1] == 'visibility':
            return self.layer_visibility.get(parts[0], 1)
        return None

    def attributeQuery(self, attr, **kwargs):
        node = kwargs.get('node')
        if attr == 'drawInfo':
            return node in self.layers
        return False

    # -- dag -----------------------------------------------------------
    def nodeType(self, name):
        return 'displayLayer' if name in self.layers else 'transform'

    def listRelatives(self, node, **kwargs):
        if kwargs.get('parent'):
            parent = self.parents.get(node)
            return [parent] if parent else None
        return None

    def ls(self, *args, **kwargs):
        if kwargs.get('type') == 'displayLayer':
            return list(self.layers.keys())
        return []

    # -- connections ---------------------------------------------------
    def connectAttr(self, source, dest, **kwargs):
        self.connections[dest] = source
        layer = source.split('.')[0]
        node = dest.split('.')[0]
        for members in self.layers.values():
            if node in members:
                members.remove(node)
        self.layers.setdefault(layer, []).append(node)

    def disconnectAttr(self, source, dest):
        self.connections.pop(dest, None)

    def isConnected(self, source, dest):
        return self.connections.get(dest) == source

    def listConnections(self, plug, **kwargs):
        if plug.endswith('.drawOverride') and kwargs.get('plugs'):
            existing = self.connections.get(plug)
            return [existing] if existing else None
        return []

    def editDisplayLayerMembers(self, layer, *nodes, **kwargs):
        if kwargs.get('query'):
            return self.layers.get(layer, [])
        for node in nodes:
            if node not in self.layers.setdefault(layer, []):
                self.layers[layer].append(node)

    def refresh(self, **kwargs):
        pass


class DisplayLayerTestCase(unittest.TestCase):

    def setUp(self):
        import core.display_layers as dl_module
        self.original_cmds = dl_module.cmds
        self.mock_cmds = MockCmds()
        dl_module.cmds = self.mock_cmds

        self.manager = DisplayLayerManager()

        self.mock_cmds.nodes.add('pCube1')
        self.mock_cmds.nodes.add('pSphere1')

        self.active = DisplayLayerManager.ACTIVE_LAYER
        self.inactive = DisplayLayerManager.INACTIVE_LAYER

    def tearDown(self):
        import core.display_layers as dl_module
        dl_module.cmds = self.original_cmds


class TestGlobalLayers(DisplayLayerTestCase):

    def test_both_global_layers_are_created(self):
        self.assertIn(self.active, self.mock_cmds.layers)
        self.assertIn(self.inactive, self.mock_cmds.layers)

    def test_active_is_visible_and_inactive_is_hidden(self):
        self.assertEqual(self.mock_cmds.layer_visibility[self.active], 1)
        self.assertEqual(self.mock_cmds.layer_visibility[self.inactive], 0)

    def test_ensure_global_layers_is_idempotent(self):
        before = sorted(self.mock_cmds.layers)
        self.manager.ensure_global_layers()
        self.assertEqual(sorted(self.mock_cmds.layers), before)


class TestAssignToLayer(DisplayLayerTestCase):

    def test_assign_connects_draw_override_to_the_layer(self):
        self.manager.assign_to_layer('pCube1', self.active)

        self.assertEqual(self.mock_cmds.connections['pCube1.drawOverride'],
                         self.active + '.drawInfo')

    def test_assign_moves_a_node_between_layers(self):
        self.manager.assign_to_layer('pCube1', self.active)
        self.manager.assign_to_layer('pCube1', self.inactive)

        self.assertEqual(self.mock_cmds.connections['pCube1.drawOverride'],
                         self.inactive + '.drawInfo')
        self.assertNotIn('pCube1', self.mock_cmds.layers[self.active])

    def test_missing_layer_raises(self):
        with self.assertRaises(ValueError):
            self.manager.assign_to_layer('pCube1', 'no_such_layer')

    def test_missing_node_raises(self):
        with self.assertRaises(ValueError):
            self.manager.assign_to_layer('no_such_node', self.active)


class TestVisibility(DisplayLayerTestCase):

    def test_set_layer_visibility(self):
        self.manager.set_layer_visibility(self.active, False)
        self.assertEqual(self.mock_cmds.layer_visibility[self.active], 0)

        self.manager.set_layer_visibility(self.active, True)
        self.assertEqual(self.mock_cmds.layer_visibility[self.active], 1)

    def test_show_layer(self):
        self.manager.hide_layer(self.active)
        self.manager.show_layer(self.active)
        self.assertEqual(self.mock_cmds.layer_visibility[self.active], 1)

    def test_hide_layer(self):
        self.manager.hide_layer(self.active)
        self.assertEqual(self.mock_cmds.layer_visibility[self.active], 0)


class TestMembership(DisplayLayerTestCase):

    def test_get_layer_members(self):
        self.manager.assign_to_layer('pCube1', self.active)
        self.manager.assign_to_layer('pSphere1', self.active)

        members = self.manager.get_layer_members(self.active)
        self.assertIn('pCube1', members)
        self.assertIn('pSphere1', members)

    def test_get_layer_members_empty(self):
        self.assertEqual(self.manager.get_layer_members(self.inactive), [])

    def test_get_layer_members_invalid_layer(self):
        self.assertEqual(self.manager.get_layer_members('no_such_layer'), [])

    def test_is_in_layer(self):
        self.manager.assign_to_layer('pCube1', self.active)

        self.assertTrue(self.manager.is_in_layer('pCube1', self.active))
        self.assertFalse(self.manager.is_in_layer('pSphere1', self.active))


class TestGetAllCtxLayers(DisplayLayerTestCase):
    """Scope is covered in depth by tests/test_ctx_layer_scope.py."""

    def test_returns_the_two_global_layers_only(self):
        self.mock_cmds.createDisplayLayer(name='MASTER_BG_A')

        ctx_layers = self.manager.get_all_ctx_layers()

        self.assertEqual(sorted(ctx_layers), sorted([self.active, self.inactive]))
        self.assertNotIn('MASTER_BG_A', ctx_layers)


if __name__ == '__main__':
    unittest.main()
