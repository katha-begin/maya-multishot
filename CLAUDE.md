# CLAUDE.md — AI Agent Instructions for Maya Multishot Pipeline

> **For AI agents working on this project.** Read this before touching any code.
> Source of truth for architecture: `spec/ARCHITECTURE_SUMMARY.md`
> Source of truth for project overview: `AGENTS.md`

---

## 1. Project in One Paragraph

Maya Multishot Pipeline is a Maya plugin that lets artists work on multiple shots in a single Maya scene. It uses custom Maya network nodes (`CTX_Manager → CTX_Sequence → CTX_Shot → CTX_Asset`) connected via message attributes, a named-template path resolver (templates in `project_configs/ctx_config.json`, tokens like `$ep`, `$seq`, `$shot`, `$assetType`, `$assetName` — all camelCase), and a hierarchical light gaffer system (Master → Sequence → Shot). All development now uses the **schema-based node system** in `core/nodes/wrappers/` — the old `core/custom_nodes.py` is deprecated.

---

## 2. Current State (2026-03-10)

| Phase | Status | Branch |
|---|---|---|
| Phase 0–5, Phase 1-schema | ✅ Complete | `feature/gaffer-system` |
| Phase 2 — UI & Tools Framework | ✅ Complete | `feature/ui-tools-framework` |
| Phase 3 — Gaffer System | ✅ Complete (core + UI) | `feature/ui-tools-framework` |
| **Phase 4 — Production & Automation** | **✅ Complete (Streams A–E)** | `feature/phase4-production-automation` |

### Phase 3 — Complete ✅

All gaffer engine + UI work done. System actively tested in Maya.

Key decisions made in Phase 3 (do not revert):
- **CTX_Light write rule**: CTX nodes written ONLY via `EditMode.commit()` snapshot-diff. Never from UI widgets directly.
- **Edit mode flow**: All edits (viewport, table, detail panel) apply to Maya live during edit mode via `cmds.setAttr()`. Commit captures changes uniformly via snapshot diff.
- **`set_target_light()` normalization**: Always resolves to the light shape node (not transform). If a transform is passed, resolves to first child shape. Fixed in `core/nodes/wrappers/light_context.py` and entry point `GafferManager.add_light_to_gaffer()`.
- **Window parenting**: Gaffer Manager uses `Qt::Tool` flag + parent to Maya main window (`OpenMayaUI.MQtUtil.mainWindow()` + shiboken). Stays above Maya without global topmost.
- **Table interaction in edit mode**: Intensity/exposure cells gain `ItemIsEditable` only during edit mode. Mute checkbox and color swatch enabled only during edit mode.
- **Right-click context menu**: Add Light, Remove Light, Clear Override accessible via right-click on lights table.
- **Clear Override (multi-select)**: Removes a child gaffer's local CTX override, making the light fall back to the inherited parent gaffer value. Supports multi-row selection.

**Completed components:**
- `core/gaffer/` — `manager.py`, `resolver.py`, `light_ops.py`, `chain_ops.py`, `edit_mode.py`
- `ui/gaffer_manager_dialog.py` — full gaffer UI with edit mode, right-click menu, clear override
- `ui/light_editor_panel.py` — per-light detail editor, all widgets disabled outside edit mode
- `ui/widgets/slider_field.py` — Maya-style QSlider + QDoubleSpinBox composite
- Shot switching applies correct gaffer chain; originals snapshot on window open

**Known remaining issues (not blocking Phase 4):**
- `tests/test_asset_manager.py` — 10 pre-existing failures (Phase 4+ renderer work)
- `core/ctx_converter.py::convert_to_ctx()` — still uses `core.custom_nodes`, not in active path

### Phase 4 — Production & Automation ✅

Full task docs at: `spec/phase4/` (INDEX.md + STREAM_A through STREAM_E)

**Completed (Streams A–E):**
- Stream A: `tools/pipeline_api.py` + `tools/cli.py` — headless API + argparse CLI (5 commands)
- Stream B: `core/validator/` — SceneValidator with 6 named checks, ValidatorReport
- Stream C: `core/logging_config.py` — structured logging, Maya output handler, replaced all print()
- Stream D: Config-driven parameters — 7 hardcoded values removed, 8 new ProjectConfig methods
- Stream E: `get_active_renderer()`, renderer config in JSON, config-driven standin paths

**Remaining gaps (deferred — not blocking):**
- No production tracker integration — shot creation is manual, frame ranges drift
- No undo/redo — gaffer operations bypass Maya's undo stack entirely
- Asset Manager standin creation (Stream F) — deferred
- VRay renderer adapter — deferred
- No farm render hook (Deadline/Tractor pre-render)

**P2 gaps still open:**
- Gaffer attributes hardcoded in Python (cannot be extended via config)
- No farm render hook (no pre-render shot-apply for Deadline/Tractor)
- No background threading (long operations block UI)
- `CTXLightOriginalsNode` is a single point of failure with no recovery path

**P3 gaps (polish):**
- No VRay renderer adapter
- No CI pipeline
- Five orphaned UI files not yet removed
- No gaffer-sharing visibility in UI

---

## 3. Non-Negotiable Rules

### Code Style
- **NO EMOJI IN `.py` FILES** — no emoji in comments, docstrings, print, logging, or names
- Markdown files (`.md`) may use emoji
- Python 3.7+ syntax only (Maya 2022+ constraint)

### Node System: Always Use Schema-Based Wrappers

```python
# ✅ CORRECT — always use this
from core.nodes.wrappers import (
    CTXManagerNode, CTXSequenceNode, CTXShotNode, CTXAssetNode,
    CTXLightGafferNode, CTXLightContextNode
)

# ❌ WRONG — deprecated, do not use for new code
from core.custom_nodes import CTXManagerNode, CTXShotNode
```

### Attribute Name: ctx_type (NOT ctx_node_type)

```python
# ✅ CORRECT
cmds.getAttr("{}.ctx_type".format(node))

# ❌ WRONG
cmds.getAttr("{}.ctx_node_type".format(node))
```

### Connections: Unidirectional Only

```python
# ✅ CORRECT — child.message → parent.attribute (ONE direction)
cmds.connectAttr("shot.message", "sequence.shots[0]", nextAvailable=True)
cmds.connectAttr("gaffer.message", "sequence.gaffer")

# ❌ WRONG — do NOT create bidirectional connections
cmds.connectAttr("sequence.message", "shot.parent_sequence")
```

### Do NOT Modify

- `core/custom_nodes.py` — frozen for backward compatibility
- `vendor/` — vendored third-party code

---

## 4. Architecture Quick Reference

### Node Hierarchy

```
CTX_Manager (singleton)
    ↑ sequences[i]  (Sequence.message → Manager.sequences[i])
CTX_Sequence
    ↑ shots[i]      (Shot.message → Sequence.shots[i])
    ↑ gaffer        (SeqGaffer.message → Sequence.gaffer)
CTX_Shot
    ↑ assets[i]     (Asset.message → Shot.assets[i])
    ↑ gaffer        (ShotGaffer.message → Shot.gaffer)
CTX_Asset

Gaffer inheritance (for light attribute resolution):
    Master CTX_LightGaffer → Sequence CTX_LightGaffer → Shot CTX_LightGaffer
    (walked via parentGaffer connections; enabled flag controls override vs. inherit)
```

### Schema-Based Node Pattern

```python
# 1. Schema defines structure (in core/nodes/schemas/)
class CTXShotSchema(NodeSchema):
    ATTRIBUTES = {'ep': {'type': 'string', 'default': ''}, ...}
    CONNECTIONS = {'assets': {'type': 'message', 'multi': True, 'direction': 'input'}, ...}

# 2. Wrapper provides API (in core/nodes/wrappers/)
class CTXShotNode(NodeWrapper):
    SCHEMA = CTXShotSchema
    def add_asset(self, asset): ...

# 3. Creation
shot = CTXShotNode.create(ep='Ep04', seq='sq0070', shot='SH0170')
```

### Token Path Resolution

**Config file:** `project_configs/ctx_config.json` — defines all templates, roots, tokens, and static paths.

Templates are **named keys** in config. You call the resolver by name — never by writing template strings by hand.

**All tokens are camelCase:** `$projRoot`, `$assetType`, `$assetName`, `$variant`, `$heroSubdir`, etc.
Underscore (`_`) is used as a **separator** in paths, NOT part of token names. E.g. `$ep_$seq_$shot` is three tokens.

**How the resolver builds the full context** (from `core/resolver.py: _build_full_context`):

```
Auto-injected from ctx_config.json (user does NOT provide these):
  projRoot  → "V:/"                (Windows) | "/mnt/igloo_swa_v/"  (Linux)
  imgRoot   → "W:/"                (Windows) | "/mnt/igloo_swa_w/"  (Linux)
  project   → "SWA"                (from config["project"]["code"])
  sceneBase → "all/scene"          (from config["staticPaths"]["sceneBase"])
  assetBase → "all/asset"          (from config["staticPaths"]["assetBase"])

User provides in context dict:
  ep, seq, shot, dept, ver, assetType, assetName, variant, ext, ...
```

**Real examples using actual template names from config:**

```
Template name : "publishPath"
Config value  : "$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish"
User context  : {ep: "Ep04", seq: "sq0070", shot: "SH0170", dept: "lighting"}
Result (Win)  : "V:\SWA\all\scene\Ep04\sq0070\SH0170\lighting\publish"

Template name : "assetPath"
Config value  : "$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish/$ver/
                 $ep_$seq_$shot__$assetType_$assetName_$variant.$ext"
User context  : {ep: "Ep04", seq: "sq0070", shot: "SH0170", dept: "lighting",
                 ver: "v003", assetType: "CHAR", assetName: "CatStompie",
                 variant: "001", ext: "abc"}
Result (Win)  : "V:\SWA\all\scene\Ep04\sq0070\SH0170\lighting\publish\v003\
                 Ep04_sq0070_SH0170__CHAR_CatStompie_001.abc"

Template name : "assetHeroPath"
Config value  : "$projRoot$project/$assetBase/$assetCategory/$assetSubdir/
                 $assetName/$heroSubdir/$assetName.$ext"
User context  : {assetCategory: "Character", assetSubdir: "Main",
                 assetName: "CatStompie", ext: "abc"}
Result (Win)  : "V:\SWA\all\asset\Character\Main\CatStompie\hero\CatStompie.abc"
```

**All template names in config:** `shotRoot`, `shotWork`, `publishPath`, `cachePath`,
`imgPath`, `assetPath`, `assetHeroPath`, `assetShaderPath`, `assetGroomPath`,
`assetSearchPath`, `fullFilename`, `namespace`, `namespaceShader`, `namespaceGroom`

**Valid token values** (from config `"tokens"` section — enforce these patterns):

| Token | Example | Pattern / Values |
|---|---|---|
| `$ep` | `Ep04` | `Ep\d+` |
| `$seq` | `sq0070` | `sq\d+` |
| `$shot` | `SH0170` | `SH\d+` |
| `$dept` | `lighting` | `anim`, `layout`, `fx`, `lighting` |
| `$ver` | `v003` | `v\d{3}` |
| `$assetType` | `CHAR` | `CHAR`, `PROP`, `SETS`, `SDRS`, `VEH`, `CAM` |
| `$assetName` | `CatStompie` | free string |
| `$variant` | `001` | `\d{3}` |
| `$assetCategory` | `Character` | mapped from `assetType` via config |
| `$ext` | `abc` | see config `"extensions"` list |

**Usage:**

```python
from config.project_config import ProjectConfig
from config.platform_config import PlatformConfig
from core.resolver import PathResolver

config = ProjectConfig('project_configs/ctx_config.json')
platform_config = PlatformConfig(config)
resolver = PathResolver(config, platform_config)

context = {'ep': 'Ep04', 'seq': 'sq0070', 'shot': 'SH0170', 'dept': 'lighting'}
path = resolver.resolve_path('publishPath', context)
# Windows: 'V:\\SWA\\all\\scene\\Ep04\\sq0070\\SH0170\\lighting\\publish'
```

### Gaffer System — Architecture & Rules

**Gaffer is optional.** If no gaffer exists, lights use their original Maya values.

**Gaffer connections (all unidirectional):**
```
# Ownership: gaffer owned by sequence or shot
gaffer.message  →  CTX_Sequence.gaffer
gaffer.message  →  CTX_Shot.gaffer

# Inheritance chain: parent feeds INTO child's parentGaffer
parent_gaffer.message  →  child_gaffer.parentGaffer

# Light membership: context feeds into gaffer's lights array
light_context.message  →  gaffer.lights[i]  (nextAvailable)
```

**Gaffer inheritance rules:**
- A gaffer can have 0 or 1 parent gaffers (via `parentGaffer`)
- Child inherits ALL lights from parent; can override any inherited light's values and/or add new lights
- Same light cannot be added twice to the same gaffer (ValueError)
- Same light CAN exist in both parent and child (child stores override values)
- A gaffer can be shared between shots — those shots get identical values

**Shot-switch apply order (in `_on_set_shot`):**
```
1. Shot has gaffer?       → apply it  (chain auto-walks to parent for inheritance)
2. Shot has no gaffer?    → check if shot's sequence has a gaffer → apply that
3. No gaffer anywhere?    → restore original light values (snapshot taken on window open)
```

**`AttributeResolver.resolve_attribute` walk order:**
```
[shot_gaffer, seq_gaffer, master_gaffer]  (build_chain order)
First gaffer where {attr}Enabled == True wins → return that value
If none found → attribute omitted (not applied)
```

**`isinstance` anti-pattern — DO NOT USE for wrapper classes:**
```python
# ❌ WRONG — breaks after module reload (stale class object)
gaffer_node = gaffer.node_name if isinstance(gaffer, CTXLightGafferNode) else gaffer

# ✅ CORRECT — safe across reloads
gaffer_node = gaffer if isinstance(gaffer, str) else gaffer.node_name
```
Apply this pattern everywhere a method accepts `(wrapper_or_str)`.

**Attribute enabled flags naming:**
- Simple: `intensity` → `intensityEnabled`, `exposure` → `exposureEnabled`
- Compound: `color` → `colorEnabled`, `translate` → `translateEnabled`, `rotate` → `rotateEnabled`, `scale` → `scaleEnabled`
- `spread` → `spreadEnabled`, `shadowEnable` → `shadowEnableEnabled`

**Original light snapshot:**
- `MainWindow._light_original_values` — captured once in `__init__` via `_capture_all_light_originals()`
- Restored by `_restore_light_originals()` when shot has no gaffer and no sequence gaffer
- Format: `{light_shape_name: GafferManager.capture_light_values() dict}`

---

## 5. Key File Locations

| What | Where |
|---|---|
| **Project config (templates, roots, tokens)** | `project_configs/ctx_config.json` |
| **Config loader** | `config/project_config.py` → `ProjectConfig` |
| **Platform path mapping** | `config/platform_config.py` → `PlatformConfig` |
| **Path resolver** | `core/resolver.py` → `PathResolver` |
| **Token expander** | `core/tokens.py` → `TokenExpander` |
| **Schema definitions** | `core/nodes/schemas/` |
| **Wrapper API (use this)** | `core/nodes/wrappers/` |
| **Legacy nodes (read-only)** | `core/custom_nodes.py` |
| **Gaffer system** | `core/gaffer/` |
| **Main UI** | `ui/main_window.py` |
| **Tests** | `tests/` |
| **Launch scripts** | `launch_multishot_dockable.py` |

---

## 6. Quick Start Commands

```python
# Launch Context Manager in Maya
exec(open(r'E:/dev/maya-multishot/launch_multishot_dockable.py').read())

# Create nodes
from core.nodes.wrappers import CTXManagerNode, CTXSequenceNode, CTXShotNode, CTXLightGafferNode

manager = CTXManagerNode.create(projectName='MyProject')
seq     = CTXSequenceNode.create(sequenceCode='sq0070', sequenceName='Sequence 70')
shot    = CTXShotNode.create(ep='Ep04', seq='sq0070', shot='SH0170')
gaffer  = CTXLightGafferNode.create(gafferName='Master', gafferType='master')

# Wire nodes (unidirectional)
manager.add_sequence(seq)
seq.add_shot(shot)
seq.set_gaffer(gaffer)
```

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest --cov=core --cov-report=html tests/

# Run specific test file
pytest tests/test_gaffer_manager.py -v
```

---

## 7. Authoritative Documentation

| Document | Use For |
|---|---|
| `spec/ARCHITECTURE_SUMMARY.md` | **Repository structure — SINGLE SOURCE OF TRUTH** |
| `AGENTS.md` | Full project overview, all context, key patterns |
| `core/nodes/AGENTS.md` | Schema-based node system technical reference |
| `spec/NODE_ARCHITECTURE.md` | Schema system design |
| `spec/DEVELOPMENT_PLAN.md` | Roadmap |
| `spec/GAFFER_IMPLEMENTATION_PLAN.md` | Gaffer task breakdown |
| `spec/CTX_lightGaffer_spec.md` | Gaffer specification |
| `spec/PRODUCTION_READINESS.md` | **Phase 4 decision doc — strengths, gaps, recommendations** |
| `.claude/memory.md` | **Persistent project state — update as you work** |

---

## 8. When Writing New Code

### Adding a new node type

1. Create schema in `core/nodes/schemas/my_node.py`
2. Create wrapper in `core/nodes/wrappers/my_node.py`
3. Export from `core/nodes/wrappers/__init__.py`
4. Write tests in `tests/test_my_node.py`

### Adding a new UI dialog

1. Inherit from `ui/base_dialog.py:BaseDialog` (once created in Phase 2)
2. Implement `_setup_ui()` and `_connect_signals()` pattern
3. Use `MAYA_AVAILABLE` guard from `tools/base_manager.py`

### Adding a tool manager

1. Inherit from `tools/base_manager.py:BaseManager` (once created in Phase 2)
2. Use dependency-injected `cmds` so tests work without Maya

---

## 9. Testing Without Maya

The project uses `MockCmds` + `MAYA_AVAILABLE` pattern for testing:

```python
# tools/base_manager.py (Phase 2 target)
try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    from tools.base_manager import MockCmds
    cmds = MockCmds()
    MAYA_AVAILABLE = False
```

Tests run without Maya installed. Always write tests that work in both modes.

---

## 10. Memory & Session Continuity

After completing significant work, update `.claude/memory.md` with:
- What was done
- What is next
- Any discovered issues or decisions

This ensures the next AI agent session can resume without re-reading all docs.
