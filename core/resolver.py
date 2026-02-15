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
import logging
from .tokens import TokenExpander

# Set up logging
logger = logging.getLogger(__name__)


# Custom Exceptions

class ResolverError(Exception):
    """Base exception for path resolver errors."""
    pass


class TemplateNotFoundError(ResolverError):
    """Raised when a template is not found in configuration.

    Attributes:
        template_name (str): Name of the template that was not found
        available_templates (list): List of available template names
    """

    def __init__(self, template_name, available_templates=None):
        """Initialize TemplateNotFoundError.

        Args:
            template_name (str): Name of the template that was not found
            available_templates (list, optional): List of available template names
        """
        self.template_name = template_name
        self.available_templates = available_templates or []

        message = "Template '{}' not found in configuration".format(template_name)
        if self.available_templates:
            message += ". Available templates: {}".format(', '.join(self.available_templates))

        super(TemplateNotFoundError, self).__init__(message)


class TokenExpansionError(ResolverError):
    """Raised when token expansion fails.

    Attributes:
        template (str): The template being expanded
        unexpanded_tokens (list): List of tokens that could not be expanded
        context (dict): The context that was provided
    """

    def __init__(self, template, unexpanded_tokens, context=None):
        """Initialize TokenExpansionError.

        Args:
            template (str): The template being expanded
            unexpanded_tokens (list): List of tokens that could not be expanded
            context (dict, optional): The context that was provided
        """
        self.template = template
        self.unexpanded_tokens = unexpanded_tokens
        self.context = context or {}

        message = "Failed to expand tokens in template '{}'. Unexpanded tokens: {}".format(
            template, ', '.join(unexpanded_tokens))

        if self.context:
            message += ". Available context keys: {}".format(', '.join(self.context.keys()))

        super(TokenExpansionError, self).__init__(message)


class PathValidationError(ResolverError):
    """Raised when path validation fails.

    Attributes:
        path (str): The path that failed validation
        reason (str): Reason for validation failure
    """

    def __init__(self, path, reason="Path does not exist"):
        """Initialize PathValidationError.

        Args:
            path (str): The path that failed validation
            reason (str): Reason for validation failure
        """
        self.path = path
        self.reason = reason

        message = "Path validation failed for '{}': {}".format(path, reason)

        super(PathValidationError, self).__init__(message)


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
    
    def resolve_path(self, template_name, context, version=None, validate_exists=False, fallback_strategy=None):
        """Resolve template path to actual file path.

        Args:
            template_name (str): Name of template in config (e.g., 'publishPath')
            context (dict): Context data with token values
            version (str, optional): Version string (e.g., 'v003', 'latest')
            validate_exists (bool): Whether to validate path exists
            fallback_strategy (callable, optional): Function to call if resolution fails.
                                                   Should accept (template_name, context, error)
                                                   and return a fallback path or None.

        Returns:
            str: Resolved absolute path

        Raises:
            TemplateNotFoundError: If template not found in config
            TokenExpansionError: If required tokens cannot be expanded
            PathValidationError: If path validation fails

        Example:
            >>> resolver = PathResolver(config, platform_config)
            >>> context = {'ep': 'Ep04', 'seq': 'sq0070', 'shot': 'SH0170'}
            >>> path = resolver.resolve_path('publishPath', context)
        """
        try:
            # Get template from config
            template = self.config.get_template(template_name)
            if not template:
                available = list(self.config.get_templates().keys())
                logger.error("Template '{}' not found. Available: {}".format(
                    template_name, ', '.join(available)))
                raise TemplateNotFoundError(template_name, available)

            logger.debug("Resolving template '{}': {}".format(template_name, template))

            # Build full context with roots and static paths
            full_context = self._build_full_context(context, version)

            # Expand tokens
            try:
                expanded = self.token_expander.expand_tokens(template, full_context, version_override=version)
            except Exception as e:
                logger.error("Token expansion failed for template '{}': {}".format(template_name, e))
                raise

            # Check for unexpanded tokens
            remaining_tokens = self.token_expander.extract_tokens(expanded)
            if remaining_tokens:
                logger.error("Unexpanded tokens in '{}': {}. Context keys: {}".format(
                    template_name, ', '.join(remaining_tokens), ', '.join(full_context.keys())))
                raise TokenExpansionError(template, remaining_tokens, full_context)

            # Normalize path
            resolved_path = os.path.normpath(expanded)

            logger.debug("Resolved '{}' to: {}".format(template_name, resolved_path))

            # Validate exists if requested
            if validate_exists and not os.path.exists(resolved_path):
                logger.warning("Resolved path does not exist: {}".format(resolved_path))
                raise PathValidationError(resolved_path, "Path does not exist")

            return resolved_path

        except ResolverError as e:
            # Try fallback strategy if provided
            if fallback_strategy:
                logger.info("Attempting fallback strategy for '{}'".format(template_name))
                try:
                    fallback_path = fallback_strategy(template_name, context, e)
                    if fallback_path:
                        logger.info("Fallback strategy succeeded: {}".format(fallback_path))
                        return fallback_path
                except Exception as fallback_error:
                    logger.error("Fallback strategy failed: {}".format(fallback_error))

            # Re-raise original error
            raise
    
    def resolve_batch(self, template_name, contexts, version=None, validate_exists=False,
                     stop_on_error=False, fallback_strategy=None):
        """Resolve multiple paths in batch.

        Args:
            template_name (str): Name of template in config
            contexts (list): List of context dictionaries
            version (str, optional): Version string
            validate_exists (bool): Whether to validate paths exist
            stop_on_error (bool): If True, raise exception on first error.
                                 If False, continue and return None for failed resolutions.
            fallback_strategy (callable, optional): Fallback function for failed resolutions

        Returns:
            list: List of tuples (path, error) where path is the resolved path or None,
                  and error is the exception or None

        Example:
            >>> contexts = [
            ...     {'ep': 'Ep04', 'seq': 'sq0070', 'shot': 'SH0170'},
            ...     {'ep': 'Ep04', 'seq': 'sq0070', 'shot': 'SH0180'},
            ... ]
            >>> results = resolver.resolve_batch('publishPath', contexts)
            >>> for path, error in results:
            ...     if error:
            ...         print("Error: {}".format(error))
            ...     else:
            ...         print("Path: {}".format(path))
        """
        results = []
        success_count = 0
        error_count = 0

        logger.info("Batch resolving {} contexts for template '{}'".format(
            len(contexts), template_name))

        for i, context in enumerate(contexts):
            try:
                path = self.resolve_path(template_name, context, version, validate_exists, fallback_strategy)
                results.append((path, None))
                success_count += 1
            except ResolverError as e:
                error_count += 1
                logger.debug("Batch resolution failed for context {}: {}".format(i, e))

                if stop_on_error:
                    logger.error("Stopping batch resolution due to error: {}".format(e))
                    raise

                results.append((None, e))

        logger.info("Batch resolution complete: {} succeeded, {} failed".format(
            success_count, error_count))

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

