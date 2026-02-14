# -*- coding: utf-8 -*-
"""Unit tests for VersionCache class.

Author: Context Variables Pipeline
Date: 2026-02-14
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import unittest
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cache import VersionCache
from config.pattern_manager import PatternManager
from config.project_config import ProjectConfig


class TestVersionCache(unittest.TestCase):
    """Test cases for VersionCache class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cache = VersionCache()
        
        # Create temp directory for testing
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test files
        self.publish_dir = os.path.join(self.temp_dir, 'publish', 'v003')
        os.makedirs(self.publish_dir)
        
        # Create test files
        test_files = [
            'Ep04_sq0070_SH0170__CHAR_CatStompie_001.abc',
            'Ep04_sq0070_SH0170__CHAR_CatStompie_002.abc',
            'Ep04_sq0070_SH0170__PROP_Table_001.abc',
        ]
        
        for filename in test_files:
            filepath = os.path.join(self.publish_dir, filename)
            with open(filepath, 'w') as f:
                f.write('test')
        
        # Load pattern manager
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'examples', 'ctx_config.json')
        self.config = ProjectConfig(config_path)
        self.pm = PatternManager(self.config)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_build_cache(self):
        """Test building cache from filesystem."""
        cache_data = self.cache.build_cache(self.publish_dir, self.pm)
        
        self.assertIn('CHAR_CatStompie_001', cache_data)
        self.assertIn('CHAR_CatStompie_002', cache_data)
        self.assertIn('PROP_Table_001', cache_data)
    
    def test_build_cache_nonexistent_path(self):
        """Test building cache for non-existent path."""
        cache_data = self.cache.build_cache('/nonexistent/path', self.pm)
        
        self.assertEqual(cache_data, {})
    
    def test_get_versions(self):
        """Test getting versions for an asset."""
        self.cache.build_cache(self.publish_dir, self.pm)
        
        versions = self.cache.get_versions(self.publish_dir, 'CHAR_CatStompie_001')
        
        self.assertIsInstance(versions, list)
        self.assertIn('v003', versions)
    
    def test_get_versions_not_in_cache(self):
        """Test getting versions for asset not in cache."""
        versions = self.cache.get_versions('/nonexistent/path', 'CHAR_Test_001')
        
        self.assertEqual(versions, [])
    
    def test_get_latest_version(self):
        """Test getting latest version."""
        self.cache.build_cache(self.publish_dir, self.pm)
        
        latest = self.cache.get_latest_version(self.publish_dir, 'CHAR_CatStompie_001')
        
        self.assertEqual(latest, 'v003')
    
    def test_get_latest_version_not_found(self):
        """Test getting latest version when not found."""
        latest = self.cache.get_latest_version('/nonexistent/path', 'CHAR_Test_001')
        
        self.assertIsNone(latest)
    
    def test_clear(self):
        """Test clearing cache."""
        self.cache.build_cache(self.publish_dir, self.pm)
        
        self.cache.clear()
        
        versions = self.cache.get_versions(self.publish_dir, 'CHAR_CatStompie_001')
        self.assertEqual(versions, [])
    
    def test_save_and_load(self):
        """Test saving and loading cache."""
        self.cache.build_cache(self.publish_dir, self.pm)
        
        # Save to file
        cache_file = os.path.join(self.temp_dir, 'cache.json')
        self.cache.save_to_file(cache_file)
        
        # Create new cache and load
        new_cache = VersionCache()
        new_cache.load_from_file(cache_file)
        
        versions = new_cache.get_versions(self.publish_dir, 'CHAR_CatStompie_001')
        self.assertIn('v003', versions)
    
    def test_load_nonexistent_file(self):
        """Test loading from non-existent file."""
        self.cache.load_from_file('/nonexistent/cache.json')
        
        # Should not raise error
        self.assertEqual(len(self.cache._cache), 0)


if __name__ == '__main__':
    unittest.main()

