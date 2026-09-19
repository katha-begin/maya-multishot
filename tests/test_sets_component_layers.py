# -*- coding: utf-8 -*-
"""A set's own components must never be layered independently of the set.

An imported SETS asset references its pieces into namespaces NESTED under the
set's own namespace:

    SETS_ToriiLivingRoomInt_001                     <- the set, one CTX_Asset
    SETS_ToriiLivingRoomInt_001:TRLRWallA_0001      <- a piece of that set
    SETS_ToriiLivingRoomInt_001:TRLRFloor_0001

The reconciler adopted those pieces as CTX_Asset records of whichever shot
happened to be open -- in the scene this was found in, all 19 landed on
SH0030.  Every other shot therefore computed them as inactive and pinned each
piece's Geo_Grp to CTX_Inactive.  The set's top transform stayed in
CTX_Active, but a child carrying its own drawOverride connection no longer
inherits its parent's layer, so the whole set went invisible on every shot
except SH0030.

Only the top transform of a set belongs in a display layer; its pieces follow
it through the hierarchy.

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


SET_NS = 'SETS_ToriiLivingRoomInt_001'
PIECES = [SET_NS + ':TRLRWallA_0001',
          SET_NS + ':TRLRFloor_0001',
          SET_NS + ':TRLRSofa_0001']


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


class SetComponentTestCase(unittest.TestCase):

    def setUp(self):
        self.manager = display_layers.DisplayLayerManager.__new__(
            display_layers.DisplayLayerManager)
        self.connected = []

        test_case = self

        def resolve(manager, namespace, asset=None):
            return namespace + ':top'

        def connect(manager, top_node, layer):
            test_case.connected.append((top_node, layer))
            return True

        for name, func in (('_resolve_top_node', resolve),
                           ('_connect_node_to_layer', connect),
                           ('ensure_global_layers', lambda self: None)):
            patcher = patch.object(display_layers.DisplayLayerManager, name, func)
            patcher.start()
            self.addCleanup(patcher.stop)

    def hidden_nodes(self):
        return [node for node, layer in self.connected
                if layer == display_layers.DisplayLayerManager.INACTIVE_LAYER]

    def run_switch(self):
        """SH0440 active; SH0030 owns the set pieces as stray records."""
        active = FakeShot('SH0440', [SET_NS, 'CAM_SH0440_camera_001'])
        stray = FakeShot('SH0030', [SET_NS, 'CAM_SH0030_camera_001'] + PIECES)
        self.manager.switch_shot_layers(active, [active, stray])


class TestSetPiecesAreNeverHidden(SetComponentTestCase):

    def test_no_nested_set_component_is_moved_to_inactive(self):
        self.run_switch()

        hidden = self.hidden_nodes()
        for piece in PIECES:
            self.assertNotIn(
                piece + ':top', hidden,
                "%s is a piece of %s and must follow the set's top transform, "
                "not be pinned to CTX_Inactive" % (piece, SET_NS))


class TestSetItselfStaysActive(SetComponentTestCase):

    def test_set_top_transform_is_active(self):
        self.run_switch()

        self.assertIn(
            (SET_NS + ':top', display_layers.DisplayLayerManager.ACTIVE_LAYER),
            self.connected)


class TestOrdinaryAssetsStillHide(SetComponentTestCase):
    """Negative control: the fix must not stop hiding real per-shot assets."""

    def test_other_shots_camera_is_still_hidden(self):
        self.run_switch()

        self.assertIn('CAM_SH0030_camera_001:top', self.hidden_nodes())


if __name__ == '__main__':
    unittest.main()
