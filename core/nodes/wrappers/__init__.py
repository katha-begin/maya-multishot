"""
Node wrapper classes for CTX pipeline.

This module contains high-level API wrappers for CTX nodes.
"""

from __future__ import absolute_import, division, print_function

try:
    import maya.cmds as _cmds
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False

from .sequence import CTXSequenceNode
from .gaffer import CTXLightGafferNode
from .light_context import CTXLightContextNode
from .light_originals import CTXLightOriginalsNode
from .shot import CTXShotNode
from .asset import CTXAssetNode
from .manager import CTXManagerNode
from .slate import CTXSlateNode
from .slate_layer import CTXSlateLayerNode
from .slate_originals import CTXSlateOriginalsNode

__all__ = [
    'MAYA_AVAILABLE',
    'CTXSequenceNode',
    'CTXLightGafferNode',
    'CTXLightContextNode',
    'CTXLightOriginalsNode',
    'CTXShotNode',
    'CTXAssetNode',
    'CTXManagerNode',
    'CTXSlateNode',
    'CTXSlateLayerNode',
    'CTXSlateOriginalsNode',
]

