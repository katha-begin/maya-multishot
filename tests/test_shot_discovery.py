# -*- coding: utf-8 -*-
"""Tests for core.shot_discovery -- the Add Shots dialog's project listing.

Plain unittest with no mock, so it also runs under Maya's Python 2.7:
    mayapy2 -m unittest tests.test_shot_discovery
"""

from __future__ import absolute_import, division, print_function

import io
import os
import shutil
import sys
import tempfile
import unittest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config.project_config import ProjectConfig
from core import shot_discovery

CONFIG_DIR = os.path.join(_PROJECT_ROOT, 'project_configs')


class TestListProjects(unittest.TestCase):

    def test_repository_lists_every_project_once(self):
        """SWA must stay listed next to EGA; ctx_config.json is not a project."""
        projects = shot_discovery.list_projects()

        self.assertEqual([p['code'] for p in projects], ['EGA', 'SWA'])
        by_code = dict((p['code'], p) for p in projects)
        self.assertEqual(os.path.basename(by_code['SWA']['config_path']), 'SWA.json')
        self.assertEqual(os.path.basename(by_code['EGA']['config_path']), 'EGA.json')
        self.assertTrue(all(p['error'] is None for p in projects))

    def test_project_file_beats_pointer_in_either_order(self):
        swa = os.path.join(CONFIG_DIR, 'SWA.json')
        pointer = os.path.join(CONFIG_DIR, 'ctx_config.json')
        for order in ([pointer, swa], [swa, pointer]):
            projects = shot_discovery.list_projects(order)
            self.assertEqual(len(projects), 1)
            self.assertEqual(os.path.basename(projects[0]['config_path']), 'SWA.json')

    def test_unloadable_config_is_reported_not_dropped(self):
        tmp = tempfile.mkdtemp()
        try:
            broken = os.path.join(tmp, 'BROKEN.json')
            with io.open(broken, 'w', encoding='utf-8') as f:
                f.write(u'{"extends": "missing_base.json"}')

            projects = shot_discovery.list_projects(
                [os.path.join(CONFIG_DIR, 'SWA.json'), broken])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        by_code = dict((p['code'], p) for p in projects)
        self.assertIsNone(by_code['SWA']['error'])
        self.assertIsNone(by_code['BROKEN']['config'])
        self.assertIn('missing_base.json', by_code['BROKEN']['error'])


class TestSceneBase(unittest.TestCase):

    def test_roots_follow_the_platform(self):
        ega = ProjectConfig(os.path.join(CONFIG_DIR, 'EGA.json'))
        swa = ProjectConfig(os.path.join(CONFIG_DIR, 'SWA.json'))

        def norm(path):
            return path.replace('\\', '/')

        self.assertEqual(norm(shot_discovery.get_scene_base(ega, 'windows')),
                         'X:/EGA/all/scene')
        self.assertEqual(norm(shot_discovery.get_scene_base(ega, 'linux')),
                         '/mnt/igloo_ega_x/EGA/all/scene')
        self.assertEqual(norm(shot_discovery.get_scene_base(swa, 'windows')),
                         'V:/SWA/all/scene')
        self.assertEqual(norm(shot_discovery.get_scene_base(swa, 'linux')),
                         '/mnt/igloo_swa_v/SWA/all/scene')


class TestDiscoverShots(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        for rel in ('Ep02/sq0210/SH1180', 'Ep02/sq0210/SH1170', 'Ep02/sq0211/SH0010',
                    'Ep02/Media/SH9999', 'Ep02/sq0220', 'ep01/sq0010/SH0010',
                    'Assets/sq0001/SH0001', 'Ep02/sq0210/notes'):
            os.makedirs(os.path.join(self.tmp, *rel.split('/')))
        with io.open(os.path.join(self.tmp, 'Ep02', 'sq0210', 'SH0001.txt'), 'w') as f:
            f.write(u'file, not a shot folder')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_walks_episode_sequence_shot_with_the_dialog_filters(self):
        self.assertEqual(shot_discovery.discover_shots(self.tmp), [
            ('Ep02', [('sq0210', ['SH1170', 'SH1180']),
                      ('sq0211', ['SH0010']),
                      ('sq0220', [])]),
            ('ep01', [('sq0010', ['SH0010'])]),
        ])

    def test_missing_folder_gives_nothing(self):
        self.assertEqual(
            shot_discovery.discover_shots(os.path.join(self.tmp, 'nope')), [])
        self.assertEqual(shot_discovery.discover_shots(None), [])


if __name__ == '__main__':
    unittest.main()
