# -*- coding: utf-8 -*-
"""Platform detection and path mapping for cross-platform compatibility.

This module provides utilities to detect the current platform (Windows/Linux)
and map paths between platforms using the platformMapping configuration.

Author: Context Variables Pipeline
Date: 2026-02-14
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import platform
import re


class PlatformConfig(object):
    """Handles platform detection and path mapping between Windows and Linux.
    
    This class provides utilities to:
    - Detect the current operating system
    - Map paths between Windows and Linux using configuration
    - Handle edge cases like UNC paths and network drives
    
    Example:
        >>> from config.project_config import ProjectConfig
        >>> from config.platform_config import PlatformConfig
        >>> 
        >>> config = ProjectConfig('examples/ctx_config.json')
        >>> platform_config = PlatformConfig(config)
        >>> 
        >>> # Map Windows path to Linux
        >>> linux_path = platform_config.map_path('V:/SWA/all/scene', 'linux')
        >>> # Returns: '/mnt/igloo_swa_v/SWA/all/scene'
    """
    
    PLATFORM_WINDOWS = 'windows'
    PLATFORM_LINUX = 'linux'
    
    def __init__(self, project_config):
        """Initialize platform configuration.

        Args:
            project_config (ProjectConfig): Project configuration instance
        """
        self.project_config = project_config
        self.current_platform = self._detect_platform()
        self.platform_mapping = self._load_platform_mapping()
        self.roots = self._load_roots()
    
    def _detect_platform(self):
        """Detect the current operating system.
        
        Returns:
            str: 'windows' or 'linux'
        """
        system = platform.system().lower()
        if system == 'windows':
            return self.PLATFORM_WINDOWS
        elif system in ['linux', 'darwin']:
            return self.PLATFORM_LINUX
        else:
            # Default to Windows if unknown
            return self.PLATFORM_WINDOWS
    
    def _load_platform_mapping(self):
        """Load platform mapping from configuration.

        For backward compatibility with legacy configs that use platformMapping.

        Returns:
            dict: Platform mapping dictionary (empty if using new roots format)
        """
        return self.project_config.data.get('platformMapping', {})

    def _load_roots(self):
        """Load roots from configuration.

        Supports two formats:

        Format 1 (New): Platform-specific roots
            "roots": {
                "windows": {"projRoot": "V:/", "imgRoot": "W:/"},
                "linux": {"projRoot": "/mnt/v/", "imgRoot": "/mnt/w/"}
            }

        Format 2 (Legacy): Flat roots + platformMapping
            "roots": {"projRoot": "V:/", "projRootLinux": "/mnt/v/"},
            "platformMapping": {
                "windows": {"projRoot": "V:/"},
                "linux": {"projRoot": "/mnt/v/"}
            }

        Returns:
            dict: Roots dictionary in platform-specific format
        """
        roots = self.project_config.get_roots()

        # Check if already in new format (has 'windows' or 'linux' keys)
        if 'windows' in roots or 'linux' in roots:
            return roots

        # Legacy format: return empty dict, will use platformMapping instead
        return {}
    
    def get_platform(self):
        """Get the current platform.
        
        Returns:
            str: 'windows' or 'linux'
        """
        return self.current_platform
    
    def get_root_for_platform(self, root_name, target_platform=None):
        """Get root path for specific platform.

        This method supports three configuration styles:

        Style 1 (New - Recommended): Platform-specific roots
            "roots": {
                "windows": {"projRoot": "V:/", "imgRoot": "W:/"},
                "linux": {"projRoot": "/mnt/v/", "imgRoot": "/mnt/w/"}
            }

        Style 2 (Legacy): platformMapping contains actual paths
            "platformMapping": {
                "windows": {"projRoot": "V:/"},
                "linux": {"projRoot": "/mnt/igloo_swa_v/"}
            }

        Style 3 (Legacy): platformMapping contains keys pointing to roots
            "roots": {
                "projRoot": "V:/",
                "projRootLinux": "/mnt/igloo_swa_v/"
            },
            "platformMapping": {
                "windows": {"projRoot": "projRoot"},
                "linux": {"projRoot": "projRootLinux"}
            }

        Args:
            root_name (str): Root name (e.g., 'projRoot')
            target_platform (str, optional): Target platform. Defaults to current.

        Returns:
            str: Root path for the platform, or None if not found
        """
        if target_platform is None:
            target_platform = self.current_platform

        # Try new format first (Style 1)
        if self.roots and target_platform in self.roots:
            platform_roots = self.roots.get(target_platform, {})
            root_path = platform_roots.get(root_name)
            if root_path:
                return root_path

        # Fall back to legacy platformMapping (Style 2 & 3)
        if self.platform_mapping:
            platform_roots = self.platform_mapping.get(target_platform, {})
            mapped_value = platform_roots.get(root_name)

            if not mapped_value:
                return None

            # Check if mapped_value is a key pointing to roots section (Style 3)
            # If it doesn't start with / or contain :, it's likely a key
            if not ('/' in mapped_value or ':' in mapped_value or '\\' in mapped_value):
                # It's a key, look it up in flat roots
                flat_roots = self.project_config.data.get('roots', {})
                actual_path = flat_roots.get(mapped_value)
                if actual_path:
                    return actual_path

            # Style 2: It's an actual path, return as-is
            return mapped_value

        return None
    
    def map_path(self, path, target_platform=None):
        """Map path from current platform to target platform.

        This method replaces the root portion of the path with the equivalent
        root for the target platform. It can detect the source platform from
        the path itself if it doesn't match the current platform.

        Args:
            path (str): Path to map
            target_platform (str, optional): Target platform ('windows' or 'linux').
                                            Defaults to current platform.

        Returns:
            str: Mapped path for target platform

        Example:
            >>> # On Windows
            >>> platform_config.map_path('V:/SWA/all/scene', 'linux')
            '/mnt/igloo_swa_v/SWA/all/scene'

            >>> # On Linux
            >>> platform_config.map_path('/mnt/igloo_swa_v/SWA/all/scene', 'windows')
            'V:/SWA/all/scene'
        """
        if target_platform is None:
            target_platform = self.current_platform

        # Normalize path separators
        path = self._normalize_path(path)

        # Detect source platform from path
        source_platform = self._detect_path_platform(path)

        # If already on target platform, return as-is
        if target_platform == source_platform:
            return path

        # Get all roots for source and target platforms
        # Try new format first
        if self.roots:
            source_roots = self.roots.get(source_platform, {})
            target_roots = self.roots.get(target_platform, {})
        else:
            # Fall back to legacy platformMapping
            source_roots = self.platform_mapping.get(source_platform, {})
            target_roots = self.platform_mapping.get(target_platform, {})

        # Try to match and replace each root
        for root_name, source_root in source_roots.items():
            target_root = target_roots.get(root_name)

            # Handle legacy format where value might be a key
            if self.platform_mapping and not self.roots:
                if not ('/' in source_root or ':' in source_root or '\\' in source_root):
                    flat_roots = self.project_config.data.get('roots', {})
                    source_root = flat_roots.get(source_root, source_root)
                if not ('/' in target_root or ':' in target_root or '\\' in target_root):
                    flat_roots = self.project_config.data.get('roots', {})
                    target_root = flat_roots.get(target_root, target_root)

            source_root_normalized = self._normalize_path(source_root)
            if target_root and path.startswith(source_root_normalized):
                # Replace source root with target root
                mapped_path = path.replace(source_root_normalized, target_root, 1)
                return self._normalize_path_separators(mapped_path, target_platform)

        # No mapping found, return original path
        return path

    def _detect_path_platform(self, path):
        """Detect which platform a path belongs to.

        Args:
            path (str): Path to analyze

        Returns:
            str: 'windows' or 'linux'
        """
        path = self._normalize_path(path)

        # Try new format first
        if self.roots:
            for platform_name, roots in self.roots.items():
                for root_name, root_path in roots.items():
                    root_path_normalized = self._normalize_path(root_path)
                    if path.startswith(root_path_normalized):
                        return platform_name

        # Fall back to legacy platformMapping
        if self.platform_mapping:
            for platform_name, roots in self.platform_mapping.items():
                for root_name, root_path in roots.items():
                    # Handle legacy format where value might be a key
                    if not ('/' in root_path or ':' in root_path or '\\' in root_path):
                        flat_roots = self.project_config.data.get('roots', {})
                        root_path = flat_roots.get(root_path, root_path)

                    root_path_normalized = self._normalize_path(root_path)
                    if path.startswith(root_path_normalized):
                        return platform_name

        # Default to current platform if no match
        return self.current_platform
    
    def _normalize_path(self, path):
        """Normalize path separators to forward slashes.
        
        Args:
            path (str): Path to normalize
        
        Returns:
            str: Normalized path with forward slashes
        """
        return path.replace('\\', '/')
    
    def _normalize_path_separators(self, path, target_platform):
        """Normalize path separators for target platform.
        
        Args:
            path (str): Path to normalize
            target_platform (str): Target platform
        
        Returns:
            str: Path with platform-appropriate separators
        """
        if target_platform == self.PLATFORM_WINDOWS:
            # Keep forward slashes for Windows (works fine)
            return path
        else:
            # Ensure forward slashes for Linux
            return path.replace('\\', '/')

