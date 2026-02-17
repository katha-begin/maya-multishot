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

        def nodeType(self, node):
            if node in self._nodes:
                return self._nodes[node].get('type')
            return None

        def referenceQuery(self, node, **kwargs):
            # Mock reference query - always return False
            return False

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

        # Add message attribute for shot connections (multi-attribute)
        cmds.addAttr(node_name, longName='shots', attributeType='message', multi=True)

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
        # Check if shots attribute exists (for backward compatibility)
        if not cmds.objExists(self.node_name + '.shots'):
            # Add it if missing
            cmds.addAttr(self.node_name, longName='shots', attributeType='message', multi=True)
            return []

        # Get all connected shot nodes via the 'shots' attribute
        connections = cmds.listConnections(
            self.node_name + '.shots',
            source=True,
            destination=False
        ) or []

        # Wrap each node in CTXShotNode
        shot_nodes = []
        for node_name in connections:
            # Verify it's a CTX_Shot node
            if node_name.startswith(CTX_SHOT_PREFIX):
                shot_nodes.append(CTXShotNode(node_name))

        return shot_nodes

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

        # Add message attribute for display layer connection
        cmds.addAttr(node_name, longName='display_layer_link', attributeType='message')

        cmds.addAttr(node_name, longName='is_active', attributeType='bool')
        cmds.setAttr(node_name + '.is_active', False)

        # Frame range attributes
        cmds.addAttr(node_name, longName='start_frame', attributeType='long')
        cmds.setAttr(node_name + '.start_frame', 1001)  # Default start frame

        cmds.addAttr(node_name, longName='end_frame', attributeType='long')
        cmds.setAttr(node_name + '.end_frame', 1100)  # Default end frame (100 frames)

        cmds.addAttr(node_name, longName='frame_offset', attributeType='long')
        cmds.setAttr(node_name + '.frame_offset', 0)  # Default no offset

        cmds.addAttr(node_name, longName='fps', attributeType='double')
        cmds.setAttr(node_name + '.fps', 24.0)  # Default 24 fps

        cmds.addAttr(node_name, longName='handles', attributeType='long')
        cmds.setAttr(node_name + '.handles', 10)  # Default 10 frame handles

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

    def get_frame_range(self):
        """Get frame range for this shot.

        Returns:
            tuple: (start_frame, end_frame)
        """
        start = cmds.getAttr(self.node_name + '.start_frame')
        end = cmds.getAttr(self.node_name + '.end_frame')
        return (start, end)

    def set_frame_range(self, start_frame, end_frame):
        """Set frame range for this shot.

        Args:
            start_frame (int): Start frame number
            end_frame (int): End frame number
        """
        cmds.setAttr(self.node_name + '.start_frame', start_frame)
        cmds.setAttr(self.node_name + '.end_frame', end_frame)

    def get_fps(self):
        """Get frames per second for this shot.

        Returns:
            float: FPS value
        """
        return cmds.getAttr(self.node_name + '.fps')

    def set_fps(self, fps):
        """Set frames per second for this shot.

        Args:
            fps (float): FPS value (e.g., 24.0, 23.976, 30.0)
        """
        cmds.setAttr(self.node_name + '.fps', fps)

    def get_frame_offset(self):
        """Get frame offset for this shot.

        Returns:
            int: Frame offset value
        """
        return cmds.getAttr(self.node_name + '.frame_offset')

    def set_frame_offset(self, offset):
        """Set frame offset for this shot.

        Args:
            offset (int): Frame offset value
        """
        cmds.setAttr(self.node_name + '.frame_offset', offset)

    def get_handles(self):
        """Get handle frames for this shot.

        Returns:
            int: Number of handle frames
        """
        return cmds.getAttr(self.node_name + '.handles')

    def set_handles(self, handles):
        """Set handle frames for this shot.

        Args:
            handles (int): Number of handle frames
        """
        cmds.setAttr(self.node_name + '.handles', handles)

    def get_assets(self):
        """Get all asset nodes connected to this shot.

        Uses the multi-message 'assets' attribute to find connected CTX_Asset nodes.

        Returns:
            list: List of CTXAssetNode instances
        """
        if not cmds.objExists(self.node_name + '.assets'):
            return []

        connections = cmds.listConnections(
            self.node_name + '.assets', source=True, destination=False) or []

        result = []
        for conn in connections:
            # Verify it's a CTX_Asset node by checking ctx_type attribute
            if cmds.objExists(conn + '.ctx_type'):
                ctx_type = cmds.getAttr(conn + '.ctx_type')
                if ctx_type == 'CTX_Asset':
                    result.append(CTXAssetNode(conn))
        return result

    def link_display_layer(self, layer_name):
        """Link display layer to this shot node via message attribute.

        Args:
            layer_name (str): Display layer node name

        Returns:
            bool: True if linked successfully
        """
        if not cmds.objExists(layer_name):
            return False

        if not cmds.objExists(self.node_name + '.display_layer_link'):
            cmds.addAttr(self.node_name, longName='display_layer_link', attributeType='message')

        # Add message attribute to display layer if not exists
        if not cmds.objExists(layer_name + '.ctx_shot_link'):
            cmds.addAttr(layer_name, longName='ctx_shot_link', attributeType='message')

        # Connect: CTX_Shot.display_layer_link -> DisplayLayer.ctx_shot_link
        if not cmds.isConnected(layer_name + '.ctx_shot_link', self.node_name + '.display_layer_link'):
            cmds.connectAttr(layer_name + '.ctx_shot_link', self.node_name + '.display_layer_link', force=True)

        return True

    def get_linked_display_layer(self):
        """Get linked display layer node.

        Returns:
            str or None: Display layer node name, or None if not linked
        """
        if not cmds.objExists(self.node_name + '.display_layer_link'):
            return None

        connections = cmds.listConnections(
            self.node_name + '.display_layer_link',
            source=True,
            destination=False
        ) or []

        return connections[0] if connections else None

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
        # Create node name: CTX_Asset_TYPE_Name_SH#### (shot code, not variant!)
        # Namespace is TYPE_Name_Variant (from filename)
        if shot_node:
            shot_code = shot_node.get_shot_code()
            node_name = cmds.createNode(CTX_ASSET_TYPE, name="{}_{}_{}_{}".format(
                CTX_ASSET_PREFIX, asset_type, asset_name, shot_code))
        else:
            # Fallback if no shot provided
            node_name = cmds.createNode(CTX_ASSET_TYPE, name="{}_{}_{}".format(
                CTX_ASSET_PREFIX, asset_type, asset_name))

        # Add custom attributes
        cmds.addAttr(node_name, longName='ctx_type', dataType='string')
        cmds.setAttr(node_name + '.ctx_type', 'CTX_Asset', type='string')

        cmds.addAttr(node_name, longName='asset_type', dataType='string')
        cmds.setAttr(node_name + '.asset_type', asset_type, type='string')

        cmds.addAttr(node_name, longName='asset_name', dataType='string')
        cmds.setAttr(node_name + '.asset_name', asset_name, type='string')

        cmds.addAttr(node_name, longName='variant', dataType='string')
        cmds.setAttr(node_name + '.variant', variant, type='string')

        # Namespace: CHAR_CatStompie_001 (from filename, includes variant)
        # Special case for cameras: namespace is just the asset name (no type prefix, no variant)
        cmds.addAttr(node_name, longName='namespace', dataType='string')
        if asset_type == 'CAM':
            # For cameras: SWA_Ep04_SH0140_camera (shot-specific, no type prefix, no variant)
            namespace = asset_name
        else:
            # Standard assets: TYPE_Name_Variant
            namespace = "{}_{}_{}".format(asset_type, asset_name, variant)
        cmds.setAttr(node_name + '.namespace', namespace, type='string')

        cmds.addAttr(node_name, longName='file_path', dataType='string')
        cmds.addAttr(node_name, longName='template', dataType='string')
        cmds.addAttr(node_name, longName='extension', dataType='string')
        cmds.addAttr(node_name, longName='version', dataType='string')

        # Connect to shot if provided
        if shot_node and shot_node.exists():
            # Add message attributes for bidirectional connection
            if not cmds.objExists(node_name + '.shot_node'):
                cmds.addAttr(node_name, longName='shot_node', attributeType='message')
            if not cmds.objExists(shot_node.node_name + '.assets'):
                cmds.addAttr(shot_node.node_name, longName='assets', attributeType='message', multi=True)

            # Connect asset to shot (bidirectional)
            connections = cmds.listConnections(shot_node.node_name + '.assets', source=True, destination=False) or []
            next_index = len(connections)
            cmds.connectAttr(node_name + '.shot_node', shot_node.node_name + '.assets[{}]'.format(next_index))

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
        """Set asset file path (resolved/cached path).

        Args:
            file_path (str): File path
        """
        cmds.setAttr(self.node_name + '.file_path', file_path, type='string')

    def get_template(self):
        """Get path template with tokens.

        Returns:
            str: Template string (e.g., '$projRoot$project/$sceneBase/...')
        """
        if cmds.objExists(self.node_name + '.template'):
            return cmds.getAttr(self.node_name + '.template') or ''
        return ''

    def set_template(self, template):
        """Set path template with tokens.

        Args:
            template (str): Template string with $tokens
        """
        if not cmds.objExists(self.node_name + '.template'):
            cmds.addAttr(self.node_name, longName='template', dataType='string')
        cmds.setAttr(self.node_name + '.template', template, type='string')

    def get_extension(self):
        """Get file extension.

        Returns:
            str: File extension (e.g., 'abc', 'vdb')
        """
        if cmds.objExists(self.node_name + '.extension'):
            return cmds.getAttr(self.node_name + '.extension') or ''
        return ''

    def set_extension(self, extension):
        """Set file extension.

        Args:
            extension (str): File extension (e.g., 'abc')
        """
        if not cmds.objExists(self.node_name + '.extension'):
            cmds.addAttr(self.node_name, longName='extension', dataType='string')
        cmds.setAttr(self.node_name + '.extension', extension, type='string')

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

    def get_department(self):
        """Get department.

        Returns:
            str: Department (e.g., 'anim', 'layout')
        """
        if cmds.objExists(self.node_name + '.department'):
            return cmds.getAttr(self.node_name + '.department')
        return ''

    def set_department(self, department):
        """Set department.

        Args:
            department (str): Department
        """
        if not cmds.objExists(self.node_name + '.department'):
            cmds.addAttr(self.node_name, longName='department', dataType='string')
        cmds.setAttr(self.node_name + '.department', department, type='string')

    def get_maya_node(self):
        """Get linked Maya node.

        Returns:
            str: Maya node name, or None if not linked
        """
        if cmds.objExists(self.node_name + '.maya_node'):
            connections = cmds.listConnections(self.node_name + '.maya_node',
                                              source=False, destination=True)
            if connections:
                return connections[0]
        return None

    def set_maya_node(self, maya_node):
        """Link to Maya node using message attributes.

        Uses the new message attribute linking system with fallback for locked nodes.

        Args:
            maya_node (str): Maya node name

        Returns:
            bool: True if message connection succeeded, False if fallback was used
        """
        from core.ctx_linker import link_to_maya_node as link_func
        return link_func(self.node_name, maya_node)

    def get_linked_maya_node(self):
        """Get Maya node linked to this CTX_Asset.

        Queries message connection first, then falls back to string attribute.

        Returns:
            str or None: Maya node name if found, None otherwise
        """
        from core.ctx_linker import get_linked_maya_node as get_func
        return get_func(self.node_name)

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

