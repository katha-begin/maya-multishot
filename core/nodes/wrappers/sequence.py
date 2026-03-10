"""
Wrapper class for CTX_Sequence node.

Provides high-level API for sequence operations including:
- Creating sequences manually
- Connecting to manager
- Connecting to shots
- Connecting to gaffer
"""

try:
    import maya.cmds as cmds
except ImportError:
    cmds = None

from ..base import NodeWrapper
from ..schemas.sequence import CTXSequenceSchema


class CTXSequenceNode(NodeWrapper):
    """Wrapper for CTX_Sequence node.
    
    Provides high-level API for sequence management and manual wiring.
    
    Example:
        >>> # Create sequence manually
        >>> seq = CTXSequenceNode.create(
        ...     sequenceCode='sq0070',
        ...     sequenceName='Sequence 70',
        ...     frameStart=1001,
        ...     frameEnd=1200
        ... )
        >>> 
        >>> # Wire to manager manually
        >>> seq.set_parent_manager(manager_node)
        >>> 
        >>> # Wire to gaffer manually
        >>> seq.set_gaffer(gaffer_node)
    """
    
    SCHEMA = CTXSequenceSchema

    @classmethod
    def create(cls, **kwargs):
        """Create sequence node with sequence-code-based naming.

        Node name format: CTX_Sequence_{sequenceCode}
        Example: CTX_Sequence_sq0070

        Args:
            **kwargs: Initial attribute values. 'sequenceCode' drives the node name.

        Returns:
            CTXSequenceNode: New sequence node instance
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        seq_code = kwargs.get('sequenceCode', '')

        instance = super().create(**kwargs)

        if seq_code:
            desired_name = 'CTX_Sequence_{}'.format(seq_code)
            try:
                new_name = cmds.rename(instance.node_name, desired_name)
                instance.node_name = new_name
            except Exception:
                pass  # Keep auto-generated name if rename fails

        return instance

    def get_sequence_code(self):
        """Get sequence code.
        
        Returns:
            str: Sequence code (e.g., 'sq0070')
        """
        return self.get_attribute('sequenceCode')
    
    def get_sequence_name(self):
        """Get sequence name.
        
        Returns:
            str: Human-readable sequence name
        """
        return self.get_attribute('sequenceName')
    
    def get_frame_range(self):
        """Get frame range.
        
        Returns:
            tuple: (start_frame, end_frame)
        """
        start = self.get_attribute('frameStart')
        end = self.get_attribute('frameEnd')
        return (start, end)
    
    def set_parent_manager(self, manager):
        """Connect to parent manager using unidirectional pattern.

        Creates ONE connection: Sequence.message → Manager.sequences[i]

        Args:
            manager (CTXManagerNode or str): Manager wrapper or node name
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        # Get manager node name
        if hasattr(manager, 'node_name'):
            manager_node = manager.node_name
        else:
            manager_node = str(manager)

        # Unidirectional connection: sequence.message → manager.sequences[i]
        # Parent (manager) owns children (sequences)
        cmds.connectAttr(
            "{}.message".format(self.node_name),
            "{}.sequences".format(manager_node),
            nextAvailable=True
        )
    
    def get_parent_manager(self):
        """Get parent manager using unidirectional pattern.

        Queries: Sequence.message → Manager.sequences[i]
        Uses destination=True to traverse from child to parent.

        Returns:
            str or None: Manager node name
        """
        if cmds is None:
            return None

        # Query where sequence.message is connected TO (destination=True)
        connections = cmds.listConnections(
            "{}.message".format(self.node_name),
            source=False,
            destination=True,
            type='network',
            plugs=False
        ) or []

        # Filter for CTX_Manager nodes
        for conn in connections:
            if cmds.attributeQuery('ctx_type', node=conn, exists=True):
                node_type = cmds.getAttr('{}.ctx_type'.format(conn))
                if node_type == 'CTX_Manager':
                    return conn

        return None
    
    def set_gaffer(self, gaffer):
        """Connect to sequence gaffer using unidirectional pattern.

        Creates ONE connection: Gaffer.message → Sequence.gaffer

        Args:
            gaffer (CTXLightGafferNode or str): Gaffer wrapper or node name
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        # Get gaffer node name — use str check to avoid isinstance failure after reload
        gaffer_node = gaffer if isinstance(gaffer, str) else gaffer.node_name

        # Unidirectional connection: gaffer.message → sequence.gaffer
        # Sequence owns gaffer (direct ownership)
        cmds.connectAttr(
            "{}.message".format(gaffer_node),
            "{}.gaffer".format(self.node_name),
            force=True
        )

    def get_gaffer(self):
        """Get connected gaffer.

        Returns:
            str or None: Gaffer node name
        """
        if cmds is None:
            return None

        connections = cmds.listConnections(
            "{}.gaffer".format(self.node_name),
            source=True,
            destination=False,
            plugs=False
        )

        return connections[0] if connections else None

    def get_slate(self):
        """Return the CTXSlateNode assigned to this sequence, or None.

        Returns:
            CTXSlateNode or None
        """
        from core.nodes.wrappers.slate import CTXSlateNode
        if cmds is None:
            return None
        connected = cmds.listConnections(
            '{}.slate'.format(self.node_name),
            source=True,
            destination=False,
        ) or []
        if connected:
            return CTXSlateNode(connected[0])
        return None

    def set_slate(self, slate):
        """Connect a CTXSlateNode to this sequence.

        Args:
            slate (CTXSlateNode or str): Slate node or node name.
        """
        slate_name = slate if isinstance(slate, str) else slate.node_name
        cmds.connectAttr(
            '{}.message'.format(slate_name),
            '{}.slate'.format(self.node_name),
            force=True,
        )

    def clear_slate(self):
        """Remove the slate connection from this sequence."""
        try:
            connected = cmds.listConnections(
                '{}.slate'.format(self.node_name),
                source=True,
                destination=False,
                plugs=True,
            ) or []
            for plug in connected:
                cmds.disconnectAttr(plug, '{}.slate'.format(self.node_name))
        except Exception:
            pass

    def add_shot(self, shot):
        """Connect a shot to this sequence.

        Args:
            shot (CTXShotNode or str): Shot wrapper or node name
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        # Get shot node name
        if hasattr(shot, 'node_name'):
            shot_node = shot.node_name
        else:
            shot_node = str(shot)

        # Connect: shot.message → sequence.shots (multi)
        cmds.connectAttr(
            "{}.message".format(shot_node),
            "{}.shots".format(self.node_name),
            nextAvailable=True
        )

    def get_shots(self):
        """Get all connected shots.

        Returns:
            list: List of CTXShotNode instances
        """
        if cmds is None:
            return []

        from .shot import CTXShotNode

        connections = cmds.listConnections(
            "{}.shots".format(self.node_name),
            source=True,
            destination=False,
            plugs=False
        ) or []

        return [CTXShotNode(n) for n in connections]

    # Lock convenience methods

    def lock(self, user=None):
        """Lock this sequence node."""
        from core.lock_manager import LockManager
        LockManager.lock_node(self.node_name, user=user)

    def unlock(self):
        """Unlock this sequence node."""
        from core.lock_manager import LockManager
        LockManager.unlock_node(self.node_name)

    def is_locked(self):
        """Return True if this sequence is locked."""
        from core.lock_manager import LockManager
        return LockManager.is_locked(self.node_name)

    def get_lock_info(self):
        """Return lock metadata dict."""
        from core.lock_manager import LockManager
        return LockManager.get_lock_info(self.node_name)

    @staticmethod
    def find_by_code(sequence_code):
        """Find sequence by sequence code.

        Args:
            sequence_code (str): Sequence code to search for

        Returns:
            CTXSequenceNode or None: Found sequence wrapper
        """
        if cmds is None:
            return None

        # Search all network nodes
        all_nodes = cmds.ls(type='network')

        for node in all_nodes:
            # Check if it's a CTX_Sequence
            if cmds.attributeQuery('ctx_type', node=node, exists=True):
                node_type = cmds.getAttr('{}.ctx_type'.format(node))
                if node_type == 'CTX_Sequence':
                    # Check sequence code
                    if cmds.attributeQuery('sequenceCode', node=node, exists=True):
                        code = cmds.getAttr('{}.sequenceCode'.format(node))
                        if code == sequence_code:
                            return CTXSequenceNode(node)

        return None

    @staticmethod
    def list_all():
        """List all CTX_Sequence nodes in scene.

        Returns:
            list: List of CTXSequenceNode wrappers
        """
        if cmds is None:
            return []

        sequences = []
        all_nodes = cmds.ls(type='network')

        for node in all_nodes:
            if cmds.attributeQuery('ctx_type', node=node, exists=True):
                node_type = cmds.getAttr('{}.ctx_type'.format(node))
                if node_type == 'CTX_Sequence':
                    sequences.append(CTXSequenceNode(node))

        return sequences

