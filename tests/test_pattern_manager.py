# -*- coding: utf-8 -*-
"""Unit tests for PatternManager class.

Author: Context Variables Pipeline
Date: 2026-02-14
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import os
import sys
import tempfile
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.project_config import ProjectConfig
from config.pattern_manager import PatternManager


class TestPatternManager(unittest.TestCase):
    """Test cases for PatternManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary config file
        self.temp_dir = tempfile.mkdtemp()
        self.temp_config_path = os.path.join(self.temp_dir, 'test_config.json')
        
        # Create test configuration
        test_config = {
            'version': '1.0',
            'project': {
                'name': 'TestProject',
                'code': 'TST'
            },
            'roots': {
                'projRoot': 'V:/'
            },
            'staticPaths': {
                'sceneBase': 'all/scene'
            },
            'templates': {
                'publishPath': '$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish'
            },
            'patterns': {
                'fullFilename': r'^(Ep\d+)_(sq\d+)_(SH\d+)__([A-Z]+)_(.+)_(\d+)\.(abc|ma|mb)$',
                'namespace': r'^([A-Z]+)_(.+)_(\d+)$',
                'version': r'v(\d{3})',
                'shotContext': r'(Ep\d+)_(sq\d+)_(SH\d+)'
            }
        }
        
        with open(self.temp_config_path, 'w') as f:
            json.dump(test_config, f, indent=2)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test PatternManager initialization."""
        config = ProjectConfig(self.temp_config_path)
        pattern_mgr = PatternManager(config)
        
        self.assertIsNotNone(pattern_mgr)
        self.assertIsNotNone(pattern_mgr.patterns)
        self.assertIsNotNone(pattern_mgr.compiled_patterns)
    
    def test_load_patterns(self):
        """Test loading patterns from config."""
        config = ProjectConfig(self.temp_config_path)
        pattern_mgr = PatternManager(config)
        
        patterns = pattern_mgr.get_all_patterns()
        self.assertIn('fullFilename', patterns)
        self.assertIn('namespace', patterns)
        self.assertIn('version', patterns)
    
    def test_get_pattern(self):
        """Test getting specific pattern."""
        config = ProjectConfig(self.temp_config_path)
        pattern_mgr = PatternManager(config)
        
        pattern = pattern_mgr.get_pattern('namespace')
        self.assertEqual(pattern, r'^([A-Z]+)_(.+)_(\d+)$')
    
    def test_get_pattern_nonexistent(self):
        """Test getting nonexistent pattern returns None."""
        config = ProjectConfig(self.temp_config_path)
        pattern_mgr = PatternManager(config)
        
        pattern = pattern_mgr.get_pattern('nonexistent')
        self.assertIsNone(pattern)
    
    def test_has_pattern(self):
        """Test checking if pattern exists."""
        config = ProjectConfig(self.temp_config_path)
        pattern_mgr = PatternManager(config)
        
        self.assertTrue(pattern_mgr.has_pattern('namespace'))
        self.assertFalse(pattern_mgr.has_pattern('nonexistent'))
    
    def test_get_compiled_pattern(self):
        """Test getting compiled pattern."""
        config = ProjectConfig(self.temp_config_path)
        pattern_mgr = PatternManager(config)
        
        compiled = pattern_mgr.get_compiled_pattern('namespace')
        self.assertIsNotNone(compiled)
        
        # Test that it's actually compiled
        match = compiled.match('CHAR_CatStompie_001')
        self.assertIsNotNone(match)
    
    def test_parse_filename_valid(self):
        """Test parsing valid filename."""
        config = ProjectConfig(self.temp_config_path)
        pattern_mgr = PatternManager(config)
        
        result = pattern_mgr.parse_filename('Ep04_sq0070_SH0170__CHAR_CatStompie_001.abc')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['ep'], 'Ep04')
        self.assertEqual(result['seq'], 'sq0070')
        self.assertEqual(result['shot'], 'SH0170')
        self.assertEqual(result['assetType'], 'CHAR')
        self.assertEqual(result['assetName'], 'CatStompie')
        self.assertEqual(result['variant'], '001')
        self.assertEqual(result['ext'], 'abc')
    
    def test_parse_filename_invalid(self):
        """Test parsing invalid filename."""
        config = ProjectConfig(self.temp_config_path)
        pattern_mgr = PatternManager(config)
        
        result = pattern_mgr.parse_filename('invalid_filename.abc')
        self.assertIsNone(result)
    
    def test_parse_namespace_valid(self):
        """Test parsing valid namespace."""
        config = ProjectConfig(self.temp_config_path)
        pattern_mgr = PatternManager(config)

        result = pattern_mgr.parse_namespace('CHAR_CatStompie_001')

        self.assertIsNotNone(result)
        self.assertEqual(result['assetType'], 'CHAR')
        self.assertEqual(result['assetName'], 'CatStompie')
        self.assertEqual(result['variant'], '001')

    def test_parse_namespace_invalid(self):
        """Test parsing invalid namespace."""
        config = ProjectConfig(self.temp_config_path)
        pattern_mgr = PatternManager(config)

        result = pattern_mgr.parse_namespace('invalid_namespace')
        self.assertIsNone(result)

    def test_parse_version_valid(self):
        """Test parsing valid version string."""
        config = ProjectConfig(self.temp_config_path)
        pattern_mgr = PatternManager(config)

        result = pattern_mgr.parse_version('v003')
        self.assertEqual(result, 3)

        result = pattern_mgr.parse_version('v123')
        self.assertEqual(result, 123)

    def test_parse_version_invalid(self):
        """Test parsing invalid version string."""
        config = ProjectConfig(self.temp_config_path)
        pattern_mgr = PatternManager(config)

        result = pattern_mgr.parse_version('invalid')
        self.assertIsNone(result)

    def test_parse_shot_context_valid(self):
        """Test parsing valid shot context."""
        config = ProjectConfig(self.temp_config_path)
        pattern_mgr = PatternManager(config)

        result = pattern_mgr.parse_shot_context('Ep04_sq0070_SH0170_lighting_v001.ma')

        self.assertIsNotNone(result)
        self.assertEqual(result['ep'], 'Ep04')
        self.assertEqual(result['seq'], 'sq0070')
        self.assertEqual(result['shot'], 'SH0170')

    def test_parse_shot_context_invalid(self):
        """Test parsing invalid shot context."""
        config = ProjectConfig(self.temp_config_path)
        pattern_mgr = PatternManager(config)

        result = pattern_mgr.parse_shot_context('invalid_context.ma')
        self.assertIsNone(result)

    def test_test_pattern_match(self):
        """Test pattern testing with match."""
        config = ProjectConfig(self.temp_config_path)
        pattern_mgr = PatternManager(config)

        matches, groups = pattern_mgr.test_pattern('namespace', 'CHAR_CatStompie_001')

        self.assertTrue(matches)
        self.assertEqual(groups, ['CHAR', 'CatStompie', '001'])

    def test_test_pattern_no_match(self):
        """Test pattern testing with no match."""
        config = ProjectConfig(self.temp_config_path)
        pattern_mgr = PatternManager(config)

        matches, groups = pattern_mgr.test_pattern('namespace', 'invalid')

        self.assertFalse(matches)
        self.assertEqual(groups, [])

    def test_get_pattern_names(self):
        """Test getting all pattern names."""
        config = ProjectConfig(self.temp_config_path)
        pattern_mgr = PatternManager(config)

        names = pattern_mgr.get_pattern_names()
        self.assertIn('fullFilename', names)
        self.assertIn('namespace', names)
        self.assertIn('version', names)

    def test_repr(self):
        """Test string representation."""
        config = ProjectConfig(self.temp_config_path)
        pattern_mgr = PatternManager(config)

        repr_str = repr(pattern_mgr)
        self.assertIn('PatternManager', repr_str)

    def test_validate_invalid_regex(self):
        """Test validation fails for invalid regex."""
        # Create config with invalid regex
        test_config = {
            'version': '1.0',
            'project': {'name': 'Test', 'code': 'TST'},
            'roots': {'projRoot': 'V:/'},
            'staticPaths': {'sceneBase': 'all/scene'},
            'templates': {},
            'patterns': {'invalid': '[unclosed'}
        }

        temp_path = os.path.join(self.temp_dir, 'invalid_pattern.json')
        with open(temp_path, 'w') as f:
            json.dump(test_config, f)

        config = ProjectConfig(temp_path)
        with self.assertRaises(ValueError) as ctx:
            PatternManager(config)

        self.assertIn('invalid regex syntax', str(ctx.exception))

    def test_validate_empty_pattern(self):
        """Test validation fails for empty pattern."""
        # Create config with empty pattern
        test_config = {
            'version': '1.0',
            'project': {'name': 'Test', 'code': 'TST'},
            'roots': {'projRoot': 'V:/'},
            'staticPaths': {'sceneBase': 'all/scene'},
            'templates': {},
            'patterns': {'empty': '   '}
        }

        temp_path = os.path.join(self.temp_dir, 'empty_pattern.json')
        with open(temp_path, 'w') as f:
            json.dump(test_config, f)

        config = ProjectConfig(temp_path)
        with self.assertRaises(ValueError) as ctx:
            PatternManager(config)

        self.assertIn('empty', str(ctx.exception))

    def test_validate_non_string_pattern(self):
        """Test validation fails for non-string pattern."""
        # Create config with non-string pattern
        test_config = {
            'version': '1.0',
            'project': {'name': 'Test', 'code': 'TST'},
            'roots': {'projRoot': 'V:/'},
            'staticPaths': {'sceneBase': 'all/scene'},
            'templates': {},
            'patterns': {'invalid': 123}
        }

        temp_path = os.path.join(self.temp_dir, 'invalid_type_pattern.json')
        with open(temp_path, 'w') as f:
            json.dump(test_config, f)

        config = ProjectConfig(temp_path)
        with self.assertRaises(ValueError) as ctx:
            PatternManager(config)

        self.assertIn('must be a string', str(ctx.exception))

    def test_default_patterns(self):
        """Test that default patterns are loaded when config has no patterns."""
        # Create config without patterns
        test_config = {
            'version': '1.0',
            'project': {'name': 'Test', 'code': 'TST'},
            'roots': {'projRoot': 'V:/'},
            'staticPaths': {'sceneBase': 'all/scene'},
            'templates': {},
            'patterns': {}
        }

        temp_path = os.path.join(self.temp_dir, 'no_patterns.json')
        with open(temp_path, 'w') as f:
            json.dump(test_config, f)

        config = ProjectConfig(temp_path)
        pattern_mgr = PatternManager(config)

        # Should have default patterns
        self.assertTrue(pattern_mgr.has_pattern('fullFilename'))
        self.assertTrue(pattern_mgr.has_pattern('namespace'))
        self.assertTrue(pattern_mgr.has_pattern('version'))


if __name__ == '__main__':
    unittest.main()

