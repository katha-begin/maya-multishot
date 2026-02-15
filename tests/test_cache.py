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

from core.cache import VersionCache, scan_publish_directory
from config.pattern_manager import PatternManager
from config.project_config import ProjectConfig


class TestScanPublishDirectory(unittest.TestCase):
    """Test cases for scan_publish_directory function."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temp directory for testing
        self.temp_dir = tempfile.mkdtemp()

        # Create test publish directory
        self.publish_dir = os.path.join(self.temp_dir, 'publish')
        os.makedirs(self.publish_dir)

        # Load pattern manager
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'examples', 'ctx_config.json')
        self.config = ProjectConfig(config_path)
        self.pm = PatternManager(self.config)

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_scan_valid_files(self):
        """Test scanning directory with valid asset files."""
        # Create test files
        test_files = [
            'Ep04_sq0070_SH0170__CHAR_CatStompie_001.abc',
            'Ep04_sq0070_SH0170__CHAR_DogBuddy_002.ma',
            'Ep04_sq0070_SH0170__PROP_Table_001.mb',
        ]

        for filename in test_files:
            filepath = os.path.join(self.publish_dir, filename)
            with open(filepath, 'w') as f:
                f.write('test')

        # Scan directory
        assets = scan_publish_directory(self.publish_dir, self.pm)

        # Verify results
        self.assertEqual(len(assets), 3)

        # Check first asset
        asset = assets[0]
        self.assertIn('filename', asset)
        self.assertIn('assetType', asset)
        self.assertIn('assetName', asset)
        self.assertIn('variant', asset)
        self.assertIn('fullPath', asset)
        self.assertIn('ep', asset)
        self.assertIn('seq', asset)
        self.assertIn('shot', asset)

        # Verify specific values
        self.assertEqual(asset['ep'], 'Ep04')
        self.assertEqual(asset['seq'], 'sq0070')
        self.assertEqual(asset['shot'], 'SH0170')

    def test_scan_multiple_extensions(self):
        """Test scanning with multiple file extensions."""
        extensions = ['abc', 'ma', 'mb', 'vdb', 'ass', 'rs']

        for ext in extensions:
            filename = 'Ep01_sq0010_SH0020__CHAR_Test_001.{}'.format(ext)
            filepath = os.path.join(self.publish_dir, filename)
            with open(filepath, 'w') as f:
                f.write('test')

        assets = scan_publish_directory(self.publish_dir, self.pm)

        self.assertEqual(len(assets), len(extensions))

        # Verify all extensions are present
        found_extensions = set(asset['extension'] for asset in assets)
        self.assertEqual(found_extensions, set(extensions))

    def test_scan_invalid_files(self):
        """Test scanning with invalid/unparseable files."""
        # Create mix of valid and invalid files
        files = [
            'Ep04_sq0070_SH0170__CHAR_Valid_001.abc',  # Valid
            'invalid_filename.abc',  # Invalid
            'no_double_underscore.abc',  # Invalid
            'README.txt',  # Wrong extension
        ]

        for filename in files:
            filepath = os.path.join(self.publish_dir, filename)
            with open(filepath, 'w') as f:
                f.write('test')

        assets = scan_publish_directory(self.publish_dir, self.pm)

        # Should only find 1 valid asset
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]['assetName'], 'Valid')

    def test_scan_nonexistent_directory(self):
        """Test scanning non-existent directory."""
        assets = scan_publish_directory('/nonexistent/path', self.pm)

        self.assertEqual(assets, [])

    def test_scan_file_not_directory(self):
        """Test scanning a file instead of directory."""
        # Create a file
        filepath = os.path.join(self.temp_dir, 'test.txt')
        with open(filepath, 'w') as f:
            f.write('test')

        assets = scan_publish_directory(filepath, self.pm)

        self.assertEqual(assets, [])

    def test_scan_empty_directory(self):
        """Test scanning empty directory."""
        assets = scan_publish_directory(self.publish_dir, self.pm)

        self.assertEqual(assets, [])

    def test_scan_with_subdirectories(self):
        """Test that subdirectories are skipped."""
        # Create subdirectory
        subdir = os.path.join(self.publish_dir, 'v001')
        os.makedirs(subdir)

        # Create file in main directory
        filepath = os.path.join(self.publish_dir, 'Ep04_sq0070_SH0170__CHAR_Test_001.abc')
        with open(filepath, 'w') as f:
            f.write('test')

        # Create file in subdirectory (should be skipped)
        subfile = os.path.join(subdir, 'Ep04_sq0070_SH0170__CHAR_SubTest_001.abc')
        with open(subfile, 'w') as f:
            f.write('test')

        assets = scan_publish_directory(self.publish_dir, self.pm)

        # Should only find file in main directory
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]['assetName'], 'Test')

    def test_scan_without_pattern_manager(self):
        """Test scanning without pattern manager (fallback parsing)."""
        # Create test file
        filepath = os.path.join(self.publish_dir, 'Ep04_sq0070_SH0170__CHAR_Test_001.abc')
        with open(filepath, 'w') as f:
            f.write('test')

        # Scan without pattern manager
        assets = scan_publish_directory(self.publish_dir, None)

        # Should still parse using basic parser
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]['assetType'], 'CHAR')
        self.assertEqual(assets[0]['assetName'], 'Test')
        self.assertEqual(assets[0]['variant'], '001')

    def test_scan_multipart_asset_names(self):
        """Test scanning files with multi-part asset names."""
        # Create file with multi-part name
        filepath = os.path.join(self.publish_dir, 'Ep04_sq0070_SH0170__CHAR_Cat_Stompie_Hero_001.abc')
        with open(filepath, 'w') as f:
            f.write('test')

        assets = scan_publish_directory(self.publish_dir, self.pm)

        self.assertEqual(len(assets), 1)
        # Multi-part names should be joined with underscores
        self.assertIn('Cat', assets[0]['assetName'])


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

