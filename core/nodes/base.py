"""
Base classes for schema-based node system.

This module provides the foundation for declarative node definitions:
- NodeSchema: Declarative node structure definition
- NodeFactory: Creates Maya nodes from schemas
- NodeWrapper: High-level API for node operations
"""

try:
    import maya.cmds as cmds
except ImportError:
    # Allow import outside Maya for testing
    cmds = None


class _NodeSchemaMeta(type):
    """Metaclass for NodeSchema that merges LOCK_ATTRIBUTES from mixins.

    When a schema class is created, any LOCK_ATTRIBUTES dict found on mixin
    classes in the MRO is merged into the schema's ATTRIBUTES dict.  This
    allows LockSchemaMixin to inject lock fields without requiring each
    schema subclass to manually copy the entries.
    """

    def __new__(mcs, name, bases, namespace):
        cls = super(_NodeSchemaMeta, mcs).__new__(mcs, name, bases, namespace)

        # Collect LOCK_ATTRIBUTES from every class in the MRO that defines it,
        # but only when the class itself declares ATTRIBUTES (i.e. it is a
        # concrete schema, not NodeSchema or a mixin base).
        if 'ATTRIBUTES' in namespace:
            merged = dict(cls.ATTRIBUTES)
            for base in cls.__mro__:
                lock_attrs = base.__dict__.get('LOCK_ATTRIBUTES')
                if lock_attrs:
                    for attr_name, attr_def in lock_attrs.items():
                        if attr_name not in merged:
                            merged[attr_name] = attr_def
            cls.ATTRIBUTES = merged

        return cls


class NodeSchema(object, metaclass=_NodeSchemaMeta):
    """Base class for node schema definitions.

    Subclasses should define:
    - NODE_TYPE: Maya node type (e.g., 'network')
    - NODE_PREFIX: Node name prefix (e.g., 'CTX_Asset')
    - CATEGORY: Category for organization
    - DESCRIPTION: Human-readable description
    - ATTRIBUTES: Dict of attribute definitions
    - CONNECTIONS: Dict of connection definitions
    """

    # Override in subclasses
    NODE_TYPE = None          # Maya node type (e.g., 'network')
    NODE_PREFIX = None        # Node name prefix (e.g., 'CTX_Asset')
    CATEGORY = None           # Category for organization
    DESCRIPTION = None        # Human-readable description

    ATTRIBUTES = {}           # Attribute definitions
    CONNECTIONS = {}          # Connection definitions
    
    def validate(self):
        """Validate schema definition.
        
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If schema is invalid
        """
        if not self.NODE_TYPE:
            raise ValueError("NODE_TYPE must be defined")
        if not self.NODE_PREFIX:
            raise ValueError("NODE_PREFIX must be defined")
        
        # Validate attributes
        for attr_name, attr_def in self.ATTRIBUTES.items():
            if 'type' not in attr_def:
                raise ValueError("Attribute '{}' missing 'type'".format(attr_name))
        
        return True
    
    def get_graph_ports(self):
        """Generate NodeGraphQt port definitions from schema.
        
        Returns:
            dict: {port_name: port_config}
        """
        ports = {}
        
        # Input ports from connections
        for conn_name, conn_def in self.CONNECTIONS.items():
            if conn_def.get('direction') == 'input':
                ports[conn_name] = {
                    'type': 'input',
                    'multi': conn_def.get('multi', False),
                    'accepts': conn_def.get('accepts', [])
                }
        
        # Output ports from connections
        for conn_name, conn_def in self.CONNECTIONS.items():
            if conn_def.get('direction') == 'output':
                ports[conn_name] = {
                    'type': 'output',
                    'multi': conn_def.get('multi', False)
                }
        
        return ports


class NodeFactory(object):
    """Factory for creating Maya nodes from schemas."""
    
    @staticmethod
    def create_from_schema(schema, **kwargs):
        """Create Maya node from schema definition.
        
        Args:
            schema (NodeSchema): Schema instance
            **kwargs: Initial attribute values
            
        Returns:
            str: Created node name
            
        Raises:
            ValueError: If schema is invalid
            RuntimeError: If Maya is not available
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")
        
        # Validate schema
        schema.validate()
        
        # Generate unique node name
        node_name = cmds.createNode(schema.NODE_TYPE, name=schema.NODE_PREFIX)
        
        # Add all attributes from schema
        for attr_name, attr_def in schema.ATTRIBUTES.items():
            NodeFactory._add_attribute(node_name, attr_name, attr_def)

        # Add all connection attributes from schema
        for conn_name, conn_def in schema.CONNECTIONS.items():
            NodeFactory._add_connection_attribute(node_name, conn_name, conn_def)

        # Set initial values from kwargs
        for attr_name, value in kwargs.items():
            if attr_name in schema.ATTRIBUTES:
                NodeFactory._set_attribute(node_name, attr_name, value, schema.ATTRIBUTES[attr_name])

        return node_name
    
    @staticmethod
    def _add_attribute(node_name, attr_name, attr_def):
        """Add attribute to node based on definition."""
        attr_type = attr_def['type']
        default_value = attr_def.get('default')
        
        if attr_type == 'string':
            cmds.addAttr(node_name, longName=attr_name, dataType='string')
            if default_value:
                cmds.setAttr("{}.{}".format(node_name, attr_name), default_value, type='string')
        
        elif attr_type == 'int':
            cmds.addAttr(node_name, longName=attr_name, attributeType='long')
            if default_value is not None:
                cmds.setAttr("{}.{}".format(node_name, attr_name), default_value)
        
        elif attr_type == 'float':
            cmds.addAttr(node_name, longName=attr_name, attributeType='double')
            if default_value is not None:
                cmds.setAttr("{}.{}".format(node_name, attr_name), default_value)

        elif attr_type == 'bool':
            cmds.addAttr(node_name, longName=attr_name, attributeType='bool')
            if default_value is not None:
                cmds.setAttr("{}.{}".format(node_name, attr_name), default_value)

        elif attr_type == 'message':
            multi = attr_def.get('multi', False)
            cmds.addAttr(node_name, longName=attr_name, attributeType='message', multi=multi)

    @staticmethod
    def _add_connection_attribute(node_name, conn_name, conn_def):
        """Add connection attribute (message) to node based on definition.

        Args:
            node_name (str): Node name
            conn_name (str): Connection attribute name
            conn_def (dict): Connection definition from schema
        """
        # All connections are message attributes
        multi = conn_def.get('multi', False)

        # Check if attribute already exists (avoid duplicates)
        if cmds.attributeQuery(conn_name, node=node_name, exists=True):
            return

        # Add message attribute
        # NOTE: indexMatters=False is required for multi attributes so that
        # connectAttr(nextAvailable=True) works correctly in Maya.
        if multi:
            cmds.addAttr(node_name, longName=conn_name, attributeType='message', multi=True, indexMatters=False)
        else:
            cmds.addAttr(node_name, longName=conn_name, attributeType='message')

    @staticmethod
    def _set_attribute(node_name, attr_name, value, attr_def):
        """Set attribute value based on type."""
        attr_type = attr_def['type']

        if attr_type == 'string':
            cmds.setAttr("{}.{}".format(node_name, attr_name), value, type='string')
        elif attr_type in ('int', 'float', 'bool'):
            cmds.setAttr("{}.{}".format(node_name, attr_name), value)
        # message attributes are set via connections, not direct values


class NodeWrapper(object):
    """Base wrapper class for CTX nodes.

    Provides high-level API for node operations. Subclasses should:
    - Set SCHEMA class attribute to their schema class
    - Implement domain-specific methods
    """

    SCHEMA = None  # Override with schema class

    def __init__(self, node_name):
        """Initialize wrapper.

        Args:
            node_name (str): Maya node name
        """
        self.node_name = node_name
        self.schema = self.SCHEMA() if self.SCHEMA else None

    @classmethod
    def create(cls, **kwargs):
        """Create new node from schema.

        Args:
            **kwargs: Initial attribute values

        Returns:
            NodeWrapper: Wrapper instance
        """
        if cls.SCHEMA is None:
            raise ValueError("SCHEMA must be defined in subclass")

        schema = cls.SCHEMA()
        node_name = NodeFactory.create_from_schema(schema, **kwargs)
        return cls(node_name)

    def get_attribute(self, attr_name):
        """Get attribute value.

        Args:
            attr_name (str): Attribute name

        Returns:
            Attribute value

        Raises:
            ValueError: If attribute doesn't exist in schema
        """
        if self.schema and attr_name not in self.schema.ATTRIBUTES:
            raise ValueError("Unknown attribute: {}".format(attr_name))

        if cmds is None:
            raise RuntimeError("Maya is not available")

        # Guard: attribute may not exist on nodes created before a schema update
        if not cmds.attributeQuery(attr_name, node=self.node_name, exists=True):
            if self.schema:
                return self.schema.ATTRIBUTES.get(attr_name, {}).get('default')
            return None

        return cmds.getAttr("{}.{}".format(self.node_name, attr_name))

    def set_attribute(self, attr_name, value):
        """Set attribute value.

        Args:
            attr_name (str): Attribute name
            value: New value

        Raises:
            ValueError: If attribute doesn't exist in schema
        """
        if self.schema and attr_name not in self.schema.ATTRIBUTES:
            raise ValueError("Unknown attribute: {}".format(attr_name))

        if cmds is None:
            raise RuntimeError("Maya is not available")

        # Auto-create attribute if missing (handles nodes created before schema updates)
        if not cmds.attributeQuery(attr_name, node=self.node_name, exists=True):
            if self.schema and attr_name in self.schema.ATTRIBUTES:
                NodeFactory._add_attribute(self.node_name, attr_name, self.schema.ATTRIBUTES[attr_name])

        if self.schema:
            attr_type = self.schema.ATTRIBUTES[attr_name]['type']
            if attr_type == 'string':
                cmds.setAttr("{}.{}".format(self.node_name, attr_name), value, type='string')
            else:
                cmds.setAttr("{}.{}".format(self.node_name, attr_name), value)
        else:
            cmds.setAttr("{}.{}".format(self.node_name, attr_name), value)

    def exists(self):
        """Check if node exists in Maya scene.

        Returns:
            bool: True if node exists
        """
        if cmds is None:
            return False
        return cmds.objExists(self.node_name)

    def delete(self):
        """Delete the Maya node."""
        if cmds is None:
            raise RuntimeError("Maya is not available")

        if self.exists():
            cmds.delete(self.node_name)

