# CLAUDE.md — AI Agent Instructions for Maya Multishot Pipeline

> **For AI agents working on this project.** Read this before touching any code.
> Source of truth for architecture: `spec/ARCHITECTURE_SUMMARY.md`
> Source of truth for project overview: `AGENTS.md`

---

## 1. Project in One Paragraph

Maya Multishot Pipeline is a Maya plugin that lets artists work on multiple shots in a single Maya scene. It uses custom Maya network nodes (`CTX_Manager → CTX_Sequence → CTX_Shot → CTX_Asset`) connected via message attributes, a named-template path resolver (templates in `project_configs/ctx_config.json`, tokens like `$ep`, `$seq`, `$shot`, `$assetType`, `$assetName` — all camelCase), and a hierarchical light gaffer system (Master → Sequence → Shot). All development now uses the **schema-based node system** in `core/nodes/wrappers/` — the old `core/custom_nodes.py` is deprecated.

---

## 2. Current State (2026-03-05)

| Phase | Status | Branch |
|---|---|---|
| Phase 0–5, Phase 1-schema | ✅ Complete | `feature/gaffer-system` |
| **Phase 2 (CURRENT)** | **🚧 In Progress** | **`feature/ui-tools-framework`** |

### Phase 2 Task List (in order)

1. 🆕 Create `tools/base_manager.py` — `BaseManager` class, `MockCmds`, `MAYA_AVAILABLE`
2. 🆕 Create `ui/base_dialog.py` — shared Qt boilerplate (`PySide6`/`PySide2` try/except)
3. 🔄 Migrate `tools/shot_manager.py` — extend `BaseManager`, use schema wrappers
4. 🔄 Migrate `tools/asset_manager.py` — extend `BaseManager`, use schema wrappers
5. 🔄 Migrate `ui/main_window.py` — replace `core.custom_nodes` imports with `core.nodes.wrappers`
6. 🔄 Update `ui/__init__.py` — remove unused entries from `__all__`
7. 🔄 Update `tools/__init__.py` — expose new manager classes
8. ❌ Delete 5 unused `ui/` files (after migration verified):
   - `ui/shot_widget.py`, `ui/asset_widget.py`, `ui/filesystem_discovery.py`
   - `ui/import_asset_dialog.py`, `ui/convert_scene_dialog.py`

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

### Gaffer Attribute Resolution Order

```
1. Check Shot gaffer → enabled? → use value
2. Check Sequence gaffer → enabled? → use value
3. Check Master gaffer → enabled? → use value
4. Fallback: use light's current value in scene
```

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
