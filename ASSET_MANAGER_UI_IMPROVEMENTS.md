# Asset Manager UI Improvements

## Summary

Improved the Asset Manager dialog UI based on user requirements for better usability and workflow.

## Changes Made

### 1. Window Size and Layout
- **Minimum size**: Increased from `(900, 500)` to `(1000, 600)`
- **Default size**: Added resize to `(1200, 700)` for better initial layout
- **Location**: `ui/asset_manager_dialog.py` lines 65-69

### 2. Table Structure
- **Removed column**: "CTX Ready" column (was column 7)
- **New column count**: 8 columns (down from 9)
- **New headers**: `["Type", "Name", "Var", "Dept", "Current", "Latest", "Status", "Action"]`
- **Location**: `ui/asset_manager_dialog.py` lines 80-127

### 3. Column Widths (Optimized for Readability)
- **Type**: 60px (fixed) - Reduced from too wide
- **Name**: Stretch - Fills available space for better readability
- **Var**: 50px (fixed)
- **Dept**: 70px (fixed)
- **Current**: 120px (fixed) - For version dropdown
- **Latest**: 80px (fixed)
- **Status**: 100px (fixed)
- **Action**: 80px (fixed)

### 4. Current Column - Version Dropdown
**Changed from text field to dropdown:**
- Displays all available versions from filesystem
- Auto-populates with versions using `_get_available_versions()`
- **Color coding**:
  - 🟢 **Green background**: Latest version selected
  - 🔴 **Red background**: Outdated version selected
  - ⚪ **Normal**: Other versions
- Connected to `_on_version_changed()` callback for real-time color updates
- **Location**: `ui/asset_manager_dialog.py` lines 473-547

### 5. Action Button Changes
**Changed from "Set" to "Apply":**
- Removed dropdown dialog (`QInputDialog.getItem()`)
- Now directly applies the version selected in the dropdown
- Button text: "Set" → "Apply"
- Connected to `_on_apply_version()` method
- **Location**: `ui/asset_manager_dialog.py` lines 543-547

### 6. Multi-Selection Support
**Enabled multi-selection in table:**
- Selection mode: `ExtendedSelection` (Ctrl+Click, Shift+Click)
- Selection behavior: `SelectRows`
- **Location**: `ui/asset_manager_dialog.py` line 124

### 7. Apply Button (Bottom) - Multi-Selection
**Updated to handle multiple selected assets:**
- Gets selected rows from table
- Shows message if no selection
- Applies version changes only to selected assets
- Refreshes table after applying changes
- **Location**: `ui/asset_manager_dialog.py` lines 1112-1253

### 8. Search/Filter Functionality
**Added real-time text filtering:**
- Search box in header with placeholder text
- Filters assets by: Type, Name, Var, Dept, Current, Latest, Status
- Real-time filtering as you type
- Clear button (X) to reset filter
- Case-insensitive search
- **Location**: `ui/asset_manager_dialog.py` lines 75-94, 178, 566-600

### 9. New Methods Added

#### `_on_search_changed(text)`
- **Purpose**: Handle search box text change
- **Behavior**:
  - Filters table rows in real-time
  - Searches across all asset fields (type, name, var, dept, versions, status)
  - Case-insensitive matching
  - Shows all rows when search is empty
- **Location**: `ui/asset_manager_dialog.py` lines 566-600

#### `_on_version_changed(row, version)`
- **Purpose**: Handle version dropdown change
- **Behavior**: 
  - Updates pending version in asset_data
  - Updates dropdown color based on version status
  - Does NOT apply to Maya yet (only visual feedback)
- **Location**: `ui/asset_manager_dialog.py` lines 549-577

#### `_on_apply_version(row)`
- **Purpose**: Handle Apply button click for single row
- **Behavior**:
  - Gets selected version from dropdown
  - Resolves new file path using PathResolver
  - Updates CTX_Asset node
  - Updates Maya node (reference/proxy)
  - Updates asset_data
- **Location**: `ui/asset_manager_dialog.py` lines 579-605

## User Workflow

### Before:
1. Scroll through all assets manually
2. Click "Set" button
3. Select version from dialog popup
4. Click OK
5. Version applied immediately

### After:
1. **Type in search box** to filter assets (e.g., "CHAR", "v003", "lighting")
2. Select version from dropdown (see color: green=latest, red=outdated)
3. Click "Apply" button to apply single asset
4. OR select multiple assets (Ctrl+Click) and click bottom "Apply" button to apply all
5. **Clear search** to see all assets again

## Benefits

✅ **Better readability**: Name column now has more space
✅ **Faster workflow**: No popup dialogs, direct dropdown selection
✅ **Visual feedback**: Color-coded version status (green/red)
✅ **Batch operations**: Multi-select and apply multiple assets at once
✅ **Better layout**: Optimized column widths for typical asset names
✅ **Larger window**: More comfortable working space (1200x700)
✅ **Quick filtering**: Search/filter assets instantly by typing
✅ **Flexible search**: Searches across all fields (type, name, dept, version, etc.)

## Testing Recommendations

1. Open Asset Manager for a shot with multiple assets
2. **Test search/filter**:
   - Type "CHAR" to filter character assets
   - Type "v003" to filter specific version
   - Type "lighting" to filter by department
   - Clear search (X button) to show all assets
3. Test version dropdown color coding (latest vs outdated)
4. Test single asset Apply button
5. Test multi-selection (Ctrl+Click multiple rows)
6. Test bottom Apply button with multiple selected assets
7. **Test search + multi-select**: Filter assets, then select multiple and apply
8. Verify table refreshes after applying changes
9. Verify Maya nodes update correctly (references, proxies)

