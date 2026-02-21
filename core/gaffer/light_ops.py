"""
Light Operations for applying and syncing gaffer values.

Provides operations for:
- Applying resolved gaffer values to Maya lights
- Syncing light contexts from Maya scene
- Batch operations on all lights in a gaffer
"""

try:
    import maya.cmds as cmds
except ImportError:
    cmds = None

from ..nodes.wrappers.gaffer import CTXLightGafferNode
from ..nodes.wrappers.light_context import CTXLightContextNode
from .resolver import AttributeResolver
from .manager import GafferManager


class LightOperations(object):
    """Operations for applying and syncing light values.
    
    Provides high-level operations for:
    - Applying resolved gaffer values to Maya lights
    - Syncing light contexts from Maya scene
    - Batch operations
    """
    
    @staticmethod
    def apply_gaffer_to_light(gaffer, light_name):
        """Apply resolved gaffer values to a Maya light.
        
        Resolves all attributes for the light and applies them to the Maya scene.
        
        Args:
            gaffer (CTXLightGafferNode or str): Gaffer to resolve from
            light_name (str): Light name to apply to
            
        Returns:
            dict: Applied attributes and their values:
                {
                    'intensity': float,
                    'exposure': float,
                    'color': (R, G, B),
                    ...
                }
                
        Raises:
            RuntimeError: If Maya is not available
            ValueError: If light not found in gaffer chain
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")
        
        # Convert to wrapper if needed
        if isinstance(gaffer, str):
            gaffer = CTXLightGafferNode(gaffer)
        
        # Find the light context to get target light shape
        target_light = GafferManager._find_light_in_chain(gaffer, light_name)
        if target_light is None:
            raise ValueError("Light '{}' not found in gaffer chain".format(light_name))
        
        if not cmds.objExists(target_light):
            raise ValueError("Target light '{}' does not exist in scene".format(target_light))
        
        # Resolve all attributes
        resolved = AttributeResolver.resolve_all_attributes(gaffer, light_name)
        
        applied = {}
        
        # Apply each resolved attribute
        for attr_name, attr_info in resolved.items():
            value = attr_info['value']
            
            try:
                LightOperations._apply_attribute_to_light(target_light, attr_name, value)
                applied[attr_name] = value
            except Exception as e:
                # Log error but continue with other attributes
                print("Warning: Failed to apply {} to {}: {}".format(attr_name, target_light, e))
        
        return applied
    
    @staticmethod
    def _apply_attribute_to_light(light_shape, attr_name, value):
        """Apply a single attribute value to a Maya light.
        
        Args:
            light_shape (str): Light shape node name
            attr_name (str): Attribute name
            value: Attribute value (float, tuple, or bool)
        """
        # Get transform node for transform attributes
        transform = None
        if attr_name in ('translate', 'rotate'):
            transforms = cmds.listRelatives(light_shape, parent=True, fullPath=True)
            if transforms:
                transform = transforms[0]
        
        # Apply based on attribute type
        if attr_name == 'intensity':
            if cmds.attributeQuery('intensity', node=light_shape, exists=True):
                cmds.setAttr('{}.intensity'.format(light_shape), value)
        
        elif attr_name == 'exposure':
            if cmds.attributeQuery('exposure', node=light_shape, exists=True):
                cmds.setAttr('{}.exposure'.format(light_shape), value)
        
        elif attr_name == 'color':
            if cmds.attributeQuery('color', node=light_shape, exists=True):
                cmds.setAttr('{}.color'.format(light_shape), value[0], value[1], value[2], type='double3')
        
        elif attr_name == 'temperature':
            if cmds.attributeQuery('temperature', node=light_shape, exists=True):
                cmds.setAttr('{}.temperature'.format(light_shape), value)
        
        elif attr_name == 'muted':
            # Muted typically controls visibility or enabled state
            if cmds.attributeQuery('visibility', node=light_shape, exists=True):
                cmds.setAttr('{}.visibility'.format(light_shape), not value)
        
        elif attr_name == 'translate' and transform:
            cmds.setAttr('{}.translate'.format(transform), value[0], value[1], value[2], type='double3')
        
        elif attr_name == 'rotate' and transform:
            cmds.setAttr('{}.rotate'.format(transform), value[0], value[1], value[2], type='double3')
    
    @staticmethod
    def apply_gaffer_to_all_lights(gaffer):
        """Apply resolved gaffer values to all lights in the gaffer.
        
        Args:
            gaffer (CTXLightGafferNode or str): Gaffer to apply
            
        Returns:
            dict: Results for each light:
                {
                    'light_name': {'intensity': ..., 'exposure': ..., ...},
                    ...
                }
                
        Raises:
            RuntimeError: If Maya is not available
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")
        
        # Convert to wrapper if needed
        if isinstance(gaffer, str):
            gaffer = CTXLightGafferNode(gaffer)
        
        # Get all lights (direct + inherited)
        lights = GafferManager.get_lights_in_gaffer(gaffer, include_inherited=True)
        
        results = {}
        
        for light_info in lights:
            light_name = light_info['name']
            try:
                applied = LightOperations.apply_gaffer_to_light(gaffer, light_name)
                results[light_name] = applied
            except Exception as e:
                print("Warning: Failed to apply gaffer to {}: {}".format(light_name, e))
                results[light_name] = {'error': str(e)}

        return results

    @staticmethod
    def sync_light_from_maya(gaffer, light_name, attributes=None):
        """Update light context from current Maya light values.

        Reads current values from Maya light and updates the light context
        in the gaffer. Only updates attributes that are enabled in the context.

        Args:
            gaffer (CTXLightGafferNode or str): Gaffer containing the light
            light_name (str): Light name to sync
            attributes (list, optional): Specific attributes to sync. If None, syncs all enabled attributes.

        Returns:
            dict: Synced attributes and their new values

        Raises:
            RuntimeError: If Maya is not available
            ValueError: If light not found in gaffer
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        # Convert to wrapper if needed
        if isinstance(gaffer, str):
            gaffer = CTXLightGafferNode(gaffer)

        # Find the light context in this gaffer (not inherited)
        light_ctx = None
        for ctx in gaffer.get_lights():
            if ctx.get_light_name() == light_name:
                light_ctx = ctx
                break

        if light_ctx is None:
            raise ValueError("Light '{}' not found in gaffer '{}'".format(
                light_name, gaffer.get_gaffer_name()))

        # Get target light
        target_light = light_ctx.get_target_light()
        if not cmds.objExists(target_light):
            raise ValueError("Target light '{}' does not exist in scene".format(target_light))

        # Capture current values from Maya
        captured = GafferManager.capture_light_values(target_light)

        # Get enabled attributes
        enabled_attrs = light_ctx.get_enabled_attributes()

        # Filter to requested attributes if specified
        if attributes:
            enabled_attrs = [attr for attr in enabled_attrs if attr in attributes]

        synced = {}

        # Update each enabled attribute
        for attr_name in enabled_attrs:
            if attr_name == 'color':
                if 'colorR' in captured:
                    light_ctx.set_attribute('colorR', captured['colorR'])
                    light_ctx.set_attribute('colorG', captured['colorG'])
                    light_ctx.set_attribute('colorB', captured['colorB'])
                    synced['color'] = (captured['colorR'], captured['colorG'], captured['colorB'])

            elif attr_name == 'translate':
                if 'translateX' in captured:
                    light_ctx.set_attribute('translateX', captured['translateX'])
                    light_ctx.set_attribute('translateY', captured['translateY'])
                    light_ctx.set_attribute('translateZ', captured['translateZ'])
                    synced['translate'] = (captured['translateX'], captured['translateY'], captured['translateZ'])

            elif attr_name == 'rotate':
                if 'rotateX' in captured:
                    light_ctx.set_attribute('rotateX', captured['rotateX'])
                    light_ctx.set_attribute('rotateY', captured['rotateY'])
                    light_ctx.set_attribute('rotateZ', captured['rotateZ'])
                    synced['rotate'] = (captured['rotateX'], captured['rotateY'], captured['rotateZ'])

            else:
                # Simple attribute
                if attr_name in captured:
                    light_ctx.set_attribute(attr_name, captured[attr_name])
                    synced[attr_name] = captured[attr_name]

        return synced

    @staticmethod
    def sync_all_lights(gaffer, attributes=None):
        """Sync all lights in gaffer from Maya scene.

        Args:
            gaffer (CTXLightGafferNode or str): Gaffer to sync
            attributes (list, optional): Specific attributes to sync. If None, syncs all enabled attributes.

        Returns:
            dict: Results for each light:
                {
                    'light_name': {'intensity': ..., 'exposure': ..., ...},
                    ...
                }

        Raises:
            RuntimeError: If Maya is not available
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        # Convert to wrapper if needed
        if isinstance(gaffer, str):
            gaffer = CTXLightGafferNode(gaffer)

        # Get direct lights only (not inherited)
        lights = gaffer.get_lights()

        results = {}

        for light_ctx in lights:
            light_name = light_ctx.get_light_name()
            try:
                synced = LightOperations.sync_light_from_maya(gaffer, light_name, attributes)
                results[light_name] = synced
            except Exception as e:
                print("Warning: Failed to sync {}: {}".format(light_name, e))
                results[light_name] = {'error': str(e)}

        return results

