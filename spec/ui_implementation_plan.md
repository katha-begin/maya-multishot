# UI Implementation Plan - Filesystem Discovery Phase

## Overview

This document provides a detailed task breakdown for implementing the UI module with **filesystem discovery only**. No CTX node integration at this stage.

---

## Scope & Requirements

### ✅ In Scope
- Integrate with `config/project_config.py` (ProjectConfig class)
- Implement filesystem scanning to discover shots and assets
- Display shots from directory structure (e.g., `V:/SWA/all/scene/Ep04/sq0070/SH####/`)
- Display assets from publish directories (e.g., `V:/SWA/all/scene/Ep04/sq0070/SH0170/anim/publish/v###/`)
- Project/Episode/Sequence navigation
- Shot selection with radio buttons
- Asset table with sortable columns
- Color-coded status based on file existence

### ❌ Out of Scope (Future Phase)
- CTX custom nodes integration
- ShotManager/AssetManager integration
- Import/Export functionality
- Shot/Asset creation
- Scene conversion

---

## Implementation Order

### Task 1: [P4-UI-01] Filesystem Discovery Module
**File:** `ui/filesystem_discovery.py`
**Duration:** 2-3 days
**Priority:** HIGH (Must complete first)

**Functions to Implement:**

1. **`scan_shots_from_filesystem(base_path, ep, seq)`**
   - Scans: `{base_path}/{ep}/{seq}/SH####/`
   - Returns: `['SH0170', 'SH0180', 'SH0190']`
   - Handles missing directories gracefully

2. **`scan_assets_from_filesystem(publish_path, pattern_manager)`**
   - Scans: `{publish_path}/v###/`
   - Parses filenames using PatternManager
   - Returns: List of asset dicts (see data structure below)
   - Handles invalid filenames gracefully

3. **`get_available_versions(publish_path, asset_id)`**
   - Scans for: `v001/`, `v002/`, `v003/`
   - Returns: `['v003', 'v002', 'v001']` (descending)

4. **`get_shot_asset_count(shot_path)`**
   - Counts assets in shot's publish directories
   - Returns: Integer count

**Data Structures:**

```python
# Shot data
{
    'shot_code': 'SH0170',
    'ep': 'Ep04',
    'seq': 'sq0070',
    'path': 'V:/SWA/all/scene/Ep04/sq0070/SH0170',
    'asset_count': 12
}

# Asset data
{
    'asset_type': 'CHAR',
    'asset_name': 'CatStompie',
    'variant': '001',
    'version': 'v003',
    'dept': 'anim',
    'path': 'V:/SWA/.../Ep04_sq0070_SH0170__CHAR_CatStompie_001.abc',
    'ext': 'abc',
    'filename': 'Ep04_sq0070_SH0170__CHAR_CatStompie_001.abc'
}
```

**Tests:** 10+ unit tests

---

### Task 2: [P4-UI-03] Shot Widget
**File:** `ui/shot_widget.py`
**Duration:** 2-3 days
**Priority:** HIGH
**Dependencies:** Task 1

**Components:**

1. **ShotWidget (QWidget)**
   - Contains QListWidget with custom item widgets
   - Radio button for selection (QRadioButton in QButtonGroup)
   - Shot code label
   - Asset count label
   - Frame range label (placeholder)

2. **Methods:**
   - `load_shots(shots_data)` - Populate list from filesystem data
   - `get_selected_shot()` - Return selected shot code
   - Signal: `shot_selected(str)` - Emitted when selection changes

**Layout:**
```
+-----------------------------------------------------------------------+
|  SHOTS IN SCENE                                            [+ Add]    |
|  +-------------------------------------------------------------------+|
|  | (*) SH0170   12 assets    [1001-1050]                            ||
|  | ( ) SH0180    8 assets    [1001-1062]                            ||
|  +-------------------------------------------------------------------+|
+-----------------------------------------------------------------------+
```

---

### Task 3: [P4-UI-04] Asset Widget
**File:** `ui/asset_widget.py`
**Duration:** 3-5 days
**Priority:** HIGH
**Dependencies:** Task 1

**Components:**

1. **AssetWidget (QWidget)**
   - Contains QTableWidget with 6 columns
   - Columns: Type, Name, Var, Dept, Ver, Status
   - Status column: QLabel with colored circle (●)

2. **Methods:**
   - `load_assets(assets_data)` - Populate table from filesystem data
   - `get_selected_assets()` - Return list of selected asset dicts
   - Support multi-row selection
   - Support sortable columns

**Layout:**
```
+-----------------------------------------------------------------------+
|  ASSETS IN SH0170                            [+ Import] [Convert]     |
|  +-------------------------------------------------------------------+|
|  | Type  | Name       | Var | Dept | Ver  | Status                  ||
|  |-------|------------|-----|------|------|-------------------------||
|  | CHAR  | CatStompie | 001 | anim | v003 | ● Valid                 ||
|  +-------------------------------------------------------------------+|
+-----------------------------------------------------------------------+
```

**Status Colors:**
- 🟢 Green: File exists (`os.path.exists()` returns True)
- 🔴 Red: File not found

---

### Task 4: [P4-UI-02] Main Window
**File:** `ui/main_window.py`
**Duration:** 3-5 days
**Priority:** HIGH
**Dependencies:** Tasks 2, 3

**Components:**

1. **MainWindow (QMainWindow)**
   - Dockable in Maya workspace
   - Size: 800x600 pixels
   - Title: "Context Manager (Filesystem Mode)"

2. **Header Section:**
   - Project selector (QComboBox) - from ProjectConfig
   - Episode selector (QComboBox) - from config
   - Sequence selector (QComboBox) - from config
   - Settings button (QPushButton) - placeholder
   - Help button (QPushButton) - placeholder

3. **Body:**
   - ShotWidget instance
   - AssetWidget instance

4. **Footer:**
   - Status bar (QStatusBar)

5. **Methods:**
   - `refresh_ui()` - Reload data from filesystem
   - `on_project_changed()` - Update ep/seq lists
   - `on_shot_selected()` - Update asset table

**Data Flow:**
```
User selects Project/Ep/Seq
    ↓
scan_shots_from_filesystem()
    ↓
ShotWidget.load_shots()
    ↓
User selects shot
    ↓
scan_assets_from_filesystem()
    ↓
AssetWidget.load_assets()
```

---

### Task 5: [P4-UI-05] Integration Tests
**File:** `tests/test_ui_integration.py`
**Duration:** 1-2 days
**Priority:** HIGH
**Dependencies:** Tasks 1-4

**Test Scenarios:**

1. `test_main_window_loads_projects()` - Project selector populated
2. `test_shot_widget_displays_discovered_shots()` - Shots from filesystem
3. `test_asset_widget_displays_discovered_assets()` - Assets from filesystem
4. `test_shot_selection_updates_asset_table()` - Selection triggers update
5. `test_status_colors_reflect_file_existence()` - Colors correct
6. `test_ui_refresh_after_filesystem_changes()` - Refresh works

**Coverage:** 80%+ for UI modules

---

## Expected Data Flow

```
Filesystem
    ↓
scan_shots_from_filesystem() → Shot Data (list of dicts)
    ↓
ShotWidget.load_shots(shot_data)
    ↓
Display shots with radio buttons
    ↓
User clicks shot radio button
    ↓
MainWindow.on_shot_selected(shot_code)
    ↓
scan_assets_from_filesystem() → Asset Data (list of dicts)
    ↓
AssetWidget.load_assets(asset_data)
    ↓
Display assets in table with status colors
```

---

## Files to Create

1. `ui/__init__.py` - Package initialization
2. `ui/filesystem_discovery.py` - Discovery functions (Task 1)
3. `ui/shot_widget.py` - Shot list widget (Task 2)
4. `ui/asset_widget.py` - Asset table widget (Task 3)
5. `ui/main_window.py` - Main window (Task 4)
6. `tests/test_ui_integration.py` - Integration tests (Task 5)

**Total:** 6 files

---

## Success Criteria

- [ ] UI opens as dockable Maya window
- [ ] Project selector loads from config
- [ ] Episode/Sequence selectors populate from config
- [ ] Shot list displays shots discovered from filesystem
- [ ] Asset table displays assets discovered from filesystem
- [ ] Selecting shot updates asset table
- [ ] Status colors reflect file existence (green/red)
- [ ] All tests pass (80%+ coverage)
- [ ] No errors in Maya script editor
- [ ] UI is responsive (no freezing)

---

## Timeline

| Task | Duration | Start | End |
|------|----------|-------|-----|
| [P4-UI-01] Filesystem Discovery | 2-3 days | Day 1 | Day 3 |
| [P4-UI-03] Shot Widget | 2-3 days | Day 4 | Day 6 |
| [P4-UI-04] Asset Widget | 3-5 days | Day 7 | Day 11 |
| [P4-UI-02] Main Window | 3-5 days | Day 12 | Day 16 |
| [P4-UI-05] Integration Tests | 1-2 days | Day 17 | Day 18 |

**Total Duration:** 11-18 days (2-3 weeks)

---

## Next Steps After Completion

Once this phase is complete, the next phase will be:

**Phase 4B: CTX Node Integration**
- Implement CTX custom nodes
- Implement ShotManager/AssetManager tools
- Integrate UI with CTX nodes
- Add import/export functionality
- Add shot/asset creation dialogs

See `spec/tasks.md` for full task list.

