# -*- coding: utf-8 -*-
"""Asset Manager - High-level tool for managing assets in shots.

This module provides asset management functionality:
- Add, remove, update assets
- Version management (update, rollback, compare)
- Asset replacement and duplication
- Asset validation
- Asset browser integration

Author: Pipeline TD
Date: 2024
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    # Mock Maya commands for testing outside Maya
    class MockCmds(object):
        """Mock Maya commands for testing."""
        
        def objExists(self, name):
            """Mock objExists."""
            return False
        
        def createNode(self, node_type, name=None, **kwargs):
            """Mock createNode."""
            return name if name else "node1"
        
        def delete(self, *nodes):
            """Mock delete."""
            pass
        
        def getAttr(self, attr):
            """Mock getAttr."""
            return None
        
        def setAttr(self, attr, value, **kwargs):
            """Mock setAttr."""
            pass
        
        def listConnections(self, node, **kwargs):
            """Mock listConnections."""
            return []
        
        def connectAttr(self, src, dst, **kwargs):
            """Mock connectAttr."""
            pass
        
        def addAttr(self, node, **kwargs):
            """Mock addAttr."""
            pass
    
    cmds = MockCmds()
    MAYA_AVAILABLE = False


class AssetManager(object):
    """High-level asset management tool.
    
    This class provides utilities to:
    - Add and remove assets from shots
    - Update asset versions
    - Replace and duplicate assets
    - Validate asset integrity
    - Browse available assets
    
    Example:
        >>> from tools.asset_manager import AssetManager
        >>> 
        >>> asset_mgr = AssetManager()
        >>> 
        >>> # Add asset to shot
        >>> asset_node = asset_mgr.add_asset(
        ...     'CTX_Shot_SH0170',
        ...     'CHAR', 'CatStompie', '002', 'v003',
        ...     '/path/to/asset.abc'
        ... )
        >>> 
        >>> # Update to latest version
        >>> asset_mgr.update_to_latest(asset_node)
    """
    
    def __init__(self, path_resolver=None, cache_manager=None, layer_manager=None):
        """Initialize asset manager.
        
        Args:
            path_resolver (PathResolver, optional): Path resolver for version lookup
            cache_manager (CacheManager, optional): Cache manager for asset discovery
            layer_manager (DisplayLayerManager, optional): Display layer manager
        """
        self.path_resolver = path_resolver
        self.cache_manager = cache_manager
        self.layer_manager = layer_manager
    
    def add_asset(self, shot_node, asset_type, asset_name, variant, version, file_path):
        """Add asset to shot.

        Creates a CTX_Asset node and links it to the CTX_Shot node using the proper
        CTXAssetNode.create_asset() method. Also creates the Maya node (aiStandIn,
        RedshiftProxyMesh, or reference) with proper namespace and links it to the
        CTX_Asset node using message attributes.

        Args:
            shot_node (str): CTX_Shot node name
            asset_type (str): Asset type (CHAR, PROP, ENV, VEH)
            asset_name (str): Asset name
            variant (str): Variant code (e.g., '002')
            version (str): Version (e.g., 'v003')
            file_path (str): Full path to asset file

        Returns:
            str: Created CTX_Asset node name

        Raises:
            ValueError: If shot node doesn't exist or file doesn't exist
        """
        from core.custom_nodes import CTXAssetNode, CTXShotNode
        from core.ctx_linker import link_to_maya_node
        from core.nodes import create_standin_with_namespace, create_redshift_proxy_with_namespace

        # Validate shot exists
        if not cmds.objExists(shot_node):
            raise ValueError("Shot node '{}' does not exist".format(shot_node))

        # Validate file exists
        if not os.path.exists(file_path):
            raise ValueError("Asset file '{}' does not exist".format(file_path))

        # Wrap shot node
        shot_node_obj = CTXShotNode(shot_node)

        # Create CTX_Asset node using proper method (this handles shot connection)
        asset_node_obj = CTXAssetNode.create_asset(
            asset_type=asset_type,
            asset_name=asset_name,
            variant=variant,
            shot_node=shot_node_obj
        )

        # Set file path and version
        asset_node_obj.set_file_path(file_path)
        asset_node_obj.set_version(version)

        # Build namespace: CHAR_ToriiMechSuit_001
        namespace = "{}_{}_{}".format(asset_type, asset_name, variant)

        # Determine node type from file extension and create Maya node
        ext = os.path.splitext(file_path)[1].lower()
        maya_node = None
        shape_node = None

        if ext == '.abc':
            # Create Arnold StandIn with namespace
            transform_node, shape_node = create_standin_with_namespace(namespace, file_path)
            maya_node = transform_node  # Store transform for display layer

            # Link shape node to CTX_Asset via message attribute
            link_to_maya_node(asset_node_obj.node_name, shape_node)

        elif ext in ['.ma', '.mb']:
            # Create Reference with namespace
            from core.reference_manager import reference_file
            ref_node = reference_file(file_path, namespace)
            if ref_node:
                maya_node = ref_node
                # Link reference node to CTX_Asset
                link_to_maya_node(asset_node_obj.node_name, ref_node)

        elif ext == '.rs':
            # Create Redshift Proxy with namespace
            transform_node, shape_node = create_redshift_proxy_with_namespace(namespace, file_path)
            maya_node = transform_node  # Store transform for display layer

            # Link shape node to CTX_Asset via message attribute
            link_to_maya_node(asset_node_obj.node_name, shape_node)

        # Assign to display layer if available
        if self.layer_manager and maya_node:
            ep = cmds.getAttr("{}.ep".format(shot_node))
            seq = cmds.getAttr("{}.seq".format(shot_node))
            shot = cmds.getAttr("{}.shot".format(shot_node))
            layer = self.layer_manager.get_layer_for_shot(ep, seq, shot)
            if layer:
                self.layer_manager.assign_to_layer(maya_node, layer)

        logger.info("Created CTX_Asset: {} linked to Maya node: {}".format(
            asset_node_obj.node_name, maya_node))

        return asset_node_obj.node_name

    def remove_asset(self, asset_node):
        """Remove asset from shot and delete Maya node.

        Args:
            asset_node (str): CTX_Asset node name

        Returns:
            bool: True if successful
        """
        if not cmds.objExists(asset_node):
            raise ValueError("Asset node '{}' does not exist".format(asset_node))

        # Get Maya node
        maya_node = cmds.getAttr("{}.maya_node".format(asset_node))

        # Delete Maya node if exists
        if maya_node and cmds.objExists(maya_node):
            cmds.delete(maya_node)

        # Delete asset node
        cmds.delete(asset_node)

        return True

    def update_asset_version(self, asset_node, new_version):
        """Update asset to a different version.

        Args:
            asset_node (str): CTX_Asset node name
            new_version (str): New version (e.g., 'v004')

        Returns:
            bool: True if successful
        """
        if not cmds.objExists(asset_node):
            raise ValueError("Asset node '{}' does not exist".format(asset_node))

        # Get current path
        old_path = cmds.getAttr("{}.path".format(asset_node))

        # Build new path by replacing version
        old_version = cmds.getAttr("{}.version".format(asset_node))
        new_path = old_path.replace(old_version, new_version)

        # Validate new path exists
        if not os.path.exists(new_path):
            raise ValueError("New version path '{}' does not exist".format(new_path))

        # Update version attribute
        cmds.setAttr("{}.version".format(asset_node), new_version, type='string')
        cmds.setAttr("{}.path".format(asset_node), new_path, type='string')

        # Update Maya node path
        maya_node = cmds.getAttr("{}.maya_node".format(asset_node))
        if maya_node and cmds.objExists(maya_node):
            ext = os.path.splitext(new_path)[1].lower()

            if ext == '.abc':
                cmds.setAttr("{}.dso".format(maya_node), new_path, type='string')
            elif ext == '.rs':
                cmds.setAttr("{}.fileName".format(maya_node), new_path, type='string')

        return True

    def get_asset_info(self, asset_node):
        """Get asset metadata.

        Args:
            asset_node (str): CTX_Asset node name

        Returns:
            dict: Asset information
        """
        if not cmds.objExists(asset_node):
            raise ValueError("Asset node '{}' does not exist".format(asset_node))

        # Get attributes
        info = {
            'node': asset_node,
            'assetType': cmds.getAttr("{}.assetType".format(asset_node)) or '',
            'assetName': cmds.getAttr("{}.assetName".format(asset_node)) or '',
            'variant': cmds.getAttr("{}.variant".format(asset_node)) or '',
            'version': cmds.getAttr("{}.version".format(asset_node)) or '',
            'path': cmds.getAttr("{}.path".format(asset_node)) or '',
            'maya_node': cmds.getAttr("{}.maya_node".format(asset_node)) or '',
        }

        # Get shot connection
        shot = cmds.listConnections("{}.shot".format(asset_node), source=False, destination=True)
        info['shot'] = shot[0] if shot else None

        # Get file info
        path = info['path']
        if path and os.path.exists(path):
            info['file_size'] = os.path.getsize(path)
            info['file_exists'] = True
        else:
            info['file_size'] = 0
            info['file_exists'] = False

        return info

    def list_assets_for_shot(self, shot_node):
        """Get all assets in a shot.

        Args:
            shot_node (str): CTX_Shot node name

        Returns:
            list: List of CTX_Asset node names
        """
        if not cmds.objExists(shot_node):
            raise ValueError("Shot node '{}' does not exist".format(shot_node))

        # Get connected assets
        assets = cmds.listConnections("{}.assets".format(shot_node), source=True, destination=False) or []

        return assets

    def update_to_latest(self, asset_node):
        """Update asset to latest available version.

        Args:
            asset_node (str): CTX_Asset node name

        Returns:
            str: New version or None if already latest
        """
        if not cmds.objExists(asset_node):
            raise ValueError("Asset node '{}' does not exist".format(asset_node))

        # Get current version
        current_version = cmds.getAttr("{}.version".format(asset_node))

        # Get available versions from cache
        if not self.cache_manager:
            raise RuntimeError("Cache manager not available")

        # Get asset info
        asset_type = cmds.getAttr("{}.assetType".format(asset_node))
        asset_name = cmds.getAttr("{}.assetName".format(asset_node))
        variant = cmds.getAttr("{}.variant".format(asset_node))

        # Get shot context
        shot = cmds.listConnections("{}.shot".format(asset_node), source=False, destination=True)
        if not shot:
            raise ValueError("Asset is not connected to a shot")

        shot_node = shot[0]
        ep = cmds.getAttr("{}.ep".format(shot_node))
        seq = cmds.getAttr("{}.seq".format(shot_node))
        shot_code = cmds.getAttr("{}.shot".format(shot_node))
        dept = cmds.getAttr("{}.dept".format(shot_node)) or 'layout'

        # Query cache for versions
        versions = self.cache_manager.get_versions(ep, seq, shot_code, dept, asset_type, asset_name, variant)

        if not versions:
            return None

        # Get latest version
        latest_version = sorted(versions)[-1]

        if latest_version == current_version:
            return None  # Already latest

        # Update to latest
        self.update_asset_version(asset_node, latest_version)

        return latest_version

    def rollback_version(self, asset_node, target_version):
        """Rollback asset to a specific older version.

        Args:
            asset_node (str): CTX_Asset node name
            target_version (str): Target version (e.g., 'v002')

        Returns:
            bool: True if successful
        """
        if not cmds.objExists(asset_node):
            raise ValueError("Asset node '{}' does not exist".format(asset_node))

        # Validate target version exists
        current_path = cmds.getAttr("{}.path".format(asset_node))
        current_version = cmds.getAttr("{}.version".format(asset_node))
        target_path = current_path.replace(current_version, target_version)

        if not os.path.exists(target_path):
            raise ValueError("Target version path '{}' does not exist".format(target_path))

        # Update to target version
        self.update_asset_version(asset_node, target_version)

        return True

    def get_version_history(self, asset_node):
        """Get all available versions for an asset.

        Args:
            asset_node (str): CTX_Asset node name

        Returns:
            list: List of version strings (e.g., ['v001', 'v002', 'v003'])
        """
        if not cmds.objExists(asset_node):
            raise ValueError("Asset node '{}' does not exist".format(asset_node))

        if not self.cache_manager:
            raise RuntimeError("Cache manager not available")

        # Get asset info
        asset_type = cmds.getAttr("{}.assetType".format(asset_node))
        asset_name = cmds.getAttr("{}.assetName".format(asset_node))
        variant = cmds.getAttr("{}.variant".format(asset_node))

        # Get shot context
        shot = cmds.listConnections("{}.shot".format(asset_node), source=False, destination=True)
        if not shot:
            raise ValueError("Asset is not connected to a shot")

        shot_node = shot[0]
        ep = cmds.getAttr("{}.ep".format(shot_node))
        seq = cmds.getAttr("{}.seq".format(shot_node))
        shot_code = cmds.getAttr("{}.shot".format(shot_node))
        dept = cmds.getAttr("{}.dept".format(shot_node)) or 'layout'

        # Query cache for versions
        versions = self.cache_manager.get_versions(ep, seq, shot_code, dept, asset_type, asset_name, variant)

        return sorted(versions) if versions else []

    def replace_asset(self, asset_node, new_name, new_variant):
        """Replace asset with a different asset (same type).

        Args:
            asset_node (str): CTX_Asset node name
            new_name (str): New asset name
            new_variant (str): New variant code

        Returns:
            str: New asset node name
        """
        if not cmds.objExists(asset_node):
            raise ValueError("Asset node '{}' does not exist".format(asset_node))

        # Get current asset info
        asset_type = cmds.getAttr("{}.assetType".format(asset_node))
        version = cmds.getAttr("{}.version".format(asset_node))

        # Get shot
        shot = cmds.listConnections("{}.shot".format(asset_node), source=False, destination=True)
        if not shot:
            raise ValueError("Asset is not connected to a shot")

        shot_node = shot[0]

        # Build new path (simplified - would use path resolver in production)
        old_path = cmds.getAttr("{}.path".format(asset_node))
        old_name = cmds.getAttr("{}.assetName".format(asset_node))
        old_variant = cmds.getAttr("{}.variant".format(asset_node))

        new_path = old_path.replace(old_name, new_name).replace(old_variant, new_variant)

        if not os.path.exists(new_path):
            raise ValueError("New asset path '{}' does not exist".format(new_path))

        # Remove old asset
        self.remove_asset(asset_node)

        # Add new asset
        new_asset_node = self.add_asset(shot_node, asset_type, new_name, new_variant, version, new_path)

        return new_asset_node

    def duplicate_asset(self, asset_node, new_variant):
        """Duplicate asset with a new variant.

        Args:
            asset_node (str): CTX_Asset node name
            new_variant (str): New variant code

        Returns:
            str: New asset node name
        """
        if not cmds.objExists(asset_node):
            raise ValueError("Asset node '{}' does not exist".format(asset_node))

        # Get asset info
        asset_type = cmds.getAttr("{}.assetType".format(asset_node))
        asset_name = cmds.getAttr("{}.assetName".format(asset_node))
        version = cmds.getAttr("{}.version".format(asset_node))
        path = cmds.getAttr("{}.path".format(asset_node))

        # Get shot
        shot = cmds.listConnections("{}.shot".format(asset_node), source=False, destination=True)
        if not shot:
            raise ValueError("Asset is not connected to a shot")

        shot_node = shot[0]

        # Create duplicate with new variant
        new_asset_node = self.add_asset(shot_node, asset_type, asset_name, new_variant, version, path)

        return new_asset_node

    def validate_asset(self, asset_node):
        """Validate asset integrity.

        Args:
            asset_node (str): CTX_Asset node name

        Returns:
            dict: Validation report with 'valid', 'errors', 'warnings'
        """
        errors = []
        warnings = []

        # Check node exists
        if not cmds.objExists(asset_node):
            return {
                'valid': False,
                'errors': ["Asset node '{}' does not exist".format(asset_node)],
                'warnings': []
            }

        # Validate file path
        try:
            path = cmds.getAttr("{}.path".format(asset_node))
            if not path:
                errors.append("Asset path is empty")
            elif not os.path.exists(path):
                errors.append("Asset file does not exist: {}".format(path))
            elif not os.access(path, os.R_OK):
                warnings.append("Asset file is not readable: {}".format(path))
        except:
            errors.append("Failed to read asset path attribute")

        # Validate Maya node
        try:
            maya_node = cmds.getAttr("{}.maya_node".format(asset_node))
            if not maya_node:
                warnings.append("Maya node reference is empty")
            elif not cmds.objExists(maya_node):
                warnings.append("Maya node '{}' does not exist".format(maya_node))
        except:
            warnings.append("Failed to read maya_node attribute")

        # Validate shot connection
        shot = cmds.listConnections("{}.shot".format(asset_node), source=False, destination=True)
        if not shot:
            warnings.append("Asset is not connected to a shot")

        # Validate namespace format
        try:
            asset_type = cmds.getAttr("{}.assetType".format(asset_node))
            asset_name = cmds.getAttr("{}.assetName".format(asset_node))
            variant = cmds.getAttr("{}.variant".format(asset_node))

            if not asset_type:
                errors.append("Asset type is empty")
            if not asset_name:
                errors.append("Asset name is empty")
            if not variant:
                errors.append("Variant is empty")
        except:
            errors.append("Failed to read asset attributes")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

