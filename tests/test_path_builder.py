# -*- coding: utf-8 -*-
"""Tests for core/path_builder.py"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import unittest
import os
import sys
import tempfile
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.path_builder import PathBuilder
from config.project_config import ProjectConfig
from config.pattern_manager import PatternManager


class TestPathBuilder(unittest.TestCase):
    """Test PathBuilder class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary config file
        self.config_data = {
            "version": "1.0",
            "project": {
                "name": "TestProject",
                "code": "TST"
            },
            "roots": {
                "projRoot": "V:/"
            },
            "static_paths": {
                "sceneBase": "all/scene"
            },
            "templates": {},
            "patterns": {}
        }
        
        # Write config to temp file
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.config_data, self.temp_file)
        self.temp_file.close()
        
        # Create config objects
        self.config = ProjectConfig(self.temp_file.name)
        self.pattern_manager = PatternManager(self.config)
        
        # Create path builder
        self.builder = PathBuilder(self.pattern_manager)
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.temp_file.name)
    
    def test_parse_filename_valid(self):
        """Test parsing valid full filename."""
        filename = 'Ep04_sq0070_SH0170__CHAR_CatStompie_002.abc'
        result = self.builder.parse_filename(filename)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['ep'], 'Ep04')
        self.assertEqual(result['seq'], 'sq0070')
        self.assertEqual(result['shot'], 'SH0170')
        self.assertEqual(result['assetType'], 'CHAR')
        self.assertEqual(result['assetName'], 'CatStompie')
        self.assertEqual(result['variant'], '002')
        self.assertEqual(result['ext'], 'abc')
    
    def test_parse_filename_invalid(self):
        """Test parsing invalid filename."""
        filename = 'invalid_filename.abc'
        result = self.builder.parse_filename(filename)
        
        self.assertIsNone(result)
    
    def test_parse_filename_empty(self):
        """Test parsing empty filename."""
        result = self.builder.parse_filename('')
        
        self.assertIsNone(result)
    
    def test_parse_namespace_valid(self):
        """Test parsing valid namespace."""
        namespace = 'CHAR_CatStompie_002'
        result = self.builder.parse_namespace(namespace)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['assetType'], 'CHAR')
        self.assertEqual(result['assetName'], 'CatStompie')
        self.assertEqual(result['variant'], '002')
    
    def test_parse_namespace_invalid(self):
        """Test parsing invalid namespace."""
        namespace = 'invalid_namespace'
        result = self.builder.parse_namespace(namespace)
        
        self.assertIsNone(result)
    
    def test_parse_namespace_empty(self):
        """Test parsing empty namespace."""
        result = self.builder.parse_namespace('')
        
        self.assertIsNone(result)
    
    def test_detect_input_format_filename(self):
        """Test detecting filename format."""
        input_str = 'Ep04_sq0070_SH0170__CHAR_CatStompie_002.abc'
        format_type = self.builder.detect_input_format(input_str)
        
        self.assertEqual(format_type, 'filename')
    
    def test_detect_input_format_namespace(self):
        """Test detecting namespace format."""
        input_str = 'CHAR_CatStompie_002'
        format_type = self.builder.detect_input_format(input_str)
        
        self.assertEqual(format_type, 'namespace')
    
    def test_detect_input_format_invalid(self):
        """Test detecting invalid format."""
        input_str = 'invalid_input'
        format_type = self.builder.detect_input_format(input_str)
        
        self.assertIsNone(format_type)
    
    def test_build_context_from_filename(self):
        """Test building context from filename."""
        filename = 'Ep04_sq0070_SH0170__CHAR_CatStompie_002.abc'
        context = self.builder.build_context_from_filename(filename)
        
        self.assertIsNotNone(context)
        self.assertEqual(context['ep'], 'Ep04')
        self.assertEqual(context['seq'], 'sq0070')
        self.assertEqual(context['shot'], 'SH0170')
        self.assertEqual(context['assetType'], 'CHAR')
        self.assertEqual(context['assetName'], 'CatStompie')
        self.assertEqual(context['variant'], '002')
        self.assertEqual(context['ext'], 'abc')
    
    def test_build_context_from_namespace(self):
        """Test building context from namespace."""
        namespace = 'CHAR_CatStompie_002'
        shot_context = {
            'ep': 'Ep04',
            'seq': 'sq0070',
            'shot': 'SH0170'
        }
        
        context = self.builder.build_context_from_namespace(namespace, shot_context)
        
        self.assertIsNotNone(context)
        self.assertEqual(context['ep'], 'Ep04')
        self.assertEqual(context['seq'], 'sq0070')
        self.assertEqual(context['shot'], 'SH0170')
        self.assertEqual(context['assetType'], 'CHAR')
        self.assertEqual(context['assetName'], 'CatStompie')
        self.assertEqual(context['variant'], '002')


if __name__ == '__main__':
    unittest.main()

