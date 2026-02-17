# Multishot Manager UI Improvements

## Summary

Comprehensive improvements to the Multishot Manager for better usability, workflow efficiency, and multi-shot operations.

## Changes Made

### 1. ✅ Removed Edit/Remove/Save Buttons from Table
- **Before**: 8 columns with individual Edit, Remove, Save buttons
- **After**: 5 columns - removed columns 5, 6, 7
- **New headers**: `["#", "Shot", "Frame Range", "Set Shot", "Version"]`
- **Benefit**: Cleaner UI, more space for shot information
- **Location**: `ui/main_window.py` lines 141-177

### 2. ✅ Added Right-Click Context Menu
- **Trigger**: Right-click on selected shot(s)
- **Menu options**:
  - **Edit Frame Range**: Opens frame range editor
    - Single shot: Opens standard dialog
    - Multiple shots: Opens table-based dialog to edit all at once
  - **Save to Shot Directory**: Saves scene to all selected shots
  - **Remove**: Removes all selected shots
- **Multi-selection support**: All actions work on multiple selected rows
- **Location**: `ui/main_window.py` lines 836-868

### 3. ✅ Enabled Multi-Selection Support
- **Selection mode**: Changed to `ExtendedSelection`
- **How to use**:
  - Ctrl+Click: Add/remove individual shots
  - Shift+Click: Select range of shots
  - Click+Drag: Select multiple shots
- **All actions support multi-selection**: Edit, Remove, Save via context menu
- **Location**: `ui/main_window.py` line 170

### 4. ✅ Fixed Shot Column Width
- **Before**: Shot column stretched to fill available space
- **After**: Fixed width of 300px
- **Benefit**: Consistent layout, no resizing when adding/removing shots
- **Location**: `ui/main_window.py` lines 153-154

### 5. ✅ Implemented Save File to Target Shot
**Workflow**:
1. Saves current Maya scene
2. Copies file to target shot directory (resolved from `shotRoot` template)
3. Renames using `sceneFilePattern` from config with `variant='CTX'`

**Pattern from config**:
```json
"sceneFilePattern": "{ep}_{seq}_{shot}_{dept}_{variant}_{ver}.ma"
```

**Example**:
- Current scene: `Ep04_sq0070_SH0170_lighting_v001.ma`
- Target shot: `SH0180`
- Result: `Ep04_sq0070_SH0180_lighting_CTX_v001.ma`
- Saved to: `V:/SWA/all/scene/Ep04/sq0070/SH0180/`

**Features**:
- Parses dept and version from current scene filename
- Falls back to `dept='lighting'`, `ver='v001'` if parsing fails
- Creates target directory if it doesn't exist
- Shows success message with full path

**Location**: `ui/main_window.py` lines 1296-1402

### 6. ✅ Added Delete All Button
- **Location**: Bottom right of button layout
- **Style**: Red background, white text, bold
- **Confirmation**: Asks for confirmation before deleting
- **Action**: Removes all CTX_Shot nodes and clears table
- **Cleanup**: Clears display layers and resets active shot
- **Location**: `ui/main_window.py` lines 206-207, 1426-1492

### 7. ✅ Added Search/Filter Box
- **Location**: Top right, next to "SHOT CONTEXT CONTROLLER" label
- **Placeholder**: "Filter shots..."
- **Width**: 200px minimum
- **Clear button**: Built-in X button
- **Real-time filtering**: Updates as you type
- **Case-insensitive**: Searches regardless of case
- **Searches**: Project, Episode, Sequence, Shot codes
- **Location**: `ui/main_window.py` lines 116-139, 789-823

### 8. ⏳ Update Launch Scripts (PENDING)
- Need to update: `launch_multishot_manager.py`
- Need to update: `launch_multishot_dockable.py`
- Both scripts should use the updated `MainWindow` class

## User Workflow

### Before:
1. Scroll through all shots manually
2. Click individual Edit/Remove/Save buttons for each shot
3. Repeat for multiple shots

### After:
1. **Type in search box** to filter shots (e.g., "SH0170")
2. **Select multiple shots** (Ctrl+Click or Shift+Click)
3. **Right-click** to open context menu
4. **Choose action**: Edit, Save, or Remove
5. **Action applies to all selected shots**

## Example Usage

### Save Multiple Shots:
```
1. Search for "sq0070" → Shows only shots from sequence 0070
2. Ctrl+Click to select SH0170, SH0180, SH0190
3. Right-click → "Save to Shot Directory"
4. All 3 shots saved with pattern: {ep}_{seq}_{shot}_lighting_CTX_v001.ma
```

### Remove Multiple Shots:
```
1. Shift+Click to select rows 3-7
2. Right-click → "Remove"
3. All 5 shots removed from scene
```

### Delete All Shots:
```
1. Click "Delete All" button (bottom right)
2. Confirm deletion
3. All shots and CTX nodes removed
```

## Benefits

✅ **Cleaner UI**: Removed 3 button columns, more space for shot info
✅ **Faster workflow**: Right-click context menu instead of individual buttons
✅ **Batch operations**: Multi-select and apply actions to multiple shots
✅ **Fixed layout**: Shot column no longer resizes
✅ **Smart save**: Automatically renames files using config pattern
✅ **Quick filtering**: Search/filter shots instantly
✅ **Bulk deletion**: Delete all shots with one click
✅ **Better UX**: Context menu feels more professional

## Technical Details

### Table Structure:
- **Columns**: 5 (down from 8)
- **Selection**: ExtendedSelection mode
- **Context menu**: CustomContextMenu policy
- **Fixed widths**: All columns except # are fixed width

### Save File Logic:
1. Save current scene (`cmds.file(save=True)`)
2. Get `sceneFilePattern` from config
3. Parse dept/version from current filename
4. Format new filename with `variant='CTX'`
5. Resolve `shotRoot` using PathResolver
6. Copy file with `shutil.copy2()`
7. Show success message

### Search Filter Logic:
- Builds searchable string from: `project_ep_seq_shot`
- Case-insensitive matching
- Hides non-matching rows
- Shows all rows when search is empty

## Testing Recommendations

1. **Test multi-selection**:
   - Ctrl+Click multiple shots
   - Shift+Click range of shots
   - Verify selection highlights

2. **Test context menu**:
   - Right-click on single shot
   - Right-click on multiple shots
   - Test Edit, Save, Remove actions

3. **Test save functionality**:
   - Save to single shot
   - Save to multiple shots
   - Verify filename pattern
   - Check target directory creation

4. **Test search filter**:
   - Type "SH0170" → Should show only that shot
   - Type "sq0070" → Should show all shots in that sequence
   - Clear search → Should show all shots

5. **Test Delete All**:
   - Add multiple shots
   - Click "Delete All"
   - Confirm deletion
   - Verify all shots removed

## Recent Fixes (2026-02-17)

### ✅ Fixed Save Shot Error (Round 1)
- **Issue**: `'ProjectConfig' object has no attribute 'get_render_settings'`
- **Fix**: Changed to use `get_render_settings_config()` method
- **Location**: `ui/main_window.py` line 1333

### ✅ Fixed Save Shot Error (Round 2)
- **Issue**: `_parse_scene_filename() takes 1 positional argument but 2 were given`
- **Fix**: Method doesn't take filename parameter, it queries Maya directly
- **Changed**: `dept, version = self._parse_scene_filename(current_scene)` → `parsed = self._parse_scene_filename()`
- **Location**: `ui/main_window.py` lines 1487-1498

### ✅ Fixed Save Target Path (Round 3)
- **Issue**: Save target was using wrong template (`shotRoot` instead of `shotWork`)
- **Fix**: Changed to use `shotWork` template with `dept` in context
- **Template**: `"shotWork": "$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/version"`
- **Example path**: `V:/SWA/all/scene/Ep04/sq0070/SH0170/lighting/version/`
- **Location**: `ui/main_window.py` lines 1556-1583

### ✅ Improved Window Resize
- **Enhancement**: Better window sizing to fit table content
- **Features**:
  - Limits visible rows to 15 (adds scrollbar if more)
  - Minimum height: 400px
  - Maximum height: 80% of screen
  - Width range: 800-1200px
  - Accounts for search box and all UI elements
- **Location**: `ui/main_window.py` lines 748-796

### ✅ Multi-Select Edit Frame Range
- **Feature**: Table-based dialog for editing multiple shots at once
- **How it works**:
  - Select multiple shots (Ctrl+Click or Shift+Click)
  - Right-click → "Edit Frame Range"
  - Shows table with all selected shots
  - Edit Start Frame, End Frame, FPS for each shot
  - Click "Apply" to update all shots
- **Benefits**: Edit 10+ shots in one dialog instead of opening 10 separate dialogs
- **Location**: `ui/main_window.py` lines 1248-1370

## Files Modified

- `ui/main_window.py` (lines 116-139, 141-177, 184-209, 213-216, 723-738, 748-796, 836-868, 1203-1370, 1330-1340, 1447-1553, 1577-1647)

## Files Pending

- `launch_multishot_manager.py` (needs update)
- `launch_multishot_dockable.py` (needs update)

