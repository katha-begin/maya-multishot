# -*- coding: utf-8 -*-
"""Diagnose why a SETS asset shows up in CTX_Inactive.

Run in the Maya Script Editor (Python tab).  Read-only: changes nothing.

Answers four questions, in order:

  1. Does the active shot contribute the SETS namespace to active_assets?
     If not, switch_shot_layers puts the set in CTX_Inactive.
  2. What does the namespace actually resolve to (its true top transforms)?
  3. Which layer is each of those top transforms wired to right now?
  4. Do any DESCENDANTS of the set carry their own drawOverride connection?
     A child with its own connection stops inheriting the top transform's
     layer, so pinning only the top node no longer controls it.
"""

from __future__ import absolute_import, division, print_function

import maya.cmds as cmds

ACTIVE_LAYER = 'CTX_Active'
INACTIVE_LAYER = 'CTX_Inactive'


def _ctx_nodes(ctx_type):
    out = []
    for node in cmds.ls(type='network') or []:
        if not cmds.attributeQuery('ctx_type', node=node, exists=True):
            continue
        if cmds.getAttr(node + '.ctx_type') == ctx_type:
            out.append(node)
    return out


def _assets_of(shot):
    linked = cmds.listConnections(shot + '.assets',
                                  source=True, destination=False) or []
    return [a for a in linked
            if cmds.attributeQuery('ctx_type', node=a, exists=True)
            and cmds.getAttr(a + '.ctx_type') == 'CTX_Asset']


def _ns_of(asset):
    if not cmds.attributeQuery('namespace', node=asset, exists=True):
        return None
    return cmds.getAttr(asset + '.namespace') or None


def _layer_of(node):
    src = cmds.listConnections(node + '.drawOverride',
                               source=True, destination=False) or []
    return src[0] if src else None


def _true_top_nodes(namespace):
    """Top transforms of a namespace, correct even when it sits under a group.

    Compares the PARENT'S SHORT NAME against the namespace, not the parent's
    full path -- a full path only starts with '|<ns>:' when the namespace root
    happens to sit directly under the world.
    """
    prefix = namespace.rstrip(':') + ':'
    roots = []
    for node in cmds.ls(prefix + '*', long=True, type='transform') or []:
        parents = cmds.listRelatives(node, parent=True, fullPath=True)
        if not parents:
            roots.append(node)
            continue
        if not parents[0].split('|')[-1].startswith(prefix):
            roots.append(node)
    return roots


def run():
    shots = _ctx_nodes('CTX_Shot')
    active = [s for s in shots
              if cmds.attributeQuery('is_active', node=s, exists=True)
              and cmds.getAttr(s + '.is_active')]

    print('=' * 74)
    print('ACTIVE SHOT(S): %s' % (active or 'NONE  <-- nothing is active'))
    print('shots in scene: %d' % len(shots))

    # ---- 1. namespace membership -------------------------------------
    all_ns, active_ns = set(), set()
    sets_records = []
    for shot in shots:
        for asset in _assets_of(shot):
            ns = _ns_of(asset)
            if '_SETS_' in asset or (ns or '').startswith('SETS_'):
                has_tgt = bool(cmds.listConnections(asset + '.targetNode',
                                                    source=True, destination=False)
                               if cmds.attributeQuery('targetNode', node=asset,
                                                      exists=True) else None)
                sets_records.append((shot, asset, ns, has_tgt))
            if ns:
                all_ns.add(ns)
                if shot in active:
                    active_ns.add(ns)

    print('-' * 74)
    print('SETS records (%d)' % len(sets_records))
    for shot, asset, ns, has_tgt in sorted(sets_records):
        flag = '' if ns else '   <-- EMPTY NAMESPACE, record is dropped'
        print('  %-30s ns=%-34r targetNode=%s%s'
              % (shot.replace('CTX_Shot_', ''), ns,
                 'yes' if has_tgt else 'NO', flag))

    sets_namespaces = sorted(set(n for _, _, n, _ in sets_records if n))
    print('-' * 74)
    for ns in sets_namespaces:
        verdict = 'ACTIVE' if ns in active_ns else 'INACTIVE  <-- set gets hidden'
        print('%-40s in_all=%s in_active=%s  => %s'
              % (ns, ns in all_ns, ns in active_ns, verdict))

    # ---- 2 + 3. resolution and current wiring ------------------------
    for ns in sets_namespaces:
        print('-' * 74)
        print('namespace %r exists: %s' % (ns, cmds.namespace(exists=ns)))
        roots = _true_top_nodes(ns)
        print('true top transforms (%d):' % len(roots))
        for r in roots:
            print('   %-58s -> %s' % (r.split('|')[-1], _layer_of(r) or 'NO LAYER'))

        # ---- 4. descendants pinned independently ---------------------
        strays = []
        for root in roots:
            for child in cmds.listRelatives(root, allDescendents=True,
                                            fullPath=True, type='transform') or []:
                layer = _layer_of(child)
                if layer:
                    strays.append((child, layer))
        print('descendants with their OWN drawOverride connection: %d' % len(strays))
        if strays:
            print('   these no longer inherit the top transform\'s layer:')
            for node, layer in strays[:40]:
                print('     %-56s -> %s' % (node.split('|')[-1], layer))
            if len(strays) > 40:
                print('     ... and %d more' % (len(strays) - 40))

    # ---- layer state --------------------------------------------------
    print('-' * 74)
    for layer in (ACTIVE_LAYER, INACTIVE_LAYER):
        if cmds.objExists(layer):
            members = cmds.editDisplayLayerMembers(layer, q=True) or []
            print('%-12s visibility=%s  members=%d'
                  % (layer, cmds.getAttr(layer + '.visibility'), len(members)))
        else:
            print('%-12s MISSING' % layer)
    print('=' * 74)


if __name__ == '__main__':
    run()
else:
    run()
