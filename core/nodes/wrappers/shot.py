"""
Wrapper for CTX_Shot node.

Provides high-level API for shot node operations including manual wiring.
"""

try:
    import maya.cmds as cmds
except ImportError:
    cmds = None

from ..base import NodeWrapper
from ..schemas import CTXShotSchema


class CTXShotNode(NodeWrapper):
    """Wrapper for CTX_Shot node.

    Provides methods for:
    - Creating shot nodes (named CTX_Shot_{ep}_{seq}_{shot})
    - Manual wiring to sequences and managers
    - Managing assets
    - Managing shot-level gaffer (direct ownership)
    - Frame range operations
    """

    SCHEMA = CTXShotSchema

    @classmethod
    def create(cls, **kwargs):
        """Create shot node with legacy-compatible naming.

        Node name format: CTX_Shot_{ep_code}_{seq_code}_{shot_code}
        Example: CTX_Shot_Ep04_sq0070_SH0170

        Args:
            **kwargs: Initial attribute values (ep_code, seq_code, shot_code, etc.)

        Returns:
            CTXShotNode: New shot node instance
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        ep_code = kwargs.get('ep_code', '')
        seq_code = kwargs.get('seq_code', '')
        shot_code = kwargs.get('shot_code', '')

        # Create node using parent class (gets auto-prefixed name)
        instance = super().create(**kwargs)

        # Rename to specific pattern if all codes are provided
        if ep_code and seq_code and shot_code:
            desired_name = 'CTX_Shot_{}_{}_{}'.format(ep_code, seq_code, shot_code)
            try:
                new_name = cmds.rename(instance.node_name, desired_name)
                instance.node_name = new_name
            except Exception:
                pass  # Keep auto-generated name if rename fails

        return instance

    # Manual wiring methods
    
    def set_parent_sequence(self, sequence):
        """Wire this shot to a parent sequence using unidirectional pattern.

        Creates ONE connection: Shot.message → Sequence.shots[i]

        Args:
            sequence: CTXSequenceNode instance or node name string

        Example:
            shot.set_parent_sequence(seq)
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        # Get node name
        sequence_node = sequence.node_name if hasattr(sequence, 'node_name') else sequence

        # Verify nodes exist
        if not cmds.objExists(self.node_name):
            raise ValueError("Shot node does not exist: {}".format(self.node_name))
        if not cmds.objExists(sequence_node):
            raise ValueError("Sequence node does not exist: {}".format(sequence_node))

        # Unidirectional connection: shot.message → sequence.shots[i]
        # Parent (sequence) owns children (shots)
        cmds.connectAttr(
            "{}.message".format(self.node_name),
            "{}.shots".format(sequence_node),
            nextAvailable=True
        )
    
    def set_manager(self, manager):
        """Wire this shot to a manager using unidirectional pattern (for backward compatibility).

        Creates ONE connection: Shot.message → Manager.shots[i]

        Args:
            manager: CTXManagerNode instance or node name string

        Example:
            shot.set_manager(mgr)
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        # Get node name
        manager_node = manager.node_name if hasattr(manager, 'node_name') else manager

        # Verify nodes exist
        if not cmds.objExists(self.node_name):
            raise ValueError("Shot node does not exist: {}".format(self.node_name))
        if not cmds.objExists(manager_node):
            raise ValueError("Manager node does not exist: {}".format(manager_node))

        # Unidirectional connection: shot.message → manager.shots[i]
        # Parent (manager) owns children (shots)
        cmds.connectAttr(
            "{}.message".format(self.node_name),
            "{}.shots".format(manager_node),
            nextAvailable=True
        )
    
    def add_asset(self, asset):
        """Wire an asset to this shot using unidirectional pattern.

        Creates ONE connection: Asset.message → Shot.assets[i]

        Args:
            asset: CTXAssetNode instance or node name string

        Example:
            shot.add_asset(asset)
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        # Get node name
        asset_node = asset.node_name if hasattr(asset, 'node_name') else asset

        # Verify nodes exist
        if not cmds.objExists(self.node_name):
            raise ValueError("Shot node does not exist: {}".format(self.node_name))
        if not cmds.objExists(asset_node):
            raise ValueError("Asset node does not exist: {}".format(asset_node))

        # Unidirectional connection: asset.message → shot.assets[i]
        # Parent (shot) owns children (assets)
        cmds.connectAttr(
            "{}.message".format(asset_node),
            "{}.assets".format(self.node_name),
            nextAvailable=True
        )

    def set_gaffer(self, gaffer):
        """Wire this shot to a shot-level gaffer using unidirectional pattern (direct ownership).

        Creates ONE connection: Gaffer.message → Shot.gaffer

        Args:
            gaffer: CTXLightGafferNode instance or node name string

        Example:
            shot.set_gaffer(shot_gaffer)
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        # Get gaffer node name — use str check to avoid isinstance failure after reload
        gaffer_node = gaffer if isinstance(gaffer, str) else gaffer.node_name

        # Verify nodes exist
        if not cmds.objExists(self.node_name):
            raise ValueError("Shot node does not exist: {}".format(self.node_name))
        if not cmds.objExists(gaffer_node):
            raise ValueError("Gaffer node does not exist: {}".format(gaffer_node))

        # Unidirectional connection: gaffer.message → shot.gaffer
        # Shot owns gaffer (direct ownership)
        cmds.connectAttr(
            "{}.message".format(gaffer_node),
            "{}.gaffer".format(self.node_name),
            force=True
        )

    # Query methods

    def get_parent_sequence(self):
        """Get parent sequence node using unidirectional pattern.

        Queries: Shot.message → Sequence.shots[i]
        Uses destination=True to traverse from child to parent.

        Returns:
            str: Sequence node name, or None if not connected
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        if not cmds.objExists(self.node_name):
            return None

        # Query where shot.message is connected TO (destination=True)
        connections = cmds.listConnections(
            "{}.message".format(self.node_name),
            source=False,
            destination=True,
            type='network',
            plugs=False
        ) or []

        # Filter for CTX_Sequence nodes
        for conn in connections:
            if cmds.attributeQuery('ctx_type', node=conn, exists=True):
                node_type = cmds.getAttr('{}.ctx_type'.format(conn))
                if node_type == 'CTX_Sequence':
                    return conn

        return None

    def get_manager(self):
        """Get manager node using unidirectional pattern (for backward compatibility).

        Queries: Shot.message → Manager.shots[i]
        Uses destination=True to traverse from child to parent.

        Returns:
            str: Manager node name, or None if not connected
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        if not cmds.objExists(self.node_name):
            return None

        # Query where shot.message is connected TO (destination=True)
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

    def get_assets(self):
        """Get all asset nodes connected to this shot.

        Returns:
            list: List of CTXAssetNode instances
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        if not cmds.objExists(self.node_name):
            return []

        from .asset import CTXAssetNode

        connections = cmds.listConnections(
            "{}.assets".format(self.node_name),
            source=True,
            destination=False
        ) or []

        return [CTXAssetNode(n) for n in connections]

    def get_gaffer(self):
        """Get connected shot-level gaffer (NEW!).

        Returns:
            str: Gaffer node name, or None if not connected
        """
        if cmds is None:
            return None

        if not cmds.objExists(self.node_name):
            return None

        connections = cmds.listConnections(
            "{}.gaffer".format(self.node_name),
            source=True,
            destination=False,
            plugs=False
        ) or []

        return connections[0] if connections else None

    def _ensure_slate_attr(self):
        """Add the slate message attribute if absent (nodes created pre-Phase-6)."""
        if cmds is not None and not cmds.attributeQuery('slate', node=self.node_name, exists=True):
            cmds.addAttr(self.node_name, longName='slate', attributeType='message')

    def get_slate(self):
        """Return the CTXSlateNode assigned to this shot, or None.

        Returns:
            CTXSlateNode or None
        """
        from core.nodes.wrappers.slate import CTXSlateNode
        if cmds is None:
            return None
        self._ensure_slate_attr()
        connected = cmds.listConnections(
            '{}.slate'.format(self.node_name),
            source=True,
            destination=False,
        ) or []
        if connected:
            return CTXSlateNode(connected[0])
        return None

    def set_slate(self, slate):
        """Connect a CTXSlateNode to this shot.

        Args:
            slate (CTXSlateNode or str): Slate node or node name.
        """
        self._ensure_slate_attr()
        slate_name = slate if isinstance(slate, str) else slate.node_name
        cmds.connectAttr(
            '{}.message'.format(slate_name),
            '{}.slate'.format(self.node_name),
            force=True,
        )

    def clear_slate(self):
        """Remove the slate connection from this shot."""
        try:
            self._ensure_slate_attr()
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

    def get_frame_range(self):
        """Get shot frame range.

        Returns:
            tuple: (start_frame, end_frame)
        """
        start = self.get_attribute('start_frame')
        end = self.get_attribute('end_frame')
        return (start, end)

    def set_frame_range(self, start, end):
        """Set shot frame range.

        Args:
            start (int): Start frame
            end (int): End frame
        """
        self.set_attribute('start_frame', int(start))
        self.set_attribute('end_frame', int(end))

    def set_fps(self, fps):
        """Set frames per second.

        Args:
            fps (float): Frames per second
        """
        self.set_attribute('fps', float(fps))

    def get_ep_code(self):
        """Get episode code.

        Returns:
            str: Episode code (e.g., 'Ep04')
        """
        return self.get_attribute('ep_code')

    def get_seq_code(self):
        """Get sequence code.

        Returns:
            str: Sequence code (e.g., 'sq0070')
        """
        return self.get_attribute('seq_code')

    def get_shot_code(self):
        """Get shot code.

        Returns:
            str: Shot code (e.g., 'SH0170')
        """
        return self.get_attribute('shot_code')

    def is_active(self):
        """Check whether this shot is currently active.

        Returns:
            bool: True if active
        """
        return bool(self.get_attribute('is_active'))

    def set_active(self, state):
        """Set the active state of this shot.

        Args:
            state (bool): True to mark as active, False to deactivate
        """
        self.set_attribute('is_active', bool(state))

    def get_shot_id(self):
        """Get full shot ID.

        Returns:
            str: Shot ID (e.g., 'Ep04_sq0070_SH0170')
        """
        ep = self.get_attribute('ep_code')
        seq = self.get_attribute('seq_code')
        shot = self.get_attribute('shot_code')
        return "{}_{}_{}".format(ep, seq, shot)

    # Lock convenience methods

    def lock(self, user=None):
        """Lock this shot node."""
        from core.lock_manager import LockManager
        LockManager.lock_node(self.node_name, user=user)

    def unlock(self):
        """Unlock this shot node."""
        from core.lock_manager import LockManager
        LockManager.unlock_node(self.node_name)

    def is_locked(self):
        """Return True if this shot is locked directly or via its sequence."""
        from core.lock_manager import LockManager
        return LockManager.is_effectively_locked(self.node_name)

    def get_lock_info(self):
        """Return lock metadata dict."""
        from core.lock_manager import LockManager
        return LockManager.get_lock_info(self.node_name)

    # Discovery methods

    @staticmethod
    def find_by_code(ep_code, seq_code, shot_code):
        """Find shot node by codes.

        Args:
            ep_code (str): Episode code
            seq_code (str): Sequence code
            shot_code (str): Shot code

        Returns:
            CTXShotNode: Shot node instance, or None if not found
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        all_nodes = cmds.ls(type='network')
        for node in all_nodes:
            if cmds.attributeQuery('ctx_type', node=node, exists=True):
                node_type = cmds.getAttr('{}.ctx_type'.format(node))
                if node_type == 'CTX_Shot':
                    ep = cmds.getAttr('{}.ep_code'.format(node))
                    seq = cmds.getAttr('{}.seq_code'.format(node))
                    shot = cmds.getAttr('{}.shot_code'.format(node))
                    if ep == ep_code and seq == seq_code and shot == shot_code:
                        return CTXShotNode(node)
        return None

    @staticmethod
    def list_all():
        """List all CTX_Shot nodes in scene.

        Returns:
            list: List of CTXShotNode instances
        """
        if cmds is None:
            return []

        shots = []
        all_nodes = cmds.ls(type='network')
        for node in all_nodes:
            if cmds.attributeQuery('ctx_type', node=node, exists=True):
                node_type = cmds.getAttr('{}.ctx_type'.format(node))
                if node_type == 'CTX_Shot':
                    shots.append(CTXShotNode(node))
        return shots

