# -*- coding: utf-8 -*-
"""Tests for core.nodes.create_standin_sequence -- CFX standin creation.

Runs without Maya by patching core.nodes.cmds.
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

from core import nodes as core_nodes_pkg

# create_standin_sequence lives in core/nodes.py, which the core.nodes package
# shadows and loads as "core.nodes_legacy".  Patch that module's globals --
# patching the package would have no effect on the function's lookups.
core_nodes = core_nodes_pkg.nodes_legacy


class MockCmds(object):
    """Mock Maya cmds covering the calls create_standin_sequence makes."""

    def __init__(self):
        self.nodes = {}          # name -> {'_type', '_parent'}
        self.attrs = {}          # 'node.attr' -> value
        self.connections = []    # (src, dst)
        self.namespaces = [':']
        self.current_ns = ':'

    # -- namespaces --------------------------------------------------------

    def namespace(self, **kwargs):
        if 'exists' in kwargs:
            return kwargs['exists'] in self.namespaces
        if 'add' in kwargs:
            self.namespaces.append(kwargs['add'])
            return kwargs['add']
        if 'set' in kwargs:
            self.current_ns = kwargs['set']
            return kwargs['set']
        return None

    def namespaceInfo(self, **kwargs):
        return self.current_ns

    # -- nodes -------------------------------------------------------------

    def createNode(self, node_type, name=None, parent=None, **kwargs):
        self.nodes[name] = {'_type': node_type, '_parent': parent}
        return name

    def objExists(self, name):
        return name.split('.')[0] in self.nodes

    def parent(self, node, target):
        short = node.split(':')[-1]
        for key in (node, short):
            if key in self.nodes:
                self.nodes[key]['_parent'] = target
                return [node]
        self.nodes[node] = {'_type': 'transform', '_parent': target}
        return [node]

    # -- attributes --------------------------------------------------------

    def setAttr(self, plug, *args, **kwargs):
        self.attrs[plug] = args[0] if args else None

    def getAttr(self, plug):
        return self.attrs.get(plug)

    def listConnections(self, plug, **kwargs):
        found = [s for s, d in self.connections if d == plug]
        return found or None

    def connectAttr(self, src, dst, **kwargs):
        self.connections.append((src, dst))


class FakeConfig(object):
    """ProjectConfig stand-in with CFX accessors."""

    def __init__(self, suffix='_aiStandIn', group='Cfx_Grp',
                 frame_driver='time', attrs=None):
        self._suffix = suffix
        self._group = group
        self._frame_driver = frame_driver
        self._attrs = attrs or {}

    def get_cfx_standin_suffix(self):
        return self._suffix

    def get_cfx_group_name(self):
        return self._group

    def get_cfx_frame_driver(self):
        return self._frame_driver

    def get_cfx_attribute(self, key):
        defaults = {
            'path': 'dso',
            'useFrameExtension': 'useFrameExtension',
            'frameNumber': 'frameNumber',
            'frameOffset': 'frameOffset',
        }
        return self._attrs.get(key, defaults.get(key, key))


NS = 'Ep02_sq0220_SH1350__CFX_botgroomSamS001'
FRAME_PATH = ('X:/EGA/all/scene/Ep02/sq0220/SH1350/cfx/publish/v009/'
              'Ep02_sq0220_SH1350__CFX_botgroomSamS001_ass/'
              'Ep02_sq0220_SH1350__CFX_botgroomSamS001.####.ass')


class CFXStandinTestCase(unittest.TestCase):

    def setUp(self):
        self.cmds = MockCmds()
        self._patches = [
            patch.object(core_nodes, 'cmds', self.cmds),
            patch.object(core_nodes, 'MAYA_AVAILABLE', True),
        ]
        for p in self._patches:
            p.start()
        self.addCleanup(self._stop)

    def _stop(self):
        for p in self._patches:
            p.stop()


class TestNodeStructure(CFXStandinTestCase):

    def test_creates_three_levels(self):
        top, transform, shape = core_nodes.create_standin_sequence(
            NS, FRAME_PATH)

        self.assertEqual(top, '{}:{}'.format(NS, NS))
        self.assertEqual(transform, '{}:{}_aiStandIn'.format(NS, NS))
        self.assertEqual(shape, '{}:{}_aiStandInShape'.format(NS, NS))

    def test_shape_is_ai_standin(self):
        core_nodes.create_standin_sequence(NS, FRAME_PATH)
        self.assertEqual(self.cmds.nodes[NS + '_aiStandInShape']['_type'],
                         'aiStandIn')

    def test_hierarchy_is_nested(self):
        core_nodes.create_standin_sequence(NS, FRAME_PATH)
        self.assertEqual(self.cmds.nodes[NS + '_aiStandIn']['_parent'], NS)
        self.assertEqual(
            self.cmds.nodes[NS + '_aiStandInShape']['_parent'],
            NS + '_aiStandIn')


class TestPathAndFrames(CFXStandinTestCase):

    def test_frame_token_survives_into_dso(self):
        core_nodes.create_standin_sequence(NS, FRAME_PATH)
        dso = self.cmds.attrs['{}_aiStandInShape.dso'.format(NS)]
        self.assertEqual(dso, FRAME_PATH)
        self.assertIn('####', dso)

    def test_use_frame_extension_enabled(self):
        core_nodes.create_standin_sequence(NS, FRAME_PATH)
        self.assertEqual(
            self.cmds.attrs['{}_aiStandInShape.useFrameExtension'.format(NS)], 1)

    def test_frame_driven_by_time(self):
        core_nodes.create_standin_sequence(NS, FRAME_PATH)
        self.assertIn(
            ('time1.outTime', '{}_aiStandInShape.frameNumber'.format(NS)),
            self.cmds.connections)

    def test_frame_driver_none_leaves_frame_undriven(self):
        cfg = FakeConfig(frame_driver='none')
        core_nodes.create_standin_sequence(NS, FRAME_PATH, config=cfg)
        self.assertEqual(self.cmds.connections, [])

    def test_existing_frame_connection_is_not_clobbered(self):
        plug = '{}_aiStandInShape.frameNumber'.format(NS)
        self.cmds.connections.append(('someExpr.output', plug))
        core_nodes.create_standin_sequence(NS, FRAME_PATH)
        drivers = [s for s, d in self.cmds.connections if d == plug]
        self.assertEqual(drivers, ['someExpr.output'])


class TestGrouping(CFXStandinTestCase):

    def test_creates_group_when_missing(self):
        core_nodes.create_standin_sequence(NS, FRAME_PATH)
        self.assertIn('Cfx_Grp', self.cmds.nodes)

    def test_reuses_existing_group(self):
        self.cmds.nodes['Cfx_Grp'] = {'_type': 'transform', '_parent': None}
        core_nodes.create_standin_sequence(NS, FRAME_PATH)
        self.assertEqual(self.cmds.nodes[NS]['_parent'], 'Cfx_Grp')

    def test_group_name_from_config(self):
        cfg = FakeConfig(group='CFX_Group')
        core_nodes.create_standin_sequence(NS, FRAME_PATH, config=cfg)
        self.assertIn('CFX_Group', self.cmds.nodes)

    def test_group_name_explicit_override(self):
        core_nodes.create_standin_sequence(
            NS, FRAME_PATH, group_name='Custom_Grp')
        self.assertIn('Custom_Grp', self.cmds.nodes)


class TestNamespace(CFXStandinTestCase):

    def test_namespace_created(self):
        core_nodes.create_standin_sequence(NS, FRAME_PATH)
        self.assertIn(NS, self.cmds.namespaces)

    def test_namespace_restored_after_creation(self):
        self.cmds.current_ns = ':'
        core_nodes.create_standin_sequence(NS, FRAME_PATH)
        self.assertEqual(self.cmds.current_ns, ':')

    def test_existing_namespace_not_recreated(self):
        self.cmds.namespaces.append(NS)
        core_nodes.create_standin_sequence(NS, FRAME_PATH)
        self.assertEqual(self.cmds.namespaces.count(NS), 1)

    def test_namespace_restored_even_on_failure(self):
        def boom(*a, **k):
            raise RuntimeError('createNode failed')
        self.cmds.createNode = boom
        self.cmds.current_ns = ':'

        with self.assertRaises(RuntimeError):
            core_nodes.create_standin_sequence(NS, FRAME_PATH)

        self.assertEqual(self.cmds.current_ns, ':')


class TestConfigDrivenAttributes(CFXStandinTestCase):

    def test_attribute_names_come_from_config(self):
        cfg = FakeConfig(attrs={'path': 'filename',
                                'useFrameExtension': 'useSequence'})
        core_nodes.create_standin_sequence(NS, FRAME_PATH, config=cfg)
        self.assertIn('{}_aiStandInShape.filename'.format(NS), self.cmds.attrs)
        self.assertIn('{}_aiStandInShape.useSequence'.format(NS), self.cmds.attrs)

    def test_standin_suffix_from_config(self):
        cfg = FakeConfig(suffix='_aiStandin')
        top, transform, shape = core_nodes.create_standin_sequence(
            NS, FRAME_PATH, config=cfg)
        self.assertTrue(transform.endswith('_aiStandin'))
        self.assertTrue(shape.endswith('_aiStandinShape'))


class TestMayaUnavailable(unittest.TestCase):

    def test_raises_without_maya(self):
        with patch.object(core_nodes, 'MAYA_AVAILABLE', False):
            with self.assertRaises(RuntimeError):
                core_nodes.create_standin_sequence(NS, FRAME_PATH)


if __name__ == '__main__':
    unittest.main()
