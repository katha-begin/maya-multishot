# -*- coding: utf-8 -*-
"""Filesystem discovery module for Context Variables Pipeline.

This module provides functions to scan the filesystem and discover shots and assets
without relying on CTX custom nodes. Used by the UI to display available content.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import re
import logging

logger = logging.getLogger(__name__)


def scan_shots_from_filesystem(base_path, ep, seq):
    """Scan filesystem for shots in a given episode and sequence.
    
    Args:
        base_path (str): Base path (e.g., "V:/SWA/all/scene")
        ep (str): Episode code (e.g., "Ep04")
        seq (str): Sequence code (e.g., "sq0070")
    
    Returns:
        list: List of shot data dicts with keys: shot_code, ep, seq, path, asset_count
        
    Example:
        >>> shots = scan_shots_from_filesystem("V:/SWA/all/scene", "Ep04", "sq0070")
        >>> shots
        [{'shot_code': 'SH0170', 'ep': 'Ep04', 'seq': 'sq0070', 'path': '...', 'asset_count': 12}]
    """
    shots = []
    shot_pattern = re.compile(r'^SH\d{4}$')
    
    # Build path to sequence directory
    seq_path = os.path.join(base_path, ep, seq)
    
    if not os.path.exists(seq_path):
        logger.warning("Sequence path does not exist: {}".format(seq_path))
        return shots
    
    try:
        # Scan for shot directories
        for item in os.listdir(seq_path):
            item_path = os.path.join(seq_path, item)
            
            # Check if it's a directory and matches shot pattern
            if os.path.isdir(item_path) and shot_pattern.match(item):
                # Count assets in this shot
                asset_count = get_shot_asset_count(item_path)
                
                shots.append({
                    'shot_code': item,
                    'ep': ep,
                    'seq': seq,
                    'path': item_path,
                    'asset_count': asset_count
                })
        
        # Sort by shot code
        shots.sort(key=lambda x: x['shot_code'])
        
        logger.info("Found {} shots in {}/{}".format(len(shots), ep, seq))
        
    except Exception as e:
        logger.error("Error scanning shots from {}: {}".format(seq_path, e))
    
    return shots


def scan_assets_from_filesystem(publish_path, pattern_manager=None):
    """Scan filesystem for assets in a publish directory.
    
    Args:
        publish_path (str): Path to publish directory (e.g., ".../SH0170/anim/publish")
        pattern_manager (PatternManager, optional): Pattern manager for parsing filenames
    
    Returns:
        list: List of asset data dicts with keys: asset_type, asset_name, variant, 
              version, dept, path, ext, filename
              
    Example:
        >>> assets = scan_assets_from_filesystem("V:/SWA/.../SH0170/anim/publish")
        >>> assets[0]
        {'asset_type': 'CHAR', 'asset_name': 'CatStompie', 'variant': '001', ...}
    """
    assets = []
    
    if not os.path.exists(publish_path):
        logger.warning("Publish path does not exist: {}".format(publish_path))
        return assets
    
    try:
        # Scan for version directories (v001, v002, v003, etc.)
        version_pattern = re.compile(r'^v\d{3}$')
        
        for item in os.listdir(publish_path):
            item_path = os.path.join(publish_path, item)
            
            # Check if it's a version directory
            if os.path.isdir(item_path) and version_pattern.match(item):
                version = item
                
                # Scan files in version directory
                for filename in os.listdir(item_path):
                    file_path = os.path.join(item_path, filename)
                    
                    # Skip directories
                    if os.path.isdir(file_path):
                        continue
                    
                    # Parse filename
                    asset_data = _parse_filename(filename, file_path, version, pattern_manager)
                    
                    if asset_data:
                        assets.append(asset_data)
        
        logger.info("Found {} assets in {}".format(len(assets), publish_path))
        
    except Exception as e:
        logger.error("Error scanning assets from {}: {}".format(publish_path, e))
    
    return assets


def _parse_filename(filename, file_path, version, pattern_manager=None):
    """Parse filename to extract asset metadata.
    
    Args:
        filename (str): Filename to parse
        file_path (str): Full path to file
        version (str): Version string (e.g., "v003")
        pattern_manager (PatternManager, optional): Pattern manager for parsing
    
    Returns:
        dict: Asset data dict or None if parsing fails
    """
    # Basic pattern: Ep##_sq####_SH####__TYPE_Name_###.ext
    # Example: Ep04_sq0070_SH0170__CHAR_CatStompie_001.abc
    pattern = r'^Ep\d{2}_sq\d{4}_SH\d{4}__([A-Z]+)_(.+)_(\d{3})\.(abc|ma|mb|vdb|ass|rs)$'
    match = re.match(pattern, filename)
    
    if match:
        asset_type = match.group(1)
        asset_name = match.group(2)
        variant = match.group(3)
        ext = match.group(4)
        
        # Extract dept from path (e.g., .../anim/publish/...)
        path_parts = file_path.replace('\\', '/').split('/')
        dept = 'unknown'
        for i, part in enumerate(path_parts):
            if part == 'publish' and i > 0:
                dept = path_parts[i - 1]
                break
        
        return {
            'asset_type': asset_type,
            'asset_name': asset_name,
            'variant': variant,
            'version': version,
            'dept': dept,
            'path': file_path,
            'ext': ext,
            'filename': filename
        }

    # If basic pattern fails, return None
    logger.debug("Failed to parse filename: {}".format(filename))
    return None


def get_available_versions(publish_path, asset_id):
    """Get available versions for an asset.

    Args:
        publish_path (str): Path to publish directory
        asset_id (str): Asset identifier (e.g., "CHAR_CatStompie_001")

    Returns:
        list: List of version strings (e.g., ['v003', 'v002', 'v001']) in descending order
    """
    versions = []

    if not os.path.exists(publish_path):
        return versions

    try:
        version_pattern = re.compile(r'^v\d{3}$')

        for item in os.listdir(publish_path):
            item_path = os.path.join(publish_path, item)

            if os.path.isdir(item_path) and version_pattern.match(item):
                # Check if this version contains the asset
                for filename in os.listdir(item_path):
                    if asset_id in filename:
                        versions.append(item)
                        break

        # Sort in descending order (newest first)
        versions.sort(reverse=True)

    except Exception as e:
        logger.error("Error getting versions from {}: {}".format(publish_path, e))

    return versions


def get_shot_asset_count(shot_path):
    """Count assets in a shot directory.

    Args:
        shot_path (str): Path to shot directory

    Returns:
        int: Number of assets found
    """
    asset_count = 0

    if not os.path.exists(shot_path):
        return asset_count

    try:
        # Scan for department directories
        for dept in os.listdir(shot_path):
            dept_path = os.path.join(shot_path, dept)

            if not os.path.isdir(dept_path):
                continue

            # Check for publish directory
            publish_path = os.path.join(dept_path, 'publish')

            if os.path.exists(publish_path):
                # Count version directories
                version_pattern = re.compile(r'^v\d{3}$')

                for item in os.listdir(publish_path):
                    item_path = os.path.join(publish_path, item)

                    if os.path.isdir(item_path) and version_pattern.match(item):
                        # Count files in version directory
                        for filename in os.listdir(item_path):
                            file_path = os.path.join(item_path, filename)
                            if os.path.isfile(file_path):
                                asset_count += 1

    except Exception as e:
        logger.error("Error counting assets in {}: {}".format(shot_path, e))

    return asset_count

