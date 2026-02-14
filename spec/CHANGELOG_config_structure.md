# Configuration Structure Update - Changelog

**Date:** 2026-02-14  
**Version:** 1.1  
**Status:** Implemented

---

## Summary

Updated configuration structure to properly separate filesystem roots from project paths and static path segments.

---

## Changes

### 1. Configuration Schema Update

#### Before (Incorrect):
```json
{
  "roots": {
    "project": "V:/SWA",
    "publish": "V:/SWA/all/scene",
    "cache": "V:/SWA/all/scene"
  },
  "templates": {
    "publish_path": "$root/all/scene/$ep/$seq/$shot/$dept/publish"
  }
}
```

**Problems:**
- Mixed filesystem roots with full paths
- Duplicated path segments in roots
- Not flexible for different projects

#### After (Correct):
```json
{
  "roots": {
    "PROJ_ROOT": "V:/"
  },
  "project": {
    "name": "SWA",
    "code": "SWA"
  },
  "static_paths": {
    "scene_base": "all/scene"
  },
  "templates": {
    "publish_path": "$PROJ_ROOT/$project/$scene_base/$ep/$seq/$shot/$dept/publish"
  },
  "platform_mapping": {
    "windows": {
      "PROJ_ROOT": "V:/"
    },
    "linux": {
      "PROJ_ROOT": "/mnt/igloo_swa_v/"
    }
  }
}
```

**Benefits:**
- Clear separation of concerns
- Filesystem root is truly just the root (V:/)
- Project name is a token ($project = "SWA")
- Static paths are reusable segments
- Platform mapping only needs to map roots

---

## Path Construction Logic

### Three-Layer Structure:

1. **Filesystem Root** (`roots`)
   - Only the drive/mount point
   - Example: `PROJ_ROOT: "V:/"`
   - Platform-specific (mapped via platform_mapping)

2. **Project Identifier** (`project`)
   - Project code/name
   - Example: `"SWA"`
   - Used as token: `$project`

3. **Static Paths** (`static_paths`)
   - Fixed path segments
   - Example: `scene_base: "all/scene"`
   - Used as tokens: `$scene_base`

### Path Assembly:

```
Full Path = $PROJ_ROOT + $project + $static_path + dynamic_tokens

Example:
  $PROJ_ROOT     = V:/
  $project       = SWA
  $scene_base    = all/scene
  $ep/$seq/$shot = Ep04/sq0070/SH0170
  $dept          = anim
  $ver           = v003

Result: V:/SWA/all/scene/Ep04/sq0070/SH0170/anim/publish/v003
```

---

## Files Updated

### 1. examples/ctx_config.json
- ✅ Updated `roots` to only contain `PROJ_ROOT: "V:/"`
- ✅ Added `static_paths` section with `scene_base: "all/scene"`
- ✅ Updated templates to use `$PROJ_ROOT/$project/$scene_base`
- ✅ Updated `platform_mapping` to map only `PROJ_ROOT`

### 2. config/project_config.py
- ✅ Added `static_paths` to `REQUIRED_KEYS`
- ✅ Added validation for `static_paths` section
- ✅ Added `get_static_paths()` method
- ✅ Added `get_static_path(name)` method
- ✅ Updated docstrings to reflect new structure

### 3. tests/test_config.py
- ✅ Updated test data to use new structure
- ✅ Updated test assertions for roots (now `PROJ_ROOT`)
- ✅ Added tests for `get_static_paths()`
- ✅ Added tests for `get_static_path(name)`
- ✅ Updated template assertions
- ✅ All 21 tests passing

### 4. spec/spec.md
- ✅ Updated Section 5.2 Configuration Schema
- ✅ Added explanation of three-layer structure
- ✅ Added path construction logic
- ✅ Updated example configuration
- ✅ Added `platform_mapping` section

---

## Token Updates

### New Tokens Available:

| Token | Description | Example |
|-------|-------------|---------|
| `$PROJ_ROOT` | Filesystem root | `V:/` or `/mnt/igloo_swa_v/` |
| `$project` | Project code | `SWA` |
| `$scene_base` | Scene base path | `all/scene` |
| `$asset_base` | Asset base path | `all/asset` |
| `$config_base` | Config base path | `config` |

### Existing Tokens (Unchanged):

| Token | Description | Example |
|-------|-------------|---------|
| `$ep` | Episode code | `Ep04` |
| `$seq` | Sequence code | `sq0070` |
| `$shot` | Shot code | `SH0170` |
| `$dept` | Department | `anim` |
| `$ver` | Version | `v003` |
| `$assetType` | Asset type | `CHAR` |
| `$assetName` | Asset name | `CatStompie` |
| `$variant` | Asset variant | `001` |

---

## Migration Guide

### For Existing Configurations:

If you have an old configuration file, update it as follows:

```python
# Old structure
{
  "roots": {
    "project": "V:/SWA",
    "publish": "V:/SWA/all/scene"
  }
}

# New structure
{
  "roots": {
    "PROJ_ROOT": "V:/"
  },
  "project": {
    "code": "SWA"
  },
  "static_paths": {
    "scene_base": "all/scene"
  }
}
```

### For Template Paths:

```python
# Old template
"$root/all/scene/$ep/$seq/$shot"

# New template
"$PROJ_ROOT/$project/$scene_base/$ep/$seq/$shot"
```

---

## Testing

### Test Results:

```bash
$ python tests/test_config.py
.....................
----------------------------------------------------------------------
Ran 21 tests in 0.091s

OK
```

### Test Coverage:
- ✅ Configuration loading
- ✅ Schema validation
- ✅ Root path access
- ✅ Static path access
- ✅ Template access
- ✅ Pattern access
- ✅ Error handling

---

## Impact on Other Modules

### Modules That Need Updates:

1. **Token Expansion Engine** (Phase 2)
   - Must support new tokens: `$PROJ_ROOT`, `$project`, `$scene_base`
   - Must handle three-layer path construction

2. **Path Resolver** (Phase 2)
   - Must assemble paths from three layers
   - Must apply platform mapping to roots

3. **Platform Config** (Phase 1, next task)
   - Must map `PROJ_ROOT` between Windows/Linux
   - Must read `platform_mapping` from config

---

## Rationale

### Why This Change?

1. **Separation of Concerns:**
   - Filesystem roots are truly roots (V:/, /mnt/)
   - Project identifier is separate
   - Static paths are reusable

2. **Flexibility:**
   - Easy to change project name
   - Easy to add new static paths
   - Platform mapping is simpler

3. **Clarity:**
   - Clear what each section represents
   - No duplication of path segments
   - Easier to understand and maintain

4. **Scalability:**
   - Can support multiple projects on same root
   - Can support different directory structures
   - Can support complex path hierarchies

---

## Status

✅ **Complete** - All files updated and tested  
✅ **Tests Passing** - 21/21 tests pass  
✅ **Documentation Updated** - spec.md reflects changes  
✅ **Ready for Next Task** - [P1-CONFIG-02] PlatformConfig

---

**Next Steps:**
1. Implement PlatformConfig class to handle platform mapping
2. Update token expansion engine to support new tokens
3. Update path resolver to use three-layer construction

