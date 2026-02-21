"""
Gaffer system for hierarchical light management.

This module provides the core gaffer functionality:
- GafferManager: Add/remove lights, manage gaffers
- AttributeResolver: Chain walking and attribute resolution
- LightOperations: Apply/sync light values
- ChainOperations: Build and validate gaffer chains
"""

from .manager import GafferManager
from .resolver import AttributeResolver
from .light_ops import LightOperations
from .chain_ops import ChainOperations

__all__ = [
    'GafferManager',
    'AttributeResolver',
    'LightOperations',
    'ChainOperations',
]

