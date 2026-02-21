"""
Schema-based node system for CTX pipeline.

This module provides a declarative, schema-based approach to creating and managing
Maya custom nodes with centralized definitions, type safety, and extensibility.
"""

from .base import NodeSchema, NodeFactory, NodeWrapper

__all__ = [
    'NodeSchema',
    'NodeFactory',
    'NodeWrapper',
]

