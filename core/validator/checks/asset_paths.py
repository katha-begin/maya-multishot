# -*- coding: utf-8 -*-
"""Asset path existence check.

For every CTX_Asset linked to the shot:
- file_path must not be empty
- file_path must not contain unexpanded $tokens
- file_path must exist on disk
"""

from __future__ import absolute_import, division, print_function

import os

from core.logging_config import get_logger
from core.validator.base_check import BaseCheck

logger = get_logger(__name__)


def _publish_present(asset, file_path, config=None):
    """Return True if an asset's publish is present on disk.

    Most types publish a single file, so plain existence is the right test.
    Sequence types such as CFX publish a directory of per-frame files and
    their stored path carries a literal frame token, so that path never
    exists as a file -- check the containing directory instead.

    The directory is not enumerated: a CFX publish holds one file per frame,
    potentially thousands, and this runs once per asset per validation.

    Args:
        asset: CTXAssetNode wrapper.
        file_path (str): Stored file path.
        config: Optional ProjectConfig instance.

    Returns:
        bool: True if the publish is present.
    """
    from core import asset_types

    try:
        asset_type = asset.get_asset_type()
    except Exception as exc:
        logger.debug('get_asset_type raised: %s', exc)
        asset_type = ''

    shape = asset_types.get_publish_shape(asset_type, config)
    if shape == asset_types.PUBLISH_SHAPE_SEQUENCE_DIR:
        return os.path.isdir(os.path.dirname(file_path))

    return os.path.exists(file_path)


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

            if not _publish_present(asset, file_path, config):
                missing_files.append('%s (%s)' % (asset_id, file_path))
                logger.debug('Publish not found for %s: %s', asset_id, file_path)

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
