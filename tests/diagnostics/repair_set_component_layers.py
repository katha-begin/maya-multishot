# -*- coding: utf-8 -*-
"""Undo per-piece display-layer pinning inside an imported set.

Run in the Maya Script Editor (Python tab).  DRY RUN BY DEFAULT:

    exec(open(r"...\repair_set_component_layers.py").read())   # report only
    repair(apply=True)                                         # actually fix

Why this is needed
------------------
An imported SETS asset references its pieces into namespaces nested under its
own (SETS_X_001:TRLRWallA_0001).  The reconciler adopted those pieces as
CTX_Asset records of whichever shot was open, so every other shot computed
them as inactive and connected each piece's Geo_Grp to CTX_Inactive.

A child that carries its own drawOverride connection stops inheriting its
parent's layer.  So the set's top transform sits in CTX_Active while its
pieces are pinned to CTX_Inactive, and the set is invisible on every shot but
the one that owns the stray records.

The code fix in core/display_layers.py stops new pins being made, but it
cannot undo connections already baked into the scene.  This does that:

  1. disconnect drawOverride on any descendant of an asset top transform,
     so it inherits its parent's layer again
  2. optionally delete the CTX_Asset records whose namespace is nested inside
     another asset's namespace -- those describe set pieces, not shot assets

Only CTX_Active / CTX_Inactive connections are touched.  A piece you put in
a display layer of your own (layer1, MASTER_*, ...) is left exactly alone.
"""

from __future__ import absolute_import, division, print_function

import maya.cmds as cmds

ACTIVE_LAYER = 'CTX_Active'
INACTIVE_LAYER = 'CTX_Inactive'
CTX_LAYERS = (ACTIVE_LAYER, INACTIVE_LAYER)


def _ctx_nodes(ctx_type):
    out = []
    for node in cmds.ls(type='network') or []:
        if not cmds.attributeQuery('ctx_type', node=node, exists=True):
            continue
        if cmds.getAttr(node + '.ctx_type') == ctx_type:
            out.append(node)
    return out


def _asset_records():
    """[(ctx_asset_node, namespace), ...] for every CTX_Asset in the scene."""
    out = []
    for node in _ctx_nodes('CTX_Asset'):
        if not cmds.attributeQuery('namespace', node=node, exists=True):
            continue
        ns = cmds.getAttr(node + '.namespace') or ''
        if ns:
            out.append((node, ns))
    return out


def _is_nested(namespace):
    """A namespace nested inside another one names a piece, not an asset."""
    return ':' in (namespace or '').strip(':')


def _top_transforms(namespace):
    """Top transforms of a namespace, correct when it sits under a group."""
    prefix = namespace.rstrip(':') + ':'
    roots = []
    for node in cmds.ls(prefix + '*', long=True, type='transform') or []:
        parents = cmds.listRelatives(node, parent=True, fullPath=True)
        if not parents or not parents[0].split('|')[-1].startswith(prefix):
            roots.append(node)
    return roots


def _layer_plug(node):
    """(source_plug, layer) currently driving node.drawOverride, or (None, None)."""
    plugs = cmds.listConnections(node + '.drawOverride', source=True,
                                 destination=False, plugs=True) or []
    if not plugs:
        return None, None
    return plugs[0], plugs[0].split('.')[0]


def repair(apply=False):
    print('=' * 74)
    print('REPAIR SET COMPONENT LAYERS  --  %s'
          % ('APPLYING CHANGES' if apply else 'DRY RUN, nothing modified'))
    print('=' * 74)

    records = _asset_records()
    asset_namespaces = sorted(set(ns for _, ns in records if not _is_nested(ns)))

    # ---- 1. descendants pinned to a CTX layer -------------------------
    to_disconnect = []
    skipped_foreign = []
    for ns in asset_namespaces:
        for root in _top_transforms(ns):
            children = cmds.listRelatives(root, allDescendents=True,
                                          fullPath=True, type='transform') or []
            for child in children:
                plug, layer = _layer_plug(child)
                if not layer:
                    continue
                if layer in CTX_LAYERS:
                    to_disconnect.append((child, plug, layer))
                else:
                    skipped_foreign.append((child, layer))

    print('\n1. Descendants pinned to a CTX layer: %d' % len(to_disconnect))
    for node, _plug, layer in to_disconnect:
        print('   %-58s -> %s' % (node.split('|')[-1], layer))
    if skipped_foreign:
        print('\n   left alone (your own display layers): %d'
              % len(skipped_foreign))
        for node, layer in skipped_foreign:
            print('   %-58s -> %s' % (node.split('|')[-1], layer))

    # ---- 2. CTX_Asset records that describe a set piece ---------------
    nested_records = [(n, ns) for n, ns in records if _is_nested(ns)]
    print('\n2. CTX_Asset records naming a nested piece: %d' % len(nested_records))
    for node, ns in sorted(nested_records, key=lambda x: x[1]):
        print('   %-46s ns=%s' % (node, ns))

    if not apply:
        print('\n' + '=' * 74)
        print('DRY RUN -- nothing changed.  To apply:')
        print('   repair(apply=True)')
        print('=' * 74)
        return {'disconnected': 0, 'removed': 0,
                'would_disconnect': len(to_disconnect),
                'would_remove': len(nested_records)}

    disconnected = 0
    for node, plug, _layer in to_disconnect:
        try:
            cmds.disconnectAttr(plug, node + '.drawOverride')
            disconnected += 1
        except Exception as exc:
            print('   ! could not disconnect %s: %s' % (node, exc))

    removed = 0
    for node, _ns in nested_records:
        try:
            if cmds.objExists(node):
                cmds.delete(node)
                removed += 1
        except Exception as exc:
            print('   ! could not delete %s: %s' % (node, exc))

    print('\n' + '=' * 74)
    print('disconnected: %d    records removed: %d' % (disconnected, removed))
    print('Switch shots once to confirm the set now follows its top transform.')
    print('=' * 74)
    return {'disconnected': disconnected, 'removed': removed}


if __name__ == '__main__':
    repair()
else:
    repair()
