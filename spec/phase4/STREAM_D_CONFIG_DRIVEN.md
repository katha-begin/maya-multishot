# Stream D — Config-Driven Parameters

**Status:** Complete
**Priority:** P2 — Do second (unlocks correct behaviour in other streams)
**Branch:** `feature/phase4-production-automation`

---

## Goal

Remove hardcoded values that are already defined in `ctx_config.json` but not
being read. Also add missing config sections needed by Streams B and E.

---

## Background

Investigation found these hardcoded values that should come from config:

| # | Location | Hardcoded Value | Config Source (already exists) |
|---|----------|-----------------|-------------------------------|
| 1 | `asset_manager_dialog.py:288` | `['anim','layout','fx','lighting']` | `tokens.dept.values` |
| 2 | `asset_scanner.py:74` | `['anim','layout','fx','lighting']` | `tokens.dept.values` |
| 3 | `asset_scanner.py:83` | `['lighting','fx','cfx','anim','layout']` | `deptPriority.order` |
| 4 | `asset_scanner.py:181` | `r'^v\d+$'` | `tokens.ver.pattern` |
| 5 | `asset_scanner.py:195` | `.abc,.rs,.ma,.mb,.vdb,.ass` | `extensions` |
| 6 | `core/nodes.py:432` | `'_camera'` string literal | new: `assetDiscovery.cameraPattern` |
| 7 | `core/gaffer/resolver.py:25-39` | `SUPPORTED_ATTRIBUTES` list | new: `gafferAttributes` section |

Items 1–5 are already in config and just need the read call added.
Items 6–7 require new config sections.

---

## Deliverables

### 1. Fix #1 and #2 — Dept list from config

**`ui/asset_manager_dialog.py` line ~288:**
```python
# Before
departments = ['anim', 'layout', 'fx', 'lighting']

# After
departments = self.config.get_token_values('dept') or ['anim', 'layout', 'fx', 'lighting']
```

**`core/asset_scanner.py` line ~74:**
```python
# Before (in the except block)
departments = ['anim', 'layout', 'fx', 'lighting']

# After
departments = self.config.get_token_values('dept') or ['anim', 'layout', 'fx', 'lighting']
```

### 2. Fix #3 — Dept priority from config

**`core/asset_scanner.py` line ~83:**
```python
# Before
priority_order = ['lighting', 'fx', 'cfx', 'anim', 'layout']

# After
priority_order = self.config.get_dept_priority() or ['lighting', 'fx', 'cfx', 'anim', 'layout']
```

`config.get_dept_priority()` already exists (added in Phase 4 Sprint 1) — this
is just making the scanner use it instead of the hardcoded fallback.

### 3. Fix #4 — Version pattern from config

**`core/asset_scanner.py` line ~181:**
```python
# Before
if os.path.isdir(item_path) and re.match(r'^v\d+$', item):

# After
ver_pattern = self.config.get_token_pattern('ver') or r'^v\d+$'
if os.path.isdir(item_path) and re.match(ver_pattern, item):
```

Add `get_token_pattern(token_name)` to `ProjectConfig`:
```python
def get_token_pattern(self, token_name):
    """Return regex pattern for a token, e.g. get_token_pattern('ver') -> r'v\d{3}'"""
    return self.data.get('tokens', {}).get(token_name, {}).get('pattern')
```

### 4. Fix #5 — Extensions from config

**`core/asset_scanner.py` line ~195:**
```python
# Before
if not filename.endswith(('.abc', '.rs', '.ma', '.mb', '.vdb', '.ass')):

# After
extensions = tuple('.' + e for e in (self.config.get_extensions() or
                                     ['abc', 'rs', 'ma', 'mb', 'vdb', 'ass']))
if not filename.endswith(extensions):
```

`config.get_extensions()` returns the list from `ctx_config.json["extensions"]`.
Add this method if it does not exist yet.

### 5. Fix #6 — Camera suffix pattern (NEW config key)

**`project_configs/ctx_config.json`** — add to `assetDiscovery`:
```json
"assetDiscovery": {
    "heroSubdir": "hero",
    "cameraFileSuffix": "_camera",
    "categoryMappings": { ... }
}
```

**`config/project_config.py`** — add:
```python
def get_camera_file_suffix(self):
    return self.data.get('assetDiscovery', {}).get('cameraFileSuffix', '_camera')
```

**`core/asset_scanner.py` `_parse_filename()` line ~353:**
```python
# Before
if asset_part.endswith('_camera'):

# After
cam_suffix = self.config.get_camera_file_suffix()
if asset_part.endswith(cam_suffix):
```

**`core/nodes.py` line ~432:**
```python
# Before
if '_camera' in namespace_val:

# After
cam_suffix = config.get_camera_file_suffix() if config else '_camera'
if cam_suffix.lstrip('_') in namespace_val:
```

### 6. Fix #7 — Gaffer attributes in config (NEW config section)

**`project_configs/ctx_config.json`** — add section:
```json
"gafferAttributes": {
    "simple": [
        "intensity", "exposure", "spread", "muted",
        "affectDiffuse", "affectSpecular", "affectGI", "shadowEnable"
    ],
    "compound": {
        "color":     ["colorR",    "colorG",    "colorB"],
        "translate": ["translateX","translateY","translateZ"],
        "rotate":    ["rotateX",   "rotateY",   "rotateZ"],
        "scale":     ["scaleX",    "scaleY",    "scaleZ"]
    }
}
```

**`config/project_config.py`** — add:
```python
def get_gaffer_attributes(self):
    """Return gaffer attribute definition dict from config."""
    return self.data.get('gafferAttributes', {})

def get_gaffer_simple_attributes(self):
    return self.get_gaffer_attributes().get('simple', [])

def get_gaffer_compound_attributes(self):
    return self.get_gaffer_attributes().get('compound', {})
```

**`core/gaffer/resolver.py`** — replace hardcoded `SUPPORTED_ATTRIBUTES`:
```python
# Before (hardcoded at module level)
SUPPORTED_ATTRIBUTES = ['intensity', 'exposure', 'color', ...]

# After (loaded lazily from config)
def _get_supported_attributes(config):
    simple = config.get_gaffer_simple_attributes()
    compound = list(config.get_gaffer_compound_attributes().keys())
    return simple + compound
```

> NOTE: The resolver currently receives no config reference. The refactor must
> either inject config or load it lazily inside the method. Injection is preferred.

---

## Config Methods to Add/Verify in `ProjectConfig`

| Method | Already Exists? | Action |
|--------|----------------|--------|
| `get_token_values(token)` | YES | Verify it returns list from `tokens.dept.values` |
| `get_dept_priority()` | YES | Verify it reads `deptPriority.order` |
| `get_token_pattern(token)` | NO | Add |
| `get_extensions()` | Likely NO | Add |
| `get_camera_file_suffix()` | NO | Add |
| `get_gaffer_attributes()` | NO | Add |
| `get_gaffer_simple_attributes()` | NO | Add |
| `get_gaffer_compound_attributes()` | NO | Add |
| `get_logging_config()` | NO | Add (Stream C) |

---

## Tests

File: `tests/test_config_driven.py`

- `test_dept_list_from_config` — scanner uses config dept list, not hardcode
- `test_dept_priority_from_config` — scanner uses config priority order
- `test_version_pattern_from_config` — version dirs matched by config pattern
- `test_extensions_from_config` — scanner filters by config extensions
- `test_camera_suffix_from_config` — camera files matched by config suffix
- `test_gaffer_attributes_from_config` — resolver attributes from config

---

## Completion Criteria

- [x] All 7 hardcoded values removed from source files
- [x] New `ctx_config.json` sections added (`gafferAttributes`, updated `assetDiscovery`)
- [x] All new `ProjectConfig` methods added
- [x] All listed tests pass
- [x] No regressions in existing test suite
