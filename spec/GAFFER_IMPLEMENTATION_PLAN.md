# Gaffer System - Implementation Plan

**Version:** 1.0
**Date:** 2026-02-22
**Status:** Planning
**Related:** [NODE_ARCHITECTURE.md](NODE_ARCHITECTURE.md), [CTX_lightGaffer.md](CTX_lightGaffer.md), [CTX_lightGaffer_spec.md](CTX_lightGaffer_spec.md)

---

## Overview

This document provides a clear, actionable task breakdown for implementing the gaffer system aligned with the new schema-based node architecture.

---

## Key Requirements (User-Confirmed)

1. ✅ **Flexible chain-based architecture** - Not hardcoded by type (master/seq/shot)
2. ✅ **User-editable values in active shot** - Direct editing creates overrides automatically
3. ✅ **Gaffer selection dropdown** - UI to select specific gaffer (Master/Seq/Shot)
4. ✅ **Convert existing Maya lights** - Function to add lights to gaffer with value capture
5. ✅ **Follow active shot from context manager** - Auto-select shot gaffer when shot switches
6. ✅ **Align with NODE_ARCHITECTURE.md** - Use schema-based, centralized node system

---

## Architecture Alignment

**See:** [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md) for complete repository structure.

### Schema-Based Node System (from NODE_ARCHITECTURE.md)

```
┌─────────────────┐
│  NodeSchema     │  ← Declarative definition (CTXLightGafferSchema)
│  (Definition)   │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  NodeFactory    │  ← Creates Maya nodes from schema
│  (Creation)     │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  NodeWrapper    │  ← High-level API (CTXLightGafferNode)
│  (API)          │
└─────────────────┘
```

### Gaffer System Structure

```
core/
├── nodes/
│   ├── base.py                    # NodeSchema, NodeFactory (existing)
│   ├── schemas/
│   │   ├── gaffer.py              # NEW: CTXLightGafferSchema
│   │   └── light_context.py      # NEW: CTXLightContextSchema
│   └── wrappers/
│       ├── gaffer.py              # NEW: CTXLightGafferNode
│       └── light_context.py      # NEW: CTXLightContextNode
├── gaffer/
│   ├── __init__.py
│   ├── manager.py                 # NEW: GafferManager (add/remove/resolve)
│   ├── resolver.py                # NEW: AttributeResolver (chain walking)
│   └── light_ops.py               # NEW: Light operations (capture/apply)
└── renderers/
    ├── base.py                    # RendererAdapter (existing)
    ├── arnold.py                  # ArnoldAdapter (existing)
    └── redshift.py                # RedshiftAdapter (existing)

ui/
└── gaffer_manager_dialog.py      # NEW: Gaffer Manager UI
```

---

## Implementation Tasks

### Phase 1: Core Schemas (Week 1, Days 1-2)

**Task 1.1: Create CTXLightGafferSchema**
- [ ] Create `core/nodes/schemas/gaffer.py`
- [ ] Define ATTRIBUTES (gafferName, gafferType, scopeCode, enabled, etc.)
- [ ] Define CONNECTIONS (parentNode, parentGaffer, childGaffers, lights)
- [ ] Add validation rules
- [ ] Write unit tests

**Task 1.2: Create CTXLightContextSchema**
- [ ] Create `core/nodes/schemas/light_context.py`
- [ ] Define ATTRIBUTES (lightName, intensity, color, transform, etc.)
- [ ] Define enabled flags for each attribute (intensityEnabled, colorEnabled, etc.)
- [ ] Define CONNECTIONS (parentGaffer, targetLight)
- [ ] Add validation rules
- [ ] Write unit tests

**Deliverable:** Schema definitions ready for node creation

---

### Phase 2: Node Wrappers (Week 1, Days 3-4)

**Task 2.1: Create CTXLightGafferNode Wrapper**
- [ ] Create `core/nodes/wrappers/gaffer.py`
- [ ] Implement `create()` - Create gaffer from schema
- [ ] Implement `get_parent_gaffer()` - Get parent in chain
- [ ] Implement `get_child_gaffers()` - Get children in chain
- [ ] Implement `get_lights()` - Get all light contexts
- [ ] Implement `build_chain()` - Build inheritance chain list
- [ ] Write unit tests

**Task 2.2: Create CTXLightContextNode Wrapper**
- [ ] Create `core/nodes/wrappers/light_context.py`
- [ ] Implement `create()` - Create light context from schema
- [ ] Implement `get_parent_gaffer()` - Get owning gaffer
- [ ] Implement `get_target_light()` - Get Maya light shape
- [ ] Implement `get_enabled_attributes()` - Get list of overridden attributes
- [ ] Implement `set_attribute_override()` - Set value + enable flag
- [ ] Write unit tests

**Deliverable:** Node creation and basic operations working

---

### Phase 3: Gaffer Manager (Week 1, Days 4-5)

**Task 3.1: Create GafferManager**
- [ ] Create `core/gaffer/manager.py`
- [ ] Implement `add_light_to_gaffer()` - Convert Maya light to CTX_LightContext
- [ ] Implement `remove_light_from_gaffer()` - Delete CTX_LightContext
- [ ] Implement `add_override_to_gaffer()` - Create override in child gaffer
- [ ] Implement `get_lights_in_gaffer()` - List all lights (direct + inherited)
- [ ] Implement `capture_light_values()` - Read values from Maya light
- [ ] Write unit tests

**Task 3.2: Create AttributeResolver**
- [ ] Create `core/gaffer/resolver.py`
- [ ] Implement `resolve_attribute()` - Walk chain to find enabled value
- [ ] Implement `resolve_all_attributes()` - Resolve all attributes for a light
- [ ] Implement `get_attribute_source()` - Find which gaffer provides value
- [ ] Write unit tests

**Deliverable:** Core gaffer operations functional

---

### Phase 4: Light Operations (Week 2, Days 1-2)

**Task 4.1: Create Light Operations Module**
- [ ] Create `core/gaffer/light_ops.py`
- [ ] Implement `apply_gaffer_to_lights()` - Apply resolved values to Maya lights
- [ ] Implement `capture_from_maya()` - Read current Maya light values
- [ ] Implement `apply_to_maya()` - Write values to Maya light
- [ ] Integrate with RendererAdapter for renderer-agnostic attribute setting
- [ ] Handle muted lights (skip application)
- [ ] Write unit tests

**Task 4.2: Shot Switching Integration**
- [ ] Update `core/custom_nodes.py` CTXShotNode.activate()
- [ ] Add gaffer resolution on shot switch
- [ ] Add automatic light value application
- [ ] Test with multiple shots

**Deliverable:** Light values apply correctly on shot switch

---

### Phase 5: UI Implementation (Week 2, Days 3-5)

**Task 5.1: Create Gaffer Manager UI**
- [ ] Create `ui/gaffer_manager_dialog.py`
- [ ] Add gaffer selection dropdown (Master/Seq/Shot)
- [ ] Add gaffer chain display (Master → Seq → Shot ← Active)
- [ ] Add light list table (Name, Enabled, Muted, Source, Override)
- [ ] Add [Add Light] button - Select Maya light → add to gaffer
- [ ] Add [Remove Light] button - Remove from current gaffer
- [ ] Add [Add Override] button - Create override in child gaffer
- [ ] Add [Apply to Maya] button - Force apply values
- [ ] Add [Refresh] button - Rebuild light list
- [ ] Auto-select active shot's gaffer when shot switches
- [ ] Write UI tests

**Task 5.2: Create Light Editor UI (Detail Window)**
- [ ] Create light detail panel
- [ ] Show all attributes with current values
- [ ] Show source gaffer for each attribute
- [ ] Show inherited value (if overridden)
- [ ] Add checkbox to enable/disable override per attribute
- [ ] Add [Capture from Maya] button
- [ ] Add [Apply to Maya] button
- [ ] Add [Reset to Parent] button
- [ ] Write UI tests

**Task 5.3: Integrate with Multishot Manager**
- [ ] Add "Gaffer Manager" button to Multishot Manager
- [ ] Connect shot switching to gaffer UI updates
- [ ] Test integration

**Deliverable:** Complete UI for gaffer management

---

### Phase 6: Documentation Updates (Week 3, Day 1)

**Task 6.1: Update CTX_lightGaffer.md**
- [ ] Update Section 2.1 - Clarify flexible architecture (not type-based)
- [ ] Update Section 2.2 - Add note about conventions vs requirements
- [ ] Update Section 7.3 - Make gafferType optional/descriptive
- [ ] Add Section 7.7 - Add/Remove Light Workflows
- [ ] Add Section 7.8 - User-Editable Active Shot Values
- [ ] Add Section 7.9 - Gaffer Selection Dropdown
- [ ] Update all examples to show new workflows

**Task 6.2: Update CTX_lightGaffer_spec.md**
- [ ] Update Section 2.4 - Reframe as "Naming Conventions"
- [ ] Update Section 3.2 - Update gafferType description
- [ ] Add Section 8 - Light Management API
- [ ] Add API docs for add_light_to_gaffer()
- [ ] Add API docs for remove_light_from_gaffer()
- [ ] Add API docs for add_override_to_gaffer()
- [ ] Add workflow diagrams

**Deliverable:** Documentation aligned with implementation

---

### Phase 7: Testing & Integration (Week 3, Days 2-5)

**Task 7.1: Integration Testing**
- [ ] Test with Arnold renderer
- [ ] Test with Redshift renderer
- [ ] Test shot switching with multiple shots
- [ ] Test gaffer chain with custom gaffers
- [ ] Test user editing values in active shot
- [ ] Performance testing (100+ lights)

**Task 7.2: User Acceptance Testing**
- [ ] Create test scene with 2 sequences, 4 shots, 10 lights
- [ ] Test all workflows (add/remove/override/edit)
- [ ] Gather feedback
- [ ] Fix issues

**Deliverable:** Production-ready gaffer system

---

## Success Criteria

✅ **Functional:**
- [ ] Can create gaffers at Master/Seq/Shot levels
- [ ] Can add existing Maya lights to gaffers
- [ ] Can remove lights from gaffers
- [ ] Can create overrides in child gaffers
- [ ] Can edit values in active shot (auto-creates overrides)
- [ ] Light values apply correctly on shot switch
- [ ] Works with Arnold and Redshift

✅ **UI:**
- [ ] Gaffer selection dropdown works
- [ ] Light list shows all lights (direct + inherited)
- [ ] Can identify which gaffer provides each value
- [ ] Override badges show correctly
- [ ] Auto-selects active shot's gaffer

✅ **Architecture:**
- [ ] Uses schema-based node system
- [ ] Follows NODE_ARCHITECTURE.md patterns
- [ ] Centralized attribute definitions
- [ ] Renderer-agnostic via adapters

✅ **Documentation:**
- [ ] CTX_lightGaffer.md updated
- [ ] CTX_lightGaffer_spec.md updated
- [ ] All workflows documented
- [ ] API reference complete

---

## Timeline

**Total Duration:** 3 weeks

- **Week 1:** Core implementation (schemas, wrappers, manager, resolver)
- **Week 2:** Light operations, UI implementation
- **Week 3:** Documentation, testing, integration

---

## Next Steps

1. **Review this plan** - Confirm alignment with your understanding
2. **Start Phase 1** - Create schemas
3. **Implement incrementally** - One phase at a time
4. **Test continuously** - Write tests as you go

---

**Status:** ⏳ Awaiting approval to begin implementation  
**Maintainer:** CTX Pipeline Team

