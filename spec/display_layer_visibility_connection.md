# Display Layer Visibility Connection

## Overview

This document describes how display layer visibility is automatically controlled via Maya attribute connections to the CTX_Shot node's `is_active` attribute.

## Architecture

### Direct Maya Connection

Instead of manually controlling display layer visibility through Python code, we use a **direct Maya attribute connection**:

```
CTX_Shot.is_active  ──────>  DisplayLayer.visibility
```

This means:
- When `CTX_Shot.is_active = True` → Display layer becomes visible
- When `CTX_Shot.is_active = False` → Display layer becomes hidden
- The connection is automatic and happens at the Maya scene level
- No Python code needed to update visibility during shot switching

## Benefits

### 1. **Maya-Native Solution**
- Uses Maya's built-in connection system
- Visibility updates happen automatically
- Works even without Python code running

### 2. **Performance**
- No need to manually iterate through layers
- Maya handles the visibility updates natively
- Faster than Python-based visibility control

### 3. **Reliability**
- Connection persists in the Maya scene
- Survives scene save/load
- No risk of Python code failing to update visibility

### 4. **Simplicity**
- Shot switching only needs to set `is_active` attribute
- Display layer visibility updates automatically
- Less code to maintain

## Implementation

### Connection Creation

When a display layer is created, the connection is established:

```python
# In DisplayLayerManager.create_display_layer()
def _connect_visibility_to_active(self, shot_node, layer_name):
    """Connect display layer visibility to CTX_Shot is_active attribute."""
    source_attr = "{}.is_active".format(shot_node)
    dest_attr = "{}.visibility".format(layer_name)
    
    # Create direct connection
    cmds.connectAttr(source_attr, dest_attr, force=True)
```

### Shot Switching

Shot switching becomes simpler:

```python
# OLD WAY (manual visibility control):
self.layer_manager.show_layer(layer_name)
self._hide_other_shots(layer_name)

# NEW WAY (automatic via connection):
cmds.setAttr("{}.is_active".format(shot_node), True)
self._deactivate_other_shots(shot_node, manager_node)
```

## Workflow

### 1. Add Shot
```
1. Create CTX_Shot node with is_active=False
2. Create display layer
3. Connect CTX_Shot.is_active → DisplayLayer.visibility
4. Layer is hidden by default
```

### 2. Switch to Shot
```
1. Set target_shot.is_active = True
2. Display layer automatically becomes visible (via connection)
3. Set other_shots.is_active = False
4. Other display layers automatically become hidden (via connection)
```

### 3. Remove Shot
```
1. Delete CTX_Shot node
2. Connection is automatically removed
3. Delete display layer
```

## Testing

### Verify Connection Exists

```python
import maya.cmds as cmds

shot_node = 'CTX_Shot_Ep04_sq0070_SH0170'
layer_name = 'CTX_Ep04_sq0070_SH0170'

# Check if connection exists
is_connected = cmds.isConnected(
    '{}.is_active'.format(shot_node),
    '{}.visibility'.format(layer_name)
)
print("Connected:", is_connected)  # Should be True
```

### Test Visibility Control

```python
# Activate shot (should show layer)
cmds.setAttr('{}.is_active'.format(shot_node), True)
visibility = cmds.getAttr('{}.visibility'.format(layer_name))
print("Visibility after activate:", visibility)  # Should be 1 (True)

# Deactivate shot (should hide layer)
cmds.setAttr('{}.is_active'.format(shot_node), False)
visibility = cmds.getAttr('{}.visibility'.format(layer_name))
print("Visibility after deactivate:", visibility)  # Should be 0 (False)
```

### Inspect Connection in Maya

1. Open **Node Editor** (Windows → Node Editor)
2. Select CTX_Shot node
3. Select Display Layer
4. You should see a connection line from `is_active` to `visibility`

## UI Refresh

### Layer Editor UI Update

When display layer visibility changes via attribute connection, the **Layer Editor UI** might not automatically refresh to show the change. To fix this, we use a MEL command to refresh the UI:

```python
import maya.mel as mel
mel.eval('layerEditorRefreshLayerDisplay()')
```

This command is called after every visibility change to ensure the UI reflects the current state.

## Troubleshooting

### Connection Not Working

If visibility doesn't update automatically:

1. **Check connection exists:**
   ```python
   cmds.isConnected(shot_node + '.is_active', layer_name + '.visibility')
   ```

2. **Manually reconnect:**
   ```python
   layer_manager._connect_visibility_to_active(shot_node, layer_name)
   ```

3. **Check for conflicting connections:**
   ```python
   connections = cmds.listConnections(layer_name + '.visibility',
                                      source=True, plugs=True)
   print(connections)
   ```

### UI Not Updating

If the visibility changes but the Layer Editor UI doesn't update:

```python
import maya.mel as mel
mel.eval('layerEditorRefreshLayerDisplay()')
```

### Fallback to Manual Control

If direct connection fails, the code falls back to manual visibility control:

```python
# In DisplayLayerManager._connect_visibility_to_active()
try:
    cmds.connectAttr(source_attr, dest_attr, force=True)
except Exception as e:
    # Falls back to manual control via show_layer()/hide_layer()
    pass
```

## Summary

The display layer visibility connection provides a **Maya-native, automatic, and reliable** solution for controlling shot visibility. By leveraging Maya's attribute connection system, we eliminate the need for manual Python-based visibility control and ensure that display layers always reflect the active state of their associated shots.

