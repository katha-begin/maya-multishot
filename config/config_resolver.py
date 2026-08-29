# -*- coding: utf-8 -*-
"""Decide which project config to load.

Before this module, four call sites each resolved the config their own way and
disagreed:

- ui/main_window.py hardcoded the repo path, so the GUI ignored every override
- tools/pipeline_api.py read the CTX_CONFIG environment variable
- config/project_config.py read CTX_CONFIG_PATH -- a different name -- and
  checked it *after* the repo path, so it could never win
- tools/maya_menu.py built the path inline again

Resolution order, highest priority first:

1. An explicit path passed by the caller (--config, API argument)
2. CTX_Manager.config_path on the open scene, so a scene loads the project it
   was built with
3. The project inferred from where the open scene lives on disk, matched
   against each config's projRoot + project + sceneBase prefix
4. The CTX_CONFIG environment variable (CTX_CONFIG_PATH is a deprecated alias)
5. project_configs/ctx_config.json in the repository

Steps 1-2 are explicit bindings and beat inference.  Step 3 beats step 4
because the environment variable is set once per session while the scene is
the specific thing being worked on.

Usage:
    from config.config_resolver import resolve_config_path

    path = resolve_config_path()
    config = ProjectConfig(path)
"""

from __future__ import absolute_import, division, print_function

import os

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    MAYA_AVAILABLE = False

from core.logging_config import get_logger

logger = get_logger(__name__)

ENV_VAR = 'CTX_CONFIG'
LEGACY_ENV_VAR = 'CTX_CONFIG_PATH'

DEFAULT_CONFIG_NAME = 'ctx_config.json'
CONFIG_DIR_NAME = 'project_configs'


def get_config_dir():
    """Return the repository's project_configs directory."""
    module_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(module_dir)
    return os.path.join(repo_root, CONFIG_DIR_NAME)


def get_default_config_path():
    """Return the repository's default config path."""
    return os.path.join(get_config_dir(), DEFAULT_CONFIG_NAME)


def list_project_configs():
    """List selectable project configs in the repository.

    Excludes 'base.json', which is a shared fragment rather than a project:
    it carries no project code or roots and is not loadable on its own.

    Returns:
        list: (name, path) pairs sorted by name.
    """
    config_dir = get_config_dir()
    if not os.path.isdir(config_dir):
        return []

    found = []
    for entry in sorted(os.listdir(config_dir)):
        if not entry.endswith('.json'):
            continue
        if entry == 'base.json':
            continue
        found.append((os.path.splitext(entry)[0],
                      os.path.join(config_dir, entry)))

    return found


def get_scene_config_path():
    """Return the config path recorded on the open scene's CTX_Manager.

    Returns:
        str or None: Path, or None when unavailable or unset.
    """
    if not MAYA_AVAILABLE:
        return None

    try:
        managers = cmds.ls(type='network') or []
    except Exception as e:
        logger.debug('Could not list scene nodes: %s', e)
        return None

    for node in managers:
        try:
            if not cmds.attributeQuery('ctx_type', node=node, exists=True):
                continue
            if cmds.getAttr('{}.ctx_type'.format(node)) != 'CTX_Manager':
                continue
            if not cmds.attributeQuery('config_path', node=node, exists=True):
                continue
            path = cmds.getAttr('{}.config_path'.format(node))
        except Exception as e:
            logger.debug('Could not read config_path from %s: %s', node, e)
            continue

        if path and os.path.exists(path):
            return path
        if path:
            logger.warning(
                "Scene names config '%s', which does not exist -- "
                "falling back", path)

    return None


def get_env_config_path():
    """Return the config path from the environment, if set.

    A path that does not exist is still returned, so loading fails with an
    error naming the file the user asked for.  Silently falling back would be
    worse: a typo in CTX_CONFIG would quietly load a different project and
    resolve every path against the wrong roots.
    """
    for var in (ENV_VAR, LEGACY_ENV_VAR):
        path = os.environ.get(var)
        if not path:
            continue
        if var == LEGACY_ENV_VAR:
            logger.warning(
                "%s is deprecated; use %s instead", LEGACY_ENV_VAR, ENV_VAR)
        if not os.path.exists(path):
            logger.warning(
                "%s points at '%s', which does not exist -- using it anyway "
                "so the failure is explicit rather than loading another "
                "project", var, path)
        return path

    return None


def get_open_scene_path():
    """Return the path of the open Maya scene, or '' when there is none."""
    if not MAYA_AVAILABLE:
        return ''

    try:
        return cmds.file(query=True, sceneName=True) or ''
    except Exception as e:
        logger.debug('Could not query scene name: %s', e)
        return ''


def _normalise(path):
    """Normalise a path for prefix comparison.

    Forward slashes throughout, and lowercased on Windows where paths are
    case-insensitive.
    """
    text = (path or '').replace('\\', '/')
    if os.name == 'nt':
        text = text.lower()
    return text


def get_project_prefix(config):
    """Build the path prefix that identifies a project on disk.

    Every shot path is built from the ``$projRoot$project/$sceneBase/...``
    template, so that leading fragment is what distinguishes one project's
    files from another's.

    Args:
        config (ProjectConfig): Loaded config.

    Returns:
        str: Prefix, or '' when the config lacks the parts to build one.
    """
    try:
        proj_root = config.get_root('projRoot')
        project = config.get_project_code()
        scene_base = config.get_static_path('sceneBase')
    except Exception as e:
        logger.debug('Could not build project prefix: %s', e)
        return ''

    if not proj_root or not project:
        return ''

    prefix = proj_root
    if not prefix.endswith('/') and not prefix.endswith('\\'):
        prefix += '/'
    prefix += project + '/'
    if scene_base:
        prefix += scene_base.strip('/') + '/'

    return prefix


def detect_config_from_scene(scene_path=None):
    """Infer which project config matches the open scene's location.

    Matches the scene path against each project config's
    ``projRoot + project + sceneBase`` prefix and returns the longest match,
    so a scene under ``X:/EGA/all/scene/...`` selects EGA even in a session
    launched for another project.

    A malformed config is skipped rather than aborting detection.

    Args:
        scene_path (str): Scene path to test.  Queried from Maya when omitted.

    Returns:
        str or None: Config path, or None when nothing matches.
    """
    if scene_path is None:
        scene_path = get_open_scene_path()

    if not scene_path:
        return None

    from config.project_config import ProjectConfig

    scene = _normalise(scene_path)
    best_path = None
    best_len = 0

    for name, path in list_project_configs():
        try:
            config = ProjectConfig(path)
        except Exception as e:
            logger.debug('Skipping unloadable config %s: %s', name, e)
            continue

        prefix = _normalise(get_project_prefix(config))
        if not prefix or not scene.startswith(prefix):
            continue

        if len(prefix) > best_len:
            best_len = len(prefix)
            best_path = path

    if best_path:
        logger.info("Scene '%s' matched project config '%s'",
                    scene_path, best_path)

    return best_path


def resolve_config_path(explicit=None, use_scene=True):
    """Resolve which project config to load.

    Args:
        explicit (str): Caller-supplied path, wins over everything.
        use_scene (bool): Consult CTX_Manager.config_path on the open scene.
            Pass False for headless work that must not depend on scene state.

    Returns:
        str: Config path.  The repository default is returned even when it
             does not exist, so the caller raises the usual IOError with a
             useful path in the message.
    """
    if explicit:
        logger.debug('Config from explicit argument: %s', explicit)
        return explicit

    if use_scene:
        bound_path = get_scene_config_path()
        if bound_path:
            logger.info('Config from scene CTX_Manager: %s', bound_path)
            return bound_path

        # Inferred from where the scene lives.  This sits above the
        # environment variable deliberately: the env var is set once per
        # session, while the scene is the specific thing being worked on, and
        # loading one project's roots for another project's scene is the
        # failure worth avoiding.
        detected = detect_config_from_scene()
        if detected:
            logger.info('Config detected from scene location: %s', detected)
            return detected

    env_path = get_env_config_path()
    if env_path:
        logger.info('Config from environment: %s', env_path)
        return env_path

    default_path = get_default_config_path()
    logger.debug('Config from repository default: %s', default_path)
    return default_path
