"""
Schema definition for CTX_LightGaffer node.

The gaffer node manages a collection of lights with inheritance-based overrides.
Gaffers can be chained (Master → Sequence → Shot) for hierarchical light management.
"""

from ..base import NodeSchema


class CTXLightGafferSchema(NodeSchema):
    """Schema for CTX_LightGaffer node.
    
    A gaffer is a container for light contexts that provides:
    - Light collection management
    - Hierarchical inheritance (parent → child)
    - Per-attribute override system
    - Flexible chain-based architecture (not hardcoded by type)
    """
    
    NODE_TYPE = "network"
    NODE_PREFIX = "CTX_LightGaffer"
    CATEGORY = "Lighting"
    DESCRIPTION = "Light gaffer with hierarchical inheritance"
    
    ATTRIBUTES = {
        # Node identification
        'ctx_type': {
            'type': 'string',
            'default': 'CTX_LightGaffer',
            'description': 'CTX node type identifier'
        },
        
        # Gaffer identity
        'gafferName': {
            'type': 'string',
            'default': '',
            'description': 'Human-readable gaffer name (e.g., "Master", "sq0070", "SH0010")'
        },
        
        'gafferType': {
            'type': 'string',
            'default': 'custom',
            'description': 'Descriptive type (master/sequence/shot/custom) - for UI organization only'
        },
        
        'scopeCode': {
            'type': 'string',
            'default': '',
            'description': 'Scope identifier (empty for master, seq code, shot code)'
        },
        
        # State
        'enabled': {
            'type': 'bool',
            'default': True,
            'description': 'Whether this gaffer is active'
        },
        
        'notes': {
            'type': 'string',
            'default': '',
            'description': 'User notes about this gaffer'
        },
    }
    
    CONNECTIONS = {
        # Inheritance chain connection (INPUT - receives from parent gaffer)
        # Unidirectional: ChildGaffer.message → ParentGaffer.parentGaffer
        'parentGaffer': {
            'type': 'message',
            'multi': False,
            'direction': 'input',
            'accepts': ['CTX_LightGaffer'],
            'description': 'Parent gaffer in inheritance chain (for attribute resolution)'
        },

        # Child gaffer connections (OUTPUT MULTI - for querying children)
        'childGaffers': {
            'type': 'message',
            'multi': True,
            'direction': 'output',
            'description': 'Child gaffers that inherit from this gaffer'
        },

        # Light context connections (INPUT MULTI - receives from CTX_LightContext.message)
        'lights': {
            'type': 'message',
            'multi': True,
            'direction': 'input',
            'description': 'Light context nodes managed by this gaffer'
        },

        # NOTE: parentNode removed - redundant with direct ownership pattern
        # Gaffers are now directly owned by Sequence/Shot via their .gaffer attribute
        # To query owner: cmds.listConnections("gaffer.message", source=False, destination=True, type='network')
        # Then filter for ctx_type in ['CTX_Sequence', 'CTX_Shot']
    }

