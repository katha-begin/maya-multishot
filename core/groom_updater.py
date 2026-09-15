# -*- coding: utf-8 -*-
"""Point CFX groom standins at the active shot's publish.

Temporary, for project EGA (config ``cfx.repathOnShotSwitch``).

A CFX groom publish is an Arnold .ass frame sequence per shot::

    <shot>/cfx/publish/<ver>/<basename>_ass/<basename>.####.ass

EGA scenes hold one standin per groom, built for whichever shot the scene
came from.  Set Shot resolved references for the new shot but never touched
these standins, so the groom stayed on the old shot.  Rather than keeping a
standin per shot, the standin's path is replaced: only the active shot's
frames are ever loaded, so another shot's missing or out-of-range frames
cannot fail a render.

Per groom (asset type + name + variant, whatever shot its path names):

- The standin is pointed at the active shot's publish: the version it already
  uses when it is on that shot, else the newest version holding the groom's
  sequence folder.  The path is only written when it changes.
- The active shot has no publish of the groom: the standin is hidden and its
  path left alone.
- Two standins of one groom: the one already on the shot (else the first by
  name) is used; the others are hidden.
- A standin left on the active shot is made visible.

The frames the shot needs are checked -- missing, empty (0 bytes) and much
smaller than the rest (likely no groom data) -- and reported, never skipped.
Node names are not changed.
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

from core import asset_types, cfx_adopter
from core.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_DEPT = 'cfx'

# A frame under this fraction of the sequence's median size most likely holds
# no groom data (an .ass with only its header).
SMALL_FRAME_RATIO = 0.1

ACTION_UPDATE = 'update'
ACTION_CURRENT = 'current'
ACTION_NO_PUBLISH = 'no_publish'
ACTION_DUPLICATE = 'duplicate'

_VERSION_RE = re.compile(r'^v(\d+)$')


def is_enabled(config):
    """Return True when the project wants grooms to follow the active shot."""
    check = getattr(config, 'is_cfx_repath_on_shot_switch', None)
    return bool(check is not None and check() is True)


# ---------------------------------------------------------------------------
# publish folders
# ---------------------------------------------------------------------------

def _norm(path):
    return (path or '').replace('\\', '/')


def _same_path(a, b):
    return (os.path.normcase(os.path.normpath(_norm(a))) ==
            os.path.normcase(os.path.normpath(_norm(b))))


def get_publish_root(config, ep, seq, shot, dept, platform=None):
    """Return ``<scene base>/<ep>/<seq>/<shot>/<dept>/publish`` for this platform."""
    from core.shot_discovery import get_scene_base

    scene_base = get_scene_base(config, platform)
    if not scene_base:
        return None
    return _norm(os.path.join(scene_base, ep, seq, shot, dept, 'publish'))


def list_versions(publish_root, basename, ext):
    """Versions of a shot's publish that hold a groom's sequence folder.

    Only the version folders are listed; the sequence folders themselves hold
    one file per frame and are not.

    Returns:
        list: ``[(version, sequence_dir), ...]``, newest first.
    """
    if not publish_root:
        return []
    try:
        names = os.listdir(publish_root)
    except OSError:
        return []

    versions = [name for name in names if _VERSION_RE.match(name)]
    versions.sort(key=lambda name: int(_VERSION_RE.match(name).group(1)), reverse=True)

    seq_dir_name = asset_types.build_sequence_dir_name(basename, ext)
    found = []
    for version in versions:
        seq_dir = _norm(os.path.join(publish_root, version, seq_dir_name))
        if os.path.isdir(seq_dir):
            found.append((version, seq_dir))
    return found


# ---------------------------------------------------------------------------
# frame check
# ---------------------------------------------------------------------------

def _file_sizes(folder):
    """``{file name: size}`` for a folder, in one listing where possible.

    os.scandir (Python 3.5+) reports sizes with the listing on Windows, so a
    network share is not asked again for every frame.
    """
    sizes = {}
    scandir = getattr(os, 'scandir', None)
    if scandir is not None:
        for entry in scandir(folder):
            try:
                if entry.is_file():
                    sizes[entry.name] = entry.stat().st_size
            except OSError:
                continue
        return sizes

    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        try:
            if os.path.isfile(path):
                sizes[name] = os.path.getsize(path)
        except OSError:
            continue
    return sizes


def check_frames(sequence_dir, basename, ext, start, end):
    """Check the frames ``start``-``end`` of a groom sequence.

    Returns:
        dict: 'count' frames needed; 'missing', 'empty' (0 bytes) and 'small'
            (under SMALL_FRAME_RATIO of the median size) frame lists; 'error'
            with the reason when the folder cannot be read, else None.
    """
    frames = list(range(int(round(start)), int(round(end)) + 1))
    result = {'count': len(frames), 'missing': [], 'empty': [], 'small': [],
              'error': None}
    try:
        listing = _file_sizes(sequence_dir)
    except OSError as exc:
        result['error'] = str(exc)
        return result

    pattern = re.compile(r'^{}\.(-?\d+)\.{}$'.format(
        re.escape(basename), re.escape(ext.lstrip('.'))), re.IGNORECASE)
    sizes = {}
    for name, size in listing.items():
        match = pattern.match(name)
        if match:
            sizes[int(match.group(1))] = size

    needed = [(frame, sizes.get(frame)) for frame in frames]
    result['missing'] = [frame for frame, size in needed if size is None]
    result['empty'] = [frame for frame, size in needed if size == 0]
    filled = sorted(size for _, size in needed if size)
    if filled:
        limit = filled[len(filled) // 2] * SMALL_FRAME_RATIO
        result['small'] = [frame for frame, size in needed if size and size < limit]
    return result


def format_frames(frames, limit=None):
    """Compact frame list: ``[1001, 1002, 1003, 1005]`` -> ``'1001-1003, 1005'``."""
    runs = []
    for frame in sorted(frames):
        if runs and frame == runs[-1][1] + 1:
            runs[-1][1] = frame
        else:
            runs.append([frame, frame])
    shown = runs if limit is None else runs[:limit]
    text = ', '.join(str(a) if a == b else '{}-{}'.format(a, b) for a, b in shown)
    if len(shown) < len(runs):
        text += ', ...'
    return text


def describe_frames(check, limit=4):
    """One line describing a frame check's problems; '' when there are none."""
    if not check:
        return ''
    if check.get('error'):
        return 'cannot read the sequence folder: {}'.format(check['error'])
    parts = []
    for key, label in (('missing', 'missing'), ('empty', 'empty'),
                       ('small', 'suspiciously small')):
        frames = check.get(key) or []
        if frames:
            parts.append('{} {} ({})'.format(len(frames), label,
                                             format_frames(frames, limit)))
    return '; '.join(parts)


# ---------------------------------------------------------------------------
# scene
# ---------------------------------------------------------------------------

def _parent(node):
    try:
        parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
    except Exception:
        return None
    return parents[0] if parents else None


def _frame_offset(shape, attr):
    try:
        if attr and cmds.attributeQuery(attr, node=shape, exists=True):
            return int(round(cmds.getAttr('{}.{}'.format(shape, attr)) or 0))
    except Exception as exc:
        logger.debug('Could not read %s.%s: %s', shape, attr, exc)
    return 0


def _set_visible(node, visible):
    if not node:
        return
    plug = '{}.visibility'.format(node)
    try:
        if bool(cmds.getAttr(plug)) == bool(visible):
            return
        if not cmds.getAttr(plug, settable=True):
            logger.warning('Cannot %s %s: its visibility is locked or connected',
                           'show' if visible else 'hide', node)
            return
        cmds.setAttr(plug, bool(visible))
    except Exception as exc:
        logger.warning('Cannot set visibility on %s: %s', node, exc)


def plan_grooms(config, shot_node, platform=None):
    """Work out what each CFX groom standin needs for a shot.

    Reads the scene and the shot's publish folders; changes nothing.

    Args:
        config: ProjectConfig instance.
        shot_node: CTXShotNode (ep/seq/shot codes and frame range).
        platform (str): 'windows' or 'linux'; defaults to the running one.

    Returns:
        list: One dict per standin, sorted by shape name.
    """
    if not MAYA_AVAILABLE:
        return []

    ep, seq, shot = shot_node.get_ep_code(), shot_node.get_seq_code(), shot_node.get_shot_code()
    start, end = shot_node.get_frame_range()
    path_attr = config.get_cfx_attribute('path')
    offset_attr = config.get_cfx_attribute('frameOffset')
    frame_token = config.get_cfx_frame_token()

    items = []
    versions_by_key = {}
    for standin in sorted(cfx_adopter.find_cfx_standins(config), key=lambda s: s['shape']):
        context = standin['context']
        dept = context['dept'] or DEFAULT_DEPT
        basename = asset_types.build_basename(
            ep, seq, shot, context['type'], context['name'], context['variant'], config)

        key = (dept, basename, context['ext'])
        if key not in versions_by_key:
            publish_root = get_publish_root(config, ep, seq, shot, dept, platform)
            versions_by_key[key] = list_versions(publish_root, basename, context['ext'])
        versions = versions_by_key[key]

        offset = _frame_offset(standin['shape'], offset_attr)
        items.append({
            'shape': standin['shape'],
            'transform': _parent(standin['shape']),
            'groom': asset_types.build_asset_part(
                context['type'], context['name'], context['variant'], config),
            'identity': (context['type'], context['name'], context['variant']),
            'current_path': standin['path'],
            'current_shot': context['shot'],
            'current_version': context['ver'],
            'on_shot': (context['ep'], context['seq'], context['shot']) == (ep, seq, shot),
            'shot': shot,
            'basename': basename,
            'ext': context['ext'],
            'frame_token': frame_token,
            'path_attr': path_attr,
            'start': start + offset,
            'end': end + offset,
            'versions': [version for version, _ in versions],
            'sequence_dirs': dict(versions),
            'duplicate_of': None,
        })

    _mark_duplicates(items)
    return items


def _mark_duplicates(items):
    groups = {}
    for item in items:
        groups.setdefault(item['identity'], []).append(item)
    for group in groups.values():
        if len(group) < 2:
            continue
        primary = next((item for item in group if item['on_shot']), group[0])
        for item in group:
            if item is not primary:
                item['duplicate_of'] = primary['shape']


def default_version(item):
    """The version a standin should use: its own when already on the shot, else the newest."""
    if not item['versions']:
        return None
    if item['on_shot'] and item['current_version'] in item['versions']:
        return item['current_version']
    return item['versions'][0]


def target_path(item, version=None):
    """The #### frame path for a version of the shot's publish, or None."""
    seq_dir = item['sequence_dirs'].get(version or default_version(item))
    if not seq_dir:
        return None
    return '{}/{}'.format(seq_dir, asset_types.build_frame_file_name(
        item['basename'], item['ext'], item['frame_token']))


def get_action(item, version=None):
    """What applying an item would do: one of the ACTION_* constants."""
    if item['duplicate_of']:
        return ACTION_DUPLICATE
    path = target_path(item, version)
    if not path:
        return ACTION_NO_PUBLISH
    if _same_path(path, item['current_path']):
        return ACTION_CURRENT
    return ACTION_UPDATE


def check_item_frames(item, version=None):
    """Frame check of the version an item would use; None without a publish."""
    seq_dir = item['sequence_dirs'].get(version or default_version(item))
    if not seq_dir:
        return None
    return check_frames(seq_dir, item['basename'], item['ext'], item['start'], item['end'])


def apply_item(item, version=None):
    """Point one standin at the shot, or hide it.

    Args:
        item (dict): From plan_grooms(); updated in place.
        version (str): Publish version; defaults to default_version().

    Returns:
        str: The ACTION_* performed.
    """
    version = version or default_version(item)
    action = get_action(item, version)

    if action == ACTION_UPDATE:
        path = target_path(item, version)
        cmds.setAttr('{}.{}'.format(item['shape'], item['path_attr']), path, type='string')
        logger.debug('Groom %s -> %s', item['shape'], path)
        item.update(current_path=path, current_shot=item['shot'],
                    current_version=version, on_shot=True)

    _set_visible(item['transform'], action in (ACTION_UPDATE, ACTION_CURRENT))
    return action


def update_grooms_for_shot(config, shot_node, platform=None):
    """Point every CFX groom standin at a shot; hide the ones it lacks.

    Returns:
        dict: 'shot', 'total', a count per ACTION_*, and 'problems' as
            ``[(groom, description), ...]`` for frame check failures.
    """
    summary = {'shot': shot_node.get_shot_code(), 'total': 0, 'problems': [],
               ACTION_UPDATE: 0, ACTION_CURRENT: 0,
               ACTION_NO_PUBLISH: 0, ACTION_DUPLICATE: 0}

    items = plan_grooms(config, shot_node, platform)
    summary['total'] = len(items)
    for item in items:
        action = apply_item(item)
        summary[action] += 1
        if action in (ACTION_UPDATE, ACTION_CURRENT):
            problem = describe_frames(check_item_frames(item))
            if problem:
                summary['problems'].append((item['groom'], problem))
                logger.warning('Groom %s for %s: %s', item['groom'], summary['shot'], problem)

    if items:
        logger.info('Grooms for %s: %s', summary['shot'], format_summary(summary))
    return summary


def format_summary(summary):
    """'1 updated, 0 already set, 1 hidden, 1 with frame problems'."""
    parts = ['{} updated'.format(summary[ACTION_UPDATE]),
             '{} already set'.format(summary[ACTION_CURRENT])]
    hidden = summary[ACTION_NO_PUBLISH] + summary[ACTION_DUPLICATE]
    if hidden:
        parts.append('{} hidden'.format(hidden))
    if summary['problems']:
        parts.append('{} with frame problems'.format(len(summary['problems'])))
    return ', '.join(parts)
