# -*- coding: utf-8 -*-
"""Tests for core.validator — SceneValidator, ValidatorReport, CheckResult.

All tests run without Maya (headless).  Maya-dependent checks are expected to
return passed=True with severity='info' when MAYA_AVAILABLE is False.
"""

from __future__ import absolute_import

import json
import os
import sys
import unittest

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.validator import CheckResult, ValidatorReport, SceneValidator
from core.validator.base_check import BaseCheck


# ---------------------------------------------------------------------------
# Minimal mock objects — no Maya required
# ---------------------------------------------------------------------------

class _MockAsset(object):
    """Minimal stand-in for CTXAssetNode used in headless tests."""

    def __init__(self, asset_id='CHAR_Test_001', namespace='ns_test',
                 file_path='', extension=''):
        self._asset_id = asset_id
        self._namespace = namespace
        self._file_path = file_path
        self._extension = extension
        # Provide a node_name so checks can reference it
        self.node_name = 'CTX_Asset_' + asset_id

    def get_asset_id(self):
        return self._asset_id

    def get_namespace(self):
        return self._namespace

    def get_file_path(self):
        return self._file_path

    def get_extension(self):
        return self._extension


class _MockShotNode(object):
    """Minimal stand-in for CTXShotNode used in headless tests."""

    def __init__(self, shot_id='Ep04_sq0070_SH0170', assets=None,
                 parent_sequence='CTX_Sequence_sq0070', gaffer=None,
                 frame_range=(1001, 1100)):
        self._shot_id = shot_id
        self._assets = assets if assets is not None else []
        self._parent_sequence = parent_sequence
        self._gaffer = gaffer
        self._frame_range = frame_range
        self.node_name = 'CTX_Shot_' + shot_id

    def get_shot_id(self):
        return self._shot_id

    def get_assets(self):
        return self._assets

    def get_parent_sequence(self):
        return self._parent_sequence

    def get_gaffer(self):
        return self._gaffer

    def get_frame_range(self):
        return self._frame_range


class _MockConfig(object):
    """Minimal stand-in for ProjectConfig."""
    pass


# ---------------------------------------------------------------------------
# CheckResult
# ---------------------------------------------------------------------------

class TestCheckResult(unittest.TestCase):

    def test_check_result_fields(self):
        r = CheckResult('my_check', True, 'warning', 'All good', {'key': 'val'})
        self.assertEqual(r.check_name, 'my_check')
        self.assertTrue(r.passed)
        self.assertEqual(r.severity, 'warning')
        self.assertEqual(r.message, 'All good')
        self.assertEqual(r.details, {'key': 'val'})

    def test_check_result_default_details(self):
        r = CheckResult('x', False, 'error', 'Nope')
        self.assertEqual(r.details, {})

    def test_check_result_details_not_shared(self):
        """Each instance should get its own details dict by default."""
        r1 = CheckResult('a', True, 'info', 'msg')
        r2 = CheckResult('b', True, 'info', 'msg')
        r1.details['foo'] = 1
        self.assertNotIn('foo', r2.details)


# ---------------------------------------------------------------------------
# ValidatorReport
# ---------------------------------------------------------------------------

class TestValidatorReport(unittest.TestCase):

    def _make_report(self, errors=0, warnings=0, infos=0):
        results = []
        for i in range(errors):
            results.append(CheckResult('err_%d' % i, False, 'error', 'Error %d' % i))
        for i in range(warnings):
            results.append(CheckResult('warn_%d' % i, False, 'warning', 'Warning %d' % i))
        for i in range(infos):
            results.append(CheckResult('info_%d' % i, True, 'info', 'Info %d' % i))
        return ValidatorReport('Ep04_sq0070_SH0170', results)

    def test_validator_report_passed_no_errors(self):
        report = self._make_report(errors=0, warnings=2)
        self.assertTrue(report.passed())

    def test_validator_report_failed_with_errors(self):
        report = self._make_report(errors=1)
        self.assertFalse(report.passed())

    def test_validator_report_passed_only_infos(self):
        report = self._make_report(infos=3)
        self.assertTrue(report.passed())

    def test_validator_report_errors_filter(self):
        report = self._make_report(errors=2, warnings=1)
        self.assertEqual(len(report.errors()), 2)

    def test_validator_report_warnings_filter(self):
        report = self._make_report(errors=1, warnings=3)
        self.assertEqual(len(report.warnings()), 3)

    def test_validator_report_to_dict_is_json_serializable(self):
        report = self._make_report(errors=1, warnings=1, infos=1)
        d = report.to_dict()
        # Must not raise
        serialized = json.dumps(d)
        self.assertIsInstance(serialized, str)

    def test_validator_report_to_dict_structure(self):
        report = self._make_report(errors=1)
        d = report.to_dict()
        self.assertIn('shot_id', d)
        self.assertIn('passed', d)
        self.assertIn('results', d)
        self.assertIsInstance(d['results'], list)
        self.assertEqual(d['passed'], False)

    def test_validator_report_to_text_contains_shot_id(self):
        report = self._make_report(errors=1)
        text = report.to_text()
        self.assertIn('Ep04_sq0070_SH0170', text)

    def test_validator_report_to_text_contains_overall_status(self):
        report_fail = self._make_report(errors=1)
        self.assertIn('FAILED', report_fail.to_text())

        report_pass = self._make_report()
        self.assertIn('PASSED', report_pass.to_text())

    def test_validator_report_to_text_lists_checks(self):
        report = self._make_report(errors=1, warnings=1)
        text = report.to_text()
        self.assertIn('ERROR', text)
        self.assertIn('WARNING', text)


# ---------------------------------------------------------------------------
# AssetPathExistsCheck (headless — works without Maya)
# ---------------------------------------------------------------------------

class TestAssetPathCheck(unittest.TestCase):

    def _run_check(self, assets):
        from core.validator.checks.asset_paths import AssetPathExistsCheck
        shot = _MockShotNode(assets=assets)
        check = AssetPathExistsCheck()
        return check.run(shot, _MockConfig())

    def test_asset_path_check_passes_when_paths_exist(self, tmp_path=None):
        """Pass when all file paths exist on disk."""
        if tmp_path is None:
            import tempfile, shutil
            tmp_dir = tempfile.mkdtemp()
            try:
                tmp_file = os.path.join(tmp_dir, 'test_asset.abc')
                with open(tmp_file, 'w') as f:
                    f.write('mock')
                assets = [_MockAsset(file_path=tmp_file)]
                result = self._run_check(assets)
                self.assertTrue(result.passed)
                self.assertEqual(result.details['missing_files'], [])
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)
        else:
            tmp_file = str(tmp_path / 'asset.abc')
            with open(tmp_file, 'w') as f:
                f.write('mock')
            assets = [_MockAsset(file_path=tmp_file)]
            result = self._run_check(assets)
            self.assertTrue(result.passed)

    def test_asset_path_check_fails_missing_file(self):
        assets = [_MockAsset(file_path='/nonexistent/path/asset.abc')]
        result = self._run_check(assets)
        self.assertFalse(result.passed)
        self.assertEqual(len(result.details['missing_files']), 1)

    def test_asset_path_check_fails_unresolved_token(self):
        assets = [_MockAsset(file_path='$projRoot/SWA/asset.abc')]
        result = self._run_check(assets)
        self.assertFalse(result.passed)
        self.assertEqual(len(result.details['unresolved_tokens']), 1)
        self.assertEqual(len(result.details['missing_files']), 0)

    def test_asset_path_check_empty_path_counts_as_unresolved(self):
        assets = [_MockAsset(file_path='')]
        result = self._run_check(assets)
        self.assertFalse(result.passed)
        self.assertEqual(len(result.details['unresolved_tokens']), 1)

    def test_asset_path_check_passes_with_no_assets(self):
        result = self._run_check([])
        self.assertTrue(result.passed)
        self.assertEqual(result.details['asset_count'], 0)

    def test_asset_path_check_severity_is_error(self):
        from core.validator.checks.asset_paths import AssetPathExistsCheck
        self.assertEqual(AssetPathExistsCheck.severity, 'error')


# ---------------------------------------------------------------------------
# NamespaceConflictCheck (headless)
# ---------------------------------------------------------------------------

class TestNamespaceCheck(unittest.TestCase):

    def _run_check(self, assets):
        from core.validator.checks.namespace import NamespaceConflictCheck
        shot = _MockShotNode(assets=assets)
        check = NamespaceConflictCheck()
        return check.run(shot, _MockConfig())

    def test_namespace_check_passes_unique_namespaces(self):
        assets = [
            _MockAsset(namespace='ns_charA'),
            _MockAsset(namespace='ns_charB'),
        ]
        result = self._run_check(assets)
        self.assertTrue(result.passed)
        self.assertEqual(result.details['conflicting_namespaces'], [])

    def test_namespace_check_fails_duplicate_namespace(self):
        assets = [
            _MockAsset(asset_id='CHAR_A_001', namespace='ns_shared'),
            _MockAsset(asset_id='CHAR_B_001', namespace='ns_shared'),
        ]
        result = self._run_check(assets)
        self.assertFalse(result.passed)
        self.assertIn('ns_shared', result.details['conflicting_namespaces'])

    def test_namespace_check_passes_empty_assets(self):
        result = self._run_check([])
        self.assertTrue(result.passed)

    def test_namespace_check_ignores_empty_namespace(self):
        """Empty namespace strings should not be flagged as duplicates."""
        assets = [
            _MockAsset(asset_id='CHAR_A_001', namespace=''),
            _MockAsset(asset_id='CHAR_B_001', namespace=''),
        ]
        result = self._run_check(assets)
        self.assertTrue(result.passed)


# ---------------------------------------------------------------------------
# GafferChainCheck (headless — no Maya)
# ---------------------------------------------------------------------------

class TestGafferCheck(unittest.TestCase):

    def _run_check(self, shot):
        from core.validator.checks.gaffer import GafferChainCheck
        check = GafferChainCheck()
        return check.run(shot, _MockConfig())

    def test_gaffer_check_passes_no_gaffer(self):
        shot = _MockShotNode(gaffer=None)
        result = self._run_check(shot)
        self.assertTrue(result.passed)
        self.assertIn('No gaffer', result.message)

    def test_gaffer_check_details_structure(self):
        shot = _MockShotNode(gaffer=None)
        result = self._run_check(shot)
        self.assertIn('cycles_found', result.details)
        self.assertIn('orphaned_contexts', result.details)
        self.assertIn('invalid_targets', result.details)


# ---------------------------------------------------------------------------
# Maya-dependent checks — must skip gracefully when headless
# ---------------------------------------------------------------------------

class TestHeadlessSkips(unittest.TestCase):

    def _shot(self):
        return _MockShotNode()

    def test_frame_range_check_skipped_headless(self):
        from core.validator.checks.frame_range import FrameRangeCheck, MAYA_AVAILABLE
        if MAYA_AVAILABLE:
            self.skipTest('Maya is available — headless skip not applicable')
        check = FrameRangeCheck()
        result = check.run(self._shot(), _MockConfig())
        self.assertTrue(result.passed)
        self.assertEqual(result.severity, 'info')
        self.assertIn('Skipped', result.message)

    def test_renderer_check_skipped_headless(self):
        from core.validator.checks.renderer import RendererMatchCheck, MAYA_AVAILABLE
        if MAYA_AVAILABLE:
            self.skipTest('Maya is available — headless skip not applicable')
        check = RendererMatchCheck()
        result = check.run(self._shot(), _MockConfig())
        self.assertTrue(result.passed)
        self.assertIn('Skipped', result.message)

    def test_hierarchy_check_skipped_headless(self):
        from core.validator.checks.shot_nodes import CTXNodeHierarchyCheck, MAYA_AVAILABLE
        if MAYA_AVAILABLE:
            self.skipTest('Maya is available — headless skip not applicable')
        check = CTXNodeHierarchyCheck()
        result = check.run(self._shot(), _MockConfig())
        self.assertTrue(result.passed)
        self.assertIn('Skipped', result.message)


# ---------------------------------------------------------------------------
# SceneValidator integration
# ---------------------------------------------------------------------------

class TestSceneValidator(unittest.TestCase):

    def _make_validator(self):
        return SceneValidator(_MockConfig())

    def test_scene_validator_runs_all_checks(self):
        validator = self._make_validator()
        shot = _MockShotNode()
        report = validator.validate_shot(shot)
        # Should have exactly 6 default checks
        self.assertEqual(len(report.results), 6)

    def test_scene_validator_returns_validator_report(self):
        validator = self._make_validator()
        shot = _MockShotNode()
        report = validator.validate_shot(shot)
        self.assertIsInstance(report, ValidatorReport)

    def test_scene_validator_accepts_shot_node_wrapper(self):
        validator = self._make_validator()
        shot = _MockShotNode()
        report = validator.validate_shot(shot)
        self.assertEqual(report.shot_id, 'Ep04_sq0070_SH0170')

    def test_scene_validator_add_check(self):
        validator = self._make_validator()
        initial_count = len(validator._checks)

        class _DummyCheck(BaseCheck):
            name = 'dummy'
            severity = 'info'
            def run(self, shot_node, config, platform_config=None, **kwargs):
                return CheckResult(self.name, True, self.severity, 'Dummy OK')

        validator.add_check(_DummyCheck())
        self.assertEqual(len(validator._checks), initial_count + 1)

        shot = _MockShotNode()
        report = validator.validate_shot(shot)
        self.assertEqual(len(report.results), initial_count + 1)

    def test_scene_validator_remove_check(self):
        validator = self._make_validator()
        initial_count = len(validator._checks)
        # Remove an existing check by name
        validator.remove_check('asset_paths')
        self.assertEqual(len(validator._checks), initial_count - 1)
        check_names = [c.name for c in validator._checks]
        self.assertNotIn('asset_paths', check_names)

    def test_scene_validator_exception_in_check_becomes_error_result(self):
        """A check that raises must not abort validation; it becomes an error result."""
        validator = SceneValidator(_MockConfig())

        class _BrokenCheck(BaseCheck):
            name = 'broken'
            severity = 'error'
            def run(self, shot_node, config, platform_config=None, **kwargs):
                raise RuntimeError('Intentional failure')

        validator.add_check(_BrokenCheck())
        shot = _MockShotNode()
        report = validator.validate_shot(shot)

        broken_results = [r for r in report.results if r.check_name == 'broken']
        self.assertEqual(len(broken_results), 1)
        self.assertFalse(broken_results[0].passed)
        self.assertEqual(broken_results[0].severity, 'error')

    def test_custom_check_can_be_registered(self):
        """add_check() supports registering custom BaseCheck subclasses."""

        class _CustomCheck(BaseCheck):
            name = 'custom_project_check'
            severity = 'warning'
            def run(self, shot_node, config, platform_config=None, **kwargs):
                return CheckResult(
                    self.name, True, self.severity, 'Custom check passed'
                )

        validator = self._make_validator()
        validator.add_check(_CustomCheck())
        shot = _MockShotNode()
        report = validator.validate_shot(shot)

        custom = [r for r in report.results if r.check_name == 'custom_project_check']
        self.assertEqual(len(custom), 1)
        self.assertTrue(custom[0].passed)

    def test_report_passed_property_true_when_no_errors(self):
        validator = self._make_validator()
        shot = _MockShotNode()
        report = validator.validate_shot(shot)
        # In headless mode, all Maya-dependent checks are skipped (passed=True),
        # so a clean shot with no assets and no gaffer should pass.
        # Even if frame_range is (1001, 1100), the check skips headlessly.
        self.assertTrue(report.passed())

    def test_report_passed_false_when_errors_present(self):
        """Inject a failing error check and confirm report.passed() is False."""

        class _AlwaysFailCheck(BaseCheck):
            name = 'always_fail'
            severity = 'error'
            def run(self, shot_node, config, platform_config=None, **kwargs):
                return CheckResult(self.name, False, self.severity, 'Intentional fail')

        validator = SceneValidator(_MockConfig())
        validator.add_check(_AlwaysFailCheck())
        shot = _MockShotNode()
        report = validator.validate_shot(shot)
        self.assertFalse(report.passed())


# ---------------------------------------------------------------------------
# BaseCheck
# ---------------------------------------------------------------------------

class TestBaseCheck(unittest.TestCase):

    def test_base_check_run_raises_not_implemented(self):
        check = BaseCheck()
        with self.assertRaises(NotImplementedError):
            check.run(_MockShotNode(), _MockConfig())

    def test_base_check_default_attributes(self):
        check = BaseCheck()
        self.assertEqual(check.name, '')
        self.assertEqual(check.severity, 'error')


if __name__ == '__main__':
    unittest.main()
