# -*- coding: utf-8 -*-
"""Platform detection and path mapping for cross-platform compatibility.

This module provides utilities to detect the current platform (Windows/Linux)
and map paths between platforms using the platform_mapping configuration.

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
        
        Returns:
            dict: Platform mapping dictionary
        """
        return self.project_config.data.get('platform_mapping', {})
    
    def get_platform(self):
        """Get the current platform.
        
        Returns:
            str: 'windows' or 'linux'
        """
        return self.current_platform
    
    def get_root_for_platform(self, root_name, target_platform=None):
        """Get root path for specific platform.
        
        Args:
            root_name (str): Root name (e.g., 'PROJ_ROOT')
            target_platform (str, optional): Target platform. Defaults to current.
        
        Returns:
            str: Root path for the platform, or None if not found
        """
        if target_platform is None:
            target_platform = self.current_platform
        
        platform_roots = self.platform_mapping.get(target_platform, {})
        return platform_roots.get(root_name)
    
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
        source_roots = self.platform_mapping.get(source_platform, {})
        target_roots = self.platform_mapping.get(target_platform, {})

        # Try to match and replace each root
        for root_name, source_root in source_roots.items():
            target_root = target_roots.get(root_name)
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

        # Check all platforms to see which roots match
        for platform_name, roots in self.platform_mapping.items():
            for root_name, root_path in roots.items():
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

