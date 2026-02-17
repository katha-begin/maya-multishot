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

    def resolve_paths_batch(self, assets, context, template_name='assetPath', version=None,
                           validate_exists=False, fallback_strategy=None):
        """Resolve paths for multiple assets with the same context.

        This method is optimized for resolving many assets in the same shot/context
        by caching template lookups and reusing the full context.

        Args:
            assets (list): List of asset dicts, each containing:
                          {'assetType': 'CHAR', 'assetName': 'Hero', 'variant': '001'}
            context (dict): Shared context for all assets (ep, seq, shot, dept, etc.)
            template_name (str): Template to use (default: 'assetPath')
            version (str, optional): Version string for all assets
            validate_exists (bool): Whether to validate paths exist
            fallback_strategy (callable, optional): Fallback function for failed resolutions

        Returns:
            dict: Mapping of asset identifier to (path, error) tuple
                  Asset identifier format: "TYPE_Name_variant"

        Example:
            >>> assets = [
            ...     {'assetType': 'CHAR', 'assetName': 'Hero', 'variant': '001'},
            ...     {'assetType': 'PROP', 'assetName': 'Table', 'variant': '001'},
            ... ]
            >>> context = {'ep': 'Ep04', 'seq': 'sq0070', 'shot': 'SH0170', 'dept': 'anim'}
            >>> results = resolver.resolve_paths_batch(assets, context)
            >>> for asset_id, (path, error) in results.items():
            ...     if error:
            ...         print("Error for {}: {}".format(asset_id, error))
            ...     else:
            ...         print("{}: {}".format(asset_id, path))
        """
        import time
        start_time = time.time()

        results = {}
        success_count = 0
        error_count = 0

        logger.info("Batch resolving {} assets for template '{}' with context: {}".format(
            len(assets), template_name, context))

        # Cache template lookup (only load once)
        try:
            template = self.config.get_template(template_name)
            if not template:
                available = list(self.config.get_templates().keys())
                error = TemplateNotFoundError(template_name, available)
                logger.error("Template '{}' not found".format(template_name))
                # Return error for all assets
                for asset in assets:
                    asset_id = "{}_{}_{}" .format(
                        asset.get('assetType', 'UNKNOWN'),
                        asset.get('assetName', 'UNKNOWN'),
                        asset.get('variant', '000')
                    )
                    results[asset_id] = (None, error)
                return results
        except Exception as e:
            logger.error("Failed to load template '{}': {}".format(template_name, e))
            # Return error for all assets
            for asset in assets:
                asset_id = "{}_{}_{}" .format(
                    asset.get('assetType', 'UNKNOWN'),
                    asset.get('assetName', 'UNKNOWN'),
                    asset.get('variant', '000')
                )
                results[asset_id] = (None, e)
            return results

        # Build full context once (reused for all assets)
        base_context = self._build_full_context(context, version)

        # Resolve each asset
        for asset in assets:
            # Create asset identifier
            asset_id = "{}_{}_{}" .format(
                asset.get('assetType', 'UNKNOWN'),
                asset.get('assetName', 'UNKNOWN'),
                asset.get('variant', '000')
            )

            try:
                # Merge asset data into context
                asset_context = base_context.copy()
                asset_context.update(asset)

                # Expand tokens
                expanded = self.token_expander.expand_tokens(template, asset_context, version_override=version)

                # Check for unexpanded tokens
                remaining_tokens = self.token_expander.extract_tokens(expanded)
                if remaining_tokens:
                    raise TokenExpansionError(template, remaining_tokens, asset_context)

                # Normalize path
                resolved_path = os.path.normpath(expanded)

                # Validate exists if requested
                if validate_exists and not os.path.exists(resolved_path):
                    raise PathValidationError(resolved_path, "Path does not exist")

                results[asset_id] = (resolved_path, None)
                success_count += 1

            except ResolverError as e:
                error_count += 1
                logger.debug("Failed to resolve asset {}: {}".format(asset_id, e))

                # Try fallback strategy if provided
                if fallback_strategy:
                    try:
                        fallback_path = fallback_strategy(template_name, asset_context, e)
                        if fallback_path:
                            results[asset_id] = (fallback_path, None)
                            success_count += 1
                            error_count -= 1
                            continue
                    except Exception as fallback_error:
                        logger.debug("Fallback strategy failed for {}: {}".format(
                            asset_id, fallback_error))

                results[asset_id] = (None, e)

        # Log statistics
        elapsed_time = time.time() - start_time
        logger.info("Batch resolution complete: {} succeeded, {} failed in {:.3f}s ({:.1f} assets/sec)".format(
            success_count, error_count, elapsed_time,
            len(assets) / elapsed_time if elapsed_time > 0 else 0))

        return results

    def validate_path(self, path, check_readable=True):
        """Validate that a path exists and is accessible.

        Args:
            path (str): Path to validate
            check_readable (bool): Whether to check if path is readable

        Returns:
            dict: Validation result with keys:
                  - 'valid' (bool): Whether path is valid
                  - 'exists' (bool): Whether path exists
                  - 'readable' (bool): Whether path is readable (if check_readable=True)
                  - 'is_file' (bool): Whether path is a file
                  - 'is_dir' (bool): Whether path is a directory
                  - 'error' (str): Error message if validation failed, None otherwise

        Example:
            >>> result = resolver.validate_path('/path/to/file.abc')
            >>> if result['valid']:
            ...     print("Path is valid")
            ... else:
            ...     print("Error: {}".format(result['error']))
        """
        result = {
            'valid': False,
            'exists': False,
            'readable': False,
            'is_file': False,
            'is_dir': False,
            'error': None
        }

        try:
            # Check if path exists
            if not os.path.exists(path):
                result['error'] = "Path does not exist"
                logger.debug("Path validation failed: {} does not exist".format(path))
                return result

            result['exists'] = True
            result['is_file'] = os.path.isfile(path)
            result['is_dir'] = os.path.isdir(path)

            # Check if readable
            if check_readable:
                if result['is_file']:
                    # Try to open file for reading
                    try:
                        with open(path, 'r') as f:
                            f.read(1)  # Read one byte to test
                        result['readable'] = True
                    except (IOError, OSError) as e:
                        result['error'] = "Path is not readable: {}".format(e)
                        logger.debug("Path validation failed: {} is not readable".format(path))
                        return result
                elif result['is_dir']:
                    # Try to list directory
                    try:
                        os.listdir(path)
                        result['readable'] = True
                    except (IOError, OSError) as e:
                        result['error'] = "Directory is not readable: {}".format(e)
                        logger.debug("Path validation failed: {} is not readable".format(path))
                        return result
            else:
                result['readable'] = True  # Skip check

            # All checks passed
            result['valid'] = True
            logger.debug("Path validation succeeded: {}".format(path))

        except Exception as e:
            result['error'] = "Validation error: {}".format(e)
            logger.error("Path validation error for {}: {}".format(path, e))

        return result

    def validate_paths_batch(self, paths, check_readable=True, stop_on_error=False):
        """Validate multiple paths in batch.

        Args:
            paths (list): List of paths to validate
            check_readable (bool): Whether to check if paths are readable
            stop_on_error (bool): If True, stop on first validation failure

        Returns:
            dict: Mapping of path to validation result dict

        Example:
            >>> paths = ['/path/to/file1.abc', '/path/to/file2.abc']
            >>> results = resolver.validate_paths_batch(paths)
            >>> for path, result in results.items():
            ...     if result['valid']:
            ...         print("{}: OK".format(path))
            ...     else:
            ...         print("{}: {}".format(path, result['error']))
        """
        import time
        start_time = time.time()

        results = {}
        valid_count = 0
        invalid_count = 0

        logger.info("Validating {} paths".format(len(paths)))

        for path in paths:
            result = self.validate_path(path, check_readable)
            results[path] = result

            if result['valid']:
                valid_count += 1
            else:
                invalid_count += 1
                if stop_on_error:
                    logger.warning("Stopping validation due to error: {}".format(result['error']))
                    break

        # Log statistics
        elapsed_time = time.time() - start_time
        logger.info("Path validation complete: {} valid, {} invalid in {:.3f}s".format(
            valid_count, invalid_count, elapsed_time))

        return results

    def _build_full_context(self, context, version=None):
        """Build full context with roots, static paths, and user context.

        Supports both new platform-specific roots and legacy flat roots.

        Args:
            context (dict): User-provided context
            version (str, optional): Version override

        Returns:
            dict: Full context dictionary
        """
        full_context = {}

        # Add roots (mapped to current platform)
        roots = self.config.get_roots()

        # Check if new format (platform-specific)
        if 'windows' in roots or 'linux' in roots:
            # New format: get roots for current platform
            current_platform = self.platform_config.get_platform()
            platform_roots = roots.get(current_platform, {})
            for root_name, root_path in platform_roots.items():
                full_context[root_name] = root_path
        else:
            # Legacy format: use platform_config to resolve
            for root_name in roots.keys():
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

