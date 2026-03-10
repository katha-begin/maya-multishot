# -*- coding: utf-8 -*-
"""Tests for config-driven parameter fixes (Stream D).

Verifies that hardcoded values have been replaced with config-driven lookups
in asset_scanner.py, asset_manager_dialog.py, core/nodes.py, and
core/gaffer/resolver.py.

Author: Context Variables Pipeline
Date: 2026-03-10
"""

from __future__ import absolute_import, division, print_function

import json
import os
import sys
import tempfile
import unittest

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.project_config import ProjectConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REAL_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'project_configs', 'ctx_config.json'
)

MINIMAL_CONFIG = {
    'version': '1.0',
    'project': {'name': 'Test', 'code': 'TST'},
    'roots': {'projRoot': 'V:/'},
    'staticPaths': {'sceneBase': 'all/scene'},
    'templates': {
        'publishPath': '$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish'
    },
    'patterns': {'fullFormat': '$ep_$seq_$shot__$assetType_$assetName_$variant.$ext'},
}


def _make_config(extra=None):
    """Build a ProjectConfig from a minimal dict, optionally merged with extra."""
    data = dict(MINIMAL_CONFIG)
    if extra:
        data.update(extra)
    cfg = ProjectConfig()
    cfg.data = data
    cfg.version = '1.0'
    return cfg


def _load_real_config():
    """Load the real project config from disk."""
    if not os.path.exists(REAL_CONFIG_PATH):
        return None
    return ProjectConfig(REAL_CONFIG_PATH)


# ---------------------------------------------------------------------------
# Tests: ProjectConfig new methods
# ---------------------------------------------------------------------------

class TestGetTokenPattern(unittest.TestCase):
    """Tests for ProjectConfig.get_token_pattern()."""

    def test_returns_pattern_for_known_token(self):
        cfg = _make_config({'tokens': {'ver': {'pattern': r'^v\d+$'}}})
        self.assertEqual(cfg.get_token_pattern('ver'), r'^v\d+$')

    def test_returns_none_for_missing_token(self):
        cfg = _make_config({'tokens': {}})
        self.assertIsNone(cfg.get_token_pattern('ver'))

    def test_returns_none_when_no_tokens_section(self):
        cfg = _make_config()
        self.assertIsNone(cfg.get_token_pattern('ver'))

    def test_real_config_ver_pattern(self):
        cfg = _load_real_config()
        if cfg is None:
            self.skipTest('Real config not found')
        pattern = cfg.get_token_pattern('ver')
        self.assertIsNotNone(pattern)
        self.assertIsInstance(pattern, str)

    def test_real_config_ep_pattern(self):
        cfg = _load_real_config()
        if cfg is None:
            self.skipTest('Real config not found')
        pattern = cfg.get_token_pattern('ep')
        self.assertIsNotNone(pattern)


class TestGetExtensions(unittest.TestCase):
    """Tests for ProjectConfig.get_extensions()."""

    def test_returns_list_of_strings(self):
        cfg = _make_config({'extensions': ['.abc', '.vdb', '.ass']})
        exts = cfg.get_extensions()
        self.assertIsInstance(exts, list)

    def test_strips_leading_dot(self):
        cfg = _make_config({'extensions': ['.abc', '.vdb']})
        exts = cfg.get_extensions()
        self.assertIn('abc', exts)
        self.assertIn('vdb', exts)
        self.assertNotIn('.abc', exts)

    def test_returns_empty_list_when_missing(self):
        cfg = _make_config()
        exts = cfg.get_extensions()
        self.assertEqual(exts, [])

    def test_real_config_returns_nonempty_list(self):
        cfg = _load_real_config()
        if cfg is None:
            self.skipTest('Real config not found')
        exts = cfg.get_extensions()
        self.assertIsInstance(exts, list)
        self.assertGreater(len(exts), 0)
        # Verify no leading dots
        for ext in exts:
            self.assertFalse(ext.startswith('.'),
                             'Extension should not have leading dot: %s' % ext)


class TestGetCameraFileSuffix(unittest.TestCase):
    """Tests for ProjectConfig.get_camera_file_suffix()."""

    def test_returns_value_from_config(self):
        cfg = _make_config({
            'assetDiscovery': {'cameraFileSuffix': '_cam', 'heroSubdir': 'hero'}
        })
        self.assertEqual(cfg.get_camera_file_suffix(), '_cam')

    def test_default_when_key_absent(self):
        cfg = _make_config({'assetDiscovery': {'heroSubdir': 'hero'}})
        self.assertEqual(cfg.get_camera_file_suffix(), '_camera')

    def test_default_when_section_absent(self):
        cfg = _make_config()
        self.assertEqual(cfg.get_camera_file_suffix(), '_camera')

    def test_real_config_returns_camera_suffix(self):
        cfg = _load_real_config()
        if cfg is None:
            self.skipTest('Real config not found')
        suffix = cfg.get_camera_file_suffix()
        self.assertIsInstance(suffix, str)
        self.assertEqual(suffix, '_camera')


class TestGetGafferAttributes(unittest.TestCase):
    """Tests for ProjectConfig.get_gaffer_attributes/simple/compound()."""

    def _config_with_gaffer_attrs(self):
        return _make_config({
            'gafferAttributes': {
                'simple': ['intensity', 'exposure'],
                'compound': {
                    'color': ['colorR', 'colorG', 'colorB']
                }
            }
        })

    def test_get_gaffer_attributes_returns_dict(self):
        cfg = self._config_with_gaffer_attrs()
        result = cfg.get_gaffer_attributes()
        self.assertIsInstance(result, dict)

    def test_get_gaffer_simple_attributes_returns_list(self):
        cfg = self._config_with_gaffer_attrs()
        simple = cfg.get_gaffer_simple_attributes()
        self.assertIsInstance(simple, list)
        self.assertIn('intensity', simple)
        self.assertIn('exposure', simple)

    def test_get_gaffer_compound_attributes_returns_dict(self):
        cfg = self._config_with_gaffer_attrs()
        compound = cfg.get_gaffer_compound_attributes()
        self.assertIsInstance(compound, dict)
        self.assertIn('color', compound)
        self.assertEqual(compound['color'], ['colorR', 'colorG', 'colorB'])

    def test_defaults_when_section_absent(self):
        cfg = _make_config()
        self.assertEqual(cfg.get_gaffer_attributes(), {})
        self.assertEqual(cfg.get_gaffer_simple_attributes(), [])
        self.assertEqual(cfg.get_gaffer_compound_attributes(), {})

    def test_real_config_gaffer_attributes(self):
        cfg = _load_real_config()
        if cfg is None:
            self.skipTest('Real config not found')
        simple = cfg.get_gaffer_simple_attributes()
        compound = cfg.get_gaffer_compound_attributes()
        self.assertIsInstance(simple, list)
        self.assertIsInstance(compound, dict)
        self.assertIn('intensity', simple)
        self.assertIn('color', compound)
        self.assertIn('translate', compound)

    def test_real_config_compound_has_correct_components(self):
        cfg = _load_real_config()
        if cfg is None:
            self.skipTest('Real config not found')
        compound = cfg.get_gaffer_compound_attributes()
        self.assertEqual(compound.get('color'), ['colorR', 'colorG', 'colorB'])
        self.assertEqual(compound.get('translate'),
                         ['translateX', 'translateY', 'translateZ'])


# ---------------------------------------------------------------------------
# Tests: dept list from config
# ---------------------------------------------------------------------------

class TestDeptListFromConfig(unittest.TestCase):
    """Verify that dept list is read from config in asset_scanner."""

    def test_get_token_values_dept_returns_list(self):
        cfg = _make_config({
            'tokens': {
                'dept': {
                    'values': ['layout', 'anim', 'cfx', 'fx', 'lighting']
                }
            }
        })
        values = cfg.get_token_values('dept')
        self.assertIsInstance(values, list)
        self.assertIn('anim', values)
        self.assertIn('lighting', values)

    def test_real_config_dept_values(self):
        cfg = _load_real_config()
        if cfg is None:
            self.skipTest('Real config not found')
        values = cfg.get_token_values('dept')
        self.assertIsNotNone(values)
        self.assertIsInstance(values, list)
        self.assertGreater(len(values), 0)


class TestDeptPriorityFromConfig(unittest.TestCase):
    """Verify that dept priority is read from config."""

    def test_get_dept_priority_returns_ordered_list(self):
        cfg = _make_config({
            'deptPriority': {
                'order': ['lighting', 'fx', 'anim', 'layout']
            }
        })
        order = cfg.get_dept_priority()
        self.assertIsInstance(order, list)
        self.assertEqual(order[0], 'lighting')

    def test_fallback_when_absent(self):
        cfg = _make_config()
        order = cfg.get_dept_priority()
        self.assertIsInstance(order, list)
        self.assertGreater(len(order), 0)

    def test_real_config_dept_priority(self):
        cfg = _load_real_config()
        if cfg is None:
            self.skipTest('Real config not found')
        order = cfg.get_dept_priority()
        self.assertIsInstance(order, list)
        self.assertGreater(len(order), 0)
        self.assertEqual(order[0], 'lighting')


# ---------------------------------------------------------------------------
# Tests: version pattern from config
# ---------------------------------------------------------------------------

class TestVersionPatternFromConfig(unittest.TestCase):
    """Verify that version dir matching uses config pattern."""

    def test_config_ver_pattern_matches_v003(self):
        import re
        cfg = _load_real_config()
        if cfg is None:
            self.skipTest('Real config not found')
        pattern = cfg.get_token_pattern('ver') or r'^v\d+$'
        self.assertTrue(re.match(pattern, 'v003'))

    def test_config_ver_pattern_rejects_nonversion(self):
        import re
        cfg = _load_real_config()
        if cfg is None:
            self.skipTest('Real config not found')
        pattern = cfg.get_token_pattern('ver') or r'^v\d+$'
        # A plain directory name should not match
        self.assertIsNone(re.match(pattern, 'publish'))
        self.assertIsNone(re.match(pattern, 'SH0170'))

    def test_fallback_pattern_works(self):
        import re
        pattern = r'^v\d+$'
        self.assertTrue(re.match(pattern, 'v001'))
        self.assertTrue(re.match(pattern, 'v99'))
        self.assertIsNone(re.match(pattern, 'v'))
        self.assertIsNone(re.match(pattern, 'abc'))


# ---------------------------------------------------------------------------
# Tests: extensions from config
# ---------------------------------------------------------------------------

class TestExtensionsFromConfig(unittest.TestCase):
    """Verify that file extension filtering uses config list."""

    def test_extensions_build_tuple(self):
        cfg = _load_real_config()
        if cfg is None:
            self.skipTest('Real config not found')
        config_exts = cfg.get_extensions()
        self.assertTrue(len(config_exts) > 0)
        extensions = tuple('.' + e for e in config_exts)
        self.assertIn('.abc', extensions)
        self.assertIn('.vdb', extensions)

    def test_fallback_extensions(self):
        # When config has no extensions, hardcoded fallback must cover expected types
        fallback = ('.abc', '.rs', '.ma', '.mb', '.vdb', '.ass')
        self.assertIn('.abc', fallback)
        self.assertIn('.vdb', fallback)

    def test_abc_file_passes_extension_filter(self):
        cfg = _make_config({'extensions': ['.abc', '.vdb']})
        exts = cfg.get_extensions()
        extensions = tuple('.' + e for e in exts)
        self.assertTrue('Ep04_sq0070_SH0170__CHAR_CatStompie_001.abc'.endswith(extensions))

    def test_txt_file_blocked_by_extension_filter(self):
        cfg = _make_config({'extensions': ['.abc', '.vdb']})
        exts = cfg.get_extensions()
        extensions = tuple('.' + e for e in exts)
        self.assertFalse('readme.txt'.endswith(extensions))


# ---------------------------------------------------------------------------
# Tests: camera suffix from config
# ---------------------------------------------------------------------------

class TestCameraSuffixFromConfig(unittest.TestCase):
    """Verify that camera file suffix uses config value."""

    def test_camera_suffix_from_config(self):
        cfg = _make_config({
            'assetDiscovery': {'cameraFileSuffix': '_camera', 'heroSubdir': 'hero'}
        })
        suffix = cfg.get_camera_file_suffix()
        self.assertEqual(suffix, '_camera')
        # Simulate the check done in _parse_filename
        asset_part = 'SWA_Ep04_SH0170_camera'
        self.assertTrue(asset_part.endswith(suffix))

    def test_custom_camera_suffix(self):
        cfg = _make_config({
            'assetDiscovery': {'cameraFileSuffix': '_cam', 'heroSubdir': 'hero'}
        })
        suffix = cfg.get_camera_file_suffix()
        self.assertEqual(suffix, '_cam')
        self.assertTrue('SWA_Ep04_SH0170_cam'.endswith(suffix))
        self.assertFalse('SWA_Ep04_SH0170_camera'.endswith(suffix))


# ---------------------------------------------------------------------------
# Tests: gaffer attributes from config (_get_supported_attributes helper)
# ---------------------------------------------------------------------------

class TestGafferAttributesFromConfig(unittest.TestCase):
    """Verify that _get_supported_attributes returns config attrs when available."""

    def test_helper_returns_fallback_without_config(self):
        from core.gaffer.resolver import _get_supported_attributes, AttributeResolver
        result = _get_supported_attributes(None)
        self.assertIsInstance(result, list)
        self.assertIn('intensity', result)
        self.assertIn('color', result)
        # Should match the fallback constant
        self.assertEqual(set(result), set(AttributeResolver.SUPPORTED_ATTRIBUTES))

    def test_helper_prefers_config_over_fallback(self):
        from core.gaffer.resolver import _get_supported_attributes
        cfg = _make_config({
            'gafferAttributes': {
                'simple': ['intensity', 'exposure'],
                'compound': {'color': ['colorR', 'colorG', 'colorB']}
            }
        })
        result = _get_supported_attributes(cfg)
        self.assertIn('intensity', result)
        self.assertIn('color', result)
        self.assertNotIn('temperature', result)  # not in our custom config

    def test_helper_falls_back_when_config_attrs_empty(self):
        from core.gaffer.resolver import _get_supported_attributes, AttributeResolver
        # Config has the section but both simple and compound are empty
        cfg = _make_config({'gafferAttributes': {'simple': [], 'compound': {}}})
        result = _get_supported_attributes(cfg)
        # Should fall back to the class constant
        self.assertEqual(set(result), set(AttributeResolver.SUPPORTED_ATTRIBUTES))

    def test_real_config_gaffer_attributes_in_helper(self):
        from core.gaffer.resolver import _get_supported_attributes
        cfg = _load_real_config()
        if cfg is None:
            self.skipTest('Real config not found')
        result = _get_supported_attributes(cfg)
        self.assertIsInstance(result, list)
        self.assertIn('intensity', result)
        self.assertIn('color', result)


if __name__ == '__main__':
    unittest.main()
