"""CTXSlateLayerNode wrapper -- analog of CTXLightContextNode."""

from __future__ import absolute_import, division, print_function

try:
    import maya.cmds as cmds
except ImportError:
    cmds = None

from ..base import NodeWrapper
from ..schemas.slate_layer import CTXSlateLayerSchema


class CTXSlateLayerNode(NodeWrapper):
    """Wrapper for CTX_SlateLayer Maya nodes.

    Stores the renderable override value and its enabled flag for one
    render layer within a slate.
    """

    SCHEMA = CTXSlateLayerSchema

    def get_layer_name(self):
        """Return the render layer name stored on this node.

        Returns:
            str: Layer name.
        """
        try:
            return cmds.getAttr('{}.layerName'.format(self.node_name)) or ''
        except Exception:
            return ''

    def get_renderable(self):
        """Return the stored renderable value.

        Returns:
            bool
        """
        try:
            return bool(cmds.getAttr('{}.renderable'.format(self.node_name)))
        except Exception:
            return True

    def set_renderable(self, value):
        """Set the renderable value.

        Args:
            value (bool): Renderable state to store.
        """
        cmds.setAttr('{}.renderable'.format(self.node_name), bool(value))

    def is_override_enabled(self):
        """Return True if renderableEnabled is True (this slate owns the value).

        Returns:
            bool
        """
        try:
            return bool(cmds.getAttr('{}.renderableEnabled'.format(self.node_name)))
        except Exception:
            return False

    def set_override_enabled(self, value):
        """Set renderableEnabled flag.

        Args:
            value (bool): True = this slate overrides renderable.
                          False = inherit from parent slate.
        """
        cmds.setAttr('{}.renderableEnabled'.format(self.node_name), bool(value))

    def set_override(self, renderable, enabled=True):
        """Convenience: set renderable value and enable the override in one call.

        Args:
            renderable (bool): Renderable state.
            enabled (bool): Whether to enable the override. Default True.
        """
        self.set_renderable(renderable)
        self.set_override_enabled(enabled)

    def to_dict(self):
        """Return layer state as a dict for snapshotting.

        Returns:
            dict: {'layerName': str, 'renderable': bool, 'renderableEnabled': bool}
        """
        return {
            'layerName': self.get_layer_name(),
            'renderable': self.get_renderable(),
            'renderableEnabled': self.is_override_enabled(),
        }
