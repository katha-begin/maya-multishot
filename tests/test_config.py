# -*- coding: utf-8 -*-
"""
Unit tests for config module.

Tests ProjectConfig, PlatformConfig, and TemplateManager classes.

Author: Context Variables Pipeline Team
Date: 2026-02-14
"""

from __future__ import absolute_import, division, print_function

import json
import os
import sys
import tempfile
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.project_config import ProjectConfig


class TestProjectConfig(unittest.TestCase):
    """Test cases for ProjectConfig class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_data = {
            'version': '1.0',
            'project': {
                'name': 'TestProject',
                'code': 'TST'
            },
            'roots': {
                'PROJ_ROOT': 'V:/'
            },
            'static_paths': {
                'scene_base': 'all/scene'
            },
            'templates': {
                'publish_path': '$PROJ_ROOT/$project/$scene_base/$ep/$seq/$shot/$dept/publish',
                'cache_path': '$PROJ_ROOT/$project/$scene_base/$ep/$seq/$shot/$dept/publish/$ver'
            },
            'patterns': {
                'full_format': '$ep_$seq_$shot__$assetType_$assetName_$variant.$ext',
                'namespace_format': '$assetType_$assetName_$variant'
            },
            'extensions': ['.abc', '.vdb']
        }
        
        # Create temporary config file
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        json.dump(self.test_config_data, self.temp_file)
        self.temp_file.close()
        self.temp_config_path = self.temp_file.name
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_config_path):
            os.unlink(self.temp_config_path)
    
    def test_init_without_path(self):
        """Test initialization without config path."""
        config = ProjectConfig()
        self.assertIsNone(config.config_path)
        self.assertEqual(config.data, {})
        self.assertIsNone(config.version)
    
    def test_init_with_path(self):
        """Test initialization with config path."""
        config = ProjectConfig(self.temp_config_path)
        self.assertEqual(config.config_path, self.temp_config_path)
        self.assertEqual(config.version, '1.0')
        self.assertIsNotNone(config.data)
    
    def test_load_valid_config(self):
        """Test loading valid configuration file."""
        config = ProjectConfig()
        config.load(self.temp_config_path)
        
        self.assertEqual(config.config_path, self.temp_config_path)
        self.assertEqual(config.version, '1.0')
        self.assertEqual(config.data['project']['name'], 'TestProject')
    
    def test_load_nonexistent_file(self):
        """Test loading non-existent file raises IOError."""
        config = ProjectConfig()
        with self.assertRaises(IOError) as context:
            config.load('/nonexistent/path/config.json')
        self.assertIn('not found', str(context.exception))
    
    def test_load_invalid_json(self):
        """Test loading invalid JSON raises ValueError."""
        # Create file with invalid JSON
        invalid_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        invalid_file.write('{invalid json content')
        invalid_file.close()
        
        config = ProjectConfig()
        try:
            with self.assertRaises(ValueError) as context:
                config.load(invalid_file.name)
            self.assertIn('Invalid JSON', str(context.exception))
        finally:
            os.unlink(invalid_file.name)
    
    def test_validate_missing_keys(self):
        """Test validation fails with missing required keys."""
        incomplete_data = {'version': '1.0', 'project': {}}
        incomplete_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        json.dump(incomplete_data, incomplete_file)
        incomplete_file.close()
        
        config = ProjectConfig()
        try:
            with self.assertRaises(ValueError) as context:
                config.load(incomplete_file.name)
            self.assertIn('Missing required keys', str(context.exception))
        finally:
            os.unlink(incomplete_file.name)
    
    def test_validate_unsupported_version(self):
        """Test validation fails with unsupported version."""
        bad_version_data = self.test_config_data.copy()
        bad_version_data['version'] = '99.9'
        bad_version_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        json.dump(bad_version_data, bad_version_file)
        bad_version_file.close()
        
        config = ProjectConfig()
        try:
            with self.assertRaises(ValueError) as context:
                config.load(bad_version_file.name)
            self.assertIn('Unsupported configuration version', str(context.exception))
        finally:
            os.unlink(bad_version_file.name)
    
    def test_get_project_name(self):
        """Test getting project name."""
        config = ProjectConfig(self.temp_config_path)
        self.assertEqual(config.get_project_name(), 'TestProject')
    
    def test_get_project_code(self):
        """Test getting project code."""
        config = ProjectConfig(self.temp_config_path)
        self.assertEqual(config.get_project_code(), 'TST')
    
    def test_get_roots(self):
        """Test getting all roots."""
        config = ProjectConfig(self.temp_config_path)
        roots = config.get_roots()
        self.assertIsInstance(roots, dict)
        self.assertEqual(roots['PROJ_ROOT'], 'V:/')

    def test_get_root(self):
        """Test getting specific root."""
        config = ProjectConfig(self.temp_config_path)
        self.assertEqual(config.get_root('PROJ_ROOT'), 'V:/')
        self.assertIsNone(config.get_root('nonexistent'))

    def test_get_static_paths(self):
        """Test getting all static paths."""
        config = ProjectConfig(self.temp_config_path)
        static_paths = config.get_static_paths()
        self.assertIsInstance(static_paths, dict)
        self.assertEqual(static_paths['scene_base'], 'all/scene')

    def test_get_static_path(self):
        """Test getting specific static path."""
        config = ProjectConfig(self.temp_config_path)
        self.assertEqual(config.get_static_path('scene_base'), 'all/scene')
        self.assertIsNone(config.get_static_path('nonexistent'))

    def test_get_templates(self):
        """Test getting all templates."""
        config = ProjectConfig(self.temp_config_path)
        templates = config.get_templates()
        self.assertIsInstance(templates, dict)
        self.assertIn('publish_path', templates)
        self.assertIn('cache_path', templates)

    def test_get_template(self):
        """Test getting specific template."""
        config = ProjectConfig(self.temp_config_path)
        self.assertEqual(
            config.get_template('publish_path'),
            '$PROJ_ROOT/$project/$scene_base/$ep/$seq/$shot/$dept/publish'
        )
        self.assertIsNone(config.get_template('nonexistent'))

    def test_get_patterns(self):
        """Test getting all patterns."""
        config = ProjectConfig(self.temp_config_path)
        patterns = config.get_patterns()
        self.assertIsInstance(patterns, dict)
        self.assertIn('full_format', patterns)

    def test_get_pattern(self):
        """Test getting specific pattern."""
        config = ProjectConfig(self.temp_config_path)
        pattern = config.get_pattern('full_format')
        self.assertEqual(
            pattern,
            '$ep_$seq_$shot__$assetType_$assetName_$variant.$ext'
        )
        self.assertIsNone(config.get_pattern('nonexistent'))

    def test_get_supported_extensions(self):
        """Test getting supported extensions."""
        config = ProjectConfig(self.temp_config_path)
        extensions = config.get_supported_extensions()
        self.assertIsInstance(extensions, list)
        self.assertIn('.abc', extensions)
        self.assertIn('.vdb', extensions)

    def test_find_config_with_paths(self):
        """Test finding config with custom search paths."""
        search_paths = ['/nonexistent/path.json', self.temp_config_path]
        found_path = ProjectConfig.find_config(search_paths)
        self.assertEqual(found_path, self.temp_config_path)

    def test_find_config_not_found(self):
        """Test finding config returns None when not found."""
        search_paths = ['/nonexistent/path1.json', '/nonexistent/path2.json']
        found_path = ProjectConfig.find_config(search_paths)
        self.assertIsNone(found_path)

    def test_repr(self):
        """Test string representation."""
        config = ProjectConfig(self.temp_config_path)
        repr_str = repr(config)
        self.assertIn('ProjectConfig', repr_str)
        self.assertIn(self.temp_config_path, repr_str)
        self.assertIn('1.0', repr_str)


if __name__ == '__main__':
    unittest.main()

