"""Tests for CTXSlateOriginalsSchema and CTXSlateOriginalsNode.

All tests run without Maya using module-level cmds patching,
matching the pattern used in test_slate_nodes.py.
"""

from __future__ import absolute_import, division, print_function

import sys
import os
import json
import unittest
from unittest.mock import MagicMock

# Ensure project root is on the path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core.nodes.schemas.slate_originals import CTXSlateOriginalsSchema
from core.nodes.wrappers.slate_originals import CTXSlateOriginalsNode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_cmds(initial_json='{}'):
    """Return a MagicMock that behaves like a minimal maya.cmds.

    The mock stores a single 'originalsJson' string attribute on node
    'CTX_SlateOriginals1' so that _load() / _save() round-trips work.
    """
    store = {'CTX_SlateOriginals1.originalsJson': initial_json}

    mock = MagicMock()
    mock.objExists.return_value = True

    def _getAttr(attr):
        return store.get(attr, '{}')

    def _setAttr(attr, value, type=None):
        store[attr] = value

    mock.getAttr.side_effect = _getAttr
    mock.setAttr.side_effect = _setAttr

    # ls(type='network') returns our node
    mock.ls.return_value = ['CTX_SlateOriginals1']
    # attributeQuery ctx_type exists -> True
    mock.attributeQuery.return_value = True

    return mock, store


def _make_empty_scene_cmds():
    """Mock where no network nodes exist yet (forces create path)."""
    store = {}

    mock = MagicMock()
    mock.objExists.return_value = True
    mock.ls.return_value = []  # No existing network nodes
    mock.attributeQuery.return_value = False

    def _getAttr(attr):
        return store.get(attr, '{}')

    def _setAttr(attr, value, type=None):
        store[attr] = value

    mock.getAttr.side_effect = _getAttr
    mock.setAttr.side_effect = _setAttr
    mock.createNode.return_value = 'CTX_SlateOriginals1'

    return mock, store


# ---------------------------------------------------------------------------
# Schema tests (no Maya required)
# ---------------------------------------------------------------------------

class TestCTXSlateOriginalsSchemaAttributes(unittest.TestCase):
    """CTXSlateOriginalsSchema has the expected attribute keys."""

    def setUp(self):
        self.schema = CTXSlateOriginalsSchema()

    def test_ctx_type_present(self):
        self.assertIn('ctx_type', self.schema.ATTRIBUTES)

    def test_ctx_type_default(self):
        self.assertEqual(
            self.schema.ATTRIBUTES['ctx_type']['default'],
            'CTX_SlateOriginals',
        )

    def test_originals_json_present(self):
        self.assertIn('originalsJson', self.schema.ATTRIBUTES)

    def test_originals_json_default_is_empty_object(self):
        self.assertEqual(self.schema.ATTRIBUTES['originalsJson']['default'], '{}')

    def test_all_attributes_have_type(self):
        for name, defn in self.schema.ATTRIBUTES.items():
            self.assertIn('type', defn, 'Attribute {} missing type'.format(name))

    def test_no_connections(self):
        self.assertEqual(len(self.schema.CONNECTIONS), 0)

    def test_node_type_is_network(self):
        self.assertEqual(self.schema.NODE_TYPE, 'network')

    def test_node_prefix(self):
        self.assertEqual(self.schema.NODE_PREFIX, 'CTX_SlateOriginals')


# ---------------------------------------------------------------------------
# get_or_create tests
# ---------------------------------------------------------------------------

class TestGetOrCreate(unittest.TestCase):
    """get_or_create() finds existing node or creates a new one."""

    def test_get_or_create_raises_without_maya(self):
        """Without Maya, get_or_create() raises RuntimeError."""
        import core.nodes.wrappers.slate_originals as mod
        orig = mod.cmds
        mod.cmds = None
        try:
            with self.assertRaises(RuntimeError):
                CTXSlateOriginalsNode.get_or_create()
        finally:
            mod.cmds = orig

    def test_get_or_create_finds_existing_node(self):
        """get_or_create() returns the existing node without creating a new one."""
        import core.nodes.wrappers.slate_originals as mod
        mock_cmds, store = _make_mock_cmds()
        # Make ctx_type check return 'CTX_SlateOriginals'
        mock_cmds.getAttr.side_effect = lambda attr: (
            'CTX_SlateOriginals' if attr == 'CTX_SlateOriginals1.ctx_type' else store.get(attr, '{}')
        )
        orig = mod.cmds
        mod.cmds = mock_cmds
        try:
            node = CTXSlateOriginalsNode.get_or_create()
            self.assertIsInstance(node, CTXSlateOriginalsNode)
            self.assertEqual(node.node_name, 'CTX_SlateOriginals1')
            # createNode should NOT have been called
            mock_cmds.createNode.assert_not_called()
        finally:
            mod.cmds = orig

    def test_get_or_create_returns_same_node_on_second_call(self):
        """Two calls to get_or_create() return wrappers for the same underlying node."""
        import core.nodes.wrappers.slate_originals as mod
        mock_cmds, store = _make_mock_cmds()
        mock_cmds.getAttr.side_effect = lambda attr: (
            'CTX_SlateOriginals' if attr == 'CTX_SlateOriginals1.ctx_type' else store.get(attr, '{}')
        )
        orig = mod.cmds
        mod.cmds = mock_cmds
        try:
            node1 = CTXSlateOriginalsNode.get_or_create()
            node2 = CTXSlateOriginalsNode.get_or_create()
            self.assertEqual(node1.node_name, node2.node_name)
        finally:
            mod.cmds = orig

    def test_get_or_create_creates_node_when_absent(self):
        """get_or_create() calls createNode when no existing node is found."""
        import core.nodes.wrappers.slate_originals as mod
        import core.nodes.base as base_mod
        mock_cmds, store = _make_empty_scene_cmds()
        orig_mod = mod.cmds
        orig_base = base_mod.cmds
        mod.cmds = mock_cmds
        base_mod.cmds = mock_cmds
        try:
            node = CTXSlateOriginalsNode.get_or_create()
            self.assertIsInstance(node, CTXSlateOriginalsNode)
            mock_cmds.createNode.assert_called_once()
        finally:
            mod.cmds = orig_mod
            base_mod.cmds = orig_base


# ---------------------------------------------------------------------------
# store_layer tests
# ---------------------------------------------------------------------------

class TestStoreLayer(unittest.TestCase):
    """store_layer() persists renderable state."""

    def _node_with_mock(self, initial_json='{}'):
        import core.nodes.wrappers.slate_originals as mod
        mock_cmds, store = _make_mock_cmds(initial_json)
        # ctx_type read not needed here -- node already wrapped
        node = CTXSlateOriginalsNode('CTX_SlateOriginals1')
        return node, mock_cmds, store, mod

    def test_store_layer_writes_to_json(self):
        node, mock_cmds, store, mod = self._node_with_mock()
        orig = mod.cmds
        mod.cmds = mock_cmds
        try:
            node.store_layer('beauty', True)
            stored = json.loads(store['CTX_SlateOriginals1.originalsJson'])
            self.assertIn('beauty', stored)
            self.assertTrue(stored['beauty'])
        finally:
            mod.cmds = orig

    def test_store_layer_is_no_op_if_already_stored(self):
        """Calling store_layer twice for the same layer name does not overwrite."""
        node, mock_cmds, store, mod = self._node_with_mock(
            json.dumps({'beauty': True})
        )
        orig = mod.cmds
        mod.cmds = mock_cmds
        try:
            node.store_layer('beauty', False)  # Attempt to overwrite with False
            stored = json.loads(store['CTX_SlateOriginals1.originalsJson'])
            # Must still be True (first-write wins)
            self.assertTrue(stored['beauty'])
        finally:
            mod.cmds = orig

    def test_store_layer_multiple_layers(self):
        node, mock_cmds, store, mod = self._node_with_mock()
        orig = mod.cmds
        mod.cmds = mock_cmds
        try:
            node.store_layer('beauty', True)
            node.store_layer('diffuse', False)
            node.store_layer('specular', True)
            stored = json.loads(store['CTX_SlateOriginals1.originalsJson'])
            self.assertEqual(len(stored), 3)
            self.assertTrue(stored['beauty'])
            self.assertFalse(stored['diffuse'])
            self.assertTrue(stored['specular'])
        finally:
            mod.cmds = orig

    def test_store_layer_coerces_to_bool(self):
        """store_layer coerces truthy/falsy values to bool."""
        node, mock_cmds, store, mod = self._node_with_mock()
        orig = mod.cmds
        mod.cmds = mock_cmds
        try:
            node.store_layer('beauty', 1)   # truthy int
            node.store_layer('diffuse', 0)  # falsy int
            stored = json.loads(store['CTX_SlateOriginals1.originalsJson'])
            self.assertIs(stored['beauty'], True)
            self.assertIs(stored['diffuse'], False)
        finally:
            mod.cmds = orig


# ---------------------------------------------------------------------------
# has_layer tests
# ---------------------------------------------------------------------------

class TestHasLayer(unittest.TestCase):
    """has_layer() returns True/False correctly."""

    def test_has_layer_true_when_stored(self):
        import core.nodes.wrappers.slate_originals as mod
        mock_cmds, store = _make_mock_cmds(json.dumps({'beauty': True}))
        orig = mod.cmds
        mod.cmds = mock_cmds
        try:
            node = CTXSlateOriginalsNode('CTX_SlateOriginals1')
            self.assertTrue(node.has_layer('beauty'))
        finally:
            mod.cmds = orig

    def test_has_layer_false_when_not_stored(self):
        import core.nodes.wrappers.slate_originals as mod
        mock_cmds, store = _make_mock_cmds()
        orig = mod.cmds
        mod.cmds = mock_cmds
        try:
            node = CTXSlateOriginalsNode('CTX_SlateOriginals1')
            self.assertFalse(node.has_layer('beauty'))
        finally:
            mod.cmds = orig

    def test_has_layer_false_after_different_layer_stored(self):
        import core.nodes.wrappers.slate_originals as mod
        mock_cmds, store = _make_mock_cmds(json.dumps({'diffuse': False}))
        orig = mod.cmds
        mod.cmds = mock_cmds
        try:
            node = CTXSlateOriginalsNode('CTX_SlateOriginals1')
            self.assertFalse(node.has_layer('beauty'))
            self.assertTrue(node.has_layer('diffuse'))
        finally:
            mod.cmds = orig


# ---------------------------------------------------------------------------
# get_layer_renderable tests
# ---------------------------------------------------------------------------

class TestGetLayerRenderable(unittest.TestCase):
    """get_layer_renderable() returns stored value or None."""

    def test_returns_true_when_stored_true(self):
        import core.nodes.wrappers.slate_originals as mod
        mock_cmds, store = _make_mock_cmds(json.dumps({'beauty': True}))
        orig = mod.cmds
        mod.cmds = mock_cmds
        try:
            node = CTXSlateOriginalsNode('CTX_SlateOriginals1')
            result = node.get_layer_renderable('beauty')
            self.assertIs(result, True)
        finally:
            mod.cmds = orig

    def test_returns_false_when_stored_false(self):
        import core.nodes.wrappers.slate_originals as mod
        mock_cmds, store = _make_mock_cmds(json.dumps({'beauty': False}))
        orig = mod.cmds
        mod.cmds = mock_cmds
        try:
            node = CTXSlateOriginalsNode('CTX_SlateOriginals1')
            result = node.get_layer_renderable('beauty')
            self.assertIs(result, False)
        finally:
            mod.cmds = orig

    def test_returns_none_when_not_stored(self):
        import core.nodes.wrappers.slate_originals as mod
        mock_cmds, store = _make_mock_cmds()
        orig = mod.cmds
        mod.cmds = mock_cmds
        try:
            node = CTXSlateOriginalsNode('CTX_SlateOriginals1')
            result = node.get_layer_renderable('missing_layer')
            self.assertIsNone(result)
        finally:
            mod.cmds = orig


# ---------------------------------------------------------------------------
# get_all tests
# ---------------------------------------------------------------------------

class TestGetAll(unittest.TestCase):
    """get_all() returns the full dict."""

    def test_get_all_returns_full_dict(self):
        import core.nodes.wrappers.slate_originals as mod
        initial = {'beauty': True, 'diffuse': False, 'specular': True}
        mock_cmds, store = _make_mock_cmds(json.dumps(initial))
        orig = mod.cmds
        mod.cmds = mock_cmds
        try:
            node = CTXSlateOriginalsNode('CTX_SlateOriginals1')
            result = node.get_all()
            self.assertEqual(result, initial)
        finally:
            mod.cmds = orig

    def test_get_all_returns_empty_dict_when_nothing_stored(self):
        import core.nodes.wrappers.slate_originals as mod
        mock_cmds, store = _make_mock_cmds()
        orig = mod.cmds
        mod.cmds = mock_cmds
        try:
            node = CTXSlateOriginalsNode('CTX_SlateOriginals1')
            result = node.get_all()
            self.assertEqual(result, {})
        finally:
            mod.cmds = orig


# ---------------------------------------------------------------------------
# clear tests
# ---------------------------------------------------------------------------

class TestClear(unittest.TestCase):
    """clear() empties the stored dict."""

    def test_clear_empties_dict(self):
        import core.nodes.wrappers.slate_originals as mod
        initial = {'beauty': True, 'diffuse': False}
        mock_cmds, store = _make_mock_cmds(json.dumps(initial))
        orig = mod.cmds
        mod.cmds = mock_cmds
        try:
            node = CTXSlateOriginalsNode('CTX_SlateOriginals1')
            node.clear()
            result = node.get_all()
            self.assertEqual(result, {})
        finally:
            mod.cmds = orig

    def test_clear_then_store_works(self):
        """After clear(), new layers can be stored."""
        import core.nodes.wrappers.slate_originals as mod
        initial = {'beauty': True}
        mock_cmds, store = _make_mock_cmds(json.dumps(initial))
        orig = mod.cmds
        mod.cmds = mock_cmds
        try:
            node = CTXSlateOriginalsNode('CTX_SlateOriginals1')
            node.clear()
            node.store_layer('diffuse', False)
            result = node.get_all()
            self.assertNotIn('beauty', result)
            self.assertIn('diffuse', result)
            self.assertFalse(result['diffuse'])
        finally:
            mod.cmds = orig


# ---------------------------------------------------------------------------
# JSON round-trip tests
# ---------------------------------------------------------------------------

class TestJsonRoundTrip(unittest.TestCase):
    """Store then reload produces identical data."""

    def test_json_round_trip(self):
        """Values stored survive a simulated save/reload cycle."""
        import core.nodes.wrappers.slate_originals as mod
        mock_cmds, store = _make_mock_cmds()
        orig = mod.cmds
        mod.cmds = mock_cmds
        try:
            node = CTXSlateOriginalsNode('CTX_SlateOriginals1')
            node.store_layer('beauty', True)
            node.store_layer('diffuse', False)
            node.store_layer('specular', True)

            # Reload by creating a new wrapper pointing to the same node name
            # (same store dict in memory, simulating scene save/reload)
            node2 = CTXSlateOriginalsNode('CTX_SlateOriginals1')
            self.assertTrue(node2.has_layer('beauty'))
            self.assertTrue(node2.has_layer('diffuse'))
            self.assertTrue(node2.has_layer('specular'))
            self.assertTrue(node2.get_layer_renderable('beauty'))
            self.assertFalse(node2.get_layer_renderable('diffuse'))
            self.assertTrue(node2.get_layer_renderable('specular'))
        finally:
            mod.cmds = orig

    def test_invalid_json_returns_empty_dict(self):
        """_load() returns {} when originalsJson contains invalid JSON."""
        import core.nodes.wrappers.slate_originals as mod
        mock_cmds, store = _make_mock_cmds('NOT VALID JSON {{{{')
        orig = mod.cmds
        mod.cmds = mock_cmds
        try:
            node = CTXSlateOriginalsNode('CTX_SlateOriginals1')
            result = node.get_all()
            self.assertEqual(result, {})
        finally:
            mod.cmds = orig


# ---------------------------------------------------------------------------
# Export / integration tests
# ---------------------------------------------------------------------------

class TestWrapperInitExport(unittest.TestCase):
    """CTXSlateOriginalsNode is exported from core.nodes.wrappers."""

    def test_in_all(self):
        import core.nodes.wrappers as wrappers
        self.assertIn('CTXSlateOriginalsNode', wrappers.__all__)

    def test_importable_from_package(self):
        from core.nodes.wrappers import CTXSlateOriginalsNode as imported
        self.assertIs(imported, CTXSlateOriginalsNode)


if __name__ == '__main__':
    unittest.main()
