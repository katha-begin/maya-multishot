# -*- coding: utf-8 -*-
"""Tests for the targetNode fallback in DisplayLayerManager.

Assets that carry no real Maya namespace -- CFX standins adopted from a scene
built by an upstream tool -- were silently skipped by switch_shot_layers,
because _get_namespace_root resolves objects with cmds.ls('<ns>:*').

Runs without Maya.
"""

from __future__ import absolute_import, division, print_function

import os
import sys
import unittest

try:
    from unittest.mock import patch
except ImportError:  # Python 2.7
    from mock import patch

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core import display_layers


BASENAME = 'Ep02_sq0220_SH1350__CFX_botgroomSamS001'
GROUP = 'Cfx_Grp'


class MockCmds(object):
    """Mock cmds modelling a flat-named CFX hierarchy under a group."""

    def __init__(self):
        # child -> parent, using bare names (no namespaces present)
        self.parents = {
            BASENAME: GROUP,
            BASENAME + '_aiStandIn': BASENAME,
            BASENAME + '_aiStandInShape': BASENAME + '_aiStandIn',
            GROUP: None,
        }
        self.types = {
            BASENAME: 'transform',
            BASENAME + '_aiStandIn': 'transform',
            BASENAME + '_aiStandInShape': 'aiStandIn',
            GROUP: 'transform',
            'CTX_Asset_CFX_botgroomSamS_SH1350': 'network',
        }
        self.target_links = {
            'CTX_Asset_CFX_botgroomSamS_SH1350': [BASENAME + '_aiStandInShape'],
        }
        self.ls_results = {}

    def objExists(self, name):
        return name.split('.')[0] in self.types

    def nodeType(self, name):
        return self.types.get(name, 'transform')

    def ls(self, pattern, **kwargs):
        return self.ls_results.get(pattern, [])

    def listRelatives(self, node, **kwargs):
        if kwargs.get('parent'):
            parent = self.parents.get(node)
            return [parent] if parent else None
        return None

    def attributeQuery(self, attr, **kwargs):
        node = kwargs.get('node')
        if attr == 'targetNode':
            return node in self.target_links
        return False

    def listConnections(self, plug, **kwargs):
        node = plug.split('.')[0]
        return self.target_links.get(node) or None


class FakeAsset(object):
    def __init__(self, node_name, namespace):
        self.node_name = node_name
        self._namespace = namespace

    def get_namespace(self):
        return self._namespace


class ResolveTopNodeTestCase(unittest.TestCase):

    def setUp(self):
        self.cmds = MockCmds()
        p = patch.object(display_layers, 'cmds', self.cmds)
        p.start()
        self.addCleanup(p.stop)
        self.mgr = display_layers.DisplayLayerManager.__new__(
            display_layers.DisplayLayerManager)


class TestNamespaceStillWins(ResolveTopNodeTestCase):

    def test_namespace_lookup_used_when_it_resolves(self):
        """A real namespace must keep resolving the way it always has."""
        ns = 'CHAR_CatStompie_001'
        self.cmds.ls_results['{}:*'.format(ns)] = ['|{}:top'.format(ns)]
        self.cmds.parents['|{}:top'.format(ns)] = None

        top = self.mgr._resolve_top_node(ns, None)
        self.assertEqual(top, '|{}:top'.format(ns))


class TestTargetNodeFallback(ResolveTopNodeTestCase):

    def test_flat_named_asset_resolves_via_target_node(self):
        asset = FakeAsset('CTX_Asset_CFX_botgroomSamS_SH1350', BASENAME)
        top = self.mgr._resolve_top_node(BASENAME, asset)
        self.assertEqual(top, BASENAME)

    def test_fallback_climbs_past_intermediate_standin_transform(self):
        """The shape's immediate parent is the middle transform, not the top."""
        asset = FakeAsset('CTX_Asset_CFX_botgroomSamS_SH1350', BASENAME)
        top = self.mgr._resolve_top_node(BASENAME, asset)
        self.assertNotEqual(top, BASENAME + '_aiStandIn')
        self.assertEqual(top, BASENAME)

    def test_fallback_stops_at_group(self):
        asset = FakeAsset('CTX_Asset_CFX_botgroomSamS_SH1350', BASENAME)
        top = self.mgr._resolve_top_node(BASENAME, asset)
        self.assertNotEqual(top, GROUP)

    def test_returns_none_without_asset(self):
        self.assertIsNone(self.mgr._resolve_top_node(BASENAME, None))

    def test_returns_none_when_target_node_missing(self):
        asset = FakeAsset('CTX_Asset_Unlinked', BASENAME)
        self.assertIsNone(self.mgr._resolve_top_node(BASENAME, asset))

    def test_returns_none_when_target_node_is_dead(self):
        self.cmds.target_links['CTX_Asset_Dead'] = ['someDeletedNode']
        self.cmds.types['CTX_Asset_Dead'] = 'network'
        asset = FakeAsset('CTX_Asset_Dead', BASENAME)
        self.assertIsNone(self.mgr._resolve_top_node(BASENAME, asset))


class TestWalkUpGuards(ResolveTopNodeTestCase):

    def test_cyclic_hierarchy_terminates(self):
        self.cmds.parents['a'] = 'ab'
        self.cmds.parents['ab'] = 'a'
        self.cmds.types['a'] = 'transform'
        self.cmds.types['ab'] = 'transform'
        result = self.mgr._walk_up_to_identity_root('a', 'a')
        self.assertIn(result, ('a', 'ab'))

    def test_node_with_no_parent_returns_itself(self):
        self.assertEqual(
            self.mgr._walk_up_to_identity_root(GROUP, GROUP), GROUP)

    def test_namespaced_parent_matched_on_short_name(self):
        self.cmds.parents['ns:' + BASENAME + '_aiStandIn'] = 'ns:' + BASENAME
        self.cmds.parents['ns:' + BASENAME] = GROUP
        result = self.mgr._walk_up_to_identity_root(
            'ns:' + BASENAME + '_aiStandIn', BASENAME)
        self.assertEqual(result, 'ns:' + BASENAME)


if __name__ == '__main__':
    unittest.main()
