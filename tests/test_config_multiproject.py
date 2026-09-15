# -*- coding: utf-8 -*-
"""Tests for multi-project config: deep_merge, 'extends', and path resolution.

Runs without Maya.
"""

from __future__ import absolute_import, division, print_function

import io
import json
import os
import shutil
import sys
import tempfile
import unittest

try:
    from unittest.mock import patch
except ImportError:  # Python 2.7
    from mock import patch

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config.project_config import ProjectConfig, deep_merge
from config import config_resolver

CONFIG_DIR = os.path.join(_PROJECT_ROOT, 'project_configs')


class TestDeepMerge(unittest.TestCase):

    def test_overlay_wins_on_scalar(self):
        self.assertEqual(deep_merge({'a': 1}, {'a': 2}), {'a': 2})

    def test_keys_from_both_survive(self):
        self.assertEqual(deep_merge({'a': 1}, {'b': 2}), {'a': 1, 'b': 2})

    def test_nested_dicts_merge_recursively(self):
        base = {'roots': {'windows': {'projRoot': 'V:/', 'imgRoot': 'W:/'}}}
        overlay = {'roots': {'windows': {'projRoot': 'X:/'}}}
        merged = deep_merge(base, overlay)
        self.assertEqual(merged['roots']['windows']['projRoot'], 'X:/')
        self.assertEqual(merged['roots']['windows']['imgRoot'], 'W:/')

    def test_lists_replace_rather_than_append(self):
        """A project's dept list must be its own, not base plus its own."""
        base = {'dept': ['anim', 'lighting']}
        overlay = {'dept': ['cfx']}
        self.assertEqual(deep_merge(base, overlay)['dept'], ['cfx'])

    def test_inputs_are_not_mutated(self):
        base = {'a': {'b': 1}}
        overlay = {'a': {'c': 2}}
        deep_merge(base, overlay)
        self.assertEqual(base, {'a': {'b': 1}})
        self.assertEqual(overlay, {'a': {'c': 2}})

    def test_dict_replaces_scalar(self):
        self.assertEqual(deep_merge({'a': 1}, {'a': {'b': 2}}), {'a': {'b': 2}})


class ExtendsTestCase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _write(self, name, data):
        path = os.path.join(self.tmp, name)
        with io.open(path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(data, indent=2))
        return path

    def _minimal_base(self):
        return {
            'version': '1.0',
            'project': {'name': 'Base', 'code': 'BASE'},
            'roots': {'windows': {'projRoot': 'V:/'}},
            'staticPaths': {'sceneBase': 'all/scene'},
            'templates': {'shotRoot': '$projRoot$project'},
            'patterns': {'version': 'v###'},
        }


class TestExtends(ExtendsTestCase):

    def test_config_without_extends_loads_unchanged(self):
        path = self._write('solo.json', self._minimal_base())
        cfg = ProjectConfig(path)
        self.assertEqual(cfg.get_project_code(), 'BASE')

    def test_overlay_inherits_from_base(self):
        self._write('base.json', self._minimal_base())
        path = self._write('EGA.json', {
            'extends': 'base.json',
            'project': {'name': 'EGA', 'code': 'EGA'},
            'roots': {'windows': {'projRoot': 'X:/'}},
        })
        cfg = ProjectConfig(path)
        self.assertEqual(cfg.get_project_code(), 'EGA')
        # Inherited untouched from base
        self.assertEqual(cfg.get_template('shotRoot'), '$projRoot$project')
        self.assertEqual(cfg.get_static_path('sceneBase'), 'all/scene')

    def test_overlay_need_not_repeat_required_keys(self):
        """Validation runs on the merged result, not the overlay alone."""
        self._write('base.json', self._minimal_base())
        path = self._write('thin.json', {
            'extends': 'base.json',
            'project': {'name': 'Thin', 'code': 'THIN'},
        })
        cfg = ProjectConfig(path)   # must not raise
        self.assertEqual(cfg.get_project_code(), 'THIN')

    def test_extends_key_removed_from_data(self):
        self._write('base.json', self._minimal_base())
        path = self._write('x.json', {'extends': 'base.json'})
        self.assertNotIn('extends', ProjectConfig(path).data)

    def test_multi_level_chain(self):
        self._write('base.json', self._minimal_base())
        self._write('mid.json', {
            'extends': 'base.json',
            'staticPaths': {'sceneBase': 'mid/scene'},
        })
        path = self._write('leaf.json', {
            'extends': 'mid.json',
            'project': {'name': 'Leaf', 'code': 'LEAF'},
        })
        cfg = ProjectConfig(path)
        self.assertEqual(cfg.get_project_code(), 'LEAF')
        self.assertEqual(cfg.get_static_path('sceneBase'), 'mid/scene')

    def test_missing_parent_raises_with_useful_message(self):
        path = self._write('orphan.json', {'extends': 'nope.json'})
        with self.assertRaises(IOError) as ctx:
            ProjectConfig(path)
        self.assertIn('nope.json', str(ctx.exception))

    def test_circular_extends_raises(self):
        self._write('a.json', {'extends': 'b.json'})
        self._write('b.json', {'extends': 'a.json'})
        with self.assertRaises(ValueError) as ctx:
            ProjectConfig(os.path.join(self.tmp, 'a.json'))
        self.assertIn('Circular', str(ctx.exception))

    def test_self_referencing_extends_raises(self):
        self._write('loop.json', {'extends': 'loop.json'})
        with self.assertRaises(ValueError):
            ProjectConfig(os.path.join(self.tmp, 'loop.json'))


class TestShippedConfigs(unittest.TestCase):
    """The real configs in project_configs/ must load and stay consistent."""

    def test_default_config_loads(self):
        cfg = ProjectConfig(os.path.join(CONFIG_DIR, 'ctx_config.json'))
        self.assertEqual(cfg.get_project_code(), 'SWA')

    def test_swa_and_default_are_identical(self):
        """ctx_config.json is the default pointer at SWA -- no drift allowed."""
        default = ProjectConfig(os.path.join(CONFIG_DIR, 'ctx_config.json'))
        swa = ProjectConfig(os.path.join(CONFIG_DIR, 'SWA.json'))
        self.assertEqual(json.dumps(default.data, sort_keys=True),
                         json.dumps(swa.data, sort_keys=True))

    def test_ega_loads_with_own_identity(self):
        cfg = ProjectConfig(os.path.join(CONFIG_DIR, 'EGA.json'))
        self.assertEqual(cfg.get_project_code(), 'EGA')
        self.assertEqual(cfg.get_root('projRoot', platform='windows'), 'X:/')
        self.assertEqual(cfg.get_root('imgRoot', platform='windows'), 'Y:/')

    def test_ega_inherits_shared_templates(self):
        swa = ProjectConfig(os.path.join(CONFIG_DIR, 'SWA.json'))
        ega = ProjectConfig(os.path.join(CONFIG_DIR, 'EGA.json'))
        self.assertEqual(swa.get_templates(), ega.get_templates())

    def test_projects_differ_where_they_should(self):
        swa = ProjectConfig(os.path.join(CONFIG_DIR, 'SWA.json'))
        ega = ProjectConfig(os.path.join(CONFIG_DIR, 'EGA.json'))
        self.assertNotEqual(swa.get_project_code(), ega.get_project_code())
        self.assertNotEqual(swa.get_root('projRoot', platform='windows'),
                            ega.get_root('projRoot', platform='windows'))

    def test_base_is_not_offered_as_a_project(self):
        names = [n for n, _ in config_resolver.list_project_configs()]
        self.assertNotIn('base', names)
        self.assertIn('EGA', names)
        self.assertIn('SWA', names)


class TestResolveConfigPath(unittest.TestCase):

    def setUp(self):
        for var in (config_resolver.ENV_VAR, config_resolver.LEGACY_ENV_VAR):
            os.environ.pop(var, None)
        p = patch.object(config_resolver, 'MAYA_AVAILABLE', False)
        p.start()
        self.addCleanup(p.stop)

    def test_explicit_wins(self):
        os.environ[config_resolver.ENV_VAR] = os.path.join(
            CONFIG_DIR, 'EGA.json')
        self.assertEqual(
            config_resolver.resolve_config_path('/explicit/path.json'),
            '/explicit/path.json')

    def test_env_var_used_when_no_explicit(self):
        ega = os.path.join(CONFIG_DIR, 'EGA.json')
        os.environ[config_resolver.ENV_VAR] = ega
        self.assertEqual(config_resolver.resolve_config_path(), ega)

    def test_legacy_env_var_still_honoured(self):
        ega = os.path.join(CONFIG_DIR, 'EGA.json')
        os.environ[config_resolver.LEGACY_ENV_VAR] = ega
        self.assertEqual(config_resolver.resolve_config_path(), ega)

    def test_current_env_var_beats_legacy(self):
        os.environ[config_resolver.ENV_VAR] = os.path.join(CONFIG_DIR, 'SWA.json')
        os.environ[config_resolver.LEGACY_ENV_VAR] = os.path.join(CONFIG_DIR, 'EGA.json')
        self.assertTrue(
            config_resolver.resolve_config_path().endswith('SWA.json'))

    def test_nonexistent_env_path_is_honoured(self):
        """A typo'd CTX_CONFIG must fail loudly, not silently load another
        project against the wrong roots."""
        os.environ[config_resolver.ENV_VAR] = '/does/not/exist.json'
        self.assertEqual(config_resolver.resolve_config_path(),
                         '/does/not/exist.json')

    def test_falls_back_to_repo_default(self):
        self.assertEqual(config_resolver.resolve_config_path(),
                         config_resolver.get_default_config_path())

    def test_env_var_reachable_via_find_config(self):
        """Regression: the env var used to be listed after the repo path,
        so find_config() could never return it."""
        ega = os.path.join(CONFIG_DIR, 'EGA.json')
        os.environ[config_resolver.ENV_VAR] = ega
        self.assertEqual(ProjectConfig.find_config(), ega)


class TestSceneBoundResolution(unittest.TestCase):

    def setUp(self):
        for var in (config_resolver.ENV_VAR, config_resolver.LEGACY_ENV_VAR):
            os.environ.pop(var, None)

    def _mock_cmds(self, config_path, ctx_type='CTX_Manager'):
        class MockCmds(object):
            def ls(self, **kwargs):
                return ['CTX_Manager']

            def attributeQuery(self, attr, **kwargs):
                return attr in ('ctx_type', 'config_path')

            def getAttr(self, plug):
                if plug.endswith('.ctx_type'):
                    return ctx_type
                return config_path
        return MockCmds()

    def test_scene_config_wins_over_env(self):
        ega = os.path.join(CONFIG_DIR, 'EGA.json')
        os.environ[config_resolver.ENV_VAR] = os.path.join(CONFIG_DIR, 'SWA.json')
        with patch.object(config_resolver, 'MAYA_AVAILABLE', True), \
             patch.object(config_resolver, 'cmds', self._mock_cmds(ega)):
            self.assertEqual(config_resolver.resolve_config_path(), ega)

    def test_use_scene_false_skips_scene(self):
        ega = os.path.join(CONFIG_DIR, 'EGA.json')
        with patch.object(config_resolver, 'MAYA_AVAILABLE', True), \
             patch.object(config_resolver, 'cmds', self._mock_cmds(ega)):
            self.assertEqual(
                config_resolver.resolve_config_path(use_scene=False),
                config_resolver.get_default_config_path())

    def test_missing_scene_config_falls_through(self):
        with patch.object(config_resolver, 'MAYA_AVAILABLE', True), \
             patch.object(config_resolver, 'cmds',
                          self._mock_cmds('/gone/missing.json')):
            self.assertEqual(config_resolver.resolve_config_path(),
                             config_resolver.get_default_config_path())

    def test_non_manager_node_ignored(self):
        ega = os.path.join(CONFIG_DIR, 'EGA.json')
        with patch.object(config_resolver, 'MAYA_AVAILABLE', True), \
             patch.object(config_resolver, 'cmds',
                          self._mock_cmds(ega, ctx_type='CTX_Shot')):
            self.assertEqual(config_resolver.resolve_config_path(),
                             config_resolver.get_default_config_path())


class TestSceneProjectDetection(unittest.TestCase):
    """A scene path already encodes its project via projRoot + project."""

    SWA_SCENE = 'V:/SWA/all/scene/Ep04/sq0070/SH0140/lighting/version/a.ma'
    EGA_SCENE = 'X:/EGA/all/scene/Ep02/sq0220/SH1350/cfx/version/b.ma'

    def _detect(self, scene):
        return config_resolver.detect_config_from_scene(scene)

    def test_swa_scene_detects_swa(self):
        got = self._detect(self.SWA_SCENE)
        self.assertIsNotNone(got)
        self.assertEqual(ProjectConfig(got).get_project_code(), 'SWA')

    def test_ega_scene_detects_ega(self):
        got = self._detect(self.EGA_SCENE)
        self.assertIsNotNone(got)
        self.assertEqual(ProjectConfig(got).get_project_code(), 'EGA')

    def test_backslash_scene_path(self):
        got = self._detect(self.EGA_SCENE.replace('/', '\\'))
        self.assertIsNotNone(got)
        self.assertEqual(ProjectConfig(got).get_project_code(), 'EGA')

    def test_unrelated_path_detects_nothing(self):
        self.assertIsNone(self._detect('C:/temp/scratch/untitled.ma'))

    def test_empty_scene_detects_nothing(self):
        self.assertIsNone(self._detect(''))

    def test_right_drive_wrong_project_detects_nothing(self):
        self.assertIsNone(self._detect('V:/OTHER/all/scene/Ep01/x.ma'))

    def test_project_prefix_shape(self):
        cfg = ProjectConfig(os.path.join(CONFIG_DIR, 'EGA.json'))
        self.assertEqual(config_resolver.get_project_prefix(cfg),
                         'X:/EGA/all/scene/')

    def test_unloadable_config_does_not_break_detection(self):
        """One malformed config must not abort the whole scan."""
        broken = os.path.join(CONFIG_DIR, 'ZZBROKEN.json')
        with io.open(broken, 'w', encoding='utf-8') as f:
            f.write(u'{ not valid json')
        try:
            got = self._detect(self.EGA_SCENE)
            self.assertIsNotNone(got)
            self.assertEqual(ProjectConfig(got).get_project_code(), 'EGA')
        finally:
            os.remove(broken)


class TestDetectionInResolutionOrder(unittest.TestCase):

    EGA_SCENE = 'X:/EGA/all/scene/Ep02/sq0220/SH1350/cfx/version/b.ma'

    def setUp(self):
        for var in (config_resolver.ENV_VAR, config_resolver.LEGACY_ENV_VAR):
            os.environ.pop(var, None)

    def _patch_scene(self, scene_path, bound=None):
        class MockCmds(object):
            def ls(self, **kwargs):
                return ['CTX_Manager'] if bound else []

            def attributeQuery(self, attr, **kwargs):
                return attr in ('ctx_type', 'config_path')

            def getAttr(self, plug):
                if plug.endswith('.ctx_type'):
                    return 'CTX_Manager'
                return bound

            def file(self, **kwargs):
                return scene_path
        return MockCmds()

    def test_detection_beats_env_var(self):
        """A session launched for SWA must still open an EGA scene as EGA."""
        os.environ[config_resolver.ENV_VAR] = os.path.join(CONFIG_DIR, 'SWA.json')
        with patch.object(config_resolver, 'MAYA_AVAILABLE', True), \
             patch.object(config_resolver, 'cmds', self._patch_scene(self.EGA_SCENE)):
            resolved = config_resolver.resolve_config_path()
        self.assertEqual(ProjectConfig(resolved).get_project_code(), 'EGA')

    def test_explicit_scene_binding_beats_detection(self):
        swa = os.path.join(CONFIG_DIR, 'SWA.json')
        with patch.object(config_resolver, 'MAYA_AVAILABLE', True), \
             patch.object(config_resolver, 'cmds',
                          self._patch_scene(self.EGA_SCENE, bound=swa)):
            resolved = config_resolver.resolve_config_path()
        self.assertEqual(resolved, swa)

    def test_legacy_default_binding_loses_to_detection(self):
        """Old versions stamped ctx_config.json on every scene, EGA included."""
        legacy = os.path.join(CONFIG_DIR, 'ctx_config.json')
        with patch.object(config_resolver, 'MAYA_AVAILABLE', True), \
             patch.object(config_resolver, 'cmds',
                          self._patch_scene(self.EGA_SCENE, bound=legacy)):
            resolved = config_resolver.resolve_config_path()
        self.assertEqual(ProjectConfig(resolved).get_project_code(), 'EGA')

    def test_legacy_default_binding_kept_when_nothing_detected(self):
        legacy = os.path.join(CONFIG_DIR, 'ctx_config.json')
        os.environ[config_resolver.ENV_VAR] = os.path.join(CONFIG_DIR, 'EGA.json')
        with patch.object(config_resolver, 'MAYA_AVAILABLE', True), \
             patch.object(config_resolver, 'cmds',
                          self._patch_scene('C:/tmp/untitled.ma', bound=legacy)):
            self.assertEqual(config_resolver.resolve_config_path(), legacy)

    def test_is_default_binding(self):
        self.assertTrue(config_resolver.is_default_binding(
            'X:/EGA/_temp/tool/project_configs/CTX_CONFIG.json'))
        self.assertFalse(config_resolver.is_default_binding(
            os.path.join(CONFIG_DIR, 'SWA.json')))
        self.assertFalse(config_resolver.is_default_binding(''))

    def test_env_used_when_scene_matches_nothing(self):
        ega = os.path.join(CONFIG_DIR, 'EGA.json')
        os.environ[config_resolver.ENV_VAR] = ega
        with patch.object(config_resolver, 'MAYA_AVAILABLE', True), \
             patch.object(config_resolver, 'cmds',
                          self._patch_scene('C:/tmp/untitled.ma')):
            self.assertEqual(config_resolver.resolve_config_path(), ega)

    def test_use_scene_false_skips_detection(self):
        with patch.object(config_resolver, 'MAYA_AVAILABLE', True), \
             patch.object(config_resolver, 'cmds', self._patch_scene(self.EGA_SCENE)):
            self.assertEqual(
                config_resolver.resolve_config_path(use_scene=False),
                config_resolver.get_default_config_path())

    def test_unsaved_scene_falls_back_to_default(self):
        with patch.object(config_resolver, 'MAYA_AVAILABLE', True), \
             patch.object(config_resolver, 'cmds', self._patch_scene('')):
            self.assertEqual(config_resolver.resolve_config_path(),
                             config_resolver.get_default_config_path())


if __name__ == '__main__':
    unittest.main()
