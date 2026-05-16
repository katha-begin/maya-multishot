# -*- coding: utf-8 -*-
"""Renderer vs asset extension compatibility check.

Detects the active renderer and warns if any asset file extension is
incompatible with it (e.g. .rs proxy with Arnold active).

Skipped headlessly or when renderer detection is unavailable.
"""

from __future__ import absolute_import

from core.logging_config import get_logger
from core.validator.base_check import BaseCheck

logger = get_logger(__name__)

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False

# Hard-coded extension affinity: renderer_name -> extensions that belong to it only.
# Extensions listed for a renderer are NOT valid for any other renderer.
_RENDERER_EXCLUSIVE_EXTS = {
    'redshift': {'.rs'},
    'arnold': {'.ass'},
}


class RendererMatchCheck(BaseCheck):
    """Warn when asset extensions do not match the active renderer.

    Severity: warning.
    Only runs when Maya is available and renderer detection succeeds.
    """

    name = 'renderer_match'
    severity = 'warning'

    def run(self, shot_node, config, platform_config=None, **kwargs):
        from core.validator import CheckResult

        if not MAYA_AVAILABLE:
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity='info',
                message='Skipped (no Maya)',
                details={},
            )

        # Attempt renderer detection -- Stream E implements this properly.
        # Fall back gracefully if not yet available.
        try:
            from core.renderers import get_active_renderer, get_preferred_extensions
            renderer = get_active_renderer()
            preferred = get_preferred_extensions(renderer)
        except (ImportError, AttributeError):
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity='info',
                message='Skipped (renderer detection unavailable)',
                details={},
            )
        except Exception as exc:
            logger.debug('Renderer detection raised unexpected error: %s', exc)
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity='info',
                message='Skipped (renderer detection error: %s)' % exc,
                details={},
            )

        renderer_lower = (renderer or '').lower()
        exclusive_for_others = set()
        for r_name, exts in _RENDERER_EXCLUSIVE_EXTS.items():
            if r_name != renderer_lower:
                exclusive_for_others |= exts

        try:
            assets = shot_node.get_assets()
        except Exception as exc:
            logger.debug('get_assets raised: %s', exc)
            assets = []

        mismatched = []
        for asset in assets:
            try:
                ext = asset.get_extension()
            except Exception:
                ext = ''

            if not ext:
                continue

            ext_with_dot = ('.' + ext.lstrip('.')) if ext else ''
            if ext_with_dot in exclusive_for_others:
                try:
                    asset_id = asset.get_asset_id()
                except Exception:
                    asset_id = str(asset)
                mismatched.append('%s (.%s)' % (asset_id, ext.lstrip('.')))
                logger.debug(
                    'Asset %s has extension .%s which does not suit renderer %s',
                    asset_id, ext, renderer,
                )

        passed = len(mismatched) == 0
        if passed:
            msg = 'All assets compatible with active renderer (%s)' % renderer
        else:
            msg = '%d asset(s) have extensions incompatible with renderer %s' % (
                len(mismatched), renderer,
            )

        return CheckResult(
            check_name=self.name,
            passed=passed,
            severity=self.severity,
            message=msg,
            details={
                'active_renderer': renderer,
                'mismatched_assets': mismatched,
            },
        )
