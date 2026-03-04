# Maya Multishot - Development Plan Summary

**Version:** 1.0
**Last Updated:** 2026-02-22
**Status:** Active Development
**Related Docs:** [spec.md](spec.md), [tasks.md](tasks.md), [NODE_ARCHITECTURE.md](NODE_ARCHITECTURE.md)

---

## Current Status

### ✅ Completed Work (Phases 0-4)

**Phase 0: Repository Setup** - COMPLETE
- Repository structure created
- Git workflow established
- Development environment configured

**Phase 1: Core Architecture & Data Model** - COMPLETE
- CTX_Manager, CTX_Shot, CTX_Asset nodes implemented
- Node wrapper classes functional
- Message attribute connections working
- Shot/asset hierarchy established

**Phase 2: Path Resolution & Token System** - COMPLETE
- Token-based path resolution implemented
- Template system working
- Config file structure established
- Path resolver functional

**Phase 3: Display Layer Management** - COMPLETE
- Per-shot display layer system implemented
- Layer creation/deletion working
- Layer switching functional
- Shot isolation working

**Phase 4: Tools & UI** - MOSTLY COMPLETE
- Multishot Manager UI implemented
- Asset Manager UI implemented
- Add Shot Dialog with filtering
- Right-click context menus
- Multi-selection support
- Search/filter functionality

**Core Modules Implemented:**
- `core/custom_nodes.py` - CTX node wrappers
- `core/config.py` - Configuration management
- `core/ctx_converter.py` - Path token resolution
- `core/display_layers.py` - Display layer management
- `core/nodes.py` - NodeManager for asset types
- `core/reference_manager.py` - Reference operations
- `core/shader_assignment.py` - Shader operations
- `core/shader_discovery.py` - Shader discovery
- `ui/multishot_manager_dialog.py` - Main UI
- `ui/asset_manager_dialog.py` - Asset management UI
- `ui/add_shot_dialog.py` - Shot addition UI

---

## Next Phase: Schema-Based Node System

### 🎯 Strategic Goal

Migrate from imperative node creation to **schema-based, declarative node system** that provides:
- Centralized node definitions
- Type safety and validation
- Extensibility for new node types, asset types, and renderers
- NodeGraphQt integration
- USD support
- Multi-renderer support (Arnold, Redshift, future)

### 📋 Four-Week Roadmap

**Week 1: Foundation + Planning**
- Create `core/nodes/` structure
- Implement base classes (NodeSchema, NodeFactory, NodeWrapper)
- Create `core/asset_types/` structure
- Create `core/renderers/` structure
- Create `core/gaffer/` structure
- Document all schemas

**Week 2: Gaffer Implementation**
- Implement gaffer schemas
- Implement gaffer wrappers
- Implement per-attribute inheritance system
- Integrate with renderer adapters
- Create Light Manager UI
- Write tests

**Week 3: Asset & Renderer Systems**
- Implement asset type handlers (Arnold, Redshift, USD)
- Implement renderer adapters (Arnold, Redshift)
- Update Asset Manager to use handlers
- Write tests

**Week 4: Node Migration**
- Migrate CTX_Asset to schema-based
- Migrate CTX_Shot to schema-based
- Migrate CTX_Manager to schema-based
- Create compatibility layer
- Update all UI code
- Write migration tests

---

## Key Architecture Documents

| Document | Purpose | Status |
|----------|---------|--------|
| [spec.md](spec.md) | Main specification | ⚠️ Needs Update |
| [tasks.md](tasks.md) | Task tracking | ⚠️ Needs Update |
| [NODE_ARCHITECTURE.md](NODE_ARCHITECTURE.md) | Schema-based node system | ✅ Complete |
| [ASSET_TYPES.md](ASSET_TYPES.md) | Asset type handlers | ✅ Complete |
| [RENDERER_ADAPTERS.md](RENDERER_ADAPTERS.md) | Renderer adapters | ✅ Complete |
| [CTX_lightGaffer.md](CTX_lightGaffer.md) | Gaffer specification | ✅ Complete |

---

## Repository Structure

**See:** [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md) for complete repository structure comparison (BEFORE/AFTER).

**Summary:** New directories will be added alongside existing code:
- `core/nodes/` - Schema-based node system (schemas + wrappers)
- `core/asset_types/` - Asset type handlers (Arnold, Redshift, USD)
- `core/renderers/` - Renderer adapters (Arnold, Redshift)
- `core/gaffer/` - Gaffer system (manager, resolver, light_ops)
- `vendor/NodeGraphQt/` - Vendored graph UI library
- `ui/gaffer_manager_dialog.py` - Gaffer Manager UI

---

## Immediate Next Steps

1. ✅ **Complete NODE_ARCHITECTURE.md** - DONE
2. ✅ **Create ASSET_TYPES.md** - DONE
3. ✅ **Create RENDERER_ADAPTERS.md** - DONE
4. ⏳ **Update spec.md** - IN PROGRESS
5. ⏳ **Update tasks.md** - IN PROGRESS
6. ⏳ **Begin Phase 1 implementation** - PENDING

---

**Maintainer:** CTX Pipeline Team  
**Contact:** katha-begin

