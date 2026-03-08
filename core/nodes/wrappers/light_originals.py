"""
Wrapper for CTX_LightOriginals node.

Singleton node that persists original Maya light values (pre-gaffer baseline)
inside the Maya scene. Values survive save/reload without re-capture.

Capture happens when a light is first added to any gaffer via GafferManager.
"""

from __future__ import absolute_import
from __future__ import print_function

import json

try:
    import maya.cmds as cmds
except ImportError:
    cmds = None

from ..base import NodeWrapper
from ..schemas.light_originals import CTXLightOriginalsSchema


class CTXLightOriginalsNode(NodeWrapper):
    """Wrapper for CTX_LightOriginals singleton node."""

    SCHEMA = CTXLightOriginalsSchema

    @staticmethod
    def get_or_create():
        """Return the existing CTX_LightOriginals node or create one.

        Returns:
            CTXLightOriginalsNode: Singleton wrapper instance

        Raises:
            RuntimeError: If Maya is not available
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        for node in cmds.ls(type='network') or []:
            if cmds.attributeQuery('ctx_type', node=node, exists=True):
                if cmds.getAttr('{}.ctx_type'.format(node)) == 'CTX_LightOriginals':
                    return CTXLightOriginalsNode(node)

        return CTXLightOriginalsNode.create()

    # ------------------------------------------------------------------
    # JSON load/save helpers
    # ------------------------------------------------------------------

    def _load(self):
        """Read and parse the stored JSON dict.

        Returns:
            dict: {light_shape: {attr: value}}
        """
        raw = cmds.getAttr('{}.originalsJson'.format(self.node_name)) or '{}'
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return {}

    def _save(self, data):
        """Serialize and write the JSON dict.

        Args:
            data (dict): {light_shape: {attr: value}}
        """
        cmds.setAttr(
            '{}.originalsJson'.format(self.node_name),
            json.dumps(data),
            type='string'
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def has_light(self, light_shape):
        """Check whether originals have been stored for a light.

        Args:
            light_shape (str): Maya light shape node name

        Returns:
            bool: True if originals are stored
        """
        return light_shape in self._load()

    def store_light(self, light_shape, values):
        """Store pre-captured original values for a light.

        Called by GafferManager.add_light_to_gaffer when a light is first
        registered into the gaffer system.

        Args:
            light_shape (str): Maya light shape node name
            values (dict): Flat values dict from GafferManager.capture_light_values
        """
        data = self._load()
        data[light_shape] = values
        self._save(data)

    def get_light_values(self, light_shape):
        """Get stored original values for a light.

        Args:
            light_shape (str): Maya light shape node name

        Returns:
            dict or None: Stored values dict, or None if not captured
        """
        return self._load().get(light_shape)

    def get_all_originals(self):
        """Return all stored originals.

        Returns:
            dict: {light_shape: values_dict}
        """
        return self._load()

    def remove_light(self, light_shape):
        """Remove stored originals for a light (e.g., when light is deleted).

        Args:
            light_shape (str): Maya light shape node name
        """
        data = self._load()
        if light_shape in data:
            del data[light_shape]
            self._save(data)

    def clear(self):
        """Clear all stored originals."""
        self._save({})
