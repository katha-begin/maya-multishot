"""
Node schema definitions for CTX pipeline.

This module contains declarative schema definitions for all CTX node types.
"""

from .gaffer import CTXLightGafferSchema
from .light_context import CTXLightContextSchema

__all__ = [
    'CTXLightGafferSchema',
    'CTXLightContextSchema',
]

