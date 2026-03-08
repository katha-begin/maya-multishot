"""
Node schema definitions for CTX pipeline.

This module contains declarative schema definitions for all CTX node types.
"""

from .sequence import CTXSequenceSchema
from .gaffer import CTXLightGafferSchema
from .light_context import CTXLightContextSchema
from .light_originals import CTXLightOriginalsSchema
from .shot import CTXShotSchema
from .asset import CTXAssetSchema
from .manager import CTXManagerSchema

__all__ = [
    'CTXSequenceSchema',
    'CTXLightGafferSchema',
    'CTXLightContextSchema',
    'CTXLightOriginalsSchema',
    'CTXShotSchema',
    'CTXAssetSchema',
    'CTXManagerSchema',
]

