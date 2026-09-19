# -*- coding: utf-8 -*-
"""List the CTX_Asset records each shot never published.  READ-ONLY.

Run in the Maya Script Editor (Python tab).

Why not repair_scene_records(remove_stale=False)?
    Because that is NOT a dry run.  Even with remove_stale off it calls
    reconcile_assets_for_shot() for every shot, which CREATES missing records
    and REPAIRS existing ones (core/asset_reconciler.py:580-582).  It only
    holds back the deletion.

    find_stale_records() reads and reports, nothing else -- so this script is
    safe to run on a scene you have not saved.

A record is reported when the shot's publish folder contains no such asset,
which is the "is it in the publish?" rule: a set present in the shot's publish
belongs to that shot, one that is not is a leftover from a scene built before
the publish check landed.
"""

from __future__ import absolute_import, division, print_function

import maya.cmds as cmds

from core.asset_reconciler import find_stale_records


def _shots():
    out = []
    for node in cmds.ls(type='network') or []:
        if not cmds.attributeQuery('ctx_type', node=node, exists=True):
            continue
        if cmds.getAttr(node + '.ctx_type') == 'CTX_Shot':
            out.append(node)
    return out


def run():
    print('=' * 74)
    print('STALE CTX_Asset RECORDS -- read-only, nothing is modified')
    print('=' * 74)

    total = 0
    scanned = 0
    for shot in sorted(_shots()):
        stale = find_stale_records(shot)
        scanned += 1
        if not stale:
            continue
        total += len(stale)
        print('\n%s   (%d stale)' % (shot, len(stale)))
        for entry in sorted(stale, key=lambda e: e.get('namespace') or ''):
            print('   %-42s %s' % (entry.get('namespace'), entry.get('reason')))

    print('\n' + '=' * 74)
    print('shots scanned: %d    stale records: %d' % (scanned, total))
    print('=' * 74)
    if total:
        print('A shot reporting 0 may simply have had no readable publishes --')
        print('find_stale_records stays silent rather than condemn a scene it')
        print('could not scan (core/asset_reconciler.py:516-519).')
        print('')
        print('To remove them (THIS WRITES -- and also reconciles every shot):')
        print('   from core.asset_reconciler import repair_scene_records')
        print('   repair_scene_records(remove_stale=True)')
        print('or the menu: CTX Tools -> Repair Scene Records')


if __name__ == '__main__':
    run()
else:
    run()
