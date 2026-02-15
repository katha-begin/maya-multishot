# -*- coding: utf-8 -*-
"""Version cache system for asset discovery.

This module provides caching for discovered asset versions and paths
for quick lookup without repeated filesystem scanning.

Author: Context Variables Pipeline
Date: 2026-02-14
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import re
import json
import logging

# Set up logging
logger = logging.getLogger(__name__)


def scan_publish_directory(path, pattern_manager=None):
    """Scan publish directory for asset files and extract metadata.

    Scans the specified directory for asset files (.abc, .ma, .mb, .vdb, .ass, .rs)
    and parses each filename to extract asset metadata.

    Args:
        path (str): Full path to publish directory to scan
        pattern_manager: Optional PatternManager instance for parsing filenames.
                        If None, basic parsing is used.

    Returns:
        list: List of dicts with asset metadata:
            [{
                'filename': 'Ep04_sq0070_SH0170__CHAR_CatStompie_001.abc',
                'assetType': 'CHAR',
                'assetName': 'CatStompie',
                'variant': '001',
                'extension': 'abc',
                'fullPath': '/full/path/to/file.abc',
                'ep': 'Ep04',
                'seq': 'sq0070',
                'shot': 'SH0170'
            }, ...]

    Example:
        >>> from config.pattern_manager import PatternManager
        >>> from config.project_config import ProjectConfig
        >>> config = ProjectConfig('config.json')
        >>> pattern_mgr = PatternManager(config)
        >>> assets = scan_publish_directory('/path/to/publish', pattern_mgr)
        >>> print(len(assets))
        42
    """
    if not os.path.exists(path):
        logger.warning("Publish directory does not exist: {}".format(path))
        return []

    if not os.path.isdir(path):
        logger.warning("Path is not a directory: {}".format(path))
        return []

    # Supported file extensions
    supported_extensions = ('.abc', '.ma', '.mb', '.vdb', '.ass', '.rs')

    assets = []
    unparseable_count = 0

    try:
        # Scan directory for files
        for filename in os.listdir(path):
            file_path = os.path.join(path, filename)

            # Skip directories
            if os.path.isdir(file_path):
                continue

            # Check file extension
            if not filename.lower().endswith(supported_extensions):
                continue

            # Parse filename
            if pattern_manager:
                parsed = pattern_manager.parse_filename(filename)
            else:
                # Fallback to basic parsing if no pattern manager
                parsed = _parse_filename_basic(filename)

            if not parsed:
                unparseable_count += 1
                logger.debug("Could not parse filename: {}".format(filename))
                continue

            # Normalize extension field (pattern_manager returns 'ext', basic parser returns 'extension')
            if 'ext' in parsed and 'extension' not in parsed:
                parsed['extension'] = parsed['ext']
            elif 'extension' in parsed and 'ext' not in parsed:
                parsed['ext'] = parsed['extension']

            # Add full path and filename
            parsed['filename'] = filename
            parsed['fullPath'] = os.path.normpath(file_path)

            assets.append(parsed)

    except Exception as e:
        logger.error("Error scanning directory {}: {}".format(path, e))
        return []

    # Log summary
    if assets:
        logger.info("Scanned {}: found {} valid assets, {} unparseable files".format(
            path, len(assets), unparseable_count))
    else:
        logger.warning("No valid assets found in {}".format(path))

    return assets


def _parse_filename_basic(filename):
    """Basic filename parser without pattern manager.

    Parses standard format: Ep##_sq####_SH####__TYPE_Name_###.ext

    Args:
        filename (str): Filename to parse

    Returns:
        dict: Parsed data or None if invalid
    """
    # Remove extension
    name_without_ext = os.path.splitext(filename)[0]
    extension = os.path.splitext(filename)[1].lstrip('.')

    # Check for double underscore separator
    if '__' not in name_without_ext:
        return None

    try:
        # Split by double underscore
        shot_part, asset_part = name_without_ext.split('__', 1)

        # Parse shot part: Ep##_sq####_SH####
        shot_parts = shot_part.split('_')
        if len(shot_parts) < 3:
            return None

        ep = shot_parts[0]
        seq = shot_parts[1]
        shot = shot_parts[2]

        # Validate shot codes
        if not (ep.startswith('Ep') and seq.startswith('sq') and shot.startswith('SH')):
            return None

        # Parse asset part: TYPE_Name_###
        asset_parts = asset_part.split('_')
        if len(asset_parts) < 3:
            return None

        asset_type = asset_parts[0]
        asset_name = '_'.join(asset_parts[1:-1])  # Handle multi-part names
        variant = asset_parts[-1]

        return {
            'ep': ep,
            'seq': seq,
            'shot': shot,
            'assetType': asset_type,
            'assetName': asset_name,
            'variant': variant,
            'extension': extension
        }

    except Exception:
        return None


class VersionCache(object):
    """Cache for discovered asset versions.
    
    Structure: {publish_path: {asset_name: [versions]}}
    
    Example:
        >>> cache = VersionCache()
        >>> cache.build_cache('/path/to/publish', pattern_manager)
        >>> versions = cache.get_versions('/path/to/publish', 'CHAR_CatStompie_001')
        ['v003', 'v002', 'v001']
    """
    
    def __init__(self):
        """Initialize version cache."""
        self._cache = {}
    
    def build_cache(self, publish_path, pattern_manager):
        """Scan filesystem and build cache for a publish directory.

        This method scans the publish directory and any version subdirectories
        (v001, v002, etc.) to discover all available asset versions.

        Args:
            publish_path (str): Full path to publish directory
            pattern_manager: PatternManager instance for parsing filenames

        Returns:
            dict: Cache data for this publish path
                  Format: {asset_name: [versions]}

        Example:
            >>> cache = VersionCache()
            >>> data = cache.build_cache('/path/to/publish', pattern_mgr)
            >>> print(data)
            {'CHAR_CatStompie_001': ['v003', 'v002', 'v001']}
        """
        if not os.path.exists(publish_path):
            logger.warning("Publish path does not exist: {}".format(publish_path))
            return {}

        cache_data = {}

        try:
            # Scan for files in main directory
            assets = scan_publish_directory(publish_path, pattern_manager)

            for asset in assets:
                # Extract asset name (assetType_assetName_variant)
                asset_name = "{}_{}_{}" .format(
                    asset['assetType'],
                    asset['assetName'],
                    asset['variant']
                )

                # Extract version from file path
                version = self._extract_version(asset['fullPath'])
                if not version:
                    continue

                # Add to cache
                if asset_name not in cache_data:
                    cache_data[asset_name] = []

                if version not in cache_data[asset_name]:
                    cache_data[asset_name].append(version)

            # Also scan version subdirectories (v001, v002, etc.)
            for item in os.listdir(publish_path):
                item_path = os.path.join(publish_path, item)

                # Check if it's a version directory
                if os.path.isdir(item_path) and re.match(r'v\d{3}', item):
                    version = item

                    # Scan this version directory
                    version_assets = scan_publish_directory(item_path, pattern_manager)

                    for asset in version_assets:
                        asset_name = "{}_{}_{}" .format(
                            asset['assetType'],
                            asset['assetName'],
                            asset['variant']
                        )

                        # Add to cache
                        if asset_name not in cache_data:
                            cache_data[asset_name] = []

                        if version not in cache_data[asset_name]:
                            cache_data[asset_name].append(version)

        except Exception as e:
            logger.error("Error building cache for {}: {}".format(publish_path, e))
            return {}

        # Sort versions (latest first)
        for asset_name in cache_data:
            cache_data[asset_name].sort(reverse=True)

        # Store in cache
        self._cache[publish_path] = cache_data

        logger.info("Built cache for {}: {} assets, {} total versions".format(
            publish_path, len(cache_data),
            sum(len(versions) for versions in cache_data.values())))

        return cache_data
    
    def _extract_version(self, file_path):
        """Extract version from file path.
        
        Args:
            file_path (str): Full file path
        
        Returns:
            str: Version string (e.g., 'v003'), or None
        """
        # Check parent directory name for version pattern
        parent_dir = os.path.basename(os.path.dirname(file_path))
        version_pattern = re.compile(r'v(\d{3})')
        match = version_pattern.search(parent_dir)
        if match:
            return match.group(0)
        
        # Check filename for version pattern
        filename = os.path.basename(file_path)
        match = version_pattern.search(filename)
        if match:
            return match.group(0)
        
        return None
    
    def get_versions(self, publish_path, asset_name):
        """Query cache for versions of an asset.
        
        Args:
            publish_path (str): Full path to publish directory
            asset_name (str): Full asset name (e.g., 'CHAR_CatStompie_001')
        
        Returns:
            list: List of version strings, sorted latest first
        """
        if publish_path not in self._cache:
            return []
        
        return self._cache[publish_path].get(asset_name, [])
    
    def get_latest_version(self, publish_path, asset_name):
        """Get latest version of an asset.
        
        Args:
            publish_path (str): Full path to publish directory
            asset_name (str): Full asset name
        
        Returns:
            str: Latest version string, or None
        """
        versions = self.get_versions(publish_path, asset_name)
        return versions[0] if versions else None
    
    def clear(self):
        """Clear all cache data."""
        self._cache = {}
    
    def save_to_file(self, filepath):
        """Save cache to JSON file.
        
        Args:
            filepath (str): Path to save cache file
        """
        with open(filepath, 'w') as f:
            json.dump(self._cache, f, indent=2)
    
    def load_from_file(self, filepath):
        """Load cache from JSON file.
        
        Args:
            filepath (str): Path to cache file
        """
        if not os.path.exists(filepath):
            return
        
        with open(filepath, 'r') as f:
            self._cache = json.load(f)

