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
        
        Args:
            publish_path (str): Full path to publish directory
            pattern_manager: PatternManager instance for parsing filenames
        
        Returns:
            dict: Cache data for this publish path
        """
        if not os.path.exists(publish_path):
            return {}
        
        cache_data = {}
        
        # Scan for files
        try:
            for filename in os.listdir(publish_path):
                # Skip directories
                file_path = os.path.join(publish_path, filename)
                if os.path.isdir(file_path):
                    continue
                
                # Parse filename
                parsed = pattern_manager.parse_filename(filename)
                if not parsed:
                    continue
                
                # Extract asset name (assetType_assetName_variant)
                asset_name = "{}_{}_{}" .format(
                    parsed['assetType'],
                    parsed['assetName'],
                    parsed['variant']
                )
                
                # Extract version from filename or parent directory
                version = self._extract_version(file_path)
                if not version:
                    continue
                
                # Add to cache
                if asset_name not in cache_data:
                    cache_data[asset_name] = []
                
                if version not in cache_data[asset_name]:
                    cache_data[asset_name].append(version)
        
        except Exception as e:
            print("Error building cache for {}: {}".format(publish_path, e))
            return {}
        
        # Sort versions (latest first)
        for asset_name in cache_data:
            cache_data[asset_name].sort(reverse=True)
        
        # Store in cache
        self._cache[publish_path] = cache_data
        
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

