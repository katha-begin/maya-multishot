# -*- coding: utf-8 -*-
"""Tests for core/resolver.py"""

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

from core.resolver import PathResolver
from config.project_config import ProjectConfig
from config.platform_config import PlatformConfig


class TestPathResolver(unittest.TestCase):
    """Test PathResolver class."""
    
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
            "staticPaths": {
                "sceneBase": "all/scene"
            },
            "templates": {
                "publishPath": "$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish",
                "cachePath": "$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish/$ver",
                "assetPath": "$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish/$assetType/$assetName/$variant"
            },
            "patterns": {},
            "platformMapping": {
                "windows": {
                    "projRoot": "V:/"
                },
                "linux": {
                    "projRoot": "/mnt/test/"
                }
            }
        }
        
        # Write config to temp file
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.config_data, self.temp_file)
        self.temp_file.close()
        
        # Create config objects
        self.config = ProjectConfig(self.temp_file.name)
        self.platform_config = PlatformConfig(self.config)
        
        # Create resolver
        self.resolver = PathResolver(self.config, self.platform_config)
        
        # Test context
        self.context = {
            'ep': 'Ep01',
            'seq': 'sq0010',
            'shot': 'SH0010',
            'dept': 'anim'
        }
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.temp_file.name)
    
    def test_resolve_path_simple(self):
        """Test resolving simple path."""
        path = self.resolver.resolve_path('publishPath', self.context)

        expected = os.path.normpath('V:/TST/all/scene/Ep01/sq0010/SH0010/anim/publish')
        self.assertEqual(path, expected)

    def test_resolve_path_with_version(self):
        """Test resolving path with version."""
        path = self.resolver.resolve_path('cachePath', self.context, version='v003')
        
        expected = os.path.normpath('V:/TST/all/scene/Ep01/sq0010/SH0010/anim/publish/v003')
        self.assertEqual(path, expected)
    
    def test_resolve_path_with_asset_data(self):
        """Test resolving path with asset data."""
        context = dict(self.context)
        context.update({
            'assetType': 'CHAR',
            'assetName': 'Hero',
            'variant': '001'
        })
        
        path = self.resolver.resolve_path('assetPath', context)
        
        expected = os.path.normpath('V:/TST/all/scene/Ep01/sq0010/SH0010/anim/publish/CHAR/Hero/001')
        self.assertEqual(path, expected)
    
    def test_resolve_path_missing_template(self):
        """Test resolving with missing template."""
        with self.assertRaises(KeyError):
            self.resolver.resolve_path('nonexistent_template', self.context)
    
    def test_resolve_path_missing_token(self):
        """Test resolving with missing token value."""
        incomplete_context = {'ep': 'Ep01'}
        
        with self.assertRaises(ValueError):
            self.resolver.resolve_path('publishPath', incomplete_context)

    def test_resolve_batch(self):
        """Test batch resolution."""
        contexts = [
            {'ep': 'Ep01', 'seq': 'sq0010', 'shot': 'SH0010', 'dept': 'anim'},
            {'ep': 'Ep01', 'seq': 'sq0010', 'shot': 'SH0020', 'dept': 'anim'},
            {'ep': 'Ep01', 'seq': 'sq0020', 'shot': 'SH0030', 'dept': 'layout'}
        ]

        paths = self.resolver.resolve_batch('publishPath', contexts)
        
        self.assertEqual(len(paths), 3)
        self.assertIn('SH0010', paths[0])
        self.assertIn('SH0020', paths[1])
        self.assertIn('SH0030', paths[2])
        self.assertIn('layout', paths[2])
    
    def test_resolve_batch_with_errors(self):
        """Test batch resolution with some errors."""
        contexts = [
            {'ep': 'Ep01', 'seq': 'sq0010', 'shot': 'SH0010', 'dept': 'anim'},
            {'ep': 'Ep01'},  # Missing tokens
            {'ep': 'Ep01', 'seq': 'sq0020', 'shot': 'SH0030', 'dept': 'layout'}
        ]
        
        paths = self.resolver.resolve_batch('publishPath', contexts)

        self.assertEqual(len(paths), 3)
        self.assertIsNotNone(paths[0])
        self.assertIsNone(paths[1])  # Error case
        self.assertIsNotNone(paths[2])


if __name__ == '__main__':
    unittest.main()

