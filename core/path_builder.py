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
    
    def __init__(self, pattern_manager):
        """Initialize path builder.
        
        Args:
            pattern_manager (PatternManager): Pattern manager for parsing
        """
        self.pattern_manager = pattern_manager
    
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

