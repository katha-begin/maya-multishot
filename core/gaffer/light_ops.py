"""
Light Operations for applying and syncing gaffer values.

Apply order (shot switch):
  1. Restore originals from CTX_LightOriginals (persistent baseline)
  2. Walk chain root-first (master -> seq -> shot)
  3. For each gaffer, apply enabled overrides:
     - mode='replace': set absolute value
     - mode='additive': read current Maya value, add delta
"""

try:
    import maya.cmds as cmds
except ImportError:
    cmds = None

from ..nodes.wrappers.gaffer import CTXLightGafferNode
from ..nodes.wrappers.light_context import CTXLightContextNode
from .resolver import AttributeResolver
from .manager import GafferManager
from ..renderers import get_maya_attr


class LightOperations(object):
    """Operations for applying and syncing light values."""

    # ------------------------------------------------------------------
    # Public: apply gaffer chain to Maya scene
    # ------------------------------------------------------------------

    @staticmethod
    def apply_gaffer_to_all_lights(gaffer):
        """Apply the full gaffer chain to all lights.

        Always starts from the persisted originals so shot switching never
        bleeds values from a previous shot.

        Apply order: restore originals -> master -> seq -> shot (root first).

        Args:
            gaffer (CTXLightGafferNode or str): Most-specific gaffer for this shot

        Returns:
            dict: {light_name: True/False} per-light success

        Raises:
            RuntimeError: If Maya is not available
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        if isinstance(gaffer, str):
            gaffer = CTXLightGafferNode(gaffer)

        # Build chain root-first (master -> ... -> shot)
        chain = list(reversed(gaffer.build_chain()))

        # Collect all target lights across the entire chain
        seen_targets = {}  # light_name -> target_shape
        for g in chain:
            for lc in g.get_lights():
                name = lc.get_light_name()
                if name not in seen_targets:
                    target = lc.get_target_light()
                    if target:
                        seen_targets[name] = target

        # Step 1: Restore originals
        LightOperations._restore_originals_for_targets(seen_targets.values())

        # Step 2: Apply each gaffer level in order
        results = {}
        for gaffer_node in chain:
            for light_ctx in gaffer_node.get_lights():
                light_name = light_ctx.get_light_name()
                target = light_ctx.get_target_light()
                if not target or not cmds.objExists(target):
                    continue
                try:
                    LightOperations._apply_light_ctx_to_maya(light_ctx, target)
                    results[light_name] = True
                except Exception as e:
                    print("Warning: Failed to apply {} from gaffer '{}': {}".format(
                        light_name, gaffer_node.get_gaffer_name(), e))
                    results[light_name] = False

        return results

    @staticmethod
    def restore_originals():
        """Restore all lights to their stored original values.

        Called when switching to a shot with no gaffer.

        Returns:
            int: Number of lights restored
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        try:
            from ..nodes.wrappers.light_originals import CTXLightOriginalsNode
            originals_node = CTXLightOriginalsNode.get_or_create()
            originals = originals_node.get_all_originals()
        except Exception as e:
            print("LightOperations.restore_originals: could not load originals: {}".format(e))
            return 0

        restored = 0
        for light_shape, values in originals.items():
            if cmds.objExists(light_shape):
                try:
                    LightOperations._apply_values_to_maya(light_shape, values)
                    restored += 1
                except Exception as e:
                    print("Warning: Failed to restore {}: {}".format(light_shape, e))

        return restored

    # ------------------------------------------------------------------
    # Public: sync from Maya back into gaffer
    # ------------------------------------------------------------------

    @staticmethod
    def sync_light_from_maya(gaffer, light_name, attributes=None):
        """Update light context from current Maya light values.

        Args:
            gaffer (CTXLightGafferNode or str): Gaffer containing the light
            light_name (str): Light name to sync
            attributes (list, optional): Specific attributes to sync.

        Returns:
            dict: Synced attributes and their new values

        Raises:
            RuntimeError: If Maya is not available
            ValueError: If light not found in gaffer
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        if isinstance(gaffer, str):
            gaffer = CTXLightGafferNode(gaffer)

        light_ctx = None
        for ctx in gaffer.get_lights():
            if ctx.get_light_name() == light_name:
                light_ctx = ctx
                break

        if light_ctx is None:
            raise ValueError("Light '{}' not found in gaffer '{}'".format(
                light_name, gaffer.get_gaffer_name()))

        target_light = light_ctx.get_target_light()
        if not cmds.objExists(target_light):
            raise ValueError("Target light '{}' does not exist in scene".format(target_light))

        captured = GafferManager.capture_light_values(target_light)
        enabled_attrs = light_ctx.get_enabled_attributes()

        if attributes:
            enabled_attrs = [attr for attr in enabled_attrs if attr in attributes]

        synced = {}

        for attr_name in enabled_attrs:
            if attr_name == 'color':
                if 'colorR' in captured:
                    light_ctx.set_attribute('colorR', captured['colorR'])
                    light_ctx.set_attribute('colorG', captured['colorG'])
                    light_ctx.set_attribute('colorB', captured['colorB'])
                    synced['color'] = (captured['colorR'], captured['colorG'], captured['colorB'])
            elif attr_name in ('translate', 'rotate', 'scale'):
                xk = '{}X'.format(attr_name)
                if xk in captured:
                    for axis in ('X', 'Y', 'Z'):
                        k = '{}{}'.format(attr_name, axis)
                        light_ctx.set_attribute(k, captured[k])
                    synced[attr_name] = (
                        captured['{}X'.format(attr_name)],
                        captured['{}Y'.format(attr_name)],
                        captured['{}Z'.format(attr_name)],
                    )
            else:
                if attr_name in captured:
                    light_ctx.set_attribute(attr_name, captured[attr_name])
                    synced[attr_name] = captured[attr_name]

        return synced

    @staticmethod
    def sync_all_lights(gaffer, attributes=None):
        """Sync all lights in gaffer from Maya scene.

        Args:
            gaffer (CTXLightGafferNode or str): Gaffer to sync
            attributes (list, optional): Specific attributes to sync.

        Returns:
            dict: {light_name: synced_attrs}
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        if isinstance(gaffer, str):
            gaffer = CTXLightGafferNode(gaffer)

        results = {}
        for light_ctx in gaffer.get_lights():
            light_name = light_ctx.get_light_name()
            try:
                synced = LightOperations.sync_light_from_maya(gaffer, light_name, attributes)
                results[light_name] = synced
            except Exception as e:
                print("Warning: Failed to sync {}: {}".format(light_name, e))
                results[light_name] = {'error': str(e)}

        return results

    # ------------------------------------------------------------------
    # Private: per-light-context apply (handles replace + additive)
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_light_ctx_to_maya(light_ctx, light_shape):
        """Apply all enabled attributes from a light context to a Maya light.

        Reads the override mode per attribute group:
          - 'replace'  : set the absolute stored value
          - 'additive' : read current Maya value and add the stored delta

        Args:
            light_ctx (CTXLightContextNode): Light context with override values
            light_shape (str): Maya light node (shape or transform)
        """
        # Resolve shape vs transform
        if cmds.nodeType(light_shape) == 'transform':
            transform = light_shape
            child_shapes = cmds.listRelatives(light_shape, shapes=True, fullPath=False) or []
            shape = child_shapes[0] if child_shapes else light_shape
        else:
            transforms = cmds.listRelatives(light_shape, parent=True, fullPath=True) or []
            transform = transforms[0] if transforms else None
            shape = light_shape

        def _apply_scalar(attr_val, maya_attr_name, mode):
            if not cmds.attributeQuery(maya_attr_name, node=shape, exists=True):
                return
            if mode == 'additive':
                current = cmds.getAttr('{}.{}'.format(shape, maya_attr_name))
                attr_val = current + attr_val
            cmds.setAttr('{}.{}'.format(shape, maya_attr_name), attr_val)

        # Intensity
        if light_ctx.get_attribute('intensityEnabled'):
            mode = light_ctx.get_override_mode('intensity')
            maya_attr = get_maya_attr(shape, 'intensity') or 'intensity'
            _apply_scalar(light_ctx.get_attribute('intensity'), maya_attr, mode)

        # Exposure
        if light_ctx.get_attribute('exposureEnabled'):
            mode = light_ctx.get_override_mode('exposure')
            maya_attr = get_maya_attr(shape, 'exposure') or 'exposure'
            _apply_scalar(light_ctx.get_attribute('exposure'), maya_attr, mode)

        # Temperature
        if light_ctx.get_attribute('temperatureEnabled'):
            mode = light_ctx.get_override_mode('temperature')
            maya_attr = get_maya_attr(shape, 'temperature') or 'temperature'
            _apply_scalar(light_ctx.get_attribute('temperature'), maya_attr, mode)

        # Color (replace only — additive RGB is not meaningful)
        if light_ctx.get_attribute('colorEnabled'):
            r = light_ctx.get_attribute('colorR')
            g = light_ctx.get_attribute('colorG')
            b = light_ctx.get_attribute('colorB')
            color_attr = get_maya_attr(shape, 'color') or 'color'
            if cmds.attributeQuery(color_attr, node=shape, exists=True):
                cmds.setAttr('{}.{}'.format(shape, color_attr), r, g, b, type='double3')

        # Muted — set renderer-specific attr (RS: .on) AND transform visibility
        if light_ctx.get_attribute('mutedEnabled'):
            muted = light_ctx.get_attribute('muted')
            muted_attr = get_maya_attr(shape, 'muted')
            if muted_attr and cmds.attributeQuery(muted_attr, node=shape, exists=True):
                cmds.setAttr('{}.{}'.format(shape, muted_attr), 0 if muted else 1)
            if transform and cmds.attributeQuery('visibility', node=transform, exists=True):
                cmds.setAttr('{}.visibility'.format(transform), not muted)

        # Spread attrs (renderer-specific float scalars)
        for gaffer_attr in ('spread', 'areaSpread'):
            if light_ctx.get_attribute('{}Enabled'.format(gaffer_attr)):
                mode = light_ctx.get_override_mode(gaffer_attr)
                maya_attr = get_maya_attr(shape, gaffer_attr)
                if maya_attr and cmds.attributeQuery(maya_attr, node=shape, exists=True):
                    val = light_ctx.get_attribute(gaffer_attr)
                    if mode == 'additive':
                        val = cmds.getAttr('{}.{}'.format(shape, maya_attr)) + val
                    cmds.setAttr('{}.{}'.format(shape, maya_attr), val)

        # Bool contribution flags (always replace)
        for flag in ('affectDiffuse', 'affectSpecular', 'affectGI', 'shadowEnable'):
            if light_ctx.get_attribute('{}Enabled'.format(flag)):
                maya_attr = get_maya_attr(shape, flag)
                if maya_attr and cmds.attributeQuery(maya_attr, node=shape, exists=True):
                    val = light_ctx.get_attribute(flag)
                    attr_type = cmds.getAttr('{}.{}'.format(shape, maya_attr), type=True)
                    write_val = (1.0 if val else 0.0) if attr_type in ('double', 'float') else bool(val)
                    cmds.setAttr('{}.{}'.format(shape, maya_attr), write_val)

        # Float contribution scales (replace or additive)
        for gaffer_attr in ('diffuseContrib', 'reflectionContrib', 'transmissionContrib',
                            'singleScatterContrib', 'multiScatterContrib', 'volumeContrib',
                            'indirectContrib', 'toonDiffuseContrib', 'toonReflectionContrib'):
            if light_ctx.get_attribute('{}Enabled'.format(gaffer_attr)):
                mode = light_ctx.get_override_mode(gaffer_attr)
                maya_attr = get_maya_attr(shape, gaffer_attr)
                if maya_attr and cmds.attributeQuery(maya_attr, node=shape, exists=True):
                    val = light_ctx.get_attribute(gaffer_attr)
                    if mode == 'additive':
                        val = cmds.getAttr('{}.{}'.format(shape, maya_attr)) + val
                    cmds.setAttr('{}.{}'.format(shape, maya_attr), val)

        # Transforms
        if transform:
            if light_ctx.get_attribute('translateEnabled'):
                mode = light_ctx.get_override_mode('translate')
                tx = light_ctx.get_attribute('translateX')
                ty = light_ctx.get_attribute('translateY')
                tz = light_ctx.get_attribute('translateZ')
                if mode == 'additive':
                    curr = cmds.getAttr('{}.translate'.format(transform))[0]
                    tx, ty, tz = curr[0] + tx, curr[1] + ty, curr[2] + tz
                cmds.setAttr('{}.translate'.format(transform), tx, ty, tz, type='double3')

            if light_ctx.get_attribute('rotateEnabled'):
                mode = light_ctx.get_override_mode('rotate')
                rx = light_ctx.get_attribute('rotateX')
                ry = light_ctx.get_attribute('rotateY')
                rz = light_ctx.get_attribute('rotateZ')
                if mode == 'additive':
                    curr = cmds.getAttr('{}.rotate'.format(transform))[0]
                    rx, ry, rz = curr[0] + rx, curr[1] + ry, curr[2] + rz
                cmds.setAttr('{}.rotate'.format(transform), rx, ry, rz, type='double3')

            if light_ctx.get_attribute('scaleEnabled'):
                mode = light_ctx.get_override_mode('scale')
                sx = light_ctx.get_attribute('scaleX')
                sy = light_ctx.get_attribute('scaleY')
                sz = light_ctx.get_attribute('scaleZ')
                if mode == 'additive':
                    curr = cmds.getAttr('{}.scale'.format(transform))[0]
                    sx, sy, sz = curr[0] + sx, curr[1] + sy, curr[2] + sz
                cmds.setAttr('{}.scale'.format(transform), sx, sy, sz, type='double3')

    @staticmethod
    def _restore_originals_for_targets(target_shapes):
        """Restore stored original values for a set of light shapes.

        Args:
            target_shapes (iterable): Maya light shape or transform node names
        """
        try:
            from ..nodes.wrappers.light_originals import CTXLightOriginalsNode
            originals_node = CTXLightOriginalsNode.get_or_create()
        except Exception as e:
            print("LightOperations._restore_originals_for_targets: {}".format(e))
            return

        for target in target_shapes:
            if not target or not cmds.objExists(target):
                continue
            values = originals_node.get_light_values(target)
            if values:
                try:
                    LightOperations._apply_values_to_maya(target, values)
                except Exception as e:
                    print("Warning: Failed to restore originals for '{}': {}".format(target, e))

    @staticmethod
    def _apply_values_to_maya(light_shape, values):
        """Apply a flat values dict directly to a Maya light (no gaffer logic).

        Used for restoring originals.

        Args:
            light_shape (str): Maya light shape or transform
            values (dict): Flat values from capture_light_values
        """
        if cmds.nodeType(light_shape) == 'transform':
            transform = light_shape
            child_shapes = cmds.listRelatives(light_shape, shapes=True, fullPath=False) or []
            shape = child_shapes[0] if child_shapes else None
        else:
            transforms = cmds.listRelatives(light_shape, parent=True, fullPath=True) or []
            transform = transforms[0] if transforms else None
            shape = light_shape

        if shape:
            if 'intensity' in values and cmds.attributeQuery('intensity', node=shape, exists=True):
                cmds.setAttr('{}.intensity'.format(shape), values['intensity'])

            if 'exposure' in values and cmds.attributeQuery('exposure', node=shape, exists=True):
                cmds.setAttr('{}.exposure'.format(shape), values['exposure'])

            if 'temperature' in values and cmds.attributeQuery('temperature', node=shape, exists=True):
                cmds.setAttr('{}.temperature'.format(shape), values['temperature'])

            if 'colorR' in values and cmds.attributeQuery('color', node=shape, exists=True):
                cmds.setAttr('{}.color'.format(shape),
                             values['colorR'], values['colorG'], values['colorB'],
                             type='double3')

            # Muted — shape attribute (RS: .on)
            if 'muted' in values:
                muted_attr = get_maya_attr(shape, 'muted')
                if muted_attr and cmds.attributeQuery(muted_attr, node=shape, exists=True):
                    cmds.setAttr('{}.{}'.format(shape, muted_attr), 0 if values['muted'] else 1)

            # Spread attrs
            for gaffer_attr in ('spread', 'areaSpread'):
                if gaffer_attr in values:
                    maya_attr = get_maya_attr(shape, gaffer_attr)
                    if maya_attr and cmds.attributeQuery(maya_attr, node=shape, exists=True):
                        cmds.setAttr('{}.{}'.format(shape, maya_attr), values[gaffer_attr])

            # Bool contribution flags
            for flag in ('affectDiffuse', 'affectSpecular', 'affectGI', 'shadowEnable'):
                if flag in values:
                    maya_attr = get_maya_attr(shape, flag)
                    if maya_attr and cmds.attributeQuery(maya_attr, node=shape, exists=True):
                        raw = values[flag]
                        attr_type = cmds.getAttr('{}.{}'.format(shape, maya_attr), type=True)
                        write_val = (1.0 if raw else 0.0) if attr_type in ('double', 'float') else bool(raw)
                        cmds.setAttr('{}.{}'.format(shape, maya_attr), write_val)

            # Float contribution scales
            for gaffer_attr in ('diffuseContrib', 'reflectionContrib', 'transmissionContrib',
                                'singleScatterContrib', 'multiScatterContrib', 'volumeContrib',
                                'indirectContrib', 'toonDiffuseContrib', 'toonReflectionContrib'):
                if gaffer_attr in values:
                    maya_attr = get_maya_attr(shape, gaffer_attr)
                    if maya_attr and cmds.attributeQuery(maya_attr, node=shape, exists=True):
                        cmds.setAttr('{}.{}'.format(shape, maya_attr), values[gaffer_attr])

        if transform:
            # Muted — transform visibility (both RS and non-RS lights)
            if 'muted' in values and cmds.attributeQuery('visibility', node=transform, exists=True):
                cmds.setAttr('{}.visibility'.format(transform), not values['muted'])

            if 'translateX' in values:
                cmds.setAttr('{}.translate'.format(transform),
                             values['translateX'], values['translateY'], values['translateZ'],
                             type='double3')
            if 'rotateX' in values:
                cmds.setAttr('{}.rotate'.format(transform),
                             values['rotateX'], values['rotateY'], values['rotateZ'],
                             type='double3')
            if 'scaleX' in values:
                cmds.setAttr('{}.scale'.format(transform),
                             values['scaleX'], values['scaleY'], values['scaleZ'],
                             type='double3')

    # ------------------------------------------------------------------
    # Legacy single-light apply (kept for backward compatibility)
    # ------------------------------------------------------------------

    @staticmethod
    def apply_gaffer_to_light(gaffer, light_name):
        """Apply resolved gaffer values to a single Maya light.

        Uses the full chain apply logic. Kept for backward compatibility.

        Args:
            gaffer (CTXLightGafferNode or str): Gaffer to resolve from
            light_name (str): Light name to apply to

        Returns:
            dict: Applied attributes
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        if isinstance(gaffer, str):
            gaffer = CTXLightGafferNode(gaffer)

        target_light = GafferManager._find_light_in_chain(gaffer, light_name)
        if target_light is None:
            raise ValueError("Light '{}' not found in gaffer chain".format(light_name))

        if not cmds.objExists(target_light):
            raise ValueError("Target light '{}' does not exist in scene".format(target_light))

        chain = list(reversed(gaffer.build_chain()))

        LightOperations._restore_originals_for_targets([target_light])

        for gaffer_node in chain:
            for light_ctx in gaffer_node.get_lights():
                if light_ctx.get_light_name() == light_name:
                    LightOperations._apply_light_ctx_to_maya(light_ctx, target_light)

        resolved = AttributeResolver.resolve_all_attributes(gaffer, light_name)
        return {k: v['value'] for k, v in resolved.items()}
