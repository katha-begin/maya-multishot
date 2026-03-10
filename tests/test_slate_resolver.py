"""Tests for SlateResolver.

All tests run without Maya using manual mock injection at the module level,
matching the pattern used in test_slate_nodes.py.
"""

import sys
import os
import unittest

# Ensure project root is on the path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_cmds():
    """Return a MagicMock that behaves like a minimal maya.cmds."""
    mock = MagicMock()
    mock.objExists.return_value = True
    return mock


def _make_slate(node_name, layers=None, enabled=True, parent=None):
    """Construct a mock CTXSlateNode-like object for testing.

    Args:
        node_name (str): Node name.
        layers (list|None): List of mock layer objects.
        enabled (bool): Value returned by is_enabled().
        parent: Another mock slate or None for get_parent_slate().

    Returns:
        MagicMock with the slate API.
    """
    slate = MagicMock()
    slate.node_name = node_name
    slate.is_enabled.return_value = enabled
    slate.get_layers.return_value = layers or []
    slate.get_parent_slate.return_value = parent

    # Build a name-to-layer map for get_layer_by_name
    layer_map = {layer.get_layer_name(): layer for layer in (layers or [])}

    def _get_layer_by_name(layer_name):
        return layer_map.get(layer_name, None)

    slate.get_layer_by_name.side_effect = _get_layer_by_name
    return slate


def _make_layer(layer_name, renderable=True, override_enabled=True):
    """Construct a mock CTXSlateLayerNode-like object for testing."""
    layer = MagicMock()
    layer.get_layer_name.return_value = layer_name
    layer.get_renderable.return_value = renderable
    layer.is_override_enabled.return_value = override_enabled
    return layer


# ---------------------------------------------------------------------------
# build_chain tests
# ---------------------------------------------------------------------------

class TestBuildChain(unittest.TestCase):
    """SlateResolver.build_chain() returns chain in most-specific-first order."""

    def test_build_chain_single_slate(self):
        """Slate with no parent returns a list of one."""
        import core.slate.resolver as resolver_mod
        import core.nodes.wrappers.slate as slate_mod

        mock_cmds = _make_mock_cmds()
        mock_cmds.listConnections.return_value = []  # no parent

        orig_resolver_cmds = resolver_mod.MAYA_AVAILABLE
        orig_slate_cmds = slate_mod.cmds
        resolver_mod.MAYA_AVAILABLE = True
        slate_mod.cmds = mock_cmds

        from core.slate.resolver import SlateResolver
        from core.nodes.wrappers.slate import CTXSlateNode

        try:
            # Build a slate whose get_parent_slate returns None
            shot_slate = _make_slate('CTX_Slate_shot')
            shot_slate.get_parent_slate.return_value = None

            # Patch CTXSlateNode so we can pass our mock directly
            chain = SlateResolver.build_chain(shot_slate)
            self.assertEqual(len(chain), 1)
            self.assertIs(chain[0], shot_slate)
        finally:
            resolver_mod.MAYA_AVAILABLE = orig_resolver_cmds
            slate_mod.cmds = orig_slate_cmds

    def test_build_chain_three_levels(self):
        """Shot -> seq -> master chain returns list of 3."""
        from core.slate.resolver import SlateResolver

        master = _make_slate('CTX_Slate_master', parent=None)
        seq = _make_slate('CTX_Slate_seq', parent=master)
        shot = _make_slate('CTX_Slate_shot', parent=seq)

        chain = SlateResolver.build_chain(shot)
        self.assertEqual(len(chain), 3)
        self.assertIs(chain[0], shot)
        self.assertIs(chain[1], seq)
        self.assertIs(chain[2], master)

    def test_build_chain_circular_guard(self):
        """Circular parentSlate connection does not infinite-loop."""
        from core.slate.resolver import SlateResolver

        # Create circular reference: A -> B -> A
        slate_a = _make_slate('CTX_Slate_A')
        slate_b = _make_slate('CTX_Slate_B')
        slate_a.get_parent_slate.return_value = slate_b
        slate_b.get_parent_slate.return_value = slate_a  # circular

        chain = SlateResolver.build_chain(slate_a)
        # Should stop at 2 -- both visited, circular detected on 3rd attempt
        self.assertGreaterEqual(len(chain), 1)
        # Must not raise or loop forever
        names = [s.node_name for s in chain]
        self.assertIn('CTX_Slate_A', names)


# ---------------------------------------------------------------------------
# resolve_layer_state tests
# ---------------------------------------------------------------------------

class TestResolveLayerState(unittest.TestCase):
    """SlateResolver.resolve_layer_state() returns correct resolution dict."""

    def _run_resolve(self, shot_slate):
        """Helper: patch _get_slate_for_node to return shot_slate and run resolve."""
        from core.slate.resolver import SlateResolver
        with patch.object(SlateResolver, '_get_slate_for_node', return_value=shot_slate):
            return SlateResolver.resolve_layer_state('CTX_Shot1')

    def test_resolve_no_override_returns_none_renderable(self):
        """Layer with renderableEnabled=False -> overridden=False, renderable=None."""
        layer = _make_layer('beauty', renderable=True, override_enabled=False)
        slate = _make_slate('CTX_Slate_shot', layers=[layer], parent=None)

        result = self._run_resolve(slate)

        self.assertIn('beauty', result)
        self.assertFalse(result['beauty']['overridden'])
        self.assertIsNone(result['beauty']['renderable'])

    def test_resolve_shot_slate_wins_over_seq(self):
        """Shot slate and seq slate both have 'beauty'; shot slate wins (index 0)."""
        # Shot slate: beauty=False, enabled
        shot_layer = _make_layer('beauty', renderable=False, override_enabled=True)
        shot_slate = _make_slate('CTX_Slate_shot', layers=[shot_layer])

        # Seq slate: beauty=True, enabled
        seq_layer = _make_layer('beauty', renderable=True, override_enabled=True)
        seq_slate = _make_slate('CTX_Slate_seq', layers=[seq_layer], parent=None)

        shot_slate.get_parent_slate.return_value = seq_slate

        result = self._run_resolve(shot_slate)

        self.assertIn('beauty', result)
        self.assertTrue(result['beauty']['overridden'])
        self.assertFalse(result['beauty']['renderable'])  # shot wins with False
        self.assertEqual(result['beauty']['source'], 'CTX_Slate_shot')

    def test_resolve_seq_slate_fallback(self):
        """Shot has no 'beauty' entry; seq slate has it with enabled=True -> uses seq value."""
        shot_slate = _make_slate('CTX_Slate_shot', layers=[], parent=None)

        seq_layer = _make_layer('beauty', renderable=True, override_enabled=True)
        seq_slate = _make_slate('CTX_Slate_seq', layers=[seq_layer], parent=None)

        shot_slate.get_parent_slate.return_value = seq_slate

        result = self._run_resolve(shot_slate)

        self.assertIn('beauty', result)
        self.assertTrue(result['beauty']['overridden'])
        self.assertTrue(result['beauty']['renderable'])
        self.assertEqual(result['beauty']['source'], 'CTX_Slate_seq')

    def test_resolve_disabled_slate_skipped(self):
        """Slate with enabled=False is in chain; its values are not applied."""
        # Shot slate: disabled
        shot_layer = _make_layer('beauty', renderable=False, override_enabled=True)
        shot_slate = _make_slate('CTX_Slate_shot', layers=[shot_layer], enabled=False)

        # Seq slate: enabled, beauty=True
        seq_layer = _make_layer('beauty', renderable=True, override_enabled=True)
        seq_slate = _make_slate('CTX_Slate_seq', layers=[seq_layer], parent=None)

        shot_slate.get_parent_slate.return_value = seq_slate

        result = self._run_resolve(shot_slate)

        self.assertIn('beauty', result)
        self.assertTrue(result['beauty']['overridden'])
        # Seq wins because shot was disabled
        self.assertTrue(result['beauty']['renderable'])
        self.assertEqual(result['beauty']['source'], 'CTX_Slate_seq')

    def test_resolve_returns_empty_when_no_slate(self):
        """_get_slate_for_node returns None -> empty dict."""
        from core.slate.resolver import SlateResolver
        with patch.object(SlateResolver, '_get_slate_for_node', return_value=None):
            result = SlateResolver.resolve_layer_state('CTX_Shot1')
        self.assertEqual(result, {})


# ---------------------------------------------------------------------------
# get_resolved_renderable_layers tests
# ---------------------------------------------------------------------------

class TestGetResolvedRenderableLayers(unittest.TestCase):

    def test_get_resolved_renderable_layers_returns_list(self):
        """Layers with renderable=True returned; renderable=False excluded."""
        from core.slate.resolver import SlateResolver

        resolved = {
            'beauty': {'renderable': True,  'overridden': True,  'source': 'CTX_Slate_shot'},
            'diffuse': {'renderable': False, 'overridden': True,  'source': 'CTX_Slate_shot'},
            'shadow':  {'renderable': True,  'overridden': False, 'source': ''},
        }

        with patch.object(SlateResolver, 'resolve_layer_state', return_value=resolved):
            result = SlateResolver.get_resolved_renderable_layers('CTX_Shot1')

        self.assertIsInstance(result, list)
        self.assertIn('beauty', result)
        self.assertNotIn('diffuse', result)  # renderable=False
        self.assertNotIn('shadow', result)   # overridden=False

    def test_get_resolved_renderable_layers_no_slate_returns_none(self):
        """Node with no slate -> returns None (caller uses scene state)."""
        from core.slate.resolver import SlateResolver

        with patch.object(SlateResolver, 'resolve_layer_state', return_value={}):
            result = SlateResolver.get_resolved_renderable_layers('CTX_Shot1')

        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# apply_to_scene tests
# ---------------------------------------------------------------------------

class TestApplyToScene(unittest.TestCase):

    def test_apply_to_scene_calls_set_renderable(self):
        """apply_to_scene calls layer.setRenderable for overridden layers."""
        import core.slate.resolver as resolver_mod
        from core.slate.resolver import SlateResolver

        resolved = {
            'beauty': {'renderable': True, 'overridden': True, 'source': 'CTX_Slate_shot'},
        }

        mock_layer = MagicMock()
        mock_rs = MagicMock()
        mock_rs.getRenderLayer.return_value = mock_layer
        mock_rs_module = MagicMock()
        mock_rs_module.instance.return_value = mock_rs

        orig_available = resolver_mod.MAYA_AVAILABLE
        resolver_mod.MAYA_AVAILABLE = True

        # Build the nested mock hierarchy for maya.app.renderSetup.model.renderSetup
        maya_mock = MagicMock()
        maya_app_mock = MagicMock()
        maya_app_rs_mock = MagicMock()
        maya_app_rs_model_mock = MagicMock()
        maya_app_rs_model_mock.renderSetup = mock_rs_module

        modules_patch = {
            'maya': maya_mock,
            'maya.app': maya_app_mock,
            'maya.app.renderSetup': maya_app_rs_mock,
            'maya.app.renderSetup.model': maya_app_rs_model_mock,
            'maya.app.renderSetup.model.renderSetup': mock_rs_module,
        }

        try:
            with patch.object(SlateResolver, 'resolve_layer_state', return_value=resolved):
                with patch.dict('sys.modules', modules_patch):
                    SlateResolver.apply_to_scene('CTX_Shot1')

            mock_rs.getRenderLayer.assert_called_once_with('beauty')
            mock_layer.setRenderable.assert_called_once_with(True)
        finally:
            resolver_mod.MAYA_AVAILABLE = orig_available

    def test_apply_to_scene_skips_non_overridden(self):
        """Layers with overridden=False do not have setRenderable called."""
        import core.slate.resolver as resolver_mod
        from core.slate.resolver import SlateResolver

        resolved = {
            'beauty': {'renderable': True, 'overridden': False, 'source': ''},
        }

        mock_layer = MagicMock()
        mock_rs = MagicMock()
        mock_rs.getRenderLayer.return_value = mock_layer
        mock_rs_module = MagicMock()
        mock_rs_module.instance.return_value = mock_rs

        orig_available = resolver_mod.MAYA_AVAILABLE
        resolver_mod.MAYA_AVAILABLE = True

        maya_mock = MagicMock()
        maya_app_mock = MagicMock()
        maya_app_rs_mock = MagicMock()
        maya_app_rs_model_mock = MagicMock()
        maya_app_rs_model_mock.renderSetup = mock_rs_module

        modules_patch = {
            'maya': maya_mock,
            'maya.app': maya_app_mock,
            'maya.app.renderSetup': maya_app_rs_mock,
            'maya.app.renderSetup.model': maya_app_rs_model_mock,
            'maya.app.renderSetup.model.renderSetup': mock_rs_module,
        }

        try:
            with patch.object(SlateResolver, 'resolve_layer_state', return_value=resolved):
                with patch.dict('sys.modules', modules_patch):
                    SlateResolver.apply_to_scene('CTX_Shot1')

            mock_layer.setRenderable.assert_not_called()
        finally:
            resolver_mod.MAYA_AVAILABLE = orig_available

    def test_apply_to_scene_no_op_without_maya(self):
        """apply_to_scene returns immediately when MAYA_AVAILABLE is False."""
        import core.slate.resolver as resolver_mod
        from core.slate.resolver import SlateResolver

        orig_available = resolver_mod.MAYA_AVAILABLE
        resolver_mod.MAYA_AVAILABLE = False
        try:
            # Should not raise
            SlateResolver.apply_to_scene('CTX_Shot1')
        finally:
            resolver_mod.MAYA_AVAILABLE = orig_available

    def test_apply_to_scene_no_op_when_empty_resolved(self):
        """apply_to_scene returns early when resolve_layer_state returns empty dict."""
        import core.slate.resolver as resolver_mod
        from core.slate.resolver import SlateResolver

        orig_available = resolver_mod.MAYA_AVAILABLE
        resolver_mod.MAYA_AVAILABLE = True
        try:
            with patch.object(SlateResolver, 'resolve_layer_state', return_value={}):
                # Should not attempt to import renderSetup
                SlateResolver.apply_to_scene('CTX_Shot1')
        finally:
            resolver_mod.MAYA_AVAILABLE = orig_available


# ---------------------------------------------------------------------------
# _get_slate_for_node tests (no-Maya path)
# ---------------------------------------------------------------------------

class TestGetSlateForNodeNoMaya(unittest.TestCase):

    def test_returns_none_without_maya(self):
        """_get_slate_for_node returns None when MAYA_AVAILABLE is False."""
        import core.slate.resolver as resolver_mod
        from core.slate.resolver import SlateResolver

        orig = resolver_mod.MAYA_AVAILABLE
        resolver_mod.MAYA_AVAILABLE = False
        try:
            result = SlateResolver._get_slate_for_node('CTX_Shot1')
            self.assertIsNone(result)
        finally:
            resolver_mod.MAYA_AVAILABLE = orig


if __name__ == '__main__':
    unittest.main()
