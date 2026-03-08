# -*- coding: utf-8 -*-
"""Asset path resolver for converting namespaces to file paths.

This module provides utilities to convert asset namespaces to correct
assetCategory and assetSubdir for path resolution, enabling shader
discovery from CTX_Asset nodes.

Author: Context Variables Pipeline
Date: 2026-02-18
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging

logger = logging.getLogger(__name__)


def get_asset_category_from_type(asset_type, config=None):
    """Convert asset type code to category directory name.
    
    Args:
        asset_type (str): Asset type code (CHAR, PROP, SETS, SDRS, VEH, CAM)
        config (dict, optional): Configuration with token mappings
    
    Returns:
        str: Category directory name (Character, Props, Sets, Setdress, Vehicle)
    
    Example:
        >>> get_asset_category_from_type('CHAR')
        >>> # Returns: 'Character'
    """
    # Try to get mapping from config
    if config and 'tokens' in config and 'assetCategory' in config['tokens']:
        mapping = config['tokens']['assetCategory'].get('mapping', {})
        if asset_type in mapping:
            return mapping[asset_type]
    
    # Fallback to default mapping
    default_mapping = {
        'CHAR': 'Character',
        'PROP': 'Props',
        'SETS': 'Sets',
        'SDRS': 'Setdress',
        'VEH': 'Vehicle',
        'CAM': 'Camera'
    }
    
    return default_mapping.get(asset_type, asset_type)


def get_asset_subdirs_for_type(asset_type, config=None):
    """Get list of subdirectories to search for an asset type.
    
    Args:
        asset_type (str): Asset type code (CHAR, PROP, SETS, SDRS)
        config (dict, optional): Configuration with category mappings
    
    Returns:
        list: List of subdirectory names to search
    
    Example:
        >>> get_asset_subdirs_for_type('CHAR')
        >>> # Returns: ['Main', 'object']
    """
    # Try to get from config
    if config and 'assetDiscovery' in config and 'categoryMappings' in config['assetDiscovery']:
        mappings = config['assetDiscovery']['categoryMappings']
        if asset_type in mappings:
            return mappings[asset_type].get('subdirs', [])
    
    # Fallback to default
    default_subdirs = {
        'CHAR': ['Main', 'object'],
        'PROP': ['Main', 'object'],
        'SETS': ['Exterior', 'Interior'],
        'SDRS': ['interior', 'exterior', 'Main', 'object'],
        'VEH': ['Main', 'object']
    }
    
    return default_subdirs.get(asset_type, ['Main'])


def resolve_asset_paths_from_namespace(namespace, config=None):
    """Resolve asset category and subdirs from namespace.
    
    This function parses a namespace (e.g., 'CHAR_CatStompie_001') and returns
    the asset category directory and list of subdirectories to search.
    
    Args:
        namespace (str): Asset namespace (e.g., 'CHAR_CatStompie_001')
        config (dict, optional): Configuration with mappings
    
    Returns:
        dict: Dictionary with 'assetType', 'assetName', 'variant', 'assetCategory', 'subdirs'
    
    Example:
        >>> resolve_asset_paths_from_namespace('CHAR_CatStompie_001')
        >>> # Returns: {
        >>> #   'assetType': 'CHAR',
        >>> #   'assetName': 'CatStompie',
        >>> #   'variant': '001',
        >>> #   'assetCategory': 'Character',
        >>> #   'subdirs': ['Main', 'object']
        >>> # }
    """
    # Parse namespace: TYPE_Name_Variant
    parts = namespace.split('_')
    
    if len(parts) < 3:
        logger.warning("Invalid namespace format: {}".format(namespace))
        return None
    
    asset_type = parts[0]
    variant = parts[-1]
    asset_name = '_'.join(parts[1:-1])  # Handle multi-part names
    
    # Get category and subdirs
    asset_category = get_asset_category_from_type(asset_type, config)
    subdirs = get_asset_subdirs_for_type(asset_type, config)
    
    return {
        'assetType': asset_type,
        'assetName': asset_name,
        'variant': variant,
        'assetCategory': asset_category,
        'subdirs': subdirs
    }


def resolve_asset_paths_from_ctx_asset(ctx_asset_node, config=None):
    """Resolve asset paths from CTX_Asset node.
    
    Args:
        ctx_asset_node: CTX_Asset node instance
        config (dict, optional): Configuration with mappings
    
    Returns:
        dict: Dictionary with asset path components
    
    Example:
        >>> resolve_asset_paths_from_ctx_asset(ctx_asset)
        >>> # Returns: {
        >>> #   'assetType': 'CHAR',
        >>> #   'assetName': 'CatStompie',
        >>> #   'variant': '001',
        >>> #   'assetCategory': 'Character',
        >>> #   'subdirs': ['Main', 'object']
        >>> # }
    """
    asset_type = ctx_asset_node.get_asset_type()
    asset_name = ctx_asset_node.get_asset_name()
    variant = ctx_asset_node.get_variant()
    
    # Get category and subdirs
    asset_category = get_asset_category_from_type(asset_type, config)
    subdirs = get_asset_subdirs_for_type(asset_type, config)
    
    return {
        'assetType': asset_type,
        'assetName': asset_name,
        'variant': variant,
        'assetCategory': asset_category,
        'subdirs': subdirs
    }

