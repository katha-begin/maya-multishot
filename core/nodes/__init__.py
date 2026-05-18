"""
Schema-based node system for CTX pipeline.

This module provides a declarative, schema-based approach to creating and managing
Maya custom nodes with centralized definitions, type safety, and extensibility.

IMPORTANT: This module also re-exports NodeManager from the legacy core.nodes module
to maintain backward compatibility with existing code (ui/main_window.py).
"""

from __future__ import absolute_import, division, print_function

from .base import NodeSchema, NodeFactory, NodeWrapper

# Import NodeManager from the parent core module (core/nodes.py file)
# This maintains backward compatibility with existing code
import sys
import os

# Get the parent directory (core/)
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import from core.nodes module (the file, not this package)
# We need to import it as a module to avoid circular imports
import importlib.util
nodes_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'nodes.py')
spec = importlib.util.spec_from_file_location("core.nodes_legacy", nodes_file)
nodes_legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nodes_legacy)

NodeManager = nodes_legacy.NodeManager
NODE_TYPE_AI_STANDIN = nodes_legacy.NODE_TYPE_AI_STANDIN
NODE_TYPE_RS_PROXY = nodes_legacy.NODE_TYPE_RS_PROXY
NODE_TYPE_REFERENCE = nodes_legacy.NODE_TYPE_REFERENCE

__all__ = [
    'NodeSchema',
    'NodeFactory',
    'NodeWrapper',
    'NodeManager',  # Legacy support
    'NODE_TYPE_AI_STANDIN',
    'NODE_TYPE_RS_PROXY',
    'NODE_TYPE_REFERENCE',
]

