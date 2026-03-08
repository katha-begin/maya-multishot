"""
Wrapper class for CTX_LightContext node.

Provides high-level API for light context operations including:
- Creating light contexts
- Managing attribute overrides
- Querying enabled attributes
- Connecting to target lights
"""

from __future__ import absolute_import

import re

try:
    import maya.cmds as cmds
except ImportError:
    cmds = None

from ..base import NodeWrapper
from ..schemas.light_context import CTXLightContextSchema


class CTXLightContextNode(NodeWrapper):
    """Wrapper for CTX_LightContext node.
    
    Provides high-level API for light attribute management with per-attribute overrides.
    """
    
    SCHEMA = CTXLightContextSchema

    @classmethod
    def create(cls, gaffer_name='', **kwargs):
        """Create light context node with descriptive naming.

        Node name format: CTX_LightCtx_{gaffer_name}_{light_name}
        Example: CTX_LightCtx_Master_keyLight

        Args:
            gaffer_name (str): Owning gaffer name (for node naming only)
            **kwargs: Schema attribute values (lightName, etc.)

        Returns:
            CTXLightContextNode: New instance
        """
        instance = super(CTXLightContextNode, cls).create(**kwargs)

        light_name = kwargs.get('lightName', '')
        if gaffer_name and light_name:
            safe_g = re.sub(r'[^A-Za-z0-9_]', '_', gaffer_name)
            safe_l = re.sub(r'[^A-Za-z0-9_]', '_', light_name)
            desired = 'CTX_LightCtx_{}_{}'.format(safe_g, safe_l)
            try:
                new_name = cmds.rename(instance.node_name, desired)
                instance.node_name = new_name
            except Exception:
                pass

        return instance

    def set_override_mode(self, attr_name, mode):
        """Set the override mode for an attribute.

        Args:
            attr_name (str): Attribute group name (e.g. 'intensity', 'translate')
            mode (str): 'replace' or 'additive'
        """
        mode_attr = '{}Mode'.format(attr_name)
        if self.schema and mode_attr in self.schema.ATTRIBUTES:
            self.set_attribute(mode_attr, mode)

    def get_override_mode(self, attr_name):
        """Get the override mode for an attribute.

        Args:
            attr_name (str): Attribute group name

        Returns:
            str: 'replace' or 'additive' (defaults to 'replace')
        """
        mode_attr = '{}Mode'.format(attr_name)
        if self.schema and mode_attr in self.schema.ATTRIBUTES:
            val = self.get_attribute(mode_attr)
            return val if val in ('replace', 'additive') else 'replace'
        return 'replace'

    def get_parent_gaffer(self):
        """Get owning gaffer using unidirectional pattern.

        Queries: LightContext.message → Gaffer.lights[i]
        Uses destination=True to traverse from child to parent.

        Returns:
            CTXLightGafferNode or None: Parent gaffer wrapper
        """
        if cmds is None:
            return None

        from .gaffer import CTXLightGafferNode

        # Query where light_context.message is connected TO (destination=True)
        connections = cmds.listConnections(
            "{}.message".format(self.node_name),
            source=False,
            destination=True,
            type='network',
            plugs=False
        ) or []

        # Filter for CTX_LightGaffer nodes
        for conn in connections:
            if cmds.attributeQuery('ctx_type', node=conn, exists=True):
                node_type = cmds.getAttr('{}.ctx_type'.format(conn))
                if node_type == 'CTX_LightGaffer':
                    return CTXLightGafferNode(conn)

        return None
    
    def set_parent_gaffer(self, gaffer):
        """Set owning gaffer using unidirectional pattern.

        Creates ONE connection: LightContext.message → Gaffer.lights[i]

        Args:
            gaffer (CTXLightGafferNode or str): Gaffer wrapper or node name
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        gaffer_node = gaffer if isinstance(gaffer, str) else str(gaffer.node_name)

        if not cmds.objExists(gaffer_node):
            raise RuntimeError("Gaffer node does not exist: '{}'".format(gaffer_node))

        # Unidirectional connection: light_context.message → gaffer.lights[i]
        # Parent (gaffer) owns children (light contexts)
        cmds.connectAttr(
            "{}.message".format(self.node_name),
            "{}.lights".format(gaffer_node),
            nextAvailable=True
        )
    
    def get_target_light(self):
        """Get Maya light shape node.

        The connection is: light_shape.message → light_ctx.targetLight
        So targetLight is the DESTINATION/input; query source=True to find
        what feeds into it (the light shape).

        Returns:
            str or None: Light shape node name
        """
        if cmds is None:
            return None

        connections = cmds.listConnections(
            "{}.targetLight".format(self.node_name),
            source=True,
            destination=False,
            plugs=False
        )

        return connections[0] if connections else None
    
    def set_target_light(self, light_node):
        """Set target Maya light shape.

        Normalizes the input to a light shape node. If a transform is passed,
        the first child shape is used. This ensures targetLight always stores
        the shape regardless of what the caller provides.

        Args:
            light_node (str): Maya light node (shape or transform)

        Raises:
            RuntimeError: If Maya is not available or no shape can be resolved
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        # Normalize: if a transform is passed, resolve to its light shape child
        node_type = cmds.nodeType(light_node) if cmds.objExists(light_node) else None
        if node_type == 'transform':
            child_shapes = cmds.listRelatives(light_node, shapes=True, fullPath=False) or []
            if not child_shapes:
                # Try descendants (light inside a group)
                child_shapes = cmds.listRelatives(
                    light_node, shapes=True, fullPath=False, allDescendants=True) or []
            if child_shapes:
                light_node = child_shapes[0]
            # If still no shape found, fall through and connect whatever was passed

        cmds.connectAttr(
            "{}.message".format(light_node),
            "{}.targetLight".format(self.node_name),
            force=True
        )
    
    def get_enabled_attributes(self):
        """Get list of attributes that are overridden (enabled) in this context.
        
        Returns:
            list: List of attribute names that are enabled
        """
        enabled_attrs = []
        
        # Check each enabled flag
        enabled_flags = [
            ('intensity', 'intensityEnabled'),
            ('exposure', 'exposureEnabled'),
            ('color', 'colorEnabled'),
            ('temperature', 'temperatureEnabled'),
            ('muted', 'mutedEnabled'),
            ('translate', 'translateEnabled'),
            ('rotate', 'rotateEnabled'),
            ('scale', 'scaleEnabled'),
            ('spread', 'spreadEnabled'),
            ('affectDiffuse', 'affectDiffuseEnabled'),
            ('affectSpecular', 'affectSpecularEnabled'),
            ('affectGI', 'affectGIEnabled'),
            ('shadowEnable', 'shadowEnableEnabled'),
        ]
        
        for attr_name, flag_name in enabled_flags:
            if self.get_attribute(flag_name):
                enabled_attrs.append(attr_name)
        
        return enabled_attrs
    
    def set_attribute_override(self, attr_name, value, enabled=True):
        """Set attribute value and enable override.
        
        Args:
            attr_name (str): Attribute name (e.g., 'intensity', 'exposure')
            value: Attribute value
            enabled (bool): Whether to enable the override
        """
        # Set the value
        self.set_attribute(attr_name, value)
        
        # Enable the override flag
        flag_name = "{}Enabled".format(attr_name)
        self.set_attribute(flag_name, enabled)
    
    def get_spread(self):
        """Get spread / cone angle value.

        Returns:
            float: Spread value
        """
        return self.get_attribute('spread')

    def get_scale(self):
        """Get scale as (X, Y, Z) tuple.

        Returns:
            tuple: (scaleX, scaleY, scaleZ)
        """
        return (
            self.get_attribute('scaleX'),
            self.get_attribute('scaleY'),
            self.get_attribute('scaleZ'),
        )

    def get_affect_diffuse(self):
        """Get affectDiffuse flag.

        Returns:
            bool: True if light affects diffuse
        """
        return self.get_attribute('affectDiffuse')

    def get_affect_specular(self):
        """Get affectSpecular flag.

        Returns:
            bool: True if light affects specular
        """
        return self.get_attribute('affectSpecular')

    def get_affect_gi(self):
        """Get affectGI flag.

        Returns:
            bool: True if light contributes to GI
        """
        return self.get_attribute('affectGI')

    def get_shadow_enable(self):
        """Get shadowEnable flag.

        Returns:
            bool: True if light casts shadows
        """
        return self.get_attribute('shadowEnable')

    def get_light_name(self):
        """Get the light name.

        Returns:
            str: Light name
        """
        return self.get_attribute('lightName')

    @staticmethod
    def list_all():
        """List all CTX_LightContext nodes in scene.

        Returns:
            list: List of CTXLightContextNode wrappers
        """
        if cmds is None:
            return []

        light_contexts = []
        all_nodes = cmds.ls(type='network')

        for node in all_nodes:
            if cmds.attributeQuery('ctx_type', node=node, exists=True):
                node_type = cmds.getAttr('{}.ctx_type'.format(node))
                if node_type == 'CTX_LightContext':
                    light_contexts.append(CTXLightContextNode(node))

        return light_contexts

