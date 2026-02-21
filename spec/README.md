# Maya Multishot - Specification Documentation

**Version:** 3.0  
**Last Updated:** 2026-02-20  
**Status:** Production + Schema Migration Planning

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

### ✅ Completed (Phases 0-4)

**Production-Ready Features:**
- Multi-shot scene management
- Token-based path resolution
- Display layer system
- Asset management UI
- Shot management UI
- Arnold/Redshift support

**Core Modules:**
- `core/custom_nodes.py` - CTX node system
- `core/config.py` - Configuration
- `core/ctx_converter.py` - Path resolution
- `core/display_layers.py` - Display layers
- `ui/multishot_manager_dialog.py` - Main UI
- `ui/asset_manager_dialog.py` - Asset UI

### ⏳ In Progress (Phases 5-8)

**Schema-Based Node System:**
- Week 1: Foundation & Planning
- Week 2: Gaffer Implementation
- Week 3: Asset & Renderer Systems
- Week 4: Node Migration

**New Features:**
- USD support
- Multi-renderer support
- Light gaffer system
- NodeGraphQt integration

---

## Architecture Overview

### Current System

```
CTX_Manager (network node)
    ├── CTX_Sequence (network node)
    │   └── CTX_Shot (network node)
    │       └── CTX_Asset (network node)
    │           └── targetNode (message link)
    │               └── Maya Node (aiStandIn/RedshiftProxy/reference)
```

**Pattern:** Imperative node creation with wrapper classes

### Future System

```
Schema Definition → NodeFactory → NodeWrapper → Maya Node
                                      ↓
                              AssetTypeHandler
                                      ↓
                              RendererAdapter
```

**Pattern:** Schema-based declarative system with plugin architecture

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

### 1. Planning Phase (Current)

- ✅ Architecture documents complete
- ✅ Task list updated
- ✅ Specifications finalized
- ⏳ Ready to begin implementation

### 2. Implementation Phase (Next)

**Week 1: Foundation**
- Create directory structure
- Implement base classes
- Document schemas

**Week 2: Gaffer**
- Implement gaffer system
- Prove schema pattern
- Create Light Manager UI

**Week 3: Asset/Renderer**
- Implement handlers/adapters
- Add USD support
- Update Asset Manager

**Week 4: Migration**
- Migrate existing nodes
- Create compatibility layer
- Update all UI code

### 3. Testing Phase

- Unit tests (90%+ coverage)
- Integration tests
- Migration tests
- Compatibility tests

### 4. Deployment Phase

- Feature flags
- Gradual rollout
- User documentation
- Training materials

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
**Last Updated:** 2026-02-20

