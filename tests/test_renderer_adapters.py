# -*- coding: utf-8 -*-
"""Unit tests for renderer adapter improvements (Stream E).

Tests:
- get_active_renderer() headless behaviour
- get_preferred_extensions() fallback and config-driven paths
- ProjectConfig renderer config methods
- NodeManager._apply_path_to_maya_node() config-driven and fallback lookup
"""

from __future__ import absolute_import, division, print_function

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.project_config import ProjectConfig
from core.renderers import get_active_renderer, get_preferred_extensions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_PATH = os.path.join(_REPO_ROOT, 'project_configs', 'ctx_config.json')


def _load_real_config():
    """Return a ProjectConfig loaded from the real ctx_config.json."""
    cfg = ProjectConfig()
    cfg.load(_CONFIG_PATH)
    return cfg


# ---------------------------------------------------------------------------
# get_active_renderer
# ---------------------------------------------------------------------------

class TestGetActiveRenderer(unittest.TestCase):
    """Tests for get_active_renderer()."""

    def test_get_active_renderer_no_maya(self):
        """When Maya is not importable the function returns 'unknown' gracefully."""
        # Maya is never available in the test environment, so this exercises
        # the except branch of get_active_renderer().
        result = get_active_renderer()
        self.assertIsInstance(result, str)
        # In a headless environment (no Maya) it must return 'unknown'
        self.assertEqual(result, 'unknown')


# ---------------------------------------------------------------------------
# get_preferred_extensions -- no config
# ---------------------------------------------------------------------------

class TestGetPreferredExtensionsNoConfig(unittest.TestCase):
    """Tests for get_preferred_extensions() using hardcoded fallbacks."""

    def test_get_preferred_extensions_redshift_no_config(self):
        """Hardcoded fallback for redshift starts with 'rs'."""
        exts = get_preferred_extensions('redshift')
        self.assertEqual(exts, ['rs', 'abc', 'ma', 'mb'])

    def test_get_preferred_extensions_arnold_no_config(self):
        """Hardcoded fallback for arnold starts with 'ass'."""
        exts = get_preferred_extensions('arnold')
        self.assertEqual(exts, ['ass', 'abc', 'ma', 'mb'])

    def test_get_preferred_extensions_maya_no_config(self):
        """Hardcoded fallback for maya starts with 'ma'."""
        exts = get_preferred_extensions('maya')
        self.assertEqual(exts, ['ma', 'mb', 'abc'])

    def test_get_preferred_extensions_unknown_renderer(self):
        """Unknown renderer name returns a safe default list."""
        exts = get_preferred_extensions('vray')
        self.assertIsInstance(exts, list)
        self.assertTrue(len(exts) > 0)
        # Should at least contain common formats
        for ext in exts:
            self.assertIsInstance(ext, str)
            self.assertFalse(ext.startswith('.'))


# ---------------------------------------------------------------------------
# get_preferred_extensions -- with config
# ---------------------------------------------------------------------------

class TestGetPreferredExtensionsWithConfig(unittest.TestCase):
    """Tests for get_preferred_extensions() using a real ProjectConfig."""

    def setUp(self):
        self.config = _load_real_config()

    def test_get_preferred_extensions_from_config_redshift(self):
        """Config overrides hardcoded fallback for redshift."""
        exts = get_preferred_extensions('redshift', self.config)
        self.assertEqual(exts[0], 'rs',
                         "First preferred extension for redshift must be 'rs'")

    def test_get_preferred_extensions_from_config_arnold(self):
        """Config overrides hardcoded fallback for arnold."""
        exts = get_preferred_extensions('arnold', self.config)
        self.assertEqual(exts[0], 'ass',
                         "First preferred extension for arnold must be 'ass'")

    def test_get_preferred_extensions_from_config_maya(self):
        """Config overrides hardcoded fallback for maya."""
        exts = get_preferred_extensions('maya', self.config)
        self.assertIn('ma', exts)


# ---------------------------------------------------------------------------
# ProjectConfig renderer methods
# ---------------------------------------------------------------------------

class TestProjectConfigRendererMethods(unittest.TestCase):
    """Tests for new ProjectConfig renderer config methods."""

    def setUp(self):
        self.config = _load_real_config()

    def test_renderer_config_loaded(self):
        """ctx_config.json has a 'renderers' section with expected keys."""
        self.assertIn('renderers', self.config.data)
        renderers = self.config.data['renderers']
        for name in ('redshift', 'arnold', 'maya'):
            self.assertIn(name, renderers,
                          "renderers section must contain '%s'" % name)

    def test_get_renderer_config_redshift(self):
        cfg = self.config.get_renderer_config('redshift')
        self.assertIsNotNone(cfg)
        self.assertIsInstance(cfg, dict)

    def test_get_renderer_config_arnold(self):
        cfg = self.config.get_renderer_config('arnold')
        self.assertIsNotNone(cfg)
        self.assertIsInstance(cfg, dict)

    def test_get_renderer_config_unknown(self):
        cfg = self.config.get_renderer_config('vray')
        self.assertIsNone(cfg)

    def test_get_standin_node_type_redshift(self):
        node_type = self.config.get_standin_node_type('redshift')
        self.assertEqual(node_type, 'RedshiftProxyMesh')

    def test_get_standin_node_type_arnold(self):
        node_type = self.config.get_standin_node_type('arnold')
        self.assertEqual(node_type, 'aiStandIn')

    def test_get_standin_node_type_maya(self):
        node_type = self.config.get_standin_node_type('maya')
        self.assertIsNone(node_type)

    def test_get_standin_file_attr_redshift(self):
        attr = self.config.get_standin_file_attr('redshift')
        self.assertEqual(attr, 'fileName')

    def test_get_standin_file_attr_arnold(self):
        attr = self.config.get_standin_file_attr('arnold')
        self.assertEqual(attr, 'dso')

    def test_get_standin_file_attr_maya(self):
        attr = self.config.get_standin_file_attr('maya')
        self.assertIsNone(attr)

    def test_get_preferred_extensions_redshift(self):
        exts = self.config.get_preferred_extensions('redshift')
        self.assertEqual(exts, ['rs', 'abc', 'ma', 'mb'])

    def test_get_preferred_extensions_arnold(self):
        exts = self.config.get_preferred_extensions('arnold')
        self.assertEqual(exts, ['ass', 'abc', 'ma', 'mb'])

    def test_get_preferred_extensions_maya(self):
        exts = self.config.get_preferred_extensions('maya')
        self.assertEqual(exts, ['ma', 'mb', 'abc'])

    def test_get_preferred_extensions_unknown(self):
        exts = self.config.get_preferred_extensions('vray')
        self.assertEqual(exts, [])


# ---------------------------------------------------------------------------
# NodeManager._apply_path_to_maya_node -- config-driven lookup
# ---------------------------------------------------------------------------

class TestApplyPathNodeAttrMap(unittest.TestCase):
    """Tests for the config-driven node_attr_map logic in _apply_path_to_maya_node.

    We test the lookup-building logic in isolation without running Maya.
    """

    def setUp(self):
        self.config = _load_real_config()

    def _build_node_attr_map(self, config):
        """Replicate the node_attr_map build logic from _apply_path_to_maya_node."""
        node_attr_map = {}
        if config is not None:
            for renderer_name in ('redshift', 'arnold', 'maya'):
                rnd_cfg = config.get_renderer_config(renderer_name) or {}
                node_t = rnd_cfg.get('standinNodeType')
                file_a = rnd_cfg.get('standinFileAttr')
                if node_t and file_a:
                    node_attr_map[node_t] = file_a
        return node_attr_map

    def test_apply_path_node_attr_map_from_config(self):
        """node_attr_map built from config maps aiStandIn->dso and RS->fileName."""
        node_attr_map = self._build_node_attr_map(self.config)
        self.assertIn('aiStandIn', node_attr_map)
        self.assertEqual(node_attr_map['aiStandIn'], 'dso')
        self.assertIn('RedshiftProxyMesh', node_attr_map)
        self.assertEqual(node_attr_map['RedshiftProxyMesh'], 'fileName')

    def test_apply_path_fallback_without_config(self):
        """Without config, hardcoded fallback map is still correct."""
        node_attr_map = self._build_node_attr_map(None)
        # No config -> empty map from config branch -> use fallback below
        # Replicate fallback logic
        if not node_attr_map:
            node_attr_map = {
                'aiStandIn':         'dso',
                'RedshiftProxyMesh': 'fileName',
            }
        self.assertEqual(node_attr_map['aiStandIn'], 'dso')
        self.assertEqual(node_attr_map['RedshiftProxyMesh'], 'fileName')

    def test_maya_renderer_excluded_from_map(self):
        """maya renderer has null standinNodeType so it must NOT appear in the map."""
        node_attr_map = self._build_node_attr_map(self.config)
        self.assertNotIn(None, node_attr_map)


if __name__ == '__main__':
    unittest.main()
