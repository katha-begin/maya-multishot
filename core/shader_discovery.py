# -*- coding: utf-8 -*-
"""Shader and groom file discovery system.

This module provides utilities to discover shader and groom files for assets
based on their category and name. It searches multiple directory paths based
on asset category conventions.

Author: Context Variables Pipeline
Date: 2026-02-18
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import logging

logger = logging.getLogger(__name__)


# Default category mappings (can be overridden by config)
DEFAULT_CATEGORY_MAPPINGS = {
    'CHAR': {
        'directory': 'Character',
        'subdirs': ['Main', 'Extra']
    },
    'PROP': {
        'directory': 'Props',
        'subdirs': ['object']
    },
    'SETS': {
        'directory': 'Sets',
        'subdirs': ['exterior', 'interior']
    },
    'SDRS': {
        'directory': 'Setdress',
        'subdirs': ['interior', 'exterior', 'Set']
    }
}

# Default file suffixes
DEFAULT_SHADER_SUFFIX = '_rsshade.ma'
DEFAULT_GROOM_SUFFIX = '_groom.ma'
DEFAULT_HERO_SUBDIR = 'hero'


def get_asset_category_from_type(asset_type, config=None):
    """Convert asset type code to category directory name.

    Args:
        asset_type (str): Asset type code (CHAR, PROP, SETS, SDRS)
        config (dict, optional): Configuration with category mappings

    Returns:
        str: Category directory name (Character, Props, Sets, Setdress)

    Example:
        >>> category = get_asset_category_from_type('CHAR', config)
        >>> # Returns: 'Character'
    """
    # Get category mapping from config or use default
    if config and 'assetDiscovery' in config and 'categoryMappings' in config['assetDiscovery']:
        category_mappings = config['assetDiscovery']['categoryMappings']
    else:
        category_mappings = DEFAULT_CATEGORY_MAPPINGS

    # Get directory name from mapping
    if asset_type in category_mappings:
        return category_mappings[asset_type].get('directory', asset_type)

    # Fallback: return asset_type as-is
    logger.warning("Unknown asset type: {}, using as-is".format(asset_type))
    return asset_type


def get_asset_subdirs_from_type(asset_type, config=None):
    """Get list of subdirectories to search for an asset type.

    Args:
        asset_type (str): Asset type code (CHAR, PROP, SETS, SDRS)
        config (dict, optional): Configuration with category mappings

    Returns:
        list: List of subdirectory names to search

    Example:
        >>> subdirs = get_asset_subdirs_from_type('CHAR', config)
        >>> # Returns: ['Main', 'Extra']
    """
    # Get category mapping from config or use default
    if config and 'assetDiscovery' in config and 'categoryMappings' in config['assetDiscovery']:
        category_mappings = config['assetDiscovery']['categoryMappings']
    else:
        category_mappings = DEFAULT_CATEGORY_MAPPINGS

    # Get subdirs from mapping
    if asset_type in category_mappings:
        return category_mappings[asset_type].get('subdirs', [])

    # Fallback: empty list
    logger.warning("Unknown asset type: {}, no subdirs defined".format(asset_type))
    return []


def build_shader_search_paths(category, name, project_root, config=None):
    """Build search paths for shader/groom files based on asset category.

    This function builds a list of directory paths to search for shader and groom files.
    It uses the config file to determine the correct directory structure for each asset type.

    Args:
        category (str): Asset category (CHAR, PROP, SETS, SDRS)
        name (str): Asset name (e.g., 'CatStompie')
        project_root (str): Project root path (e.g., 'V:/SWA')
        config (dict, optional): Configuration with category mappings

    Returns:
        list: List of directory paths to search

    Example:
        >>> paths = build_shader_search_paths('CHAR', 'CatStompie', 'V:/SWA', config)
        >>> # Returns: ['V:/SWA/all/asset/Character/Main/CatStompie/hero',
        >>> #           'V:/SWA/all/asset/Character/object/CatStompie/hero']
    """
    search_paths = []

    # Get category mapping from config or use default
    if config and 'assetDiscovery' in config and 'categoryMappings' in config['assetDiscovery']:
        category_mappings = config['assetDiscovery']['categoryMappings']
    else:
        category_mappings = DEFAULT_CATEGORY_MAPPINGS

    # Get hero subdir from config or use default
    if config and 'assetDiscovery' in config and 'heroSubdir' in config['assetDiscovery']:
        hero_subdir = config['assetDiscovery']['heroSubdir']
    else:
        hero_subdir = DEFAULT_HERO_SUBDIR

    # Get asset base from config or use default
    if config and 'staticPaths' in config and 'assetBase' in config['staticPaths']:
        asset_base_rel = config['staticPaths']['assetBase']
    else:
        asset_base_rel = 'all/asset'

    # Get project name from config
    if config and 'project' in config and 'name' in config['project']:
        project_name = config['project']['name']
    else:
        # Extract from project_root (e.g., 'V:/SWA' -> 'SWA')
        project_name = os.path.basename(project_root.rstrip('/\\'))

    # Get mapping for this category
    if category not in category_mappings:
        logger.warning("Unknown asset category: {}".format(category))
        return search_paths

    mapping = category_mappings[category]
    directory = mapping.get('directory', '')
    subdirs = mapping.get('subdirs', [])

    # Build paths: project_root/project_name/asset_base/{directory}/{subdir}/{name}/hero
    asset_base = os.path.join(project_root, project_name, asset_base_rel)

    for subdir in subdirs:
        path = os.path.join(asset_base, directory, subdir, name, hero_subdir)
        search_paths.append(path)

    logger.debug("Built {} search paths for {}/{}".format(len(search_paths), category, name))

    return search_paths


def discover_shader_files(category, name, project_root, config=None):
    """Discover shader and groom files for an asset.
    
    Args:
        category (str): Asset category (CHAR, PROP, SETS, SDRS)
        name (str): Asset name (e.g., 'CatStompie')
        project_root (str): Project root path (e.g., 'V:/SWA')
        config (dict, optional): Configuration with discovery settings
    
    Returns:
        dict: Dictionary with 'shader' and 'groom' keys, values are file paths or None
    
    Example:
        >>> result = discover_shader_files('CHAR', 'CatStompie', 'V:/SWA')
        >>> # Returns: {'shader': 'V:/SWA/.../CatStompie_rsshade.ma', 'groom': None}
    """
    result = {
        'shader': None,
        'groom': None
    }
    
    # Get file suffixes from config or use defaults
    if config and 'assetDiscovery' in config:
        shader_suffix = config['assetDiscovery'].get('shaderFileSuffix', DEFAULT_SHADER_SUFFIX)
        groom_suffix = config['assetDiscovery'].get('groomFileSuffix', DEFAULT_GROOM_SUFFIX)
    else:
        shader_suffix = DEFAULT_SHADER_SUFFIX
        groom_suffix = DEFAULT_GROOM_SUFFIX
    
    # Build search paths
    search_paths = build_shader_search_paths(category, name, project_root, config)
    
    # Search for shader and groom files
    shader_filename = "{}{}".format(name, shader_suffix)
    groom_filename = "{}{}".format(name, groom_suffix)
    
    for search_path in search_paths:
        if not os.path.exists(search_path):
            continue
        
        # Check for shader file
        if result['shader'] is None:
            shader_file = os.path.join(search_path, shader_filename)
            if os.path.exists(shader_file):
                result['shader'] = shader_file
                logger.info("Found shader file: {}".format(shader_file))
        
        # Check for groom file
        if result['groom'] is None:
            groom_file = os.path.join(search_path, groom_filename)
            if os.path.exists(groom_file):
                result['groom'] = groom_file
                logger.info("Found groom file: {}".format(groom_file))
        
        # Stop if both found
        if result['shader'] and result['groom']:
            break
    
    return result

