# -*- coding: utf-8 -*-
"""Tests for core/cfx_adopter.py and the CFXNamespaceCheck validator check.

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

from core import cfx_adopter


BASENAME = 'Ep02_sq0220_SH1350__CFX_botgroomSamS001'
DSO = ('X:/EGA/all/scene/Ep02/sq0220/SH1350/cfx/publish/v009/'
       + BASENAME + '_ass/' + BASENAME + '.####.ass')


class TestParseDsoPath(unittest.TestCase):

    def test_full_context_recovered(self):
        ctx = cfx_adopter.parse_dso_path(DSO)
        self.assertEqual(ctx['ep'], 'Ep02')
        self.assertEqual(ctx['seq'], 'sq0220')
        self.assertEqual(ctx['shot'], 'SH1350')
        self.assertEqual(ctx['dept'], 'cfx')
        self.assertEqual(ctx['ver'], 'v009')
        self.assertEqual(ctx['type'], 'CFX')
        self.assertEqual(ctx['name'], 'botgroomSamS')
        self.assertEqual(ctx['variant'], '001')
        self.assertEqual(ctx['ext'], 'ass')
        self.assertEqual(ctx['basename'], BASENAME)

    def test_windows_separators(self):
        ctx = cfx_adopter.parse_dso_path(DSO.replace('/', '\\'))
        self.assertEqual(ctx['shot'], 'SH1350')
        self.assertEqual(ctx['ver'], 'v009')

    def test_roundtrip_with_builder(self):
        from core import asset_types
        basename = asset_types.build_basename(
            'Ep02', 'sq0220', 'SH1350', 'CFX', 'botgroomSamS', '001')
        path = '/'.join([
            'X:/EGA/all/scene/Ep02/sq0220/SH1350/cfx/publish/v009',
            asset_types.build_sequence_dir_name(basename, 'ass'),
            asset_types.build_frame_file_name(basename, 'ass'),
        ])
        ctx = cfx_adopter.parse_dso_path(path)
        self.assertEqual(ctx['basename'], basename)

    def test_empty_path(self):
        self.assertIsNone(cfx_adopter.parse_dso_path(''))
        self.assertIsNone(cfx_adopter.parse_dso_path(None))

    def test_non_sequence_path_rejected(self):
        path = ('V:/SWA/all/scene/Ep04/sq0070/SH0140/lighting/publish/v003/'
                'Ep04_sq0070_SH0140__CHAR_CatStompie_001.abc')
        self.assertIsNone(cfx_adopter.parse_dso_path(path))

    def test_short_path_rejected(self):
        self.assertIsNone(cfx_adopter.parse_dso_path('just/two'))

    def test_missing_version_dir_still_parses_asset(self):
        path = 'somewhere/' + BASENAME + '_ass/' + BASENAME + '.####.ass'
        ctx = cfx_adopter.parse_dso_path(path)
        self.assertEqual(ctx['basename'], BASENAME)
        self.assertEqual(ctx['ver'], '')


class MockCmds(object):
    """Mock cmds modelling a small CFX scene."""

    def __init__(self):
        self.standins = {}       # shape -> dso
        self.networks = {}       # node -> {attr: value}
        self.links = {}          # node -> [linked]
        self.namespaces = []
        self.ns_contents = {}
        self.parents = {}
        self.types = {}

    def ls(self, *args, **kwargs):
        node_type = kwargs.get('type')
        if node_type == 'aiStandIn':
            return list(self.standins.keys())
        if node_type == 'network':
            return list(self.networks.keys())
        if args:
            return list(self.ns_contents.get(args[0], []))
        return []

    def objExists(self, name):
        node = name.split('.')[0]
        if '.' in name:
            attr = name.split('.', 1)[1]
            if node in self.standins:
                return attr in ('dso',)
        return (node in self.standins or node in self.networks
                or node in self.types)

    def getAttr(self, plug):
        node, attr = plug.split('.', 1)
        if node in self.standins and attr == 'dso':
            return self.standins[node]
        return self.networks.get(node, {}).get(attr)

    def nodeType(self, node):
        if node in self.standins:
            return 'aiStandIn'
        return self.types.get(node, 'transform')

    def attributeQuery(self, attr, **kwargs):
        node = kwargs.get('node')
        if node in self.networks:
            return attr in self.networks[node]
        return False

    def listConnections(self, plug, **kwargs):
        node = plug.split('.')[0]
        return self.links.get(node) or None

    def listRelatives(self, node, **kwargs):
        if kwargs.get('parent'):
            parent = self.parents.get(node)
            return [parent] if parent else None
        return None

    def namespace(self, **kwargs):
        if 'exists' in kwargs:
            return kwargs['exists'] in self.namespaces
        return None


class AdopterTestCase(unittest.TestCase):

    def setUp(self):
        self.cmds = MockCmds()
        patches = [
            patch.object(cfx_adopter, 'cmds', self.cmds),
            patch.object(cfx_adopter, 'MAYA_AVAILABLE', True),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)


class TestFindCfxStandins(AdopterTestCase):

    def test_finds_standin_by_path(self):
        self.cmds.standins[BASENAME + '_aiStandInShape'] = DSO
        found = cfx_adopter.find_cfx_standins()
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['context']['basename'], BASENAME)

    def test_ignores_non_cfx_standin(self):
        self.cmds.standins['someShape'] = (
            'V:/SWA/all/scene/Ep04/sq0070/SH0140/lighting/publish/v003/'
            'Ep04_sq0070_SH0140__CHAR_CatStompie_001.abc')
        self.assertEqual(cfx_adopter.find_cfx_standins(), [])

    def test_detects_namespace_when_present(self):
        shape = BASENAME + ':' + BASENAME + '_aiStandInShape'
        self.cmds.standins[shape] = DSO
        found = cfx_adopter.find_cfx_standins()
        self.assertEqual(found[0]['namespace'], BASENAME)

    def test_flat_named_standin_has_empty_namespace(self):
        self.cmds.standins[BASENAME + '_aiStandInShape'] = DSO
        found = cfx_adopter.find_cfx_standins()
        self.assertEqual(found[0]['namespace'], '')

    def test_group_membership_detected(self):
        shape = BASENAME + '_aiStandInShape'
        self.cmds.standins[shape] = DSO
        self.cmds.parents[shape] = BASENAME + '_aiStandIn'
        self.cmds.parents[BASENAME + '_aiStandIn'] = BASENAME
        self.cmds.parents[BASENAME] = 'Cfx_Grp'
        found = cfx_adopter.find_cfx_standins()
        self.assertTrue(found[0]['in_group'])

    def test_returns_empty_without_maya(self):
        with patch.object(cfx_adopter, 'MAYA_AVAILABLE', False):
            self.assertEqual(cfx_adopter.find_cfx_standins(), [])


class TestNamespaceConflict(AdopterTestCase):

    def test_free_namespace_has_no_conflict(self):
        self.assertIsNone(cfx_adopter.namespace_conflict(BASENAME))

    def test_empty_namespace_reported(self):
        self.assertIsNotNone(cfx_adopter.namespace_conflict(''))

    def test_existing_empty_namespace_is_free(self):
        self.cmds.namespaces.append(BASENAME)
        self.assertIsNone(cfx_adopter.namespace_conflict(BASENAME))

    def test_namespace_with_unrelated_content_conflicts(self):
        self.cmds.namespaces.append(BASENAME)
        self.cmds.ns_contents['{}:*'.format(BASENAME)] = ['someOtherNode']
        self.cmds.types['someOtherNode'] = 'transform'
        reason = cfx_adopter.namespace_conflict(BASENAME)
        self.assertIn('unrelated', reason)

    def test_namespace_holding_same_asset_reports_duplicate(self):
        shape = BASENAME + ':' + BASENAME + '_aiStandInShape'
        self.cmds.namespaces.append(BASENAME)
        self.cmds.ns_contents['{}:*'.format(BASENAME)] = [shape]
        self.cmds.standins[shape] = DSO
        reason = cfx_adopter.namespace_conflict(BASENAME)
        self.assertIn('already holds this CFX asset', reason)


class TestUnadoptedAndDead(AdopterTestCase):

    def _add_ctx_asset(self, node, namespace, target=None):
        self.cmds.networks[node] = {
            'asset_type': 'CFX',
            'namespace': namespace,
            'targetNode': None,
        }
        if target is not None:
            self.cmds.links[node] = [target]

    def test_standin_without_ctx_asset_is_unadopted(self):
        self.cmds.standins[BASENAME + '_aiStandInShape'] = DSO
        unadopted = cfx_adopter.find_unadopted()
        self.assertEqual(len(unadopted), 1)

    def test_standin_with_ctx_asset_is_not_unadopted(self):
        shape = BASENAME + '_aiStandInShape'
        self.cmds.standins[shape] = DSO
        self._add_ctx_asset('CTX_Asset_CFX_botgroomSamS_SH1350', BASENAME, shape)
        self.assertEqual(cfx_adopter.find_unadopted(), [])

    def test_dead_target_detected(self):
        self._add_ctx_asset('CTX_Asset_CFX_dead_SH1350', BASENAME,
                            'deletedShape')
        self.assertIn('CTX_Asset_CFX_dead_SH1350',
                      cfx_adopter.find_dead_targets())

    def test_live_target_not_reported_dead(self):
        shape = BASENAME + '_aiStandInShape'
        self.cmds.standins[shape] = DSO
        self._add_ctx_asset('CTX_Asset_CFX_live_SH1350', BASENAME, shape)
        self.assertEqual(cfx_adopter.find_dead_targets(), [])

    def test_non_cfx_ctx_asset_ignored(self):
        self.cmds.networks['CTX_Asset_CHAR_Cat_SH0140'] = {
            'asset_type': 'CHAR',
            'namespace': 'CHAR_Cat_001',
        }
        self.assertEqual(cfx_adopter.find_dead_targets(), [])


class TestDuplicateBasenames(AdopterTestCase):

    def test_duplicates_detected(self):
        self.cmds.standins['a_aiStandInShape'] = DSO
        self.cmds.standins['b_aiStandInShape'] = DSO
        dupes = cfx_adopter.find_duplicate_basenames()
        self.assertIn(BASENAME, dupes)
        self.assertEqual(len(dupes[BASENAME]), 2)

    def test_distinct_shots_are_not_duplicates(self):
        other = BASENAME.replace('SH1350', 'SH1180').replace('sq0220', 'sq0210')
        other_dso = ('X:/EGA/all/scene/Ep02/sq0210/SH1180/cfx/publish/v009/'
                     + other + '_ass/' + other + '.####.ass')
        self.cmds.standins['a_aiStandInShape'] = DSO
        self.cmds.standins['b_aiStandInShape'] = other_dso
        self.assertEqual(cfx_adopter.find_duplicate_basenames(), {})


class TestCFXNamespaceCheck(AdopterTestCase):

    def _run_check(self):
        from core.validator.checks import CFXNamespaceCheck
        return CFXNamespaceCheck().run(shot_node=None, config=None)

    def test_passes_on_clean_scene(self):
        result = self._run_check()
        self.assertTrue(result.passed)

    def test_fails_on_duplicate_basenames(self):
        self.cmds.standins['a_aiStandInShape'] = DSO
        self.cmds.standins['b_aiStandInShape'] = DSO
        result = self._run_check()
        self.assertFalse(result.passed)
        self.assertIn(BASENAME, result.message)

    def test_unadopted_reported_but_does_not_fail(self):
        self.cmds.standins[BASENAME + '_aiStandInShape'] = DSO
        result = self._run_check()
        self.assertTrue(result.passed)
        self.assertEqual(len(result.details['unadopted_standins']), 1)

    def test_un_namespaced_reported_but_does_not_fail(self):
        self.cmds.standins[BASENAME + '_aiStandInShape'] = DSO
        result = self._run_check()
        self.assertTrue(result.passed)
        self.assertEqual(len(result.details['un_namespaced_standins']), 1)

    def test_passes_headless(self):
        with patch.object(cfx_adopter, 'MAYA_AVAILABLE', False):
            result = self._run_check()
        self.assertTrue(result.passed)
        self.assertIn('Maya unavailable', result.message)


class _StubAsset(object):
    def __init__(self, asset_type, file_path):
        self._type = asset_type
        self._path = file_path

    def get_asset_type(self):
        return self._type

    def get_file_path(self):
        return self._path

    def get_asset_id(self):
        return '%s_stub' % self._type


class TestSequenceAwarePathCheck(unittest.TestCase):
    """A CFX path carries a frame token and never exists as a file."""

    def setUp(self):
        import tempfile
        from core.validator.checks import asset_paths
        self.asset_paths = asset_paths
        self.tmp = tempfile.mkdtemp()
        self.seq_dir = os.path.join(self.tmp, BASENAME + '_ass')
        os.makedirs(self.seq_dir)

        import shutil
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_cfx_present_when_sequence_dir_exists(self):
        frame_path = os.path.join(self.seq_dir, BASENAME + '.####.ass')
        asset = _StubAsset('CFX', frame_path)
        self.assertTrue(self.asset_paths._publish_present(asset, frame_path))

    def test_cfx_absent_when_sequence_dir_missing(self):
        frame_path = os.path.join(
            self.tmp, 'nope_ass', BASENAME + '.####.ass')
        asset = _StubAsset('CFX', frame_path)
        self.assertFalse(self.asset_paths._publish_present(asset, frame_path))

    def test_plain_file_type_still_uses_exists(self):
        real = os.path.join(self.tmp, 'a.abc')
        with open(real, 'w') as fh:
            fh.write('x')
        asset = _StubAsset('CHAR', real)
        self.assertTrue(self.asset_paths._publish_present(asset, real))

    def test_plain_file_type_missing_is_absent(self):
        missing = os.path.join(self.tmp, 'missing.abc')
        asset = _StubAsset('CHAR', missing)
        self.assertFalse(self.asset_paths._publish_present(asset, missing))

    def test_frame_path_would_fail_a_naive_exists_check(self):
        """Guards the reason this branch exists."""
        frame_path = os.path.join(self.seq_dir, BASENAME + '.####.ass')
        self.assertFalse(os.path.exists(frame_path))
        self.assertTrue(self.asset_paths._publish_present(
            _StubAsset('CFX', frame_path), frame_path))


if __name__ == '__main__':
    unittest.main()
