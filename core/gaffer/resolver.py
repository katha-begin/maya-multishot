"""
Attribute Resolver for gaffer chain inheritance.

Provides attribute resolution by walking the gaffer chain to find
the first enabled value for each attribute.
"""

try:
    import maya.cmds as cmds
except ImportError:
    cmds = None

from ..nodes.wrappers.gaffer import CTXLightGafferNode
from ..nodes.wrappers.light_context import CTXLightContextNode


class AttributeResolver(object):
    """Resolver for attribute inheritance in gaffer chains.
    
    Walks the gaffer chain from child to parent to find the first
    enabled value for each attribute.
    """
    
    # Supported attributes
    SUPPORTED_ATTRIBUTES = [
        'intensity',
        'exposure',
        'color',
        'temperature',
        'muted',
        'translate',
        'rotate',
        'scale',
        'spread',
        'affectDiffuse',
        'affectSpecular',
        'affectGI',
        'shadowEnable',
    ]
    
    @staticmethod
    def resolve_attribute(gaffer, light_name, attribute):
        """Resolve a single attribute by walking the gaffer chain.
        
        Walks from the given gaffer up through parent chain to find the first
        enabled value for the specified attribute.
        
        Args:
            gaffer (CTXLightGafferNode or str): Starting gaffer
            light_name (str): Light name to resolve
            attribute (str): Attribute name (e.g., 'intensity', 'exposure')
            
        Returns:
            dict or None: Resolved value info:
                {
                    'value': attribute value (float, tuple, or bool),
                    'source_gaffer': CTXLightGafferNode,
                    'source_context': CTXLightContextNode
                }
                Returns None if attribute is not enabled anywhere in chain.
                
        Raises:
            ValueError: If attribute is not supported
        """
        if attribute not in AttributeResolver.SUPPORTED_ATTRIBUTES:
            raise ValueError("Unsupported attribute: {}".format(attribute))
        
        # Convert to wrapper if needed
        if isinstance(gaffer, str):
            gaffer = CTXLightGafferNode(gaffer)
        
        # Build chain from child to parent
        chain = gaffer.build_chain()
        
        # Walk chain looking for enabled attribute
        for gaffer_node in chain:
            lights = gaffer_node.get_lights()
            
            for light_ctx in lights:
                if light_ctx.get_light_name() == light_name:
                    # Check if this attribute is enabled
                    enabled_flag = "{}Enabled".format(attribute)
                    
                    if light_ctx.get_attribute(enabled_flag):
                        # Get the value
                        value = AttributeResolver._get_attribute_value(light_ctx, attribute)
                        
                        return {
                            'value': value,
                            'source_gaffer': gaffer_node,
                            'source_context': light_ctx
                        }
        
        return None
    
    @staticmethod
    def _get_attribute_value(light_ctx, attribute):
        """Get attribute value from light context.
        
        Handles compound attributes (color, translate, rotate).
        
        Args:
            light_ctx (CTXLightContextNode): Light context
            attribute (str): Attribute name
            
        Returns:
            Value (float, tuple, or bool)
        """
        if attribute == 'color':
            return (
                light_ctx.get_attribute('colorR'),
                light_ctx.get_attribute('colorG'),
                light_ctx.get_attribute('colorB')
            )
        elif attribute == 'translate':
            return (
                light_ctx.get_attribute('translateX'),
                light_ctx.get_attribute('translateY'),
                light_ctx.get_attribute('translateZ')
            )
        elif attribute == 'rotate':
            return (
                light_ctx.get_attribute('rotateX'),
                light_ctx.get_attribute('rotateY'),
                light_ctx.get_attribute('rotateZ')
            )
        elif attribute == 'scale':
            return (
                light_ctx.get_attribute('scaleX'),
                light_ctx.get_attribute('scaleY'),
                light_ctx.get_attribute('scaleZ')
            )
        else:
            return light_ctx.get_attribute(attribute)
    
    @staticmethod
    def resolve_all_attributes(gaffer, light_name):
        """Resolve all attributes for a light.
        
        Args:
            gaffer (CTXLightGafferNode or str): Starting gaffer
            light_name (str): Light name to resolve
            
        Returns:
            dict: Resolved attributes:
                {
                    'intensity': {'value': float, 'source_gaffer': ..., 'source_context': ...},
                    'exposure': {...},
                    'color': {...},
                    'temperature': {...},
                    'muted': {...},
                    'translate': {...},
                    'rotate': {...}
                }
                Attributes not enabled anywhere in chain are omitted.
        """
        resolved = {}
        
        for attribute in AttributeResolver.SUPPORTED_ATTRIBUTES:
            result = AttributeResolver.resolve_attribute(gaffer, light_name, attribute)
            if result is not None:
                resolved[attribute] = result

        return resolved

    @staticmethod
    def get_attribute_source(gaffer, light_name, attribute):
        """Find which gaffer provides the value for an attribute.

        Similar to resolve_attribute but only returns source information,
        not the actual value.

        Args:
            gaffer (CTXLightGafferNode or str): Starting gaffer
            light_name (str): Light name
            attribute (str): Attribute name

        Returns:
            dict or None: Source information:
                {
                    'gaffer': CTXLightGafferNode,
                    'gaffer_name': str,
                    'gaffer_type': str,
                    'is_direct': bool (True if from starting gaffer)
                }
                Returns None if attribute is not enabled anywhere in chain.

        Raises:
            ValueError: If attribute is not supported
        """
        result = AttributeResolver.resolve_attribute(gaffer, light_name, attribute)

        if result is None:
            return None

        source_gaffer = result['source_gaffer']

        # Convert to wrapper if needed
        if isinstance(gaffer, str):
            gaffer = CTXLightGafferNode(gaffer)

        return {
            'gaffer': source_gaffer,
            'gaffer_name': source_gaffer.get_gaffer_name(),
            'gaffer_type': source_gaffer.get_gaffer_type(),
            'is_direct': source_gaffer.node_name == gaffer.node_name
        }

    @staticmethod
    def get_all_attribute_sources(gaffer, light_name):
        """Get source information for all attributes.

        Args:
            gaffer (CTXLightGafferNode or str): Starting gaffer
            light_name (str): Light name

        Returns:
            dict: Source information for each attribute:
                {
                    'intensity': {'gaffer': ..., 'gaffer_name': ..., 'is_direct': ...},
                    'exposure': {...},
                    ...
                }
                Attributes not enabled anywhere are omitted.
        """
        sources = {}

        for attribute in AttributeResolver.SUPPORTED_ATTRIBUTES:
            source = AttributeResolver.get_attribute_source(gaffer, light_name, attribute)
            if source is not None:
                sources[attribute] = source

        return sources

