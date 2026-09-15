# -*- coding: utf-8 -*-
"""CFX groom standins follow the active shot (core/groom_updater.py).

A fake cmds holds the scene; the publish folders are real, in a temp dir.
Plain unittest, so it also runs under Maya's Python 2.7:
    mayapy2 -m unittest tests.test_groom_updater
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
from core import cfx_adopter, groom_updater
from core.nodes import nodes_legacy

EGA_CONFIG = os.path.join(_PROJECT_ROOT, 'project_configs', 'EGA.json')
SWA_CONFIG = os.path.join(_PROJECT_ROOT, 'project_configs', 'SWA.json')


class _FakeCmds(object):
    """Standins: shape -> dso; parents: node -> parent; plus visibility."""

    def __init__(self):
        self.dso = {}
        self.parents = {}
        self.visibility = {}
        self.locked = set()
        self.frame_offset = {}
        self.set_calls = []

    def add_standin(self, shape, dso, visible=True):
        transform = shape[:-len('Shape')] if shape.endswith('Shape') else shape + '_xform'
        self.dso[shape] = dso
        self.parents[shape] = transform
        self.parents[transform] = 'Cfx_Grp'
        self.visibility[transform] = visible
        return transform

    def ls(self, type=None, **kwargs):
        return sorted(self.dso) if type == 'aiStandIn' else []

    def objExists(self, name):
        node = name.split('.', 1)[0]
        return node in self.dso or node in self.parents

    def listRelatives(self, node, parent=False, fullPath=False, **kwargs):
        return [self.parents[node]] if parent and node in self.parents else None

    def attributeQuery(self, attr, node=None, exists=False):
        return attr == 'frameOffset' and node in self.frame_offset

    def getAttr(self, plug, settable=False):
        node, attr = plug.split('.', 1)
        if attr == 'visibility':
            if settable:
                return node not in self.locked
            return self.visibility[node]
        if attr == 'frameOffset':
            return self.frame_offset[node]
        return self.dso[node]

    def setAttr(self, plug, value, **kwargs):
        node, attr = plug.split('.', 1)
        self.set_calls.append((plug, value))
        if attr == 'visibility':
            self.visibility[node] = bool(value)
        else:
            self.dso[node] = value


class _Shot(object):
    def __init__(self, shot, start=1001, end=1010):
        self._shot, self._range = shot, (start, end)
        self.node_name = 'CTX_Shot_Ep02_sq0570_{}'.format(shot)

    def get_ep_code(self):
        return 'Ep02'

    def get_seq_code(self):
        return 'sq0570'

    def get_shot_code(self):
        return self._shot

    def get_frame_range(self):
        return self._range


def _write(path, size):
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    with io.open(path, 'wb') as fh:
        fh.write(b'x' * size)


class GroomUpdaterTestBase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = self.tmp.replace('\\', '/') + '/'
        self.config = ProjectConfig(EGA_CONFIG)
        for platform in self.config.data['roots']:
            self.config.data['roots'][platform]['projRoot'] = self.root

        self.cmds = _FakeCmds()
        self._saved = (cfx_adopter.cmds, cfx_adopter.MAYA_AVAILABLE,
                       groom_updater.cmds, groom_updater.MAYA_AVAILABLE)
        cfx_adopter.cmds = groom_updater.cmds = self.cmds
        cfx_adopter.MAYA_AVAILABLE = groom_updater.MAYA_AVAILABLE = True

    def tearDown(self):
        (cfx_adopter.cmds, cfx_adopter.MAYA_AVAILABLE,
         groom_updater.cmds, groom_updater.MAYA_AVAILABLE) = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def publish(self, shot, groom, version, frames=range(1001, 1011), sizes=None):
        """Create a groom sequence; returns its #### frame path."""
        basename = 'Ep02_sq0570_{}__CFX_{}'.format(shot, groom)
        seq_dir = '{}EGA/all/scene/Ep02/sq0570/{}/cfx/publish/{}/{}_ass'.format(
            self.root, shot, version, basename)
        sizes = sizes or {}
        for frame in frames:
            _write('{}/{}.{:04d}.ass'.format(seq_dir, basename, frame), sizes.get(frame, 100))
        return '{}/{}.####.ass'.format(seq_dir, basename)


class TestFrameCheck(GroomUpdaterTestBase):

    def test_reports_missing_empty_and_small_frames(self):
        path = self.publish('SH5660', 'botgroomthornby001', 'v004',
                            frames=[f for f in range(1001, 1011) if f != 1004],
                            sizes={1006: 0, 1008: 1})
        check = groom_updater.check_frames(
            os.path.dirname(path), 'Ep02_sq0570_SH5660__CFX_botgroomthornby001', 'ass', 1001, 1010)
        self.assertEqual(check['count'], 10)
        self.assertEqual(check['missing'], [1004])
        self.assertEqual(check['empty'], [1006])
        self.assertEqual(check['small'], [1008])
        self.assertIsNone(check['error'])

    def test_frames_outside_the_range_do_not_count(self):
        path = self.publish('SH5660', 'botgroomthornby001', 'v004', frames=range(1001, 1006))
        check = groom_updater.check_frames(
            os.path.dirname(path), 'Ep02_sq0570_SH5660__CFX_botgroomthornby001', 'ass', 1003, 1007)
        self.assertEqual(check['missing'], [1006, 1007])

    def test_unreadable_folder_is_an_error_not_a_crash(self):
        check = groom_updater.check_frames(os.path.join(self.tmp, 'nope'), 'x', 'ass', 1, 2)
        self.assertTrue(check['error'])

    def test_format_frames_compacts_runs(self):
        self.assertEqual(groom_updater.format_frames([1010, 1001, 1002, 1003, 1005]),
                         '1001-1003, 1005, 1010')


class TestUpdateGrooms(GroomUpdaterTestBase):

    def setUp(self):
        super(TestUpdateGrooms, self).setUp()
        self.thornby_5630 = self.publish('SH5630', 'botgroomthornby001', 'v002')
        self.publish('SH5660', 'botgroomthornby001', 'v003')
        self.thornby_5660_v4 = self.publish(
            'SH5660', 'botgroomthornby001', 'v004',
            frames=[f for f in range(1001, 1011) if f != 1004])
        self.keeper_5670 = self.publish('SH5670', 'botgroomTimekeeperS001', 'v002')

        self.thornby = self.cmds.add_standin(
            'Ep02_sq0570_SH5630__CFX_botgroomthornby001_aiStandInShape', self.thornby_5630)
        self.keeper = self.cmds.add_standin(
            'Ep02_sq0570_SH5670__CFX_botgroomTimekeeperS001_aiStandInShape', self.keeper_5670)
        self.cmds.add_standin('SETS_IntTSODShape', 'X:/EGA/all/asset/Sets/IntTSOD.ass')

    def test_switch_points_groom_at_latest_version_of_new_shot(self):
        summary = groom_updater.update_grooms_for_shot(self.config, _Shot('SH5660'))

        shape = 'Ep02_sq0570_SH5630__CFX_botgroomthornby001_aiStandInShape'
        self.assertEqual(self.cmds.dso[shape], self.thornby_5660_v4)
        self.assertTrue(self.cmds.visibility[self.thornby])
        self.assertEqual(summary[groom_updater.ACTION_UPDATE], 1)

    def test_groom_not_published_for_shot_is_hidden_and_left_alone(self):
        groom_updater.update_grooms_for_shot(self.config, _Shot('SH5660'))

        shape = 'Ep02_sq0570_SH5670__CFX_botgroomTimekeeperS001_aiStandInShape'
        self.assertEqual(self.cmds.dso[shape], self.keeper_5670)
        self.assertFalse(self.cmds.visibility[self.keeper])

    def test_non_cfx_standins_are_untouched(self):
        groom_updater.update_grooms_for_shot(self.config, _Shot('SH5660'))
        self.assertEqual(self.cmds.dso['SETS_IntTSODShape'], 'X:/EGA/all/asset/Sets/IntTSOD.ass')
        self.assertNotIn('SETS_IntTSOD.visibility', [p for p, _ in self.cmds.set_calls])

    def test_frame_problems_are_reported(self):
        summary = groom_updater.update_grooms_for_shot(self.config, _Shot('SH5660'))
        self.assertEqual(len(summary['problems']), 1)
        groom, text = summary['problems'][0]
        self.assertEqual(groom, 'CFX_botgroomthornby001')
        self.assertIn('1004', text)

    def test_switching_back_restores_path_and_visibility(self):
        groom_updater.update_grooms_for_shot(self.config, _Shot('SH5660'))
        groom_updater.update_grooms_for_shot(self.config, _Shot('SH5670'))
        self.assertFalse(self.cmds.visibility[self.thornby])
        self.assertTrue(self.cmds.visibility[self.keeper])

        groom_updater.update_grooms_for_shot(self.config, _Shot('SH5630'))
        shape = 'Ep02_sq0570_SH5630__CFX_botgroomthornby001_aiStandInShape'
        self.assertEqual(self.cmds.dso[shape], self.thornby_5630)
        self.assertTrue(self.cmds.visibility[self.thornby])

    def test_path_already_on_shot_is_not_rewritten(self):
        del self.cmds.set_calls[:]
        summary = groom_updater.update_grooms_for_shot(self.config, _Shot('SH5630'))
        dso_writes = [p for p, _ in self.cmds.set_calls if p.endswith('.dso')]
        self.assertEqual(dso_writes, [])
        self.assertEqual(summary[groom_updater.ACTION_CURRENT], 1)

    def test_version_already_chosen_on_the_shot_is_kept(self):
        shape = 'Ep02_sq0570_SH5630__CFX_botgroomthornby001_aiStandInShape'
        v3 = self.thornby_5660_v4.replace('/v004/', '/v003/')
        self.cmds.dso[shape] = v3
        groom_updater.update_grooms_for_shot(self.config, _Shot('SH5660'))
        self.assertEqual(self.cmds.dso[shape], v3)

    def test_plan_lists_versions_newest_first_and_picks_one(self):
        items = groom_updater.plan_grooms(self.config, _Shot('SH5660'))
        thornby = [i for i in items if i['groom'] == 'CFX_botgroomthornby001'][0]
        self.assertEqual(thornby['versions'], ['v004', 'v003'])
        self.assertIn('/v003/', groom_updater.target_path(thornby, 'v003'))
        groom_updater.apply_item(thornby, 'v003')
        self.assertIn('/v003/', self.cmds.dso[thornby['shape']])

    def test_duplicate_standin_of_same_groom_is_hidden(self):
        self.publish('SH5660', 'botgroomthornby001', 'v004')
        second = self.cmds.add_standin(
            'Ep02_sq0570_SH5660__CFX_botgroomthornby001_aiStandInShape', self.thornby_5660_v4)

        summary = groom_updater.update_grooms_for_shot(self.config, _Shot('SH5660'))

        first = 'Ep02_sq0570_SH5630__CFX_botgroomthornby001_aiStandInShape'
        self.assertEqual(self.cmds.dso[first], self.thornby_5630)
        self.assertFalse(self.cmds.visibility[self.thornby])
        self.assertTrue(self.cmds.visibility[second])
        self.assertEqual(summary[groom_updater.ACTION_DUPLICATE], 1)

    def test_frame_offset_shifts_the_checked_range(self):
        shape = 'Ep02_sq0570_SH5630__CFX_botgroomthornby001_aiStandInShape'
        self.cmds.frame_offset[shape] = 5
        items = groom_updater.plan_grooms(self.config, _Shot('SH5630'))
        thornby = [i for i in items if i['shape'] == shape][0]
        check = groom_updater.check_item_frames(thornby)
        self.assertEqual(check['missing'], list(range(1011, 1016)))

    def test_locked_visibility_is_skipped_without_error(self):
        self.cmds.locked.add(self.keeper)
        summary = groom_updater.update_grooms_for_shot(self.config, _Shot('SH5660'))
        self.assertTrue(self.cmds.visibility[self.keeper])
        self.assertEqual(summary['total'], 2)


class TestShotSwitchHook(GroomUpdaterTestBase):

    def test_project_flag(self):
        self.assertTrue(self.config.is_cfx_repath_on_shot_switch())
        self.assertFalse(ProjectConfig(SWA_CONFIG).is_cfx_repath_on_shot_switch())

    def _run_update_shot_paths(self, config, assets):
        calls = []
        saved = groom_updater.update_grooms_for_shot
        groom_updater.update_grooms_for_shot = lambda cfg, shot: calls.append(shot) or {'total': 0}
        manager = nodes_legacy.NodeManager()
        manager.get_assets_for_shot = lambda shot: assets
        updated = []
        manager.update_asset_path = lambda asset, *a: updated.append(asset) or True
        try:
            manager.update_shot_paths(_Shot('SH5660'), config, None)
        finally:
            groom_updater.update_grooms_for_shot = saved
        return manager, calls, updated

    def test_update_shot_paths_runs_groom_update_when_enabled(self):
        manager, calls, _ = self._run_update_shot_paths(self.config, [])
        self.assertEqual(len(calls), 1)
        self.assertEqual(manager.last_groom_summary, {'total': 0})

    def test_update_shot_paths_skips_groom_update_when_disabled(self):
        _, calls, _ = self._run_update_shot_paths(ProjectConfig(SWA_CONFIG), [])
        self.assertEqual(calls, [])

    def test_cfx_assets_are_left_to_the_groom_update(self):
        class Asset(object):
            def __init__(self, asset_type, ns):
                self.asset_type, self.ns, self.node_name = asset_type, ns, ns

            def get_asset_type(self):
                return self.asset_type

            def get_namespace(self):
                return self.ns

            def get_department(self):
                return 'anim'

        char = Asset('CHAR', 'CHAR_thornby_001')
        cfx = Asset('CFX', 'CFX_botgroomthornby_001')
        _, _, updated = self._run_update_shot_paths(self.config, [char, cfx])
        self.assertEqual(updated, [char])

        _, _, updated = self._run_update_shot_paths(ProjectConfig(SWA_CONFIG), [char, cfx])
        self.assertEqual(updated, [char, cfx])


if __name__ == '__main__':
    unittest.main()
