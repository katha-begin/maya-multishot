# Stream E — Renderer Adapter Improvements

**Status:** Complete
**Priority:** P2
**Branch:** `feature/phase4-production-automation`
**Dependencies:** Stream D (config-driven) should be done first

---

## Goal

1. Add `get_active_renderer()` to the renderer package so all systems can detect
   which renderer is currently in use without duplicating the detection logic.
2. Add per-renderer config to `ctx_config.json` so standin node type, file attribute
   and preferred extension are config-driven rather than hardcoded.
3. Make `NodeManager._apply_path_to_maya_node()` renderer-agnostic (config-driven).
4. Add `get_preferred_extensions(renderer)` so the asset scanner can prefer the
   correct file format when multiple exist for the same asset.

> VRay adapter is deferred — not in scope for this branch.

---

## Background

### Current State

`core/renderers/__init__.py` provides:
- `get_node_type(node)` — detect renderer from light node type
- `get_maya_attr(light_shape, gaffer_attr)` — translate gaffer attribute to Maya attr

**Gaps:**
- No `get_active_renderer()` function
- No preferred extension per renderer
- Standin node type/attr is hardcoded in `core/nodes.py`:
  ```python
  if node_type == 'aiStandIn':
      cmds.setAttr(node + '.dso', path, type='string')
  elif node_type == 'RedshiftProxyMesh':
      cmds.setAttr(node + '.fileName', path, type='string')
  ```
- No config section for renderer-specific settings

---

## Deliverables

### 1. New config section in `project_configs/ctx_config.json`

```json
"renderers": {
    "redshift": {
        "standinExtension": "rs",
        "standinNodeType": "RedshiftProxyMesh",
        "standinFileAttr": "fileName",
        "preferredExtensions": ["rs", "abc", "ma", "mb"]
    },
    "arnold": {
        "standinExtension": "ass",
        "standinNodeType": "aiStandIn",
        "standinFileAttr": "dso",
        "preferredExtensions": ["ass", "abc", "ma", "mb"]
    },
    "maya": {
        "standinExtension": null,
        "standinNodeType": null,
        "standinFileAttr": null,
        "preferredExtensions": ["ma", "mb", "abc"]
    }
}
```

### 2. New `ProjectConfig` methods (in `config/project_config.py`)

```python
def get_renderer_config(self, renderer_name):
    """Return config dict for a specific renderer.

    Args:
        renderer_name (str): 'redshift' | 'arnold' | 'maya'

    Returns:
        dict or None
    """
    return self.data.get('renderers', {}).get(renderer_name)

def get_standin_node_type(self, renderer_name):
    cfg = self.get_renderer_config(renderer_name) or {}
    return cfg.get('standinNodeType')

def get_standin_file_attr(self, renderer_name):
    cfg = self.get_renderer_config(renderer_name) or {}
    return cfg.get('standinFileAttr')

def get_preferred_extensions(self, renderer_name):
    cfg = self.get_renderer_config(renderer_name) or {}
    return cfg.get('preferredExtensions', [])
```

### 3. `get_active_renderer()` in `core/renderers/__init__.py`

```python
def get_active_renderer():
    """Return the name of the currently active renderer.

    Returns:
        str: 'redshift' | 'arnold' | 'maya' | 'unknown'
    """
    try:
        import maya.cmds as cmds
        renderer = cmds.getAttr('defaultRenderGlobals.currentRenderer') or ''
        renderer = renderer.lower()
        if 'redshift' in renderer:
            return 'redshift'
        if 'arnold' in renderer or 'mtoa' in renderer:
            return 'arnold'
        if renderer in ('mayasoftware', 'mayahardware', 'mayahardware2'):
            return 'maya'
        return 'unknown'
    except Exception:
        return 'unknown'
```

### 4. `get_preferred_extensions(renderer)` in `core/renderers/__init__.py`

```python
def get_preferred_extensions(renderer_name, config=None):
    """Return preferred file extensions for the given renderer.

    Falls back to hardcoded defaults if config not provided.

    Args:
        renderer_name (str): Renderer name from get_active_renderer().
        config: Optional ProjectConfig instance.

    Returns:
        list[str]: Extensions in preference order, without leading dot.
    """
    if config:
        exts = config.get_preferred_extensions(renderer_name)
        if exts:
            return exts

    # Hardcoded fallback
    _FALLBACK = {
        'redshift': ['rs', 'abc', 'ma', 'mb'],
        'arnold':   ['ass', 'abc', 'ma', 'mb'],
        'maya':     ['ma', 'mb', 'abc'],
    }
    return _FALLBACK.get(renderer_name, ['abc', 'ma', 'mb'])
```

### 5. Refactor `NodeManager._apply_path_to_maya_node()` in `core/nodes.py`

Replace hardcoded if/elif with config lookup:

```python
def _apply_path_to_maya_node(self, maya_node, resolved_path, config=None):
    """Apply resolved path to a Maya node.

    Renderer-specific node type and attribute are read from config if provided,
    with hardcoded fallback for backward compatibility.
    """
    from core.renderers import get_active_renderer
    node_type = cmds.nodeType(maya_node)

    # Build lookup: {node_type: file_attr}
    node_attr_map = {}
    if config:
        for renderer_name in ('redshift', 'arnold', 'maya'):
            rnd_cfg = config.get_renderer_config(renderer_name) or {}
            node_t = rnd_cfg.get('standinNodeType')
            file_a = rnd_cfg.get('standinFileAttr')
            if node_t and file_a:
                node_attr_map[node_t] = file_a

    # Hardcoded fallback (always available even without config)
    if not node_attr_map:
        node_attr_map = {
            'aiStandIn':          'dso',
            'RedshiftProxyMesh':  'fileName',
        }

    if node_type in node_attr_map:
        attr = node_attr_map[node_type]
        cmds.setAttr('{}.{}'.format(maya_node, attr), resolved_path, type='string')
        return True

    # Reference nodes use file command
    if cmds.referenceQuery(maya_node, isNodeReferenced=True):
        cmds.file(resolved_path, loadReference=maya_node)
        return True

    logger.warning("Unknown node type for path application: %s", node_type)
    return False
```

### 6. Asset scanner renderer-aware format selection

In `core/asset_scanner._discover_assets_in_dept()`, after collecting filenames,
sort them by renderer preference:

```python
from core.renderers import get_active_renderer, get_preferred_extensions

renderer = get_active_renderer()
preferred = get_preferred_extensions(renderer, self.config)

# Sort files: preferred extension first, others alphabetically after
def ext_rank(filename):
    ext = os.path.splitext(filename)[1].lstrip('.')
    try:
        return preferred.index(ext)
    except ValueError:
        return len(preferred)

filenames_sorted = sorted(filenames, key=ext_rank)
```

Then use `filenames_sorted` when iterating — the first file found for each
`asset_key` will be the renderer-preferred format.

---

## File Changes Summary

| File | Change |
|------|--------|
| `project_configs/ctx_config.json` | Add `renderers` section |
| `config/project_config.py` | Add 4 new methods |
| `core/renderers/__init__.py` | Add `get_active_renderer()`, `get_preferred_extensions()` |
| `core/nodes.py` | Refactor `_apply_path_to_maya_node()` to config-driven |
| `core/asset_scanner.py` | Sort discovered files by renderer preference |

---

## Tests

File: `tests/test_renderer_adapters.py`

- `test_get_active_renderer_no_maya` — returns 'unknown' gracefully headless
- `test_get_preferred_extensions_redshift` — returns rs-first list
- `test_get_preferred_extensions_arnold` — returns ass-first list
- `test_get_preferred_extensions_from_config` — config overrides hardcode
- `test_apply_path_to_standin_from_config` — config-driven attr lookup
- `test_apply_path_to_standin_fallback` — hardcoded fallback still works
- `test_renderer_config_loaded` — ctx_config.json has renderers section
- `test_scanner_prefers_renderer_format` — (mock) scanner picks .rs over .abc for RS

---

## Completion Criteria

- [x] `project_configs/ctx_config.json` has `renderers` section
- [x] All new `ProjectConfig` methods added and tested
- [x] `get_active_renderer()` added to `core/renderers/__init__.py`
- [x] `get_preferred_extensions()` added to `core/renderers/__init__.py`
- [x] `NodeManager._apply_path_to_maya_node()` reads from config
- [x] Asset scanner uses renderer preference for format selection
- [x] All tests pass (25 new + 179 regression)
- [x] No regressions in existing test suite
