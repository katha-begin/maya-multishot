# -*- coding: utf-8 -*-
"""Gaffer chain integrity check.

Validates:
- parentGaffer chain has no cycles (max 10 hops)
- All CTX_LightContext nodes in each gaffer have a valid target light in scene
- No CTX_LightContext nodes are orphaned (exist but belong to no gaffer)
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

_MAX_CHAIN_HOPS = 10


class GafferChainCheck(BaseCheck):
    """Validate the gaffer chain attached to this shot.

    Severity: warning -- a broken gaffer chain causes incorrect lighting but
    does not necessarily prevent a render from starting.
    """

    name = 'gaffer_chain'
    severity = 'warning'

    def run(self, shot_node, config, platform_config=None, **kwargs):
        from core.validator import CheckResult

        # Get shot gaffer -- returns node name string or None
        try:
            gaffer = shot_node.get_gaffer()
        except Exception as exc:
            logger.debug('get_gaffer raised: %s', exc)
            gaffer = None

        if gaffer is None:
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity=self.severity,
                message='No gaffer attached to shot',
                details={
                    'cycles_found': False,
                    'orphaned_contexts': [],
                    'invalid_targets': [],
                },
            )

        from core.nodes.wrappers import CTXLightGafferNode, CTXLightContextNode

        # Resolve to wrapper
        gaffer_node_name = gaffer if isinstance(gaffer, str) else gaffer.node_name
        gaffer_wrapper = CTXLightGafferNode(gaffer_node_name)

        cycles_found = False
        invalid_targets = []

        # Walk the parentGaffer chain, detect cycles
        seen = set()
        current = gaffer_wrapper
        hops = 0
        chain_nodes = []

        while current is not None and hops <= _MAX_CHAIN_HOPS:
            node_name_cur = current.node_name
            if node_name_cur in seen:
                cycles_found = True
                logger.warning('Cycle detected in gaffer chain at node %s', node_name_cur)
                break
            seen.add(node_name_cur)
            chain_nodes.append(current)
            hops += 1
            try:
                current = current.get_parent_gaffer()
            except Exception as exc:
                logger.debug('get_parent_gaffer raised: %s', exc)
                break

        if hops > _MAX_CHAIN_HOPS:
            cycles_found = True
            logger.warning('Gaffer chain exceeded %d hops -- likely a cycle', _MAX_CHAIN_HOPS)

        # Validate all light contexts in each gaffer in chain
        for chain_gaffer in chain_nodes:
            try:
                lights = chain_gaffer.get_lights()
            except Exception as exc:
                logger.debug('get_lights raised for %s: %s', chain_gaffer.node_name, exc)
                lights = []

            for light_ctx in lights:
                ctx_name = light_ctx.node_name if hasattr(light_ctx, 'node_name') else str(light_ctx)
                if MAYA_AVAILABLE:
                    try:
                        target = light_ctx.get_target_light()
                    except Exception as exc:
                        logger.debug('get_target_light raised for %s: %s', ctx_name, exc)
                        target = None

                    if target is None:
                        invalid_targets.append('%s (no target)' % ctx_name)
                        logger.debug('Light context %s has no target', ctx_name)
                    elif not cmds.objExists(target):
                        invalid_targets.append('%s (target %s missing)' % (ctx_name, target))
                        logger.debug('Target light %s for %s does not exist', target, ctx_name)

        # Check for orphaned CTX_LightContext nodes (not connected to any gaffer)
        orphaned_contexts = []
        if MAYA_AVAILABLE:
            try:
                all_contexts = CTXLightContextNode.list_all()
            except Exception as exc:
                logger.debug('list_all raised: %s', exc)
                all_contexts = []

            for ctx in all_contexts:
                ctx_name = ctx.node_name if hasattr(ctx, 'node_name') else str(ctx)
                try:
                    parent_gaffer = ctx.get_parent_gaffer()
                except Exception as exc:
                    logger.debug('get_parent_gaffer raised for context %s: %s', ctx_name, exc)
                    parent_gaffer = None

                if parent_gaffer is None:
                    orphaned_contexts.append(ctx_name)
                    logger.debug('Orphaned CTX_LightContext: %s', ctx_name)

        passed = (not cycles_found) and (not invalid_targets) and (not orphaned_contexts)

        if passed:
            msg = 'Gaffer chain is valid (%d gaffer(s) in chain)' % len(chain_nodes)
        else:
            parts = []
            if cycles_found:
                parts.append('cycle detected')
            if invalid_targets:
                parts.append('%d invalid target(s)' % len(invalid_targets))
            if orphaned_contexts:
                parts.append('%d orphaned context(s)' % len(orphaned_contexts))
            msg = 'Gaffer chain issues: ' + ', '.join(parts)

        return CheckResult(
            check_name=self.name,
            passed=passed,
            severity=self.severity,
            message=msg,
            details={
                'cycles_found': cycles_found,
                'orphaned_contexts': orphaned_contexts,
                'invalid_targets': invalid_targets,
            },
        )
