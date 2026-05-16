# -*- coding: utf-8 -*-
"""Asset path existence check.

For every CTX_Asset linked to the shot:
- file_path must not be empty
- file_path must not contain unexpanded $tokens
- file_path must exist on disk
"""

from __future__ import absolute_import

import os

from core.logging_config import get_logger
from core.validator.base_check import BaseCheck

logger = get_logger(__name__)


class AssetPathExistsCheck(BaseCheck):
    """Verify that all asset file paths are resolved and exist on disk.

    Severity: error -- missing files will cause render failures.
    Works fully headless (no Maya dependency).
    """

    name = 'asset_paths'
    severity = 'error'

    def run(self, shot_node, config, platform_config=None, **kwargs):
        from core.validator import CheckResult

        missing_files = []
        unresolved_tokens = []

        try:
            assets = shot_node.get_assets()
        except Exception as exc:
            logger.debug('get_assets raised: %s', exc)
            assets = []

        for asset in assets:
            try:
                file_path = asset.get_file_path()
            except Exception as exc:
                logger.debug('get_file_path raised for %s: %s', asset, exc)
                file_path = ''

            asset_id = ''
            try:
                asset_id = asset.get_asset_id()
            except Exception:
                asset_id = str(asset)

            if not file_path:
                unresolved_tokens.append(asset_id)
                logger.debug('Empty file_path for asset %s', asset_id)
                continue

            if '$' in file_path:
                unresolved_tokens.append('%s (%s)' % (asset_id, file_path))
                logger.debug('Unresolved token in path for %s: %s', asset_id, file_path)
                continue

            if not os.path.exists(file_path):
                missing_files.append('%s (%s)' % (asset_id, file_path))
                logger.debug('File does not exist for %s: %s', asset_id, file_path)

        passed = (not missing_files) and (not unresolved_tokens)

        if passed:
            msg = 'All %d asset paths resolved and exist on disk' % len(assets)
        else:
            parts = []
            if unresolved_tokens:
                parts.append('%d unresolved' % len(unresolved_tokens))
            if missing_files:
                parts.append('%d missing on disk' % len(missing_files))
            msg = 'Asset path issues: ' + ', '.join(parts)

        return CheckResult(
            check_name=self.name,
            passed=passed,
            severity=self.severity,
            message=msg,
            details={
                'missing_files': missing_files,
                'unresolved_tokens': unresolved_tokens,
                'asset_count': len(assets),
            },
        )
