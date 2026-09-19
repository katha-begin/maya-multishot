# -*- coding: utf-8 -*-
"""Tests for core/asset_reconciler.py.

All tests run without Maya installed by patching the cmds import.
"""

from __future__ import absolute_import, division, print_function

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


# ---------------------------------------------------------------------------
# MockCmds -- shared mock for cmds used by both reconciler and node wrappers
# ---------------------------------------------------------------------------

class MockCmds:
    """Mock Maya cmds with enough fidelity for the reconciler + node creation."""

    def __init__(self):
        self.nodes = {}          # node_name -> {attr: value}
        self.connections = []    # list of (src_plug, dst_plug)
        self._counter = 0

    def objExists(self, name):
        node = name.split('.')[0]
        return node in self.nodes

    def createNode(self, node_type, name=None, **kwargs):
        if not name:
            self._counter += 1
            name = 'node{}'.format(self._counter)
        self.nodes[name] = {'_type': node_type}
        return name

    def rename(self, old_name, new_name):
        if old_name in self.nodes:
            self.nodes[new_name] = self.nodes.pop(old_name)
            updated = []
            for src, dst in self.connections:
                src = src.replace(old_name + '.', new_name + '.')
                dst = dst.replace(old_name + '.', new_name + '.')
                updated.append((src, dst))
            self.connections = updated
        return new_name

    def addAttr(self, node, **kwargs):
        attr_name = kwargs.get('longName') or kwargs.get('ln')
        if attr_name and node in self.nodes:
            if attr_name not in self.nodes[node]:
                default = kwargs.get('defaultValue')
                at = kwargs.get('attributeType') or kwargs.get('at', '')
                if at == 'message':
                    default = '__message__'
                elif at == 'bool':
                    default = kwargs.get('defaultValue', False)
                self.nodes[node][attr_name] = default

    def setAttr(self, attr, value=None, **kwargs):
        parts = attr.split('.', 1)
        if len(parts) == 2:
            node, a = parts
            if node in self.nodes:
                self.nodes[node][a] = value

    def getAttr(self, attr):
        parts = attr.split('.', 1)
        if len(parts) == 2:
            node, a = parts
            if node in self.nodes:
                return self.nodes[node].get(a)
        return None

    def attributeQuery(self, attr, node=None, exists=False, **kwargs):
        if exists and node in self.nodes:
            return attr in self.nodes[node]
        return False

    def connectAttr(self, src, dst, **kwargs):
        if kwargs.get('force'):
            self.connections = [
                (s, d) for s, d in self.connections if d != dst
            ]
        self.connections.append((src, dst))

    def listConnections(self, attr, **kwargs):
        source = kwargs.get('source', True)
        destination = kwargs.get('destination', True)
        plugs = kwargs.get('plugs', False)
        results = []

        if destination:
            for src, dst in self.connections:
                if src == attr or self._attr_match(src, attr):
                    entry = dst if plugs else dst.split('.')[0]
                    if entry not in results:
                        results.append(entry)

        if source:
            for src, dst in self.connections:
                if dst == attr or self._attr_match(dst, attr):
                    entry = src if plugs else src.split('.')[0]
                    if entry not in results:
                        results.append(entry)

        return results or None

    def _attr_match(self, plug, query):
        """Match 'shot.assets[0]' against query 'shot.assets'."""
        if '[' in plug:
            base = plug.split('[')[0]
            return base == query
        return False

    def ls(self, **kwargs):
        node_type = kwargs.get('type')
        if node_type:
            return [n for n, d in self.nodes.items()
                    if d.get('_type') == node_type]
        return list(self.nodes.keys())

    def delete(self, *nodes):
        for node in nodes:
            self.nodes.pop(node, None)
            self.connections = [(s, d) for s, d in self.connections
                                if s.split('.')[0] != node and d.split('.')[0] != node]

    def referenceQuery(self, ref_node, **kwargs):
        if kwargs.get('namespace'):
            return self.nodes.get(ref_node, {}).get('_ref_ns', '')
        if kwargs.get('filename'):
            return self.nodes.get(ref_node, {}).get('_ref_file', '')
        return ''


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_reference(mock, name, namespace, filepath='/some/path.abc'):
    """Create a mock reference node."""
    mock.createNode('reference', name=name)
    mock.nodes[name]['_ref_ns'] = ':' + namespace
    mock.nodes[name]['_ref_file'] = filepath


def _make_shot(mock, name, shot_code):
    """Create a mock CTX_Shot node."""
    mock.createNode('network', name=name)
    mock.addAttr(name, longName='ctx_type')
    mock.setAttr('{}.ctx_type'.format(name), 'CTX_Shot')
    mock.addAttr(name, longName='shot')
    mock.setAttr('{}.shot'.format(name), shot_code)
    mock.addAttr(name, longName='assets', attributeType='message')


class AnyPublishes(dict):
    """Stands in for a shot that published every asset in the scene."""

    def get(self, key, default=None):
        return {'dept': 'anim', 'version': 'v001', 'file_path': '',
                'info': {'ext': 'abc'}}


def _make_ctx_asset(mock, name, namespace, shot_code=None):
    """Create a mock CTX_Asset node with standard attrs."""
    mock.createNode('network', name=name)
    mock.addAttr(name, longName='ctx_type')
    mock.setAttr('{}.ctx_type'.format(name), 'CTX_Asset')
    mock.addAttr(name, longName='namespace')
    mock.setAttr('{}.namespace'.format(name), namespace)
    mock.addAttr(name, longName='asset_type')
    mock.addAttr(name, longName='asset_name')
    mock.addAttr(name, longName='variant')
    mock.addAttr(name, longName='message', attributeType='message')
    mock.addAttr(name, longName='targetNode', attributeType='message')


# ---------------------------------------------------------------------------
# _parse_namespace tests
# ---------------------------------------------------------------------------

class TestParseNamespace(unittest.TestCase):

    def test_standard_namespace(self):
        from core.asset_reconciler import _parse_namespace
        self.assertEqual(_parse_namespace('CHAR_BuffA_001'),
                         ('CHAR', 'BuffA', '001'))

    def test_multi_part_name(self):
        from core.asset_reconciler import _parse_namespace
        self.assertEqual(_parse_namespace('PROP_Stuffy_Woo_Toy_002'),
                         ('PROP', 'Stuffy_Woo_Toy', '002'))

    def test_too_few_parts(self):
        from core.asset_reconciler import _parse_namespace
        self.assertIsNone(_parse_namespace('CHAR'))
        self.assertIsNone(_parse_namespace('CHAR_BuffA'))

    def test_empty_or_none(self):
        from core.asset_reconciler import _parse_namespace
        self.assertIsNone(_parse_namespace(''))
        self.assertIsNone(_parse_namespace(None))


# ---------------------------------------------------------------------------
# reconcile_assets_for_shot tests
# ---------------------------------------------------------------------------

class TestReconcileAssets(unittest.TestCase):

    def setUp(self):
        self.mock = MockCmds()

        import core.asset_reconciler as recon_mod
        import core.nodes.wrappers.asset as asset_mod
        import core.nodes.base as base_mod

        self.recon_mod = recon_mod
        self.asset_mod = asset_mod
        self.base_mod = base_mod

        # Save originals
        self._orig_recon_cmds = recon_mod.cmds
        self._orig_recon_avail = recon_mod.MAYA_AVAILABLE
        self._orig_asset_cmds = asset_mod.cmds
        self._orig_base_cmds = base_mod.cmds

        # Inject mock
        recon_mod.cmds = self.mock
        recon_mod.MAYA_AVAILABLE = True
        asset_mod.cmds = self.mock
        base_mod.cmds = self.mock

        # Create shot node
        _make_shot(self.mock, 'CTX_Shot_Ep10_sq0030_SH0140', 'SH0140')
        self.shot_name = 'CTX_Shot_Ep10_sq0030_SH0140'

        # These tests cover wiring, so treat every reference as published
        patcher = patch.object(recon_mod, '_shot_publishes',
                               lambda config, node_name: AnyPublishes())
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.recon_mod.cmds = self._orig_recon_cmds
        self.recon_mod.MAYA_AVAILABLE = self._orig_recon_avail
        self.asset_mod.cmds = self._orig_asset_cmds
        self.base_mod.cmds = self._orig_base_cmds

    def test_creates_missing_ctx_asset(self):
        """Creates a CTX_Asset node for an unlinked reference."""
        _make_reference(self.mock, 'CHAR_BuffA_001RN', 'CHAR_BuffA_001')

        stats = self.recon_mod.reconcile_assets_for_shot(self.shot_name)

        self.assertEqual(stats['created'], 1)
        self.assertEqual(stats['skipped'], 0)
        self.assertEqual(len(stats['created_nodes']), 1)

        created_nodes = [n for n in self.mock.nodes
                         if n.startswith('CTX_Asset_') and 'BuffA' in n]
        self.assertEqual(len(created_nodes), 1)
        self.assertIn(created_nodes[0], stats['created_nodes'])
        self.assertEqual(
            self.mock.getAttr('{}.namespace'.format(created_nodes[0])),
            'CHAR_BuffA_001'
        )

    def test_creates_ctx_asset_with_correct_attributes(self):
        """Created CTX_Asset has correct asset_type, asset_name, variant."""
        _make_reference(self.mock, 'PROP_ToyA_003RN', 'PROP_ToyA_003')

        self.recon_mod.reconcile_assets_for_shot(self.shot_name)

        created = [n for n in self.mock.nodes
                   if n.startswith('CTX_Asset_') and 'ToyA' in n]
        self.assertEqual(len(created), 1)
        node = created[0]
        self.assertEqual(self.mock.getAttr('{}.asset_type'.format(node)), 'PROP')
        self.assertEqual(self.mock.getAttr('{}.asset_name'.format(node)), 'ToyA')
        self.assertEqual(self.mock.getAttr('{}.variant'.format(node)), '003')

    def test_wires_ctx_asset_to_shot(self):
        """Created CTX_Asset is wired to the shot's assets array."""
        _make_reference(self.mock, 'CHAR_BuffA_001RN', 'CHAR_BuffA_001')

        self.recon_mod.reconcile_assets_for_shot(self.shot_name)

        created = [n for n in self.mock.nodes
                   if n.startswith('CTX_Asset_') and 'BuffA' in n][0]

        wired = any(
            src == '{}.message'.format(created) and
            dst.startswith('{}.assets'.format(self.shot_name))
            for src, dst in self.mock.connections
        )
        self.assertTrue(wired, "CTX_Asset should be connected to shot.assets")

    def test_links_reference_to_ctx_target_node(self):
        """Created CTX_Asset has reference linked to targetNode."""
        _make_reference(self.mock, 'CHAR_BuffA_001RN', 'CHAR_BuffA_001')

        self.recon_mod.reconcile_assets_for_shot(self.shot_name)

        created = [n for n in self.mock.nodes
                   if n.startswith('CTX_Asset_') and 'BuffA' in n][0]

        linked = any(
            src == 'CHAR_BuffA_001RN.message' and
            dst == '{}.targetNode'.format(created)
            for src, dst in self.mock.connections
        )
        self.assertTrue(linked, "Reference should be linked to CTX_Asset.targetNode")

    def test_skips_already_linked_asset(self):
        """Skips assets that already have a CTX_Asset wired to the shot."""
        _make_reference(self.mock, 'CHAR_BuffA_001RN', 'CHAR_BuffA_001')
        _make_ctx_asset(self.mock, 'CTX_Asset_CHAR_BuffA_SH0140',
                        'CHAR_BuffA_001')

        # Wire to shot
        self.mock.connectAttr(
            'CTX_Asset_CHAR_BuffA_SH0140.message',
            '{}.assets[0]'.format(self.shot_name)
        )
        # Link reference
        self.mock.connectAttr(
            'CHAR_BuffA_001RN.message',
            'CTX_Asset_CHAR_BuffA_SH0140.targetNode', force=True
        )

        stats = self.recon_mod.reconcile_assets_for_shot(self.shot_name)

        self.assertEqual(stats['created'], 0)
        self.assertEqual(stats['skipped'], 1)

    def test_links_existing_ctx_asset_not_wired_to_shot(self):
        """If CTX_Asset exists but is not wired to shot, reconcile wires it."""
        _make_reference(self.mock, 'CHAR_DeerA_001RN', 'CHAR_DeerA_001')
        _make_ctx_asset(self.mock, 'CTX_Asset_CHAR_DeerA_SH0140',
                        'CHAR_DeerA_001')

        stats = self.recon_mod.reconcile_assets_for_shot(self.shot_name)

        self.assertEqual(stats['created'], 0)
        self.assertGreaterEqual(stats['linked'], 1)
        self.assertIn('CTX_Asset_CHAR_DeerA_SH0140', stats['linked_nodes'])

        wired = any(
            src == 'CTX_Asset_CHAR_DeerA_SH0140.message' and
            dst.startswith('{}.assets'.format(self.shot_name))
            for src, dst in self.mock.connections
        )
        self.assertTrue(wired)

    def test_skips_non_asset_namespaces(self):
        """References with < 3 namespace parts (e.g. shader refs) are skipped."""
        _make_reference(self.mock, 'SDRS_FloorRN', 'SDRS_Floor')

        stats = self.recon_mod.reconcile_assets_for_shot(self.shot_name)

        self.assertEqual(stats['created'], 0)
        self.assertEqual(stats['linked'], 0)

    def test_skips_default_reference_nodes(self):
        """sharedReferenceNode and _UNKNOWN_REF_NODE_ are skipped."""
        self.mock.createNode('reference', name='sharedReferenceNode')
        self.mock.createNode('reference', name='_UNKNOWN_REF_NODE_')

        stats = self.recon_mod.reconcile_assets_for_shot(self.shot_name)
        self.assertEqual(stats['created'], 0)

    def test_handles_multiple_references(self):
        """Reconcile handles multiple unlinked references in one pass."""
        _make_reference(self.mock, 'CHAR_BuffA_001RN', 'CHAR_BuffA_001')
        _make_reference(self.mock, 'CHAR_DeerA_001RN', 'CHAR_DeerA_001')
        _make_reference(self.mock, 'PROP_ToyA_001RN', 'PROP_ToyA_001')

        stats = self.recon_mod.reconcile_assets_for_shot(self.shot_name)
        self.assertEqual(stats['created'], 3)

    def test_nonexistent_shot_returns_zeros(self):
        """Returns zeros for a non-existent shot node."""
        stats = self.recon_mod.reconcile_assets_for_shot('CTX_Shot_DOES_NOT_EXIST')
        self.assertEqual(stats['created'], 0)
        self.assertEqual(stats['linked'], 0)
        self.assertEqual(stats['skipped'], 0)

    def test_accepts_wrapper_object(self):
        """Accepts a wrapper-like object with .node_name."""
        _make_reference(self.mock, 'CHAR_BuffA_001RN', 'CHAR_BuffA_001')

        class FakeWrapper:
            node_name = 'CTX_Shot_Ep10_sq0030_SH0140'

        stats = self.recon_mod.reconcile_assets_for_shot(FakeWrapper())
        self.assertEqual(stats['created'], 1)

    def test_maya_not_available(self):
        """Returns zeros when Maya is not available."""
        self.recon_mod.MAYA_AVAILABLE = False
        stats = self.recon_mod.reconcile_assets_for_shot(self.shot_name)
        self.assertEqual(stats['created'], 0)
        self.assertEqual(stats['linked'], 0)
        self.assertEqual(stats['skipped'], 0)

    def test_multi_part_asset_name(self):
        """Handles references with multi-part asset names correctly."""
        _make_reference(self.mock, 'PROP_StuffyWooWooToyA_002RN',
                        'PROP_StuffyWooWooToyA_002')

        stats = self.recon_mod.reconcile_assets_for_shot(self.shot_name)
        self.assertEqual(stats['created'], 1)

        created = [n for n in self.mock.nodes
                   if n.startswith('CTX_Asset_') and 'StuffyWooWooToyA' in n]
        self.assertEqual(len(created), 1)
        self.assertEqual(
            self.mock.getAttr('{}.asset_name'.format(created[0])),
            'StuffyWooWooToyA'
        )


# ---------------------------------------------------------------------------
# _check_asset_in_scene tests
# ---------------------------------------------------------------------------

class TestCheckAssetInScene(unittest.TestCase):
    """Test the updated _check_asset_in_scene returns 'managed'/'unlinked'/'missing'."""

    def setUp(self):
        self.mock = MockCmds()

    def _call(self, asset_data):
        """Call _check_asset_in_scene with mocked cmds."""
        # Patch maya.cmds import inside the method
        mock_maya = MagicMock()
        mock_maya.cmds = self.mock
        with patch.dict('sys.modules', {'maya': mock_maya, 'maya.cmds': self.mock}):
            from ui.asset_manager_dialog import AssetManagerDialog
            return AssetManagerDialog._check_asset_in_scene(None, asset_data)

    def test_returns_managed_when_ctx_and_target_linked(self):
        _make_ctx_asset(self.mock, 'CTX_Asset_CHAR_A_SH01', 'CHAR_A_001')
        _make_reference(self.mock, 'CHAR_A_001RN', 'CHAR_A_001')
        self.mock.connectAttr('CHAR_A_001RN.message',
                              'CTX_Asset_CHAR_A_SH01.targetNode', force=True)

        asset_data = {'ctx_node': 'CTX_Asset_CHAR_A_SH01', 'maya_node': None}
        result = self._call(asset_data)
        self.assertEqual(result, 'managed')
        self.assertEqual(asset_data['maya_node'], 'CHAR_A_001RN')

    def test_returns_unlinked_when_maya_node_exists_no_ctx(self):
        _make_reference(self.mock, 'CHAR_A_001RN', 'CHAR_A_001')

        asset_data = {'ctx_node': None, 'maya_node': 'CHAR_A_001RN'}
        result = self._call(asset_data)
        self.assertEqual(result, 'unlinked')

    def test_returns_missing_when_nothing(self):
        asset_data = {'ctx_node': None, 'maya_node': None}
        result = self._call(asset_data)
        self.assertEqual(result, 'missing')

    def test_returns_unlinked_when_ctx_exists_but_no_target_link(self):
        """ctx_node exists but has no targetNode connection -> falls back to maya_node."""
        _make_ctx_asset(self.mock, 'CTX_Asset_CHAR_A_SH01', 'CHAR_A_001')
        _make_reference(self.mock, 'CHAR_A_001RN', 'CHAR_A_001')
        # No targetNode connection made

        asset_data = {
            'ctx_node': 'CTX_Asset_CHAR_A_SH01',
            'maya_node': 'CHAR_A_001RN'
        }
        result = self._call(asset_data)
        self.assertEqual(result, 'unlinked')



# ---------------------------------------------------------------------------
# reconciled record fields -- what resolve_asset_path needs
# ---------------------------------------------------------------------------

ASSET_PATH_TEMPLATE = ('$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish/$ver/'
                       '$ep_$seq_$shot__$assetType_$assetName_$variant.$ext')
CAMERA_PATH_TEMPLATE = ('$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish/$ver/'
                        '$ep_$seq_$shot__$assetName.$ext')


class FakeConfig(object):
    """Minimal ProjectConfig stand-in -- the templates the reconciler reads."""

    TEMPLATES = {
        'assetPath': ASSET_PATH_TEMPLATE,
        'namespace': '$assetType_$assetName_$variant',
        'namespaceShader': '$assetType_$assetName_$variant_Shade',
        'namespaceGroom': '$assetType_$assetName_$variant_Groom',
    }

    def get_template(self, name):
        return self.TEMPLATES.get(name)


def _publish(dept, version, asset_part, ext='abc'):
    """One entry of what core/asset_scanner discovers for a shot."""
    path = ('V:/SWA/all/scene/Ep10/sq0030/SH0140/{dept}/publish/{version}/'
            'Ep10_sq0030_SH0140__{asset_part}.{ext}'.format(
                dept=dept, version=version, asset_part=asset_part, ext=ext))
    return {'dept': dept, 'version': version, 'file_path': path,
            'info': {'ext': ext}}


class TestReconciledRecordFields(unittest.TestCase):
    """A record must describe a publish the shot actually has.

    resolve_asset_path builds every path from the record's template, dept and
    version, so a record for an asset the shot never published resolves to a
    file that does not exist ("does not exist", "Unexpanded tokens: dept, ver").
    """

    def setUp(self):
        self.mock = MockCmds()

        import core.asset_reconciler as recon_mod
        import core.nodes.wrappers.asset as asset_mod
        import core.nodes.base as base_mod

        self.recon_mod = recon_mod
        self.asset_mod = asset_mod
        self.base_mod = base_mod

        self._orig_recon_cmds = recon_mod.cmds
        self._orig_recon_avail = recon_mod.MAYA_AVAILABLE
        self._orig_asset_cmds = asset_mod.cmds
        self._orig_base_cmds = base_mod.cmds

        recon_mod.cmds = self.mock
        recon_mod.MAYA_AVAILABLE = True
        asset_mod.cmds = self.mock
        base_mod.cmds = self.mock

        _make_shot(self.mock, 'CTX_Shot_Ep10_sq0030_SH0140', 'SH0140')
        self.shot_name = 'CTX_Shot_Ep10_sq0030_SH0140'
        self.config = FakeConfig()

        # What the shot published, as core/asset_scanner discovers it
        self.publishes = {
            ('CHAR', 'BuffA', '001'): _publish('anim', 'v005', 'CHAR_BuffA_001'),
            ('CAM', 'SWA_Ep10_SH0140_camera', '001'): _publish(
                'anim', 'v002', 'SWA_Ep10_SH0140_camera'),
            ('CFX', 'botgroomSamS', '001'): _publish(
                'cfx', 'v003', 'CFX_botgroomSamS001', ext='ass'),
        }
        patcher = patch.object(recon_mod, '_shot_publishes',
                               lambda config, node_name: self.publishes)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.recon_mod.cmds = self._orig_recon_cmds
        self.recon_mod.MAYA_AVAILABLE = self._orig_recon_avail
        self.asset_mod.cmds = self._orig_asset_cmds
        self.base_mod.cmds = self._orig_base_cmds

    def _created_node(self, fragment):
        nodes = [n for n in self.mock.nodes
                 if n.startswith('CTX_Asset_') and fragment in n]
        self.assertEqual(len(nodes), 1, "expected one record for {}".format(fragment))
        return nodes[0]

    def test_created_record_carries_template_and_publish_fields(self):
        _make_reference(self.mock, 'CHAR_BuffA_001RN', 'CHAR_BuffA_001')

        self.recon_mod.reconcile_assets_for_shot(self.shot_name, config=self.config)

        node = self._created_node('BuffA')
        self.assertEqual(self.mock.getAttr('{}.template'.format(node)),
                         ASSET_PATH_TEMPLATE)
        self.assertEqual(self.mock.getAttr('{}.department'.format(node)), 'anim')
        self.assertEqual(self.mock.getAttr('{}.version'.format(node)), 'v005')
        self.assertEqual(self.mock.getAttr('{}.extension'.format(node)), 'abc')

    def test_camera_record_uses_the_camera_template(self):
        # A camera publish carries no type or variant in its filename
        _make_reference(self.mock, 'CAM_SWA_Ep10_SH0140_camera_001RN',
                        'CAM_SWA_Ep10_SH0140_camera_001')

        self.recon_mod.reconcile_assets_for_shot(self.shot_name, config=self.config)

        node = self._created_node('camera')
        self.assertEqual(self.mock.getAttr('{}.template'.format(node)),
                         CAMERA_PATH_TEMPLATE)
        self.assertEqual(self.mock.getAttr('{}.version'.format(node)), 'v002')

    def test_existing_record_without_template_is_repaired(self):
        node = 'CTX_Asset_CHAR_BuffA_SH0140'
        _make_ctx_asset(self.mock, node, 'CHAR_BuffA_001')
        self.mock.addAttr(node, longName='template')
        _make_reference(self.mock, 'CHAR_BuffA_001RN', 'CHAR_BuffA_001')

        self.recon_mod.reconcile_assets_for_shot(self.shot_name, config=self.config)

        self.assertEqual(self.mock.getAttr('{}.template'.format(node)),
                         ASSET_PATH_TEMPLATE)
        self.assertEqual(self.mock.getAttr('{}.department'.format(node)), 'anim')
        self.assertEqual(self.mock.getAttr('{}.version'.format(node)), 'v005')

    def test_basename_namespace_parses_as_its_asset(self):
        # A CFX namespace is the whole publish name; the asset half follows '__'
        _make_reference(self.mock, 'groomRN',
                        'Ep10_sq0030_SH0140__CFX_botgroomSamS001')

        self.recon_mod.reconcile_assets_for_shot(self.shot_name, config=self.config)

        node = self._created_node('botgroom')
        self.assertEqual(self.mock.getAttr('{}.asset_type'.format(node)), 'CFX')
        self.assertEqual(self.mock.getAttr('{}.asset_name'.format(node)), 'botgroomSamS')
        self.assertEqual(self.mock.getAttr('{}.variant'.format(node)), '001')
        self.assertEqual(self.mock.getAttr('{}.department'.format(node)), 'cfx')

    def test_asset_the_shot_never_published_gets_no_record(self):
        # Another shot's character, loaded in the scene; SH0140 has no publish
        _make_reference(self.mock, 'CHAR_Kit_001RN', 'CHAR_Kit_001')

        stats = self.recon_mod.reconcile_assets_for_shot(self.shot_name,
                                                         config=self.config)

        self.assertEqual(stats['created'], 0)
        self.assertEqual([n for n in self.mock.nodes if n.startswith('CTX_Asset_')], [])

    def test_shader_reference_is_not_an_asset(self):
        # namespaceShader is $assetType_$assetName_$variant_Shade
        _make_reference(self.mock, 'CHAR_BuffA_001_ShadeRN', 'CHAR_BuffA_001_Shade')

        stats = self.recon_mod.reconcile_assets_for_shot(self.shot_name,
                                                         config=self.config)

        self.assertEqual(stats['created'], 0)
        self.assertEqual([n for n in self.mock.nodes if n.startswith('CTX_Asset_')], [])

    def test_set_piece_reference_of_a_set_asset_gets_no_record(self):
        # References nested in a set assembly are not shot publishes
        _make_reference(self.mock, 'SETS_Living_001:TRLRFloor_0001RN',
                        'SETS_Living_001:TRLRFloor_0001')

        stats = self.recon_mod.reconcile_assets_for_shot(self.shot_name,
                                                         config=self.config)

        self.assertEqual(stats['created'], 0)


# ---------------------------------------------------------------------------
# stale records left by the old reconciler
# ---------------------------------------------------------------------------

class TestStaleRecords(unittest.TestCase):
    """Scenes built before the publish check carry records for assets the shot
    never published: shader namespaces, references nested in a set, and other
    shots' assets.  They resolve no path on every shot switch."""

    def setUp(self):
        self.mock = MockCmds()

        import core.asset_reconciler as recon_mod
        import core.nodes.wrappers.asset as asset_mod
        import core.nodes.base as base_mod

        self.recon_mod = recon_mod
        self._orig_cmds = recon_mod.cmds
        self._orig_avail = recon_mod.MAYA_AVAILABLE
        self._orig_asset_cmds = asset_mod.cmds
        self._orig_base_cmds = base_mod.cmds
        self.asset_mod = asset_mod
        self.base_mod = base_mod

        recon_mod.cmds = self.mock
        recon_mod.MAYA_AVAILABLE = True
        asset_mod.cmds = self.mock
        base_mod.cmds = self.mock

        _make_shot(self.mock, 'CTX_Shot_Ep10_sq0030_SH0140', 'SH0140')
        self.shot_name = 'CTX_Shot_Ep10_sq0030_SH0140'
        self.config = FakeConfig()

        self.publishes = {
            ('CHAR', 'BuffA', '001'): _publish('anim', 'v005', 'CHAR_BuffA_001'),
        }
        patcher = patch.object(recon_mod, '_shot_publishes',
                               lambda config, node_name: self.publishes)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.recon_mod.cmds = self._orig_cmds
        self.recon_mod.MAYA_AVAILABLE = self._orig_avail
        self.asset_mod.cmds = self._orig_asset_cmds
        self.base_mod.cmds = self._orig_base_cmds

    def _wire(self, node, namespace):
        _make_ctx_asset(self.mock, node, namespace)
        self.mock.connectAttr('{}.message'.format(node),
                              '{}.assets'.format(self.shot_name), nextAvailable=True)

    def _stale_nodes(self):
        return [record['node'] for record
                in self.recon_mod.find_stale_records(self.shot_name, config=self.config)]

    def test_record_of_a_published_asset_is_kept(self):
        self._wire('CTX_Asset_CHAR_BuffA_SH0140', 'CHAR_BuffA_001')
        self.assertEqual(self._stale_nodes(), [])

    def test_shader_record_is_stale(self):
        self._wire('CTX_Asset_CHAR_BuffA_Shade_SH0140', 'CHAR_BuffA_001_Shade')
        self.assertEqual(self._stale_nodes(), ['CTX_Asset_CHAR_BuffA_Shade_SH0140'])

    def test_set_piece_record_is_stale(self):
        self._wire('TRLRFloor_SH0140', 'SETS_Living_001:TRLRFloor_0001')
        self.assertEqual(self._stale_nodes(), ['TRLRFloor_SH0140'])

    def test_record_of_another_shots_asset_is_stale(self):
        self._wire('CTX_Asset_CHAR_Kit_SH0140', 'CHAR_Kit_001')
        self.assertEqual(self._stale_nodes(), ['CTX_Asset_CHAR_Kit_SH0140'])

    def test_every_stale_record_carries_a_reason(self):
        self._wire('CTX_Asset_CHAR_Kit_SH0140', 'CHAR_Kit_001')
        records = self.recon_mod.find_stale_records(self.shot_name, config=self.config)
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0]['reason'])
        self.assertEqual(records[0]['namespace'], 'CHAR_Kit_001')

    def test_nothing_is_reported_without_publishes(self):
        # A scan that found nothing must not condemn every record
        self.publishes = {}
        self._wire('CTX_Asset_CHAR_BuffA_SH0140', 'CHAR_BuffA_001')
        self.assertEqual(self._stale_nodes(), [])

    def test_remove_records_deletes_the_nodes(self):
        self._wire('CTX_Asset_CHAR_Kit_SH0140', 'CHAR_Kit_001')
        removed = self.recon_mod.remove_records(['CTX_Asset_CHAR_Kit_SH0140'])
        self.assertEqual(removed, 1)
        self.assertNotIn('CTX_Asset_CHAR_Kit_SH0140', self.mock.nodes)


class TestRepairSceneRecords(unittest.TestCase):
    """Repairing a scene built by the old setup: add what a shot's publishes
    need, report what describes no publish."""

    def setUp(self):
        self.mock = MockCmds()

        import core.asset_reconciler as recon_mod
        import core.nodes.wrappers.asset as asset_mod
        import core.nodes.base as base_mod

        self.recon_mod = recon_mod
        self._orig_cmds = recon_mod.cmds
        self._orig_avail = recon_mod.MAYA_AVAILABLE
        self._orig_asset_cmds = asset_mod.cmds
        self._orig_base_cmds = base_mod.cmds
        self.asset_mod = asset_mod
        self.base_mod = base_mod

        recon_mod.cmds = self.mock
        recon_mod.MAYA_AVAILABLE = True
        asset_mod.cmds = self.mock
        base_mod.cmds = self.mock

        _make_shot(self.mock, 'CTX_Shot_Ep10_sq0030_SH0140', 'SH0140')
        self.shot_name = 'CTX_Shot_Ep10_sq0030_SH0140'
        self.config = FakeConfig()

        self.publishes = {
            ('CHAR', 'BuffA', '001'): _publish('anim', 'v005', 'CHAR_BuffA_001'),
        }
        patcher = patch.object(recon_mod, '_shot_publishes',
                               lambda config, node_name: self.publishes)
        patcher.start()
        self.addCleanup(patcher.stop)

        # A reference the shot published but has no record for, and a record
        # for an asset it never published
        _make_reference(self.mock, 'CHAR_BuffA_001RN', 'CHAR_BuffA_001')
        _make_ctx_asset(self.mock, 'CTX_Asset_CHAR_Kit_SH0140', 'CHAR_Kit_001')
        self.mock.connectAttr('CTX_Asset_CHAR_Kit_SH0140.message',
                              '{}.assets'.format(self.shot_name), nextAvailable=True)

    def tearDown(self):
        self.recon_mod.cmds = self._orig_cmds
        self.recon_mod.MAYA_AVAILABLE = self._orig_avail
        self.asset_mod.cmds = self._orig_asset_cmds
        self.base_mod.cmds = self._orig_base_cmds

    def test_creates_missing_records_and_reports_stale_ones(self):
        report = self.recon_mod.repair_scene_records(config=self.config)

        self.assertEqual(report['shots'], 1)
        self.assertEqual(report['created'], 1)
        self.assertEqual([entry['node'] for entry in report['stale']],
                         ['CTX_Asset_CHAR_Kit_SH0140'])
        self.assertEqual(report['removed'], 0)
        # Reporting alone must not delete anything
        self.assertIn('CTX_Asset_CHAR_Kit_SH0140', self.mock.nodes)

    def test_remove_stale_deletes_the_reported_records(self):
        report = self.recon_mod.repair_scene_records(config=self.config,
                                                     remove_stale=True)

        self.assertEqual(report['removed'], 1)
        self.assertNotIn('CTX_Asset_CHAR_Kit_SH0140', self.mock.nodes)


if __name__ == '__main__':
    unittest.main()
