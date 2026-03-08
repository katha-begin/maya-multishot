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
    NODE_PREFIX = "CTX_LightCtx"
    CATEGORY = "Lighting"
    DESCRIPTION = "Light attribute context with per-attribute overrides"
    
    ATTRIBUTES = {
        # Node identification
        'ctx_type': {
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
        'intensityMode': {
            'type': 'string',
            'default': 'replace',
            'description': 'Override mode: replace or additive'
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
        'exposureMode': {
            'type': 'string',
            'default': 'replace',
            'description': 'Override mode: replace or additive'
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
        'colorMode': {
            'type': 'string',
            'default': 'replace',
            'description': 'Override mode: replace only (additive not supported for color)'
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
        'temperatureMode': {
            'type': 'string',
            'default': 'replace',
            'description': 'Override mode: replace or additive'
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
        'translateMode': {
            'type': 'string',
            'default': 'replace',
            'description': 'Override mode: replace or additive'
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
        'rotateMode': {
            'type': 'string',
            'default': 'replace',
            'description': 'Override mode: replace or additive'
        },

        # Scale
        'scaleX': {
            'type': 'float',
            'default': 1.0,
            'description': 'Light X scale'
        },
        'scaleY': {
            'type': 'float',
            'default': 1.0,
            'description': 'Light Y scale'
        },
        'scaleZ': {
            'type': 'float',
            'default': 1.0,
            'description': 'Light Z scale'
        },
        'scaleEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether scale is overridden in this gaffer'
        },
        'scaleMode': {
            'type': 'string',
            'default': 'replace',
            'description': 'Override mode: replace or additive'
        },

        # Spread (cone angle / softness for spot/physical lights)
        'spread': {
            'type': 'float',
            'default': 1.0,
            'description': 'Light spread / cone angle'
        },
        'spreadEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether spread is overridden in this gaffer'
        },
        'spreadMode': {
            'type': 'string',
            'default': 'replace',
            'description': 'Override mode: replace or additive'
        },

        # Contribution flags
        'affectDiffuse': {
            'type': 'bool',
            'default': True,
            'description': 'Whether light affects diffuse'
        },
        'affectDiffuseEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether affectDiffuse is overridden in this gaffer'
        },

        'affectSpecular': {
            'type': 'bool',
            'default': True,
            'description': 'Whether light affects specular'
        },
        'affectSpecularEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether affectSpecular is overridden in this gaffer'
        },

        'affectGI': {
            'type': 'bool',
            'default': True,
            'description': 'Whether light contributes to GI / indirect'
        },
        'affectGIEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether affectGI is overridden in this gaffer'
        },

        'shadowEnable': {
            'type': 'bool',
            'default': True,
            'description': 'Whether light casts shadows'
        },
        'shadowEnableEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether shadowEnable is overridden in this gaffer'
        },

        # Area spread (Redshift areaSpread)
        'areaSpread': {
            'type': 'float',
            'default': 1.0,
            'description': 'Area spread (Redshift areaSpread)'
        },
        'areaSpreadEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether areaSpread is overridden in this gaffer'
        },
        'areaSpreadMode': {
            'type': 'string',
            'default': 'replace',
            'description': 'Override mode: replace or additive'
        },

        # Per-ray contribution scales (Redshift)
        'diffuseContrib': {
            'type': 'float',
            'default': 1.0,
            'description': 'Diffuse ray contribution scale'
        },
        'diffuseContribEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether diffuseContrib is overridden in this gaffer'
        },
        'diffuseContribMode': {
            'type': 'string',
            'default': 'replace',
            'description': 'Override mode: replace or additive'
        },

        'reflectionContrib': {
            'type': 'float',
            'default': 1.0,
            'description': 'Reflection ray contribution scale'
        },
        'reflectionContribEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether reflectionContrib is overridden in this gaffer'
        },
        'reflectionContribMode': {
            'type': 'string',
            'default': 'replace',
            'description': 'Override mode: replace or additive'
        },

        'transmissionContrib': {
            'type': 'float',
            'default': 1.0,
            'description': 'Transmission ray contribution scale'
        },
        'transmissionContribEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether transmissionContrib is overridden in this gaffer'
        },
        'transmissionContribMode': {
            'type': 'string',
            'default': 'replace',
            'description': 'Override mode: replace or additive'
        },

        'singleScatterContrib': {
            'type': 'float',
            'default': 1.0,
            'description': 'Single scattering ray contribution scale'
        },
        'singleScatterContribEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether singleScatterContrib is overridden in this gaffer'
        },
        'singleScatterContribMode': {
            'type': 'string',
            'default': 'replace',
            'description': 'Override mode: replace or additive'
        },

        'multiScatterContrib': {
            'type': 'float',
            'default': 1.0,
            'description': 'Multiple scattering ray contribution scale'
        },
        'multiScatterContribEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether multiScatterContrib is overridden in this gaffer'
        },
        'multiScatterContribMode': {
            'type': 'string',
            'default': 'replace',
            'description': 'Override mode: replace or additive'
        },

        'volumeContrib': {
            'type': 'float',
            'default': 1.0,
            'description': 'Volume ray contribution scale'
        },
        'volumeContribEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether volumeContrib is overridden in this gaffer'
        },
        'volumeContribMode': {
            'type': 'string',
            'default': 'replace',
            'description': 'Override mode: replace or additive'
        },

        'indirectContrib': {
            'type': 'float',
            'default': 1.0,
            'description': 'Indirect ray contribution scale'
        },
        'indirectContribEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether indirectContrib is overridden in this gaffer'
        },
        'indirectContribMode': {
            'type': 'string',
            'default': 'replace',
            'description': 'Override mode: replace or additive'
        },

        'toonDiffuseContrib': {
            'type': 'float',
            'default': 1.0,
            'description': 'Toon diffuse ray contribution scale'
        },
        'toonDiffuseContribEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether toonDiffuseContrib is overridden in this gaffer'
        },
        'toonDiffuseContribMode': {
            'type': 'string',
            'default': 'replace',
            'description': 'Override mode: replace or additive'
        },

        'toonReflectionContrib': {
            'type': 'float',
            'default': 1.0,
            'description': 'Toon reflection ray contribution scale'
        },
        'toonReflectionContribEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether toonReflectionContrib is overridden in this gaffer'
        },
        'toonReflectionContribMode': {
            'type': 'string',
            'default': 'replace',
            'description': 'Override mode: replace or additive'
        },
    }
    
    CONNECTIONS = {
        # Target light connection (OUTPUT - sends to Maya light)
        'targetLight': {
            'type': 'message',
            'multi': False,
            'direction': 'output',
            'description': 'Maya light shape node'
        },

        # NOTE: parentGaffer removed - redundant with unidirectional pattern
        # Light contexts are owned by gaffer via gaffer.lights[i] OUTPUT connection
        # To query parent gaffer: cmds.listConnections("light_context.message", source=False, destination=True, type='network')
        # Then filter for ctx_type == 'CTX_LightGaffer'
    }

