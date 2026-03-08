"""
Schema definition for CTX_Shot node.

The shot node stores shot-specific context (ep, seq, shot codes) and manages
assets for that shot.
"""

from ..base import NodeSchema


class CTXShotSchema(NodeSchema):
    """Schema for CTX_Shot node.

    A shot node provides:
    - Shot identification (episode, sequence, shot codes)
    - Frame range and timing information
    - Display layer management
    - Asset connections
    - Parent sequence connection
    - Shot-level gaffer ownership (NEW!)
    """
    
    NODE_TYPE = "network"
    NODE_PREFIX = "CTX_Shot"
    CATEGORY = "Context"
    DESCRIPTION = "Shot context with asset management"
    
    ATTRIBUTES = {
        # Node identification
        'ctx_type': {
            'type': 'string',
            'default': 'CTX_Shot',
            'description': 'CTX node type identifier'
        },
        
        # Shot identity
        'ep_code': {
            'type': 'string',
            'default': '',
            'description': 'Episode code (e.g., "Ep04")'
        },
        
        'seq_code': {
            'type': 'string',
            'default': '',
            'description': 'Sequence code (e.g., "sq0070")'
        },
        
        'shot_code': {
            'type': 'string',
            'default': '',
            'description': 'Shot code (e.g., "SH0170")'
        },
        
        # Display layer
        'display_layer_name': {
            'type': 'string',
            'default': '',
            'description': 'Associated display layer name'
        },
        
        # Active state
        'is_active': {
            'type': 'bool',
            'default': False,
            'description': 'Whether this shot is currently active'
        },
        
        # Frame range
        'start_frame': {
            'type': 'int',
            'default': 1001,
            'description': 'Shot start frame'
        },
        
        'end_frame': {
            'type': 'int',
            'default': 1100,
            'description': 'Shot end frame'
        },
        
        'frame_offset': {
            'type': 'int',
            'default': 0,
            'description': 'Frame offset for this shot'
        },
        
        'fps': {
            'type': 'float',
            'default': 24.0,
            'description': 'Frames per second'
        },
        
        'handles': {
            'type': 'int',
            'default': 10,
            'description': 'Handle frames before/after shot'
        },
    }
    
    CONNECTIONS = {
        # Gaffer connection (INPUT - receives from LightGaffer, direct ownership)
        # Unidirectional: Gaffer.message → Shot.gaffer
        'gaffer': {
            'type': 'message',
            'multi': False,
            'direction': 'input',
            'accepts': ['CTX_LightGaffer'],
            'description': 'Input connection from CTX_LightGaffer (Gaffer.message → Shot.gaffer) - Direct ownership of shot-level gaffer'
        },

        # Asset connections (INPUT MULTI - receives from multiple Assets)
        # Unidirectional: Asset.message → Shot.assets[i]
        'assets': {
            'type': 'message',
            'multi': True,
            'direction': 'input',
            'accepts': ['CTX_Asset'],
            'description': 'Input connections from CTX_Asset nodes (Asset.message → Shot.assets[i])'
        },

        # Display layer connection (OUTPUT - sends to display layer)
        'display_layer_link': {
            'type': 'message',
            'multi': False,
            'direction': 'output',
            'description': 'Output connection to Maya display layer'
        },

        # NOTE: parentSequence removed - redundant with unidirectional pattern
        # To query parent sequence: cmds.listConnections("shot.message", source=False, destination=True, type='network')
        # Then filter for ctx_type == 'CTX_Sequence'

        # NOTE: manager removed - redundant with unidirectional pattern
        # To query manager: cmds.listConnections("shot.message", source=False, destination=True, type='network')
        # Then filter for ctx_type == 'CTX_Manager'
    }

