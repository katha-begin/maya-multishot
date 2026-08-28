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


# Maximum depth of an "extends" chain, so a malformed set of configs cannot
# recurse forever.
_MAX_EXTENDS_DEPTH = 8


def deep_merge(base, overlay):
    """Merge overlay onto base, returning a new dict.

    Dictionaries merge recursively.  Every other value -- including lists --
    is replaced wholesale rather than combined.  Replacement is the safer rule
    for this config: a project's ``dept.values`` should be that project's list,
    not the base list with the project's entries appended.

    Args:
        base (dict): Values to start from.
        overlay (dict): Values that win.

    Returns:
        dict: Merged result.  Neither input is modified.
    """
    merged = dict(base)

    for key, value in overlay.items():
        if (key in merged
                and isinstance(merged[key], dict)
                and isinstance(value, dict)):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value

    return merged


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

        self.data = self._load_with_extends(config_path, [])
        self.config_path = config_path

        # Validate the merged result, so a project overlay only has to declare
        # what it changes rather than repeating every required key.
        self._validate()

    @classmethod
    def _read_json(cls, config_path):
        """Read one JSON file with the module's error contract."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (IOError, OSError) as e:
            raise IOError("Failed to read configuration file: {}".format(e))
        except ValueError as e:
            raise ValueError(
                "Invalid JSON in configuration file {}: {}".format(config_path, e))

    @classmethod
    def _load_with_extends(cls, config_path, chain):
        """Load a config, resolving an optional 'extends' parent first.

        A config may name a parent with ``"extends": "base.json"``, resolved
        relative to the config's own directory.  The parent loads first and
        the child merges over it, so a project overlay declares only what it
        changes.  This keeps shared machinery -- templates, patterns, gaffer
        attributes -- in one place, where it cannot drift between projects.

        A config with no 'extends' key loads exactly as it always has.

        Args:
            config_path (str): Config to load.
            chain (list): Absolute paths already being loaded, for cycle
                detection.

        Returns:
            dict: Merged configuration data, without the 'extends' key.

        Raises:
            IOError: If a file is missing.
            ValueError: On invalid JSON, a cycle, or excessive nesting.
        """
        abs_path = os.path.abspath(config_path)

        if abs_path in chain:
            raise ValueError(
                "Circular 'extends' in configuration: {}".format(
                    ' -> '.join(chain + [abs_path])))

        if len(chain) >= _MAX_EXTENDS_DEPTH:
            raise ValueError(
                "Configuration 'extends' nested more than {} levels deep: "
                "{}".format(_MAX_EXTENDS_DEPTH, abs_path))

        raw = cls._read_json(config_path)

        parent_ref = raw.pop('extends', None)
        if not parent_ref:
            return raw

        parent_path = parent_ref
        if not os.path.isabs(parent_path):
            parent_path = os.path.join(os.path.dirname(abs_path), parent_path)

        if not os.path.exists(parent_path):
            raise IOError(
                "Configuration '{}' extends '{}', which does not exist "
                "(looked in {})".format(config_path, parent_ref, parent_path))

        parent_data = cls._load_with_extends(parent_path, chain + [abs_path])

        return deep_merge(parent_data, raw)
    
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

    def get_dept_priority(self):
        """Get the ordered department priority list.

        Index 0 = highest priority (wins when the same asset exists in multiple
        departments). Falls back to a sensible default if not set in config.

        Returns:
            list: Department names ordered from highest to lowest priority.
                  Example: ['lighting', 'fx', 'cfx', 'anim', 'layout']
        """
        dept_priority_cfg = self.data.get('deptPriority', {})
        order = dept_priority_cfg.get('order')
        if order and isinstance(order, list) and len(order) > 0:
            return list(order)
        # Fallback if config key is missing
        return ['lighting', 'fx', 'cfx', 'anim', 'layout']

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

        # 1. Environment variable.  This must come BEFORE the repository path:
        # find_config() returns the first hit, so when the repo config was
        # listed first the environment variable could never win, which made it
        # dead configuration.  CTX_CONFIG is the current name; CTX_CONFIG_PATH
        # is kept as a deprecated alias.
        for var in ('CTX_CONFIG', 'CTX_CONFIG_PATH'):
            env_config = os.environ.get(var)
            if env_config:
                paths.append(env_config)

        # 2. Repository-based (default)
        # Assuming this module is in <repo>/config/project_config.py
        module_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(module_dir)
        repo_config = os.path.join(repo_root, 'project_configs', 'ctx_config.json')
        paths.append(repo_config)

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

    def get_logging_config(self):
        """Get logging configuration.

        Returns:
            dict: Logging config with keys: level, file, verbose.
                  Defaults to {'level': 'INFO', 'file': None, 'verbose': False}
                  if the 'logging' section is absent from the config file.
        """
        return self.data.get('logging', {'level': 'INFO', 'file': None, 'verbose': False})

    def get_token_pattern(self, token_name):
        """Return regex pattern for a token from config.

        Args:
            token_name (str): Token name (e.g. 'ver', 'ep', 'shot')

        Returns:
            str: Regex pattern string, or None if not defined
        """
        return self.data.get('tokens', {}).get(token_name, {}).get('pattern')

    def get_extensions(self):
        """Return supported file extensions list from config.

        Returns:
            list: List of extension strings (without leading dot, e.g. ['abc', 'vdb']),
                  or empty list if not defined. Note: the config stores extensions with
                  a leading dot (e.g. '.abc') so this method strips them for consistency
                  with the callers that add their own dot prefix.
        """
        raw = self.data.get('extensions', [])
        return [e.lstrip('.') for e in raw]

    def get_camera_file_suffix(self):
        """Return camera file suffix pattern from config.

        Returns:
            str: Camera file suffix (e.g. '_camera'), defaults to '_camera' if not set
        """
        return self.data.get('assetDiscovery', {}).get('cameraFileSuffix', '_camera')

    def get_gaffer_attributes(self):
        """Return gaffer attribute definition dict from config.

        Returns:
            dict: Gaffer attribute definitions with 'simple' and 'compound' keys,
                  or empty dict if not defined
        """
        return self.data.get('gafferAttributes', {})

    def get_gaffer_simple_attributes(self):
        """Return list of simple (scalar) gaffer attribute names.

        Returns:
            list: Simple attribute names (e.g. ['intensity', 'exposure', ...])
        """
        return self.get_gaffer_attributes().get('simple', [])

    def get_gaffer_compound_attributes(self):
        """Return dict of compound gaffer attribute names to their components.

        Returns:
            dict: Maps compound name to component list
                  (e.g. {'color': ['colorR', 'colorG', 'colorB'], ...})
        """
        return self.get_gaffer_attributes().get('compound', {})

    def get_renderer_config(self, renderer_name):
        """Return config dict for a specific renderer.

        Args:
            renderer_name (str): 'redshift' | 'arnold' | 'maya'

        Returns:
            dict or None
        """
        return self.data.get('renderers', {}).get(renderer_name)

    def get_standin_node_type(self, renderer_name):
        """Return the standin node type for a renderer.

        Args:
            renderer_name (str): Renderer name.

        Returns:
            str or None: Node type string (e.g. 'RedshiftProxyMesh') or None.
        """
        cfg = self.get_renderer_config(renderer_name) or {}
        return cfg.get('standinNodeType')

    def get_standin_file_attr(self, renderer_name):
        """Return the standin file attribute name for a renderer.

        Args:
            renderer_name (str): Renderer name.

        Returns:
            str or None: Attribute name (e.g. 'fileName') or None.
        """
        cfg = self.get_renderer_config(renderer_name) or {}
        return cfg.get('standinFileAttr')

    def get_preferred_extensions(self, renderer_name):
        """Return preferred file extensions for a renderer.

        Args:
            renderer_name (str): Renderer name.

        Returns:
            list: Extensions in preference order, without leading dot.
                  Empty list if renderer not in config.
        """
        cfg = self.get_renderer_config(renderer_name) or {}
        return cfg.get('preferredExtensions', [])

    def get_batch_render_config(self):
        """Return full batchRender config dict."""
        return self.data.get('batchRender', {})

    def get_reserved_gpus(self):
        """Return number of GPUs reserved for interactive use."""
        return int(self.get_batch_render_config().get('reservedGpus', 1))

    def get_temp_scene_max_count(self):
        """Return max number of temp scenes to keep (0 = unlimited)."""
        return int(self.get_batch_render_config().get('tempSceneMaxCount', 5))

    def get_temp_scene_dir(self):
        """Return configured temp scene directory or None (auto)."""
        return self.get_batch_render_config().get('tempSceneDir')

    def get_batch_log_dir(self):
        """Return configured log directory or None (auto)."""
        return self.get_batch_render_config().get('logDir')

    def get_frame_handles(self):
        """Return extra handle frames to add around shot range."""
        return int(self.get_batch_render_config().get('frameHandles', 0))

    def get_slate_manager_config(self):
        """Return full slateManager config dict."""
        return self.data.get('slateManager', {})

    def get_default_frame_range_mode(self):
        """Return default frame range mode for batch render Configure tab.

        Returns:
            str: 'startEnd' (default) or 'full'.
        """
        return self.get_slate_manager_config().get('defaultFrameRangeMode', 'startEnd')

    def get_asset_type_policies(self):
        """Return per-asset-type naming and discovery policy overrides.

        Consumed by core/asset_types.py.  An empty dict means the built-in
        defaults apply.

        Returns:
            dict: {assetType: {parse, publishShape, namespace, ...}}
        """
        return self.data.get('assetTypePolicies', {})

    def get_cfx_config(self):
        """Return full cfx config dict."""
        return self.data.get('cfx', {})

    def get_cfx_group_name(self):
        """Return the scene group all CFX standins are parented under."""
        return self.get_cfx_config().get('groupName', 'Cfx_Grp')

    def get_cfx_standin_suffix(self):
        """Return the standin transform suffix (shape appends 'Shape')."""
        return self.get_cfx_config().get('standinSuffix', '_aiStandIn')

    def get_cfx_frame_token(self):
        """Return the literal frame token left in the standin path.

        Arnold substitutes this itself when useFrameExtension is enabled, so
        it must survive token expansion unexpanded.
        """
        return self.get_cfx_config().get('frameToken', '####')

    def get_cfx_frame_driver(self):
        """Return how the standin frameNumber attribute is driven.

        'time' connects time1.outTime; 'none' leaves it untouched.
        """
        return self.get_cfx_config().get('frameDriver', 'time')

    def get_cfx_extension(self):
        """Return the CFX publish file extension (without dot)."""
        return self.get_cfx_config().get('extension', 'ass')

    def get_cfx_attribute(self, key):
        """Map a logical standin attribute name to its Maya attribute name.

        MtoA attribute names have drifted across versions, so they are
        config-driven rather than hardcoded.

        Args:
            key (str): One of 'path', 'useFrameExtension', 'frameNumber',
                'frameOffset'.

        Returns:
            str: Maya attribute name.
        """
        defaults = {
            'path': 'dso',
            'useFrameExtension': 'useFrameExtension',
            'frameNumber': 'frameNumber',
            'frameOffset': 'frameOffset',
        }
        attrs = self.get_cfx_config().get('attributes', {})
        return attrs.get(key, defaults.get(key, key))

    def __repr__(self):
        """String representation of ProjectConfig."""
        return "ProjectConfig(config_path='{}', version='{}')".format(
            self.config_path, self.version
        )

