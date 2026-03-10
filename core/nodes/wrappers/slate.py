"""CTXSlateNode wrapper -- analog of CTXLightGafferNode."""

try:
    import maya.cmds as cmds
except ImportError:
    cmds = None

from ..base import NodeWrapper
from ..schemas.slate import CTXSlateSchema


class CTXSlateNode(NodeWrapper):
    """Wrapper for CTX_Slate Maya nodes.

    Analog of CTXLightGafferNode. Stores per-scope render layer renderable
    overrides. Inherits from parent slate via parentSlate connection.

    Usage
    -----
    Create a master slate::

        master = CTXSlateNode.create(slateName='Master', slateType='master')

    Create a sequence-level slate that inherits from master::

        seq_slate = CTXSlateNode.create(slateName='sq0070', slateType='sequence',
                                        scopeCode='sq0070')
        seq_slate.set_parent_slate(master)

    Assign to sequence::

        seq_node.set_slate(seq_slate)
    """

    SCHEMA = CTXSlateSchema

    # ------------------------------------------------------------------
    # Layer management
    # ------------------------------------------------------------------

    def get_layers(self):
        """Return list of CTXSlateLayerNode wrappers connected to this slate.

        Returns:
            list[CTXSlateLayerNode]: Layer entries, order not guaranteed.
        """
        from core.nodes.wrappers.slate_layer import CTXSlateLayerNode
        if cmds is None:
            return []
        connected = cmds.listConnections(
            '{}.layers'.format(self.node_name),
            source=True,
            destination=False,
        ) or []
        return [CTXSlateLayerNode(n) for n in connected if cmds.objExists(n)]

    def get_layer_by_name(self, layer_name):
        """Return the CTXSlateLayerNode for a given render layer name, or None.

        Args:
            layer_name (str): Render layer name to look up.

        Returns:
            CTXSlateLayerNode or None
        """
        for layer in self.get_layers():
            try:
                if cmds.getAttr('{}.layerName'.format(layer.node_name)) == layer_name:
                    return layer
            except Exception:
                continue
        return None

    def add_layer(self, layer_name, renderable=True, enabled=False):
        """Create a CTXSlateLayerNode and connect it to this slate.

        If a layer with this name already exists in the slate, returns the
        existing node without creating a duplicate.

        Args:
            layer_name (str): Render layer name (must match scene layer exactly).
            renderable (bool): Initial renderable value.
            enabled (bool): Initial renderableEnabled value. Default False (inherit).

        Returns:
            CTXSlateLayerNode: The created or existing layer node.
        """
        from core.nodes.wrappers.slate_layer import CTXSlateLayerNode

        existing = self.get_layer_by_name(layer_name)
        if existing is not None:
            return existing

        layer_node = CTXSlateLayerNode.create(
            layerName=layer_name,
            renderable=renderable,
            renderableEnabled=enabled,
        )
        cmds.connectAttr(
            '{}.message'.format(layer_node.node_name),
            '{}.layers'.format(self.node_name),
            nextAvailable=True,
        )
        return layer_node

    def remove_layer(self, layer_name):
        """Disconnect and delete the CTXSlateLayerNode for a render layer.

        Args:
            layer_name (str): Render layer name to remove.
        """
        layer = self.get_layer_by_name(layer_name)
        if layer is None:
            return
        try:
            connections = cmds.listConnections(
                '{}.message'.format(layer.node_name),
                plugs=True,
                source=False,
                destination=True,
            ) or []
            for plug in connections:
                cmds.disconnectAttr('{}.message'.format(layer.node_name), plug)
            cmds.delete(layer.node_name)
        except Exception as exc:
            from core.logging_config import get_logger
            get_logger(__name__).error(
                'Failed to remove layer %s from slate: %s', layer_name, exc
            )

    # ------------------------------------------------------------------
    # Parent slate (inheritance chain)
    # ------------------------------------------------------------------

    def get_parent_slate(self):
        """Return the parent CTXSlateNode, or None.

        Returns:
            CTXSlateNode or None
        """
        if cmds is None:
            return None
        connected = cmds.listConnections(
            '{}.parentSlate'.format(self.node_name),
            source=True,
            destination=False,
        ) or []
        if connected:
            return CTXSlateNode(connected[0])
        return None

    def set_parent_slate(self, parent):
        """Wire a parent slate into this slate's parentSlate attribute.

        Args:
            parent (CTXSlateNode or str): Parent slate node or node name.
        """
        parent_name = parent if isinstance(parent, str) else parent.node_name
        cmds.connectAttr(
            '{}.message'.format(parent_name),
            '{}.parentSlate'.format(self.node_name),
            force=True,
        )

    def clear_parent_slate(self):
        """Remove the parentSlate connection, making this slate a root."""
        try:
            connected = cmds.listConnections(
                '{}.parentSlate'.format(self.node_name),
                source=True,
                destination=False,
                plugs=True,
            ) or []
            for plug in connected:
                cmds.disconnectAttr(plug, '{}.parentSlate'.format(self.node_name))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Enabled flag
    # ------------------------------------------------------------------

    def is_enabled(self):
        """Return True if this slate participates in chain resolution.

        Returns:
            bool
        """
        try:
            return bool(cmds.getAttr('{}.enabled'.format(self.node_name)))
        except Exception:
            return True

    def set_enabled(self, value):
        """Set the enabled flag.

        Args:
            value (bool): True to include this slate in chain resolution.
        """
        cmds.setAttr('{}.enabled'.format(self.node_name), bool(value))

    # ------------------------------------------------------------------
    # Class-level queries
    # ------------------------------------------------------------------

    @classmethod
    def list_all(cls):
        """Return all CTXSlateNode wrappers in the current scene.

        Returns:
            list[CTXSlateNode]
        """
        if cmds is None:
            return []
        nodes = cmds.ls(type='network') or []
        results = []
        for n in nodes:
            try:
                if cmds.getAttr('{}.ctx_type'.format(n)) == 'CTX_Slate':
                    results.append(cls(n))
            except Exception:
                continue
        return results
