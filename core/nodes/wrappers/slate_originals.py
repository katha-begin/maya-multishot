"""Wrapper for CTX_SlateOriginals singleton node.

Stores and retrieves the original renderable state of render layers
before any slate override is applied. Mirrors CTXLightOriginalsNode.
"""

from __future__ import absolute_import

import json

try:
    import maya.cmds as cmds
except ImportError:
    cmds = None

from ..base import NodeWrapper
from ..schemas.slate_originals import CTXSlateOriginalsSchema
from core.logging_config import get_logger

logger = get_logger(__name__)


class CTXSlateOriginalsNode(NodeWrapper):
    """Singleton per-scene node storing original render layer renderable states."""

    SCHEMA = CTXSlateOriginalsSchema

    @classmethod
    def get_or_create(cls):
        """Return the existing originals node or create one.

        Returns:
            CTXSlateOriginalsNode: The singleton node.

        Raises:
            RuntimeError: If Maya is not available.
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        # Find existing node
        existing = cmds.ls(type='network') or []
        for node in existing:
            try:
                if cmds.attributeQuery('ctx_type', node=node, exists=True):
                    if cmds.getAttr('{}.ctx_type'.format(node)) == 'CTX_SlateOriginals':
                        return cls(node)
            except Exception:
                continue

        # Create new singleton
        return cls.create()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load(self):
        """Read and parse the stored JSON dict.

        Returns:
            dict: {layer_name: renderable_bool}
        """
        raw = cmds.getAttr('{}.originalsJson'.format(self.node_name)) or '{}'
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return {}

    def _save(self, data):
        """Serialize and write the JSON dict.

        Args:
            data (dict): {layer_name: renderable_bool}
        """
        cmds.setAttr(
            '{}.originalsJson'.format(self.node_name),
            json.dumps(data),
            type='string',
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def has_layer(self, layer_name):
        """Return True if the original state for this layer is stored.

        Args:
            layer_name (str): Render layer name.

        Returns:
            bool
        """
        return layer_name in self._load()

    def store_layer(self, layer_name, renderable):
        """Store the original renderable state for a render layer.

        Should be called only once per layer (before any slate override).
        Subsequent calls are no-ops if the layer is already stored.

        Args:
            layer_name (str): Render layer name.
            renderable (bool): Original renderable state.
        """
        data = self._load()
        if layer_name not in data:
            data[layer_name] = bool(renderable)
            self._save(data)
            logger.debug("Stored original renderable for %r: %s", layer_name, renderable)

    def get_layer_renderable(self, layer_name):
        """Return the original renderable state for a layer, or None if not stored.

        Args:
            layer_name (str): Render layer name.

        Returns:
            bool or None
        """
        return self._load().get(layer_name)

    def get_all(self):
        """Return the full {layer_name: renderable_bool} dict.

        Returns:
            dict
        """
        return self._load()

    def clear(self):
        """Remove all stored originals (use with caution -- one-way operation)."""
        self._save({})
        logger.debug("CTXSlateOriginalsNode cleared")
