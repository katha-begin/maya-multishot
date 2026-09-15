# -*- coding: utf-8 -*-
"""Tests for writing a custom frame range to the shot metadata JSON.

Plain unittest with no mock, so it also runs under Maya's Python 2.7:
    mayapy2 -m unittest tests.test_shot_metadata_writer
"""

from __future__ import absolute_import, division, print_function

import json
import os
import shutil
import sys
import tempfile
import unittest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config.project_config import ProjectConfig
from core.shot_metadata_loader import ShotMetadataLoader


class _StubConfig(object):
    """Stand-in exposing only the shotMetadata section."""

    def __init__(self, metadata_config):
        self._metadata_config = metadata_config

    def get_shot_metadata_config(self):
        return self._metadata_config


def _metadata(parse_format, json_field='shot_info'):
    return {
        'enabled': True,
        'filenamePattern': '.{shot_id}.json',
        'location': 'shotRoot',
        'fieldMapping': {
            'frameRange': {
                'jsonField': json_field,
                'parseFormat': parse_format,
                'startField': 'start_frame',
                'endField': 'end_frame',
                'defaultStart': 1001,
                'defaultEnd': 1100,
            },
            'fps': {'jsonField': 'fps', 'default': 25.0},
        },
    }


class _TempDirCase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, '.Ep04_sq0070_SH0170.json')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, text):
        with open(self.path, 'w') as f:
            f.write(text)

    def _read(self):
        with open(self.path, 'r') as f:
            return json.load(f)


class TestNestedFormat(_TempDirCase):

    def setUp(self):
        super(TestNestedFormat, self).setUp()
        self.loader = ShotMetadataLoader(_StubConfig(_metadata('nested')))

    def test_missing_json_is_created_in_the_read_format(self):
        created = self.loader.save_frame_range(self.path, 1001, 1042, fps=25.0)

        self.assertTrue(created)
        self.assertEqual(self._read(), {
            'shot_info': {'start_frame': 1001, 'end_frame': 1042},
            'fps': 25.0,
        })
        self.assertEqual(self.loader.load_frame_range(self.path), (1001, 1042))
        self.assertEqual(self.loader.load_fps(self.path), 25.0)

    def test_existing_json_updates_only_start_and_end(self):
        self._write(json.dumps({
            'shot_name': 'SH0170',
            'shot_info': {'start_frame': 1001, 'end_frame': 1100,
                          'cut_in': 1009, 'status': 'ip'},
            'fps': 24.0,
            'tags': ['hero'],
        }))

        created = self.loader.save_frame_range(self.path, 1005, 1060, fps=30.0)

        self.assertFalse(created)
        self.assertEqual(self._read(), {
            'shot_name': 'SH0170',
            'shot_info': {'start_frame': 1005, 'end_frame': 1060,
                          'cut_in': 1009, 'status': 'ip'},
            'fps': 24.0,
            'tags': ['hero'],
        })

    def test_existing_key_order_is_kept(self):
        self._write('{"zeta": 1, "shot_info": {"end_frame": 1100, '
                    '"start_frame": 1001}, "alpha": 2}')

        self.loader.save_frame_range(self.path, 1010, 1020)

        with open(self.path, 'r') as f:
            text = f.read()
        self.assertLess(text.index('"zeta"'), text.index('"shot_info"'))
        self.assertLess(text.index('"shot_info"'), text.index('"alpha"'))
        self.assertLess(text.index('"end_frame"'), text.index('"start_frame"'))

    def test_existing_json_without_the_field_gains_it(self):
        self._write('{"fps": 24.0}')

        self.loader.save_frame_range(self.path, 1001, 1010, fps=30.0)

        self.assertEqual(self._read(), {
            'fps': 24.0,
            'shot_info': {'start_frame': 1001, 'end_frame': 1010},
        })

    def test_unreadable_json_is_left_untouched(self):
        self._write('{not json')

        with self.assertRaises(ValueError):
            self.loader.save_frame_range(self.path, 1001, 1010)

        with open(self.path, 'r') as f:
            self.assertEqual(f.read(), '{not json')

    def test_nested_field_of_wrong_type_is_rejected(self):
        self._write('{"shot_info": "1001-1100"}')

        with self.assertRaises(ValueError):
            self.loader.save_frame_range(self.path, 1001, 1010)

        self.assertEqual(self._read(), {'shot_info': '1001-1100'})

    def test_end_before_start_is_rejected(self):
        with self.assertRaises(ValueError):
            self.loader.save_frame_range(self.path, 1100, 1001)
        self.assertFalse(os.path.exists(self.path))

    def test_missing_shot_folder_is_not_created(self):
        folder = os.path.join(self.tmp, 'no_such_shot')
        path = os.path.join(folder, '.x.json')

        with self.assertRaises(IOError):
            self.loader.save_frame_range(path, 1001, 1010)
        self.assertFalse(os.path.exists(folder))

    def test_save_shot_frame_range_uses_the_configured_filename(self):
        json_path, created = self.loader.save_shot_frame_range(
            'Ep04_sq0070_SH0170', self.tmp, 1001, 1024, fps=25.0)

        self.assertTrue(created)
        self.assertEqual(os.path.normpath(json_path), os.path.normpath(self.path))
        self.assertEqual(self.loader.load_all_metadata('Ep04_sq0070_SH0170', self.tmp),
                         {'frame_range': (1001, 1024), 'fps': 25.0})


class TestOtherFormats(_TempDirCase):

    def test_range_format_round_trips(self):
        loader = ShotMetadataLoader(
            _StubConfig(_metadata('range', json_field='sequence_frames')))
        self._write('{"sequence_frames": "1001-1100", "fps": 24.0}')

        loader.save_frame_range(self.path, 1001, 1033)

        self.assertEqual(self._read(), {'sequence_frames': '1001-1033', 'fps': 24.0})
        self.assertEqual(loader.load_frame_range(self.path), (1001, 1033))

    def test_separate_format_round_trips(self):
        loader = ShotMetadataLoader(_StubConfig(_metadata('separate')))

        loader.save_frame_range(self.path, 990, 1200, fps=24.0)

        self.assertEqual(self._read(),
                         {'start_frame': 990, 'end_frame': 1200, 'fps': 24.0})
        self.assertEqual(loader.load_frame_range(self.path), (990, 1200))

    def test_no_metadata_config_is_an_error(self):
        loader = ShotMetadataLoader(_StubConfig(None))
        with self.assertRaises(ValueError):
            loader.save_frame_range(self.path, 1001, 1010)


class TestProjectConfigFormat(_TempDirCase):
    """The shipped config must write what it reads."""

    def test_default_config_round_trips(self):
        config = ProjectConfig(
            os.path.join(_PROJECT_ROOT, 'project_configs', 'ctx_config.json'))
        loader = ShotMetadataLoader(config)

        json_path, created = loader.save_shot_frame_range(
            'Ep04_sq0070_SH0170', self.tmp, 1001, 1077, fps=25.0)

        self.assertTrue(created)
        self.assertEqual(loader.load_all_metadata('Ep04_sq0070_SH0170', self.tmp),
                         {'frame_range': (1001, 1077), 'fps': 25.0})


if __name__ == '__main__':
    unittest.main()
