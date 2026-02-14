# -*- coding: utf-8 -*-
"""Template management system for path templates.

This module provides utilities to load, validate, and manage path templates
from the project configuration. Templates use token-based substitution for
dynamic path construction.

Author: Context Variables Pipeline
Date: 2026-02-14
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import re


class TemplateManager(object):
    """Manages path templates from configuration.
    
    This class provides utilities to:
    - Load templates from ProjectConfig
    - Validate template syntax
    - Extract tokens from templates
    - Provide template lookup by name
    
    Example:
        >>> from config.project_config import ProjectConfig
        >>> from config.template_manager import TemplateManager
        >>> 
        >>> config = ProjectConfig('examples/ctx_config.json')
        >>> template_mgr = TemplateManager(config)
        >>> 
        >>> # Get a template
        >>> template = template_mgr.get_template('publish_path')
        >>> # Returns: '$PROJ_ROOT/$project/$scene_base/$ep/$seq/$shot/$dept/publish'
        >>> 
        >>> # Get all tokens in a template
        >>> tokens = template_mgr.get_template_tokens('publish_path')
        >>> # Returns: ['PROJ_ROOT', 'project', 'scene_base', 'ep', 'seq', 'shot', 'dept']
    """
    
    # Token pattern: matches $token_name
    TOKEN_PATTERN = re.compile(r'\$([a-zA-Z_][a-zA-Z0-9_]*)')
    
    def __init__(self, project_config):
        """Initialize template manager.
        
        Args:
            project_config (ProjectConfig): Project configuration instance
        """
        self.project_config = project_config
        self.templates = self._load_templates()
        self._validate_templates()
    
    def _load_templates(self):
        """Load templates from configuration.
        
        Returns:
            dict: Templates dictionary
        """
        return self.project_config.get_templates()
    
    def _validate_templates(self):
        """Validate all templates for syntax errors.
        
        Raises:
            ValueError: If template syntax is invalid
        """
        for name, template in self.templates.items():
            if not isinstance(template, str):
                raise ValueError(
                    "Template '{}' must be a string, got {}".format(
                        name, type(template).__name__
                    )
                )
            
            # Check for empty templates
            if not template.strip():
                raise ValueError("Template '{}' is empty".format(name))
    
    def get_template(self, name):
        """Get template by name.
        
        Args:
            name (str): Template name
        
        Returns:
            str: Template string, or None if not found
        """
        return self.templates.get(name)
    
    def get_all_templates(self):
        """Get all templates.
        
        Returns:
            dict: All templates
        """
        return self.templates.copy()
    
    def has_template(self, name):
        """Check if template exists.
        
        Args:
            name (str): Template name
        
        Returns:
            bool: True if template exists
        """
        return name in self.templates
    
    def get_template_tokens(self, name):
        """Extract all tokens from a template.
        
        Args:
            name (str): Template name
        
        Returns:
            list: List of token names (without $ prefix), or None if template not found
        
        Example:
            >>> tokens = template_mgr.get_template_tokens('publish_path')
            >>> # Returns: ['PROJ_ROOT', 'project', 'scene_base', 'ep', 'seq', 'shot', 'dept']
        """
        template = self.get_template(name)
        if template is None:
            return None
        
        return self.extract_tokens(template)
    
    @classmethod
    def extract_tokens(cls, template):
        """Extract all tokens from a template string.

        Args:
            template (str): Template string

        Returns:
            list: List of token names (without $ prefix)

        Example:
            >>> tokens = TemplateManager.extract_tokens('$PROJ_ROOT/$project/$ep')
            >>> # Returns: ['PROJ_ROOT', 'project', 'ep']
        """
        matches = cls.TOKEN_PATTERN.findall(template)
        # Return unique tokens in order of appearance
        seen = set()
        result = []
        for token in matches:
            if token not in seen:
                seen.add(token)
                result.append(token)
        return result

    def validate_template_tokens(self, name, required_tokens=None):
        """Validate that a template contains required tokens.

        Args:
            name (str): Template name
            required_tokens (list, optional): List of required token names

        Returns:
            tuple: (is_valid, missing_tokens)

        Example:
            >>> is_valid, missing = template_mgr.validate_template_tokens(
            ...     'publish_path', ['ep', 'seq', 'shot']
            ... )
        """
        if required_tokens is None:
            return (True, [])

        template_tokens = self.get_template_tokens(name)
        if template_tokens is None:
            return (False, required_tokens)

        missing = [t for t in required_tokens if t not in template_tokens]
        return (len(missing) == 0, missing)

    def get_template_names(self):
        """Get all template names.

        Returns:
            list: List of template names
        """
        return list(self.templates.keys())

    def __repr__(self):
        """String representation of TemplateManager.

        Returns:
            str: String representation
        """
        return "TemplateManager({} templates)".format(len(self.templates))

