"""
Gaffer system for hierarchical light management.

This module provides the core gaffer functionality:
- GafferManager: Add/remove lights, manage gaffers
- AttributeResolver: Chain walking and attribute resolution
- LightOperations: Capture/apply light values
"""

from .manager import GafferManager
from .resolver import AttributeResolver

__all__ = [
    'GafferManager',
    'AttributeResolver',
]

