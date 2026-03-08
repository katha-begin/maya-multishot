"""
Edit Mode for gaffer-wide light editing with snapshot/diff/restore.

Workflow:
  1. enter()  - snapshot current Maya values for all lights in the gaffer
  2. User edits lights freely in the viewport / attribute editor
  3. commit() - diff current values vs snapshot; store changed attrs as
                gaffer overrides (enabled=True); skip unchanged attrs
     OR
     cancel() - restore snapshot values back to Maya lights without storing
                any overrides

Design:
- Gaffer-wide: all lights in the selected gaffer (direct + inherited)
- No real-time callbacks; pure snapshot diff on exit
- Float comparison uses FLOAT_THRESHOLD to ignore floating-point noise
"""

try:
    import maya.cmds as cmds
except ImportError:
    cmds = None

from .manager import GafferManager

# Minimum float delta to consider an attribute changed
FLOAT_THRESHOLD = 0.0001

# Compound attribute groups: group_name -> [sub_attr, ...]
# The group_name maps to the schema's Enabled flag (e.g. colorEnabled)
COMPOUND_GROUPS = {
    'color':     ['colorR', 'colorG', 'colorB'],
    'translate': ['translateX', 'translateY', 'translateZ'],
    'rotate':    ['rotateX', 'rotateY', 'rotateZ'],
    'scale':     ['scaleX', 'scaleY', 'scaleZ'],
}

# Simple (scalar) attributes tracked in the snapshot
SIMPLE_ATTRS = [
    'intensity', 'exposure', 'temperature', 'muted',
    'spread', 'areaSpread',
    'affectDiffuse', 'affectSpecular', 'affectGI', 'shadowEnable',
    'diffuseContrib', 'reflectionContrib', 'transmissionContrib',
    'singleScatterContrib', 'multiScatterContrib', 'volumeContrib',
    'indirectContrib', 'toonDiffuseContrib', 'toonReflectionContrib',
]


class EditMode(object):
    """Snapshot-diff edit mode manager for a single gaffer.

    Usage:
        mode = EditMode(gaffer)
        mode.enter()          # snapshot
        # ... user edits in Maya viewport ...
        changed = mode.commit()   # diff + store overrides
        # OR
        mode.cancel()         # restore snapshot, discard changes
    """

    def __init__(self, gaffer):
        """Create an EditMode instance for a gaffer.

        Args:
            gaffer (CTXLightGafferNode): Gaffer to manage
        """
        self._gaffer = gaffer
        self._snapshot = {}  # {light_name: {flat_attr: value}}
        self._active = False

    @property
    def is_active(self):
        """bool: True while edit mode is active."""
        return self._active

    def enter(self):
        """Snapshot current Maya values for all lights in the gaffer.

        Captures values from the live Maya scene so we can diff on exit.

        Returns:
            dict: Snapshot data {light_name: {attr: value}}

        Raises:
            RuntimeError: If Maya is not available or already active
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")
        if self._active:
            raise RuntimeError("Edit mode is already active")

        self._snapshot = {}

        lights = GafferManager.get_lights_in_gaffer(self._gaffer, include_inherited=True)
        print("EditMode.enter: found {} lights in gaffer '{}'".format(
            len(lights), self._gaffer.get_gaffer_name()))
        for light_info in lights:
            target = light_info.get('target')
            light_name = light_info.get('name', '')
            if not target:
                print("EditMode.enter: '{}' has no target light (targetLight not connected)".format(light_name))
                continue
            if not cmds.objExists(target):
                print("EditMode.enter: target '{}' for light '{}' does not exist in scene".format(
                    target, light_name))
                continue
            try:
                node_type = cmds.nodeType(target) if cmds.objExists(target) else 'N/A'
                values = GafferManager.capture_light_values(target)
                self._snapshot[light_name] = values
                print("EditMode.enter: snapshotted '{}' target='{}' type='{}' ({} values)".format(
                    light_name, target, node_type, len(values)))
            except Exception as e:
                print("EditMode.enter: failed to capture '{}': {}".format(light_name, e))

        print("EditMode.enter: snapshot complete for {} lights".format(len(self._snapshot)))
        self._active = True
        return self._snapshot

    def commit(self):
        """Diff current Maya values vs snapshot and store changed attrs as overrides.

        Only attributes that changed beyond FLOAT_THRESHOLD are stored.
        Existing overrides for unchanged attributes are left as-is.

        Returns:
            dict: Changed attributes per light:
                {light_name: {group_or_attr: (snapshot_value, current_value)}}

        Raises:
            RuntimeError: If Maya is not available or not in edit mode
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")
        if not self._active:
            raise RuntimeError("Edit mode is not active")

        changed_report = {}

        lights = GafferManager.get_lights_in_gaffer(self._gaffer, include_inherited=True)
        print("EditMode.commit: comparing {} lights against snapshot ({} entries)".format(
            len(lights), len(self._snapshot)))
        for light_info in lights:
            target = light_info.get('target')
            light_name = light_info.get('name', '')
            if not target or not cmds.objExists(target):
                print("EditMode.commit: skipping '{}' (target '{}' not found)".format(light_name, target))
                continue

            if light_name not in self._snapshot:
                print("EditMode.commit: skipping '{}' (no snapshot — was not captured at enter)".format(light_name))
                continue
            snapshot = self._snapshot[light_name]

            try:
                current = GafferManager.capture_light_values(target)
            except Exception as e:
                print("EditMode.commit: failed to capture '{}': {}".format(light_name, e))
                continue

            light_changes = {}

            is_direct = self._is_direct_in_gaffer(light_name)

            # Check compound groups first
            for group, sub_attrs in COMPOUND_GROUPS.items():
                group_changed = False
                for sub in sub_attrs:
                    old_val = snapshot.get(sub)
                    new_val = current.get(sub)
                    if old_val is None or new_val is None:
                        continue
                    if abs(float(new_val) - float(old_val)) > FLOAT_THRESHOLD:
                        group_changed = True
                        break

                if group_changed:
                    old_tuple = tuple(snapshot.get(s, 0.0) for s in sub_attrs)
                    new_tuple = tuple(current.get(s, 0.0) for s in sub_attrs)
                    light_changes[group] = (old_tuple, new_tuple)
                    # Color is always replace — additive RGB delta is not meaningful
                    if group == 'color' or is_direct:
                        self._store_compound_override(light_name, group, sub_attrs, current, mode='replace')
                    else:
                        # Inherited transform: store delta as additive
                        deltas = {s: current.get(s, 0.0) - snapshot.get(s, 0.0) for s in sub_attrs}
                        self._store_compound_override(light_name, group, sub_attrs, deltas, mode='additive')

            # Check simple scalar attributes
            for attr in SIMPLE_ATTRS:
                old_val = snapshot.get(attr)
                new_val = current.get(attr)
                if old_val is None or new_val is None:
                    continue

                if isinstance(old_val, bool) or isinstance(new_val, bool):
                    attr_changed = bool(old_val) != bool(new_val)
                else:
                    try:
                        attr_changed = abs(float(new_val) - float(old_val)) > FLOAT_THRESHOLD
                    except (TypeError, ValueError):
                        attr_changed = old_val != new_val

                if attr_changed:
                    light_changes[attr] = (old_val, new_val)
                    if is_direct or isinstance(new_val, bool):
                        # Direct lights and bool flags always replace
                        self._store_simple_override(light_name, attr, new_val, mode='replace')
                    else:
                        # Inherited: store delta as additive
                        try:
                            delta = float(new_val) - float(old_val)
                        except (TypeError, ValueError):
                            delta = new_val
                        self._store_simple_override(light_name, attr, delta, mode='additive')

            if light_changes:
                changed_report[light_name] = light_changes

        self._active = False
        self._snapshot = {}
        return changed_report

    def cancel(self):
        """Restore snapshot values to Maya lights without storing any overrides.

        Returns:
            int: Number of lights restored

        Raises:
            RuntimeError: If Maya is not available or not in edit mode
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")
        if not self._active:
            raise RuntimeError("Edit mode is not active")

        restored = 0
        lights = GafferManager.get_lights_in_gaffer(self._gaffer, include_inherited=True)

        for light_info in lights:
            target = light_info.get('target')
            light_name = light_info.get('name', '')
            if not target or not cmds.objExists(target):
                continue

            if light_name not in self._snapshot:
                continue
            snapshot = self._snapshot[light_name]

            try:
                self._apply_snapshot_to_light(target, snapshot)
                restored += 1
            except Exception as e:
                print("EditMode.cancel: failed to restore '{}': {}".format(light_name, e))

        self._active = False
        self._snapshot = {}
        return restored

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_direct_in_gaffer(self, light_name):
        """Check if a light has a direct context in this gaffer (not just inherited).

        Args:
            light_name (str): Light name

        Returns:
            bool: True if the light has a direct context in this gaffer
        """
        for ctx in self._gaffer.get_lights():
            if ctx.get_light_name() == light_name:
                return True
        return False

    def _store_simple_override(self, light_name, attr_name, value, mode='replace'):
        """Store a simple attribute override in this gaffer's light context.

        Args:
            light_name (str): Light name
            attr_name (str): Schema attribute name
            value: Value (absolute for replace, delta for additive)
            mode (str): 'replace' or 'additive'
        """
        try:
            ctx = self._get_or_create_light_ctx(light_name)
            if ctx is None:
                return
            ctx.set_attribute(attr_name, value)
            ctx.set_attribute('{}Enabled'.format(attr_name), True)
            ctx.set_override_mode(attr_name, mode)
        except Exception as e:
            print("EditMode: failed to store override {}.{}: {}".format(light_name, attr_name, e))

    def _store_compound_override(self, light_name, group, sub_attrs, values_dict, mode='replace'):
        """Store a compound attribute group override in this gaffer's light context.

        Args:
            light_name (str): Light name
            group (str): Group name ('color', 'translate', etc.)
            sub_attrs (list): Sub-attribute names
            values_dict (dict): Flat dict of values (absolute or deltas)
            mode (str): 'replace' or 'additive'
        """
        try:
            ctx = self._get_or_create_light_ctx(light_name)
            if ctx is None:
                return
            for sub in sub_attrs:
                if sub in values_dict:
                    ctx.set_attribute(sub, values_dict[sub])
            ctx.set_attribute('{}Enabled'.format(group), True)
            ctx.set_override_mode(group, mode)
        except Exception as e:
            print("EditMode: failed to store compound override {}.{}: {}".format(light_name, group, e))

    def _get_or_create_light_ctx(self, light_name):
        """Get or create a light context in this gaffer for the given light.

        Args:
            light_name (str): Light name

        Returns:
            CTXLightContextNode or None
        """
        from ..nodes.wrappers.light_context import CTXLightContextNode

        # Look for existing context in this gaffer (direct only, not inherited)
        for ctx in self._gaffer.get_lights():
            if ctx.get_light_name() == light_name:
                return ctx

        # Not in this gaffer; find target light from parent chain and create override
        target_light = GafferManager._find_light_in_chain(self._gaffer, light_name)
        if target_light is None:
            print("EditMode: light '{}' not found in chain".format(light_name))
            return None

        ctx = CTXLightContextNode.create(
            gaffer_name=self._gaffer.get_gaffer_name(),
            lightName=light_name
        )
        ctx.set_parent_gaffer(self._gaffer)
        ctx.set_target_light(target_light)
        return ctx

    def _apply_snapshot_to_light(self, light_shape, snapshot):
        """Apply snapshot values directly to a Maya light shape.

        Args:
            light_shape (str): Maya light shape node name
            snapshot (dict): Flat attribute dict from capture_light_values
        """
        from ..renderers import get_maya_attr

        # Get transform
        transforms = cmds.listRelatives(light_shape, parent=True, fullPath=True) or []
        transform = transforms[0] if transforms else None

        # Restore simple scalar attrs using duck-typing
        _SIMPLE_DIRECT = {
            'intensity': 'intensity',
            'exposure':  'exposure',
            'temperature': 'temperature',
        }
        for snap_key, maya_attr in _SIMPLE_DIRECT.items():
            if snap_key in snapshot:
                if cmds.attributeQuery(maya_attr, node=light_shape, exists=True):
                    cmds.setAttr('{}.{}'.format(light_shape, maya_attr), snapshot[snap_key])

        # Restore color
        if 'colorR' in snapshot and cmds.attributeQuery('color', node=light_shape, exists=True):
            cmds.setAttr(
                '{}.color'.format(light_shape),
                snapshot['colorR'], snapshot['colorG'], snapshot['colorB'],
                type='double3'
            )

        # Restore muted (via visibility on shape's transform)
        if 'muted' in snapshot and transform:
            # muted=True means hidden
            pass  # Muted state is complex; skip restore to avoid side effects

        # Restore spread
        if 'spread' in snapshot:
            spread_attr = get_maya_attr(light_shape, 'spread')
            if spread_attr and cmds.attributeQuery(spread_attr, node=light_shape, exists=True):
                cmds.setAttr('{}.{}'.format(light_shape, spread_attr), snapshot['spread'])

        # Restore contribution flags
        for gaffer_attr in ('affectDiffuse', 'affectSpecular', 'affectGI', 'shadowEnable'):
            if gaffer_attr in snapshot:
                maya_attr = get_maya_attr(light_shape, gaffer_attr)
                if maya_attr and cmds.attributeQuery(maya_attr, node=light_shape, exists=True):
                    raw = snapshot[gaffer_attr]
                    attr_type = cmds.getAttr('{}.{}'.format(light_shape, maya_attr), type=True)
                    write_val = (1.0 if raw else 0.0) if attr_type in ('double', 'float') else bool(raw)
                    cmds.setAttr('{}.{}'.format(light_shape, maya_attr), write_val)

        # Restore transform
        if transform:
            if 'translateX' in snapshot:
                cmds.setAttr(
                    '{}.translate'.format(transform),
                    snapshot['translateX'], snapshot['translateY'], snapshot['translateZ'],
                    type='double3'
                )
            if 'rotateX' in snapshot:
                cmds.setAttr(
                    '{}.rotate'.format(transform),
                    snapshot['rotateX'], snapshot['rotateY'], snapshot['rotateZ'],
                    type='double3'
                )
            if 'scaleX' in snapshot:
                cmds.setAttr(
                    '{}.scale'.format(transform),
                    snapshot['scaleX'], snapshot['scaleY'], snapshot['scaleZ'],
                    type='double3'
                )
