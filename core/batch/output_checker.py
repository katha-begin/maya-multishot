"""Render output checker.

Scans the resolved imgPath directory to determine if render output
exists for a given shot at its current version. No Maya required.
"""

from __future__ import absolute_import, division, print_function

import os

from core.logging_config import get_logger

logger = get_logger(__name__)

# Image file extensions to scan for
IMAGE_EXTENSIONS = {'.exr', '.jpg', '.jpeg', '.png', '.tif', '.tiff', '.tga', '.dpx'}

HAS_OUTPUT = 'has_output'
NO_OUTPUT = 'no_output'
UNKNOWN = 'unknown'


def check_shot_output(config, platform_config, ep, seq, shot, ver=None):
    """Check whether render output files exist for a shot.

    Resolves the imgPath template with the shot's current version and
    scans the resulting directory for image files.

    Args:
        config: ProjectConfig instance.
        platform_config: PlatformConfig instance.
        ep (str): Episode code.
        seq (str): Sequence code.
        shot (str): Shot code.
        ver (str|None): Version string (e.g. 'v001'). If None, attempts
                        to read from CTXShotNode or falls back to 'v001'.

    Returns:
        str: HAS_OUTPUT, NO_OUTPUT, or UNKNOWN (on error).
    """
    try:
        from core.resolver import PathResolver

        resolver = PathResolver(config, platform_config)

        resolved_ver = ver or _resolve_version(ep, seq, shot)

        rs_cfg = config.get_render_settings_config() if hasattr(config, 'get_render_settings_config') else {}
        out_cfg = rs_cfg.get('outputPath', {}) if rs_cfg else {}
        dept = out_cfg.get('deptFallback', 'lighting')

        context = {
            'ep': ep,
            'seq': seq,
            'shot': shot,
            'dept': dept,
            'ver': resolved_ver,
        }

        img_path = resolver.resolve_path('imgPath', context)
        # imgPath includes <RenderLayer> segments -- get the base output dir
        # by stripping the last two path components
        output_dir = os.path.dirname(os.path.dirname(img_path))

        if not os.path.isdir(output_dir):
            logger.debug("Output dir does not exist: %s", output_dir)
            return NO_OUTPUT

        # Scan recursively for any image file
        for root, dirs, files in os.walk(output_dir):
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext in IMAGE_EXTENSIONS:
                    logger.debug("Found output for %s_%s_%s at %s",
                                 ep, seq, shot, os.path.join(root, filename))
                    return HAS_OUTPUT

        logger.debug("No image files found in %s", output_dir)
        return NO_OUTPUT

    except Exception as exc:
        logger.warning("Output check failed for %s_%s_%s: %s", ep, seq, shot, exc)
        return UNKNOWN


def _resolve_version(ep, seq, shot):
    """Attempt to read version from CTXShotNode. Falls back to 'v001'."""
    try:
        from core.nodes.wrappers import CTXShotNode
        node = CTXShotNode.find_by_code(ep, seq, shot)
        if node:
            ver = getattr(node, 'ver', None) or getattr(node, 'version', None)
            if ver:
                return ver
    except Exception:
        pass
    return 'v001'
