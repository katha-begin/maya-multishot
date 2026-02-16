# Version Update Fixes - Summary

## Issues Fixed

### Issue 1: Setting Version Doesn't Update Asset Path
**Problem:** When setting version from v005 to v006 in active shot SH0140, the asset path doesn't change to the new version.

**Root Cause:** The version was being set on the CTX_Asset node and `update_asset_path()` was being called, but the UI table wasn't refreshing to show the change.

**Solution:** Added `self._populate_asset_table()` after successful path update to refresh the UI.

**File:** `ui/asset_manager_dialog.py` (line 583)

```python
if success:
    logger.info("Successfully updated asset path to version {}".format(version))
    # Refresh the table to show the update
    self._populate_asset_table()  # <-- ADDED THIS
    QtWidgets.QMessageBox.information(...)
```

---

### Issue 2: "Update All to Latest" Should Update Each Asset to Its Own Latest Version
**Problem:** User reported that "Update All to Latest" should update each asset to its own latest version, not the highest version across all assets.

**Analysis:** The code was already correct - each asset tracks its own `latest` version during filesystem scan. However, the "Update All" function was not resolving paths for the active shot.

**Solution:** Enhanced `_on_update_all()` to:
1. Check if current shot is the active shot
2. For each asset being updated:
   - Set version on CTX_Asset node
   - If active shot: Resolve path and apply to Maya node
   - If inactive shot: Only update version (path resolves on shot switch)

**File:** `ui/asset_manager_dialog.py` (lines 816-950)

**Key Changes:**
```python
# Check if this shot is the active shot
manager_node = CTXManagerNode.get_manager()
is_active_shot = False
shot_node_name = None
if manager_node:
    active_shot_id = manager_node.get_active_shot_id()
    shot_node_name = "CTX_Shot_{}_{}_{}" .format(...)
    is_active_shot = (active_shot_id == shot_node_name)

# For each asset to update:
for asset_data in self._assets:
    if asset_data['status'] == 'update':
        # Set version to THIS asset's latest (not global latest)
        new_version = asset_data['latest']  # Each asset has its own latest
        ctx_node.set_version(new_version)
        
        # If active shot, resolve and apply path
        if is_active_shot and shot_node_name:
            node_manager.update_asset_path(
                ctx_node, shot_node, self._config, platform_config)
```

---

## How It Works Now

### Single Asset Version Update (Active Shot)
1. User clicks "Set" button, selects v006
2. CTX_Asset version updated to v006
3. Path resolved with v006 in context
4. Maya node updated with new path
5. **UI table refreshes to show v006** ✅
6. Success message displayed

### Update All to Latest (Active Shot)
1. User clicks "Update All to Latest"
2. For each asset with `status='update'`:
   - Get **that asset's** `latest` version (e.g., CatStompie → v006, ToriiMech → v003)
   - Set CTX_Asset version to its own latest
   - Resolve path with new version
   - Apply to Maya node
3. UI table refreshes
4. Message: "Updated X assets, Y paths resolved"

### Update All to Latest (Inactive Shot)
1. User clicks "Update All to Latest"
2. For each asset:
   - Set CTX_Asset version to its own latest
   - **Skip path resolution** (will happen on shot switch)
3. UI table refreshes
4. Message: "Updated X assets (Paths will be resolved when shot becomes active)"

---

## Example Scenario

**Scene has 3 assets in SH0140 (active shot):**
- CHAR_CatStompie_001: current=v003, latest=v006
- CHAR_ToriiMechSuit_001: current=v002, latest=v003
- PROP_ToriiSpeedline_001: current=v001, latest=v001

**User clicks "Update All to Latest":**

1. CatStompie: v003 → v006
   - Path: `.../v003/...` → `.../v006/...`
   - Maya reference reloads with v006 file

2. ToriiMechSuit: v002 → v003
   - Path: `.../v002/...` → `.../v003/...`
   - Maya reference reloads with v003 file

3. ToriiSpeedline: Already at latest (v001)
   - No change

**Result:** Each asset updated to its own latest version, not all to v006!

---

## Testing Instructions

### Test 1: Single Asset Version Update
1. Open Asset Manager for SH0140 (active shot)
2. Find CHAR_CatStompie_001 showing v003
3. Click "Set", select v006
4. **Expected:**
   - Asset reloads with v006 geometry
   - Table shows v006 as current version
   - Success message appears

### Test 2: Update All to Latest (Active Shot)
1. Set some assets to older versions manually
2. Click "Update All to Latest"
3. **Expected:**
   - Each asset updates to its own latest version
   - All assets reload in viewport
   - Message shows count of updated assets and resolved paths

### Test 3: Update All to Latest (Inactive Shot)
1. Open Asset Manager for SH0150 (inactive shot)
2. Click "Update All to Latest"
3. **Expected:**
   - Versions updated on CTX nodes
   - Assets in viewport don't change yet
   - Message says "Paths will be resolved when shot becomes active"
4. Switch to SH0150 as active shot
5. **Expected:**
   - All assets now reload with their latest versions

---

## Files Modified

1. `ui/asset_manager_dialog.py` - Two fixes:
   - Line 583: Added table refresh after single version update
   - Lines 816-950: Enhanced "Update All" to resolve paths for active shot

2. `VERSION_UPDATE_FIXES.md` - This summary document

