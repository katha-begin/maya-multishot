# -*- coding: utf-8 -*-
"""Tests for DisplayLayerManager.switch_shot_layers.

The active shot's own camera was ending up in CTX_Inactive: one CTX_Asset
record per shot names the Maya reference, and records the reconciler adopted
into the wrong shot made the layer switch hide a node the active shot uses.

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


class FakeAsset(object):
    def __init__(self, namespace):
        self.node_name = 'CTX_Asset_' + namespace
        self._namespace = namespace

    def get_namespace(self):
        return self._namespace


class FakeShot(object):
    def __init__(self, shot_code, namespaces):
        self.node_name = 'CTX_Shot_' + shot_code
        self._shot_code = shot_code
        self._assets = [FakeAsset(ns) for ns in namespaces]

    def get_shot_code(self):
        return self._shot_code

    def get_assets(self):
        return self._assets


class SwitchLayersTestCase(unittest.TestCase):
    """Records every namespace -> layer decision the switch makes."""

    def setUp(self):
        self.manager = display_layers.DisplayLayerManager.__new__(
            display_layers.DisplayLayerManager)
        self.connected = []   # (top_node, layer)

        # One Maya node per namespace unless a test says otherwise
        self.nodes = {}

        test_case = self

        def resolve(manager, namespace, asset=None):
            return test_case.nodes.get(namespace, namespace + ':top')

        def connect(manager, top_node, layer):
            test_case.connected.append((top_node, layer))
            return True

        for name, func in (('_resolve_top_node', resolve),
                           ('_connect_node_to_layer', connect),
                           ('ensure_global_layers', lambda self: None)):
            patcher = patch.object(display_layers.DisplayLayerManager, name, func)
            patcher.start()
            self.addCleanup(patcher.stop)

    def layer_of(self, top_node):
        """The last layer a node was connected to, or None."""
        for node, layer in reversed(self.connected):
            if node == top_node:
                return layer
        return None


class TestSharedReferenceStaysVisible(SwitchLayersTestCase):
    """One camera reference serves every shot, repathed on Set Shot.

    Each shot holds its own CTX_Asset record for it and they all link to that
    one reference, so an inactive shot's record resolves -- through the
    targetNode fallback -- to the node the active shot is using.
    """

    def _camera_shots(self):
        shots = []
        for code in ('SH0060', 'SH0080', 'SH0130'):
            namespace = 'CAM_SWA_Ep20_{}_camera_001'.format(code)
            # Every record resolves to the one reference in the scene
            self.nodes[namespace] = 'CAM_SWA_Ep20_SH0080_camera_001:cam'
            shots.append(FakeShot(code, ['CHAR_Ajay_001', namespace]))
        return shots

    def test_shared_camera_is_not_hidden_by_other_shots(self):
        shots = self._camera_shots()
        active = [s for s in shots if s.get_shot_code() == 'SH0080'][0]

        self.manager.switch_shot_layers(active, shots)

        self.assertEqual(self.layer_of('CAM_SWA_Ep20_SH0080_camera_001:cam'),
                         display_layers.DisplayLayerManager.ACTIVE_LAYER)

    def test_shared_camera_is_never_connected_to_the_inactive_layer(self):
        shots = self._camera_shots()
        active = [s for s in shots if s.get_shot_code() == 'SH0080'][0]

        self.manager.switch_shot_layers(active, shots)

        hidden = [node for node, layer in self.connected
                  if layer == display_layers.DisplayLayerManager.INACTIVE_LAYER]
        self.assertNotIn('CAM_SWA_Ep20_SH0080_camera_001:cam', hidden)

    def test_node_shared_with_an_inactive_namespace_is_not_hidden(self):
        # A shader reference resolves to the same top node as its asset
        self.nodes['CHAR_Ajay_001'] = 'ajay:top'
        self.nodes['CHAR_Ajay_001_Shade'] = 'ajay:top'
        active = FakeShot('SH0080', ['CHAR_Ajay_001'])
        other = FakeShot('SH0030', ['CHAR_Ajay_001_Shade'])

        self.manager.switch_shot_layers(active, [active, other])

        self.assertEqual(self.layer_of('ajay:top'),
                         display_layers.DisplayLayerManager.ACTIVE_LAYER)


class TestOtherShotAssetsAreHidden(SwitchLayersTestCase):

    def test_asset_of_another_shot_only_is_hidden(self):
        active = FakeShot('SH0080', ['CHAR_Ajay_001'])
        other = FakeShot('SH0030', ['PROP_ToyA_002'])

        self.manager.switch_shot_layers(active, [active, other])

        self.assertEqual(self.layer_of('PROP_ToyA_002:top'),
                         display_layers.DisplayLayerManager.INACTIVE_LAYER)
        self.assertEqual(self.layer_of('CHAR_Ajay_001:top'),
                         display_layers.DisplayLayerManager.ACTIVE_LAYER)


if __name__ == '__main__':
    unittest.main()
