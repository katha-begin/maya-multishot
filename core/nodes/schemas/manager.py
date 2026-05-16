"""
Schema definition for CTX_Manager node.

The manager node is the root node that stores global context and manages
all shots and sequences in the scene. Only one CTX_Manager should exist
per scene (singleton pattern).
"""

from ..base import NodeSchema


class CTXManagerSchema(NodeSchema):
    """Schema for CTX_Manager node.
    
    A manager node provides:
    - Global project configuration
    - Root of the context hierarchy
    - Sequence and shot management
    - Active shot tracking
    """
    
    NODE_TYPE = "network"
    NODE_PREFIX = "CTX_Manager"
    CATEGORY = "Context"
    DESCRIPTION = "Root context manager (singleton)"
    
    ATTRIBUTES = {
        # Node identification
        'ctx_type': {
            'type': 'string',
            'default': 'CTX_Manager',
            'description': 'CTX node type identifier'
        },
        
        # Project configuration
        'config_path': {
            'type': 'string',
            'default': '',
            'description': 'Path to project configuration file'
        },
        
        'project_root': {
            'type': 'string',
            'default': '',
            'description': 'Project root directory'
        },
        
        # Active shot tracking
        'active_shot_id': {
            'type': 'string',
            'default': '',
            'description': 'ID of currently active shot (e.g., "Ep04_sq0070_SH0170")'
        },
    }
    
    CONNECTIONS = {
        # Sequence connections (INPUT MULTI - receives from multiple Sequences)
        'sequences': {
            'type': 'message',
            'multi': True,
            'direction': 'input',
            'accepts': ['CTX_Sequence'],
            'description': 'Input connections from CTX_Sequence nodes (Sequence.message -> Manager.sequences[i])'
        },
        
        # Shot connections (INPUT MULTI - receives from multiple Shots, for backward compatibility)
        'shots': {
            'type': 'message',
            'multi': True,
            'direction': 'input',
            'accepts': ['CTX_Shot'],
            'description': 'Input connections from CTX_Shot nodes (Shot.message -> Manager.shots[i]) - for backward compatibility'
        },
    }

