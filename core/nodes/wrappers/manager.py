"""
Wrapper for CTX_Manager node.

Provides high-level API for manager node operations including manual wiring.
The manager is a singleton - only one should exist per scene.
"""

try:
    import maya.cmds as cmds
except ImportError:
    cmds = None

from ..base import NodeWrapper
from ..schemas import CTXManagerSchema


class CTXManagerNode(NodeWrapper):
    """Wrapper for CTX_Manager node.
    
    Provides methods for:
    - Creating manager node (singleton)
    - Manual wiring to sequences and shots
    - Project configuration management
    
    Note: Only one CTX_Manager should exist per scene.
    """
    
    SCHEMA = CTXManagerSchema
    
    @classmethod
    def create(cls, **kwargs):
        """Create new manager node (singleton check).
        
        Args:
            **kwargs: Initial attribute values
            
        Returns:
            CTXManagerNode: Manager node instance
            
        Raises:
            RuntimeError: If manager already exists
        """
        # Check if manager already exists
        existing = cls.get_manager()
        if existing is not None:
            raise RuntimeError(
                "CTX_Manager already exists: {}. Only one manager allowed per scene.".format(
                    existing.node_name
                )
            )
        
        # Create using parent class method
        return super(CTXManagerNode, cls).create(**kwargs)
    
    # Manual wiring methods
    
    def add_sequence(self, sequence):
        """Wire a sequence to this manager using unidirectional pattern.

        Creates ONE connection: Sequence.message → Manager.sequences[i]

        Args:
            sequence: CTXSequenceNode instance or node name string

        Example:
            manager.add_sequence(seq)
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        # Get node name
        sequence_node = sequence.node_name if hasattr(sequence, 'node_name') else sequence

        # Verify nodes exist
        if not cmds.objExists(self.node_name):
            raise ValueError("Manager node does not exist: {}".format(self.node_name))
        if not cmds.objExists(sequence_node):
            raise ValueError("Sequence node does not exist: {}".format(sequence_node))

        # Unidirectional connection: sequence.message → manager.sequences[i]
        # Parent (manager) owns children (sequences)
        cmds.connectAttr(
            "{}.message".format(sequence_node),
            "{}.sequences".format(self.node_name),
            nextAvailable=True
        )
    
    def add_shot(self, shot):
        """Wire a shot to this manager using unidirectional pattern (for backward compatibility).

        Creates ONE connection: Shot.message → Manager.shots[i]

        Args:
            shot: CTXShotNode instance or node name string

        Example:
            manager.add_shot(shot)
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        # Get node name
        shot_node = shot.node_name if hasattr(shot, 'node_name') else shot

        # Verify nodes exist
        if not cmds.objExists(self.node_name):
            raise ValueError("Manager node does not exist: {}".format(self.node_name))
        if not cmds.objExists(shot_node):
            raise ValueError("Shot node does not exist: {}".format(shot_node))

        # Unidirectional connection: shot.message → manager.shots[i]
        # Parent (manager) owns children (shots)
        cmds.connectAttr(
            "{}.message".format(shot_node),
            "{}.shots".format(self.node_name),
            nextAvailable=True
        )
    
    # Query methods
    
    def get_sequences(self):
        """Get all sequence nodes connected to this manager.
        
        Returns:
            list: List of sequence node names
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")
        
        if not cmds.objExists(self.node_name):
            return []
        
        connections = cmds.listConnections(
            "{}.sequences".format(self.node_name),
            source=True,
            destination=False
        ) or []
        
        return connections
    
    def get_shots(self):
        """Get all shot nodes connected to this manager.
        
        Returns:
            list: List of shot node names
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")
        
        if not cmds.objExists(self.node_name):
            return []
        
        connections = cmds.listConnections(
            "{}.shots".format(self.node_name),
            source=True,
            destination=False
        ) or []

        return connections

    # Discovery methods

    @staticmethod
    def get_manager():
        """Get existing CTX_Manager node (singleton).

        Returns:
            CTXManagerNode: Existing manager node, or None if not found
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        all_nodes = cmds.ls(type='network')
        for node in all_nodes:
            if cmds.attributeQuery('ctx_type', node=node, exists=True):
                node_type = cmds.getAttr('{}.ctx_type'.format(node))
                if node_type == 'CTX_Manager':
                    return CTXManagerNode(node)
        return None

