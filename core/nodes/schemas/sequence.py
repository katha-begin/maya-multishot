"""
Schema definition for CTX_Sequence node.

The sequence node is a container for organizing shots within a sequence.
It owns a sequence-level light gaffer for sequence-wide lighting adjustments.
"""

from ..base import NodeSchema
from .lock_mixin import LockSchemaMixin


class CTXSequenceSchema(LockSchemaMixin, NodeSchema):
    """Schema for CTX_Sequence node.
    
    A sequence node provides:
    - Sequence-level organization (groups shots)
    - Sequence metadata (frame range, etc.)
    - Connection to sequence-level gaffer
    - Connection to parent manager
    """
    
    NODE_TYPE = "network"
    NODE_PREFIX = "CTX_Sequence"
    CATEGORY = "Context"
    DESCRIPTION = "Sequence container with gaffer connection"
    
    ATTRIBUTES = {
        # Node identification
        'ctx_type': {
            'type': 'string',
            'default': 'CTX_Sequence',
            'description': 'CTX node type identifier'
        },
        
        # Sequence identity
        'sequenceCode': {
            'type': 'string',
            'default': '',
            'description': 'Sequence code (e.g., "sq0070")'
        },
        
        'sequenceName': {
            'type': 'string',
            'default': '',
            'description': 'Human-readable sequence name'
        },
        
        # Frame range
        'frameStart': {
            'type': 'int',
            'default': 1001,
            'description': 'Sequence start frame'
        },
        
        'frameEnd': {
            'type': 'int',
            'default': 2000,
            'description': 'Sequence end frame'
        },
        
        # Notes
        'notes': {
            'type': 'string',
            'default': '',
            'description': 'User notes about this sequence'
        },
    }
    
    CONNECTIONS = {
        # Child connections (INPUT MULTI - receives from multiple Shots)
        # Unidirectional: Shot.message -> Sequence.shots[i]
        'shots': {
            'type': 'message',
            'multi': True,
            'direction': 'input',
            'accepts': ['CTX_Shot'],
            'description': 'Input connections from CTX_Shot nodes (Shot.message -> Sequence.shots[i])'
        },

        # Slate connection (INPUT - receives from CTXSlateNode)
        # Unidirectional: Slate.message -> Sequence.slate
        'slate': {
            'type': 'message',
            'multi': False,
            'direction': 'input',
            'accepts': ['CTX_Slate'],
            'description': 'Input connection from CTXSlateNode (Slate.message -> Sequence.slate)',
        },

        # Gaffer connection (INPUT - receives from Gaffer)
        # Unidirectional: Gaffer.message -> Sequence.gaffer
        'gaffer': {
            'type': 'message',
            'multi': False,
            'direction': 'input',
            'accepts': ['CTX_LightGaffer'],
            'description': 'Input connection from CTX_LightGaffer (Gaffer.message -> Sequence.gaffer)'
        },

        # NOTE: parentManager removed - redundant with unidirectional pattern
        # To query parent manager: cmds.listConnections("sequence.message", source=False, destination=True)
    }

