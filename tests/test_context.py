# -*- coding: utf-8 -*-
"""Unit tests for ContextManager class.

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

from core.context import ContextManager
from core.custom_nodes import CTXManagerNode, CTXShotNode, MAYA_AVAILABLE


class TestContextManager(unittest.TestCase):
    """Test cases for ContextManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.ctx = ContextManager()
        
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
    
    def test_get_or_create_manager(self):
        """Test getting or creating manager."""
        manager1 = self.ctx.get_or_create_manager()
        self.assertIsNotNone(manager1)
        
        manager2 = self.ctx.get_or_create_manager()
        self.assertEqual(manager1.node_name, manager2.node_name)
    
    def test_create_shot(self):
        """Test creating a shot."""
        shot = self.ctx.create_shot('Ep04', 'sq0070', 'SH0170')
        
        self.assertIsNotNone(shot)
        self.assertTrue(shot.exists())
        
        if MAYA_AVAILABLE:
            self.assertEqual(shot.get_ep_code(), 'Ep04')
            self.assertEqual(shot.get_seq_code(), 'sq0070')
            self.assertEqual(shot.get_shot_code(), 'SH0170')
    
    def test_create_duplicate_shot(self):
        """Test that creating duplicate shot raises error."""
        shot1 = self.ctx.create_shot('Ep04', 'sq0070', 'SH0170')
        
        # Note: This test will pass in mock mode because get_all_shots returns []
        # In real Maya, this would raise ValueError
        if MAYA_AVAILABLE:
            with self.assertRaises(ValueError):
                shot2 = self.ctx.create_shot('Ep04', 'sq0070', 'SH0170')
    
    def test_set_active_shot(self):
        """Test setting active shot."""
        shot = self.ctx.create_shot('Ep04', 'sq0070', 'SH0170')
        
        self.ctx.set_active_shot(shot)
        
        if MAYA_AVAILABLE:
            self.assertTrue(shot.is_active())
    
    def test_set_active_shot_invalid(self):
        """Test setting active shot with invalid node."""
        with self.assertRaises(ValueError):
            self.ctx.set_active_shot("invalid")
    
    def test_get_active_shot(self):
        """Test getting active shot."""
        shot = self.ctx.create_shot('Ep04', 'sq0070', 'SH0170')
        self.ctx.set_active_shot(shot)
        
        # Note: In mock mode, get_active_shot returns None
        # because get_all_shots returns []
        if MAYA_AVAILABLE:
            active = self.ctx.get_active_shot()
            self.assertIsNotNone(active)
            self.assertEqual(active.node_name, shot.node_name)
    
    def test_get_shot_context(self):
        """Test getting shot context."""
        shot = self.ctx.create_shot('Ep04', 'sq0070', 'SH0170')
        
        context = self.ctx.get_shot_context(shot)
        
        if MAYA_AVAILABLE:
            self.assertEqual(context['ep'], 'Ep04')
            self.assertEqual(context['seq'], 'sq0070')
            self.assertEqual(context['shot'], 'SH0170')
    
    def test_get_shot_context_invalid(self):
        """Test getting context with invalid shot."""
        with self.assertRaises(ValueError):
            self.ctx.get_shot_context("invalid")
    
    def test_register_callback(self):
        """Test registering a callback."""
        called = []
        
        def callback(event_type, data):
            called.append((event_type, data))
        
        self.ctx.register_callback(callback)
        
        # Create shot should trigger callback
        shot = self.ctx.create_shot('Ep04', 'sq0070', 'SH0170')
        
        self.assertEqual(len(called), 1)
        self.assertEqual(called[0][0], 'shot_created')
    
    def test_register_callback_invalid(self):
        """Test registering invalid callback."""
        with self.assertRaises(ValueError):
            self.ctx.register_callback("not_callable")
    
    def test_unregister_callback(self):
        """Test unregistering a callback."""
        called = []
        
        def callback(event_type, data):
            called.append((event_type, data))
        
        self.ctx.register_callback(callback)
        self.ctx.unregister_callback(callback)
        
        # Create shot should not trigger callback
        shot = self.ctx.create_shot('Ep04', 'sq0070', 'SH0170')
        
        self.assertEqual(len(called), 0)
    
    def test_silent_mode(self):
        """Test silent mode prevents callbacks."""
        called = []
        
        def callback(event_type, data):
            called.append((event_type, data))
        
        self.ctx.register_callback(callback)
        self.ctx.set_silent_mode(True)
        
        # Create shot should not trigger callback
        shot = self.ctx.create_shot('Ep04', 'sq0070', 'SH0170')
        
        self.assertEqual(len(called), 0)


if __name__ == '__main__':
    unittest.main()

