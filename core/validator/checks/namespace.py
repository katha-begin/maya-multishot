# -*- coding: utf-8 -*-
"""Namespace conflict check.

No two CTX_Asset nodes on the same shot may share the same namespace string.
Works fully headless.
"""

from __future__ import absolute_import

from core.logging_config import get_logger
from core.validator.base_check import BaseCheck

logger = get_logger(__name__)


class NamespaceConflictCheck(BaseCheck):
    """Verify that all assets on a shot have unique namespace values.

    Duplicate namespaces cause reference load failures or silent data
    corruption when the pipeline tries to apply per-shot settings.

    Severity: error -- duplicate namespaces will cause reference issues.
    Works headless (no Maya dependency).
    """

    name = 'namespace_conflict'
    severity = 'error'

    def run(self, shot_node, config, platform_config=None, **kwargs):
        from core.validator import CheckResult

        try:
            assets = shot_node.get_assets()
        except Exception as exc:
            logger.debug('get_assets raised: %s', exc)
            assets = []

        namespace_counts = {}
        for asset in assets:
            try:
                ns = asset.get_namespace()
            except Exception as exc:
                logger.debug('get_namespace raised for %s: %s', asset, exc)
                ns = ''

            if not ns:
                continue

            namespace_counts[ns] = namespace_counts.get(ns, 0) + 1

        conflicting = [ns for ns, count in namespace_counts.items() if count > 1]

        if conflicting:
            logger.debug('Namespace conflicts found: %s', conflicting)

        passed = len(conflicting) == 0
        if passed:
            msg = 'All asset namespaces are unique'
        else:
            msg = 'Duplicate namespaces found: %s' % ', '.join(conflicting)

        return CheckResult(
            check_name=self.name,
            passed=passed,
            severity=self.severity,
            message=msg,
            details={
                'conflicting_namespaces': conflicting,
            },
        )
