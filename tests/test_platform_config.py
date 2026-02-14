# -*- coding: utf-8 -*-
"""Unit tests for PlatformConfig class.

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
from config.platform_config import PlatformConfig


class TestPlatformConfig(unittest.TestCase):
    """Test cases for PlatformConfig class."""
    
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
                'PROJ_ROOT': 'V:/'
            },
            'static_paths': {
                'scene_base': 'all/scene'
            },
            'templates': {
                'publish_path': '$PROJ_ROOT/$project/$scene_base/$ep/$seq/$shot/$dept/publish'
            },
            'patterns': {
                'full_format': '$ep_$seq_$shot__$assetType_$assetName_$variant.$ext'
            },
            'platform_mapping': {
                'windows': {
                    'PROJ_ROOT': 'V:/'
                },
                'linux': {
                    'PROJ_ROOT': '/mnt/igloo_swa_v/'
                }
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
        """Test PlatformConfig initialization."""
        config = ProjectConfig(self.temp_config_path)
        platform_config = PlatformConfig(config)
        
        self.assertIsNotNone(platform_config)
        self.assertIsNotNone(platform_config.current_platform)
        self.assertIn(platform_config.current_platform, ['windows', 'linux'])
    
    def test_detect_platform(self):
        """Test platform detection."""
        config = ProjectConfig(self.temp_config_path)
        platform_config = PlatformConfig(config)
        
        platform = platform_config.get_platform()
        self.assertIn(platform, ['windows', 'linux'])
    
    def test_get_root_for_platform_windows(self):
        """Test getting root for Windows platform."""
        config = ProjectConfig(self.temp_config_path)
        platform_config = PlatformConfig(config)
        
        root = platform_config.get_root_for_platform('PROJ_ROOT', 'windows')
        self.assertEqual(root, 'V:/')
    
    def test_get_root_for_platform_linux(self):
        """Test getting root for Linux platform."""
        config = ProjectConfig(self.temp_config_path)
        platform_config = PlatformConfig(config)
        
        root = platform_config.get_root_for_platform('PROJ_ROOT', 'linux')
        self.assertEqual(root, '/mnt/igloo_swa_v/')
    
    def test_get_root_for_platform_default(self):
        """Test getting root for current platform (default)."""
        config = ProjectConfig(self.temp_config_path)
        platform_config = PlatformConfig(config)
        
        root = platform_config.get_root_for_platform('PROJ_ROOT')
        self.assertIsNotNone(root)
    
    def test_get_root_for_platform_nonexistent(self):
        """Test getting nonexistent root."""
        config = ProjectConfig(self.temp_config_path)
        platform_config = PlatformConfig(config)
        
        root = platform_config.get_root_for_platform('NONEXISTENT', 'windows')
        self.assertIsNone(root)
    
    def test_map_path_windows_to_linux(self):
        """Test mapping path from Windows to Linux."""
        config = ProjectConfig(self.temp_config_path)
        platform_config = PlatformConfig(config)
        
        windows_path = 'V:/TST/all/scene/Ep04/sq0070/SH0170'
        linux_path = platform_config.map_path(windows_path, 'linux')
        
        self.assertEqual(linux_path, '/mnt/igloo_swa_v/TST/all/scene/Ep04/sq0070/SH0170')
    
    def test_map_path_linux_to_windows(self):
        """Test mapping path from Linux to Windows."""
        config = ProjectConfig(self.temp_config_path)
        platform_config = PlatformConfig(config)
        
        linux_path = '/mnt/igloo_swa_v/TST/all/scene/Ep04/sq0070/SH0170'
        windows_path = platform_config.map_path(linux_path, 'windows')
        
        self.assertEqual(windows_path, 'V:/TST/all/scene/Ep04/sq0070/SH0170')
    
    def test_map_path_same_platform(self):
        """Test mapping path to same platform returns unchanged."""
        config = ProjectConfig(self.temp_config_path)
        platform_config = PlatformConfig(config)

        current_platform = platform_config.get_platform()
        test_path = 'V:/TST/all/scene'

        mapped_path = platform_config.map_path(test_path, current_platform)
        self.assertEqual(mapped_path, test_path)

    def test_map_path_with_backslashes(self):
        """Test mapping path with backslashes."""
        config = ProjectConfig(self.temp_config_path)
        platform_config = PlatformConfig(config)

        windows_path = 'V:\\TST\\all\\scene\\Ep04'
        linux_path = platform_config.map_path(windows_path, 'linux')

        self.assertEqual(linux_path, '/mnt/igloo_swa_v/TST/all/scene/Ep04')

    def test_map_path_no_matching_root(self):
        """Test mapping path with no matching root returns original."""
        config = ProjectConfig(self.temp_config_path)
        platform_config = PlatformConfig(config)

        unmapped_path = 'C:/SomeOtherPath/file.txt'
        result = platform_config.map_path(unmapped_path, 'linux')

        # Should return original path if no root matches
        self.assertEqual(result, unmapped_path)

    def test_map_path_default_target(self):
        """Test mapping path with default target platform."""
        config = ProjectConfig(self.temp_config_path)
        platform_config = PlatformConfig(config)

        test_path = 'V:/TST/all/scene'
        mapped_path = platform_config.map_path(test_path)

        # Should return same path when target is current platform
        self.assertEqual(mapped_path, test_path)

    def test_normalize_path(self):
        """Test path normalization."""
        config = ProjectConfig(self.temp_config_path)
        platform_config = PlatformConfig(config)

        path_with_backslashes = 'V:\\TST\\all\\scene'
        normalized = platform_config._normalize_path(path_with_backslashes)

        self.assertEqual(normalized, 'V:/TST/all/scene')

    def test_platform_mapping_loaded(self):
        """Test that platform mapping is loaded correctly."""
        config = ProjectConfig(self.temp_config_path)
        platform_config = PlatformConfig(config)

        self.assertIsNotNone(platform_config.platform_mapping)
        self.assertIn('windows', platform_config.platform_mapping)
        self.assertIn('linux', platform_config.platform_mapping)

    def test_string_representation(self):
        """Test string representation of PlatformConfig."""
        config = ProjectConfig(self.temp_config_path)
        platform_config = PlatformConfig(config)

        # Should not raise an error
        str_repr = str(platform_config)
        self.assertIsInstance(str_repr, str)


if __name__ == '__main__':
    unittest.main()

