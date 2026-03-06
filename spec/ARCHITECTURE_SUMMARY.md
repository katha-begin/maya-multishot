# Maya Multishot - Architecture Summary

**Version:** 3.0
**Last Updated:** 2026-03-04
**Status:** SINGLE SOURCE OF TRUTH for Repository Structure

---

## Overview

**⚠️ This document is the SINGLE SOURCE OF TRUTH for repository structure.**

All other documents should reference this document for structure information.

### Development Phases

| Phase | Name | Branch | Status |
|---|---|---|---|
| Phase 0 | Repository Setup | `main` | ✅ Complete |
| Phase 1–4 | Core System (nodes, paths, display layers, UI) | `feature/gaffer-system` | ✅ Complete |
| Phase 5 | Light Gaffer System | `feature/gaffer-system` | ✅ Complete |
| Phase 1 (schema) | Schema-Based Node System | `feature/gaffer-system` | ✅ Complete |
| **Phase 2 (current)** | **UI & Tools Framework Migration** | **`feature/ui-tools-framework`** | **🚧 In Progress** |

---

## Node System: Primary vs. Legacy

> **Rule for all new code:** Use `core/nodes/wrappers/` exclusively.
> `core/custom_nodes.py` is **DEPRECATED** — kept only for backward compatibility with existing Maya scenes.

| System | Location | Status | Use For |
|---|---|---|---|
| **Schema-Based (PRIMARY)** | `core/nodes/wrappers/` | ✅ Active | All new development |
| Legacy | `core/custom_nodes.py` | ⚠️ Deprecated | Backward compat only |

### Correct Import Pattern

```python
# ✅ CORRECT — use schema-based wrappers
from core.nodes.wrappers import (
    CTXManagerNode, CTXSequenceNode, CTXShotNode, CTXAssetNode,
    CTXLightGafferNode, CTXLightContextNode
)

# ❌ WRONG — do not use for new code
from core.custom_nodes import CTXManagerNode, CTXShotNode
```

### Correct Attribute Name

```python
# ✅ CORRECT
cmds.getAttr("{}.ctx_type".format(node_name))   # snake_case

# ❌ WRONG
cmds.getAttr("{}.ctx_node_type".format(node_name))  # do not use
```

---

## Connection Pattern: Unidirectional Only

All node relationships use **unidirectional connections** (`child.message → parent.attribute[i]`).

```python
# ✅ CORRECT — one connection per relationship
cmds.connectAttr("shot.message", "sequence.shots[0]", nextAvailable=True)
cmds.connectAttr("gaffer.message", "sequence.gaffer")

# ❌ WRONG — bidirectional (creates redundant connections)
cmds.connectAttr("sequence.message", "shot.parent_sequence")  # remove this
```

**Querying from either direction:**

```python
# Get all shots from a sequence (children from parent)
shots = cmds.listConnections("sequence.shots", source=True, destination=False)

# Get parent sequence from a shot (parent from child)
parent = cmds.listConnections("shot.message", source=False, destination=True)
```

---

## Node Hierarchy

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

Gaffer Inheritance Chain:
    Master CTX_LightGaffer
        ↑ parentGaffer  (MasterGaffer.message → SeqGaffer.parentGaffer)
    Sequence CTX_LightGaffer
        ↑ parentGaffer  (SeqGaffer.message → ShotGaffer.parentGaffer)
    Shot CTX_LightGaffer
        ↑ lights[i]     (LightContext.message → Gaffer.lights[i])
    CTX_LightContext (per-light attribute storage)
```

---

## Current Repository Structure (Post Phase 1)

This is the **actual current state** of the repository after completing the Schema-Based Node System migration.

```
maya-multishot/
│
├── core/
│   ├── custom_nodes.py          # ⚠️ DEPRECATED — legacy CTX node wrappers (keep for compat)
│   │
│   ├── nodes/                   # ✅ PRIMARY — Schema-based node system
│   │   ├── __init__.py
│   │   ├── base.py              # NodeSchema, NodeFactory, NodeWrapper base classes
│   │   ├── AGENTS.md            # Technical reference for node system
│   │   │
│   │   ├── schemas/             # Declarative node definitions
│   │   │   ├── __init__.py
│   │   │   ├── manager.py       # CTX_Manager schema
│   │   │   ├── sequence.py      # CTX_Sequence schema
│   │   │   ├── shot.py          # CTX_Shot schema
│   │   │   ├── asset.py         # CTX_Asset schema
│   │   │   ├── gaffer.py        # CTX_LightGaffer schema
│   │   │   └── light_context.py # CTX_LightContext schema
│   │   │
│   │   └── wrappers/            # High-level API (USE THIS)
│   │       ├── __init__.py
│   │       ├── manager.py       # CTXManagerNode wrapper
│   │       ├── sequence.py      # CTXSequenceNode wrapper
│   │       ├── shot.py          # CTXShotNode wrapper
│   │       ├── asset.py         # CTXAssetNode wrapper
│   │       ├── gaffer.py        # CTXLightGafferNode wrapper
│   │       └── light_context.py # CTXLightContextNode wrapper
│   │
│   ├── gaffer/                  # Light Gaffer system
│   │   ├── __init__.py
│   │   ├── manager.py           # GafferManager (add/remove/resolve)
│   │   ├── resolver.py          # AttributeResolver (chain walking)
│   │   ├── chain_ops.py         # Chain management operations
│   │   └── light_ops.py         # Light attribute capture/apply
│   │
│   ├── asset_path_resolver.py   # Asset path resolution
│   ├── asset_scanner.py         # Filesystem asset discovery
│   ├── config.py                # Configuration management
│   ├── context.py               # Context management
│   ├── ctx_converter.py         # Path token resolution
│   ├── ctx_linker.py            # Node linking utilities
│   ├── display_layers.py        # Display layer management
│   ├── nodes.py                 # NodeManager for asset types (legacy)
│   ├── path_builder.py          # Path building utilities
│   ├── reference_manager.py     # Maya reference operations
│   ├── resolver.py              # Path resolution engine
│   ├── shader_assignment.py     # Shader operations
│   ├── shader_discovery.py      # Shader discovery
│   ├── shot_metadata_loader.py  # Shot metadata
│   ├── shot_switching.py        # Shot switching logic
│   └── tokens.py                # Token system
│
├── ui/
│   ├── main_window.py           # 🔄 NEEDS MIGRATION — imports core.custom_nodes
│   ├── dockable_window.py       # ✅ No CTX node dependency
│   ├── gaffer_manager_dialog.py # ✅ Uses core.nodes.wrappers.gaffer
│   ├── light_editor_panel.py    # ✅ Uses core.nodes.wrappers.light_context
│   ├── add_shot_dialog.py       # ✅ No CTX node dependency
│   ├── add_light_dialog.py      # ✅ No CTX node dependency
│   ├── shot_context_dialog.py   # ✅ Accepts CTXShotNode as argument
│   ├── asset_manager_dialog.py  # ✅ No CTX node dependency
│   ├── create_reference_dialog.py # ✅ No CTX node dependency
│   ├── settings_dialog.py       # ✅ No CTX node dependency
│   ├── shot_widget.py           # ❌ Unused — superseded by main_window shot table
│   ├── asset_widget.py          # ❌ Unused — superseded by asset_manager_dialog
│   ├── filesystem_discovery.py  # ❌ Unused — absorbed by core/asset_scanner.py
│   ├── import_asset_dialog.py   # ❌ Unused — merged into asset_manager_dialog
│   └── convert_scene_dialog.py  # ❌ Unused — no active caller
│
├── tools/
│   ├── maya_menu.py             # ✅ Already uses core.nodes.wrappers
│   ├── shot_manager.py          # 🔄 NEEDS MIGRATION — uses legacy cmds + custom_nodes
│   └── asset_manager.py         # 🔄 NEEDS MIGRATION — inline custom_nodes imports
│
├── launch_multishot_dockable.py # ✅ Imports MainWindow (benefits from ui migration)
├── launch_multishot_manager.py  # ✅ Imports MainWindow (benefits from ui migration)
│
├── tests/
│   ├── node_creation_flow/      # Manual test scripts for node creation
│   ├── test_gaffer_manager.py   # Gaffer system tests (63 passing)
│   └── (other test modules)
│
├── vendor/
│   └── NodeGraphQt/             # Vendored graph UI library (future use)
│
├── spec/                        # Technical specifications
├── docs/                        # User documentation
└── examples/                    # Example scripts
```

---

## Target Repository Structure (Post Phase 2 Migration)

This is the **goal state** after completing the UI & Tools Framework migration (branch: `feature/ui-tools-framework`).

**Legend:** ✅ Exists & correct | 🔄 Needs migration | 🆕 Needs creation | ❌ Will be removed

```
maya-multishot/
│
├── core/
│   ├── custom_nodes.py          # ✅ KEEP — legacy compat, do NOT modify
│   ├── nodes/                   # ✅ PRIMARY node system — no changes needed
│   │   ├── schemas/             # ✅ All 6 schemas complete
│   │   └── wrappers/            # ✅ All 6 wrappers complete
│   ├── gaffer/                  # ✅ Complete — no changes needed
│   └── (all other core modules) # ✅ No changes needed
│
├── ui/
│   ├── __init__.py              # 🔄 Update __all__ — remove unused entries
│   ├── base_dialog.py           # 🆕 Create — shared Qt boilerplate (PySide6/2 try/except,
│   │                            #             _setup_ui/_connect_signals convention)
│   ├── main_window.py           # 🔄 Migrate — replace core.custom_nodes with core.nodes.wrappers
│   ├── dockable_window.py       # ✅ No changes needed
│   ├── gaffer_manager_dialog.py # ✅ Already uses new system
│   ├── light_editor_panel.py    # ✅ Already uses new system
│   ├── add_shot_dialog.py       # ✅ No CTX node dependency
│   ├── add_light_dialog.py      # ✅ No CTX node dependency
│   ├── shot_context_dialog.py   # ✅ No changes needed
│   ├── asset_manager_dialog.py  # ✅ No CTX node dependency
│   ├── create_reference_dialog.py # ✅ No CTX node dependency
│   ├── settings_dialog.py       # ✅ No CTX node dependency
│   ├── shot_widget.py           # ❌ Remove (superseded by shot table in main_window)
│   ├── asset_widget.py          # ❌ Remove (superseded by asset_manager_dialog)
│   ├── filesystem_discovery.py  # ❌ Remove (absorbed by core/asset_scanner.py)
│   ├── import_asset_dialog.py   # ❌ Remove (merged into asset_manager_dialog)
│   └── convert_scene_dialog.py  # ❌ Remove (no active caller)
│
├── tools/
│   ├── __init__.py              # 🔄 Update — expose new manager classes
│   ├── base_manager.py          # 🆕 Create — shared MockCmds, MAYA_AVAILABLE flag,
│   │                            #             BaseManager class (dependency injection)
│   ├── maya_menu.py             # ✅ Already uses core.nodes.wrappers
│   ├── shot_manager.py          # 🔄 Migrate — extend BaseManager, use wrappers
│   └── asset_manager.py         # 🔄 Migrate — extend BaseManager, use wrappers
│
├── launch_multishot_dockable.py # ✅ Auto-benefits from main_window migration
├── launch_multishot_manager.py  # ✅ Auto-benefits from main_window migration
│
└── (tests, vendor, spec, docs, examples — no changes needed)
```

---

## Phase 2 Migration: Implementation Order

Implement **one file at a time**, in this order:

| Step | File | Type | Reason |
|---|---|---|---|
| 1 | `tools/base_manager.py` | 🆕 Create | Foundation — no dependencies |
| 2 | `ui/base_dialog.py` | 🆕 Create | Foundation — no dependencies |
| 3 | `tools/shot_manager.py` | 🔄 Migrate | Extends base_manager + uses wrappers |
| 4 | `tools/asset_manager.py` | 🔄 Migrate | Extends base_manager + uses wrappers |
| 5 | `ui/main_window.py` | 🔄 Migrate | Replace CTXManagerNode/CTXShotNode imports |
| 6 | `ui/__init__.py` | 🔄 Update | Remove unused entries from `__all__` |
| 7 | `tools/__init__.py` | 🔄 Update | Expose new manager classes |
| 8 | Remove 5 unused `ui/` files | ❌ Remove | After migration verified |

---

## Implementation Order: Schema → Wrapper → Factory

For any new node type added in the future:

1. **NodeSchema** (Definition) — Define attributes and connection ports declaratively
2. **NodeWrapper** (API) — Implement high-level methods that use the schema
3. **NodeFactory** (Creation) — Built into `NodeWrapper.create()` classmethod

---

## Documentation Structure

| Document | Purpose | Contains Structure? |
|---|---|---|
| **ARCHITECTURE_SUMMARY.md** | **Repository structure** | ✅ **YES — Single source of truth** |
| `core/nodes/AGENTS.md` | Schema-based node system reference | ❌ NO — References this doc |
| `AGENTS.md` (root) | Project overview & key commands | ❌ NO — References this doc |
| `spec/NODE_ARCHITECTURE.md` | Schema system design details | ❌ NO — References this doc |
| `spec/DEVELOPMENT_PLAN.md` | Development roadmap | ❌ NO — References this doc |
| `spec/GAFFER_IMPLEMENTATION_PLAN.md` | Gaffer task breakdown | ❌ NO — References this doc |
| `spec/CTX_lightGaffer_spec.md` | Gaffer detailed specification | ❌ NO |
| `spec/CONNECTION_PATTERN_ANALYSIS.md` | Unidirectional connection justification | ❌ NO |

---

**Maintainer:** CTX Pipeline Team
**Last Review:** 2026-03-04

