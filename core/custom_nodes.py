# -*- coding: utf-8 -*-
"""Custom Maya network nodes for Context Variables Pipeline.

This module defines custom network nodes for storing hierarchical context data:
- CTX_Manager: Root node managing global context and all shots
- CTX_Shot: Shot-specific node storing ep/seq/shot codes
- CTX_Asset: Asset-specific node storing asset metadata and file paths

Author: Context Variables Pipeline
Date: 2026-02-14
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False
    # Mock cmds for testing outside Maya
    class MockCmds(object):
        def __init__(self):
            self._nodes = {}  # Track created nodes
            self._node_counter = 0

        def createNode(self, node_type, **kwargs):
            self._node_counter += 1
            name = kwargs.get('name', 'node{}'.format(self._node_counter))
            self._nodes[name] = {'type': node_type, 'attrs': {}}
            return name

        def ls(self, *args, **kwargs):
            node_type = kwargs.get('type')
            if node_type:
                return [n for n, data in self._nodes.items() if data['type'] == node_type]
            return list(self._nodes.keys())

        def objExists(self, obj):
            # Handle attribute queries (node.attr)
            if '.' in obj:
                node_name = obj.split('.')[0]
                return node_name in self._nodes
            return obj in self._nodes

        def addAttr(self, node, **kwargs):
            if node in self._nodes:
                attr_name = kwargs.get('longName')
                if attr_name:
                    self._nodes[node]['attrs'][attr_name] = None

        def setAttr(self, attr_path, value=None, **kwargs):
            if '.' in attr_path:
                node_name, attr_name = attr_path.split('.', 1)
                if node_name in self._nodes:
                    self._nodes[node_name]['attrs'][attr_name] = value

        def getAttr(self, attr_path):
            if '.' in attr_path:
                node_name, attr_name = attr_path.split('.', 1)
                if node_name in self._nodes:
                    return self._nodes[node_name]['attrs'].get(attr_name)
            return None

        def connectAttr(self, *args, **kwargs):
            pass

        def listConnections(self, *args, **kwargs):
            return []

        def delete(self, node):
            if node in self._nodes:
                del self._nodes[node]

    cmds = MockCmds()


# Node type names
CTX_MANAGER_TYPE = "network"
CTX_SHOT_TYPE = "network"
CTX_ASSET_TYPE = "network"

# Node name prefixes
CTX_MANAGER_PREFIX = "CTX_Manager"
CTX_SHOT_PREFIX = "CTX_Shot"
CTX_ASSET_PREFIX = "CTX_Asset"


class CTXManagerNode(object):
    """CTX_Manager custom network node.
    
    This is the root node that stores global context and manages all shots in the scene.
    Only one CTX_Manager should exist per scene (singleton pattern).
    
    Attributes:
        config_path (str): Path to project configuration file
        project_root (str): Project root directory
        active_shot_id (str): ID of currently active shot
    
    Example:
        >>> manager = CTXManagerNode.create_manager('/path/to/config.json')
        >>> manager.set_config_path('/new/path/config.json')
        >>> shots = manager.get_shots()
    """
    
    def __init__(self, node_name):
        """Initialize CTX_Manager node wrapper.
        
        Args:
            node_name (str): Name of the Maya node
        """
        self.node_name = node_name
    
    @classmethod
    def create_manager(cls, config_path=None):
        """Create a new CTX_Manager node.
        
        Args:
            config_path (str, optional): Path to configuration file
        
        Returns:
            CTXManagerNode: New manager node instance
        
        Raises:
            RuntimeError: If a manager already exists
        """
        # Check if manager already exists
        existing = cls.get_manager()
        if existing is not None:
            raise RuntimeError(
                "CTX_Manager already exists: {}. Only one manager allowed per scene.".format(
                    existing.node_name
                )
            )
        
        # Create network node
        node_name = cmds.createNode(CTX_MANAGER_TYPE, name=CTX_MANAGER_PREFIX)
        
        # Add custom attributes
        cmds.addAttr(node_name, longName='ctx_type', dataType='string')
        cmds.setAttr(node_name + '.ctx_type', 'CTX_Manager', type='string')
        
        cmds.addAttr(node_name, longName='config_path', dataType='string')
        cmds.addAttr(node_name, longName='project_root', dataType='string')
        cmds.addAttr(node_name, longName='active_shot_id', dataType='string')
        
        # Set config path if provided
        if config_path:
            cmds.setAttr(node_name + '.config_path', config_path, type='string')
        
        return cls(node_name)
    
    @classmethod
    def get_manager(cls):
        """Get existing CTX_Manager node (singleton).
        
        Returns:
            CTXManagerNode: Existing manager node, or None if not found
        """
        # Find all network nodes
        network_nodes = cmds.ls(type=CTX_MANAGER_TYPE) or []
        
        # Filter for CTX_Manager nodes
        for node in network_nodes:
            if node.startswith(CTX_MANAGER_PREFIX):
                # Check if it has ctx_type attribute
                if cmds.objExists(node + '.ctx_type'):
                    ctx_type = cmds.getAttr(node + '.ctx_type')
                    if ctx_type == 'CTX_Manager':
                        return cls(node)
        
        return None

    def set_config_path(self, config_path):
        """Set configuration file path.

        Args:
            config_path (str): Path to configuration file
        """
        cmds.setAttr(self.node_name + '.config_path', config_path, type='string')

    def get_config_path(self):
        """Get configuration file path.

        Returns:
            str: Configuration file path
        """
        return cmds.getAttr(self.node_name + '.config_path')

    def set_project_root(self, project_root):
        """Set project root directory.

        Args:
            project_root (str): Project root directory
        """
        cmds.setAttr(self.node_name + '.project_root', project_root, type='string')

    def get_project_root(self):
        """Get project root directory.

        Returns:
            str: Project root directory
        """
        return cmds.getAttr(self.node_name + '.project_root')

    def set_active_shot_id(self, shot_id):
        """Set active shot ID.

        Args:
            shot_id (str): Shot ID (e.g., 'Ep04_sq0070_SH0170')
        """
        cmds.setAttr(self.node_name + '.active_shot_id', shot_id, type='string')

    def get_active_shot_id(self):
        """Get active shot ID.

        Returns:
            str: Active shot ID
        """
        return cmds.getAttr(self.node_name + '.active_shot_id')

    def get_shots(self):
        """Get all shot nodes connected to this manager.

        Returns:
            list: List of CTXShotNode instances
        """
        # This will be implemented after CTXShotNode is defined
        # For now, return empty list
        return []

    def delete(self):
        """Delete this manager node."""
        if cmds.objExists(self.node_name):
            cmds.delete(self.node_name)

    def exists(self):
        """Check if this node exists in the scene.

        Returns:
            bool: True if node exists
        """
        return cmds.objExists(self.node_name)

    def __repr__(self):
        """String representation.

        Returns:
            str: String representation
        """
        return "CTXManagerNode('{}')".format(self.node_name)


class CTXShotNode(object):
    """CTX_Shot custom network node.

    This node stores shot-specific context (ep, seq, shot codes) and manages
    assets for that shot.

    Attributes:
        ep_code (str): Episode code (e.g., 'Ep04')
        seq_code (str): Sequence code (e.g., 'sq0070')
        shot_code (str): Shot code (e.g., 'SH0170')
        display_layer_name (str): Associated display layer name
        is_active (bool): Whether this shot is currently active

    Example:
        >>> shot = CTXShotNode.create_shot('Ep04', 'sq0070', 'SH0170')
        >>> shot.set_active(True)
        >>> assets = shot.get_assets()
    """

    def __init__(self, node_name):
        """Initialize CTX_Shot node wrapper.

        Args:
            node_name (str): Name of the Maya node
        """
        self.node_name = node_name

    @classmethod
    def create_shot(cls, ep_code, seq_code, shot_code, manager_node=None):
        """Create a new CTX_Shot node.

        Args:
            ep_code (str): Episode code
            seq_code (str): Sequence code
            shot_code (str): Shot code
            manager_node (CTXManagerNode, optional): Parent manager node

        Returns:
            CTXShotNode: New shot node instance
        """
        # Create node name
        shot_id = "{}_{}_{}" .format(ep_code, seq_code, shot_code)
        node_name = cmds.createNode(CTX_SHOT_TYPE, name="{}_{}" .format(CTX_SHOT_PREFIX, shot_id))

        # Add custom attributes
        cmds.addAttr(node_name, longName='ctx_type', dataType='string')
        cmds.setAttr(node_name + '.ctx_type', 'CTX_Shot', type='string')

        cmds.addAttr(node_name, longName='ep_code', dataType='string')
        cmds.setAttr(node_name + '.ep_code', ep_code, type='string')

        cmds.addAttr(node_name, longName='seq_code', dataType='string')
        cmds.setAttr(node_name + '.seq_code', seq_code, type='string')

        cmds.addAttr(node_name, longName='shot_code', dataType='string')
        cmds.setAttr(node_name + '.shot_code', shot_code, type='string')

        cmds.addAttr(node_name, longName='display_layer_name', dataType='string')
        layer_name = "CTX_{}_{}_{}".format(ep_code, seq_code, shot_code)
        cmds.setAttr(node_name + '.display_layer_name', layer_name, type='string')

        cmds.addAttr(node_name, longName='is_active', attributeType='bool')
        cmds.setAttr(node_name + '.is_active', False)

        # Connect to manager if provided
        if manager_node and manager_node.exists():
            # Add message attribute for connection if not exists
            if not cmds.objExists(node_name + '.manager'):
                cmds.addAttr(node_name, longName='manager', attributeType='message')
            if not cmds.objExists(manager_node.node_name + '.shots'):
                cmds.addAttr(manager_node.node_name, longName='shots', attributeType='message', multi=True)

            # Connect shot to manager
            # Find next available index
            connections = cmds.listConnections(manager_node.node_name + '.shots', source=True, destination=False) or []
            next_index = len(connections)
            cmds.connectAttr(node_name + '.manager', manager_node.node_name + '.shots[{}]'.format(next_index))

        return cls(node_name)

    def get_ep_code(self):
        """Get episode code.

        Returns:
            str: Episode code
        """
        return cmds.getAttr(self.node_name + '.ep_code')

    def get_seq_code(self):
        """Get sequence code.

        Returns:
            str: Sequence code
        """
        return cmds.getAttr(self.node_name + '.seq_code')

    def get_shot_code(self):
        """Get shot code.

        Returns:
            str: Shot code
        """
        return cmds.getAttr(self.node_name + '.shot_code')

    def get_shot_id(self):
        """Get full shot ID.

        Returns:
            str: Shot ID (e.g., 'Ep04_sq0070_SH0170')
        """
        return "{}_{}_{}" .format(
            self.get_ep_code(),
            self.get_seq_code(),
            self.get_shot_code()
        )

    def get_display_layer_name(self):
        """Get display layer name.

        Returns:
            str: Display layer name
        """
        return cmds.getAttr(self.node_name + '.display_layer_name')

    def is_active(self):
        """Check if this shot is active.

        Returns:
            bool: True if active
        """
        return cmds.getAttr(self.node_name + '.is_active')

    def set_active(self, active):
        """Set shot active state.

        Args:
            active (bool): Active state
        """
        cmds.setAttr(self.node_name + '.is_active', active)

    def get_assets(self):
        """Get all asset nodes connected to this shot.

        Returns:
            list: List of CTXAssetNode instances
        """
        # This will be implemented after CTXAssetNode is defined
        return []

    def delete(self):
        """Delete this shot node."""
        if cmds.objExists(self.node_name):
            cmds.delete(self.node_name)

    def exists(self):
        """Check if this node exists.

        Returns:
            bool: True if exists
        """
        return cmds.objExists(self.node_name)

    def __repr__(self):
        """String representation.

        Returns:
            str: String representation
        """
        return "CTXShotNode('{}')".format(self.node_name)


class CTXAssetNode(object):
    """CTX_Asset custom network node.

    This node stores asset-specific metadata and file paths for a particular
    asset instance in a shot.

    Attributes:
        asset_type (str): Asset type (e.g., 'CHAR', 'PROP')
        asset_name (str): Asset name (e.g., 'CatStompie')
        variant (str): Asset variant (e.g., '001')
        namespace (str): Maya namespace
        file_path (str): Path to asset file
        version (str): Asset version (e.g., 'v003')

    Example:
        >>> asset = CTXAssetNode.create_asset('CHAR', 'CatStompie', '001')
        >>> asset.set_file_path('/path/to/asset.abc')
        >>> asset.set_version('v003')
    """

    def __init__(self, node_name):
        """Initialize CTX_Asset node wrapper.

        Args:
            node_name (str): Name of the Maya node
        """
        self.node_name = node_name

    @classmethod
    def create_asset(cls, asset_type, asset_name, variant, shot_node=None):
        """Create a new CTX_Asset node.

        Args:
            asset_type (str): Asset type
            asset_name (str): Asset name
            variant (str): Asset variant
            shot_node (CTXShotNode, optional): Parent shot node

        Returns:
            CTXAssetNode: New asset node instance
        """
        # Create node name
        asset_id = "{}_{}_{}".format(asset_type, asset_name, variant)
        node_name = cmds.createNode(CTX_ASSET_TYPE, name="{}_{}" .format(CTX_ASSET_PREFIX, asset_id))

        # Add custom attributes
        cmds.addAttr(node_name, longName='ctx_type', dataType='string')
        cmds.setAttr(node_name + '.ctx_type', 'CTX_Asset', type='string')

        cmds.addAttr(node_name, longName='asset_type', dataType='string')
        cmds.setAttr(node_name + '.asset_type', asset_type, type='string')

        cmds.addAttr(node_name, longName='asset_name', dataType='string')
        cmds.setAttr(node_name + '.asset_name', asset_name, type='string')

        cmds.addAttr(node_name, longName='variant', dataType='string')
        cmds.setAttr(node_name + '.variant', variant, type='string')

        cmds.addAttr(node_name, longName='namespace', dataType='string')
        namespace = asset_id
        cmds.setAttr(node_name + '.namespace', namespace, type='string')

        cmds.addAttr(node_name, longName='file_path', dataType='string')
        cmds.addAttr(node_name, longName='version', dataType='string')

        # Connect to shot if provided
        if shot_node and shot_node.exists():
            # Add message attribute for connection if not exists
            if not cmds.objExists(node_name + '.shot'):
                cmds.addAttr(node_name, longName='shot', attributeType='message')
            if not cmds.objExists(shot_node.node_name + '.assets'):
                cmds.addAttr(shot_node.node_name, longName='assets', attributeType='message', multi=True)

            # Connect asset to shot
            connections = cmds.listConnections(shot_node.node_name + '.assets', source=True, destination=False) or []
            next_index = len(connections)
            cmds.connectAttr(node_name + '.shot', shot_node.node_name + '.assets[{}]'.format(next_index))

        return cls(node_name)

    def get_asset_type(self):
        """Get asset type.

        Returns:
            str: Asset type
        """
        return cmds.getAttr(self.node_name + '.asset_type')

    def get_asset_name(self):
        """Get asset name.

        Returns:
            str: Asset name
        """
        return cmds.getAttr(self.node_name + '.asset_name')

    def get_variant(self):
        """Get asset variant.

        Returns:
            str: Asset variant
        """
        return cmds.getAttr(self.node_name + '.variant')

    def get_namespace(self):
        """Get Maya namespace.

        Returns:
            str: Namespace
        """
        return cmds.getAttr(self.node_name + '.namespace')

    def set_namespace(self, namespace):
        """Set Maya namespace.

        Args:
            namespace (str): Namespace
        """
        cmds.setAttr(self.node_name + '.namespace', namespace, type='string')

    def get_file_path(self):
        """Get asset file path.

        Returns:
            str: File path
        """
        return cmds.getAttr(self.node_name + '.file_path')

    def set_file_path(self, file_path):
        """Set asset file path.

        Args:
            file_path (str): File path
        """
        cmds.setAttr(self.node_name + '.file_path', file_path, type='string')

    def get_version(self):
        """Get asset version.

        Returns:
            str: Version
        """
        return cmds.getAttr(self.node_name + '.version')

    def set_version(self, version):
        """Set asset version.

        Args:
            version (str): Version
        """
        cmds.setAttr(self.node_name + '.version', version, type='string')

    def delete(self):
        """Delete this asset node."""
        if cmds.objExists(self.node_name):
            cmds.delete(self.node_name)

    def exists(self):
        """Check if this node exists.

        Returns:
            bool: True if exists
        """
        return cmds.objExists(self.node_name)

    def __repr__(self):
        """String representation.

        Returns:
            str: String representation
        """
        return "CTXAssetNode('{}')".format(self.node_name)

