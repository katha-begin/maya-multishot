# -*- coding: utf-8 -*-
"""Node manager for proxy/reference operations.

This module handles operations on Arnold StandIns, Redshift Proxies,
and Maya References with a unified API. Also provides token-based path
resolution for updating asset paths when switching shots.

Author: Context Variables Pipeline
Date: 2026-02-14
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False
    from core.custom_nodes import cmds  # Use mock cmds

logger = logging.getLogger(__name__)

# Supported node types
NODE_TYPE_AI_STANDIN = 'aiStandIn'
NODE_TYPE_RS_PROXY = 'RedshiftProxyMesh'
NODE_TYPE_REFERENCE = 'reference'

# Attribute names for file paths
PATH_ATTRS = {
    NODE_TYPE_AI_STANDIN: 'dso',
    NODE_TYPE_RS_PROXY: 'fileName',
    NODE_TYPE_REFERENCE: 'ftn'  # file texture name
}


class NodeManager(object):
    """Manager for proxy and reference node operations.
    
    Provides unified API for working with Arnold StandIns, Redshift Proxies,
    and Maya References.
    
    Example:
        >>> nm = NodeManager()
        >>> node_type = nm.get_node_type('my_standin')
        >>> path = nm.get_path('my_standin')
        >>> nm.set_path('my_standin', '/new/path.abc')
    """
    
    def __init__(self):
        """Initialize node manager."""
        pass
    
    def get_node_type(self, node):
        """Detect node type.
        
        Args:
            node (str): Node name
        
        Returns:
            str: Node type (aiStandIn, RedshiftProxyMesh, reference), or None
        """
        if not cmds.objExists(node):
            return None
        
        # Check if it's a reference node
        if cmds.objExists(node) and MAYA_AVAILABLE:
            try:
                if cmds.referenceQuery(node, isNodeReferenced=True):
                    return NODE_TYPE_REFERENCE
            except:
                pass
        
        # Check node type
        if MAYA_AVAILABLE:
            node_type = cmds.nodeType(node)
        else:
            # In mock mode, check if node has type attribute
            if hasattr(cmds, '_nodes') and node in cmds._nodes:
                node_type = cmds._nodes[node].get('type')
            else:
                return None
        
        if node_type == NODE_TYPE_AI_STANDIN:
            return NODE_TYPE_AI_STANDIN
        elif node_type == NODE_TYPE_RS_PROXY:
            return NODE_TYPE_RS_PROXY
        
        return None
    
    def get_path(self, node):
        """Get current file path from node.
        
        Args:
            node (str): Node name
        
        Returns:
            str: File path, or None if not found
        """
        node_type = self.get_node_type(node)
        if node_type is None:
            return None
        
        # Get attribute name for this node type
        attr_name = PATH_ATTRS.get(node_type)
        if attr_name is None:
            return None
        
        # Get attribute value
        attr_path = "{}.{}".format(node, attr_name)
        if not cmds.objExists(attr_path):
            return None
        
        return cmds.getAttr(attr_path)
    
    def set_path(self, node, path):
        """Update file path on node.
        
        Args:
            node (str): Node name
            path (str): New file path
        
        Returns:
            bool: True if successful, False otherwise
        """
        node_type = self.get_node_type(node)
        if node_type is None:
            return False
        
        # Get attribute name for this node type
        attr_name = PATH_ATTRS.get(node_type)
        if attr_name is None:
            return False
        
        # Set attribute value
        attr_path = "{}.{}".format(node, attr_name)
        if not cmds.objExists(attr_path):
            return False
        
        try:
            cmds.setAttr(attr_path, path, type='string')
            return True
        except:
            return False
    
    def is_valid_node(self, node):
        """Check if node exists and is a supported type.

        Args:
            node (str): Node name

        Returns:
            bool: True if valid
        """
        return self.get_node_type(node) is not None

    def register_asset(self, shot_node, maya_node, asset_type, asset_name, variant):
        """Register a Maya node as a CTX asset.

        Args:
            shot_node: CTXShotNode instance
            maya_node (str): Maya node name
            asset_type (str): Asset type (e.g., 'CHAR')
            asset_name (str): Asset name (e.g., 'CatStompie')
            variant (str): Asset variant (e.g., '001')

        Returns:
            CTXAssetNode: Created asset node, or None if failed
        """
        from core.custom_nodes import CTXAssetNode

        # Validate Maya node exists
        if not cmds.objExists(maya_node):
            return None

        # Validate it's a supported node type
        if not self.is_valid_node(maya_node):
            return None

        # Create CTX_Asset node
        asset_node = CTXAssetNode.create_asset(asset_type, asset_name, variant, shot_node)

        # Store Maya node path
        path = self.get_path(maya_node)
        if path:
            asset_node.set_file_path(path)

        return asset_node

    def get_assets_for_shot(self, shot_node):
        """Get all assets for a shot via message connections.

        Args:
            shot_node: CTXShotNode instance

        Returns:
            list: List of CTXAssetNode instances
        """
        return shot_node.get_assets()

    def get_asset_by_maya_node(self, maya_node):
        """Find CTX_Asset linked to a Maya node.

        Args:
            maya_node (str): Maya node name

        Returns:
            CTXAssetNode: Asset node, or None if not found
        """
        from core.ctx_linker import get_linked_ctx_assets
        from core.custom_nodes import CTXAssetNode

        ctx_names = get_linked_ctx_assets(maya_node)
        if ctx_names:
            return CTXAssetNode(ctx_names[0])
        return None

    def get_assets_by_type(self, shot_node, asset_type):
        """Get assets filtered by type.

        Args:
            shot_node: CTXShotNode instance
            asset_type (str): Asset type to filter

        Returns:
            list: List of CTXAssetNode instances
        """
        all_assets = self.get_assets_for_shot(shot_node)
        return [a for a in all_assets if a.get_asset_type() == asset_type]

    def find_asset(self, shot_node, asset_name, variant):
        """Find specific asset by name and variant.

        Args:
            shot_node: CTXShotNode instance
            asset_name (str): Asset name
            variant (str): Asset variant

        Returns:
            CTXAssetNode: Asset node, or None if not found
        """
        all_assets = self.get_assets_for_shot(shot_node)
        for asset in all_assets:
            if asset.get_asset_name() == asset_name and asset.get_variant() == variant:
                return asset
        return None

    def resolve_asset_path(self, asset_node, shot_node, config, platform_config):
        """Resolve template path to actual file path for an asset.

        Builds full context from config, shot, and asset data, then expands
        the template string stored on the CTX_Asset node.

        Args:
            asset_node: CTXAssetNode instance
            shot_node: CTXShotNode instance
            config: ProjectConfig instance
            platform_config: PlatformConfig instance

        Returns:
            str: Resolved absolute path, or None if resolution fails
        """
        from core.tokens import TokenExpander

        # Get template from CTX_Asset
        template = asset_node.get_template()
        if not template:
            logger.warning("No template on %s", asset_node.node_name)
            return None

        # Build full context
        full_context = {}

        # Add roots (mapped to current platform)
        for root_name in config.get_roots().keys():
            root_path = platform_config.get_root_for_platform(root_name)
            if root_path:
                full_context[root_name] = root_path

        # Add static paths
        full_context.update(config.get_static_paths())

        # Add project code
        full_context['project'] = config.get_project_code()

        # Add shot context
        full_context['ep'] = shot_node.get_ep_code()
        full_context['seq'] = shot_node.get_seq_code()
        full_context['shot'] = shot_node.get_shot_code()

        # Add asset context
        full_context['assetType'] = asset_node.get_asset_type()
        full_context['assetName'] = asset_node.get_asset_name()
        full_context['variant'] = asset_node.get_variant()
        full_context['dept'] = asset_node.get_department()
        full_context['ext'] = asset_node.get_extension()
        full_context['ver'] = asset_node.get_version()

        # Expand tokens
        expander = TokenExpander()
        resolved = expander.expand_tokens(template, full_context)

        # Check for unexpanded tokens
        remaining = expander.extract_tokens(resolved)
        if remaining:
            logger.warning("Unexpanded tokens in %s: %s",
                           asset_node.node_name, ', '.join(remaining))

        # Normalize path separators
        resolved = resolved.replace('\\', '/')

        logger.debug("Resolved %s -> %s", asset_node.node_name, resolved)
        return resolved

    def update_asset_path(self, asset_node, shot_node, config, platform_config):
        """Resolve template and update the linked Maya node's file path.

        This is the core method that implements the token-based path resolution
        workflow: template -> token expansion -> apply to Maya node.

        Args:
            asset_node: CTXAssetNode instance
            shot_node: CTXShotNode instance
            config: ProjectConfig instance
            platform_config: PlatformConfig instance

        Returns:
            bool: True if Maya node was updated successfully
        """
        from core.ctx_linker import get_linked_maya_node, link_to_maya_node

        # 1. Resolve template to path
        resolved_path = self.resolve_asset_path(
            asset_node, shot_node, config, platform_config)
        if not resolved_path:
            logger.warning("Could not resolve path for %s", asset_node.node_name)
            return False

        # 2. Get linked Maya node
        maya_node = get_linked_maya_node(asset_node.node_name)

        # Special handling for cameras: if not linked, find any camera reference
        if not maya_node and asset_node.get_asset_type() == 'CAM':
            logger.info("Camera %s not linked, searching for camera reference in scene",
                       asset_node.node_name)
            maya_node = self._find_camera_reference()

            if maya_node:
                logger.info("Found camera reference %s, linking to %s",
                           maya_node, asset_node.node_name)
                # Link it for future use
                try:
                    link_to_maya_node(asset_node.node_name, maya_node)
                except Exception as e:
                    logger.warning("Could not link camera: %s", e)

        if not maya_node:
            logger.warning("No Maya node linked to %s", asset_node.node_name)
            return False

        # 3. Apply resolved path to Maya node
        success = self._apply_path_to_maya_node(maya_node, resolved_path)

        if success:
            # Cache resolved path on CTX_Asset
            asset_node.set_file_path(resolved_path)
            logger.info("Updated %s -> %s (path: %s)",
                        asset_node.node_name, maya_node, resolved_path)
        else:
            logger.error("Failed to apply path to %s", maya_node)

        return success

    def _find_camera_reference(self):
        """Find any camera reference in the scene.

        Searches for reference nodes that contain '_camera' in their namespace.
        Used when a camera CTX node is not linked yet.

        Returns:
            str or None: Camera reference node name
        """
        references = cmds.ls(type='reference') or []

        for ref_node in references:
            if ref_node in ['sharedReferenceNode', '_UNKNOWN_REF_NODE_']:
                continue

            try:
                ref_ns = cmds.referenceQuery(ref_node, namespace=True)
                if ref_ns and ref_ns.startswith(':'):
                    ref_ns = ref_ns[1:]

                # Check if this is a camera reference
                if '_camera' in ref_ns.lower():
                    logger.debug("Found camera reference: {} (namespace: {})".format(
                        ref_node, ref_ns))
                    return ref_node
            except Exception:
                continue

        logger.debug("No camera reference found in scene")
        return None

    def _apply_path_to_maya_node(self, maya_node, resolved_path):
        """Apply resolved path to a Maya node based on its type.

        Handles aiStandIn (.dso), RedshiftProxyMesh (.fileName),
        and reference nodes (file reload).

        Args:
            maya_node (str): Maya node name
            resolved_path (str): Resolved file path

        Returns:
            bool: True if successful
        """
        if not cmds.objExists(maya_node):
            logger.error("Maya node %s does not exist", maya_node)
            return False

        node_type = cmds.nodeType(maya_node)

        try:
            if node_type == NODE_TYPE_AI_STANDIN:
                cmds.setAttr('{}.dso'.format(maya_node),
                             resolved_path, type='string')
                logger.debug("Set aiStandIn.dso: %s", resolved_path)
                return True

            elif node_type == NODE_TYPE_RS_PROXY:
                cmds.setAttr('{}.fileName'.format(maya_node),
                             resolved_path, type='string')
                logger.debug("Set RedshiftProxyMesh.fileName: %s", resolved_path)
                return True

            elif node_type == 'reference':
                # For references, use file command to swap
                if MAYA_AVAILABLE:
                    cmds.file(resolved_path, loadReference=maya_node)
                    logger.debug("Reloaded reference %s: %s",
                                 maya_node, resolved_path)
                return True

            else:
                logger.warning("Unsupported node type %s for %s",
                               node_type, maya_node)
                return False

        except Exception as e:
            logger.error("Failed to apply path to %s: %s", maya_node, e)
            return False

    def update_shot_paths(self, shot_node, config, platform_config):
        """Update paths for all assets in a shot.

        Called when switching active shot to resolve all templates
        with the new shot's context.

        Args:
            shot_node: CTXShotNode instance
            config: ProjectConfig instance
            platform_config: PlatformConfig instance

        Returns:
            int: Number of assets successfully updated
        """
        assets = self.get_assets_for_shot(shot_node)
        count = 0
        total = len(assets)

        logger.info("Updating paths for %d assets in shot %s",
                     total, shot_node.node_name)

        for asset in assets:
            try:
                if self.update_asset_path(asset, shot_node, config, platform_config):
                    count += 1
            except Exception as e:
                logger.error("Failed to update %s: %s", asset.node_name, e)

        logger.info("Updated %d/%d asset paths for shot %s",
                     count, total, shot_node.node_name)
        return count

    def update_all_paths(self, config, platform_config):
        """Update paths for all assets in the active shot.

        Args:
            config: ProjectConfig instance
            platform_config: PlatformConfig instance

        Returns:
            int: Number of assets updated
        """
        from core.context import ContextManager

        ctx = ContextManager()
        active_shot = ctx.get_active_shot()
        if not active_shot:
            logger.warning("No active shot to update paths for")
            return 0

        return self.update_shot_paths(active_shot, config, platform_config)

