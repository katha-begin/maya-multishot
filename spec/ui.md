# UI Design & User Flow Documentation
**Based on Nuke Multishot Manager Design**

## Table of Contents
1. [Main Window Architecture](#1-main-window-architecture)
2. [Add Shots Dialog](#2-add-shots-dialog)
3. [Asset Manager Dialog](#3-asset-manager-dialog)
4. [User Workflows](#4-user-workflows)
5. [CTX Node Integration](#5-ctx-node-integration)
6. [Implementation Plan](#6-implementation-plan)

---

## 1. Main Window Architecture

The **Multishot Manager** is a **dockable Maya window** that manages multiple shots in a single scene.

### 1.1 Main Window Layout

```
+================================================================================+
|  Multishot Manager                                    [Refresh]    [_] [□] [X] |
+================================================================================+
|  Current Shot: SWA_s004_sq0070_SH0140                                          |
+--------------------------------------------------------------------------------+
|                                                                                |
|  SHOT CONTEXT CONTROLLER                                                       |
|  +----------------------------------------------------------------------------+|
|  | # | Shot                      | Set Shot | Version | Remove | Save        ||
|  |---|---------------------------|----------|---------|--------|-------------||
|  | 1 | SWA_s004_sq0070_SH0140    | [Active] | v003    | [X]    | [Save]      ||
|  | 2 | SWA_s004_sq0070_SH0150    | [Set]    | v002    | [X]    | [Save]      ||
|  | 3 | SWA_s004_sq0080_SH0160    | [Set]    | v001    | [X]    | [Save]      ||
|  +----------------------------------------------------------------------------+|
|                                                                                |
+--------------------------------------------------------------------------------+
|                                                                                |
|  [Add Shots]  [Update All Versions]  [Validate All]  [Save All]               |
|                                                                                |
+--------------------------------------------------------------------------------+
|  Status: Ready                                                                 |
+================================================================================+
```

### 1.2 Window Components

#### **Title Bar**
- **Title:** "Multishot Manager"
- **Refresh Button:** Refresh shot list and versions from CTX nodes
- **Dockable:** Can be docked in Maya workspace

#### **Current Shot Display**
- Shows the currently active shot context
- Format: `PROJECT_EPISODE_SEQUENCE_SHOT` (e.g., `SWA_s004_sq0070_SH0140`)
- Updates when "Set Shot" button is clicked

#### **Shot Context Controller Table**

**Purpose:** Manage all shots added to the current Maya scene

**Columns:**

1. **# (Row Number)**
   - Type: Integer
   - Auto-incremented
   - Read-only

2. **Shot (Shot Path)**
   - Type: String
   - Format: `PROJECT_EPISODE_SEQUENCE_SHOT`
   - Example: `SWA_s004_sq0070_SH0140`
   - Read-only
   - Source: CTX node shot context

3. **Set Shot (Active Button)**
   - Type: Button
   - States:
     - `[Active]` - Blue/highlighted, current active shot
     - `[Set]` - Gray/normal, inactive shot
   - Action: Set this shot as active context
   - Effect: Updates scene tokens ($ep, $seq, $shot)

4. **Version (Version Selector)**
   - Type: Button/Label
   - Format: `v###` (e.g., `v001`, `v002`, `v003`)
   - Action: Click to open Asset Manager dialog
   - Shows current shot version

5. **Remove (Delete Button)**
   - Type: Button
   - Icon: `[X]`
   - Action: Remove shot from scene
   - Confirmation: "Remove shot SH0140 from scene?"
   - Effect: Deletes CTX node and associated data

6. **Save (Save Button)**
   - Type: Button
   - Label: `[Save]`
   - Action: Save scene to shot's version directory
   - Path: Resolved from template using shot context
   - Example: `V:/SWA/all/scene/Ep04/sq0070/SH0140/anim/publish/v003/`

#### **Action Buttons (Bottom Section)**

**Buttons:**

1. **Add Shots** (QPushButton)
   - Action: Open "Add Shots Dialog"
   - Icon: Plus icon
   - Opens tree view to select multiple shots

2. **Update All Versions** (QPushButton)
   - Action: Update all shots to latest versions
   - Opens Asset Manager for each shot
   - Batch operation

3. **Validate All** (QPushButton)
   - Action: Validate all shot contexts and assets
   - Checks:
     - CTX nodes exist
     - Shot paths are valid
     - Asset files exist
   - Shows validation report

4. **Save All** (QPushButton)
   - Action: Save scene to all shot directories
   - Iterates through all shots
   - Saves to each shot's version directory
   - Shows progress bar

#### **Status Bar**

**Components:**
- Status message (QLabel): Shows current operation status
- Examples:
  - "Ready"
  - "Shot SH0140 set as active"
  - "Saving to shot SH0140..."
  - "3 shots in scene"

### 1.3 Key Features

**Multi-Shot Management:**
- Multiple shots can exist in one scene
- Only ONE shot is active at a time
- Active shot determines context tokens ($ep, $seq, $shot)
- Each shot has independent version

**Shot Context:**
- Stored in CTX custom nodes
- Contains: project, episode, sequence, shot, version
- Persists with Maya scene file

**Version Management:**
- Each shot has its own version
- Click "Version" button to open Asset Manager
- Asset Manager shows all assets for that shot
- Can set different versions per shot

**Save Workflow:**
- "Save" button saves to specific shot's directory
- "Save All" button saves to all shots' directories
- Path resolved from template: `$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish/$ver/`

---

## 2. Add Shots Dialog

**Purpose:** Select and add multiple shots to the current Maya scene

### 2.1 Dialog Layout

```
+================================================================================+
|  Add Shots                                                          [X]        |
+================================================================================+
|                                                                                |
|  Select Shots to Add                                                           |
|                                                                                |
|  +--------------------------------------------------------------------------+  |
|  | Shot Structure                                                           |  |
|  | +----------------------------------------------------------------------+ |  |
|  | | ▼ SWA                                                                | |  |
|  | |   ▼ Ep01                                                             | |  |
|  | |     ▼ sq0010                                                         | |  |
|  | |       □ SH0110                                                       | |  |
|  | |       □ SH0120                                                       | |  |
|  | |       □ SH0130                                                       | |  |
|  | |     ▼ sq0020                                                         | |  |
|  | |       □ SH0210                                                       | |  |
|  | |   ▼ Ep04                                                             | |  |
|  | |     ▼ sq0070                                                         | |  |
|  | |       ☑ SH0140  (selected - orange highlight)                       | |  |
|  | |       ☑ SH0150  (selected - orange highlight)                       | |  |
|  | |       □ SH0160                                                       | |  |
|  | |     ▼ sq0080                                                         | |  |
|  | |       □ SH0170                                                       | |  |
|  | +----------------------------------------------------------------------+ |  |
|  +--------------------------------------------------------------------------+  |
|                                                                                |
|  [Select All]  [Deselect All]                                                  |
|                                                                                |
|  [Add Selected]  [Cancel]                                                      |
|                                                                                |
+================================================================================+
```

### 2.2 Dialog Components

#### **Shot Structure Tree (QTreeWidget)**

**Features:**
- Hierarchical tree view: Project → Episode → Sequence → Shot
- Multi-selection enabled (checkboxes)
- Collapsible/expandable nodes
- Orange highlight for selected items
- Data source: Filesystem discovery or config cache

**Tree Structure:**
```
Project (SWA)
├── Episode (Ep01)
│   ├── Sequence (sq0010)
│   │   ├── Shot (SH0110) ☐
│   │   ├── Shot (SH0120) ☐
│   │   └── Shot (SH0130) ☐
│   └── Sequence (sq0020)
│       └── Shot (SH0210) ☐
└── Episode (Ep04)
    ├── Sequence (sq0070)
    │   ├── Shot (SH0140) ☑ (selected)
    │   ├── Shot (SH0150) ☑ (selected)
    │   └── Shot (SH0160) ☐
    └── Sequence (sq0080)
        └── Shot (SH0170) ☐
```

**Interactions:**
- Click checkbox: Select/deselect shot
- Click node: Expand/collapse
- Ctrl+Click: Multi-select
- Shift+Click: Range select

#### **Action Buttons**

1. **Select All** (QPushButton)
   - Action: Check all shot checkboxes
   - Expands all nodes

2. **Deselect All** (QPushButton)
   - Action: Uncheck all shot checkboxes

3. **Add Selected** (QPushButton)
   - Action: Add all selected shots to scene
   - Creates CTX node for each shot
   - Sets first shot as active
   - Closes dialog

4. **Cancel** (QPushButton)
   - Action: Close dialog without changes

### 2.3 Add Shots Workflow

**Step 1:** User clicks "Add Shots" button in main window

**Step 2:** Dialog opens with shot tree structure

**Step 3:** User navigates tree and selects shots (multi-select)

**Step 4:** User clicks "Add Selected"

**Step 5:** System creates CTX nodes for each selected shot
- Node name: `CTX_SH####`
- Stores: project, episode, sequence, shot, version (v001)

**Step 6:** First shot is set as active context

**Step 7:** Dialog closes, main window updates with new shots

---

## 3. Asset Manager Dialog

**Purpose:** Manage assets and versions for a specific shot

**Triggered by:** Clicking "Version" button in Shot Context Controller table

### 3.1 Dialog Layout

```
+================================================================================+
|  Asset Manager - SWA_s004_sq0070_SH0140 (v003)                     [X]        |
+================================================================================+
|                                                                                |
|  ASSETS IN SHOT                                                                |
|  +----------------------------------------------------------------------------+|
|  | Type  | Name           | Var | Dept | Current | Latest | Status | Action ||
|  |-------|----------------|-----|------|---------|--------|--------|--------||
|  | CHAR  | CatStompie     | 001 | anim | v003    | v003   | ✓      | [Set]  ||
|  | CHAR  | CatStompie     | 002 | anim | v002    | v003   | Update | [Set]  ||
|  | CHAR  | DogBounce      | 001 | anim | v002    | v002   | ✓      | [Set]  ||
|  | PROP  | TreeBig        | 001 | anim | v001    | v002   | Update | [Set]  ||
|  +----------------------------------------------------------------------------+|
|                                                                                |
|  [Import Asset]  [Update All to Latest]  [Validate All]                        |
|                                                                                |
|  [Apply]  [Cancel]                                                             |
|                                                                                |
+================================================================================+
```

### 3.2 Dialog Components

#### **Asset Table (QTableWidget)**

**Columns:**

1. **Type** (str)
   - Asset type: CHAR, PROP, SET, VEH, ENV, FX
   - Read-only

2. **Name** (str)
   - Asset name: CatStompie, DogBounce, TreeBig
   - Read-only

3. **Var** (str)
   - Variant number: 001, 002, 003
   - Read-only

4. **Dept** (str)
   - Department: anim, model, rig, fx, light
   - Read-only

5. **Current** (str)
   - Current version in scene: v001, v002, v003
   - Read-only

6. **Latest** (str)
   - Latest version available on disk: v001, v002, v003
   - Scanned from publish directories
   - Read-only

7. **Status** (widget)
   - Visual indicator:
     - ✓ (Green): Up to date (Current == Latest)
     - Update (Yellow): Update available (Current < Latest)
     - Missing (Red): File not found
   - Read-only

8. **Action** (button)
   - **[Set]** button: Opens version selector dropdown
   - Allows selecting specific version
   - Updates asset to selected version

#### **Action Buttons**

1. **Import Asset** (QPushButton)
   - Action: Opens Import Asset Dialog (simplified)
   - Allows adding new assets to the shot
   - Fields: Department, Asset Type, Asset Name, Variant, Version
   - Creates CTX_Asset node and imports file

2. **Update All to Latest** (QPushButton)
   - Action: Updates all assets to latest versions
   - Only updates assets with "Update" status
   - Batch operation

3. **Validate All** (QPushButton)
   - Action: Validates all asset paths
   - Checks file existence
   - Updates status column

4. **Apply** (QPushButton)
   - Action: Apply all version changes
   - Updates CTX nodes
   - Reloads assets in scene
   - Closes dialog

5. **Cancel** (QPushButton)
   - Action: Close dialog without applying changes

### 3.3 Asset Manager Workflow

**Step 1:** User clicks "Version" button for a shot in main window

**Step 2:** Asset Manager dialog opens showing all assets in that shot

**Step 3:** User reviews asset versions:
- Green ✓: Asset is up to date
- Yellow "Update": Newer version available
- Red "Missing": File not found

**Step 4:** User can:
- Click **[Set]** button to select specific version
- Click **Update All to Latest** to update all assets
- Click **Import Asset** to add new assets

**Step 5:** User clicks **Apply** to save changes

**Step 6:** System updates CTX nodes and reloads assets

**Step 7:** Dialog closes, main window updates

---

## 4. User Workflows

### 4.1 Workflow: Add Multiple Shots to Scene

**Goal:** Add multiple shots to the current Maya scene

**Steps:**

1. User opens Multishot Manager window
2. User clicks **"Add Shots"** button
3. Add Shots Dialog opens with tree structure
4. User navigates tree: Project → Episode → Sequence → Shot
5. User selects multiple shots (checkboxes)
6. User clicks **"Add Selected"**
7. System creates CTX_Shot node for each selected shot
8. First shot is set as active context
9. Dialog closes
10. Main window updates with new shots in table

**Result:** Multiple shots are now in the scene, first shot is active

### 4.2 Workflow: Set Active Shot

**Goal:** Change which shot's context is active

**Steps:**

1. User views Shot Context Controller table
2. User identifies desired shot (e.g., SH0150)
3. User clicks **"[Set]"** button for that shot
4. System updates active shot
5. System updates scene tokens ($ep, $seq, $shot)
6. Button changes to **"[Active]"** (blue/highlighted)
7. Previous active shot button changes to **"[Set]"** (gray)
8. "Current Shot" display updates

**Result:** New shot is active, scene tokens updated

### 4.3 Workflow: Manage Asset Versions

**Goal:** Update asset versions for a specific shot

**Steps:**

1. User views Shot Context Controller table
2. User clicks **"Version"** button for desired shot
3. Asset Manager dialog opens
4. User reviews asset status:
   - Green ✓: Up to date
   - Yellow "Update": Newer version available
   - Red "Missing": File not found
5. User clicks **"[Set]"** button for specific asset
6. Version selector dropdown appears
7. User selects desired version
8. User clicks **"Apply"**
9. System updates CTX nodes and reloads assets
10. Dialog closes

**Result:** Asset versions updated for that shot

### 4.4 Workflow: Save to Shot Directory

**Goal:** Save scene to specific shot's version directory

**Steps:**

1. User views Shot Context Controller table
2. User clicks **"[Save]"** button for desired shot
3. System resolves save path from template
4. Path example: `V:/SWA/all/scene/Ep04/sq0070/SH0140/anim/publish/v003/`
5. System creates directories if needed
6. System saves Maya scene file
7. Status bar shows: "Saved to SH0140 v003"

**Result:** Scene saved to shot's version directory

### 4.5 Workflow: Save to All Shots

**Goal:** Save scene to all shots' version directories

**Steps:**

1. User clicks **"Save All"** button
2. System iterates through all shots in table
3. For each shot:
   - Resolves save path from template
   - Creates directories if needed
   - Saves Maya scene file
4. Progress bar shows: "Saving 2/3 shots..."
5. Status bar shows: "Saved to 3 shots"

**Result:** Scene saved to all shots' directories

---

## 5. CTX Node Integration

### 5.1 CTX Node Architecture

**CTX_Shot Node:**
- **Purpose:** Store shot context data
- **Type:** Custom Maya node (network node)
- **Naming:** `CTX_SH####` (e.g., `CTX_SH0140`)
- **Attributes:**
  - `project` (string): Project code (e.g., "SWA")
  - `episode` (string): Episode code (e.g., "Ep04")
  - `sequence` (string): Sequence code (e.g., "sq0070")
  - `shot` (string): Shot code (e.g., "SH0140")
  - `version` (string): Shot version (e.g., "v003")
  - `isActive` (bool): Whether this shot is active
  - `frameStart` (int): Start frame
  - `frameEnd` (int): End frame

**CTX_Asset Node:**
- **Purpose:** Store asset metadata and link to Maya nodes
- **Type:** Custom Maya node (network node)
- **Naming:** `CTX_ASSET_TYPE_Name_Var_SH####` (e.g., `CTX_ASSET_CHAR_CatStompie_001_SH0140`)
- **Attributes:**
  - `assetType` (string): Asset type (CHAR, PROP, SET, etc.)
  - `assetName` (string): Asset name (CatStompie, DogBounce, etc.)
  - `variant` (string): Variant number (001, 002, etc.)
  - `department` (string): Department (anim, model, rig, etc.)
  - `version` (string): Asset version (v001, v002, v003)
  - `mayaNode` (message): Link to Maya node (aiStandIn, reference, etc.)
  - `shotNode` (message): Link to parent CTX_Shot node

### 5.2 Active Shot Token System

**How Active Shot Works:**

1. **Only ONE shot is active at a time**
   - Active shot has `isActive = True`
   - All other shots have `isActive = False`

2. **Active shot sets scene tokens:**
   - `$ep` = Active shot's episode (e.g., "Ep04")
   - `$seq` = Active shot's sequence (e.g., "sq0070")
   - `$shot` = Active shot's shot code (e.g., "SH0140")
   - `$ver` = Active shot's version (e.g., "v003")

3. **Clicking "Set Shot" button:**
   - Sets clicked shot's `isActive = True`
   - Sets all other shots' `isActive = False`
   - Updates scene tokens
   - Updates "Current Shot" display
   - Button changes to "[Active]" (blue)

### 5.3 Node Naming Conventions

**CTX_Shot Nodes:**
- Format: `CTX_SH####`
- Examples:
  - `CTX_SH0140`
  - `CTX_SH0150`
  - `CTX_SH0160`

**CTX_Asset Nodes:**
- Format: `CTX_ASSET_TYPE_Name_Var_SH####`
- Examples:
  - `CTX_ASSET_CHAR_CatStompie_001_SH0140`
  - `CTX_ASSET_PROP_TreeBig_001_SH0150`
  - `CTX_ASSET_SET_ForestGround_001_SH0160`

**Display Layers:**
- Format: `CTX_EPISODE_SEQUENCE_SHOT`
- Examples:
  - `CTX_Ep04_sq0070_SH0140`
  - `CTX_Ep04_sq0070_SH0150`
  - `CTX_Ep04_sq0080_SH0160`

### 5.4 Integration with Existing Modules

**ShotManager Integration:**
- `ShotManager.create_shot()`: Creates CTX_Shot node
- `ShotManager.set_active_shot()`: Sets active shot and updates tokens
- `ShotManager.get_active_shot()`: Returns active CTX_Shot node
- `ShotManager.get_all_shots()`: Returns list of all CTX_Shot nodes
- `ShotManager.remove_shot()`: Deletes CTX_Shot node and associated assets

**AssetManager Integration:**
- `AssetManager.import_asset()`: Creates CTX_Asset node and imports file
- `AssetManager.get_shot_assets()`: Returns assets for specific shot
- `AssetManager.update_asset_version()`: Updates asset version
- `AssetManager.remove_asset()`: Deletes CTX_Asset node and Maya node

**NodeManager Integration:**
- `NodeManager.create_ctx_node()`: Creates custom CTX nodes
- `NodeManager.get_ctx_nodes()`: Queries CTX nodes by type
- `NodeManager.link_nodes()`: Links CTX_Asset to Maya nodes

---

## 6. Implementation Plan

### 6.1 Phase 4B Tasks (UI Redesign & CTX Integration)

**Task 4B.1: Rewrite Main Window**
- Remove header dropdowns (Project/Episode/Sequence)
- Change title to "Multishot Manager"
- Add "Current Shot" display
- Replace shot list with Shot Context Controller table
- Add table columns: #, Shot, Set Shot, Version, Remove, Save
- Add action buttons: Add Shots, Update All Versions, Validate All, Save All
- Make window properly dockable in Maya
- Integrate with ShotManager to query CTX nodes

**Task 4B.2: Implement Add Shots Dialog**
- Create tree view widget (QTreeWidget)
- Implement hierarchical structure: Project → Episode → Sequence → Shot
- Add multi-selection with checkboxes
- Add Select All / Deselect All buttons
- Add Add Selected / Cancel buttons
- Implement filesystem discovery or config cache data source
- Integrate with ShotManager to create CTX nodes

**Task 4B.3: Implement Asset Manager Dialog**
- Create asset table widget (QTableWidget)
- Add columns: Type, Name, Var, Dept, Current, Latest, Status, Action
- Implement version scanning from publish directories
- Add status indicators (Green ✓, Yellow Update, Red Missing)
- Add [Set] button with version selector dropdown
- Add Import Asset / Update All to Latest / Validate All buttons
- Integrate with AssetManager to update CTX nodes

**Task 4B.4: Implement Set Shot Functionality**
- Add "Set Shot" button click handler
- Implement active shot switching logic
- Update CTX_Shot.isActive attribute
- Update scene tokens ($ep, $seq, $shot, $ver)
- Update button states ([Active] vs [Set])
- Update "Current Shot" display
- Integrate with ShotManager.set_active_shot()

**Task 4B.5: Implement Version Management**
- Add "Version" button click handler
- Open Asset Manager dialog for specific shot
- Query assets from CTX nodes
- Scan filesystem for latest versions
- Implement version comparison logic
- Update asset versions in CTX nodes
- Reload assets in Maya scene

**Task 4B.6: Implement Save Functionality**
- Add "Save" button click handler (per shot)
- Resolve save path from template
- Create directories if needed
- Save Maya scene file to shot directory
- Add "Save All" button click handler
- Iterate through all shots and save to each directory
- Show progress bar for batch operations

**Task 4B.7: Implement Remove Shot Functionality**
- Add "Remove" button click handler
- Show confirmation dialog
- Delete CTX_Shot node
- Delete associated CTX_Asset nodes
- Delete display layer
- Remove shot from table
- Update active shot if removed shot was active

**Task 4B.8: Testing & Integration**
- Test multi-shot workflow
- Test active shot switching
- Test version management
- Test save functionality
- Test with existing modules (ShotManager, AssetManager, NodeManager)
- Update unit tests
- Update documentation

### 6.2 File Changes Required

**Files to Rewrite:**
1. `ui/main_window.py` - Complete rewrite for new design
2. `ui/add_shot_dialog.py` - Rewrite for tree view with multi-selection
3. `ui/asset_manager_dialog.py` - New file for Asset Manager

**Files to Remove:**
1. `ui/shot_widget.py` - No longer needed (integrated into main window)
2. `ui/asset_widget.py` - No longer needed (replaced by Asset Manager)
3. `ui/import_asset_dialog.py` - Functionality moved to Asset Manager
4. `ui/convert_scene_dialog.py` - May not be needed
5. `ui/filesystem_discovery.py` - May not be needed

**Files to Update:**
1. `ui/__init__.py` - Update imports
2. `tools/shot_manager.py` - Add methods for UI integration
3. `tools/asset_manager.py` - Add methods for UI integration

### 6.3 Testing Strategy

**Unit Tests:**
- Test CTX node creation and querying
- Test active shot switching
- Test version management
- Test save path resolution

**Integration Tests:**
- Test Add Shots workflow
- Test Set Shot workflow
- Test Asset Manager workflow
- Test Save workflow
- Test Remove Shot workflow

**Manual Tests:**
- Test UI docking in Maya
- Test multi-shot scene with 3+ shots
- Test version updates across multiple shots
- Test save to all shots
- Test with real filesystem structure

---

## 7. Summary

This UI design is based on the Nuke Multishot Manager pattern and provides:

1. **Multi-Shot Management:** Add multiple shots to one scene
2. **Active Shot System:** Set which shot's context is active
3. **Version Management:** Manage asset versions per shot
4. **Save Workflow:** Save to specific shot or all shots
5. **CTX Integration:** Full integration with CTX nodes and existing modules

**Key Differences from Old Design:**
- ❌ Old: Filesystem discovery of shots
- ✅ New: CTX node-based shot management
- ❌ Old: Header dropdowns in main window
- ✅ New: Dropdowns only in Add Shots Dialog
- ❌ Old: Simple shot list
- ✅ New: Shot Context Controller table with actions
- ❌ Old: Separate Import Asset dialog
- ✅ New: Integrated Asset Manager dialog
- ❌ Old: Not dockable
- ✅ New: Properly dockable in Maya

**Next Steps:**
1. Review and approve this specification
2. Implement Phase 4B tasks one by one
3. Test each component thoroughly
4. Update documentation and tests

---

**End of UI Design & User Flow Documentation**


