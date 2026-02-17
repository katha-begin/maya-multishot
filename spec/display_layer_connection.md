# Display Layer Message Attribute Connection

## Overview

This document describes the message attribute connection between CTX_Shot nodes and Display Layers.

## Architecture

### Message Attribute Connection

```
CTX_Shot_Ep04_sq0070_SH0170
    ├── display_layer_name (string): "CTX_Ep04_sq0070_SH0170"
    └── display_layer_link (message) ──┐
                                        │
                                        ├─> DisplayLayer: CTX_Ep04_sq0070_SH0170
                                        │       └── ctx_shot_link (message)
                                        │
                                        └── Connection established via:
                                            cmds.connectAttr(
                                                'CTX_Ep04_sq0070_SH0170.ctx_shot_link',
                                                'CTX_Shot_Ep04_sq0070_SH0170.display_layer_link',
                                                force=True
                                            )
```

### Attributes

**CTX_Shot Node:**
- `display_layer_name` (string): Stores the expected layer name
- `display_layer_link` (message): Message attribute for connection to display layer

**Display Layer Node:**
- `ctx_shot_link` (message): Message attribute for connection back to CTX_Shot

## Implementation

### 1. CTX_Shot Node Creation

When creating a CTX_Shot node, the `display_layer_link` message attribute is added:

```python
# In core/custom_nodes.py - CTXShotNode.create_shot()
cmds.addAttr(node_name, longName='display_layer_link', attributeType='message')
```

### 2. Display Layer Creation

When creating a display layer, the connection is established:

```python
# In core/display_layers.py - DisplayLayerManager.create_display_layer()
layer_name = self._layer_manager.create_display_layer(
    ep_code='Ep04',
    seq_code='sq0070',
    shot_code='SH0170',
    shot_node=ctx_shot  # Pass CTX_Shot node to establish connection
)
```

### 3. Linking Method

The `CTXShotNode.link_display_layer()` method establishes the connection:

```python
def link_display_layer(self, layer_name):
    """Link display layer to this shot node via message attribute."""
    # Add message attribute to display layer
    if not cmds.objExists(layer_name + '.ctx_shot_link'):
        cmds.addAttr(layer_name, longName='ctx_shot_link', attributeType='message')
    
    # Connect: DisplayLayer.ctx_shot_link -> CTX_Shot.display_layer_link
    cmds.connectAttr(
        layer_name + '.ctx_shot_link',
        self.node_name + '.display_layer_link',
        force=True
    )
```

### 4. Query Linked Layer

Get the linked display layer from a CTX_Shot node:

```python
# In core/custom_nodes.py - CTXShotNode.get_linked_display_layer()
layer_node = shot_node.get_linked_display_layer()
# Returns: 'CTX_Ep04_sq0070_SH0170' or None
```

## Benefits

1. **Bidirectional Link**: Can query from CTX_Shot to Display Layer and vice versa
2. **Maya Native**: Uses Maya's message attribute system (same as CTX_Manager ↔ CTX_Shot)
3. **Automatic Cleanup**: When display layer is deleted, connection is automatically removed
4. **Consistent Architecture**: Follows the same pattern as other CTX node connections

## Usage Examples

### Example 1: Create Shot with Display Layer

```python
from core.context import ContextManager
from core.display_layers import DisplayLayerManager

ctx_mgr = ContextManager()
layer_mgr = DisplayLayerManager()

# Create shot
shot_node = ctx_mgr.create_shot('Ep04', 'sq0070', 'SH0170')

# Create display layer and link
layer_name = layer_mgr.create_display_layer(
    'Ep04', 'sq0070', 'SH0170',
    shot_node=shot_node
)

# Verify connection
linked_layer = shot_node.get_linked_display_layer()
print(linked_layer)  # Output: CTX_Ep04_sq0070_SH0170
```

### Example 2: Query Display Layer from Shot

```python
from core.custom_nodes import CTXShotNode

shot_node = CTXShotNode('CTX_Shot_Ep04_sq0070_SH0170')

# Get linked display layer
layer_name = shot_node.get_linked_display_layer()

if layer_name:
    print("Shot is linked to layer: {}".format(layer_name))
else:
    print("No display layer linked")
```

## Connection Hierarchy

```
CTX_Manager (root)
    ├── shots (multi-message) ──> CTX_Shot nodes
    │
    └── CTX_Shot_Ep04_sq0070_SH0170
            ├── manager (message) ──> CTX_Manager
            ├── assets (multi-message) ──> CTX_Asset nodes
            └── display_layer_link (message) ──> Display Layer
                    │
                    └── CTX_Ep04_sq0070_SH0170 (Display Layer)
                            └── ctx_shot_link (message) ──> CTX_Shot
```

## Testing

To verify the connection is established:

```python
from maya import cmds

shot_node = 'CTX_Shot_Ep04_sq0070_SH0170'
layer_name = 'CTX_Ep04_sq0070_SH0170'

# Check if connection exists
is_connected = cmds.isConnected(
    layer_name + '.ctx_shot_link',
    shot_node + '.display_layer_link'
)

print("Connection exists: {}".format(is_connected))  # Should be True
```

