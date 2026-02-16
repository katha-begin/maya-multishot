# Version Update Flow - Detailed Explanation

## Scenario: User Sets Version v005 for CHAR_CatStompie_001 in Active Shot SH0140

### Step-by-Step Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USER ACTION                                                  │
│    - Opens Asset Manager for SH0140                             │
│    - Clicks "Set" button for CHAR_CatStompie_001                │
│    - Selects version: v005                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. UPDATE CTX_ASSET NODE                                        │
│    ctx_node.set_version('v005')                                 │
│                                                                 │
│    CTX_Asset_CHAR_CatStompie_SH0140:                           │
│      .version = "v005"  ← UPDATED                              │
│      .template = "$projRoot$project/.../$ver/...$ext"          │
│      .extension = "abc"                                         │
│      .namespace = "CHAR_CatStompie_001"                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. CHECK IF ACTIVE SHOT                                         │
│    manager_node.get_active_shot_id()                            │
│    → "CTX_Shot_Ep04_sq0070_SH0140"                             │
│                                                                 │
│    Current shot: "CTX_Shot_Ep04_sq0070_SH0140"                 │
│    ✓ MATCH → This is the ACTIVE shot                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. RESOLVE PATH WITH NEW VERSION                                │
│    node_manager.update_asset_path(ctx_node, shot_node, ...)    │
│                                                                 │
│    A. Get template from CTX_Asset:                              │
│       "$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/      │
│        publish/$ver/$ep_$seq_$shot__$assetType_$assetName_     │
│        $variant.$ext"                                           │
│                                                                 │
│    B. Build context:                                            │
│       {                                                         │
│         'projRoot': 'V:/',                                      │
│         'project': 'SWA',                                       │
│         'sceneBase': 'all/scene',                               │
│         'ep': 'Ep04',                                           │
│         'seq': 'sq0070',                                        │
│         'shot': 'SH0140',                                       │
│         'dept': 'anim',                                         │
│         'ver': 'v005',        ← NEW VERSION                     │
│         'assetType': 'CHAR',                                    │
│         'assetName': 'CatStompie',                              │
│         'variant': '001',                                       │
│         'ext': 'abc'                                            │
│       }                                                         │
│                                                                 │
│    C. Expand tokens:                                            │
│       "V:/SWA/all/scene/Ep04/sq0070/SH0140/anim/publish/v005/  │
│        Ep04_sq0070_SH0140__CHAR_CatStompie_001.abc"            │
│                                                                 │
│       ↑ Notice: v005 (not v001 or v003)                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. GET LINKED MAYA NODE                                         │
│    get_linked_maya_node(ctx_node)                               │
│    → "CHAR_CatStompie_001RN" (reference node)                  │
│                                                                 │
│    (Uses message attribute connection)                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. APPLY PATH TO MAYA NODE                                      │
│    cmds.file(resolved_path, loadReference=maya_node)            │
│                                                                 │
│    Maya reloads reference with new file:                        │
│    "V:/SWA/all/scene/Ep04/sq0070/SH0140/anim/publish/v005/     │
│     Ep04_sq0070_SH0140__CHAR_CatStompie_001.abc"               │
│                                                                 │
│    ✓ Asset in viewport now shows v005 geometry                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. USER FEEDBACK                                                │
│    QMessageBox: "Asset CatStompie updated to version v005       │
│                  Path resolved and applied to Maya node."       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Points

1. **Version is stored on CTX_Asset BEFORE path resolution**
   - This ensures `resolve_asset_path()` uses the new version

2. **Path resolution uses token expansion**
   - Template: `...$ver/...` 
   - Context: `'ver': 'v005'`
   - Result: `.../v005/...`

3. **Maya node is updated immediately (active shot only)**
   - Reference nodes: `cmds.file(path, loadReference=node)`
   - aiStandIn: `cmds.setAttr(node + '.dso', path)`
   - RedshiftProxyMesh: `cmds.setAttr(node + '.fileName', path)`

4. **User sees immediate feedback**
   - Success message with version number
   - Asset updates in viewport

---

## Comparison: Active vs Inactive Shot

| Step | Active Shot | Inactive Shot |
|------|-------------|---------------|
| 1. Set version on CTX_Asset | ✓ Yes | ✓ Yes |
| 2. Resolve path | ✓ Yes | ✗ No |
| 3. Apply to Maya node | ✓ Yes | ✗ No |
| 4. User feedback | "Path applied" | "Will apply on shot switch" |
| 5. When does Maya update? | Immediately | On next shot switch |

---

## Example: Camera Version Update

Same flow applies to cameras:

```
User selects camera version v003 in active shot SH0140
  ↓
CTX_Asset_CAM_SWA_Ep04_SH0140_camera_SH0140.version = "v003"
  ↓
Template: "$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish/$ver/$ep_$seq_$shot__$assetName.$ext"
Context: {'ver': 'v003', 'assetName': 'SWA_Ep04_SH0140_camera', ...}
  ↓
Resolved: "V:/SWA/all/scene/Ep04/sq0070/SH0140/anim/publish/v003/Ep04_sq0070_SH0140__SWA_Ep04_SH0140_camera.abc"
  ↓
Maya reference "SWA_Ep04_SH0140_cameraRN" reloads with v003 file
  ↓
Camera in viewport updates to v003
```

Note: Camera namespace is `SWA_Ep04_SH0140_camera` (no type prefix, no variant)

