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
        """Set parent gaffer in inheritance chain.
        
        Args:
            parent_gaffer (CTXLightGafferNode or str): Parent gaffer wrapper or node name
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")
        
        parent_node = parent_gaffer.node_name if isinstance(parent_gaffer, CTXLightGafferNode) else parent_gaffer
        
        # Connect parent gaffer
        cmds.connectAttr(
            "{}.message".format(parent_node),
            "{}.parentGaffer".format(self.node_name),
            force=True
        )
        
        # Also connect to parent's childGaffers
        cmds.connectAttr(
            "{}.message".format(self.node_name),
            "{}.childGaffers".format(parent_node),
            nextAvailable=True
        )
    
    def get_child_gaffers(self):
        """Get child gaffers that inherit from this gaffer.
        
        Returns:
            list: List of CTXLightGafferNode wrappers
        """
        if cmds is None:
            return []
        
        connections = cmds.listConnections(
            "{}.childGaffers".format(self.node_name),
            source=False,
            destination=True,
            plugs=False
        )
        
        if not connections:
            return []
        
        return [CTXLightGafferNode(node) for node in connections]
    
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

