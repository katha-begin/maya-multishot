# -*- coding: utf-8 -*-
"""Reference manager for geometry cache, shader, and groom files.

This module provides unified reference operations for Maya files including
geometry caches (.abc), shader files (.ma), and groom files (.ma).

Author: Context Variables Pipeline
Date: 2026-02-18
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


def reference_file(file_path, namespace, reference_type='file'):
    """Reference a Maya file with specified namespace.

    Args:
        file_path (str): Path to file to reference
        namespace (str): Namespace for the reference
        reference_type (str): Type of reference ('file' for general, 'shader', 'groom', 'cache')

    Returns:
        str: Reference node name (e.g., 'CHAR_CatStompie_001RN'), or None if failed

    Example:
        >>> ref_node = reference_file('V:/SWA/.../CatStompie_rsshade.ma', 'CHAR_CatStompie_001_Shade')
        >>> # Returns: 'CHAR_CatStompie_001_ShadeRN'
    """
    if not MAYA_AVAILABLE:
        logger.warning("Maya not available, cannot reference file")
        return None

    try:
        # Check if namespace already exists
        if cmds.namespace(exists=namespace):
            logger.warning("Namespace already exists: {}".format(namespace))
            # Maya will auto-rename to namespace1, namespace2, etc.

        # Reference the file
        # Note: cmds.file() with returnNewNodes=False returns the file path, not the reference node
        result = cmds.file(
            file_path,
            reference=True,
            namespace=namespace,
            returnNewNodes=False
        )

        logger.info("DEBUG: cmds.file() returned: {} (type: {})".format(result, type(result)))

        # Query the reference node name from the file path
        try:
            ref_node = cmds.referenceQuery(file_path, referenceNode=True)
            logger.info("DEBUG: cmds.referenceQuery() returned: {} (type: {})".format(ref_node, type(ref_node)))
        except Exception as e:
            logger.error("Failed to query reference node for {}: {}".format(file_path, e))
            return None

        # Verify we got a reference node name, not a file path
        if '/' in ref_node or '\\' in ref_node:
            logger.error("Got file path instead of reference node name: {}".format(ref_node))
            return None

        # Verify the reference node exists
        if not cmds.objExists(ref_node):
            logger.error("Reference node does not exist: {}".format(ref_node))
            return None

        logger.info("Referenced {} file: {} as namespace: {} (ref node: {})".format(
            reference_type, file_path, namespace, ref_node))

        return ref_node

    except Exception as e:
        logger.error("Failed to reference file {}: {}".format(file_path, str(e)))
        return None


def reference_geometry_cache(cache_file, namespace):
    """Reference alembic geometry cache.
    
    Args:
        cache_file (str): Path to .abc file
        namespace (str): Namespace for the reference
    
    Returns:
        str: Reference node name, or None if failed
    """
    return reference_file(cache_file, namespace, reference_type='cache')


def reference_shader(shader_file, namespace):
    """Reference shader Maya file.
    
    Args:
        shader_file (str): Path to shader .ma file
        namespace (str): Namespace for the reference
    
    Returns:
        str: Reference node name, or None if failed
    """
    return reference_file(shader_file, namespace, reference_type='shader')


def reference_groom(groom_file, namespace):
    """Reference groom Maya file.
    
    Args:
        groom_file (str): Path to groom .ma file
        namespace (str): Namespace for the reference
    
    Returns:
        str: Reference node name, or None if failed
    """
    return reference_file(groom_file, namespace, reference_type='groom')


def get_reference_top_level_nodes(namespace):
    """Get top-level transform nodes from a reference namespace.
    
    Args:
        namespace (str): Reference namespace
    
    Returns:
        list: List of top-level transform node names
    
    Example:
        >>> nodes = get_reference_top_level_nodes('CHAR_CatStompie_001')
        >>> # Returns: ['CHAR_CatStompie_001:GEO', 'CHAR_CatStompie_001:RIG']
    """
    if not MAYA_AVAILABLE:
        return []
    
    try:
        # Get all transforms in namespace
        all_transforms = cmds.ls("{}:*".format(namespace), type='transform') or []
        
        # Filter to top-level (no parent or parent is world)
        top_level = []
        for node in all_transforms:
            parent = cmds.listRelatives(node, parent=True, fullPath=False)
            if not parent or parent[0] == 'world':
                top_level.append(node)
        
        return top_level
        
    except Exception as e:
        logger.error("Failed to get top-level nodes for namespace {}: {}".format(
            namespace, str(e)))
        return []


def get_shader_namespace(ctx_asset_node, config):
    """Get shader namespace using config template.
    
    Args:
        ctx_asset_node: CTX_Asset node instance
        config: Project configuration with templates
    
    Returns:
        str: Shader namespace
    
    Example:
        >>> shader_ns = get_shader_namespace(ctx_asset, config)
        >>> # Returns: 'CHAR_CatStompie_001_Shade'
    """
    # Get base namespace from CTX_Asset
    base_namespace = ctx_asset_node.get_namespace()
    
    # Try to use config template
    if config and hasattr(config, 'expand_template'):
        try:
            context = {
                'assetType': ctx_asset_node.get_asset_type(),
                'assetName': ctx_asset_node.get_asset_name(),
                'variant': ctx_asset_node.get_variant()
            }
            shader_ns = config.expand_template('namespaceShader', context)
            return shader_ns
        except Exception as e:
            logger.warning("Failed to expand namespaceShader template: {}".format(str(e)))
    
    # Fallback: append _Shade to base namespace
    return "{}_Shade".format(base_namespace)


def get_groom_namespace(ctx_asset_node, config):
    """Get groom namespace using config template.
    
    Args:
        ctx_asset_node: CTX_Asset node instance
        config: Project configuration with templates
    
    Returns:
        str: Groom namespace
    
    Example:
        >>> groom_ns = get_groom_namespace(ctx_asset, config)
        >>> # Returns: 'CHAR_CatStompie_001_Groom'
    """
    # Get base namespace from CTX_Asset
    base_namespace = ctx_asset_node.get_namespace()
    
    # Try to use config template
    if config and hasattr(config, 'expand_template'):
        try:
            context = {
                'assetType': ctx_asset_node.get_asset_type(),
                'assetName': ctx_asset_node.get_asset_name(),
                'variant': ctx_asset_node.get_variant()
            }
            groom_ns = config.expand_template('namespaceGroom', context)
            return groom_ns
        except Exception as e:
            logger.warning("Failed to expand namespaceGroom template: {}".format(str(e)))
    
    # Fallback: append _Groom to base namespace
    return "{}_Groom".format(base_namespace)

