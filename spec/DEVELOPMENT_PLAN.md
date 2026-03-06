# Maya Multishot - Development Plan Summary

**Version:** 2.0
**Last Updated:** 2026-03-06
**Status:** Phase 2 In Progress — UI & Tools Framework Migration
**Related Docs:** [spec.md](spec.md), [tasks.md](tasks.md), [NODE_ARCHITECTURE.md](NODE_ARCHITECTURE.md), [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md)

---

## Current Status

### ✅ Completed Work

**Phases 0–4: Core Infrastructure** - COMPLETE
- Repository setup, CTX node system, token-based path resolution
- Display layer management, Shot/Asset management UI
- Maya menu integration

**Phase 5: Light Gaffer System** - COMPLETE
- Hierarchical light management (Master → Sequence → Shot)
- Per-attribute inheritance with enable flags
- 63 passing tests
- `core/gaffer/` — manager, resolver, chain_ops, light_ops

**Phase 1 (schema): Schema-Based Node System** - COMPLETE
- All 6 node types in `core/nodes/wrappers/`: Manager, Sequence, Shot, Asset, LightGaffer, LightContext
- Unidirectional connection pattern (`child.message → parent.attribute`)
- `ctx_type` attribute naming (replaces deprecated `ctx_node_type`)
- `core/custom_nodes.py` marked deprecated — kept for backward compat only

---

## Current Phase: Phase 2 — UI & Tools Framework Migration

**Branch:** `feature/ui-tools-framework`

### Task List (in order)

| # | Task | Status |
|---|------|--------|
| 1 | Create `tools/base_manager.py` — `BaseManager`, `MockCmds`, `MAYA_AVAILABLE` | 🚧 Pending |
| 2 | Create `ui/base_dialog.py` — shared Qt boilerplate | 🚧 Pending |
| 3 | Migrate `tools/shot_manager.py` — extend `BaseManager`, use wrappers | 🚧 Pending |
| 4 | Migrate `tools/asset_manager.py` — extend `BaseManager`, use wrappers | 🚧 Pending |
| 5 | Migrate `ui/main_window.py` — replace `core.custom_nodes` with `core.nodes.wrappers` | 🚧 Pending |
| 6 | Update `ui/__init__.py` and `tools/__init__.py` | 🚧 Pending |
| 7 | Delete 5 unused `ui/` files | 🚧 Pending |

---

## Roadmap

### Q1 2026

- Complete Phase 2 UI & Tools Framework migration
- Migrate all tools to `BaseManager`
- Remove unused UI files

### Q2 2026

- NodeGraphQt visual graph integration
- USD support
- Multi-renderer support (Arnold, Redshift)

---

## Key Architecture Documents

| Document | Purpose | Status |
|----------|---------|--------|
| [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md) | Repository structure — single source of truth | ✅ Current |
| [spec.md](spec.md) | Main specification | ✅ Current |
| [tasks.md](tasks.md) | Task tracking | ✅ Current |
| [NODE_ARCHITECTURE.md](NODE_ARCHITECTURE.md) | Schema-based node system | ✅ Complete |
| [ASSET_TYPES.md](ASSET_TYPES.md) | Asset type handlers | ✅ Complete |
| [RENDERER_ADAPTERS.md](RENDERER_ADAPTERS.md) | Renderer adapters | ✅ Complete |
| [CTX_lightGaffer.md](CTX_lightGaffer.md) | Gaffer specification | ✅ Complete |

---

## Repository Structure

**See:** [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md) for the full current and target repository structure.

---

**Maintainer:** CTX Pipeline Team  
**Contact:** katha-begin

