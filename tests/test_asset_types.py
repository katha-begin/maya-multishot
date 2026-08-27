# -*- coding: utf-8 -*-
"""Tests for core/asset_types.py -- asset type naming and discovery policy.

Runs without Maya.
"""

from __future__ import absolute_import, division, print_function

import os
import sys
import unittest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core import asset_types


class FakeConfig(object):
    """Minimal ProjectConfig stand-in exposing only what asset_types reads."""

    def __init__(self, extensions=None, camera_suffix='_camera', policies=None):
        self._extensions = extensions or ['abc', 'vdb', 'ass', 'rs', 'ma', 'mb']
        self._camera_suffix = camera_suffix
        self._policies = policies or {}

    def get_extensions(self):
        return list(self._extensions)

    def get_camera_file_suffix(self):
        return self._camera_suffix

    def get_asset_type_policies(self):
        return dict(self._policies)


class TestPublishShape(unittest.TestCase):

    def test_cfx_is_sequence_dir(self):
        self.assertEqual(asset_types.get_publish_shape('CFX'),
                         asset_types.PUBLISH_SHAPE_SEQUENCE_DIR)

    def test_char_is_file(self):
        self.assertEqual(asset_types.get_publish_shape('CHAR'),
                         asset_types.PUBLISH_SHAPE_FILE)

    def test_unknown_type_defaults_to_file(self):
        self.assertEqual(asset_types.get_publish_shape('NOPE'),
                         asset_types.PUBLISH_SHAPE_FILE)

    def test_config_can_override_publish_shape(self):
        cfg = FakeConfig(policies={'CROWD': {'publishShape': 'sequenceDir'}})
        self.assertEqual(asset_types.get_publish_shape('CROWD', cfg),
                         asset_types.PUBLISH_SHAPE_SEQUENCE_DIR)


class TestParseAssetPart(unittest.TestCase):

    def test_standard_type_name_variant(self):
        info = asset_types.parse_asset_part('CHAR_CatStompie_001')
        self.assertEqual(info['type'], 'CHAR')
        self.assertEqual(info['name'], 'CatStompie')
        self.assertEqual(info['variant'], '001')

    def test_standard_multi_part_name(self):
        info = asset_types.parse_asset_part('CHAR_Cat_Stompie_001')
        self.assertEqual(info['name'], 'Cat_Stompie')
        self.assertEqual(info['variant'], '001')

    def test_cfx_no_separator_variant(self):
        info = asset_types.parse_asset_part('CFX_botgroomSamS001')
        self.assertEqual(info['type'], 'CFX')
        self.assertEqual(info['name'], 'botgroomSamS')
        self.assertEqual(info['variant'], '001')

    def test_cfx_lowercase_name(self):
        info = asset_types.parse_asset_part('CFX_botgroomevelyn001')
        self.assertEqual(info['name'], 'botgroomevelyn')
        self.assertEqual(info['variant'], '001')

    def test_cfx_name_with_trailing_capital(self):
        info = asset_types.parse_asset_part('CFX_botgroomWardenGuardD001')
        self.assertEqual(info['name'], 'botgroomWardenGuardD')
        self.assertEqual(info['variant'], '001')

    def test_cfx_without_variant_is_rejected(self):
        self.assertIsNone(asset_types.parse_asset_part('CFX_botgroomSamS'))

    def test_camera_detected_by_suffix(self):
        info = asset_types.parse_asset_part('SWA_Ep04_SH0170_camera')
        self.assertEqual(info['type'], 'CAM')
        self.assertEqual(info['name'], 'SWA_Ep04_SH0170_camera')
        self.assertEqual(info['variant'], asset_types.DEFAULT_VARIANT)

    def test_standard_too_few_parts_is_rejected(self):
        self.assertIsNone(asset_types.parse_asset_part('CHAR_Only'))

    def test_empty_is_rejected(self):
        self.assertIsNone(asset_types.parse_asset_part(''))
        self.assertIsNone(asset_types.parse_asset_part(None))

    def test_documented_risk_name_ending_in_digits(self):
        """A CFX name genuinely ending in digits mis-splits.

        Documented in the design as inherent to the no-separator convention.
        This test pins the behaviour so a future change is deliberate.
        """
        info = asset_types.parse_asset_part('CFX_bot2000')
        self.assertEqual(info['name'], 'bot2')
        self.assertEqual(info['variant'], '000')


class TestParsePublishName(unittest.TestCase):

    def test_cfx_sequence_directory(self):
        info = asset_types.parse_publish_name(
            'Ep02_sq0210_SH1180__CFX_botgroomevelyn001_ass', is_dir=True)
        self.assertEqual(info['type'], 'CFX')
        self.assertEqual(info['name'], 'botgroomevelyn')
        self.assertEqual(info['variant'], '001')
        self.assertEqual(info['ext'], 'ass')

    def test_standard_file(self):
        info = asset_types.parse_publish_name(
            'Ep04_sq0070_SH0140__CHAR_CatStompie_001.abc', is_dir=False)
        self.assertEqual(info['type'], 'CHAR')
        self.assertEqual(info['name'], 'CatStompie')
        self.assertEqual(info['ext'], 'abc')

    def test_sequence_type_as_plain_file_is_rejected(self):
        """A bare .ass file is not a valid CFX publish -- CFX is a directory."""
        self.assertIsNone(asset_types.parse_publish_name(
            'Ep02_sq0210_SH1180__CFX_botgroomevelyn001.ass', is_dir=False))

    def test_file_type_as_directory_is_rejected(self):
        self.assertIsNone(asset_types.parse_publish_name(
            'Ep04_sq0070_SH0140__CHAR_CatStompie_001_abc', is_dir=True))

    def test_missing_double_underscore_is_rejected(self):
        self.assertIsNone(asset_types.parse_publish_name(
            'Ep04_sq0070_SH0140_CHAR_CatStompie_001.abc', is_dir=False))

    def test_unknown_extension_directory_is_rejected(self):
        self.assertIsNone(asset_types.parse_publish_name(
            'Ep02_sq0210_SH1180__CFX_botgroomevelyn001_xyz', is_dir=True))


class TestBuildBasename(unittest.TestCase):

    def test_cfx_basename_has_no_variant_separator(self):
        name = asset_types.build_basename(
            'Ep02', 'sq0220', 'SH1350', 'CFX', 'botgroomSamS', '001')
        self.assertEqual(name, 'Ep02_sq0220_SH1350__CFX_botgroomSamS001')

    def test_standard_basename_keeps_variant_separator(self):
        name = asset_types.build_basename(
            'Ep04', 'sq0070', 'SH0140', 'CHAR', 'CatStompie', '001')
        self.assertEqual(name, 'Ep04_sq0070_SH0140__CHAR_CatStompie_001')

    def test_roundtrip_cfx(self):
        basename = asset_types.build_basename(
            'Ep02', 'sq0220', 'SH1350', 'CFX', 'botgroomSamS', '001')
        asset_part = basename.split('__')[1]
        info = asset_types.parse_asset_part(asset_part)
        self.assertEqual(info['type'], 'CFX')
        self.assertEqual(info['name'], 'botgroomSamS')
        self.assertEqual(info['variant'], '001')


class TestSequenceDirName(unittest.TestCase):

    def test_cfx_sequence_dir_name(self):
        basename = 'Ep02_sq0220_SH1350__CFX_botgroomSamS001'
        self.assertEqual(asset_types.build_sequence_dir_name(basename, 'ass'),
                         'Ep02_sq0220_SH1350__CFX_botgroomSamS001_ass')

    def test_cfx_frame_file_name(self):
        basename = 'Ep02_sq0220_SH1350__CFX_botgroomSamS001'
        self.assertEqual(asset_types.build_frame_file_name(basename, 'ass'),
                         'Ep02_sq0220_SH1350__CFX_botgroomSamS001.####.ass')

    def test_frame_token_is_configurable(self):
        basename = 'A__CFX_x001'
        self.assertEqual(
            asset_types.build_frame_file_name(basename, 'ass', frame_token='%04d'),
            'A__CFX_x001.%04d.ass')


class TestBuildNamespace(unittest.TestCase):

    def test_cfx_namespace_is_full_basename(self):
        basename = 'Ep02_sq0220_SH1350__CFX_botgroomSamS001'
        ns = asset_types.build_namespace('CFX', basename, 'botgroomSamS', '001')
        self.assertEqual(ns, basename)

    def test_standard_namespace_is_type_name_variant(self):
        basename = 'Ep04_sq0070_SH0140__CHAR_CatStompie_001'
        ns = asset_types.build_namespace('CHAR', basename, 'CatStompie', '001')
        self.assertEqual(ns, 'CHAR_CatStompie_001')

    def test_camera_namespace_is_name_only(self):
        basename = 'Ep04_sq0070_SH0170__SWA_Ep04_SH0170_camera'
        ns = asset_types.build_namespace(
            'CAM', basename, 'SWA_Ep04_SH0170_camera', '001')
        self.assertEqual(ns, 'SWA_Ep04_SH0170_camera')

    def test_cfx_namespaces_differ_between_shots(self):
        """Shot-unique namespaces are what make display-layer keying work."""
        a = asset_types.build_namespace(
            'CFX', 'Ep02_sq0210_SH1180__CFX_botgroomSamS001',
            'botgroomSamS', '001')
        b = asset_types.build_namespace(
            'CFX', 'Ep02_sq0220_SH1350__CFX_botgroomSamS001',
            'botgroomSamS', '001')
        self.assertNotEqual(a, b)


class TestStandinNodeNames(unittest.TestCase):

    def test_three_level_names(self):
        basename = 'Ep02_sq0220_SH1350__CFX_botgroomSamS001'
        names = asset_types.build_standin_node_names(basename)
        self.assertEqual(names['top'], basename)
        self.assertEqual(names['transform'], basename + '_aiStandIn')
        self.assertEqual(names['shape'], basename + '_aiStandInShape')

    def test_suffix_is_configurable(self):
        names = asset_types.build_standin_node_names('X', suffix='_aiStandin')
        self.assertEqual(names['transform'], 'X_aiStandin')
        self.assertEqual(names['shape'], 'X_aiStandinShape')


if __name__ == '__main__':
    unittest.main()
