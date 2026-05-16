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
from ..renderers import get_maya_attr
from ..logging_config import get_logger

logger = get_logger(__name__)


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

        # Normalize light_shape to the actual shape node (not a transform).
        # set_target_light() also does this, but we need the resolved name here
        # so that light_name defaults to the shape rather than the transform.
        resolved_shape = light_shape
        if cmds.objExists(light_shape) and cmds.nodeType(light_shape) == 'transform':
            child_shapes = cmds.listRelatives(light_shape, shapes=True, fullPath=False) or []
            if not child_shapes:
                child_shapes = cmds.listRelatives(
                    light_shape, shapes=True, fullPath=False, allDescendants=True) or []
            if child_shapes:
                resolved_shape = child_shapes[0]

        resolved_name = light_name or resolved_shape

        # Check if light already exists in this gaffer
        existing_lights = gaffer.get_lights()
        for light_ctx in existing_lights:
            if light_ctx.get_light_name() == resolved_name:
                raise ValueError("Light '{}' already exists in gaffer '{}'".format(
                    resolved_name, gaffer.get_gaffer_name()))

        # Create light context with descriptive node name
        light_ctx = CTXLightContextNode.create(
            gaffer_name=gaffer.get_gaffer_name(),
            lightName=resolved_name
        )

        # Connect to gaffer
        light_ctx.set_parent_gaffer(gaffer)

        # Connect to target light (set_target_light also normalizes, but we pass
        # resolved_shape directly so the connection is always the shape node)
        light_ctx.set_target_light(resolved_shape)

        # Capture current Maya values.
        # - Store in CTX_LightOriginals node as persistent baseline (once per light).
        # - Store as enabled overrides in the light context so UI shows real values.
        try:
            captured = GafferManager.capture_light_values(resolved_shape)

            # Persist as originals if this light has not been registered before
            try:
                from ..nodes.wrappers.light_originals import CTXLightOriginalsNode
                originals_node = CTXLightOriginalsNode.get_or_create()
                if not originals_node.has_light(resolved_shape):
                    originals_node.store_light(resolved_shape, captured)
            except Exception as orig_err:
                logger.warning("GafferManager: could not store originals for '%s': %s",
                               resolved_shape, orig_err)
            # Simple scalar attrs
            _SIMPLE = ['intensity', 'exposure', 'temperature', 'muted',
                       'spread', 'areaSpread',
                       'affectDiffuse', 'affectSpecular', 'affectGI', 'shadowEnable',
                       'diffuseContrib', 'reflectionContrib', 'transmissionContrib',
                       'singleScatterContrib', 'multiScatterContrib', 'volumeContrib',
                       'indirectContrib', 'toonDiffuseContrib', 'toonReflectionContrib']
            for attr in _SIMPLE:
                if attr in captured:
                    light_ctx.set_attribute_override(attr, captured[attr], enabled=True)

            # Color (compound stored as three sub-attrs + one enable)
            if 'colorR' in captured:
                light_ctx.set_attribute('colorR', captured['colorR'])
                light_ctx.set_attribute('colorG', captured['colorG'])
                light_ctx.set_attribute('colorB', captured['colorB'])
                light_ctx.set_attribute('colorEnabled', True)

            # Transform attrs (compound groups)
            for group, subs in [('translate', ['translateX', 'translateY', 'translateZ']),
                                 ('rotate',    ['rotateX', 'rotateY', 'rotateZ']),
                                 ('scale',     ['scaleX', 'scaleY', 'scaleZ'])]:
                if subs[0] in captured:
                    for sub in subs:
                        light_ctx.set_attribute(sub, captured[sub])
                    light_ctx.set_attribute('{}Enabled'.format(group), True)
        except Exception as e:
            logger.warning("GafferManager.add_light_to_gaffer: could not capture values for '%s': %s",
                           resolved_shape, e)

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
            light_ctx = CTXLightContextNode.create(
                gaffer_name=child_gaffer.get_gaffer_name(),
                lightName=light_name
            )
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

        # Resolve shape vs transform.
        # Callers may pass either the shape node or its transform parent.
        # We need the SHAPE for attribute queries and the TRANSFORM for translate/rotate/scale.
        if cmds.nodeType(light_shape) == 'transform':
            transform = light_shape
            child_shapes = cmds.listRelatives(light_shape, shapes=True, fullPath=False) or []
            light_shape = child_shapes[0] if child_shapes else None
        else:
            transforms = cmds.listRelatives(light_shape, parent=True, fullPath=True) or []
            transform = transforms[0] if transforms else None

        if light_shape is None:
            return values  # transform with no shape -- nothing to capture

        # Capture intensity -- use renderer-specific attribute name (e.g. RS dome: 'multiplier')
        intensity_attr = get_maya_attr(light_shape, 'intensity') or 'intensity'
        if cmds.attributeQuery(intensity_attr, node=light_shape, exists=True):
            values['intensity'] = cmds.getAttr('{}.{}'.format(light_shape, intensity_attr))

        # Capture exposure -- use renderer-specific attribute name
        exposure_attr = get_maya_attr(light_shape, 'exposure') or 'exposure'
        if cmds.attributeQuery(exposure_attr, node=light_shape, exists=True):
            values['exposure'] = cmds.getAttr('{}.{}'.format(light_shape, exposure_attr))

        # Capture color -- use renderer-specific attribute name
        color_attr = get_maya_attr(light_shape, 'color') or 'color'
        if cmds.attributeQuery(color_attr, node=light_shape, exists=True):
            color = cmds.getAttr('{}.{}'.format(light_shape, color_attr))[0]
            values['colorR'] = color[0]
            values['colorG'] = color[1]
            values['colorB'] = color[2]

        # Capture temperature (if exists)
        temperature_attr = get_maya_attr(light_shape, 'temperature') or 'temperature'
        if cmds.attributeQuery(temperature_attr, node=light_shape, exists=True):
            values['temperature'] = cmds.getAttr('{}.{}'.format(light_shape, temperature_attr))

        # Capture muted state (renderer-specific: RS uses .on, others use transform visibility)
        muted_attr = get_maya_attr(light_shape, 'muted')
        if muted_attr and cmds.attributeQuery(muted_attr, node=light_shape, exists=True):
            on_val = cmds.getAttr('{}.{}'.format(light_shape, muted_attr))
            values['muted'] = not bool(on_val)  # on=0 -> muted=True
        elif transform and cmds.attributeQuery('visibility', node=transform, exists=True):
            vis = cmds.getAttr('{}.visibility'.format(transform))
            values['muted'] = not bool(vis)

        # Capture spread attrs (renderer-specific)
        for gaffer_attr in ('spread', 'areaSpread'):
            maya_attr = get_maya_attr(light_shape, gaffer_attr)
            if maya_attr and cmds.attributeQuery(maya_attr, node=light_shape, exists=True):
                values[gaffer_attr] = cmds.getAttr('{}.{}'.format(light_shape, maya_attr))

        # Capture bool contribution flags (renderer-specific attr names)
        for gaffer_attr in ('affectDiffuse', 'affectSpecular', 'affectGI', 'shadowEnable'):
            maya_attr = get_maya_attr(light_shape, gaffer_attr)
            if maya_attr and cmds.attributeQuery(maya_attr, node=light_shape, exists=True):
                raw = cmds.getAttr('{}.{}'.format(light_shape, maya_attr))
                values[gaffer_attr] = bool(raw)

        # Capture float contribution scales (renderer-specific)
        for gaffer_attr in ('diffuseContrib', 'reflectionContrib', 'transmissionContrib',
                            'singleScatterContrib', 'multiScatterContrib', 'volumeContrib',
                            'indirectContrib', 'toonDiffuseContrib', 'toonReflectionContrib'):
            maya_attr = get_maya_attr(light_shape, gaffer_attr)
            if maya_attr and cmds.attributeQuery(maya_attr, node=light_shape, exists=True):
                values[gaffer_attr] = cmds.getAttr('{}.{}'.format(light_shape, maya_attr))

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

            scale = cmds.getAttr('{}.scale'.format(transform))[0]
            values['scaleX'] = scale[0]
            values['scaleY'] = scale[1]
            values['scaleZ'] = scale[2]

        return values

