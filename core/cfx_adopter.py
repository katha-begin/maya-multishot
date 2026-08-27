# -*- coding: utf-8 -*-
"""Adopt CFX standins that already exist in a scene.

The reference-based reconciler in core/asset_reconciler.py cannot see CFX
assets: it scans Maya references, and CFX standins are created nodes.  This
module provides the standin-side equivalent, plus the namespace pre-flight the
import flow runs before creating anything.

Adoption is deliberately non-destructive.  It never renames a node, never adds
a namespace to a node it did not create, and never touches dso or frameNumber.
It only creates the CTX_Asset records that make existing scene content visible
to the tool.  Migrating flat-named nodes into namespaces is a separate,
explicit action -- this repo has no undo, so an unintended migration is not
recoverable.

Usage:
    from core import cfx_adopter

    reason = cfx_adopter.namespace_conflict('Ep02_..._CFX_botgroomSamS001')
    if reason:
        raise RuntimeError(reason)

    stats = cfx_adopter.adopt_cfx_standins(config)
"""

from __future__ import absolute_import, division, print_function

import os
import re

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    MAYA_AVAILABLE = False

from core import asset_types
from core.logging_config import get_logger

logger = get_logger(__name__)

CFX_ASSET_TYPE = 'CFX'
_VERSION_RE = re.compile(r'^v\d+$')


# ---------------------------------------------------------------------------
# path parsing
# ---------------------------------------------------------------------------

def parse_dso_path(dso_path, config=None):
    """Recover asset context from a CFX standin's file path.

    Parses the path back through the same naming contract used to build it
    (core/asset_types.py) rather than re-deriving it from a template, so
    adopt and import cannot disagree about what a path means.

    Expected shape:
        .../<ep>/<seq>/<shot>/<dept>/publish/<ver>/<basename>_<ext>/<basename>.####.<ext>

    Args:
        dso_path (str): Value of the standin's path attribute.
        config: Optional ProjectConfig instance.

    Returns:
        dict: ep, seq, shot, dept, ver, type, name, variant, ext, basename.
              None if the path does not match the contract.
    """
    if not dso_path:
        return None

    normalised = dso_path.replace('\\', '/')
    parts = [p for p in normalised.split('/') if p]
    if len(parts) < 3:
        return None

    seq_dir = parts[-2]
    info = asset_types.parse_publish_name(seq_dir, is_dir=True, config=config)
    if not info:
        return None

    basename = seq_dir[:-(len(info['ext']) + 1)]

    shot_part = basename.split(asset_types.SHOT_ASSET_SEPARATOR)[0]
    shot_segments = shot_part.split('_')
    if len(shot_segments) < 3:
        return None

    version = parts[-3] if _VERSION_RE.match(parts[-3]) else ''

    dept = ''
    if version and len(parts) >= 5 and parts[-4] == 'publish':
        dept = parts[-5]

    return {
        'ep': shot_segments[0],
        'seq': shot_segments[1],
        'shot': shot_segments[2],
        'dept': dept,
        'ver': version,
        'type': info['type'],
        'name': info['name'],
        'variant': info['variant'],
        'ext': info['ext'],
        'basename': basename,
    }


# ---------------------------------------------------------------------------
# scene scanning
# ---------------------------------------------------------------------------

def _path_attr(config):
    if config is not None and hasattr(config, 'get_cfx_attribute'):
        return config.get_cfx_attribute('path')
    return 'dso'


def _group_name(config):
    if config is not None and hasattr(config, 'get_cfx_group_name'):
        return config.get_cfx_group_name()
    return 'Cfx_Grp'


def find_cfx_standins(config=None, group_name=None):
    """Find aiStandIn shapes in the scene that look like CFX publishes.

    A standin qualifies when its path parses back to an asset whose type has
    a sequence-directory publish shape.  Membership of the CFX group is
    recorded but not required, so a standin an artist re-parented is still
    found.

    Args:
        config: Optional ProjectConfig instance.
        group_name (str): Optional group override.

    Returns:
        list: dicts with shape, namespace, path, in_group and parsed context.
    """
    if not MAYA_AVAILABLE:
        return []

    if group_name is None:
        group_name = _group_name(config)
    path_attr = _path_attr(config)

    found = []
    for shape in cmds.ls(type='aiStandIn') or []:
        plug = '{}.{}'.format(shape, path_attr)
        try:
            if not cmds.objExists(plug):
                continue
            dso = cmds.getAttr(plug)
        except Exception as e:
            logger.debug('Could not read %s: %s', plug, e)
            continue

        parsed = parse_dso_path(dso, config)
        if not parsed:
            continue

        if asset_types.get_publish_shape(parsed['type'], config) != \
                asset_types.PUBLISH_SHAPE_SEQUENCE_DIR:
            continue

        namespace = ''
        if ':' in shape:
            namespace = shape.rsplit(':', 1)[0]

        found.append({
            'shape': shape,
            'namespace': namespace,
            'path': dso,
            'in_group': _is_under_group(shape, group_name),
            'context': parsed,
        })

    logger.debug('Found %d CFX standins', len(found))
    return found


def _is_under_group(node, group_name):
    """Return True if node has group_name somewhere among its ancestors."""
    current = node
    for _ in range(32):
        try:
            parents = cmds.listRelatives(current, parent=True, fullPath=True)
        except Exception:
            return False
        if not parents:
            return False
        parent = parents[0]
        if parent.split('|')[-1].split(':')[-1] == group_name:
            return True
        current = parent
    return False


# ---------------------------------------------------------------------------
# namespace pre-flight
# ---------------------------------------------------------------------------

def namespace_conflict(namespace, config=None):
    """Check whether a namespace can be safely created for a new CFX asset.

    Run before import.  A conflict aborts rather than auto-renaming: silently
    renaming an artist's nodes is not recoverable without undo.

    Args:
        namespace (str): Namespace the import intends to create.
        config: Optional ProjectConfig instance.

    Returns:
        str: Human-readable reason, or None when the namespace is free.
    """
    if not namespace:
        return 'Namespace is empty'

    if not MAYA_AVAILABLE:
        return None

    try:
        if not cmds.namespace(exists=namespace):
            return None
    except Exception as e:
        logger.debug('namespace(exists) raised for %s: %s', namespace, e)
        return None

    contents = cmds.ls('{}:*'.format(namespace)) or []
    if not contents:
        return None

    path_attr = _path_attr(config)
    for node in contents:
        try:
            if cmds.nodeType(node) != 'aiStandIn':
                continue
            dso = cmds.getAttr('{}.{}'.format(node, path_attr))
        except Exception:
            continue

        parsed = parse_dso_path(dso, config)
        if parsed and parsed['basename'] == namespace:
            # Same asset already imported -- not a conflict, just a duplicate.
            return ("Namespace '{}' already holds this CFX asset"
                    .format(namespace))

    return ("Namespace '{}' already exists and holds {} unrelated node(s)"
            .format(namespace, len(contents)))


# ---------------------------------------------------------------------------
# adoption
# ---------------------------------------------------------------------------

def find_unadopted(config=None, group_name=None):
    """Return CFX standins in the scene that have no backing CTX_Asset.

    Args:
        config: Optional ProjectConfig instance.
        group_name (str): Optional group override.

    Returns:
        list: Entries from find_cfx_standins() lacking a CTX_Asset.
    """
    standins = find_cfx_standins(config, group_name)
    if not standins:
        return []

    known = _existing_cfx_namespaces()
    return [s for s in standins
            if _identity_of(s) not in known]


def _identity_of(standin):
    """Identity key for a standin -- its publish basename."""
    return standin['context']['basename']


def _existing_cfx_namespaces():
    """Collect the namespace attribute of every CFX CTX_Asset in the scene."""
    if not MAYA_AVAILABLE:
        return set()

    known = set()
    for node in cmds.ls(type='network') or []:
        if not node.startswith('CTX_Asset_'):
            continue
        try:
            if not cmds.attributeQuery('asset_type', node=node, exists=True):
                continue
            if cmds.getAttr('{}.asset_type'.format(node)) != CFX_ASSET_TYPE:
                continue
            if not cmds.attributeQuery('namespace', node=node, exists=True):
                continue
            ns = cmds.getAttr('{}.namespace'.format(node))
        except Exception as e:
            logger.debug('Could not read CTX_Asset %s: %s', node, e)
            continue

        if ns:
            known.add(ns)

    return known


def find_dead_targets():
    """Return CFX CTX_Asset nodes whose targetNode link resolves to nothing.

    Returns:
        list: CTX_Asset node names.
    """
    if not MAYA_AVAILABLE:
        return []

    dead = []
    for node in cmds.ls(type='network') or []:
        if not node.startswith('CTX_Asset_'):
            continue
        try:
            if not cmds.attributeQuery('asset_type', node=node, exists=True):
                continue
            if cmds.getAttr('{}.asset_type'.format(node)) != CFX_ASSET_TYPE:
                continue
            if not cmds.attributeQuery('targetNode', node=node, exists=True):
                dead.append(node)
                continue
            linked = cmds.listConnections(
                '{}.targetNode'.format(node),
                source=True, destination=False) or []
        except Exception as e:
            logger.debug('Could not inspect %s: %s', node, e)
            continue

        if not any(cmds.objExists(n) for n in linked):
            dead.append(node)

    return dead


def find_duplicate_basenames(config=None, group_name=None):
    """Return publish basenames claimed by more than one standin in the scene.

    Two standins sharing a basename would collapse to one identity key and
    break display-layer switching, since that key is what tells one shot's
    CFX from another's.

    Returns:
        dict: {basename: [shape, ...]} for basenames seen more than once.
    """
    seen = {}
    for standin in find_cfx_standins(config, group_name):
        seen.setdefault(_identity_of(standin), []).append(standin['shape'])

    return dict((k, v) for k, v in seen.items() if len(v) > 1)
