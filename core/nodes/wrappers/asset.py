"""
Wrapper for CTX_Asset node.

Provides high-level API for asset node operations including manual wiring.
"""

try:
    import maya.cmds as cmds
except ImportError:
    cmds = None

from ..base import NodeWrapper
from ..schemas import CTXAssetSchema


class CTXAssetNode(NodeWrapper):
    """Wrapper for CTX_Asset node.
    
    Provides methods for:
    - Creating asset nodes
    - Manual wiring to shots
    - File path and version management
    """
    
    SCHEMA = CTXAssetSchema
    
    # Manual wiring methods
    
    def set_parent_shot(self, shot):
        """Wire this asset to a parent shot using unidirectional pattern.

        Creates ONE connection: Asset.message → Shot.assets[i]

        Args:
            shot: CTXShotNode instance or node name string

        Example:
            asset.set_parent_shot(shot)
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        # Get node name
        shot_node = shot.node_name if hasattr(shot, 'node_name') else shot

        # Verify nodes exist
        if not cmds.objExists(self.node_name):
            raise ValueError("Asset node does not exist: {}".format(self.node_name))
        if not cmds.objExists(shot_node):
            raise ValueError("Shot node does not exist: {}".format(shot_node))

        # Unidirectional connection: asset.message → shot.assets[i]
        # Parent (shot) owns children (assets)
        cmds.connectAttr(
            "{}.message".format(self.node_name),
            "{}.assets".format(shot_node),
            nextAvailable=True
        )
    
    # Query methods
    
    def get_parent_shot(self):
        """Get parent shot node using unidirectional pattern.

        Queries: Asset.message → Shot.assets[i]
        Uses destination=True to traverse from child to parent.

        Returns:
            str: Shot node name, or None if not connected
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        if not cmds.objExists(self.node_name):
            return None

        # Query where asset.message is connected TO (destination=True)
        connections = cmds.listConnections(
            "{}.message".format(self.node_name),
            source=False,
            destination=True,
            type='network',
            plugs=False
        ) or []

        # Filter for CTX_Shot nodes
        for conn in connections:
            if cmds.attributeQuery('ctx_type', node=conn, exists=True):
                node_type = cmds.getAttr('{}.ctx_type'.format(conn))
                if node_type == 'CTX_Shot':
                    return conn

        return None
    
    def get_asset_id(self):
        """Get asset identifier.
        
        Returns:
            str: Asset ID (e.g., 'CHAR_CatStompie_001')
        """
        asset_type = self.get_attribute('asset_type')
        asset_name = self.get_attribute('asset_name')
        variant = self.get_attribute('variant')
        return "{}_{}_{}".format(asset_type, asset_name, variant)
    
    # Discovery methods
    
    @staticmethod
    def find_by_name(asset_type, asset_name, variant):
        """Find asset node by type, name, and variant.
        
        Args:
            asset_type (str): Asset type
            asset_name (str): Asset name
            variant (str): Asset variant
            
        Returns:
            CTXAssetNode: Asset node instance, or None if not found
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")
        
        all_nodes = cmds.ls(type='network')
        for node in all_nodes:
            if cmds.attributeQuery('ctx_type', node=node, exists=True):
                node_type = cmds.getAttr('{}.ctx_type'.format(node))
                if node_type == 'CTX_Asset':
                    atype = cmds.getAttr('{}.asset_type'.format(node))
                    aname = cmds.getAttr('{}.asset_name'.format(node))
                    avar = cmds.getAttr('{}.variant'.format(node))
                    if atype == asset_type and aname == asset_name and avar == variant:
                        return CTXAssetNode(node)
        return None
    
    @staticmethod
    def list_all():
        """List all CTX_Asset nodes in scene.
        
        Returns:
            list: List of CTXAssetNode instances
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")
        
        assets = []
        all_nodes = cmds.ls(type='network')
        for node in all_nodes:
            if cmds.attributeQuery('ctx_type', node=node, exists=True):
                node_type = cmds.getAttr('{}.ctx_type'.format(node))
                if node_type == 'CTX_Asset':
                    assets.append(CTXAssetNode(node))
        return assets

