"""
Renderer attribute maps for Maya lights.

Provides a unified interface for resolving Maya attribute names from
gaffer attribute names, accounting for renderer-specific naming differences.

Supported renderers: Redshift, Arnold, Maya default lights
"""

try:
    import maya.cmds as cmds
except ImportError:
    cmds = None

from .redshift import (
    ATTR_MAP as RS_ATTR_MAP,
    LIGHT_TYPES as RS_LIGHT_TYPES,
    LIGHT_TYPE_ATTR_OVERRIDES as RS_TYPE_OVERRIDES,
)
from .arnold import ATTR_MAP as AI_ATTR_MAP, LIGHT_TYPES as AI_LIGHT_TYPES


def get_node_type(node):
    """Get Maya node type for a light shape.

    Args:
        node (str): Node name

    Returns:
        str: Node type, or empty string if unavailable
    """
    if cmds is None:
        return ''
    try:
        return cmds.nodeType(node)
    except Exception:
        return ''


def get_maya_attr(light_shape, gaffer_attr):
    """Resolve the Maya attribute name for a gaffer attribute on a specific light.

    Detects the renderer from the light node type and returns the correct
    Maya attribute name. Returns None if the attribute is not supported
    by this light type.

    Args:
        light_shape (str): Maya light shape node name
        gaffer_attr (str): Gaffer attribute name (e.g., 'spread', 'affectDiffuse')

    Returns:
        str or None: Maya attribute name, or None if not supported
    """
    node_type = get_node_type(light_shape)

    if node_type in RS_LIGHT_TYPES:
        # Check per-type overrides first, then fall back to the shared map
        type_overrides = RS_TYPE_OVERRIDES.get(node_type, {})
        if gaffer_attr in type_overrides:
            return type_overrides[gaffer_attr]
        return RS_ATTR_MAP.get(gaffer_attr)

    if node_type in AI_LIGHT_TYPES:
        return AI_ATTR_MAP.get(gaffer_attr)

    # Maya default lights — try common names only
    MAYA_DEFAULT_ATTR_MAP = {
        'intensity': 'intensity',
        'color': 'color',
        'spread': None,
        'affectDiffuse': 'emitDiffuse',
        'affectSpecular': 'emitSpecular',
        'affectGI': None,
        'shadowEnable': 'useDepthMapShadows',
    }
    return MAYA_DEFAULT_ATTR_MAP.get(gaffer_attr)
