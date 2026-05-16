# -*- coding: utf-8 -*-
"""One-shot migration script: reset all gaffer override modes to 'replace'.

Run inside Maya Script Editor or via:
    exec(open(r'E:/dev/maya-multishot/tools/fix_additive_modes.py').read())

What it does:
  1. Walks all CTX_LightContext nodes in the scene.
  2. For every *Mode attribute (intensityMode, translateMode, etc.),
     if the value is 'additive', resets it to 'replace'.
  3. For attributes that were additive, recaptures the current Maya value
     so the stored value is absolute (not a stale delta).
  4. Prints a summary of changes.
"""

from __future__ import absolute_import, division, print_function

try:
    import maya.cmds as cmds
except ImportError:
    raise RuntimeError("This script must be run inside Maya.")


# All *Mode attribute names on CTX_LightContext
_MODE_ATTRS = [
    'intensityMode', 'exposureMode', 'colorMode', 'temperatureMode',
    'translateMode', 'rotateMode', 'scaleMode',
    'spreadMode', 'areaSpreadMode',
    'diffuseContribMode', 'reflectionContribMode', 'transmissionContribMode',
    'singleScatterContribMode', 'multiScatterContribMode', 'volumeContribMode',
    'indirectContribMode', 'toonDiffuseContribMode', 'toonReflectionContribMode',
]

# Map mode-attr prefix to the sub-attributes that store the value
_COMPOUND_SUBS = {
    'color': ['colorR', 'colorG', 'colorB'],
    'translate': ['translateX', 'translateY', 'translateZ'],
    'rotate': ['rotateX', 'rotateY', 'rotateZ'],
    'scale': ['scaleX', 'scaleY', 'scaleZ'],
}


def _get_target_light(node):
    """Return the Maya light shape connected to a CTX_LightContext, or None."""
    conns = cmds.listConnections(
        '{}.targetLight'.format(node), source=True, destination=False) or []
    return conns[0] if conns else None


def _recapture_attr(node, attr_prefix, target_shape):
    """Recapture the current Maya value into the CTX_LightContext attrs.

    For compound groups (color, translate, etc.) recaptures all sub-attrs.
    For simple scalars, recaptures the single attr.
    """
    from core.gaffer.manager import GafferManager
    from core.renderers import get_maya_attr

    if not target_shape or not cmds.objExists(target_shape):
        return False

    try:
        captured = GafferManager.capture_light_values(target_shape)
    except Exception:
        return False

    if attr_prefix in _COMPOUND_SUBS:
        for sub in _COMPOUND_SUBS[attr_prefix]:
            if sub in captured:
                cmds.setAttr('{}.{}'.format(node, sub), captured[sub])
        return True

    if attr_prefix in captured:
        cmds.setAttr('{}.{}'.format(node, attr_prefix), captured[attr_prefix])
        return True

    return False


def fix_additive_modes():
    """Main entry point. Walk all CTX_LightContext nodes and fix modes."""
    all_nodes = cmds.ls(type='network') or []
    ctx_nodes = []
    for n in all_nodes:
        if cmds.attributeQuery('ctx_type', node=n, exists=True):
            if cmds.getAttr('{}.ctx_type'.format(n)) == 'CTX_LightContext':
                ctx_nodes.append(n)

    if not ctx_nodes:
        print('[fix_additive_modes] No CTX_LightContext nodes found.')
        return

    total_fixed = 0
    total_recaptured = 0
    details = []

    for node in ctx_nodes:
        target = _get_target_light(node)

        for mode_attr in _MODE_ATTRS:
            if not cmds.attributeQuery(mode_attr, node=node, exists=True):
                continue

            current_mode = cmds.getAttr('{}.{}'.format(node, mode_attr)) or 'replace'
            if current_mode != 'additive':
                continue

            # Reset to replace
            cmds.setAttr('{}.{}'.format(node, mode_attr), 'replace', type='string')
            total_fixed += 1

            # Recapture the absolute value from Maya
            attr_prefix = mode_attr.replace('Mode', '')
            if _recapture_attr(node, attr_prefix, target):
                total_recaptured += 1
                details.append(
                    '  {} . {} : additive -> replace (recaptured)'.format(node, attr_prefix))
            else:
                details.append(
                    '  {} . {} : additive -> replace (no recapture - target missing)'.format(
                        node, attr_prefix))

    print('[fix_additive_modes] Done.')
    print('  CTX_LightContext nodes scanned: {}'.format(len(ctx_nodes)))
    print('  Mode attrs reset to replace: {}'.format(total_fixed))
    print('  Values recaptured from Maya: {}'.format(total_recaptured))
    if details:
        print('  Details:')
        for d in details:
            print(d)
    else:
        print('  No additive overrides found -- nothing to fix.')


# Auto-run when exec'd
fix_additive_modes()
