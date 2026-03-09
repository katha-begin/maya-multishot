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

    @classmethod
    def create(cls, **kwargs):
        """Create asset node with per-shot naming.

        Node name format: CTX_Asset_{assetType}_{assetName}_{shotCode}
        Example: CTX_Asset_CHAR_CatStompie_SH0140

        Each shot gets its own CTX_Asset node. Multiple CTX_Asset nodes that
        represent the same Maya reference share the same 'namespace' attribute
        value and are each linked via ReferenceNode.message -> CTX_Asset.targetNode.

        Args:
            **kwargs: Initial attribute values. 'asset_type', 'asset_name', and
                      'shot_code' drive the node name. 'shot_code' is consumed
                      here and not passed to NodeFactory.

        Returns:
            CTXAssetNode: New asset node instance
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        asset_type = kwargs.get('asset_type', '')
        asset_name = kwargs.get('asset_name', '')
        shot_code = kwargs.pop('shot_code', '')  # consumed here, not a schema attribute

        instance = super().create(**kwargs)

        if asset_type and asset_name and shot_code:
            desired_name = 'CTX_Asset_{}_{}_{}'.format(asset_type, asset_name, shot_code)
            try:
                new_name = cmds.rename(instance.node_name, desired_name)
                instance.node_name = new_name
            except Exception:
                pass  # Keep auto-generated name if rename fails

        return instance

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
    
    def get_asset_type(self):
        """Get asset type.

        Returns:
            str: Asset type (e.g., 'CHAR', 'PROP', 'CAM')
        """
        return self.get_attribute('asset_type')

    def get_asset_name(self):
        """Get asset name.

        Returns:
            str: Asset name (e.g., 'CatStompie')
        """
        return self.get_attribute('asset_name')

    def get_variant(self):
        """Get asset variant.

        Returns:
            str: Variant (e.g., '001')
        """
        return self.get_attribute('variant')

    def get_namespace(self):
        """Get Maya namespace for this asset.

        Returns:
            str: Namespace string
        """
        return self.get_attribute('namespace')

    def get_department(self):
        """Get department.

        Returns:
            str: Department (e.g., 'lighting')
        """
        return self.get_attribute('department')

    def set_department(self, dept):
        """Set department.

        Args:
            dept (str): Department name
        """
        self.set_attribute('department', dept)

    def set_version(self, version):
        """Set asset version.

        Args:
            version (str): Version string (e.g., 'v003')
        """
        self.set_attribute('version', version)

    def set_template(self, template):
        """Set path template string.

        Args:
            template (str): Template with tokens (e.g., '$projRoot$project/...')
        """
        self.set_attribute('template', template)

    def set_extension(self, ext):
        """Set file extension.

        Args:
            ext (str): Extension without dot (e.g., 'abc')
        """
        self.set_attribute('extension', ext)

    def get_version(self):
        """Get asset version.

        Returns:
            str: Version string (e.g., 'v003')
        """
        return self.get_attribute('version')

    def get_template(self):
        """Get path template string.

        Returns:
            str: Template with tokens (e.g., '$projRoot$project/...')
        """
        return self.get_attribute('template')

    def get_extension(self):
        """Get file extension.

        Returns:
            str: Extension without dot (e.g., 'abc')
        """
        return self.get_attribute('extension')

    def get_file_path(self):
        """Get resolved/cached file path.

        Returns:
            str: Absolute file path
        """
        return self.get_attribute('file_path')

    def set_file_path(self, path):
        """Set resolved/cached file path.

        Args:
            path (str): Absolute file path
        """
        self.set_attribute('file_path', path)

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

