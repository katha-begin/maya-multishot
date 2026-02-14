# -*- coding: utf-8 -*-
"""Unit tests for TokenExpander class.

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

from core.tokens import TokenExpander


class TestTokenExpander(unittest.TestCase):
    """Test cases for TokenExpander class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.expander = TokenExpander()
        self.context = {
            'projRoot': 'V:/',
            'project': 'SWA',
            'sceneBase': 'all/scene',
            'ep': 'Ep04',
            'seq': 'sq0070',
            'shot': 'SH0170',
            'dept': 'anim',
            'ver': 'v003',
            'assetType': 'CHAR',
            'assetName': 'CatStompie',
            'variant': '001',
            'ext': 'abc'
        }
    
    def test_expand_tokens_simple(self):
        """Test expanding simple tokens."""
        template = '$ep/$seq/$shot'
        result = self.expander.expand_tokens(template, self.context)
        
        self.assertEqual(result, 'Ep04/sq0070/SH0170')
    
    def test_expand_tokens_complex(self):
        """Test expanding complex template."""
        template = '$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish'
        result = self.expander.expand_tokens(template, self.context)

        self.assertEqual(result, 'V:/SWA/all/scene/Ep04/sq0070/SH0170/anim/publish')
    
    def test_expand_tokens_filename(self):
        """Test expanding filename template."""
        template = '$ep_$seq_$shot__$assetType_$assetName_$variant.$ext'
        result = self.expander.expand_tokens(template, self.context)
        
        self.assertEqual(result, 'Ep04_sq0070_SH0170__CHAR_CatStompie_001.abc')
    
    def test_expand_tokens_missing_value(self):
        """Test expanding with missing context value."""
        template = '$ep/$missing/$shot'
        result = self.expander.expand_tokens(template, self.context)
        
        # Missing token should remain unexpanded
        self.assertEqual(result, 'Ep04/$missing/SH0170')
    
    def test_expand_tokens_version_override(self):
        """Test version override."""
        template = '$ep/$seq/$shot/$ver'
        result = self.expander.expand_tokens(template, self.context, version_override='v005')
        
        self.assertEqual(result, 'Ep04/sq0070/SH0170/v005')
    
    def test_expand_tokens_empty_template(self):
        """Test expanding empty template."""
        result = self.expander.expand_tokens('', self.context)
        
        self.assertEqual(result, '')
    
    def test_validate_template_valid(self):
        """Test validating valid template."""
        template = '$ep/$seq/$shot'
        is_valid, error = self.expander.validate_template(template)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_validate_template_empty(self):
        """Test validating empty template."""
        is_valid, error = self.expander.validate_template('')
        
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
    
    def test_validate_template_required_tokens(self):
        """Test validating with required tokens."""
        template = '$ep/$seq'
        is_valid, error = self.expander.validate_template(template, required_tokens=['ep', 'seq', 'shot'])
        
        self.assertFalse(is_valid)
        self.assertIn('shot', error)
    
    def test_extract_tokens(self):
        """Test extracting tokens from template."""
        template = '$ep/$seq/$shot/$dept'
        tokens = self.expander.extract_tokens(template)
        
        self.assertEqual(tokens, ['ep', 'seq', 'shot', 'dept'])
    
    def test_extract_tokens_duplicates(self):
        """Test extracting tokens with duplicates."""
        template = '$ep/$seq/$ep/$shot'
        tokens = self.expander.extract_tokens(template)
        
        # Should return unique tokens in order of first appearance
        self.assertEqual(tokens, ['ep', 'seq', 'shot'])
    
    def test_extract_tokens_empty(self):
        """Test extracting tokens from empty template."""
        tokens = self.expander.extract_tokens('')
        
        self.assertEqual(tokens, [])
    
    def test_get_token_values(self):
        """Test getting token values."""
        template = '$ep/$seq/$shot'
        values = self.expander.get_token_values(template, self.context)
        
        self.assertEqual(values['ep'], 'Ep04')
        self.assertEqual(values['seq'], 'sq0070')
        self.assertEqual(values['shot'], 'SH0170')
    
    def test_get_token_values_missing(self):
        """Test getting token values with missing context."""
        template = '$ep/$missing'
        values = self.expander.get_token_values(template, self.context)
        
        self.assertEqual(values['ep'], 'Ep04')
        self.assertIsNone(values['missing'])


if __name__ == '__main__':
    unittest.main()

