# -*- coding: utf-8 -*-
"""Pattern management system for regex patterns.

This module provides utilities to load, validate, and manage regex patterns
from the project configuration. Patterns are used for parsing filenames,
namespaces, and version strings.

Author: Context Variables Pipeline
Date: 2026-02-14
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import re


class PatternManager(object):
    """Manages regex patterns from configuration.
    
    This class provides utilities to:
    - Load patterns from ProjectConfig
    - Compile and cache regex patterns
    - Validate pattern syntax
    - Parse filenames, namespaces, and versions
    - Provide pattern testing utilities
    
    Example:
        >>> from config.project_config import ProjectConfig
        >>> from config.pattern_manager import PatternManager
        >>> 
        >>> config = ProjectConfig('examples/ctx_config.json')
        >>> pattern_mgr = PatternManager(config)
        >>> 
        >>> # Parse a filename
        >>> result = pattern_mgr.parse_filename('Ep04_sq0070_SH0170__CHAR_CatStompie_001.abc')
        >>> # Returns: {'ep': 'Ep04', 'seq': 'sq0070', 'shot': 'SH0170', 
        >>> #           'assetType': 'CHAR', 'assetName': 'CatStompie', 
        >>> #           'variant': '001', 'ext': 'abc'}
    """
    
    # Default patterns based on POC reference
    DEFAULT_PATTERNS = {
        'fullFilename': r'^(Ep\d+)_(sq\d+)_(SH\d+)__([A-Z]+)_(.+)_(\d+)\.(abc|ma|mb|vdb|ass|rs)$',
        'namespace': r'^([A-Z]+)_(.+)_(\d+)$',
        'version': r'v(\d{3})',
        'shotContext': r'(Ep\d+)_(sq\d+)_(SH\d+)'
    }
    
    def __init__(self, project_config):
        """Initialize pattern manager.
        
        Args:
            project_config (ProjectConfig): Project configuration instance
        """
        self.project_config = project_config
        self.patterns = self._load_patterns()
        self.compiled_patterns = {}
        self._compile_patterns()
    
    def _load_patterns(self):
        """Load patterns from configuration.
        
        Returns:
            dict: Patterns dictionary
        """
        config_patterns = self.project_config.get_patterns()
        
        # Merge with defaults (config patterns override defaults)
        patterns = self.DEFAULT_PATTERNS.copy()
        if config_patterns:
            patterns.update(config_patterns)
        
        return patterns
    
    def _compile_patterns(self):
        """Compile all patterns and cache them.
        
        Raises:
            ValueError: If pattern syntax is invalid
        """
        for name, pattern in self.patterns.items():
            if not isinstance(pattern, str):
                raise ValueError(
                    "Pattern '{}' must be a string, got {}".format(
                        name, type(pattern).__name__
                    )
                )
            
            # Check for empty patterns
            if not pattern.strip():
                raise ValueError("Pattern '{}' is empty".format(name))
            
            # Try to compile the pattern
            try:
                self.compiled_patterns[name] = re.compile(pattern)
            except re.error as e:
                raise ValueError(
                    "Pattern '{}' has invalid regex syntax: {}".format(name, str(e))
                )
    
    def get_pattern(self, name):
        """Get pattern string by name.
        
        Args:
            name (str): Pattern name
        
        Returns:
            str: Pattern string, or None if not found
        """
        return self.patterns.get(name)
    
    def get_compiled_pattern(self, name):
        """Get compiled regex pattern by name.
        
        Args:
            name (str): Pattern name
        
        Returns:
            re.Pattern: Compiled pattern, or None if not found
        """
        return self.compiled_patterns.get(name)
    
    def has_pattern(self, name):
        """Check if pattern exists.
        
        Args:
            name (str): Pattern name
        
        Returns:
            bool: True if pattern exists
        """
        return name in self.patterns
    
    def get_all_patterns(self):
        """Get all pattern strings.
        
        Returns:
            dict: All patterns
        """
        return self.patterns.copy()
    
    def get_pattern_names(self):
        """Get all pattern names.

        Returns:
            list: List of pattern names
        """
        return list(self.patterns.keys())

    def parse_filename(self, filename):
        """Parse full filename using the 'fullFilename' pattern.

        Args:
            filename (str): Filename to parse

        Returns:
            dict: Parsed components, or None if parsing fails

        Example:
            >>> result = pattern_mgr.parse_filename('Ep04_sq0070_SH0170__CHAR_CatStompie_001.abc')
            >>> # Returns: {'ep': 'Ep04', 'seq': 'sq0070', 'shot': 'SH0170',
            >>> #           'assetType': 'CHAR', 'assetName': 'CatStompie',
            >>> #           'variant': '001', 'ext': 'abc'}
        """
        pattern = self.get_compiled_pattern('fullFilename')
        if pattern is None:
            return None

        match = pattern.match(filename)
        if not match:
            return None

        groups = match.groups()
        if len(groups) >= 7:
            return {
                'ep': groups[0],
                'seq': groups[1],
                'shot': groups[2],
                'assetType': groups[3],
                'assetName': groups[4],
                'variant': groups[5],
                'ext': groups[6]
            }

        return None

    def parse_namespace(self, namespace):
        """Parse namespace using the 'namespace' pattern.

        Args:
            namespace (str): Namespace to parse

        Returns:
            dict: Parsed components, or None if parsing fails

        Example:
            >>> result = pattern_mgr.parse_namespace('CHAR_CatStompie_001')
            >>> # Returns: {'assetType': 'CHAR', 'assetName': 'CatStompie', 'variant': '001'}
        """
        pattern = self.get_compiled_pattern('namespace')
        if pattern is None:
            return None

        match = pattern.match(namespace)
        if not match:
            return None

        groups = match.groups()
        if len(groups) >= 3:
            return {
                'assetType': groups[0],
                'assetName': groups[1],
                'variant': groups[2]
            }

        return None

    def parse_version(self, version_str):
        """Parse version string using the 'version' pattern.

        Args:
            version_str (str): Version string to parse (e.g., 'v003')

        Returns:
            int: Version number, or None if parsing fails

        Example:
            >>> version = pattern_mgr.parse_version('v003')
            >>> # Returns: 3
        """
        pattern = self.get_compiled_pattern('version')
        if pattern is None:
            return None

        match = pattern.search(version_str)
        if not match:
            return None

        try:
            return int(match.group(1))
        except (ValueError, IndexError):
            return None

    def parse_shot_context(self, text):
        """Parse shot context using the 'shotContext' pattern.

        Args:
            text (str): Text to parse (filename, path, etc.)

        Returns:
            dict: Parsed components, or None if parsing fails

        Example:
            >>> result = pattern_mgr.parse_shot_context('Ep04_sq0070_SH0170_lighting_v001.ma')
            >>> # Returns: {'ep': 'Ep04', 'seq': 'sq0070', 'shot': 'SH0170'}
        """
        pattern = self.get_compiled_pattern('shotContext')
        if pattern is None:
            return None

        match = pattern.search(text)
        if not match:
            return None

        groups = match.groups()
        if len(groups) >= 3:
            return {
                'ep': groups[0],
                'seq': groups[1],
                'shot': groups[2]
            }

        return None

    def test_pattern(self, pattern_name, test_string):
        """Test a pattern against a string.

        Args:
            pattern_name (str): Pattern name
            test_string (str): String to test

        Returns:
            tuple: (matches, groups) where matches is bool and groups is list

        Example:
            >>> matches, groups = pattern_mgr.test_pattern('namespace', 'CHAR_CatStompie_001')
            >>> # Returns: (True, ['CHAR', 'CatStompie', '001'])
        """
        pattern = self.get_compiled_pattern(pattern_name)
        if pattern is None:
            return (False, [])

        match = pattern.search(test_string)
        if match:
            return (True, list(match.groups()))

        return (False, [])

    def __repr__(self):
        """String representation of PatternManager.

        Returns:
            str: String representation
        """
        return "PatternManager({} patterns)".format(len(self.patterns))

