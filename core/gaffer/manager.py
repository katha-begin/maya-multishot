"""
Gaffer Manager for light management operations.

Provides high-level operations for:
- Adding/removing lights from gaffers
- Creating overrides in child gaffers
- Querying lights (direct + inherited)
- Capturing light values from Maya scene
"""

try:
    import maya.cmds as cmds
except ImportError:
    cmds = None

from ..nodes.wrappers.gaffer import CTXLightGafferNode
from ..nodes.wrappers.light_context import CTXLightContextNode


class GafferManager(object):
    """Manager for gaffer operations.
    
    Provides high-level API for managing lights within gaffers,
    including inheritance and override management.
    """
    
    @staticmethod
    def add_light_to_gaffer(gaffer, light_shape, light_name=None):
        """Add a Maya light to a gaffer by creating a CTX_LightContext.
        
        Args:
            gaffer (CTXLightGafferNode or str): Gaffer wrapper or node name
            light_shape (str): Maya light shape node name
            light_name (str, optional): Human-readable light name. If None, uses light_shape.
            
        Returns:
            CTXLightContextNode: Created light context wrapper
            
        Raises:
            RuntimeError: If Maya is not available
            ValueError: If light already exists in gaffer
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")
        
        # Convert to wrapper if needed
        if isinstance(gaffer, str):
            gaffer = CTXLightGafferNode(gaffer)
        
        # Check if light already exists in this gaffer
        existing_lights = gaffer.get_lights()
        for light_ctx in existing_lights:
            if light_ctx.get_light_name() == (light_name or light_shape):
                raise ValueError("Light '{}' already exists in gaffer '{}'".format(
                    light_name or light_shape, gaffer.get_gaffer_name()))
        
        # Create light context
        light_ctx = CTXLightContextNode.create(
            lightName=light_name or light_shape
        )
        
        # Connect to gaffer
        light_ctx.set_parent_gaffer(gaffer)
        
        # Connect to target light
        light_ctx.set_target_light(light_shape)
        
        return light_ctx
    
    @staticmethod
    def remove_light_from_gaffer(gaffer, light_name):
        """Remove a light from a gaffer by deleting its CTX_LightContext.
        
        Args:
            gaffer (CTXLightGafferNode or str): Gaffer wrapper or node name
            light_name (str): Light name to remove
            
        Returns:
            bool: True if light was removed, False if not found
            
        Raises:
            RuntimeError: If Maya is not available
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")
        
        # Convert to wrapper if needed
        if isinstance(gaffer, str):
            gaffer = CTXLightGafferNode(gaffer)
        
        # Find the light context
        lights = gaffer.get_lights()
        for light_ctx in lights:
            if light_ctx.get_light_name() == light_name:
                light_ctx.delete()
                return True
        
        return False
    
    @staticmethod
    def add_override_to_gaffer(child_gaffer, light_name, attribute, value):
        """Create or update an attribute override in a child gaffer.
        
        If the light doesn't exist in the child gaffer, creates a new light context.
        If it exists, updates the attribute override.
        
        Args:
            child_gaffer (CTXLightGafferNode or str): Child gaffer wrapper or node name
            light_name (str): Light name
            attribute (str): Attribute to override (e.g., 'intensity', 'exposure')
            value: Attribute value
            
        Returns:
            CTXLightContextNode: Light context with override
            
        Raises:
            RuntimeError: If Maya is not available
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")
        
        # Convert to wrapper if needed
        if isinstance(child_gaffer, str):
            child_gaffer = CTXLightGafferNode(child_gaffer)
        
        # Check if light context already exists in this gaffer
        lights = child_gaffer.get_lights()
        light_ctx = None
        
        for ctx in lights:
            if ctx.get_light_name() == light_name:
                light_ctx = ctx
                break
        
        # If not found, need to find the light in parent chain and create override
        if light_ctx is None:
            # Find the light's target shape from parent chain
            target_light = GafferManager._find_light_in_chain(child_gaffer, light_name)
            if target_light is None:
                raise ValueError("Light '{}' not found in gaffer chain".format(light_name))
            
            # Create new light context in child gaffer
            light_ctx = CTXLightContextNode.create(lightName=light_name)
            light_ctx.set_parent_gaffer(child_gaffer)
            light_ctx.set_target_light(target_light)
        
        # Set the attribute override
        light_ctx.set_attribute_override(attribute, value, enabled=True)

        return light_ctx

    @staticmethod
    def _find_light_in_chain(gaffer, light_name):
        """Find a light's target shape by walking up the gaffer chain.

        Args:
            gaffer (CTXLightGafferNode): Gaffer to start search from
            light_name (str): Light name to find

        Returns:
            str or None: Light shape node name, or None if not found
        """
        chain = gaffer.build_chain()

        for gaffer_node in chain:
            lights = gaffer_node.get_lights()
            for light_ctx in lights:
                if light_ctx.get_light_name() == light_name:
                    return light_ctx.get_target_light()

        return None

    @staticmethod
    def get_lights_in_gaffer(gaffer, include_inherited=True):
        """Get all lights in a gaffer, optionally including inherited lights.

        Args:
            gaffer (CTXLightGafferNode or str): Gaffer wrapper or node name
            include_inherited (bool): If True, includes lights from parent chain

        Returns:
            list: List of dicts with light information:
                {
                    'name': str,
                    'context': CTXLightContextNode,
                    'target': str (light shape),
                    'source_gaffer': CTXLightGafferNode,
                    'is_direct': bool
                }
        """
        if cmds is None:
            return []

        # Convert to wrapper if needed
        if isinstance(gaffer, str):
            gaffer = CTXLightGafferNode(gaffer)

        lights_info = []
        seen_lights = set()

        # Get direct lights first
        direct_lights = gaffer.get_lights()
        for light_ctx in direct_lights:
            light_name = light_ctx.get_light_name()
            lights_info.append({
                'name': light_name,
                'context': light_ctx,
                'target': light_ctx.get_target_light(),
                'source_gaffer': gaffer,
                'is_direct': True
            })
            seen_lights.add(light_name)

        # Get inherited lights if requested
        if include_inherited:
            chain = gaffer.build_chain()[1:]  # Skip self
            for parent_gaffer in chain:
                parent_lights = parent_gaffer.get_lights()
                for light_ctx in parent_lights:
                    light_name = light_ctx.get_light_name()
                    if light_name not in seen_lights:
                        lights_info.append({
                            'name': light_name,
                            'context': light_ctx,
                            'target': light_ctx.get_target_light(),
                            'source_gaffer': parent_gaffer,
                            'is_direct': False
                        })
                        seen_lights.add(light_name)

        return lights_info

    @staticmethod
    def capture_light_values(light_shape):
        """Capture current attribute values from a Maya light.

        Args:
            light_shape (str): Maya light shape node name

        Returns:
            dict: Attribute values that can be used to create/update light context
                {
                    'intensity': float,
                    'exposure': float,
                    'colorR': float,
                    'colorG': float,
                    'colorB': float,
                    'temperature': float,
                    'translateX': float,
                    'translateY': float,
                    'translateZ': float,
                    'rotateX': float,
                    'rotateY': float,
                    'rotateZ': float,
                }

        Raises:
            RuntimeError: If Maya is not available
            ValueError: If light doesn't exist
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        if not cmds.objExists(light_shape):
            raise ValueError("Light '{}' does not exist".format(light_shape))

        values = {}

        # Get transform node
        transform = cmds.listRelatives(light_shape, parent=True, fullPath=True)
        if transform:
            transform = transform[0]

        # Capture intensity (common attribute)
        if cmds.attributeQuery('intensity', node=light_shape, exists=True):
            values['intensity'] = cmds.getAttr('{}.intensity'.format(light_shape))

        # Capture exposure (Arnold/Redshift)
        if cmds.attributeQuery('exposure', node=light_shape, exists=True):
            values['exposure'] = cmds.getAttr('{}.exposure'.format(light_shape))

        # Capture color
        if cmds.attributeQuery('color', node=light_shape, exists=True):
            color = cmds.getAttr('{}.color'.format(light_shape))[0]
            values['colorR'] = color[0]
            values['colorG'] = color[1]
            values['colorB'] = color[2]

        # Capture temperature (if exists)
        if cmds.attributeQuery('temperature', node=light_shape, exists=True):
            values['temperature'] = cmds.getAttr('{}.temperature'.format(light_shape))

        # Capture transform
        if transform:
            translate = cmds.getAttr('{}.translate'.format(transform))[0]
            values['translateX'] = translate[0]
            values['translateY'] = translate[1]
            values['translateZ'] = translate[2]

            rotate = cmds.getAttr('{}.rotate'.format(transform))[0]
            values['rotateX'] = rotate[0]
            values['rotateY'] = rotate[1]
            values['rotateZ'] = rotate[2]

        return values

