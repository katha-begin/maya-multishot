# Maya Multishot Pipeline - AI Agent Summary

**Version:** 2.0
**Last Updated:** 2026-03-04
**Purpose:** High-level project overview for AI agents and new developers

---

## 1. Purpose

### What Problem Does This Solve?

**Pain Point:** VFX artists need to work on multiple shots simultaneously in Maya, but Maya's single-scene paradigm makes this difficult. Traditional workflows require:
- Opening/closing scenes repeatedly (slow, error-prone)
- Manual path management for assets across shots
- Duplicate asset references consuming memory
- No shot-specific visibility control
- Manual light adjustments per shot

**Solution:** Maya Multishot Pipeline provides:
- **Multi-shot context management** - Work on multiple shots in one Maya scene
- **Token-based path resolution** - Automatic path resolution using templates (`$ep/$seq/$shot/$asset`)
- **Display layer management** - Shot-specific visibility control
- **Hierarchical light gaffer system** - Inheritance-based light overrides (Master → Sequence → Shot)
- **Asset version management** - Independent asset versions per shot
- **Cross-platform support** - Windows/Linux with automatic path mapping

### Target Users

- **Pipeline TDs** - Implement and customize the pipeline
- **Lighting TDs** - Manage hierarchical light setups
- **Layout Artists** - Work on multiple shots simultaneously
- **Animation Artists** - Reference assets across shots efficiently

### Key Pain Points Addressed

✅ **Shot switching overhead** - No more scene open/close cycles  
✅ **Path management complexity** - Automatic token resolution  
✅ **Memory waste** - Shared asset references across shots  
✅ **Light management chaos** - Hierarchical inheritance system  
✅ **Version tracking** - Per-shot asset version control  
✅ **Platform differences** - Automatic Windows/Linux path mapping  

---

## 2. Objective

### Core Features

**Production-Ready:**
- ✅ Multi-shot support in single Maya scene
- ✅ Token-based path resolution (`$ep`, `$seq`, `$shot`, `$ver`, etc.)
- ✅ Display layer management (shot-specific visibility)
- ✅ CTX node hierarchy (Manager → Shot → Asset)
- ✅ Asset reference management
- ✅ Cross-platform path mapping
- ✅ **Light Gaffer System** (Phase 5 complete)
  - Hierarchical light management (Master → Sequence → Shot)
  - Per-attribute inheritance with enable flags
  - Flexible gaffer chains (not hardcoded by type)
  - Light Editor UI with real-time updates
- ✅ **Schema-Based Node System** (Phase 1 complete)
  - Declarative node definitions with NodeSchema
  - NodeFactory for automatic node creation
  - NodeWrapper high-level API
  - Unidirectional message attribute connections
  - All 6 core node types (Manager, Sequence, Shot, Asset, LightGaffer, LightContext)
  - Manual wiring methods for flexible node composition

**In Development:**
- 🚧 Asset type handlers (Arnold, Redshift, USD)
- 🚧 Renderer adapters (Arnold, Redshift)
- 🚧 NodeGraphQt visual graph editor (future)

### Current Status

**Branch:** `feature/ui-tools-framework`
**Phase:** Phase 2 - UI & Tools Framework Migration (In Progress)
**Lines of Code:** ~8,000+ (core + UI + tests)
**Test Coverage:** 63 passing tests for gaffer system

**Completed Phases:**
- Phase 0: Repository Setup
- Phase 1-4: Core system (nodes, paths, display layers, UI)
- Phase 5: Light Gaffer System
- Phase 1 (schema): Schema-Based Node System — all 6 node types, unidirectional connections

**Current Phase — Phase 2: UI & Tools Framework Migration**
- Create `tools/base_manager.py` (shared BaseManager class, MockCmds, MAYA_AVAILABLE)
- Create `ui/base_dialog.py` (shared Qt boilerplate)
- Migrate `tools/shot_manager.py` to schema-based wrappers
- Migrate `tools/asset_manager.py` to schema-based wrappers
- Migrate `ui/main_window.py` to schema-based wrappers
- Remove 5 unused `ui/` files (shot_widget, asset_widget, filesystem_discovery, import_asset_dialog, convert_scene_dialog)

### Roadmap Highlights

**Q1 2026:**
- Complete UI & tools framework migration (Phase 2)
- Migrate main_window.py to schema-based nodes
- Remove unused UI files

**Q2 2026:**
- NodeGraphQt visual graph integration
- USD support
- Multi-renderer support (Arnold, Redshift)

**Q3 2026:**
- Render farm integration
- Advanced gaffer features (animation, expressions)
- Performance optimization

---

## 3. Success Criteria

### Functional Requirements

**Must Work:**
- ✅ Create/manage multiple shots in single scene
- ✅ Switch between shots without scene reload
- ✅ Resolve token-based paths automatically
- ✅ Manage shot-specific display layers
- ✅ Reference assets with version control
- ✅ Apply hierarchical light overrides
- ✅ Support Windows and Linux platforms

### Performance Requirements

- Scene with 10 shots + 50 assets: < 5 seconds to switch shots
- Path resolution: < 100ms per token
- Light attribute resolution: < 50ms per chain walk
- UI responsiveness: < 200ms for all interactions

### User Acceptance Criteria

- Artists can work on 5+ shots simultaneously without confusion
- Light TDs can create Master → Sequence → Shot gaffer chains
- Pipeline TDs can add new asset types without core code changes
- Zero data loss during shot switching
- Intuitive UI requiring < 30 minutes training

### Test Coverage Goals

- Core modules: > 80% coverage
- Gaffer system: > 90% coverage (currently 63 tests passing)
- UI components: > 60% coverage
- Integration tests: All critical workflows covered

---

## 4. Technical Specification

### Maya Compatibility

- **Maya Version:** 2022+ (tested on 2022, 2023, 2024)
- **Python Version:** 3.7+ (Maya 2022+)
- **API:** maya.cmds (MEL commands via Python)

### Key Dependencies

```python
# Core Dependencies
PySide2 / PySide6  # Qt UI framework (Maya 2022+ uses PySide2)
NodeGraphQt        # Visual graph editor (future, vendored)

# Optional Dependencies
pytest             # Testing framework
pytest-cov         # Coverage reporting
```

### Platform Support

- **Windows:** Primary development platform
- **Linux:** Full support with path mapping
- **macOS:** Not officially supported (should work with minor adjustments)

### Core Technologies

- **Maya Network Nodes** - Custom CTX nodes using message attributes
- **Qt/PySide** - Cross-platform UI framework
- **Token System** - Template-based path resolution
- **Message Attributes** - Maya's connection system for node relationships
- **Display Layers** - Shot-specific visibility control

### Design Patterns

- **Schema-First** - Declarative node definitions before implementation
- **Plugin Architecture** - Registry pattern for extensible node types, asset types, renderers
- **Adapter Pattern** - Renderer-agnostic light attribute handling
- **Wrapper Pattern** - High-level API over low-level Maya commands
- **Singleton Pattern** - CTX_Manager (one per scene)
- **Observer Pattern** - UI updates on node changes (future)

---

## 5. Architecture

### System Design Overview

**Migration-Phase Architecture:**

1. **Legacy System** (`core/custom_nodes.py`) - Deprecated, kept for backward compatibility with existing Maya scenes only
2. **Schema-Based System** (`core/nodes/wrappers/`) - Primary system, use for all new development

Both systems coexist during migration. Do not modify `core/custom_nodes.py`. All new code must use `core/nodes/wrappers/`.

### Schema-Based Node System (NEW)

**Core Concept:** Separate node definition (schema) from implementation (wrapper) from creation (factory).

```
NodeSchema (Definition)
    ↓
NodeFactory (Creation) → Maya Node
    ↓
NodeWrapper (High-level API)
```

**Key Components:**

```python
# 1. Schema - Declarative definition
class CTXSequenceSchema(NodeSchema):
    ATTRIBUTES = {
        'sequenceCode': {'type': 'string', 'default': ''},
        'frameStart': {'type': 'int', 'default': 1001},
    }
    CONNECTIONS = {
        'shots': {'type': 'message', 'multi': True, 'direction': 'input'},
        'gaffer': {'type': 'message', 'multi': False, 'direction': 'input'},
    }

# 2. Factory - Creates Maya nodes from schema
node_name = NodeFactory.create_from_schema(schema, **kwargs)

# 3. Wrapper - High-level API
class CTXSequenceNode(NodeWrapper):
    SCHEMA = CTXSequenceSchema

    def add_shot(self, shot):
        # Wire shot to sequence
        cmds.connectAttr(f"{shot}.message", f"{self.node_name}.shots", nextAvailable=True)
```

**Benefits:**
- ✅ Schema IS the documentation
- ✅ Automatic validation
- ✅ Easy to extend (add new node types)
- ✅ Graph UI integration (auto-generate ports)

### Repository Structure

See [spec/ARCHITECTURE_SUMMARY.md](spec/ARCHITECTURE_SUMMARY.md) for the complete, authoritative directory tree including current state and target state (post Phase 2 migration).

### Core Modules

**Context Management:**
- `core/custom_nodes.py` - Legacy CTX node wrappers (Manager, Shot, Asset)
- `core/nodes/` - NEW schema-based node system
- `core/context.py` - Context management
- `core/ctx_linker.py` - Node linking utilities

**Path Resolution:**
- `core/tokens.py` - Token system (`$ep`, `$seq`, `$shot`, etc.)
- `core/resolver.py` - Path resolution engine
- `core/ctx_converter.py` - Token-to-path conversion
- `core/path_builder.py` - Path building utilities

**Asset Management:**
- `core/reference_manager.py` - Maya reference operations
- `core/nodes.py` - NodeManager for asset types
- `core/shader_assignment.py` - Shader operations
- `core/shader_discovery.py` - Shader discovery

**Display Layers:**
- `core/display_layers.py` - Shot-specific visibility control

**Light Gaffer System:**
- `core/gaffer/manager.py` - Gaffer CRUD operations
- `core/gaffer/resolver.py` - Attribute inheritance resolution
- `core/gaffer/chain_ops.py` - Chain management
- `core/gaffer/light_ops.py` - Light attribute capture/apply

**UI Components:**
- `ui/main_window.py` - Context Manager (main UI)
- `ui/gaffer_manager_dialog.py` - Gaffer Manager UI
- `ui/asset_manager_dialog.py` - Asset Manager UI
- `tools/maya_menu.py` - Maya menu integration

### Data Flow

**Node Hierarchy:**

```
CTX_Manager (singleton)
    ↓ sequences (multi)
CTX_Sequence
    ↓ shots (multi)
CTX_Shot
    ↓ assets (multi)
CTX_Asset
```

**Light Gaffer Hierarchy (Ownership + Inheritance):**

```
CTX_Sequence
    ↓ gaffer (single) - Sequence owns its gaffer
CTX_LightGaffer (Sequence-level)
    ↓ parentGaffer (single) - Inherits from Master gaffer
    ↓ lights (multi)
CTX_LightContext (per-light attribute storage)

CTX_Shot
    ↓ gaffer (single) - Shot owns its gaffer (NEW!)
CTX_LightGaffer (Shot-level)
    ↓ parentGaffer (single) - Inherits from Sequence gaffer
    ↓ lights (multi)
CTX_LightContext (per-light attribute storage)
```

**Gaffer Architecture: Ownership + Inheritance (NEW!)**

The gaffer system uses a **dual-connection pattern** combining direct ownership with inheritance:

**Direct Ownership (Parent-Child):**
- Sequence owns its gaffer via `Sequence.gaffer` connection
- Shot owns its gaffer via `Shot.gaffer` connection (NEW!)
- Similar to how Sequence owns shots, Shot owns assets

**Inheritance Chain (Hierarchical):**
- Shot gaffer inherits from Sequence gaffer via `parentGaffer` connection
- Sequence gaffer inherits from Master gaffer via `parentGaffer` connection
- Attribute resolution walks up the chain checking enabled flags

**Benefits:**
- ✅ **Symmetry** - Both Sequence and Shot directly own their gaffers
- ✅ **Clarity** - Clear parent-child relationship (like Sequence→Shots, Shot→Assets)
- ✅ **Direct Access** - Can query `shot.get_gaffer()` directly
- ✅ **Consistency** - Follows same pattern as other parent-child relationships
- ✅ **Inheritance Still Works** - Shot gaffer's `parentGaffer` still points to Sequence gaffer
- ✅ **Flexible Chains** - Not hardcoded by type (Master/Sequence/Shot), supports custom chains

**Attribute Resolution Flow:**

```
1. Query light attribute (e.g., intensity)
2. Check Shot gaffer → enabled? Use value : Continue
3. Check Sequence gaffer → enabled? Use value : Continue
4. Check Master gaffer → enabled? Use value : Continue
5. Use light's current value (fallback)
```

**Path Resolution Flow:**

```
1. Template: "/proj/$ep/$seq/$shot/assets/$asset_type/$asset_name/$ver"
2. Context: {ep: "Ep04", seq: "sq0070", shot: "SH0170", ...}
3. Resolve: "/proj/Ep04/sq0070/SH0170/assets/CHAR/CatStompie/v003"
4. Platform map: Windows → "E:/proj/...", Linux → "/mnt/proj/..."
```

### Key Design Patterns

**Schema-First Pattern:**
```python
# 1. Define schema (declarative)
class CTXShotSchema(NodeSchema):
    ATTRIBUTES = {...}
    CONNECTIONS = {...}

# 2. Create wrapper (high-level API)
class CTXShotNode(NodeWrapper):
    SCHEMA = CTXShotSchema

    def add_asset(self, asset):
        # Implementation uses schema
```

**Plugin Architecture:**
```python
# Asset type handlers (future)
class AssetTypeRegistry:
    def register(self, asset_type, handler_class):
        self._handlers[asset_type] = handler_class

    def get_handler(self, asset_type):
        return self._handlers.get(asset_type)

# Usage
registry.register('arnold_standin', ArnoldStandInHandler)
handler = registry.get_handler('arnold_standin')
```

**Adapter Pattern:**
```python
# Renderer adapters (future)
class RendererAdapter:
    def get_light_attributes(self, light_node):
        # Renderer-specific implementation
        pass

class ArnoldAdapter(RendererAdapter):
    def get_light_attributes(self, light_node):
        return ['aiExposure', 'aiIntensity', 'aiColor', ...]
```

---

## 6. Key Concepts

### CTX Nodes

**Custom Maya network nodes** with message attribute connections for hierarchy.

- **CTX_Manager** - Root node (singleton), stores project config
- **CTX_Sequence** - Sequence container, owns sequence-level gaffer
- **CTX_Shot** - Shot context, stores ep/seq/shot codes, frame range
- **CTX_Asset** - Asset metadata, file path, version, namespace
- **CTX_LightGaffer** - Light attribute storage with inheritance
- **CTX_LightContext** - Per-light attribute values

### Message Attributes

**Maya's connection system** for node relationships using **unidirectional connections**.

```python
# Connection pattern: source.message → target.customAttr (ONE direction only)
cmds.connectAttr("shot.message", "sequence.shots[0]", nextAvailable=True)
cmds.connectAttr("gaffer.message", "sequence.gaffer")
```

**Key Principle:** Use **unidirectional connections** (child → parent) for hierarchy.

**Why Unidirectional?**
- ✅ Single source of truth (parent owns children)
- ✅ Simpler code (one connection, not two)
- ✅ Better performance (half the connections)
- ✅ Can query in BOTH directions from ONE connection

**Querying:**
```python
# Get children from parent
children = cmds.listConnections("parent.children", source=True, destination=False)

# Get parent from child
parent = cmds.listConnections("child.message", source=False, destination=True)
```

**Direction:**
- **INPUT** - Receives connections (e.g., `shots[0]`, `gaffer`)
- **OUTPUT** - Sends connections (e.g., `.message`)

### Token System

**Template-based path resolution** with automatic context substitution.

```python
# Template
"/proj/$ep/$seq/$shot/assets/$asset_type/$asset_name/$ver"

# Context
{
    'ep': 'Ep04',
    'seq': 'sq0070',
    'shot': 'SH0170',
    'asset_type': 'CHAR',
    'asset_name': 'CatStompie',
    'ver': 'v003'
}

# Resolved
"/proj/Ep04/sq0070/SH0170/assets/CHAR/CatStompie/v003"
```

### Gaffer Inheritance

**Per-attribute inheritance** with enable flags for flexible override control.

```python
# Master gaffer
intensity: 1.0 (enabled)
color: [1, 1, 1] (enabled)

# Sequence gaffer (inherits from Master)
intensity: 1.5 (enabled) → OVERRIDES Master
color: [1, 0.8, 0.6] (disabled) → INHERITS from Master

# Shot gaffer (inherits from Sequence)
intensity: 2.0 (disabled) → INHERITS from Sequence (1.5)
color: [1, 0, 0] (enabled) → OVERRIDES Sequence
```

---

## 7. Development Status

### Current Phase: UI & Tools Framework Migration

**Status:** In Progress (Phase 2)
**Branch:** `feature/ui-tools-framework`

**Completed (Phase 1 — Schema-Based Node System):**
- Created schema-based node system architecture
- Implemented all 6 node schemas (Manager, Sequence, Shot, Asset, LightGaffer, LightContext)
- Created all 6 wrappers with manual wiring methods
- Fixed NodeFactory to process CONNECTIONS dict
- Added Maya menu integration (CTX Tools -> Nodes)
- Removed popup dialogs from node creation
- Migrated documentation to reflect unidirectional connection pattern

**Completed (Phase 2 — partial):**
- Created tools/base_manager.py (BaseManager, MockCmds, MAYA_AVAILABLE)
- Created ui/base_dialog.py (shared Qt boilerplate)
- Migrated tools/shot_manager.py
- Migrated tools/asset_manager.py
- Updated ui/main_window.py import line
- Updated ui/__init__.py and tools/__init__.py
- Removed 5 unused ui/ files
- Fixed core/ctx_linker.py Maya import guard
- Fixed tests/test_node_schemas.py stale assertions

**Remaining (Phase 2 — core migration):**
- `core/nodes/wrappers/shot.py`: add `get_ep_code/seq_code/shot_code()`, `is_active()`, `set_active()`, fix `get_assets()`, override `create()` for naming
- `core/nodes/wrappers/manager.py`: fix `get_sequences()`/`get_shots()` return types, add `set_active_shot_id()`
- `core/nodes/wrappers/sequence.py`: fix `get_parent_manager()` attribute bug, fix `get_shots()` return type
- `core/context.py`: replace `core.custom_nodes` imports, add `_get_or_create_sequence()`, wire `Manager → Sequence → Shot`

### Known Issues

1. **core/context.py still legacy** - Still imports from `core.custom_nodes`; the main tool end-to-end uses the old node system until this is migrated
2. **Wrapper return types** - `manager.get_shots()`, `sequence.get_shots()` return raw strings instead of wrapper instances
3. **Legacy compatibility** - Ensure old scenes still work with schema-based nodes
4. **Pre-existing test failure** - `tests/test_asset_manager.py` (10 failures): `add_asset()` imports `create_standin_with_namespace` from `core.nodes` which does not exist (renderer handlers are Phase 3+ work)

---

## 8. Quick Reference

### Essential Documents

- **[ARCHITECTURE_SUMMARY.md](spec/ARCHITECTURE_SUMMARY.md)** - Repository structure (SINGLE SOURCE OF TRUTH)
- **[core/nodes/AGENTS.md](core/nodes/AGENTS.md)** - Schema-based node system technical reference
- **[NODE_ARCHITECTURE.md](spec/NODE_ARCHITECTURE.md)** - Schema-based node system details
- **[DEVELOPMENT_PLAN.md](spec/DEVELOPMENT_PLAN.md)** - Development roadmap
- **[spec.md](spec/spec.md)** - Complete technical specification
- **[GAFFER_IMPLEMENTATION_PLAN.md](spec/GAFFER_IMPLEMENTATION_PLAN.md)** - Gaffer task breakdown
- **[CTX_lightGaffer_spec.md](spec/CTX_lightGaffer_spec.md)** - Gaffer detailed specification

### Node System

**Primary system (use for all new code):** `core/nodes/wrappers/`
**Legacy system (backward compat only):** `core/custom_nodes.py` — DEPRECATED, do not use for new development

**Correct imports:**

```python
# CORRECT
from core.nodes.wrappers import (
    CTXManagerNode, CTXSequenceNode, CTXShotNode, CTXAssetNode,
    CTXLightGafferNode, CTXLightContextNode
)

# WRONG — do not use for new code
from core.custom_nodes import CTXManagerNode, CTXShotNode
```

**Correct attribute name:** `ctx_type` (snake_case)
**Wrong attribute name:** `ctx_node_type` — do not use

### Migration Priority

Files that still use the legacy node system and need migration in Phase 2:

| File | Issue | Action |
|---|---|---|
| `ui/main_window.py` | Imports `CTXManagerNode, CTXShotNode` from `core.custom_nodes` | Migrate to `core.nodes.wrappers` |
| `tools/shot_manager.py` | Uses raw `cmds.createNode` + legacy node operations | Extend `BaseManager`, use wrappers |
| `tools/asset_manager.py` | Inline `from core.custom_nodes import ...` inside methods | Extend `BaseManager`, use wrappers |

Migration order: `base_manager.py` -> `base_dialog.py` -> `shot_manager.py` -> `asset_manager.py` -> `main_window.py`

### Key Commands

```python
# Launch Context Manager
exec(open(r'E:/dev/maya-multishot/launch_multishot_dockable.py').read())

# Create nodes (schema-based wrappers)
from core.nodes.wrappers import CTXManagerNode, CTXSequenceNode, CTXShotNode
from core.nodes.wrappers import CTXLightGafferNode

manager = CTXManagerNode.create(projectName='MyProject')
seq = CTXSequenceNode.create(sequenceCode='sq0070', sequenceName='Sequence 70')
shot = CTXShotNode.create(ep='Ep04', seq='sq0070', shot='SH0170')
gaffer = CTXLightGafferNode.create(gafferName='Master', gafferType='master')

# Wire nodes (unidirectional: child.message -> parent.attribute)
manager.add_sequence(seq)
seq.add_shot(shot)
seq.set_gaffer(gaffer)

# Reload menu (for development)
from tools import maya_menu
maya_menu.reload_menu()
```

### Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=core --cov-report=html tests/

# Run specific test
pytest tests/test_gaffer_manager.py -v
```

### Code Style Rules

- DO NOT USE EMOJI IN CODE FILES (.py files)
  - No emoji in comments, docstrings, print statements, or logging messages
  - No emoji in variable names, class names, or function names
  - Documentation files (.md) may use emoji for readability

---

**Maintainer:** CTX Pipeline Team
**Repository:** https://github.com/katha-begin/maya-multishot.git
**Last Updated:** 2026-03-04

