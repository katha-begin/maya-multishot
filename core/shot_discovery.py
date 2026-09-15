# -*- coding: utf-8 -*-
"""Discover shot folders on disk for every project config.

Backs the Add Shots dialog.  Kept free of Qt and Maya so the listing can be
tested on its own.

The dialog used to list only the project of the config the Multishot Manager
had loaded.  That was always SWA before multi-project configs; once a scene
could load EGA, SWA vanished from the list, and when the config failed to
load the list was silently empty.  Listing every project config, and reporting
why a project cannot be listed, fixes both.
"""

from __future__ import absolute_import, division, print_function

import os

from core.logging_config import get_logger

logger = get_logger(__name__)


def list_projects(config_paths=None):
    """Load every selectable project config, one entry per project code.

    ctx_config.json only points at another project's config, so when both it
    and that project's own file load, the project's own file is kept.

    Args:
        config_paths (list): Config files to load.  Defaults to the
            repository's project configs.

    Returns:
        list: dicts with keys 'code', 'config_path', 'config' and 'error',
            sorted by code.  A config that fails to load keeps its file name
            as 'code', 'config' None and the reason in 'error'.
    """
    from config.config_resolver import DEFAULT_CONFIG_NAME, list_project_configs
    from config.project_config import ProjectConfig

    if config_paths is None:
        config_paths = [path for _, path in list_project_configs()]

    by_code = {}
    for path in config_paths:
        name = os.path.splitext(os.path.basename(path))[0]
        is_pointer = os.path.basename(path).lower() == DEFAULT_CONFIG_NAME

        try:
            config = ProjectConfig(path)
            entry = {'code': config.get_project_code() or name,
                     'config_path': path, 'config': config, 'error': None}
        except Exception as exc:
            logger.warning("Could not load project config %s: %s", path, exc)
            entry = {'code': name, 'config_path': path, 'config': None,
                     'error': str(exc)}

        current = by_code.get(entry['code'])
        if current is None or (current['_pointer'] and not is_pointer):
            entry['_pointer'] = is_pointer
            by_code[entry['code']] = entry

    projects = []
    for code in sorted(by_code):
        entry = by_code[code]
        del entry['_pointer']
        projects.append(entry)
    return projects


def get_scene_base(config, platform=None):
    """Return the folder holding a project's episodes on this platform.

    Built from ``projRoot + project + sceneBase``, the same prefix every shot
    path template starts with.

    Args:
        config (ProjectConfig): Project config.
        platform (str): 'windows' or 'linux'.  Defaults to the running one.

    Returns:
        str or None: Folder path, or None when the config lacks a part.
    """
    from config.platform_config import PlatformConfig

    proj_root = PlatformConfig(config).get_root_for_platform('projRoot', platform)
    project = config.get_project_code()
    scene_base = config.get_static_path('sceneBase')

    if not (proj_root and project and scene_base):
        return None

    return os.path.join(proj_root, project, scene_base)


def _subdirs(path, accept):
    """Sorted child folder names of ``path`` accepted by ``accept``.

    Uses os.scandir where available (Python 3.5+): on Windows the folder
    listing already says which entries are folders, so the network share is
    not asked again for every shot.  Python 2 falls back to listdir + isdir.
    """
    scandir = getattr(os, 'scandir', None)
    try:
        if scandir is not None:
            names = []
            for entry in scandir(path):
                try:
                    if accept(entry.name) and entry.is_dir():
                        names.append(entry.name)
                except OSError:
                    continue
            return sorted(names)
        return sorted(n for n in os.listdir(path)
                      if accept(n) and os.path.isdir(os.path.join(path, n)))
    except OSError as exc:
        logger.warning("Cannot list %s: %s", path, exc)
        return []


def discover_shots(scene_base):
    """Walk ``<scene_base>/Ep*/sq*/SH*``.

    An unreadable folder is skipped with a warning rather than hiding the rest
    of the project.

    Args:
        scene_base (str): Folder holding the episodes.

    Returns:
        list: ``[(ep, [(seq, [shot, ...]), ...]), ...]``; episodes or
            sequences with nothing beneath them are kept, matching the dialog.
            Empty when the folder does not exist.
    """
    if not scene_base or not os.path.isdir(scene_base):
        return []

    episodes = []
    for ep in _subdirs(scene_base, lambda n: n.startswith(('Ep', 'ep'))):
        ep_path = os.path.join(scene_base, ep)
        sequences = []
        for seq in _subdirs(ep_path, lambda n: n.startswith('sq')):
            seq_path = os.path.join(ep_path, seq)
            shots = _subdirs(seq_path, lambda n: n.startswith('SH'))
            sequences.append((seq, shots))
        episodes.append((ep, sequences))
    return episodes
