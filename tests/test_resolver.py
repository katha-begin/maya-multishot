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

from core.resolver import (
    PathResolver,
    TemplateNotFoundError,
    TokenExpansionError,
    PathValidationError,
    ResolverError
)
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
        with self.assertRaises(TemplateNotFoundError):
            self.resolver.resolve_path('nonexistent_template', self.context)

    def test_resolve_path_missing_token(self):
        """Test resolving with missing token value."""
        incomplete_context = {'ep': 'Ep01'}

        with self.assertRaises(TokenExpansionError):
            self.resolver.resolve_path('publishPath', incomplete_context)

    def test_resolve_batch(self):
        """Test batch resolution."""
        contexts = [
            {'ep': 'Ep01', 'seq': 'sq0010', 'shot': 'SH0010', 'dept': 'anim'},
            {'ep': 'Ep01', 'seq': 'sq0010', 'shot': 'SH0020', 'dept': 'anim'},
            {'ep': 'Ep01', 'seq': 'sq0020', 'shot': 'SH0030', 'dept': 'layout'}
        ]

        results = self.resolver.resolve_batch('publishPath', contexts)

        self.assertEqual(len(results), 3)
        # Check each result is a tuple (path, error)
        self.assertIn('SH0010', results[0][0])
        self.assertIsNone(results[0][1])
        self.assertIn('SH0020', results[1][0])
        self.assertIsNone(results[1][1])
        self.assertIn('SH0030', results[2][0])
        self.assertIn('layout', results[2][0])
        self.assertIsNone(results[2][1])
    
    def test_resolve_batch_with_errors(self):
        """Test batch resolution with some errors."""
        contexts = [
            {'ep': 'Ep01', 'seq': 'sq0010', 'shot': 'SH0010', 'dept': 'anim'},
            {'ep': 'Ep01'},  # Missing tokens
            {'ep': 'Ep01', 'seq': 'sq0020', 'shot': 'SH0030', 'dept': 'layout'}
        ]

        results = self.resolver.resolve_batch('publishPath', contexts)

        self.assertEqual(len(results), 3)
        # First should succeed
        self.assertIsNotNone(results[0][0])
        self.assertIsNone(results[0][1])
        # Second should fail
        self.assertIsNone(results[1][0])
        self.assertIsNotNone(results[1][1])
        # Third should succeed
        self.assertIsNotNone(results[2][0])
        self.assertIsNone(results[2][1])


class TestResolverErrorHandling(unittest.TestCase):
    """Test error handling in PathResolver."""

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
                "cachePath": "$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish/$ver"
            },
            "patterns": {},
            "platformMapping": {
                "windows": {
                    "projRoot": "V:/"
                },
                "linux": {
                    "projRoot": "/mnt/projects/"
                }
            }
        }

        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'config.json')

        with open(self.config_file, 'w') as f:
            json.dump(self.config_data, f)

        self.config = ProjectConfig(self.config_file)
        self.platform_config = PlatformConfig(self.config)
        self.resolver = PathResolver(self.config, self.platform_config)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_template_not_found_error(self):
        """Test TemplateNotFoundError is raised for missing template."""
        context = {'ep': 'Ep01', 'seq': 'sq0010', 'shot': 'SH0010', 'dept': 'anim'}

        with self.assertRaises(TemplateNotFoundError) as cm:
            self.resolver.resolve_path('nonexistentTemplate', context)

        error = cm.exception
        self.assertEqual(error.template_name, 'nonexistentTemplate')
        self.assertIn('publishPath', error.available_templates)
        self.assertIn('cachePath', error.available_templates)

    def test_token_expansion_error(self):
        """Test TokenExpansionError is raised for missing tokens."""
        context = {'ep': 'Ep01'}  # Missing seq, shot, dept

        with self.assertRaises(TokenExpansionError) as cm:
            self.resolver.resolve_path('publishPath', context)

        error = cm.exception
        self.assertIn('seq', error.unexpanded_tokens)
        self.assertIn('shot', error.unexpanded_tokens)
        self.assertIn('dept', error.unexpanded_tokens)

    def test_path_validation_error(self):
        """Test PathValidationError is raised when path doesn't exist."""
        context = {'ep': 'Ep01', 'seq': 'sq0010', 'shot': 'SH0010', 'dept': 'anim'}

        with self.assertRaises(PathValidationError) as cm:
            self.resolver.resolve_path('publishPath', context, validate_exists=True)

        error = cm.exception
        self.assertIn('V:', error.path)
        self.assertEqual(error.reason, "Path does not exist")

    def test_fallback_strategy_success(self):
        """Test fallback strategy is called on error."""
        context = {'ep': 'Ep01'}  # Missing tokens

        def fallback(template_name, ctx, error):
            # Return a fallback path (already normalized)
            return os.path.normpath("V:/TST/fallback/path")

        path = self.resolver.resolve_path('publishPath', context, fallback_strategy=fallback)

        self.assertEqual(path, os.path.normpath("V:/TST/fallback/path"))

    def test_fallback_strategy_failure(self):
        """Test original error is raised when fallback fails."""
        context = {'ep': 'Ep01'}  # Missing tokens

        def fallback(template_name, ctx, error):
            # Fallback also fails
            raise ValueError("Fallback failed")

        with self.assertRaises(TokenExpansionError):
            self.resolver.resolve_path('publishPath', context, fallback_strategy=fallback)

    def test_fallback_strategy_returns_none(self):
        """Test original error is raised when fallback returns None."""
        context = {'ep': 'Ep01'}  # Missing tokens

        def fallback(template_name, ctx, error):
            return None

        with self.assertRaises(TokenExpansionError):
            self.resolver.resolve_path('publishPath', context, fallback_strategy=fallback)

    def test_batch_stop_on_error(self):
        """Test batch resolution stops on first error when stop_on_error=True."""
        contexts = [
            {'ep': 'Ep01', 'seq': 'sq0010', 'shot': 'SH0010', 'dept': 'anim'},
            {'ep': 'Ep01'},  # Missing tokens - should stop here
            {'ep': 'Ep01', 'seq': 'sq0020', 'shot': 'SH0030', 'dept': 'layout'}
        ]

        with self.assertRaises(TokenExpansionError):
            self.resolver.resolve_batch('publishPath', contexts, stop_on_error=True)

    def test_batch_continue_on_error(self):
        """Test batch resolution continues on error when stop_on_error=False."""
        contexts = [
            {'ep': 'Ep01', 'seq': 'sq0010', 'shot': 'SH0010', 'dept': 'anim'},
            {'ep': 'Ep01'},  # Missing tokens
            {'ep': 'Ep01', 'seq': 'sq0020', 'shot': 'SH0030', 'dept': 'layout'}
        ]

        results = self.resolver.resolve_batch('publishPath', contexts, stop_on_error=False)

        self.assertEqual(len(results), 3)
        # First should succeed
        self.assertIsNotNone(results[0][0])
        self.assertIsNone(results[0][1])
        # Second should fail
        self.assertIsNone(results[1][0])
        self.assertIsInstance(results[1][1], TokenExpansionError)
        # Third should succeed
        self.assertIsNotNone(results[2][0])
        self.assertIsNone(results[2][1])

    def test_error_message_details(self):
        """Test error messages contain helpful details."""
        context = {'ep': 'Ep01'}

        try:
            self.resolver.resolve_path('publishPath', context)
        except TokenExpansionError as e:
            # Check error message contains helpful info
            error_msg = str(e)
            self.assertIn('seq', error_msg)
            self.assertIn('shot', error_msg)
            self.assertIn('dept', error_msg)
            self.assertIn('Available context keys', error_msg)


class TestBatchPathResolution(unittest.TestCase):
    """Test batch path resolution for multiple assets."""

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
                "assetPath": "$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish/$assetType/$assetName/$variant"
            },
            "patterns": {},
            "platformMapping": {
                "windows": {
                    "projRoot": "V:/"
                },
                "linux": {
                    "projRoot": "/mnt/projects/"
                }
            }
        }

        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'config.json')

        with open(self.config_file, 'w') as f:
            json.dump(self.config_data, f)

        self.config = ProjectConfig(self.config_file)
        self.platform_config = PlatformConfig(self.config)
        self.resolver = PathResolver(self.config, self.platform_config)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_resolve_paths_batch_success(self):
        """Test batch resolution of multiple assets."""
        assets = [
            {'assetType': 'CHAR', 'assetName': 'Hero', 'variant': '001'},
            {'assetType': 'PROP', 'assetName': 'Table', 'variant': '001'},
            {'assetType': 'CHAR', 'assetName': 'Villain', 'variant': '002'},
        ]
        context = {'ep': 'Ep01', 'seq': 'sq0010', 'shot': 'SH0010', 'dept': 'anim'}

        results = self.resolver.resolve_paths_batch(assets, context)

        # Check all assets resolved
        self.assertEqual(len(results), 3)

        # Check CHAR_Hero_001
        path, error = results['CHAR_Hero_001']
        self.assertIsNotNone(path)
        self.assertIsNone(error)
        self.assertIn('CHAR', path)
        self.assertIn('Hero', path)

        # Check PROP_Table_001
        path, error = results['PROP_Table_001']
        self.assertIsNotNone(path)
        self.assertIsNone(error)
        self.assertIn('PROP', path)
        self.assertIn('Table', path)

        # Check CHAR_Villain_002
        path, error = results['CHAR_Villain_002']
        self.assertIsNotNone(path)
        self.assertIsNone(error)
        self.assertIn('Villain', path)

    def test_resolve_paths_batch_with_errors(self):
        """Test batch resolution with some invalid assets."""
        assets = [
            {'assetType': 'CHAR', 'assetName': 'Hero', 'variant': '001'},
            {'assetName': 'Table', 'variant': '001'},  # Missing assetType
            {'assetType': 'CHAR', 'assetName': 'Villain', 'variant': '002'},
        ]
        context = {'ep': 'Ep01', 'seq': 'sq0010', 'shot': 'SH0010', 'dept': 'anim'}

        results = self.resolver.resolve_paths_batch(assets, context)

        # Check all assets processed
        self.assertEqual(len(results), 3)

        # First should succeed
        path, error = results['CHAR_Hero_001']
        self.assertIsNotNone(path)
        self.assertIsNone(error)

        # Second should fail (missing assetType)
        path, error = results['UNKNOWN_Table_001']
        self.assertIsNone(path)
        self.assertIsNotNone(error)

        # Third should succeed
        path, error = results['CHAR_Villain_002']
        self.assertIsNotNone(path)
        self.assertIsNone(error)

    def test_resolve_paths_batch_template_not_found(self):
        """Test batch resolution with invalid template."""
        assets = [
            {'assetType': 'CHAR', 'assetName': 'Hero', 'variant': '001'},
        ]
        context = {'ep': 'Ep01', 'seq': 'sq0010', 'shot': 'SH0010', 'dept': 'anim'}

        results = self.resolver.resolve_paths_batch(assets, context, template_name='nonexistent')

        # All assets should have same error
        self.assertEqual(len(results), 1)
        path, error = results['CHAR_Hero_001']
        self.assertIsNone(path)
        self.assertIsInstance(error, TemplateNotFoundError)

    def test_resolve_paths_batch_empty_list(self):
        """Test batch resolution with empty asset list."""
        assets = []
        context = {'ep': 'Ep01', 'seq': 'sq0010', 'shot': 'SH0010', 'dept': 'anim'}

        results = self.resolver.resolve_paths_batch(assets, context)

        self.assertEqual(len(results), 0)

    def test_resolve_paths_batch_with_version(self):
        """Test batch resolution with version override."""
        assets = [
            {'assetType': 'CHAR', 'assetName': 'Hero', 'variant': '001'},
        ]
        context = {'ep': 'Ep01', 'seq': 'sq0010', 'shot': 'SH0010', 'dept': 'anim'}

        results = self.resolver.resolve_paths_batch(assets, context, version='v003')

        path, error = results['CHAR_Hero_001']
        self.assertIsNotNone(path)
        self.assertIsNone(error)

    def test_resolve_paths_batch_performance(self):
        """Test batch resolution performance with many assets."""
        # Create 100 assets
        assets = []
        for i in range(100):
            assets.append({
                'assetType': 'CHAR',
                'assetName': 'Asset{:03d}'.format(i),
                'variant': '001'
            })

        context = {'ep': 'Ep01', 'seq': 'sq0010', 'shot': 'SH0010', 'dept': 'anim'}

        import time
        start = time.time()
        results = self.resolver.resolve_paths_batch(assets, context)
        elapsed = time.time() - start

        # Check all resolved
        self.assertEqual(len(results), 100)

        # Should be fast (< 1 second for 100 assets)
        self.assertLess(elapsed, 1.0)

        # Check all succeeded
        for asset_id, (path, error) in results.items():
            self.assertIsNotNone(path)
            self.assertIsNone(error)


class TestPathValidation(unittest.TestCase):
    """Test path validation functionality."""

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
                "publishPath": "$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish"
            },
            "patterns": {},
            "platformMapping": {
                "windows": {
                    "projRoot": "V:/"
                },
                "linux": {
                    "projRoot": "/mnt/projects/"
                }
            }
        }

        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'config.json')

        with open(self.config_file, 'w') as f:
            json.dump(self.config_data, f)

        self.config = ProjectConfig(self.config_file)
        self.platform_config = PlatformConfig(self.config)
        self.resolver = PathResolver(self.config, self.platform_config)

        # Create test files
        self.test_file = os.path.join(self.temp_dir, 'test.txt')
        with open(self.test_file, 'w') as f:
            f.write('test content')

        self.test_dir = os.path.join(self.temp_dir, 'test_dir')
        os.makedirs(self.test_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_validate_path_file_exists(self):
        """Test validating an existing file."""
        result = self.resolver.validate_path(self.test_file)

        self.assertTrue(result['valid'])
        self.assertTrue(result['exists'])
        self.assertTrue(result['readable'])
        self.assertTrue(result['is_file'])
        self.assertFalse(result['is_dir'])
        self.assertIsNone(result['error'])

    def test_validate_path_dir_exists(self):
        """Test validating an existing directory."""
        result = self.resolver.validate_path(self.test_dir)

        self.assertTrue(result['valid'])
        self.assertTrue(result['exists'])
        self.assertTrue(result['readable'])
        self.assertFalse(result['is_file'])
        self.assertTrue(result['is_dir'])
        self.assertIsNone(result['error'])

    def test_validate_path_not_exists(self):
        """Test validating a non-existent path."""
        result = self.resolver.validate_path('/nonexistent/path/file.txt')

        self.assertFalse(result['valid'])
        self.assertFalse(result['exists'])
        self.assertFalse(result['readable'])
        self.assertFalse(result['is_file'])
        self.assertFalse(result['is_dir'])
        self.assertEqual(result['error'], "Path does not exist")

    def test_validate_path_skip_readable_check(self):
        """Test validating path without readable check."""
        result = self.resolver.validate_path(self.test_file, check_readable=False)

        self.assertTrue(result['valid'])
        self.assertTrue(result['exists'])
        self.assertTrue(result['readable'])  # Set to True when skipped

    def test_validate_paths_batch_all_valid(self):
        """Test batch validation with all valid paths."""
        paths = [self.test_file, self.test_dir, self.config_file]

        results = self.resolver.validate_paths_batch(paths)

        self.assertEqual(len(results), 3)
        for path, result in results.items():
            self.assertTrue(result['valid'])
            self.assertIsNone(result['error'])

    def test_validate_paths_batch_with_invalid(self):
        """Test batch validation with some invalid paths."""
        paths = [
            self.test_file,
            '/nonexistent/path1.txt',
            self.test_dir,
            '/nonexistent/path2.txt'
        ]

        results = self.resolver.validate_paths_batch(paths)

        self.assertEqual(len(results), 4)

        # Check valid paths
        self.assertTrue(results[self.test_file]['valid'])
        self.assertTrue(results[self.test_dir]['valid'])

        # Check invalid paths
        self.assertFalse(results['/nonexistent/path1.txt']['valid'])
        self.assertFalse(results['/nonexistent/path2.txt']['valid'])

    def test_validate_paths_batch_stop_on_error(self):
        """Test batch validation stops on first error."""
        paths = [
            self.test_file,
            '/nonexistent/path.txt',  # This should stop validation
            self.test_dir
        ]

        results = self.resolver.validate_paths_batch(paths, stop_on_error=True)

        # Should only have 2 results (stopped after error)
        self.assertEqual(len(results), 2)
        self.assertIn(self.test_file, results)
        self.assertIn('/nonexistent/path.txt', results)
        self.assertNotIn(self.test_dir, results)

    def test_validate_paths_batch_empty_list(self):
        """Test batch validation with empty list."""
        results = self.resolver.validate_paths_batch([])

        self.assertEqual(len(results), 0)


if __name__ == '__main__':
    unittest.main()

