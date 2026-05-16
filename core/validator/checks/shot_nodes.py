# -*- coding: utf-8 -*-
"""CTX node hierarchy integrity check.

Validates that the shot exists in scene and its connections are intact:
- Shot has a parent sequence
- All asset[i] connections resolve to valid CTX_Asset nodes (not dangling)
- Gaffer connection (if present) resolves to a valid CTX_LightGaffer node
"""

from __future__ import absolute_import, division, print_function

from core.logging_config import get_logger
from core.validator.base_check import BaseCheck

logger = get_logger(__name__)

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False


class CTXNodeHierarchyCheck(BaseCheck):
    """Verify that shot node hierarchy connections are intact.

    Severity: error -- a broken hierarchy means scene data is unreliable.
    """

    name = 'ctx_node_hierarchy'
    severity = 'error'

    def run(self, shot_node, config, platform_config=None, **kwargs):
        # Import here to avoid circular imports at module level
        from core.validator import CheckResult

        if not MAYA_AVAILABLE:
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity='info',
                message='Skipped (no Maya)',
                details={},
            )

        node_name = shot_node.node_name if hasattr(shot_node, 'node_name') else str(shot_node)

        missing_connections = []
        dangling_assets = []

        # 1. Shot node must exist
        if not cmds.objExists(node_name):
            return CheckResult(
                check_name=self.name,
                passed=False,
                severity=self.severity,
                message='Shot node does not exist in scene: %s' % node_name,
                details={
                    'node_name': node_name,
                    'missing_connections': [],
                    'dangling_assets': [],
                },
            )

        # 2. Shot must have a parent sequence
        try:
            parent_seq = shot_node.get_parent_sequence()
        except Exception as exc:
            logger.debug('get_parent_sequence raised: %s', exc)
            parent_seq = None

        if not parent_seq:
            missing_connections.append('parent_sequence')
            logger.debug('Shot %s has no parent sequence', node_name)

        # 3. All asset connections must resolve to valid nodes
        try:
            assets = shot_node.get_assets()
        except Exception as exc:
            logger.debug('get_assets raised: %s', exc)
            assets = []

        for asset in assets:
            asset_name = asset.node_name if hasattr(asset, 'node_name') else str(asset)
            if not cmds.objExists(asset_name):
                dangling_assets.append(asset_name)
                logger.debug('Dangling asset connection: %s', asset_name)

        # 4. Gaffer connection (if any) must resolve to a valid node
        try:
            gaffer = shot_node.get_gaffer()
        except Exception as exc:
            logger.debug('get_gaffer raised: %s', exc)
            gaffer = None

        if gaffer is not None:
            gaffer_name = gaffer if isinstance(gaffer, str) else gaffer.node_name
            if not cmds.objExists(gaffer_name):
                missing_connections.append('gaffer')
                logger.debug('Gaffer node does not exist: %s', gaffer_name)

        passed = (not missing_connections) and (not dangling_assets)
        if passed:
            msg = 'Node hierarchy is intact'
        else:
            parts = []
            if missing_connections:
                parts.append('missing connections: %s' % ', '.join(missing_connections))
            if dangling_assets:
                parts.append('dangling assets: %s' % ', '.join(dangling_assets))
            msg = 'Hierarchy issues found -- ' + '; '.join(parts)

        return CheckResult(
            check_name=self.name,
            passed=passed,
            severity=self.severity,
            message=msg,
            details={
                'node_name': node_name,
                'missing_connections': missing_connections,
                'dangling_assets': dangling_assets,
            },
        )
