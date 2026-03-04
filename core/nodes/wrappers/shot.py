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
    - Creating shot nodes
    - Manual wiring to sequences and managers
    - Managing assets
    - Managing shot-level gaffer (direct ownership - NEW!)
    - Frame range operations
    """
    
    SCHEMA = CTXShotSchema
    
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

        from .gaffer import CTXLightGafferNode

        # Get gaffer node name
        if isinstance(gaffer, CTXLightGafferNode):
            gaffer_node = gaffer.node_name
        else:
            gaffer_node = str(gaffer)

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
            if cmds.attributeQuery('ctx_node_type', node=conn, exists=True):
                node_type = cmds.getAttr('{}.ctx_node_type'.format(conn))
                if node_type == 'CTX_Manager':
                    return conn

        return None

    def get_assets(self):
        """Get all asset nodes connected to this shot.

        Returns:
            list: List of asset node names
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        if not cmds.objExists(self.node_name):
            return []

        connections = cmds.listConnections(
            "{}.assets".format(self.node_name),
            source=True,
            destination=False
        ) or []

        return connections

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

    def get_shot_id(self):
        """Get full shot ID.

        Returns:
            str: Shot ID (e.g., 'Ep04_sq0070_SH0170')
        """
        ep = self.get_attribute('ep_code')
        seq = self.get_attribute('seq_code')
        shot = self.get_attribute('shot_code')
        return "{}_{}_{}" .format(ep, seq, shot)

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
            raise RuntimeError("Maya is not available")

        shots = []
        all_nodes = cmds.ls(type='network')
        for node in all_nodes:
            if cmds.attributeQuery('ctx_type', node=node, exists=True):
                node_type = cmds.getAttr('{}.ctx_type'.format(node))
                if node_type == 'CTX_Shot':
                    shots.append(CTXShotNode(node))
        return shots

