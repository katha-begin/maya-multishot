"""
Wrapper class for CTX_LightGaffer node.

Provides high-level API for gaffer operations including:
- Creating gaffers
- Building inheritance chains
- Managing child/parent relationships
- Querying lights
"""

try:
    import maya.cmds as cmds
except ImportError:
    cmds = None

from ..base import NodeWrapper
from ..schemas.gaffer import CTXLightGafferSchema


class CTXLightGafferNode(NodeWrapper):
    """Wrapper for CTX_LightGaffer node.
    
    Provides high-level API for gaffer management and chain operations.
    """
    
    SCHEMA = CTXLightGafferSchema
    
    def get_parent_gaffer(self):
        """Get parent gaffer in inheritance chain.
        
        Returns:
            CTXLightGafferNode or None: Parent gaffer wrapper
        """
        if cmds is None:
            return None
        
        # Check for parentGaffer connection
        connections = cmds.listConnections(
            "{}.parentGaffer".format(self.node_name),
            source=True,
            destination=False,
            plugs=False
        )
        
        if connections:
            return CTXLightGafferNode(connections[0])
        
        return None
    
    def set_parent_gaffer(self, parent_gaffer):
        """Set parent gaffer in inheritance chain using unidirectional pattern.

        Creates ONE connection: ChildGaffer.message → ParentGaffer.parentGaffer

        Note: This creates the inheritance chain connection, NOT the ownership connection.
        Ownership is handled separately via Sequence.gaffer or Shot.gaffer.

        Args:
            parent_gaffer (CTXLightGafferNode or str): Parent gaffer wrapper or node name
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        parent_node = parent_gaffer.node_name if isinstance(parent_gaffer, CTXLightGafferNode) else parent_gaffer

        # Unidirectional connection: parent_gaffer.message → child_gaffer.parentGaffer
        # This creates the inheritance chain for attribute resolution
        cmds.connectAttr(
            "{}.message".format(parent_node),
            "{}.parentGaffer".format(self.node_name),
            force=True
        )
    
    def get_child_gaffers(self):
        """Get child gaffers that inherit from this gaffer using unidirectional pattern.

        Queries: ParentGaffer.message → ChildGaffer.parentGaffer
        Uses destination=True to find children that reference this gaffer as parent.

        Returns:
            list: List of CTXLightGafferNode wrappers
        """
        if cmds is None:
            return []

        # Query where this gaffer's .message is connected TO (destination=True)
        connections = cmds.listConnections(
            "{}.message".format(self.node_name),
            source=False,
            destination=True,
            type='network',
            plugs=False
        ) or []

        # Filter for CTX_LightGaffer nodes that have this as parentGaffer
        child_gaffers = []
        for conn in connections:
            if cmds.attributeQuery('ctx_type', node=conn, exists=True):
                node_type = cmds.getAttr('{}.ctx_type'.format(conn))
                if node_type == 'CTX_LightGaffer':
                    # Verify this connection is via parentGaffer attribute
                    parent_conn = cmds.listConnections(
                        "{}.parentGaffer".format(conn),
                        source=True,
                        destination=False,
                        plugs=False
                    ) or []
                    if self.node_name in parent_conn:
                        child_gaffers.append(CTXLightGafferNode(conn))

        return child_gaffers
    
    def get_lights(self):
        """Get all light context nodes in this gaffer.
        
        Returns:
            list: List of CTXLightContextNode wrappers
        """
        if cmds is None:
            return []
        
        from .light_context import CTXLightContextNode
        
        connections = cmds.listConnections(
            "{}.lights".format(self.node_name),
            source=False,
            destination=True,
            plugs=False
        )
        
        if not connections:
            return []
        
        return [CTXLightContextNode(node) for node in connections]
    
    def build_chain(self):
        """Build inheritance chain from this gaffer up to root.
        
        Returns:
            list: List of CTXLightGafferNode wrappers [self, parent, grandparent, ...]
        """
        chain = [self]
        current = self
        
        # Walk up the chain
        while True:
            parent = current.get_parent_gaffer()
            if parent is None:
                break
            chain.append(parent)
            current = parent
        
        return chain
    
    def get_gaffer_name(self):
        """Get human-readable gaffer name.
        
        Returns:
            str: Gaffer name
        """
        return self.get_attribute('gafferName')
    
    def get_gaffer_type(self):
        """Get gaffer type (master/sequence/shot/custom).
        
        Returns:
            str: Gaffer type
        """
        return self.get_attribute('gafferType')
    
    def is_enabled(self):
        """Check if gaffer is enabled.

        Returns:
            bool: True if enabled
        """
        return self.get_attribute('enabled')

    @staticmethod
    def list_all():
        """List all CTX_LightGaffer nodes in scene.

        Returns:
            list: List of CTXLightGafferNode wrappers
        """
        if cmds is None:
            return []

        gaffers = []
        all_nodes = cmds.ls(type='network')

        for node in all_nodes:
            if cmds.attributeQuery('ctx_type', node=node, exists=True):
                node_type = cmds.getAttr('{}.ctx_type'.format(node))
                if node_type == 'CTX_LightGaffer':
                    gaffers.append(CTXLightGafferNode(node))

        return gaffers

