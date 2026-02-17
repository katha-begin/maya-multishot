# -*- coding: utf-8 -*-
"""
Project Configuration Loader

This module handles loading and validating project configuration from JSON files.
Supports both repository-based and workspace-based configuration locations.

Author: Context Variables Pipeline Team
Date: 2026-02-14
"""

from __future__ import absolute_import, division, print_function

import json
import os


class ProjectConfig(object):
    """
    Loads and manages project configuration from JSON files.

    Configuration can be loaded from:
    1. Code repository (recommended): <repo>/project_configs/ctx_config.json
    2. Project workspace (legacy): <workspace>/config/ctx_config.json

    Attributes:
        config_path (str): Path to the loaded configuration file
        data (dict): Parsed configuration data
        version (str): Configuration schema version
    """
    
    REQUIRED_KEYS = ['version', 'project', 'roots', 'staticPaths', 'templates', 'patterns']
    SUPPORTED_VERSIONS = ['1.0', '1.1']
    
    def __init__(self, config_path=None):
        """
        Initialize ProjectConfig.
        
        Args:
            config_path (str, optional): Path to configuration JSON file.
                If None, will search in default locations.
        
        Raises:
            IOError: If configuration file not found
            ValueError: If configuration is invalid
        """
        self.config_path = config_path
        self.data = {}
        self.version = None
        
        if config_path:
            self.load(config_path)
    
    def load(self, config_path):
        """
        Load configuration from JSON file.
        
        Args:
            config_path (str): Path to configuration JSON file
        
        Raises:
            IOError: If file doesn't exist or can't be read
            ValueError: If JSON is invalid or schema validation fails
        """
        if not os.path.exists(config_path):
            raise IOError("Configuration file not found: {}".format(config_path))
        
        try:
            with open(config_path, 'r') as f:
                self.data = json.load(f)
        except (IOError, OSError) as e:
            raise IOError("Failed to read configuration file: {}".format(e))
        except ValueError as e:
            raise ValueError("Invalid JSON in configuration file: {}".format(e))
        
        self.config_path = config_path
        self._validate()
    
    def _validate(self):
        """
        Validate configuration schema.
        
        Raises:
            ValueError: If required keys are missing or version is unsupported
        """
        # Check required keys
        missing_keys = [key for key in self.REQUIRED_KEYS if key not in self.data]
        if missing_keys:
            raise ValueError(
                "Missing required keys in configuration: {}".format(', '.join(missing_keys))
            )
        
        # Check version
        self.version = self.data.get('version')
        if self.version not in self.SUPPORTED_VERSIONS:
            raise ValueError(
                "Unsupported configuration version: {}. Supported versions: {}".format(
                    self.version, ', '.join(self.SUPPORTED_VERSIONS)
                )
            )
        
        # Validate project section
        if not isinstance(self.data.get('project'), dict):
            raise ValueError("'project' must be a dictionary")
        
        # Validate roots section
        if not isinstance(self.data.get('roots'), dict):
            raise ValueError("'roots' must be a dictionary")

        # Validate staticPaths section
        if not isinstance(self.data.get('staticPaths'), dict):
            raise ValueError("'staticPaths' must be a dictionary")

        # Validate templates section
        if not isinstance(self.data.get('templates'), dict):
            raise ValueError("'templates' must be a dictionary")

        # Validate patterns section
        if not isinstance(self.data.get('patterns'), dict):
            raise ValueError("'patterns' must be a dictionary")
    
    def get_project_name(self):
        """Get project name from configuration."""
        return self.data.get('project', {}).get('name', '')
    
    def get_project_code(self):
        """Get project code from configuration."""
        return self.data.get('project', {}).get('code', '')
    
    def get_roots(self):
        """
        Get all root paths.

        Supports two configuration formats:

        Format 1 (New): Platform-specific roots
            "roots": {
                "windows": {"projRoot": "V:/", "imgRoot": "W:/"},
                "linux": {"projRoot": "/mnt/v/", "imgRoot": "/mnt/w/"}
            }

        Format 2 (Legacy): Flat roots with platform suffixes
            "roots": {
                "projRoot": "V:/",
                "projRootLinux": "/mnt/v/"
            }

        Returns:
            dict: Dictionary of root paths
                  For new format: returns platform-specific dict
                  For legacy format: returns flat dict
        """
        roots = self.data.get('roots', {})

        # Detect format by checking if 'windows' or 'linux' keys exist
        if 'windows' in roots or 'linux' in roots:
            # New format: platform-specific
            return roots
        else:
            # Legacy format: flat structure
            return roots
    
    def get_root(self, root_name, platform=None):
        """
        Get specific root path.

        Supports both new and legacy formats.

        Args:
            root_name (str): Name of the root (e.g., 'projRoot')
            platform (str, optional): Platform name ('windows' or 'linux').
                                     Only used for new format.

        Returns:
            str: Root path or None if not found
        """
        roots = self.data.get('roots', {})

        # Detect format
        if 'windows' in roots or 'linux' in roots:
            # New format: platform-specific
            if platform:
                platform_roots = roots.get(platform, {})
                return platform_roots.get(root_name)
            else:
                # No platform specified, try to return from any platform
                for plat in ['windows', 'linux']:
                    if plat in roots and root_name in roots[plat]:
                        return roots[plat][root_name]
                return None
        else:
            # Legacy format: flat structure
            return roots.get(root_name)

    def get_static_paths(self):
        """
        Get all static paths.

        Returns:
            dict: Dictionary of static paths (e.g., {'sceneBase': 'all/scene'})
        """
        return self.data.get('staticPaths', {})

    def get_static_path(self, path_name):
        """
        Get specific static path.

        Args:
            path_name (str): Name of the static path (e.g., 'sceneBase')

        Returns:
            str: Static path or None if not found
        """
        return self.data.get('staticPaths', {}).get(path_name)

    def get_templates(self):
        """
        Get all path templates.

        Returns:
            dict: Dictionary of path templates with tokens
        """
        return self.data.get('templates', {})

    def get_template(self, template_name):
        """
        Get specific path template.

        Args:
            template_name (str): Name of the template (e.g., 'publish_path', 'cache_path')

        Returns:
            str: Template string with tokens or None if not found
        """
        return self.data.get('templates', {}).get(template_name)

    def get_patterns(self):
        """
        Get all filename patterns.

        Returns:
            dict: Dictionary of filename patterns
        """
        return self.data.get('patterns', {})

    def get_pattern(self, pattern_name):
        """
        Get specific filename pattern.

        Args:
            pattern_name (str): Name of the pattern (e.g., 'full_format', 'namespace_format')

        Returns:
            str: Pattern string or None if not found
        """
        return self.data.get('patterns', {}).get(pattern_name)

    def get_supported_extensions(self):
        """
        Get list of supported file extensions.

        Returns:
            list: List of supported extensions (e.g., ['.abc', '.vdb', '.ass'])
        """
        return self.data.get('extensions', [])

    def get_tokens(self):
        """
        Get all token definitions.

        Returns:
            dict: Dictionary of token definitions
        """
        return self.data.get('tokens', {})

    def get_token_values(self, token_name):
        """
        Get predefined values for a token.

        Args:
            token_name (str): Name of the token (e.g., 'dept', 'assetType')

        Returns:
            list: List of predefined values, or None if token has no predefined values
        """
        token_def = self.data.get('tokens', {}).get(token_name, {})
        return token_def.get('values')

    def get_shot_metadata_config(self):
        """
        Get shot metadata configuration.

        Returns:
            dict: Shot metadata config or None if not defined
        """
        return self.data.get('shotMetadata')

    def is_shot_metadata_enabled(self):
        """
        Check if shot metadata import is enabled.

        Returns:
            bool: True if enabled, False otherwise
        """
        metadata_config = self.get_shot_metadata_config()
        if not metadata_config:
            return False
        return metadata_config.get('enabled', False)

    @classmethod
    def find_config(cls, search_paths=None):
        """
        Search for configuration file in default locations.

        Args:
            search_paths (list, optional): List of paths to search.
                If None, searches in default locations.

        Returns:
            str: Path to configuration file or None if not found
        """
        if search_paths is None:
            search_paths = cls._get_default_search_paths()

        for path in search_paths:
            if os.path.exists(path):
                return path

        return None

    @staticmethod
    def _get_default_search_paths():
        """
        Get default search paths for configuration file.

        Returns:
            list: List of default search paths
        """
        paths = []

        # 1. Repository-based (recommended)
        # Assuming this module is in <repo>/config/project_config.py
        module_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(module_dir)
        repo_config = os.path.join(repo_root, 'project_configs', 'ctx_config.json')
        paths.append(repo_config)

        # 2. Environment variable
        env_config = os.environ.get('CTX_CONFIG_PATH')
        if env_config:
            paths.append(env_config)

        # 3. Workspace-based (legacy)
        # This would need to be determined from Maya workspace
        # For now, we'll skip this as it requires Maya API

        return paths

    def get_render_settings_config(self):
        """Get render settings configuration.

        Returns:
            dict: Render settings config or None
        """
        return self.data.get('renderSettings')

    def is_render_settings_enabled(self):
        """Check if render settings automation is enabled.

        Returns:
            bool: True if enabled
        """
        render_config = self.get_render_settings_config()
        if not render_config:
            return False
        return render_config.get('enabled', False)

    def get_render_output_config(self):
        """Get render output path configuration.

        Returns:
            dict: Output path config or None
        """
        render_config = self.get_render_settings_config()
        if not render_config:
            return None
        return render_config.get('outputPath')

    def get_render_camera_config(self):
        """Get render camera configuration.

        Returns:
            dict: Camera config or None
        """
        render_config = self.get_render_settings_config()
        if not render_config:
            return None
        return render_config.get('camera')

    def __repr__(self):
        """String representation of ProjectConfig."""
        return "ProjectConfig(config_path='{}', version='{}')".format(
            self.config_path, self.version
        )

