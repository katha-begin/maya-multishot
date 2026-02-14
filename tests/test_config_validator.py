# -*- coding: utf-8 -*-
"""Unit tests for ConfigValidator class.

Author: Context Variables Pipeline
Date: 2026-02-14
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config_validator import ConfigValidator, ConfigValidationError


class TestConfigValidator(unittest.TestCase):
    """Test cases for ConfigValidator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = ConfigValidator()
        
        # Valid config for testing
        self.valid_config = {
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
                'publish_path': '$PROJ_ROOT/$project/$scene_base/$ep/$seq/$shot/$dept/publish'
            },
            'patterns': {
                'full_filename': r'^(Ep\d+)_(sq\d+)_(SH\d+)__([A-Z]+)_(.+)_(\d+)\.(abc|ma|mb)$'
            }
        }
    
    def test_validate_valid_config(self):
        """Test validating a valid configuration."""
        is_valid, errors = self.validator.validate(self.valid_config)
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_missing_required_key(self):
        """Test validation fails for missing required key."""
        config = self.valid_config.copy()
        del config['version']
        
        is_valid, errors = self.validator.validate(config)
        
        self.assertFalse(is_valid)
        self.assertTrue(any('version' in err for err in errors))
    
    def test_validate_invalid_version(self):
        """Test validation fails for invalid version."""
        config = self.valid_config.copy()
        config['version'] = '99.9'
        
        is_valid, errors = self.validator.validate(config)
        
        self.assertFalse(is_valid)
        self.assertTrue(any('Unsupported version' in err for err in errors))
    
    def test_validate_version_not_string(self):
        """Test validation fails for non-string version."""
        config = self.valid_config.copy()
        config['version'] = 1.0
        
        is_valid, errors = self.validator.validate(config)
        
        self.assertFalse(is_valid)
        self.assertTrue(any('must be a string' in err for err in errors))
    
    def test_validate_missing_project_field(self):
        """Test validation fails for missing project field."""
        config = self.valid_config.copy()
        config['project'] = {'name': 'Test'}  # Missing 'code'
        
        is_valid, errors = self.validator.validate(config)
        
        self.assertFalse(is_valid)
        self.assertTrue(any('code' in err for err in errors))
    
    def test_validate_project_not_dict(self):
        """Test validation fails for non-dict project."""
        config = self.valid_config.copy()
        config['project'] = 'invalid'
        
        is_valid, errors = self.validator.validate(config)
        
        self.assertFalse(is_valid)
        self.assertTrue(any('must be a dictionary' in err for err in errors))
    
    def test_validate_project_name_not_string(self):
        """Test validation fails for non-string project name."""
        config = self.valid_config.copy()
        config['project']['name'] = 123
        
        is_valid, errors = self.validator.validate(config)
        
        self.assertFalse(is_valid)
        self.assertTrue(any('name must be a string' in err for err in errors))
    
    def test_validate_roots_not_dict(self):
        """Test validation fails for non-dict roots."""
        config = self.valid_config.copy()
        config['roots'] = 'invalid'
        
        is_valid, errors = self.validator.validate(config)
        
        self.assertFalse(is_valid)
        self.assertTrue(any('must be a dictionary' in err for err in errors))
    
    def test_validate_empty_roots(self):
        """Test validation fails for empty roots."""
        config = self.valid_config.copy()
        config['roots'] = {}
        
        is_valid, errors = self.validator.validate(config)
        
        self.assertFalse(is_valid)
        self.assertTrue(any('empty' in err for err in errors))
    
    def test_validate_root_not_string(self):
        """Test validation fails for non-string root."""
        config = self.valid_config.copy()
        config['roots']['PROJ_ROOT'] = 123
        
        is_valid, errors = self.validator.validate(config)
        
        self.assertFalse(is_valid)
        self.assertTrue(any('must be a string' in err for err in errors))
    
    def test_validate_static_paths_not_dict(self):
        """Test validation fails for non-dict static_paths."""
        config = self.valid_config.copy()
        config['static_paths'] = 'invalid'

        is_valid, errors = self.validator.validate(config)

        self.assertFalse(is_valid)
        self.assertTrue(any('must be a dictionary' in err for err in errors))

    def test_validate_static_path_not_string(self):
        """Test validation fails for non-string static path."""
        config = self.valid_config.copy()
        config['static_paths']['scene_base'] = 123

        is_valid, errors = self.validator.validate(config)

        self.assertFalse(is_valid)
        self.assertTrue(any('must be a string' in err for err in errors))

    def test_validate_templates_not_dict(self):
        """Test validation fails for non-dict templates."""
        config = self.valid_config.copy()
        config['templates'] = 'invalid'

        is_valid, errors = self.validator.validate(config)

        self.assertFalse(is_valid)
        self.assertTrue(any('must be a dictionary' in err for err in errors))

    def test_validate_template_not_string(self):
        """Test validation fails for non-string template."""
        config = self.valid_config.copy()
        config['templates']['publish_path'] = 123

        is_valid, errors = self.validator.validate(config)

        self.assertFalse(is_valid)
        self.assertTrue(any('must be a string' in err for err in errors))

    def test_validate_empty_template(self):
        """Test validation fails for empty template."""
        config = self.valid_config.copy()
        config['templates']['empty'] = '   '

        is_valid, errors = self.validator.validate(config)

        self.assertFalse(is_valid)
        self.assertTrue(any('empty' in err for err in errors))

    def test_validate_patterns_not_dict(self):
        """Test validation fails for non-dict patterns."""
        config = self.valid_config.copy()
        config['patterns'] = 'invalid'

        is_valid, errors = self.validator.validate(config)

        self.assertFalse(is_valid)
        self.assertTrue(any('must be a dictionary' in err for err in errors))

    def test_validate_pattern_not_string(self):
        """Test validation fails for non-string pattern."""
        config = self.valid_config.copy()
        config['patterns']['full_filename'] = 123

        is_valid, errors = self.validator.validate(config)

        self.assertFalse(is_valid)
        self.assertTrue(any('must be a string' in err for err in errors))

    def test_validate_empty_pattern(self):
        """Test validation fails for empty pattern."""
        config = self.valid_config.copy()
        config['patterns']['empty'] = '   '

        is_valid, errors = self.validator.validate(config)

        self.assertFalse(is_valid)
        self.assertTrue(any('empty' in err for err in errors))

    def test_validate_invalid_regex_pattern(self):
        """Test validation fails for invalid regex pattern."""
        config = self.valid_config.copy()
        config['patterns']['invalid'] = '[unclosed'

        is_valid, errors = self.validator.validate(config)

        self.assertFalse(is_valid)
        self.assertTrue(any('invalid regex syntax' in err for err in errors))

    def test_get_warnings(self):
        """Test getting validation warnings."""
        is_valid, errors = self.validator.validate(self.valid_config)
        warnings = self.validator.get_warnings()

        self.assertIsInstance(warnings, list)

    def test_migrate_config_same_version(self):
        """Test migrating config to same version."""
        migrated = self.validator.migrate_config(self.valid_config, '1.0')

        self.assertEqual(migrated['version'], '1.0')

    def test_migrate_config_different_version(self):
        """Test migrating config to different version."""
        migrated = self.validator.migrate_config(self.valid_config, '1.1')

        self.assertEqual(migrated['version'], '1.1')

    def test_migrate_config_unsupported_version(self):
        """Test migration fails for unsupported version."""
        with self.assertRaises(ConfigValidationError):
            self.validator.migrate_config(self.valid_config, '99.9')

    def test_multiple_errors(self):
        """Test that multiple errors are collected."""
        config = {
            'version': 99,  # Invalid type
            'project': 'invalid',  # Invalid type
            'roots': {},  # Empty
            'static_paths': 'invalid',  # Invalid type
            'templates': 'invalid',  # Invalid type
            'patterns': 'invalid'  # Invalid type
        }

        is_valid, errors = self.validator.validate(config)

        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 1)


if __name__ == '__main__':
    unittest.main()

