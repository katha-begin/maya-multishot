"""
Wrapper class for CTX_LightContext node.

Provides high-level API for light context operations including:
- Creating light contexts
- Managing attribute overrides
- Querying enabled attributes
- Connecting to target lights
"""

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
    
    def get_parent_gaffer(self):
        """Get owning gaffer.
        
        Returns:
            CTXLightGafferNode or None: Parent gaffer wrapper
        """
        if cmds is None:
            return None
        
        from .gaffer import CTXLightGafferNode
        
        connections = cmds.listConnections(
            "{}.parentGaffer".format(self.node_name),
            source=True,
            destination=False,
            plugs=False
        )
        
        if connections:
            return CTXLightGafferNode(connections[0])
        
        return None
    
    def set_parent_gaffer(self, gaffer):
        """Set owning gaffer.
        
        Args:
            gaffer (CTXLightGafferNode or str): Gaffer wrapper or node name
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")
        
        from .gaffer import CTXLightGafferNode
        
        gaffer_node = gaffer.node_name if isinstance(gaffer, CTXLightGafferNode) else gaffer
        
        # Connect to gaffer
        cmds.connectAttr(
            "{}.message".format(gaffer_node),
            "{}.parentGaffer".format(self.node_name),
            force=True
        )
        
        # Also connect to gaffer's lights array
        cmds.connectAttr(
            "{}.message".format(self.node_name),
            "{}.lights".format(gaffer_node),
            nextAvailable=True
        )
    
    def get_target_light(self):
        """Get Maya light shape node.
        
        Returns:
            str or None: Light shape node name
        """
        if cmds is None:
            return None
        
        connections = cmds.listConnections(
            "{}.targetLight".format(self.node_name),
            source=False,
            destination=True,
            plugs=False
        )
        
        return connections[0] if connections else None
    
    def set_target_light(self, light_shape):
        """Set target Maya light shape.
        
        Args:
            light_shape (str): Light shape node name
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")
        
        cmds.connectAttr(
            "{}.message".format(light_shape),
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
    
    def get_light_name(self):
        """Get the light name.
        
        Returns:
            str: Light name
        """
        return self.get_attribute('lightName')

