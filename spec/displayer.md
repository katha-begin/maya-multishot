# Display Layer Integration Implementation Plan

**Document Version:** 1.0  
**Date:** 2026-02-17  
**Status:** Ready for Implementation

---

## 1. Overview

### 1.1 Purpose
Integrate the existing display layer modules (`core/display_layers.py` and `core/shot_switching.py`) into the UI workflow to enable shot-specific visibility control in multi-shot Maya scenes.

### 1.2 Current Status
- ✅ **DisplayLayerManager** class fully implemented (304 lines)
- ✅ **ShotSwitcher** class fully implemented (280 lines)
- ✅ **CTX_Shot** node stores `display_layer_name` attribute
- ❌ **NOT integrated** into UI workflow (Main Window, Asset Manager)
- ❌ **NOT creating** actual Maya display layers
- ❌ **NOT managing** layer visibility on shot switching
- ❌ **NOT assigning** assets to layers on import

### 1.3 Architecture Decision: CTX-Based Layer Management

**Key Principle:** Display layer metadata is stored in CTX_Shot nodes and linked to Maya display layers through the existing CTX hierarchy.

**Hierarchy Tracing:**
```
CTX_Shot (stores display_layer_name)
    ↓ (get_assets())
CTX_Asset (connected via message attributes)
    ↓ (get_linked_maya_node())
Maya Node (aiStandIn, reference, etc.)
    ↓ (assign_to_layer())
Display Layer (Maya display layer)
```

**Benefits:**
- Leverages existing CTX node connections
- No duplicate tracking needed
- Automatic cleanup when CTX nodes are deleted
- Consistent with project architecture

---

## 2. Display Layer Metadata Storage

### 2.1 CTX_Shot Node Attributes

**Existing Implementation** (lines 342-344 in `core/custom_nodes.py`):
```python
cmds.addAttr(node_name, longName='display_layer_name', dataType='string')
layer_name = "CTX_{}_{}_{}".format(ep_code, seq_code, shot_code)
cmds.setAttr(node_name + '.display_layer_name', layer_name, type='string')
```

**Getter Method** (lines 401-407):
```python
def get_display_layer_name(self):
    """Get display layer name."""
    return cmds.getAttr(self.node_name + '.display_layer_name')
```

### 2.2 Asset Tracing Workflow

**Step 1: Get all assets for a shot**
```python
shot_node = CTXShotNode('CTX_Shot_Ep04_sq0070_SH0170')
assets = shot_node.get_assets()  # Returns list of CTXAssetNode instances
```

**Step 2: Get Maya node for each asset**
```python
for asset in assets:
    maya_node = asset.get_linked_maya_node()  # Returns Maya node name
    if maya_node:
        # Maya node found, ready for layer assignment
```

**Step 3: Assign Maya node to display layer**
```python
layer_name = shot_node.get_display_layer_name()
layer_manager.assign_to_layer(maya_node, layer_name)
```

---

## 3. Implementation Tasks Breakdown

### Task 1: Integrate DisplayLayerManager into Main Window
**Priority:** HIGH  
**Complexity:** Simple (1-2 hours)  
**File:** `ui/main_window.py`

**Changes Required:**
1. Import `DisplayLayerManager` and `ShotSwitcher`
2. Initialize in `__init__()` method
3. Pass to child components (Asset Manager Dialog)

**Code Changes:**
```python
# Add imports (after line 20)
from core.display_layers import DisplayLayerManager
from core.shot_switching import ShotSwitcher

# In __init__() method (after line 60)
self._layer_manager = DisplayLayerManager()
self._shot_switcher = ShotSwitcher(
    self._layer_manager,
    self._context_manager
)
```

---

### Task 2: Create Display Layers When Adding Shots
**Priority:** HIGH  
**Complexity:** Simple (1-2 hours)  
**File:** `ui/main_window.py`

**Method:** `_on_add_shots()` (lines 394-493)

**Changes Required:**
After creating CTX_Shot node, create the Maya display layer:

```python
# After line 470 (after shot_node creation)
if shot_node:
    # Create display layer for this shot
    layer_name = self._layer_manager.create_display_layer(
        ep_code, seq_code, shot_code
    )
    logger.info("Created display layer: {}".format(layer_name))
```

**Expected Behavior:**
- Maya display layer created with name `CTX_{ep}_{seq}_{shot}`
- Layer is visible by default
- Layer name matches `CTX_Shot.display_layer_name` attribute

---

### Task 3: Toggle Layer Visibility When Switching Shots
**Priority:** HIGH  
**Complexity:** Medium (2-3 hours)  
**File:** `ui/main_window.py`

**Method:** `_on_set_shot()` (lines 494-545)

**Current Implementation:**
- Only updates CTX node active state
- Does NOT manage display layer visibility

**New Implementation:**
Replace manual CTX node updates with `ShotSwitcher`:

```python
def _on_set_shot(self, row):
    """Handle Set Shot button click."""
    shot_data = self._shots[row]
    
    if 'ctx_node' not in shot_data or not shot_data['ctx_node']:
        logger.warning("No CTX node for shot at row {}".format(row))
        return
    
    shot_node = shot_data['ctx_node']
    manager_node = self._context_manager.get_manager_node()
    
    if not manager_node:
        logger.error("No CTX_Manager node found")
        return
    
    # Use ShotSwitcher to handle layer visibility
    success = self._shot_switcher.switch_to_shot(
        shot_node.node_name,
        manager_node.node_name,
        hide_others=True  # Hide other shots' layers
    )
    
    if success:
        # Update UI
        self._active_shot_index = row
        self._update_shot_table()
        logger.info("Switched to shot: {}".format(shot_node.get_shot_id()))
    else:
        logger.error("Failed to switch to shot")
```

**Expected Behavior:**
- Active shot's display layer becomes visible
- Inactive shots' display layers become hidden
- CTX_Manager.active_shot_id updated
- UI reflects active shot state

---

### Task 4: Assign Assets to Layers When Importing
**Priority:** HIGH
**Complexity:** Medium (2-3 hours)
**File:** `core/asset_scanner.py`

**Method:** `import_asset()` (lines 200-350)

**Changes Required:**
1. Add `layer_manager` parameter to `__init__()`
2. After creating Maya node, assign to shot's display layer

**Code Changes:**

```python
# In __init__() method (line 50)
def __init__(self, config, layer_manager=None):
    self._config = config
    self._layer_manager = layer_manager
    # ... rest of init

# In import_asset() method (after Maya node creation, around line 300)
# After successfully creating Maya node:
if maya_node and self._layer_manager:
    # Get shot info from context
    shot_node = self._get_active_shot_node()
    if shot_node:
        layer_name = shot_node.get_display_layer_name()
        if layer_name and cmds.objExists(layer_name):
            self._layer_manager.assign_to_layer(maya_node, layer_name)
            logger.info("Assigned {} to layer {}".format(maya_node, layer_name))
        else:
            logger.warning("Display layer {} not found".format(layer_name))
```

**Expected Behavior:**
- Imported assets automatically added to active shot's display layer
- Assets visible/hidden based on shot's layer visibility
- No manual layer assignment needed

---

### Task 5: Update Asset Manager Dialog to Use Layers
**Priority:** HIGH
**Complexity:** Simple (1 hour)
**File:** `ui/asset_manager_dialog.py`

**Changes Required:**
1. Accept `layer_manager` parameter in constructor
2. Pass `layer_manager` to `AssetScanner`

**Code Changes:**

```python
# In __init__() method (around line 80)
def __init__(self, shot_data, config, layer_manager=None, parent=None):
    super(AssetManagerDialog, self).__init__(parent)
    self._shot_data = shot_data
    self._config = config
    self._layer_manager = layer_manager  # Store layer manager
    # ... rest of init

# In _on_import_asset() method (around line 600)
# When creating AssetScanner:
scanner = AssetScanner(self._config, self._layer_manager)
```

**In Main Window** (`ui/main_window.py`):
```python
# In _on_manage_assets() method (around line 560)
dialog = AssetManagerDialog(
    shot_data,
    self._config,
    layer_manager=self._layer_manager,  # Pass layer manager
    parent=self
)
```

**Expected Behavior:**
- Asset Manager Dialog has access to layer manager
- All asset imports automatically assigned to layers
- Consistent layer management across UI

---

### Task 6: Handle Display Layer Cleanup on Shot Removal
**Priority:** MEDIUM
**Complexity:** Simple (1 hour)
**File:** `ui/main_window.py`

**Method:** `_on_remove_shot()` (lines 547-600)

**Changes Required:**
Before deleting CTX_Shot node, delete the display layer:

```python
# Before deleting shot_node (around line 580)
if shot_node:
    # Get layer name before deleting node
    layer_name = shot_node.get_display_layer_name()

    # Delete CTX_Shot node
    shot_node.delete()

    # Delete display layer if it exists
    if layer_name and cmds.objExists(layer_name):
        try:
            cmds.delete(layer_name)
            logger.info("Deleted display layer: {}".format(layer_name))
        except Exception as e:
            logger.warning("Failed to delete layer {}: {}".format(layer_name, e))
```

**Expected Behavior:**
- Display layer deleted when shot is removed
- No orphaned layers left in scene
- Clean scene hierarchy

---

### Task 7: Assign Existing Assets to Layers (Batch Operation)
**Priority:** MEDIUM
**Complexity:** Medium (2-3 hours)
**File:** New utility function in `core/display_layers.py`

**Purpose:** Assign all existing assets in a shot to its display layer (for scenes converted from POC or manually created).

**Implementation:**

```python
def sync_shot_assets_to_layer(shot_node, layer_manager):
    """Assign all assets in a shot to its display layer.

    Args:
        shot_node (CTXShotNode): Shot node instance
        layer_manager (DisplayLayerManager): Layer manager instance

    Returns:
        dict: Statistics {assigned: int, failed: int, skipped: int}
    """
    stats = {'assigned': 0, 'failed': 0, 'skipped': 0}

    # Get layer name
    layer_name = shot_node.get_display_layer_name()
    if not layer_name:
        logger.error("Shot has no display layer name")
        return stats

    # Create layer if it doesn't exist
    if not cmds.objExists(layer_name):
        ep = shot_node.get_ep_code()
        seq = shot_node.get_seq_code()
        shot = shot_node.get_shot_code()
        layer_manager.create_display_layer(ep, seq, shot)

    # Get all assets for this shot
    assets = shot_node.get_assets()

    for asset in assets:
        maya_node = asset.get_linked_maya_node()
        if not maya_node:
            stats['skipped'] += 1
            continue

        if not cmds.objExists(maya_node):
            stats['skipped'] += 1
            continue

        try:
            layer_manager.assign_to_layer(maya_node, layer_name)
            stats['assigned'] += 1
        except Exception as e:
            logger.error("Failed to assign {}: {}".format(maya_node, e))
            stats['failed'] += 1

    return stats
```

**Usage in Main Window:**
```python
# Add menu action: "Tools > Sync Assets to Layers"
def _on_sync_assets_to_layers(self):
    """Sync all assets to their shot display layers."""
    total_stats = {'assigned': 0, 'failed': 0, 'skipped': 0}

    for shot_data in self._shots:
        if 'ctx_node' in shot_data and shot_data['ctx_node']:
            stats = sync_shot_assets_to_layer(
                shot_data['ctx_node'],
                self._layer_manager
            )
            for key in total_stats:
                total_stats[key] += stats[key]

    msg = "Sync complete:\n"
    msg += "Assigned: {}\n".format(total_stats['assigned'])
    msg += "Failed: {}\n".format(total_stats['failed'])
    msg += "Skipped: {}".format(total_stats['skipped'])

    QMessageBox.information(self, "Sync Assets to Layers", msg)
```

---

## 4. Testing Checklist

### 4.1 Unit Tests
- [ ] Test `DisplayLayerManager.create_display_layer()`
- [ ] Test `DisplayLayerManager.assign_to_layer()`
- [ ] Test `DisplayLayerManager.set_layer_visibility()`
- [ ] Test `ShotSwitcher.switch_to_shot()`
- [ ] Test `CTXShotNode.get_display_layer_name()`
- [ ] Test `CTXShotNode.get_assets()`
- [ ] Test `CTXAssetNode.get_linked_maya_node()`

### 4.2 Integration Tests

**Test Case 1: Add Shot**
1. Open Main Window
2. Click "Add Shot" → Enter SH0170
3. Verify: Display layer `CTX_Ep04_sq0070_SH0170` created
4. Verify: Layer is visible
5. Verify: CTX_Shot node has correct `display_layer_name` attribute

**Test Case 2: Import Asset**
1. Add shot SH0170 (set as active)
2. Click "Manage Assets" → Import CHAR_CatStompie_001
3. Verify: Maya node created (aiStandIn or reference)
4. Verify: Maya node assigned to `CTX_Ep04_sq0070_SH0170` layer
5. Verify: Asset visible in viewport

**Test Case 3: Switch Active Shot**
1. Add two shots: SH0170 (active), SH0180 (inactive)
2. Import asset to SH0170
3. Import asset to SH0180
4. Click "Set" on SH0180
5. Verify: `CTX_Ep04_sq0070_SH0180` layer becomes visible
6. Verify: `CTX_Ep04_sq0070_SH0170` layer becomes hidden
7. Verify: Only SH0180 assets visible in viewport

**Test Case 4: Remove Shot**
1. Add shot SH0170 with assets
2. Click "Remove" on SH0170
3. Verify: CTX_Shot node deleted
4. Verify: Display layer `CTX_Ep04_sq0070_SH0170` deleted
5. Verify: No orphaned layers in scene

**Test Case 5: Multi-Shot Workflow**
1. Add 3 shots: SH0170, SH0180, SH0190
2. Import different assets to each shot
3. Switch between shots
4. Verify: Only active shot's assets visible
5. Verify: Layer visibility updates correctly
6. Verify: No performance issues

**Test Case 6: Sync Assets to Layers (Batch)**
1. Open scene with CTX nodes but no layer assignments
2. Run "Tools > Sync Assets to Layers"
3. Verify: All assets assigned to correct layers
4. Verify: Statistics report shows correct counts

---

## 5. Expected Behavior After Implementation

### 5.1 User Experience

**Scenario: Animator Working on Multi-Shot Scene**

1. **Scene Setup:**
   - Scene has 3 shots: SH0170, SH0180, SH0190
   - Each shot has 5-10 assets (characters, props, sets)
   - Total: 20-30 assets in scene

2. **Working on SH0170:**
   - User clicks "Set" on SH0170
   - **Result:** Only SH0170 assets visible in viewport
   - **Performance:** Switch happens instantly (< 100ms)
   - **Viewport:** Clean, only relevant assets shown

3. **Switching to SH0180:**
   - User clicks "Set" on SH0180
   - **Result:** SH0170 assets hidden, SH0180 assets shown
   - **Paths:** All asset paths resolve for SH0180 context
   - **Viewport:** Updated to show SH0180 assets

4. **Importing New Asset:**
   - User imports PROP_TreeBig_001 to SH0180
   - **Result:** Asset automatically added to SH0180 layer
   - **Visibility:** Asset immediately visible (SH0180 is active)

### 5.2 Technical Behavior

**Display Layer State:**
```
Scene State:
├── CTX_Ep04_sq0070_SH0170 (hidden)
│   ├── CHAR_CatStompie_001
│   └── PROP_TreeBig_001
├── CTX_Ep04_sq0070_SH0180 (visible) ← Active
│   ├── CHAR_DogBounce_001
│   └── SET_ForestGround_001
└── CTX_Ep04_sq0070_SH0190 (hidden)
    └── CHAR_BirdFly_001
```

**CTX Node Hierarchy:**
```
CTX_Manager
├── active_shot_id: "Ep04_sq0070_SH0180"
├── CTX_Shot_SH0170 (is_active: False)
│   ├── display_layer_name: "CTX_Ep04_sq0070_SH0170"
│   ├── CTX_Asset_CHAR_CatStompie_001_SH0170
│   └── CTX_Asset_PROP_TreeBig_001_SH0170
├── CTX_Shot_SH0180 (is_active: True)
│   ├── display_layer_name: "CTX_Ep04_sq0070_SH0180"
│   ├── CTX_Asset_CHAR_DogBounce_001_SH0180
│   └── CTX_Asset_SET_ForestGround_001_SH0180
└── CTX_Shot_SH0190 (is_active: False)
    ├── display_layer_name: "CTX_Ep04_sq0070_SH0190"
    └── CTX_Asset_CHAR_BirdFly_001_SH0190
```

---

## 6. Implementation Order

**Phase 1: Core Integration (Day 1)**
1. Task 1: Integrate DisplayLayerManager into Main Window (1-2 hours)
2. Task 2: Create display layers when adding shots (1-2 hours)
3. Task 3: Toggle layer visibility when switching shots (2-3 hours)

**Phase 2: Asset Integration (Day 2)**
4. Task 4: Assign assets to layers when importing (2-3 hours)
5. Task 5: Update Asset Manager Dialog (1 hour)
6. Task 6: Handle display layer cleanup (1 hour)

**Phase 3: Utilities & Testing (Day 3)**
7. Task 7: Batch sync utility (2-3 hours)
8. Integration testing (3-4 hours)
9. Bug fixes and polish (2-3 hours)

**Total Estimated Time:** 2-3 days

---

## 7. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Performance issues with many assets** | Medium | Use batch operations, optimize layer queries |
| **Locked nodes prevent layer assignment** | Low | Handle exceptions, log warnings |
| **Orphaned layers after crashes** | Low | Implement cleanup utility |
| **Layer name conflicts** | Low | Use unique naming convention |
| **Undo/redo breaks layer state** | Medium | Test Maya undo/redo thoroughly |

---

## 8. Success Criteria

✅ **Implementation Complete When:**
1. Display layers created automatically when adding shots
2. Layer visibility toggles correctly when switching shots
3. Assets assigned to layers automatically on import
4. Layers cleaned up when shots are removed
5. All integration tests pass
6. No performance degradation (< 100ms for shot switching)
7. Works in both Python 2.7 (Maya 2022) and Python 3.x (Maya 2023+)

---

## 9. Future Enhancements (Post-Implementation)

- **Layer Color Coding:** Auto-assign colors to layers for visual distinction
- **Layer Isolation Mode:** Isolate single shot, hide all others
- **Layer Templates:** Save/load layer configurations
- **Layer Groups:** Group related shots (e.g., all shots in a sequence)
- **Layer Animation:** Animate layer visibility for shot transitions

---

**Document End**

