# -*- coding: utf-8 -*-
"""Unit tests for TemplateManager class.

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
from config.template_manager import TemplateManager


class TestTemplateManager(unittest.TestCase):
    """Test cases for TemplateManager class."""
    
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
                'publishPath': '$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish',
                'cachePath': '$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish/$ver',
                'fullFilename': '$ep_$seq_$shot__$assetType_$assetName_$variant.$ext',
                'namespace': '$assetType_$assetName_$variant',
                'simple': '$ep/$seq'
            },
            'patterns': {
                'fullFormat': '$ep_$seq_$shot__$assetType_$assetName_$variant.$ext'
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
        """Test TemplateManager initialization."""
        config = ProjectConfig(self.temp_config_path)
        template_mgr = TemplateManager(config)
        
        self.assertIsNotNone(template_mgr)
        self.assertIsNotNone(template_mgr.templates)
        self.assertEqual(len(template_mgr.templates), 5)
    
    def test_load_templates(self):
        """Test loading templates from config."""
        config = ProjectConfig(self.temp_config_path)
        template_mgr = TemplateManager(config)
        
        templates = template_mgr.get_all_templates()
        self.assertIn('publishPath', templates)
        self.assertIn('cachePath', templates)
        self.assertIn('fullFilename', templates)
    
    def test_get_template(self):
        """Test getting specific template."""
        config = ProjectConfig(self.temp_config_path)
        template_mgr = TemplateManager(config)

        template = template_mgr.get_template('publishPath')
        self.assertEqual(
            template,
            '$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish'
        )
    
    def test_get_template_nonexistent(self):
        """Test getting nonexistent template returns None."""
        config = ProjectConfig(self.temp_config_path)
        template_mgr = TemplateManager(config)
        
        template = template_mgr.get_template('nonexistent')
        self.assertIsNone(template)
    
    def test_has_template(self):
        """Test checking if template exists."""
        config = ProjectConfig(self.temp_config_path)
        template_mgr = TemplateManager(config)

        self.assertTrue(template_mgr.has_template('publishPath'))
        self.assertFalse(template_mgr.has_template('nonexistent'))

    def test_get_template_tokens(self):
        """Test extracting tokens from template."""
        config = ProjectConfig(self.temp_config_path)
        template_mgr = TemplateManager(config)

        tokens = template_mgr.get_template_tokens('publishPath')
        expected = ['projRoot', 'project', 'sceneBase', 'ep', 'seq', 'shot', 'dept']
        self.assertEqual(tokens, expected)
    
    def test_get_template_tokens_nonexistent(self):
        """Test getting tokens from nonexistent template."""
        config = ProjectConfig(self.temp_config_path)
        template_mgr = TemplateManager(config)
        
        tokens = template_mgr.get_template_tokens('nonexistent')
        self.assertIsNone(tokens)
    
    def test_extract_tokens_classmethod(self):
        """Test extracting tokens from template string."""
        tokens = TemplateManager.extract_tokens('$PROJ_ROOT/$project/$ep/$seq')
        self.assertEqual(tokens, ['PROJ_ROOT', 'project', 'ep', 'seq'])
    
    def test_extract_tokens_unique(self):
        """Test that duplicate tokens are returned only once."""
        tokens = TemplateManager.extract_tokens('$ep/$seq/$ep/$shot')
        self.assertEqual(tokens, ['ep', 'seq', 'shot'])
    
    def test_extract_tokens_empty(self):
        """Test extracting tokens from template with no tokens."""
        tokens = TemplateManager.extract_tokens('no/tokens/here')
        self.assertEqual(tokens, [])

    def test_validate_template_tokens_valid(self):
        """Test validating template with all required tokens."""
        config = ProjectConfig(self.temp_config_path)
        template_mgr = TemplateManager(config)

        is_valid, missing = template_mgr.validate_template_tokens(
            'publishPath', ['ep', 'seq', 'shot']
        )
        self.assertTrue(is_valid)
        self.assertEqual(missing, [])

    def test_validate_template_tokens_missing(self):
        """Test validating template with missing tokens."""
        config = ProjectConfig(self.temp_config_path)
        template_mgr = TemplateManager(config)

        is_valid, missing = template_mgr.validate_template_tokens(
            'simple', ['ep', 'seq', 'shot']
        )
        self.assertFalse(is_valid)
        self.assertEqual(missing, ['shot'])

    def test_validate_template_tokens_no_requirements(self):
        """Test validating template with no requirements."""
        config = ProjectConfig(self.temp_config_path)
        template_mgr = TemplateManager(config)

        is_valid, missing = template_mgr.validate_template_tokens('publishPath')
        self.assertTrue(is_valid)
        self.assertEqual(missing, [])

    def test_get_template_names(self):
        """Test getting all template names."""
        config = ProjectConfig(self.temp_config_path)
        template_mgr = TemplateManager(config)

        names = template_mgr.get_template_names()
        self.assertIn('publishPath', names)
        self.assertIn('cachePath', names)
        self.assertEqual(len(names), 5)

    def test_repr(self):
        """Test string representation."""
        config = ProjectConfig(self.temp_config_path)
        template_mgr = TemplateManager(config)

        repr_str = repr(template_mgr)
        self.assertIn('TemplateManager', repr_str)
        self.assertIn('5', repr_str)

    def test_validate_empty_template(self):
        """Test validation fails for empty template."""
        # Create config with empty template
        test_config = {
            'version': '1.0',
            'project': {'name': 'Test', 'code': 'TST'},
            'roots': {'projRoot': 'V:/'},
            'staticPaths': {'sceneBase': 'all/scene'},
            'templates': {'empty': '   '},
            'patterns': {}
        }

        temp_path = os.path.join(self.temp_dir, 'empty_template.json')
        with open(temp_path, 'w') as f:
            json.dump(test_config, f)

        config = ProjectConfig(temp_path)
        with self.assertRaises(ValueError) as ctx:
            TemplateManager(config)

        self.assertIn('empty', str(ctx.exception))

    def test_validate_non_string_template(self):
        """Test validation fails for non-string template."""
        # Create config with non-string template
        test_config = {
            'version': '1.0',
            'project': {'name': 'Test', 'code': 'TST'},
            'roots': {'projRoot': 'V:/'},
            'staticPaths': {'sceneBase': 'all/scene'},
            'templates': {'invalid': 123},
            'patterns': {}
        }

        temp_path = os.path.join(self.temp_dir, 'invalid_template.json')
        with open(temp_path, 'w') as f:
            json.dump(test_config, f)

        config = ProjectConfig(temp_path)
        with self.assertRaises(ValueError) as ctx:
            TemplateManager(config)

        self.assertIn('must be a string', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()

