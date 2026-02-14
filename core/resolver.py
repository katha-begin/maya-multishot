# -*- coding: utf-8 -*-
"""Path Resolver - Resolve template paths to actual file paths.

This module provides path resolution functionality that combines:
- Template management (from config)
- Token expansion (from tokens module)
- Platform mapping (from platform_config)
- Version resolution (from cache)

Author: Pipeline TD
Date: 2024
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
from .tokens import TokenExpander


class PathResolver(object):
    """Resolve template paths to actual file paths.
    
    Combines templates, tokens, context, and platform mapping to resolve
    full file paths for assets and shots.
    
    Example:
        >>> from config.project_config import ProjectConfig
        >>> from config.platform_config import PlatformConfig
        >>> from core.resolver import PathResolver
        >>> 
        >>> config = ProjectConfig('path/to/config.json')
        >>> platform_config = PlatformConfig(config)
        >>> resolver = PathResolver(config, platform_config)
        >>> 
        >>> context = {'ep': 'Ep04', 'seq': 'sq0070', 'shot': 'SH0170', 'dept': 'anim'}
        >>> path = resolver.resolve_path('publish_path', context)
        >>> print(path)
        'V:/SWA/all/scene/Ep04/sq0070/SH0170/anim/publish'
    """
    
    def __init__(self, project_config, platform_config):
        """Initialize path resolver.
        
        Args:
            project_config (ProjectConfig): Project configuration
            platform_config (PlatformConfig): Platform configuration
        """
        self.config = project_config
        self.platform_config = platform_config
        self.token_expander = TokenExpander()
    
    def resolve_path(self, template_name, context, version=None, validate_exists=False):
        """Resolve template path to actual file path.
        
        Args:
            template_name (str): Name of template in config (e.g., 'publish_path')
            context (dict): Context data with token values
            version (str, optional): Version string (e.g., 'v003', 'latest')
            validate_exists (bool): Whether to validate path exists
        
        Returns:
            str: Resolved absolute path
        
        Raises:
            KeyError: If template not found
            ValueError: If required tokens missing or path invalid
        """
        # Get template from config
        template = self.config.get_template(template_name)
        if not template:
            raise KeyError("Template '{}' not found in config".format(template_name))
        
        # Build full context with roots and static paths
        full_context = self._build_full_context(context, version)
        
        # Expand tokens
        expanded = self.token_expander.expand_tokens(template, full_context, version_override=version)
        
        # Check for unexpanded tokens
        remaining_tokens = self.token_expander.extract_tokens(expanded)
        if remaining_tokens:
            raise ValueError("Unexpanded tokens in path: {}".format(', '.join(remaining_tokens)))
        
        # Normalize path
        resolved_path = os.path.normpath(expanded)
        
        # Validate exists if requested
        if validate_exists and not os.path.exists(resolved_path):
            raise ValueError("Resolved path does not exist: {}".format(resolved_path))
        
        return resolved_path
    
    def resolve_batch(self, template_name, contexts, version=None, validate_exists=False):
        """Resolve multiple paths in batch.
        
        Args:
            template_name (str): Name of template in config
            contexts (list): List of context dictionaries
            version (str, optional): Version string
            validate_exists (bool): Whether to validate paths exist
        
        Returns:
            list: List of resolved paths (same order as contexts)
        """
        results = []
        for context in contexts:
            try:
                path = self.resolve_path(template_name, context, version, validate_exists)
                results.append(path)
            except (KeyError, ValueError) as e:
                # Store error instead of path
                results.append(None)
        
        return results
    
    def _build_full_context(self, context, version=None):
        """Build full context with roots, static paths, and user context.
        
        Args:
            context (dict): User-provided context
            version (str, optional): Version override
        
        Returns:
            dict: Full context dictionary
        """
        full_context = {}
        
        # Add roots (mapped to current platform)
        for root_name in self.config.get_roots().keys():
            root_path = self.platform_config.get_root_for_platform(root_name)
            full_context[root_name] = root_path
        
        # Add static paths
        full_context.update(self.config.get_static_paths())
        
        # Add project code
        full_context['project'] = self.config.get_project_code()
        
        # Add user context (overrides above if conflicts)
        full_context.update(context)
        
        # Add version if provided
        if version:
            full_context['ver'] = version
        
        return full_context

