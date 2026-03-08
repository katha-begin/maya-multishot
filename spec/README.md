# Maya Multishot - Specification Documentation

**Version:** 3.1
**Last Updated:** 2026-03-06
**Status:** Phase 2 In Progress — UI & Tools Framework Migration

---

## Documentation Index

This directory contains all specification and planning documents for the maya-multishot project.

### Core Specifications

| Document | Purpose | Status |
|----------|---------|--------|
| **[spec.md](spec.md)** | Main technical specification | ✅ Updated (v3.0) |
| **[tasks.md](tasks.md)** | Implementation task list and roadmap | ✅ Updated (v2.0) |

### Architecture Documents

| Document | Purpose | Status |
|----------|---------|--------|
| **[NODE_ARCHITECTURE.md](NODE_ARCHITECTURE.md)** | Schema-based node system architecture | ✅ Complete |
| **[ASSET_TYPES.md](ASSET_TYPES.md)** | Asset type handler system | ✅ Complete |
| **[RENDERER_ADAPTERS.md](RENDERER_ADAPTERS.md)** | Renderer adapter system | ✅ Complete |
| **[CTX_lightGaffer.md](CTX_lightGaffer.md)** | Light gaffer specification | ✅ Complete |

### Planning Documents

| Document | Purpose | Status |
|----------|---------|--------|
| **[DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)** | Development roadmap summary | ✅ Complete |
| **[ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md)** | Architecture overview | ✅ Complete |
| **[README.md](README.md)** | This document | ✅ Complete |

---

## Quick Start Guide

### For New Developers

1. **Read the main specification:**
   - Start with [spec.md](spec.md) to understand the project
   - Review [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) for current status

2. **Understand the architecture:**
   - Read [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md) for overview
   - Review [NODE_ARCHITECTURE.md](NODE_ARCHITECTURE.md) for details

3. **Check the task list:**
   - See [tasks.md](tasks.md) for implementation roadmap
   - Find tasks marked as ⏳ Pending to start working

### For Existing Developers

1. **Check what's new:**
   - Review [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) for latest updates
   - Check [tasks.md](tasks.md) for new phases

2. **Understand schema migration:**
   - Read [NODE_ARCHITECTURE.md](NODE_ARCHITECTURE.md) Section 8
   - Review migration strategy and compatibility layer

3. **Start implementing:**
   - Begin with Phase 5 tasks in [tasks.md](tasks.md)
   - Follow acceptance criteria for each task

---

## Project Status

### ✅ Completed

- **Phases 0–4:** Multi-shot management, token-based path resolution, display layers, asset/shot management UI
- **Phase 5:** Light Gaffer System — hierarchical light management (Master → Sequence → Shot), 63 passing tests
- **Phase 1 (schema):** Schema-Based Node System — all 6 node types (Manager, Sequence, Shot, Asset, LightGaffer, LightContext), unidirectional connections, `core/nodes/wrappers/`

**Primary Node System:** `core/nodes/wrappers/` — use for all new code
**Legacy (deprecated, read-only):** `core/custom_nodes.py` — backward compatibility only

### 🚧 In Progress — Phase 2: UI & Tools Framework Migration

**Branch:** `feature/ui-tools-framework`

1. Create `tools/base_manager.py` — `BaseManager` class, `MockCmds`, `MAYA_AVAILABLE`
2. Create `ui/base_dialog.py` — shared Qt boilerplate (PySide6/PySide2 try/except)
3. Migrate `tools/shot_manager.py` — extend `BaseManager`, use schema wrappers
4. Migrate `tools/asset_manager.py` — extend `BaseManager`, use schema wrappers
5. Migrate `ui/main_window.py` — replace `core.custom_nodes` imports with `core.nodes.wrappers`
6. Remove 5 unused `ui/` files

---

## Architecture Overview

### Current System (Schema-Based)

```
NodeSchema (Definition)
    ↓
NodeFactory (Creation) → Maya Node
    ↓
NodeWrapper (High-level API)
```

**Node Hierarchy:**
```
CTX_Manager (singleton)
    ↑ sequences[i]   (Sequence.message → Manager.sequences[i])
CTX_Sequence
    ↑ shots[i]       (Shot.message → Sequence.shots[i])
    ↑ gaffer         (SeqGaffer.message → Sequence.gaffer)
CTX_Shot
    ↑ assets[i]      (Asset.message → Shot.assets[i])
    ↑ gaffer         (ShotGaffer.message → Shot.gaffer)
CTX_Asset
```

**Key Rule:** All connections are **unidirectional** (`child.message → parent.attribute`). Never bidirectional.

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Node Architecture** | Schema-based | Centralized, extensible, graph-friendly |
| **Node Types** | Network + filtering | Simple, backward compatible |
| **Asset Types** | Handler registry | Extensible, USD-ready |
| **Renderers** | Adapter pattern | Renderer-agnostic core |
| **Migration** | Parallel implementation | No breaking changes |
| **Gaffer** | Per-attribute inheritance | Flexible, no gaffer_type needed |

---

## Development Workflow

### Current Phase: Phase 2 — UI & Tools Framework Migration

See [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md) for the full Phase 2 task list and target repository structure.

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=core --cov-report=html tests/
```

### Contributing

1. Read [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md) for current state
2. Use `core.nodes.wrappers` — never `core.custom_nodes`
3. Write tests first (TDD)
4. Follow unidirectional connection pattern

---

## Contributing

### Before Starting Work

1. Read relevant specification documents
2. Check task dependencies in [tasks.md](tasks.md)
3. Create feature branch from `develop`
4. Follow acceptance criteria

### During Development

1. Write tests first (TDD)
2. Follow code style guidelines
3. Update documentation
4. Commit frequently with clear messages

### Before Submitting PR

1. All tests passing
2. Code coverage > 90%
3. Documentation updated
4. PR template filled out

---

## Questions?

- **Architecture Questions:** See [NODE_ARCHITECTURE.md](NODE_ARCHITECTURE.md)
- **Task Questions:** See [tasks.md](tasks.md)
- **General Questions:** See [spec.md](spec.md)
- **Status Questions:** See [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)

---

**Maintainer:** CTX Pipeline Team
**Repository:** https://github.com/katha-begin/maya-multishot.git
**Last Updated:** 2026-03-06

