# -*- coding: utf-8 -*-
"""Path Builder - Build full paths from filenames or namespaces.

This module provides path building functionality that:
- Parses full filenames to extract shot context and asset metadata
- Parses namespaces to extract asset metadata (requires context)
- Builds full paths using templates and cache
- Supports version resolution (latest or specific)

Author: Pipeline TD
Date: 2024
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import re
import os
import logging

logger = logging.getLogger(__name__)


class PathBuilder(object):
    """Build full paths from filenames or namespaces.
    
    Supports two input formats:
    1. Full filename: Ep04_sq0070_SH0170__CHAR_CatStompie_002.abc
    2. Namespace only: CHAR_CatStompie_002 (requires context)
    
    Example:
        >>> from config.project_config import ProjectConfig
        >>> from config.pattern_manager import PatternManager
        >>> from core.path_builder import PathBuilder
        >>> 
        >>> config = ProjectConfig('path/to/config.json')
        >>> pattern_mgr = PatternManager(config)
        >>> builder = PathBuilder(pattern_mgr)
        >>> 
        >>> # Parse full filename
        >>> data = builder.parse_filename('Ep04_sq0070_SH0170__CHAR_CatStompie_002.abc')
        >>> print(data)
        {'ep': 'Ep04', 'seq': 'sq0070', 'shot': 'SH0170', 
         'assetType': 'CHAR', 'assetName': 'CatStompie', 'variant': '002', 'ext': 'abc'}
        >>> 
        >>> # Parse namespace
        >>> data = builder.parse_namespace('CHAR_CatStompie_002')
        >>> print(data)
        {'assetType': 'CHAR', 'assetName': 'CatStompie', 'variant': '002'}
    """
    
    def __init__(self, pattern_manager, resolver=None, cache=None):
        """Initialize path builder.

        Args:
            pattern_manager (PatternManager): Pattern manager for parsing
            resolver (PathResolver, optional): Path resolver for building paths
            cache (VersionCache, optional): Version cache for version lookup
        """
        self.pattern_manager = pattern_manager
        self.resolver = resolver
        self.cache = cache
    
    def parse_filename(self, filename):
        """Parse full filename to extract components.

        Args:
            filename (str): Full filename (e.g., 'Ep04_sq0070_SH0170__CHAR_CatStompie_002.abc')

        Returns:
            dict: Parsed components or None if invalid
                  Keys: ep, seq, shot, assetType, assetName, variant, ext
        """
        if not filename:
            return None

        # Parse using pattern manager
        result = self.pattern_manager.parse_filename(filename)

        return result
    
    def parse_namespace(self, namespace):
        """Parse namespace to extract asset components.

        Args:
            namespace (str): Namespace (e.g., 'CHAR_CatStompie_002')

        Returns:
            dict: Parsed components or None if invalid
                  Keys: assetType, assetName, variant
        """
        if not namespace:
            return None

        # Parse using pattern manager
        result = self.pattern_manager.parse_namespace(namespace)

        return result
    
    def detect_input_format(self, input_str):
        """Detect whether input is full filename or namespace.
        
        Args:
            input_str (str): Input string
        
        Returns:
            str: 'filename', 'namespace', or None if invalid
        """
        if not input_str:
            return None
        
        # Try parsing as full filename first
        if self.parse_filename(input_str):
            return 'filename'
        
        # Try parsing as namespace
        if self.parse_namespace(input_str):
            return 'namespace'
        
        return None
    
    def build_context_from_filename(self, filename):
        """Build context dictionary from full filename.
        
        Args:
            filename (str): Full filename
        
        Returns:
            dict: Context dictionary with all parsed components
        """
        parsed = self.parse_filename(filename)
        if not parsed:
            return None
        
        # Build context from parsed data
        context = {
            'ep': parsed.get('ep'),
            'seq': parsed.get('seq'),
            'shot': parsed.get('shot'),
            'assetType': parsed.get('assetType'),
            'assetName': parsed.get('assetName'),
            'variant': parsed.get('variant'),
            'ext': parsed.get('ext')
        }
        
        return context
    
    def build_context_from_namespace(self, namespace, shot_context):
        """Build context dictionary from namespace and shot context.
        
        Args:
            namespace (str): Namespace string
            shot_context (dict): Shot context with ep, seq, shot
        
        Returns:
            dict: Context dictionary with all components
        """
        parsed = self.parse_namespace(namespace)
        if not parsed:
            return None
        
        # Build context from parsed data and shot context
        context = dict(shot_context)
        context.update({
            'assetType': parsed.get('assetType'),
            'assetName': parsed.get('assetName'),
            'variant': parsed.get('variant')
        })

        return context

    def build_path(self, input_str, context=None, version='latest', template_name='assetPath'):
        """Build full path from filename or namespace.

        This is the main entry point for path building. It:
        1. Detects input format (filename or namespace)
        2. Parses input to extract components
        3. Builds context dictionary
        4. Resolves version if 'latest'
        5. Uses resolver to build full path

        Args:
            input_str (str): Input string (filename or namespace)
            context (dict, optional): Shot context (required for namespace input)
            version (str): Version string ('latest' or 'v###')
            template_name (str): Template to use for path resolution

        Returns:
            str: Full resolved path or None if not found

        Example:
            >>> # With full filename
            >>> path = builder.build_path('Ep04_sq0070_SH0170__CHAR_CatStompie_002.abc')
            >>> print(path)
            'V:/TST/all/scene/Ep04/sq0070/SH0170/anim/publish/CHAR/CatStompie/002/Ep04_sq0070_SH0170__CHAR_CatStompie_002.abc'
            >>>
            >>> # With namespace (requires context)
            >>> context = {'ep': 'Ep04', 'seq': 'sq0070', 'shot': 'SH0170', 'dept': 'anim'}
            >>> path = builder.build_path('CHAR_CatStompie_002', context=context)
        """
        if not input_str:
            logger.error("build_path: Empty input string")
            return None

        if not self.resolver:
            logger.error("build_path: No resolver configured")
            return None

        logger.info("Building path for input: '{}', version: '{}'".format(input_str, version))

        # Detect input format
        input_format = self.detect_input_format(input_str)
        if not input_format:
            logger.error("build_path: Invalid input format: '{}'".format(input_str))
            return None

        logger.debug("Detected input format: {}".format(input_format))

        # Build context based on input format
        if input_format == 'filename':
            full_context = self.build_context_from_filename(input_str)
            if not full_context:
                logger.error("build_path: Failed to parse filename: '{}'".format(input_str))
                return None
        elif input_format == 'namespace':
            if not context:
                logger.error("build_path: Namespace input requires context")
                return None
            full_context = self.build_context_from_namespace(input_str, context)
            if not full_context:
                logger.error("build_path: Failed to parse namespace: '{}'".format(input_str))
                return None
        else:
            logger.error("build_path: Unknown input format: {}".format(input_format))
            return None

        logger.debug("Built context: {}".format(full_context))

        # Resolve version if 'latest'
        resolved_version = version
        if version == 'latest' and self.cache:
            logger.debug("Resolving 'latest' version from cache")
            asset_id = "{}_{}_{}".format(
                full_context.get('assetType', 'UNKNOWN'),
                full_context.get('assetName', 'UNKNOWN'),
                full_context.get('variant', '000')
            )

            # Build publish path for cache lookup
            try:
                publish_path = self.resolver.resolve_path(
                    'publishPath',
                    full_context,
                    version=None
                )

                if publish_path:
                    # Get latest version from cache
                    latest = self.cache.get_latest_version(publish_path, asset_id)

                    if latest:
                        resolved_version = latest
                        logger.info("Resolved 'latest' to version: {}".format(resolved_version))
                    else:
                        logger.warning("No cached version found for asset: {}".format(asset_id))
                        # Continue with 'latest' - resolver will handle it
                else:
                    logger.warning("Could not resolve publish path for cache lookup")
            except Exception as e:
                logger.warning("Failed to resolve publish path for cache lookup: {}".format(e))

        # Use resolver to build full path
        try:
            path = self.resolver.resolve_path(
                template_name,
                full_context,
                version=resolved_version
            )

            if path:
                logger.info("Successfully built path: {}".format(path))
            else:
                logger.warning("Resolver returned None for input: '{}'".format(input_str))

            return path

        except Exception as e:
            logger.error("build_path: Failed to resolve path: {}".format(e))
            return None

