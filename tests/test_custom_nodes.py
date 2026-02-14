# -*- coding: utf-8 -*-
"""Unit tests for custom nodes.

These tests can run both inside and outside Maya.
When running outside Maya, mock objects are used.

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

from core.custom_nodes import (
    CTXManagerNode,
    CTXShotNode,
    CTXAssetNode,
    MAYA_AVAILABLE
)


class TestCTXManagerNode(unittest.TestCase):
    """Test cases for CTXManagerNode class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Clean up any existing manager
        existing = CTXManagerNode.get_manager()
        if existing:
            existing.delete()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up manager
        existing = CTXManagerNode.get_manager()
        if existing:
            existing.delete()
    
    def test_create_manager(self):
        """Test creating a manager node."""
        manager = CTXManagerNode.create_manager('/path/to/config.json')
        
        self.assertIsNotNone(manager)
        self.assertTrue(manager.exists())
    
    def test_create_manager_singleton(self):
        """Test that only one manager can exist."""
        manager1 = CTXManagerNode.create_manager()
        
        with self.assertRaises(RuntimeError):
            manager2 = CTXManagerNode.create_manager()
    
    def test_get_manager(self):
        """Test getting existing manager."""
        manager1 = CTXManagerNode.create_manager()
        manager2 = CTXManagerNode.get_manager()
        
        self.assertIsNotNone(manager2)
        self.assertEqual(manager1.node_name, manager2.node_name)
    
    def test_get_manager_none(self):
        """Test getting manager when none exists."""
        manager = CTXManagerNode.get_manager()
        self.assertIsNone(manager)
    
    def test_set_get_config_path(self):
        """Test setting and getting config path."""
        manager = CTXManagerNode.create_manager()
        
        manager.set_config_path('/new/path/config.json')
        path = manager.get_config_path()
        
        if MAYA_AVAILABLE:
            self.assertEqual(path, '/new/path/config.json')
    
    def test_set_get_project_root(self):
        """Test setting and getting project root."""
        manager = CTXManagerNode.create_manager()
        
        manager.set_project_root('V:/SWA')
        root = manager.get_project_root()
        
        if MAYA_AVAILABLE:
            self.assertEqual(root, 'V:/SWA')
    
    def test_set_get_active_shot_id(self):
        """Test setting and getting active shot ID."""
        manager = CTXManagerNode.create_manager()
        
        manager.set_active_shot_id('Ep04_sq0070_SH0170')
        shot_id = manager.get_active_shot_id()
        
        if MAYA_AVAILABLE:
            self.assertEqual(shot_id, 'Ep04_sq0070_SH0170')
    
    def test_delete_manager(self):
        """Test deleting manager."""
        manager = CTXManagerNode.create_manager()
        self.assertTrue(manager.exists())
        
        manager.delete()
        self.assertFalse(manager.exists())
    
    def test_repr(self):
        """Test string representation."""
        manager = CTXManagerNode.create_manager()
        repr_str = repr(manager)
        
        self.assertIn('CTXManagerNode', repr_str)


class TestCTXShotNode(unittest.TestCase):
    """Test cases for CTXShotNode class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create manager for testing
        existing = CTXManagerNode.get_manager()
        if existing:
            existing.delete()
        self.manager = CTXManagerNode.create_manager()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up manager
        if self.manager:
            self.manager.delete()
    
    def test_create_shot(self):
        """Test creating a shot node."""
        shot = CTXShotNode.create_shot('Ep04', 'sq0070', 'SH0170')
        
        self.assertIsNotNone(shot)
        self.assertTrue(shot.exists())
    
    def test_get_shot_codes(self):
        """Test getting shot codes."""
        shot = CTXShotNode.create_shot('Ep04', 'sq0070', 'SH0170')
        
        if MAYA_AVAILABLE:
            self.assertEqual(shot.get_ep_code(), 'Ep04')
            self.assertEqual(shot.get_seq_code(), 'sq0070')
            self.assertEqual(shot.get_shot_code(), 'SH0170')
    
    def test_get_shot_id(self):
        """Test getting full shot ID."""
        shot = CTXShotNode.create_shot('Ep04', 'sq0070', 'SH0170')

        if MAYA_AVAILABLE:
            self.assertEqual(shot.get_shot_id(), 'Ep04_sq0070_SH0170')

    def test_get_display_layer_name(self):
        """Test getting display layer name."""
        shot = CTXShotNode.create_shot('Ep04', 'sq0070', 'SH0170')

        if MAYA_AVAILABLE:
            self.assertEqual(shot.get_display_layer_name(), 'CTX_Ep04_sq0070_SH0170')

    def test_set_get_active(self):
        """Test setting and getting active state."""
        shot = CTXShotNode.create_shot('Ep04', 'sq0070', 'SH0170')

        if MAYA_AVAILABLE:
            self.assertFalse(shot.is_active())

            shot.set_active(True)
            self.assertTrue(shot.is_active())

    def test_delete_shot(self):
        """Test deleting shot."""
        shot = CTXShotNode.create_shot('Ep04', 'sq0070', 'SH0170')
        self.assertTrue(shot.exists())

        shot.delete()
        self.assertFalse(shot.exists())

    def test_repr(self):
        """Test string representation."""
        shot = CTXShotNode.create_shot('Ep04', 'sq0070', 'SH0170')
        repr_str = repr(shot)

        self.assertIn('CTXShotNode', repr_str)


class TestCTXAssetNode(unittest.TestCase):
    """Test cases for CTXAssetNode class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create manager and shot for testing
        existing = CTXManagerNode.get_manager()
        if existing:
            existing.delete()
        self.manager = CTXManagerNode.create_manager()
        self.shot = CTXShotNode.create_shot('Ep04', 'sq0070', 'SH0170', self.manager)

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up manager (will cascade delete shot)
        if self.manager:
            self.manager.delete()

    def test_create_asset(self):
        """Test creating an asset node."""
        asset = CTXAssetNode.create_asset('CHAR', 'CatStompie', '001')

        self.assertIsNotNone(asset)
        self.assertTrue(asset.exists())

    def test_get_asset_info(self):
        """Test getting asset information."""
        asset = CTXAssetNode.create_asset('CHAR', 'CatStompie', '001')

        if MAYA_AVAILABLE:
            self.assertEqual(asset.get_asset_type(), 'CHAR')
            self.assertEqual(asset.get_asset_name(), 'CatStompie')
            self.assertEqual(asset.get_variant(), '001')

    def test_get_namespace(self):
        """Test getting namespace."""
        asset = CTXAssetNode.create_asset('CHAR', 'CatStompie', '001')

        if MAYA_AVAILABLE:
            self.assertEqual(asset.get_namespace(), 'CHAR_CatStompie_001')

    def test_set_get_namespace(self):
        """Test setting and getting namespace."""
        asset = CTXAssetNode.create_asset('CHAR', 'CatStompie', '001')

        asset.set_namespace('custom_namespace')

        if MAYA_AVAILABLE:
            self.assertEqual(asset.get_namespace(), 'custom_namespace')

    def test_set_get_file_path(self):
        """Test setting and getting file path."""
        asset = CTXAssetNode.create_asset('CHAR', 'CatStompie', '001')

        asset.set_file_path('/path/to/asset.abc')

        if MAYA_AVAILABLE:
            self.assertEqual(asset.get_file_path(), '/path/to/asset.abc')

    def test_set_get_version(self):
        """Test setting and getting version."""
        asset = CTXAssetNode.create_asset('CHAR', 'CatStompie', '001')

        asset.set_version('v003')

        if MAYA_AVAILABLE:
            self.assertEqual(asset.get_version(), 'v003')

    def test_delete_asset(self):
        """Test deleting asset."""
        asset = CTXAssetNode.create_asset('CHAR', 'CatStompie', '001')
        self.assertTrue(asset.exists())

        asset.delete()
        self.assertFalse(asset.exists())

    def test_repr(self):
        """Test string representation."""
        asset = CTXAssetNode.create_asset('CHAR', 'CatStompie', '001')
        repr_str = repr(asset)

        self.assertIn('CTXAssetNode', repr_str)


if __name__ == '__main__':
    unittest.main()

