# CTX Node Architecture - Schema-Based System

**Version:** 3.0
**Last Updated:** 2026-02-20
**Status:** Planning Phase
**Related Docs:** [spec.md](spec.md), [CTX_lightGaffer.md](CTX_lightGaffer.md)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Current State vs Future State](#2-current-state-vs-future-state)
3. [Schema-Based Architecture](#3-schema-based-architecture)
4. [Repository Structure](#4-repository-structure)
5. [Node Type System](#5-node-type-system)
6. [Asset Type Extensibility](#6-asset-type-extensibility)
7. [Renderer Abstraction](#7-renderer-abstraction)
8. [Migration Strategy](#8-migration-strategy)
9. [Implementation Roadmap](#9-implementation-roadmap)

---

## 1. Overview

### 1.1 Purpose

This document defines the architecture for migrating from imperative node creation to a **schema-based, declarative node system** that provides:

- **Centralized node definitions** - All attributes and connections defined in schemas
- **Type safety** - Validation against schema definitions
- **Extensibility** - Easy to add new node types, asset types, and renderers
- **Graph UI integration** - Automatic port generation from schemas
- **Maintainability** - Single source of truth for node structure

### 1.2 Design Principles

| Principle | Description |
|-----------|-------------|
| **Schema-First** | Define node structure declaratively before implementation |
| **Separation of Concerns** | Schema (definition) vs Wrapper (API) vs Factory (creation) |
| **Plugin Architecture** | Registry pattern for extensible node types, asset types, renderers |
| **Backward Compatible** | Parallel implementation with feature flags |
| **Graph-Friendly** | Schema defines ports for NodeGraphQt integration |

### 1.3 Key Benefits

- ✅ **Flexible** - Add new node types without changing core code
- ✅ **Documented** - Schema IS the documentation
- ✅ **Testable** - Validate against schema, mock easily
- ✅ **Discoverable** - Query available node types programmatically
- ✅ **Consistent** - All nodes follow same creation pattern

---

## 2. Current State vs Future State

### 2.1 Current Implementation (Imperative)

**Pattern:** Wrapper Class + Factory Method + Imperative Attribute Addition

```python
# core/custom_nodes.py (Current)

CTX_MANAGER_TYPE = "network"  # All nodes use generic 'network' type
CTX_SHOT_TYPE = "network"
CTX_ASSET_TYPE = "network"

class CTXAssetNode(object):
    @classmethod
    def create_asset(cls, asset_type, asset_name, variant, shot_node=None):
        # 1. Create Maya node
        node_name = cmds.createNode(CTX_ASSET_TYPE, name="...")

        # 2. Add attributes imperatively (scattered in code)
        cmds.addAttr(node_name, longName='asset_type', dataType='string')
        cmds.setAttr(node_name + '.asset_type', asset_type, type='string')

        cmds.addAttr(node_name, longName='asset_name', dataType='string')
        cmds.setAttr(node_name + '.asset_name', asset_name, type='string')
        # ... more attributes

        # 3. Create connections
        if shot_node:
            cmds.connectAttr(...)

        return cls(node_name)
```

**Problems:**
- ❌ Attributes scattered throughout code
- ❌ No centralized definition
- ❌ Hard to extend
- ❌ No validation
- ❌ All nodes use generic 'network' type (hard to filter in Maya)

### 2.2 Future Implementation (Schema-Based)

**Pattern:** Schema Definition + Node Factory + Wrapper API

```python
# core/nodes/schemas/asset.py (Future)

class CTXAssetNodeSchema(NodeSchema):
    """Schema definition for CTX_Asset node."""

    NODE_TYPE = "network"  # Maya node type
    NODE_PREFIX = "CTX_Asset"
    CATEGORY = "Asset"

    ATTRIBUTES = {
        'ctx_node_type': {'type': 'string', 'default': 'CTX_Asset'},
        'asset_type': {'type': 'string', 'default': ''},
        'asset_name': {'type': 'string', 'default': ''},
        'variant': {'type': 'string', 'default': ''},
        'version': {'type': 'string', 'default': ''},
        'file_path': {'type': 'string', 'default': ''},
        'namespace': {'type': 'string', 'default': ''},
        'department': {'type': 'string', 'default': 'anim'},
        'maya_node_type': {'type': 'string', 'default': ''},
        'renderer': {'type': 'string', 'default': 'Arnold'},
    }

    CONNECTIONS = {
        'shot_node': {
            'type': 'message',
            'multi': False,
            'direction': 'input',
            'accepts': ['CTX_Shot']
        },
        'targetNode': {
            'type': 'message',
            'multi': False,
            'direction': 'output'
        }
    }



# Usage
schema = CTXAssetNodeSchema()
node = NodeFactory.create_from_schema(schema, asset_type='model', asset_name='chair')
```

**Benefits:**
- ✅ Centralized definition
- ✅ Easy to validate
- ✅ Auto-generates graph ports
- ✅ Self-documenting

---

## 3. Schema-Based Architecture

### 3.1 Core Components

The schema-based system consists of three main components:

```
┌─────────────────┐
│  NodeSchema     │  ← Declarative definition
│  (Definition)   │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  NodeFactory    │  ← Creates Maya nodes from schema
│  (Creation)     │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  NodeWrapper    │  ← High-level API for node operations
│  (API)          │
└─────────────────┘
```

### 3.2 Base Schema Class

```python
# core/nodes/base.py

class NodeSchema(object):
    """Base class for node schema definitions."""

    # Override in subclasses
    NODE_TYPE = None          # Maya node type (e.g., 'network')
    NODE_PREFIX = None        # Node name prefix (e.g., 'CTX_Asset')
    CATEGORY = None           # Category for organization
    DESCRIPTION = None        # Human-readable description

    ATTRIBUTES = {}           # Attribute definitions
    CONNECTIONS = {}          # Connection definitions

    def validate(self):
        """Validate schema definition.

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
                raise ValueError(f"Attribute '{attr_name}' missing 'type'")

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
```

### 3.3 Node Factory

```python
# core/nodes/base.py

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
        """
        # Validate schema
        schema.validate()

        # Generate unique node name
        node_name = cmds.createNode(schema.NODE_TYPE, name=schema.NODE_PREFIX)

        # Add all attributes from schema
        for attr_name, attr_def in schema.ATTRIBUTES.items():
            attr_type = attr_def['type']
            default_value = attr_def.get('default')

            # Create attribute
            if attr_type == 'string':
                cmds.addAttr(node_name, longName=attr_name, dataType='string')
                if default_value:
                    cmds.setAttr(f"{node_name}.{attr_name}", default_value, type='string')

            elif attr_type == 'int':
                cmds.addAttr(node_name, longName=attr_name, attributeType='long')
                if default_value is not None:
                    cmds.setAttr(f"{node_name}.{attr_name}", default_value)

            elif attr_type == 'float':
                cmds.addAttr(node_name, longName=attr_name, attributeType='double')
                if default_value is not None:
                    cmds.setAttr(f"{node_name}.{attr_name}", default_value)

            elif attr_type == 'bool':
                cmds.addAttr(node_name, longName=attr_name, attributeType='bool')
                if default_value is not None:
                    cmds.setAttr(f"{node_name}.{attr_name}", default_value)

            elif attr_type == 'message':
                multi = attr_def.get('multi', False)
                cmds.addAttr(node_name, longName=attr_name,
                           attributeType='message', multi=multi)

        # Set initial values from kwargs
        for attr_name, value in kwargs.items():
            if attr_name in schema.ATTRIBUTES:
                attr_type = schema.ATTRIBUTES[attr_name]['type']
                if attr_type == 'string':
                    cmds.setAttr(f"{node_name}.{attr_name}", value, type='string')
                else:
                    cmds.setAttr(f"{node_name}.{attr_name}", value)

        return node_name
```

### 3.4 Node Wrapper Pattern

```python
# core/nodes/wrappers/base.py

class NodeWrapper(object):
    """Base wrapper class for CTX nodes."""

    SCHEMA = None  # Override with schema class

    def __init__(self, node_name):
        """Initialize wrapper.

        Args:
            node_name (str): Maya node name
        """
        self.node_name = node_name
        self.schema = self.SCHEMA()

    @classmethod
    def create(cls, **kwargs):
        """Create new node from schema.

        Args:
            **kwargs: Initial attribute values

        Returns:
            NodeWrapper: Wrapper instance
        """
        schema = cls.SCHEMA()
        node_name = NodeFactory.create_from_schema(schema, **kwargs)
        return cls(node_name)

    def get_attribute(self, attr_name):
        """Get attribute value.

        Args:
            attr_name (str): Attribute name

        Returns:
            Attribute value
        """
        if attr_name not in self.schema.ATTRIBUTES:
            raise ValueError(f"Unknown attribute: {attr_name}")

        return cmds.getAttr(f"{self.node_name}.{attr_name}")

    def set_attribute(self, attr_name, value):
        """Set attribute value.

        Args:
            attr_name (str): Attribute name
            value: New value
        """
        if attr_name not in self.schema.ATTRIBUTES:
            raise ValueError(f"Unknown attribute: {attr_name}")

        attr_type = self.schema.ATTRIBUTES[attr_name]['type']
        if attr_type == 'string':
            cmds.setAttr(f"{self.node_name}.{attr_name}", value, type='string')
        else:
            cmds.setAttr(f"{self.node_name}.{attr_name}", value)
```

---

## 4. Repository Structure

**⚠️ See [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md) for the complete repository structure comparison (BEFORE/AFTER).**

This document focuses on the schema-based node system architecture details.

### 4.1 Module Organization

**Core Modules:**
- `core/nodes/` - Schema-based node system (NEW)
- `core/asset_types/` - Asset type handlers (NEW)
- `core/renderers/` - Renderer adapters (NEW)
- `core/gaffer/` - Gaffer system (NEW)
- `core/custom_nodes.py` - Legacy node system (KEEP for compatibility)

**Integration:**
- `vendor/NodeGraphQt/` - Vendored graph UI library
- `tests/nodegraphqt_components/` - Graph integration code

---

## 5. Node Type System

### 5.1 Current Approach: Network Nodes + Filtering

**Recommendation:** Keep using `network` nodes but add filtering attributes.

```python
# All CTX nodes remain as 'network' type
CTX_MANAGER_TYPE = "network"
CTX_SHOT_TYPE = "network"
CTX_ASSET_TYPE = "network"
CTX_GAFFER_TYPE = "network"

# But add unique identifier attribute
CTX_NODE_IDENTIFIER = "ctx_pipeline_node"

# And specific type attribute
# ctx_node_type = 'CTX_Manager' | 'CTX_Shot' | 'CTX_Asset' | 'CTX_LightGaffer'
```

**Filtering in Maya:**

```python
# List all CTX nodes
def list_ctx_nodes(node_type=None):
    """List all CTX pipeline nodes.

    Args:
        node_type (str): Filter by specific type (e.g., 'CTX_Asset')

    Returns:
        list: List of node names
    """
    all_network_nodes = cmds.ls(type='network')
    ctx_nodes = []

    for node in all_network_nodes:
        # Check if it's a CTX node
        if cmds.attributeQuery('ctx_node_type', node=node, exists=True):
            if node_type:
                # Filter by specific type
                if cmds.getAttr(f"{node}.ctx_node_type") == node_type:
                    ctx_nodes.append(node)
            else:
                ctx_nodes.append(node)

    return ctx_nodes

# Usage
all_assets = list_ctx_nodes('CTX_Asset')
all_gaffers = list_ctx_nodes('CTX_LightGaffer')
all_ctx = list_ctx_nodes()  # All CTX nodes
```

### 5.2 Future Approach: Custom Maya Node Types (Optional)

For deeper Maya integration, custom node types can be implemented via Maya plugin:

```cpp
// Custom Maya node type (C++ plugin)
class CTXAssetNode : public MPxNode {
public:
    static MTypeId id;
    static MString typeName;

    // Custom attributes
    static MObject aAssetType;
    static MObject aAssetName;
    // ...
};
```

**Benefits of Custom Types:**
- Native Maya filtering: `cmds.ls(type='CTXAssetNode')`
- Better Outliner integration
- Custom icons in Node Editor
- Attribute Editor templates

**Drawbacks:**
- Requires C++ plugin compilation
- More complex deployment
- Platform-specific builds

**Decision:** Start with network nodes + filtering, migrate to custom types in future if needed.

---

## 6. Asset Type Extensibility

See [ASSET_TYPES.md](ASSET_TYPES.md) for complete documentation.

### 6.1 Overview

The Asset Type Handler system provides extensible support for different Maya asset node types:

- **Arnold StandIn** (`.abc`, `.ass`)
- **Redshift Proxy** (`.rs`, `.abc`)
- **USD Reference** (`.usd`, `.usda`, `.usdc`, `.usdz`) ← NEW
- **Maya Reference** (`.ma`, `.mb`)
- **Alembic Cache** (`.abc`)
- **Future:** FBX, OBJ, custom formats

### 6.2 Integration with CTX_Asset

```python
# core/nodes/wrappers/asset.py

from core.asset_types.registry import AssetTypeRegistry

class CTXAssetNode(NodeWrapper):
    """Wrapper for CTX_Asset node."""

    SCHEMA = CTXAssetNodeSchema

    def create_target_node(self, file_path):
        """Create target Maya node based on file extension.

        Args:
            file_path (str): Path to asset file

        Returns:
            str: Created target node name
        """
        # Get file extension
        ext = os.path.splitext(file_path)[1]

        # Get appropriate handler
        handler = AssetTypeRegistry.get_handler_by_extension(ext)
        if not handler:
            raise ValueError(f"No handler for extension: {ext}")

        # Create node using handler
        namespace = self.get_attribute('namespace')
        target_node = handler.create_node(namespace, file_path)

        # Link to CTX_Asset via message attribute
        cmds.connectAttr(f"{target_node}.message",
                        f"{self.node_name}.targetNode")

        # Store node type
        self.set_attribute('maya_node_type', handler.MAYA_NODE_TYPE)

        return target_node
```

---

## 7. Renderer Abstraction

See [RENDERER_ADAPTERS.md](RENDERER_ADAPTERS.md) for complete documentation.

### 7.1 Overview

The Renderer Adapter system provides unified interface for renderer-specific operations:

- **Arnold** - aiStandIn, aiAreaLight, Arnold shaders
- **Redshift** - RedshiftProxyMesh, RedshiftPhysicalLight, Redshift shaders
- **Future:** Karma, V-Ray, RenderMan

### 7.2 Integration with Gaffer System

```python
# core/gaffer/inheritance.py

from core.renderers.registry import RendererRegistry

def apply_gaffer_to_light(light_name, gaffer_chain):
    """Apply gaffer overrides to light (renderer-agnostic).

    Args:
        light_name (str): Maya light node name
        gaffer_chain (list): List of gaffer nodes (Shot → Seq → Master)
    """
    # Get active renderer adapter
    renderer = RendererRegistry.get_adapter()

    # Resolve each attribute through gaffer chain
    for attr in ['intensity', 'exposure', 'color', 'temperature', 'muted']:
        value, enabled = resolve_gaffer_attribute(light_name, attr, gaffer_chain)

        if enabled and value is not None:
            # Apply using renderer adapter (works for any renderer!)
            renderer.set_light_attribute(light_name, attr, value)
```

---

## 8. Migration Strategy

### 8.1 Parallel Implementation Approach

**Goal:** Migrate incrementally without breaking existing code.

```
┌──────────────────────────────────────────────────────┐
│  Phase 1: Foundation (Week 1)                        │
│  - Create core/nodes/ structure                      │
│  - Implement base classes (NodeSchema, NodeFactory)  │
│  - Keep core/custom_nodes.py unchanged               │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│  Phase 2: Gaffer Implementation (Week 2)             │
│  - Implement gaffer schemas (NEW code)               │
│  - Implement gaffer wrappers                         │
│  - Test gaffer system independently                  │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│  Phase 3: Asset/Renderer Systems (Week 3)            │
│  - Implement asset type handlers                     │
│  - Implement renderer adapters                       │
│  - Integrate with existing Asset Manager             │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│  Phase 4: Node Migration (Week 4)                    │
│  - Migrate CTX_Asset to schema-based                 │
│  - Migrate CTX_Shot to schema-based                  │
│  - Migrate CTX_Manager to schema-based               │
│  - Add compatibility layer                           │
└──────────────────────────────────────────────────────┘
```

### 8.2 Compatibility Layer

```python
# core/custom_nodes.py (Updated)

from core.nodes.wrappers.asset import CTXAssetNode as CTXAssetNodeNew

class CTXAssetNode(object):
    """Legacy wrapper - delegates to new schema-based implementation."""

    def __init__(self, node_name):
        # Use new implementation internally
        self._new_impl = CTXAssetNodeNew(node_name)
        self.node_name = node_name

    @classmethod
    def create_asset(cls, asset_type, asset_name, variant, shot_node=None):
        """Legacy factory method - uses new implementation."""
        # Delegate to new schema-based creation
        new_node = CTXAssetNodeNew.create(
            asset_type=asset_type,
            asset_name=asset_name,
            variant=variant
        )

        # Connect to shot if provided
        if shot_node:
            # ... connection logic

        return cls(new_node.node_name)

    # All other methods delegate to self._new_impl
```

### 8.3 Feature Flags

```python
# core/config.py

class Config(object):
    # Feature flags for gradual rollout
    USE_SCHEMA_BASED_NODES = True
    USE_ASSET_TYPE_HANDLERS = True
    USE_RENDERER_ADAPTERS = True

    @classmethod
    def is_feature_enabled(cls, feature_name):
        return getattr(cls, feature_name, False)

# Usage
if Config.is_feature_enabled('USE_SCHEMA_BASED_NODES'):
    node = CTXAssetNodeNew.create(...)
else:
    node = CTXAssetNode.create_asset(...)
```

---

## 9. Implementation Roadmap

### 9.1 Phase 1: Foundation + Planning (Week 1)

**Goals:**
- Create repository structure
- Implement base infrastructure
- Document all schemas

**Tasks:**
1. ✅ Create `core/nodes/` directory structure
2. ✅ Implement `NodeSchema` base class
3. ✅ Implement `NodeFactory` class
4. ✅ Implement `NodeWrapper` base class
5. ✅ Create `core/asset_types/` structure
6. ✅ Create `core/renderers/` structure
7. ✅ Create `core/gaffer/` structure
8. ✅ Document all schemas in planning docs

**Deliverables:**
- Base classes implemented and tested
- Directory structure created
- Schema planning documents complete

### 9.2 Phase 2: Gaffer Implementation (Week 2)

**Goals:**
- Implement gaffer system using schema-based approach
- Prove the pattern works

**Tasks:**
1. Implement `CTXLightGafferSchema`
2. Implement `CTXLightContextSchema`
3. Implement `CTXLightGafferNode` wrapper
4. Implement gaffer chain resolution
5. Implement per-attribute inheritance system
6. Integrate with renderer adapters
7. Create Light Manager UI
8. Write tests

**Deliverables:**
- Working gaffer system
- Light Manager UI
- Test suite passing

### 9.3 Phase 3: Asset & Renderer Systems (Week 3)

**Goals:**
- Implement asset type handlers
- Implement renderer adapters
- Integrate with existing code

**Tasks:**
1. Implement `AssetTypeHandler` base class
2. Implement Arnold/Redshift/USD handlers
3. Implement `RendererAdapter` base class
4. Implement Arnold/Redshift adapters
5. Update Asset Manager to use handlers
6. Write tests

**Deliverables:**
- Asset type handler system working
- Renderer adapter system working
- USD support functional

### 9.4 Phase 4: Node Migration (Week 4)

**Goals:**
- Migrate existing nodes to schema-based
- Maintain backward compatibility

**Tasks:**
1. Create `CTXAssetNodeSchema`
2. Migrate `CTXAssetNode` to schema-based
3. Create compatibility layer
4. Create `CTXShotNodeSchema`
5. Migrate `CTXShotNode` to schema-based
6. Create `CTXManagerNodeSchema`
7. Migrate `CTXManagerNode` to schema-based
8. Update all UI code
9. Write migration tests
10. Update documentation

**Deliverables:**
- All nodes migrated to schema-based
- Backward compatibility maintained
- All tests passing

---

## 10. NodeGraphQt Integration

### 10.1 Vendored Library

NodeGraphQt is vendored in `vendor/NodeGraphQt/` for visual node graph representation.

**Version:** Latest stable
**License:** MIT
**Purpose:** Visual representation of CTX node hierarchy

### 10.2 Schema to Graph Mapping

Schemas automatically generate NodeGraphQt port definitions:

```python
# tests/nodegraphqt_components/ctx_nodes.py

from NodeGraphQt import BaseNode
from core.nodes.schemas.asset import CTXAssetNodeSchema

class CTXAssetGraphNode(BaseNode):
    """NodeGraphQt node for CTX_Asset."""

    __identifier__ = 'ctx.pipeline'
    NODE_NAME = 'CTX Asset'

    def __init__(self):
        super(CTXAssetGraphNode, self).__init__()

        # Get schema
        schema = CTXAssetNodeSchema()

        # Auto-generate ports from schema
        ports = schema.get_graph_ports()

        for port_name, port_config in ports.items():
            if port_config['type'] == 'input':
                self.add_input(port_name, multi_input=port_config['multi'])
            else:
                self.add_output(port_name, multi_output=port_config['multi'])
```

### 10.3 Building Graph from Maya Scene

```python
# tests/nodegraphqt_components/ctx_graph.py

from NodeGraphQt import NodeGraph
from core.nodes.registry import NodeRegistry

def build_graph_from_scene():
    """Build NodeGraphQt graph from Maya scene.

    Returns:
        NodeGraph: Graph instance
    """
    graph = NodeGraph()

    # Get all CTX nodes from Maya
    ctx_nodes = list_ctx_nodes()

    # Create graph nodes
    graph_nodes = {}
    for maya_node in ctx_nodes:
        node_type = cmds.getAttr(f"{maya_node}.ctx_node_type")

        # Create corresponding graph node
        graph_node = graph.create_node(f'ctx.pipeline.{node_type}')
        graph_nodes[maya_node] = graph_node

    # Create connections
    for maya_node in ctx_nodes:
        # Find connections in Maya
        connections = cmds.listConnections(maya_node,
                                          connections=True,
                                          plugs=True)

        # Replicate in graph
        # ... connection logic

    return graph
```

---

## 11. Testing Strategy

### 11.1 Unit Tests

```python
# tests/test_node_schema.py

import unittest
from core.nodes.schemas.asset import CTXAssetNodeSchema
from core.nodes.base import NodeFactory

class TestNodeSchema(unittest.TestCase):

    def test_schema_validation(self):
        """Test schema validation."""
        schema = CTXAssetNodeSchema()
        self.assertTrue(schema.validate())

    def test_node_creation(self):
        """Test creating node from schema."""
        schema = CTXAssetNodeSchema()
        node = NodeFactory.create_from_schema(
            schema,
            asset_type='model',
            asset_name='chair'
        )

        self.assertTrue(cmds.objExists(node))
        self.assertEqual(cmds.getAttr(f"{node}.asset_type"), 'model')

    def test_graph_port_generation(self):
        """Test automatic port generation."""
        schema = CTXAssetNodeSchema()
        ports = schema.get_graph_ports()

        self.assertIn('shot_node', ports)
        self.assertEqual(ports['shot_node']['type'], 'input')
```

### 11.2 Integration Tests

```python
# tests/test_asset_workflow.py

import unittest
from core.nodes.wrappers.asset import CTXAssetNode
from core.asset_types.registry import AssetTypeRegistry

class TestAssetWorkflow(unittest.TestCase):

    def test_usd_asset_creation(self):
        """Test creating USD asset."""
        # Create CTX_Asset node
        asset = CTXAssetNode.create(
            asset_type='model',
            asset_name='chair',
            variant='wood'
        )

        # Create target USD node
        usd_path = '/path/to/chair.usd'
        target = asset.create_target_node(usd_path)

        # Verify
        self.assertTrue(cmds.objExists(target))
        self.assertEqual(cmds.nodeType(target), 'transform')

        # Verify USD shape
        shapes = cmds.listRelatives(target, shapes=True)
        self.assertEqual(cmds.nodeType(shapes[0]), 'mayaUsdProxyShape')
```

---

## 12. Summary

### 12.1 Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Node Architecture** | Schema-based | Centralized, extensible, graph-friendly |
| **Node Types** | Network + filtering | Simple, backward compatible |
| **Asset Types** | Handler registry | Extensible, USD-ready |
| **Renderers** | Adapter pattern | Renderer-agnostic core |
| **Migration** | Parallel implementation | No breaking changes |
| **Gaffer** | Per-attribute inheritance | Flexible, no gaffer_type needed |

### 12.2 Benefits

- ✅ **Flexible** - Easy to add new node types, asset types, renderers
- ✅ **Maintainable** - Centralized definitions, single source of truth
- ✅ **Testable** - Schema validation, mock-friendly
- ✅ **Graph-Friendly** - Auto-generates NodeGraphQt ports
- ✅ **Production-Ready** - Backward compatible, feature flags
- ✅ **USD-Ready** - Built-in USD support
- ✅ **Multi-Renderer** - Works with Arnold, Redshift, future renderers

### 12.3 Next Steps

1. Review and approve this architecture document
2. Begin Phase 1 implementation (foundation)
3. Create detailed schema planning documents
4. Implement base infrastructure
5. Start gaffer implementation (Phase 2)

---

**Document Status:** ✅ Complete
**Version:** 3.0
**Last Updated:** 2026-02-20
**Maintainer:** CTX Pipeline Team