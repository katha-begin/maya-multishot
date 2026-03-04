# Maya Multishot - Architecture Summary

**Version:** 2.0
**Last Updated:** 2026-02-22
**Status:** SINGLE SOURCE OF TRUTH for Repository Structure

---

## Overview

**⚠️ This document is the SINGLE SOURCE OF TRUTH for repository structure.**

All other documents should reference this document for structure information.

---

## Repository Structure Comparison

### BEFORE (Current Production Structure)

```
maya-multishot/
├── core/
│   ├── custom_nodes.py          # CTX node wrappers (Manager, Sequence, Shot, Asset)
│   ├── config.py                # Configuration management
│   ├── context.py               # Context management
│   ├── ctx_converter.py         # Path token resolution
│   ├── ctx_linker.py            # Node linking utilities
│   ├── display_layers.py        # Display layer management
│   ├── nodes.py                 # NodeManager for asset types
│   ├── path_builder.py          # Path building utilities
│   ├── reference_manager.py     # Reference operations
│   ├── resolver.py              # Path resolution
│   ├── shader_assignment.py     # Shader operations
│   ├── shader_discovery.py      # Shader discovery
│   ├── shot_metadata_loader.py  # Shot metadata
│   ├── shot_switching.py        # Shot switching logic
│   └── tokens.py                # Token system
│
├── ui/
│   ├── main_window.py           # Multishot Manager (main UI)
│   ├── asset_manager_dialog.py  # Asset management UI
│   ├── add_shot_dialog.py       # Add shot dialog
│   ├── shot_context_dialog.py   # Shot context UI
│   ├── create_reference_dialog.py
│   ├── import_asset_dialog.py
│   ├── settings_dialog.py
│   ├── asset_widget.py
│   ├── shot_widget.py
│   ├── dockable_window.py
│   └── filesystem_discovery.py
│
├── spec/                        # Documentation
└── tests/                       # Test files
```

**Characteristics:**
- ✅ All existing code in `core/` directory
- ✅ UI files in `ui/` directory
- ❌ No schema-based node system
- ❌ No asset type handlers
- ❌ No renderer adapters
- ❌ No gaffer system

---

### AFTER (Future Schema-Based Structure)

```
maya-multishot/
├── core/
│   ├── custom_nodes.py          # LEGACY - keep for compatibility
│   │
│   ├── nodes/                   # NEW - Schema-based node system
│   │   ├── __init__.py
│   │   ├── base.py              # NodeSchema, NodeFactory, NodeWrapper base classes
│   │   ├── registry.py          # Node type registry
│   │   │
│   │   ├── schemas/             # Node schema definitions (declarative)
│   │   │   ├── __init__.py
│   │   │   ├── manager.py       # CTX_Manager schema
│   │   │   ├── sequence.py      # CTX_Sequence schema
│   │   │   ├── shot.py          # CTX_Shot schema
│   │   │   ├── asset.py         # CTX_Asset schema
│   │   │   ├── gaffer.py        # CTX_LightGaffer schema
│   │   │   └── light_context.py # CTX_LightContext schema
│   │   │
│   │   └── wrappers/            # Node wrapper classes (high-level API)
│   │       ├── __init__.py
│   │       ├── base.py          # NodeWrapper base class
│   │       ├── manager.py       # CTX_Manager wrapper
│   │       ├── sequence.py      # CTX_Sequence wrapper
│   │       ├── shot.py          # CTX_Shot wrapper
│   │       ├── asset.py         # CTX_Asset wrapper
│   │       ├── gaffer.py        # CTX_LightGaffer wrapper
│   │       └── light_context.py # CTX_LightContext wrapper
│   │
│   ├── asset_types/             # NEW - Asset type handlers (plugin architecture)
│   │   ├── __init__.py
│   │   ├── base.py              # AssetTypeHandler base class
│   │   ├── registry.py          # AssetTypeRegistry
│   │   ├── arnold.py            # ArnoldStandInHandler
│   │   ├── redshift.py          # RedshiftProxyHandler
│   │   ├── usd.py               # USDReferenceHandler
│   │   └── reference.py         # MayaReferenceHandler
│   │
│   ├── renderers/               # NEW - Renderer adapters (plugin architecture)
│   │   ├── __init__.py
│   │   ├── base.py              # RendererAdapter base class
│   │   ├── registry.py          # RendererRegistry
│   │   ├── arnold.py            # ArnoldAdapter
│   │   └── redshift.py          # RedshiftAdapter
│   │
│   ├── gaffer/                  # NEW - Gaffer system
│   │   ├── __init__.py
│   │   ├── manager.py           # GafferManager (add/remove/resolve operations)
│   │   ├── resolver.py          # AttributeResolver (chain walking)
│   │   └── light_ops.py         # Light operations (capture/apply values)
│   │
│   └── (all existing modules remain unchanged)
│
├── ui/
│   ├── (all existing UI files remain unchanged)
│   │
│   └── gaffer_manager_dialog.py # NEW - Gaffer Manager UI
│
├── vendor/
│   └── NodeGraphQt/             # NEW - Vendored graph UI library (future)
│
├── tests/
│   ├── (existing tests)
│   └── nodegraphqt_components/  # NEW - Graph integration tests (future)
│
└── spec/
    ├── (existing docs)
    ├── CTX_gaffer_UI.md         # NEW - Gaffer UI specification
    └── GAFFER_IMPLEMENTATION_PLAN.md # Implementation task breakdown
```

**Characteristics:**
- ✅ All existing code remains unchanged
- ✅ New directories added alongside existing code
- ✅ Schema-based node system in `core/nodes/`
- ✅ Asset type handlers in `core/asset_types/`
- ✅ Renderer adapters in `core/renderers/`
- ✅ Gaffer system in `core/gaffer/`
- ✅ Gaffer UI in `ui/gaffer_manager_dialog.py`

---

## Implementation Order

### Correct Order: Schema → Wrapper → Factory

1. **NodeSchema** (Definition) - Define what the node looks like
2. **NodeWrapper** (API) - Create the API that uses the schema
3. **NodeFactory** (Creation) - Helper for creation (can be inside Wrapper or separate)

**Why this order?**
- Schema defines structure (ATTRIBUTES, CONNECTIONS)
- Wrapper uses schema to provide high-level API
- Factory is just a utility function (can be a method inside Wrapper.create())

---

## Documentation Structure

| Document | Purpose | Contains Structure? |
|----------|---------|---------------------|
| **ARCHITECTURE_SUMMARY.md** | **Repository structure** | ✅ **YES - Single source of truth** |
| NODE_ARCHITECTURE.md | Schema-based node system details | ❌ NO - References this doc |
| DEVELOPMENT_PLAN.md | Development roadmap | ❌ NO - References this doc |
| GAFFER_IMPLEMENTATION_PLAN.md | Gaffer task breakdown | ❌ NO - References this doc |
| CTX_lightGaffer.md | Gaffer architecture overview | ❌ NO |
| CTX_lightGaffer_spec.md | Gaffer detailed specification | ❌ NO |
| CTX_gaffer_UI.md | Gaffer UI specification | ❌ NO |

---

**Maintainer:** CTX Pipeline Team  
**Last Review:** 2026-02-21

