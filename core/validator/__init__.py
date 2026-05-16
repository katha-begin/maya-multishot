# -*- coding: utf-8 -*-
"""Scene Validator package.

Exports:
    CheckResult      -- result of a single named check
    ValidatorReport  -- aggregated results for one shot
    SceneValidator   -- orchestrator that runs all checks and returns a report

Usage::

    from core.validator import SceneValidator, ValidatorReport, CheckResult
    from config.project_config import ProjectConfig

    config = ProjectConfig('project_configs/ctx_config.json')
    validator = SceneValidator(config)
    report = validator.validate_shot(shot_node)
    if not report.passed():
        print(report.to_text())
"""

from __future__ import absolute_import, division, print_function

from core.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class CheckResult(object):
    """Result produced by a single BaseCheck.run() call.

    Attributes:
        check_name (str): Unique name of the check (e.g. 'asset_paths').
        passed (bool): True if the check found no issues.
        severity (str): 'error' | 'warning' | 'info'
        message (str): One-line human-readable summary.
        details (dict): Extra context (which files, which nodes, etc.).
    """

    def __init__(self, check_name, passed, severity, message, details=None):
        self.check_name = check_name
        self.passed = passed
        self.severity = severity
        self.message = message
        self.details = details if details is not None else {}


class ValidatorReport(object):
    """Aggregated validation results for a single shot.

    Attributes:
        shot_id (str): Human-readable shot identifier (e.g. 'Ep04_sq0070_SH0170').
        results (list[CheckResult]): All check results in run order.
    """

    def __init__(self, shot_id, results):
        self.shot_id = shot_id
        self.results = results

    def passed(self):
        """Return True if no check produced an unsatisfied error-severity result.

        Returns:
            bool
        """
        return not any(
            r.severity == 'error' and not r.passed
            for r in self.results
        )

    def errors(self):
        """Return all results that are error-severity and failed.

        Returns:
            list[CheckResult]
        """
        return [r for r in self.results if r.severity == 'error' and not r.passed]

    def warnings(self):
        """Return all results that are warning-severity and failed.

        Returns:
            list[CheckResult]
        """
        return [r for r in self.results if r.severity == 'warning' and not r.passed]

    def to_dict(self):
        """Return a JSON-serialisable representation of the report.

        Returns:
            dict
        """
        return {
            'shot_id': self.shot_id,
            'passed': self.passed(),
            'results': [
                {
                    'check_name': r.check_name,
                    'passed': r.passed,
                    'severity': r.severity,
                    'message': r.message,
                    'details': r.details,
                }
                for r in self.results
            ],
        }

    def to_text(self):
        """Return a human-readable multi-line summary.

        Returns:
            str
        """
        lines = ['Validator Report: %s' % self.shot_id]
        lines.append('Overall: %s' % ('PASSED' if self.passed() else 'FAILED'))
        lines.append('-' * 60)
        for r in self.results:
            status = 'OK' if r.passed else r.severity.upper()
            lines.append('[%s] %s: %s' % (status, r.check_name, r.message))
        return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class SceneValidator(object):
    """Orchestrates all scene validation checks against a single shot.

    Checks are run in order; exceptions from individual checks are caught and
    converted to error-severity CheckResult instances so that one broken check
    never silently aborts the rest.

    Args:
        config: ProjectConfig instance.
        platform_config: PlatformConfig instance or None.
    """

    def __init__(self, config, platform_config=None):
        self.config = config
        self.platform_config = platform_config

        # Import check classes lazily to allow the checks package to import
        # CheckResult from this module without triggering a circular import.
        from core.validator.checks import (
            CTXNodeHierarchyCheck,
            AssetPathExistsCheck,
            FrameRangeCheck,
            RendererMatchCheck,
            GafferChainCheck,
            NamespaceConflictCheck,
        )

        self._checks = [
            CTXNodeHierarchyCheck(),
            AssetPathExistsCheck(),
            FrameRangeCheck(),
            RendererMatchCheck(),
            GafferChainCheck(),
            NamespaceConflictCheck(),
        ]

    def validate_shot(self, shot_node):
        """Run all registered checks for shot_node.

        Args:
            shot_node: CTXShotNode wrapper instance OR node name string.

        Returns:
            ValidatorReport
        """
        from core.nodes.wrappers import CTXShotNode

        if isinstance(shot_node, str):
            shot_node = CTXShotNode(shot_node)

        if hasattr(shot_node, 'get_shot_id'):
            try:
                shot_id = shot_node.get_shot_id()
            except Exception:
                shot_id = str(shot_node)
        else:
            shot_id = str(shot_node)

        results = []
        for check in self._checks:
            check_name = getattr(check, 'name', type(check).__name__)
            try:
                result = check.run(shot_node, self.config, self.platform_config)
                results.append(result)
                if result.passed:
                    logger.debug('Check %s PASSED', check_name)
                else:
                    logger.debug(
                        'Check %s %s: %s',
                        check_name,
                        result.severity.upper(),
                        result.message,
                    )
            except Exception as exc:
                logger.error('Check %s raised an exception: %s', check_name, exc)
                results.append(CheckResult(
                    check_name=check_name,
                    passed=False,
                    severity='error',
                    message='Check raised exception: %s' % exc,
                    details={'exception': str(exc)},
                ))

        report = ValidatorReport(shot_id, results)
        logger.info(
            'Validation %s for shot %s (%d checks, %d errors, %d warnings)',
            'PASSED' if report.passed() else 'FAILED',
            shot_id,
            len(results),
            len(report.errors()),
            len(report.warnings()),
        )
        return report

    def validate_shot_by_code(self, ep, seq, shot):
        """Convenience wrapper: locate a shot by codes then validate it.

        Args:
            ep (str): Episode code (e.g. 'Ep04').
            seq (str): Sequence code (e.g. 'sq0070').
            shot (str): Shot code (e.g. 'SH0170').

        Returns:
            ValidatorReport
        """
        from core.nodes.wrappers import CTXShotNode

        shot_id = '%s_%s_%s' % (ep, seq, shot)
        try:
            node = CTXShotNode.find_by_code(ep, seq, shot)
        except Exception as exc:
            result = CheckResult(
                check_name='find_shot',
                passed=False,
                severity='error',
                message='Could not search for shot node: %s' % exc,
                details={'exception': str(exc)},
            )
            return ValidatorReport(shot_id, [result])

        if node is None:
            result = CheckResult(
                check_name='find_shot',
                passed=False,
                severity='error',
                message='Shot not found in scene: %s' % shot_id,
                details={},
            )
            return ValidatorReport(shot_id, [result])

        return self.validate_shot(node)

    def add_check(self, check):
        """Register an additional check at the end of the check list.

        Args:
            check: BaseCheck instance.
        """
        self._checks.append(check)

    def remove_check(self, check_name):
        """Deregister a check by its name attribute.

        Args:
            check_name (str): The ``name`` attribute of the check to remove.
        """
        self._checks = [
            c for c in self._checks
            if getattr(c, 'name', '') != check_name
        ]


__all__ = [
    'CheckResult',
    'ValidatorReport',
    'SceneValidator',
]
