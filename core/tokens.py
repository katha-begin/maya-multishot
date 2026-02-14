# -*- coding: utf-8 -*-
"""Token expansion engine for template paths.

This module handles token replacement in template strings with actual
values from context and asset data.

Author: Context Variables Pipeline
Date: 2026-02-14
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import re


class TokenExpander(object):
    """Token expansion engine for template paths.
    
    Replaces tokens like $ep, $seq, $shot with actual values from context.
    
    Example:
        >>> expander = TokenExpander()
        >>> context = {'ep': 'Ep04', 'seq': 'sq0070', 'shot': 'SH0170'}
        >>> template = '$ep/$seq/$shot'
        >>> expander.expand_tokens(template, context)
        'Ep04/sq0070/SH0170'
    """
    
    # Token pattern: $tokenName (camelCase convention)
    # Matches: $ep, $projRoot, $assetName, $sceneBase
    # Underscore (_) is used ONLY as separator, NOT part of token names
    # Examples: $ep_$seq_$shot (three tokens: ep, seq, shot)
    TOKEN_PATTERN = re.compile(r'\$([a-zA-Z][a-zA-Z0-9]*)')
    
    def __init__(self):
        """Initialize token expander."""
        pass
    
    def expand_tokens(self, template, context, version_override=None):
        """Replace all tokens in template with values from context.
        
        Args:
            template (str): Template string with tokens
            context (dict): Context data with token values
            version_override (str, optional): Override version token
        
        Returns:
            str: Expanded template with tokens replaced
        """
        if not template:
            return template
        
        # Make a copy of context
        ctx = dict(context)
        
        # Apply version override
        if version_override:
            ctx['ver'] = version_override
        
        # Find all tokens
        def replace_token(match):
            token_name = match.group(1)
            
            # Get value from context
            value = ctx.get(token_name)
            
            if value is None:
                # Leave token unexpanded
                return match.group(0)
            
            return str(value)
        
        # Replace all tokens
        expanded = self.TOKEN_PATTERN.sub(replace_token, template)
        
        return expanded
    
    def validate_template(self, template, required_tokens=None):
        """Validate template string for valid token syntax.
        
        Args:
            template (str): Template string to validate
            required_tokens (list, optional): List of required token names
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not template:
            return (False, "Template is empty")
        
        # Extract tokens
        tokens = self.extract_tokens(template)
        
        # Check required tokens
        if required_tokens:
            missing = set(required_tokens) - set(tokens)
            if missing:
                return (False, "Missing required tokens: {}".format(', '.join(missing)))
        
        return (True, None)
    
    def extract_tokens(self, template):
        """Extract list of tokens from template.
        
        Args:
            template (str): Template string
        
        Returns:
            list: List of token names (without $)
        """
        if not template:
            return []
        
        matches = self.TOKEN_PATTERN.findall(template)
        
        # Return unique tokens in order of first appearance
        seen = set()
        result = []
        for token in matches:
            if token not in seen:
                seen.add(token)
                result.append(token)
        
        return result
    
    def get_token_values(self, template, context):
        """Get dictionary of token names and their values from context.
        
        Args:
            template (str): Template string
            context (dict): Context data
        
        Returns:
            dict: Token names mapped to their values
        """
        tokens = self.extract_tokens(template)
        
        result = {}
        for token in tokens:
            value = context.get(token)
            result[token] = value
        
        return result

