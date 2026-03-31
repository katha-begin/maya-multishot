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
import re

from tools.base_manager import cmds, MAYA_AVAILABLE, BaseManager

import logging
logger = logging.getLogger(__name__)


class AssetManager(BaseManager):
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
        super(AssetManager, self).__init__()
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
        from core.nodes.wrappers import CTXAssetNode, CTXShotNode
        from core.ctx_converter import CTXConverter

        # Validate shot exists
        if not cmds.objExists(shot_node):
            raise ValueError("Shot node '{}' does not exist".format(shot_node))

        # Validate file exists
        if not os.path.exists(file_path):
            raise ValueError("Asset file '{}' does not exist".format(file_path))

        # Wrap shot node
        shot_node_obj = CTXShotNode(shot_node)
        shot_code = shot_node_obj.get_shot_code() or ''

        # Build namespace: CHAR_ToriiMechSuit_001
        namespace = "{}_{}_{}".format(asset_type, asset_name, variant)

        # Create CTX_Asset node with per-shot naming
        asset_node_obj = CTXAssetNode.create(
            asset_type=asset_type,
            asset_name=asset_name,
            variant=variant,
            namespace=namespace,
            shot_code=shot_code
        )
        shot_node_obj.add_asset(asset_node_obj)

        # Set file path and version
        asset_node_obj.set_file_path(file_path)
        asset_node_obj.set_version(version)

        # Determine node type from file extension and create Maya node
        ext = os.path.splitext(file_path)[1].lower()
        maya_node = None
        shape_node = None

        if ext == '.abc':
            # Create Arnold StandIn with namespace (Phase 3)
            from core.nodes import create_standin_with_namespace
            transform_node, shape_node = create_standin_with_namespace(namespace, file_path)
            maya_node = transform_node  # Store transform for display layer

        elif ext in ['.ma', '.mb']:
            # Create Reference with namespace
            from core.reference_manager import reference_file
            ref_node = reference_file(file_path, namespace)
            if ref_node:
                maya_node = ref_node

        elif ext == '.rs':
            # Create Redshift Proxy with namespace (Phase 3)
            from core.nodes import create_redshift_proxy_with_namespace
            transform_node, shape_node = create_redshift_proxy_with_namespace(namespace, file_path)
            maya_node = transform_node  # Store transform for display layer

        # Link ALL CTX_Asset nodes sharing this namespace to the Maya reference
        CTXConverter().link_all_by_namespace(namespace)

        # Assign to display layer if available
        if self.layer_manager and maya_node:
            ep = shot_node_obj.get_ep_code()
            seq = shot_node_obj.get_seq_code()
            shot = shot_node_obj.get_shot_code()
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


def _connect_decomp_matrix(src_xform, dst_node):
    """Connect src_xform.worldMatrix[0] to dst_node via decomposeMatrix (TRS+Shear).

    If a decomposeMatrix already exists for the destination, it is deleted first.
    Naming convention: EE_{dst_flat}_decomp (one decomp per destination node).

    Args:
        src_xform (str): Source transform node (geo group)
        dst_node (str): Destination node (place3dTexture) to drive TRS
    """
    if not MAYA_AVAILABLE:
        return

    dst_flat = dst_node.replace(':', '_')
    decomp_name = 'EE_{}_decomp'.format(dst_flat)

    if cmds.objExists(decomp_name):
        cmds.delete(decomp_name)

    decomp = cmds.createNode('decomposeMatrix', name=decomp_name)
    cmds.connectAttr('{}.worldMatrix[0]'.format(src_xform), '{}.inputMatrix'.format(decomp), force=True)

    for out_attr, in_attr in [
        ('outputTranslate', 'translate'),
        ('outputRotate', 'rotate'),
        ('outputScale', 'scale'),
        ('outputShear', 'shear'),
    ]:
        src_plug = '{}.{}'.format(decomp, out_attr)
        dst_plug = '{}.{}'.format(dst_node, in_attr)
        if cmds.objExists(dst_plug):
            try:
                cmds.connectAttr(src_plug, dst_plug, force=True)
            except Exception as e:
                logger.warning('decomposeMatrix: could not connect {} -> {}: {}'.format(
                    src_plug, dst_plug, e))

    logger.info('decomposeMatrix linked: {} -> {} via {}'.format(src_xform, dst_node, decomp_name))


def _connect_place3d_for_char(geo_namespace, shader_namespace):
    """Find place3dTexture nodes in shader_namespace and connect each to its
    matching geo transform in geo_namespace via decomposeMatrix.

    Pairing convention (mirrors igl_shot_build):
      shader: {shader_ns}:Body_Place3dTexture  ->  geo: {geo_ns}:Body_Grp
      suffix strip: '_Place3dTexture' on shader side, '_Grp' on geo side

    Args:
        geo_namespace (str): Geometry namespace (e.g. 'CHAR_CatStompie_001')
        shader_namespace (str): Shader namespace (e.g. 'CHAR_CatStompie_001_Shade')

    Returns:
        int: Number of pairs connected
    """
    if not MAYA_AVAILABLE:
        return 0

    place_suffix = '_Place3dTexture'
    geo_suffix = '_Grp'

    places = cmds.ls('{}:*'.format(shader_namespace), type='place3dTexture') or []
    if not places:
        logger.info('No place3dTexture nodes in {} -- skipping decomposeMatrix'.format(
            shader_namespace))
        return 0

    # Build lookup: short name -> full path for geo transforms
    geo_transforms = cmds.ls('{}:*'.format(geo_namespace), type='transform') or []
    geo_map = {}
    for g in geo_transforms:
        short = g.split(':')[-1]
        geo_map[short] = g

    connected = 0
    for place_node in places:
        short_place = place_node.split(':')[-1]
        # Strip suffix to get base name, then look for matching geo
        if short_place.endswith(place_suffix):
            base = short_place[:-len(place_suffix)]
        else:
            base = short_place

        wanted = base + geo_suffix
        xform = geo_map.get(wanted)

        # Fuzzy fallback: find any geo transform starting with base
        if not xform:
            for short_geo, full_geo in geo_map.items():
                if short_geo.startswith(base):
                    xform = full_geo
                    break

        if xform:
            _connect_decomp_matrix(xform, place_node)
            connected += 1
        else:
            logger.warning('decomposeMatrix: no geo match for {} (tried {})'.format(
                place_node, wanted))

    logger.info('decomposeMatrix: connected {}/{} place3dTexture pairs ({} -> {})'.format(
        connected, len(places), geo_namespace, shader_namespace))
    return connected


def import_sets_asset(shot_info, sets_abc_path, config, platform_config):
    """Import or merge a SETS alembic into the scene and build the component hierarchy.

    Args:
        shot_info (dict): Keys: ep, seq, shot
        sets_abc_path (str): Full path to the SETS abc file
        config: ProjectConfig instance
        platform_config: PlatformConfig instance

    Returns:
        str: The set_namespace that was imported, or None on failure
    """
    if not MAYA_AVAILABLE:
        logger.warning('Maya not available, cannot import SETS asset')
        return None

    from core.shader_assignment import assign_shaders_to_geometry
    from core.reference_manager import reference_file
    from core.nodes.wrappers import CTXAssetNode, CTXShotNode

    abc_basename = os.path.basename(sets_abc_path)
    # Parse: Ep09_sq0050_SH0270__SETS_KitBedRoomIntA_001.abc
    parts = abc_basename.rsplit('.', 1)[0].split('__', 1)
    if len(parts) != 2:
        logger.error('Cannot parse SETS abc filename: {}'.format(abc_basename))
        return None

    asset_part = parts[1]  # e.g. SETS_KitBedRoomIntA_001
    # Mirror _parse_filename: type=first token, variant=last token, name=everything between
    asset_tokens = asset_part.split('_')
    if len(asset_tokens) < 3:
        logger.error('Cannot parse asset part from SETS abc: {}'.format(asset_part))
        return None

    set_id = asset_tokens[-1]                      # 001
    set_name = '_'.join(asset_tokens[1:-1])         # KitBedRoomIntA (handles underscores in name)
    set_namespace = asset_part                      # SETS_KitBedRoomIntA_001

    # Check if this SET was already imported (namespace exists)
    set_exists = cmds.namespace(exists=set_namespace)

    if set_exists:
        # Already imported — merge the alembic to reposition locators
        main_grp = '{}:Main_Grp'.format(set_namespace)
        if cmds.objExists(main_grp):
            try:
                cmds.select(main_grp)
                cmds.AbcImport(sets_abc_path, mode='merge',
                               connect=main_grp, fitTimeRange=False)
                logger.info('Merged SETS alembic: {}'.format(sets_abc_path))
            except Exception as e:
                logger.error('AbcImport merge failed for {}: {}'.format(sets_abc_path, e))
                return None
        else:
            logger.warning('Namespace exists but Main_Grp not found: {}'.format(main_grp))
    else:
        # Fresh import
        cmds.namespace(add=set_namespace)
        prev_ns = cmds.namespaceInfo(currentNamespace=True)
        cmds.namespace(setNamespace=set_namespace)
        try:
            cmds.AbcImport(sets_abc_path, mode='import', fitTimeRange=False)
        except Exception as e:
            logger.error('AbcImport failed for {}: {}'.format(sets_abc_path, e))
            cmds.namespace(setNamespace=prev_ns)
            return None
        cmds.namespace(setNamespace=prev_ns)

    # Gather locators
    locators = cmds.ls('{}:*_Loc'.format(set_namespace), type='transform') or []
    logger.info('Found {} locators in {}'.format(len(locators), set_namespace))

    for locator in locators:
        loc_short = locator.split(':')[-1]  # e.g. KBDIntCelling_001_Loc
        # Asset names are camelCase — strip _Loc, split once on last _ for id
        loc_base = loc_short[:-4] if loc_short.endswith('_Loc') else loc_short
        loc_tokens = loc_base.rsplit('_', 1)
        if len(loc_tokens) != 2:
            logger.warning('Cannot parse locator name: {}'.format(loc_short))
            continue

        component_name = loc_tokens[0]   # KBDIntCelling
        component_id = loc_tokens[1]     # 001
        nested_ns = '{}:{}_{}'.format(set_namespace, component_name, component_id)
        shader_ns = '{}_shade'.format(nested_ns)

        # Check state: geo parented to locator, shader referenced
        locator_children = cmds.listRelatives(locator, children=True, type='transform') or []
        has_geo = len(locator_children) > 0
        shader_exists = (cmds.namespace(exists=shader_ns) and
                         bool(cmds.ls('{}:*'.format(shader_ns))))

        if has_geo and shader_exists:
            continue

        # Need hero_path for geo and/or shader files
        hero_attr = '{}.snow__pub_location'.format(locator)
        if not cmds.objExists(hero_attr):
            logger.warning('No snow__pub_location on {}'.format(locator))
            continue
        hero_path = cmds.getAttr(hero_attr) or ''
        if not hero_path:
            logger.warning('Empty snow__pub_location on {}'.format(locator))
            continue

        geo_file = os.path.join(hero_path, '{}_geo.abc'.format(component_name))
        shader_file = os.path.join(hero_path, '{}_rsshade.ma'.format(component_name))

        # Reference geo if not already present
        if not has_geo:
            if not os.path.exists(geo_file):
                logger.warning('Geo file not found: {}'.format(geo_file))
                continue
            if not cmds.namespace(exists=nested_ns):
                cmds.namespace(add=nested_ns)
            try:
                cmds.file(geo_file, reference=True, namespace=nested_ns,
                          loadReferenceDepth='all', mergeNamespacesOnClash=False)
            except Exception as e:
                logger.error('Failed to reference geo {}: {}'.format(geo_file, e))
                continue

            # Find top-level transform and parent to locator
            all_in_ns = cmds.ls('{}:*'.format(nested_ns), type='transform') or []
            top_nodes = [n for n in all_in_ns
                         if not (cmds.listRelatives(n, parent=True, fullPath=False) or [None])[0]]
            if top_nodes:
                cmds.parent(top_nodes[0], locator)
                cmds.xform(top_nodes[0], translation=[0, 0, 0], rotation=[0, 0, 0])
                cmds.xform(top_nodes[0], scale=[1, 1, 1])

        # Reference shader if not already present
        if not shader_exists and os.path.exists(shader_file):
            if not cmds.namespace(exists=shader_ns):
                cmds.namespace(add=shader_ns)
            try:
                cmds.file(shader_file, reference=True, namespace=shader_ns,
                          loadReferenceDepth='all', mergeNamespacesOnClash=False)
            except Exception as e:
                logger.error('Failed to reference shader {}: {}'.format(shader_file, e))

        # Assign shaders
        if cmds.namespace(exists=shader_ns):
            try:
                assign_shaders_to_geometry(shader_ns, nested_ns)
            except Exception as e:
                logger.error('Shader assignment failed for {}: {}'.format(nested_ns, e))

    # Create CTX_Asset node (one per SETS abc)
    shot_code = shot_info.get('shot', '')
    ep_code = shot_info.get('ep', '')
    seq_code = shot_info.get('seq', '')

    # Find existing CTX_Shot node
    shot_node_obj = None
    all_network = cmds.ls(type='network') or []
    ctx_shot_nodes = [n for n in all_network if n.startswith('CTX_Shot_')]
    for sn in ctx_shot_nodes:
        try:
            tmp = CTXShotNode(sn)
            if tmp.get_shot_code() == shot_code:
                shot_node_obj = tmp
                break
        except Exception:
            continue

    if shot_node_obj is None:
        shot_node_obj = CTXShotNode.create(ep_code=ep_code, seq_code=seq_code, shot_code=shot_code)

    ctx_asset_obj = CTXAssetNode.create(
        asset_type='SETS',
        asset_name=set_name,
        variant=set_id,
        namespace=set_namespace,
        shot_code=shot_code
    )
    shot_node_obj.add_asset(ctx_asset_obj)
    ctx_asset_obj.set_file_path(sets_abc_path)
    ctx_asset_obj.set_version('v001')

    logger.info('SETS import complete: namespace={}, ctx_node={}'.format(
        set_namespace, ctx_asset_obj.node_name))
    return set_namespace
