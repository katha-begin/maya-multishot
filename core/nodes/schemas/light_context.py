"""
Schema definition for CTX_LightContext node.

The light context node stores per-gaffer overrides for a specific light.
Each attribute has a corresponding "enabled" flag to control inheritance.
"""

from ..base import NodeSchema


class CTXLightContextSchema(NodeSchema):
    """Schema for CTX_LightContext node.
    
    A light context stores attribute values and override flags for a single light
    within a gaffer. Each attribute can be independently enabled/disabled for
    per-attribute inheritance control.
    """
    
    NODE_TYPE = "network"
    NODE_PREFIX = "CTX_LightContext"
    CATEGORY = "Lighting"
    DESCRIPTION = "Light attribute context with per-attribute overrides"
    
    ATTRIBUTES = {
        # Node identification
        'ctx_node_type': {
            'type': 'string',
            'default': 'CTX_LightContext',
            'description': 'CTX node type identifier'
        },
        
        # Light identity
        'lightName': {
            'type': 'string',
            'default': '',
            'description': 'Name of the Maya light (e.g., "keyLight1")'
        },
        
        # Light attributes with enabled flags
        # Intensity
        'intensity': {
            'type': 'float',
            'default': 1.0,
            'description': 'Light intensity value'
        },
        'intensityEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether intensity is overridden in this gaffer'
        },
        
        # Exposure
        'exposure': {
            'type': 'float',
            'default': 0.0,
            'description': 'Light exposure value'
        },
        'exposureEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether exposure is overridden in this gaffer'
        },
        
        # Color
        'colorR': {
            'type': 'float',
            'default': 1.0,
            'description': 'Light color red channel'
        },
        'colorG': {
            'type': 'float',
            'default': 1.0,
            'description': 'Light color green channel'
        },
        'colorB': {
            'type': 'float',
            'default': 1.0,
            'description': 'Light color blue channel'
        },
        'colorEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether color is overridden in this gaffer'
        },
        
        # Temperature
        'temperature': {
            'type': 'float',
            'default': 6500.0,
            'description': 'Light color temperature in Kelvin'
        },
        'temperatureEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether temperature is overridden in this gaffer'
        },
        
        # Muted state
        'muted': {
            'type': 'bool',
            'default': False,
            'description': 'Whether light is muted (disabled)'
        },
        'mutedEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether muted state is overridden in this gaffer'
        },
        
        # Transform attributes
        'translateX': {
            'type': 'float',
            'default': 0.0,
            'description': 'Light X translation'
        },
        'translateY': {
            'type': 'float',
            'default': 0.0,
            'description': 'Light Y translation'
        },
        'translateZ': {
            'type': 'float',
            'default': 0.0,
            'description': 'Light Z translation'
        },
        'translateEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether translation is overridden in this gaffer'
        },
        
        'rotateX': {
            'type': 'float',
            'default': 0.0,
            'description': 'Light X rotation'
        },
        'rotateY': {
            'type': 'float',
            'default': 0.0,
            'description': 'Light Y rotation'
        },
        'rotateZ': {
            'type': 'float',
            'default': 0.0,
            'description': 'Light Z rotation'
        },
        'rotateEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether rotation is overridden in this gaffer'
        },
    }
    
    CONNECTIONS = {
        # Parent gaffer
        'parentGaffer': {
            'type': 'message',
            'multi': False,
            'direction': 'input',
            'accepts': ['CTX_LightGaffer'],
            'description': 'Gaffer that owns this light context'
        },
        
        # Target light
        'targetLight': {
            'type': 'message',
            'multi': False,
            'direction': 'output',
            'description': 'Maya light shape node'
        },
    }

