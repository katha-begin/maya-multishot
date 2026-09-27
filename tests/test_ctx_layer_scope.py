# -*- coding: utf-8 -*-
"""The tools must only ever touch CTX_Active and CTX_Inactive.

A lighting scene carries display layers the artist made -- MASTER_BG_A,
MASTER_CHAR_A, MASTER_ATMOS, layer1 -- and those are their work.  Nothing
here may show, hide or delete one of them.

get_all_ctx_layers() used to filter on a LAYER_PREFIX of "CTX_", from the
abandoned per-shot layer scheme.  That prefix is wrong twice over: the
attribute no longer exists, so every caller raises AttributeError; and were
it restored, it would also match a layer an artist happened to name CTX_*,
and cleanup_orphaned_layers() would then delete it -- along with CTX_Active
and CTX_Inactive themselves, which are never in its valid_layers set.

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
from core import shot_switching


ARTIST_LAYERS = ['MASTER_BG_A', 'MASTER_CHAR_A', 'MASTER_ATMOS',
                 'MASTER_FX_A', 'MASTER_VISOR_A', 'layer1',
                 'CTX_HandMadeByArtist', 'CTX_Ep20_sq0010_SH0010']


class MockCmds(object):
    def __init__(self, layers):
        self.layers = list(layers)
        self.visibility = {}

    def ls(self, *args, **kwargs):
        if kwargs.get('type') == 'displayLayer':
            return list(self.layers)
        return []

    def objExists(self, name):
        return name.split('.')[0] in self.layers

    def setAttr(self, plug, value, **kwargs):
        node, attr = plug.split('.', 1)
        if attr == 'visibility':
            self.visibility[node] = value

    def getAttr(self, plug):
        node, attr = plug.split('.', 1)
        return self.visibility.get(node)

    def delete(self, name):
        raise AssertionError(
            "delete(%r) -- nothing may delete a display layer" % name)


class CtxLayerScopeTestCase(unittest.TestCase):

    def setUp(self):
        self.cmds = MockCmds(['defaultLayer',
                              display_layers.DisplayLayerManager.ACTIVE_LAYER,
                              display_layers.DisplayLayerManager.INACTIVE_LAYER]
                             + ARTIST_LAYERS)
        patcher = patch.object(display_layers, 'cmds', self.cmds)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.manager = display_layers.DisplayLayerManager.__new__(
            display_layers.DisplayLayerManager)


class TestGetAllCtxLayers(CtxLayerScopeTestCase):

    def test_returns_only_the_two_global_layers(self):
        self.assertEqual(
            sorted(self.manager.get_all_ctx_layers()),
            sorted([display_layers.DisplayLayerManager.ACTIVE_LAYER,
                    display_layers.DisplayLayerManager.INACTIVE_LAYER]))

    def test_never_returns_an_artist_layer(self):
        returned = self.manager.get_all_ctx_layers()
        for layer in ARTIST_LAYERS:
            self.assertNotIn(
                layer, returned,
                "%s is the artist's layer and must never be touched" % layer)

    def test_omits_a_global_layer_that_does_not_exist(self):
        self.cmds.layers.remove(
            display_layers.DisplayLayerManager.INACTIVE_LAYER)
        self.assertEqual(
            self.manager.get_all_ctx_layers(),
            [display_layers.DisplayLayerManager.ACTIVE_LAYER])


class TestShowHideAllShots(CtxLayerScopeTestCase):
    """show_all_shots / hide_all_shots drive only the CTX layers."""

    def setUp(self):
        CtxLayerScopeTestCase.setUp(self)
        patcher = patch.object(shot_switching, 'cmds', self.cmds)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.switcher = shot_switching.ShotSwitcher.__new__(
            shot_switching.ShotSwitcher)
        self.switcher.layer_manager = self.manager

    def test_show_all_shots_leaves_artist_layers_alone(self):
        self.switcher.show_all_shots()

        for layer in ARTIST_LAYERS:
            self.assertNotIn(
                layer, self.cmds.visibility,
                "show_all_shots touched the artist's layer %s" % layer)

    def test_hide_all_shots_leaves_artist_layers_alone(self):
        self.switcher.hide_all_shots()

        for layer in ARTIST_LAYERS:
            self.assertNotIn(
                layer, self.cmds.visibility,
                "hide_all_shots touched the artist's layer %s" % layer)


if __name__ == '__main__':
    unittest.main()
