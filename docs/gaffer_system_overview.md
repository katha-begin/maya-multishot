# CTX Light Gaffer System - Overview

**Version:** 1.0  
**Last Updated:** 2026-02-21  
**Status:** Production Ready

---

## Table of Contents

1. [Introduction](#introduction)
2. [Key Concepts](#key-concepts)
3. [Architecture](#architecture)
4. [Quick Start](#quick-start)
5. [Related Documentation](#related-documentation)

---

## Introduction

The CTX Light Gaffer System is a hierarchical light management system for Maya that enables artists to manage lighting across multiple shots with inheritance-based overrides.

### What is a Gaffer?

A **gaffer** is a container that stores light attribute values (intensity, color, position, etc.) and can inherit from parent gaffers. This creates a hierarchy where:

- **Master Gaffer**: Global lighting setup (all shots inherit from this)
- **Sequence Gaffer**: Sequence-specific overrides (all shots in sequence inherit)
- **Shot Gaffer**: Shot-specific overrides (highest priority)

### Key Benefits

✅ **Hierarchical Inheritance**: Child gaffers inherit from parents, reducing duplication  
✅ **Per-Attribute Overrides**: Each attribute can be independently overridden  
✅ **Flexible Chains**: Not limited to Master→Seq→Shot, supports custom hierarchies  
✅ **Non-Destructive**: Original Maya lights remain unchanged  
✅ **Version Control Friendly**: Gaffer data stored in Maya scene as network nodes  
✅ **Artist-Friendly UI**: Intuitive interface for managing lights and overrides

---

## Key Concepts

### 1. Gaffer Hierarchy

```
Master Gaffer (Global)
    ↓ inherits
Sequence Gaffer (sq0070)
    ↓ inherits
Shot Gaffer (SH0010)
```

Each gaffer can override specific attributes while inheriting others from its parent.

### 2. Light Context

A **Light Context** (`CTX_LightContext`) is a node that stores attribute values for a specific light within a gaffer. It contains:

- Target light reference (Maya light shape)
- Attribute values (intensity, exposure, color, etc.)
- Per-attribute enable flags (which attributes are overridden)

### 3. Attribute Resolution

When you query a light's attributes, the system **walks the gaffer chain** from child to parent:

1. Check Shot gaffer: Is intensity enabled? → Use shot value
2. If not, check Sequence gaffer: Is intensity enabled? → Use sequence value
3. If not, check Master gaffer: Is intensity enabled? → Use master value
4. If not found anywhere: Use default value

### 4. Per-Attribute Inheritance

Each attribute has an independent enable flag:

```
Shot Gaffer:
  - intensity: 1.5 (enabled) ← Override
  - exposure: (disabled) ← Inherit from parent
  - color: (disabled) ← Inherit from parent

Sequence Gaffer:
  - intensity: 1.0 (enabled)
  - exposure: 0.0 (enabled) ← Shot inherits this
  - color: (disabled) ← Inherit from parent

Master Gaffer:
  - intensity: 1.0 (enabled)
  - exposure: 0.0 (enabled)
  - color: 1,1,1 (enabled) ← Shot inherits this
```

**Result for Shot:**
- intensity: 1.5 (from Shot)
- exposure: 0.0 (from Sequence)
- color: 1,1,1 (from Master)

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     UI Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Gaffer     │  │    Light     │  │  Add Light   │      │
│  │   Manager    │  │    Editor    │  │   Dialog     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   Core API Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Gaffer     │  │  Attribute   │  │    Light     │      │
│  │   Manager    │  │  Resolver    │  │  Operations  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐                                           │
│  │    Chain     │                                           │
│  │  Operations  │                                           │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   Node Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ CTXLight     │  │ CTXLight     │  │    Node      │      │
│  │   Gaffer     │  │  Context     │  │   Factory    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   Maya Scene                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Network    │  │   Network    │  │    Maya      │      │
│  │    Nodes     │  │    Nodes     │  │   Lights     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

1. **Node Layer** (`core/nodes/`)
   - Schema-based node definitions
   - Node wrappers for high-level API
   - Node factory for creation

2. **Gaffer API** (`core/gaffer/`)
   - GafferManager: Add/remove lights, manage overrides
   - AttributeResolver: Chain walking and resolution
   - LightOperations: Apply/sync operations
   - ChainOperations: Build and validate chains

3. **UI Layer** (`ui/`)
   - GafferManagerDialog: Main management interface
   - LightEditorPanel: Detailed attribute editing
   - AddLightDialog: Add Maya lights to gaffers

---

## Quick Start

### 1. Open Gaffer Manager

```python
from ui.gaffer_manager_dialog import GafferManagerDialog

dialog = GafferManagerDialog()
dialog.show()
```

Or from Main Window: **Tools → Gaffer Manager**

### 2. Create a Gaffer Chain

```python
from core.gaffer.chain_ops import ChainOperations

# Create Master → Sequence → Shot chain
chain = ChainOperations.build_gaffer_chain(
    master_name='Master',
    sequence_name='sq0070',
    shot_name='SH0010'
)

master = chain['master']
sequence = chain['sequence']
shot = chain['shot']
```

### 3. Add Lights to Master

In UI: Select "Master" gaffer → Click "+ Add Light" → Select lights → Add

Or programmatically:
```python
from core.gaffer.manager import GafferManager

GafferManager.add_light_to_gaffer(master, 'keyLight1Shape', light_name='keyLight1')
```

### 4. Create Override in Shot

In UI: Select "Shot" gaffer → Click ">>" next to light → Edit intensity → Apply

Or programmatically:
```python
GafferManager.add_override_to_gaffer(shot, 'keyLight1', 'intensity', 1.5)
```

### 5. Apply to Scene

In UI: Click "Apply to Scene"

Or programmatically:
```python
from core.gaffer.light_ops import LightOperations

LightOperations.apply_gaffer_to_all_lights(shot)
```

---

## Related Documentation

- **[Gaffer API Reference](gaffer_api_reference.md)** - Complete API documentation
- **[Gaffer UI Guide](gaffer_ui_guide.md)** - User interface guide
- **[Gaffer Workflows](gaffer_workflows.md)** - Common workflows and examples
- **[spec/CTX_lightGaffer_spec.md](../spec/CTX_lightGaffer_spec.md)** - Technical specification
- **[spec/NODE_ARCHITECTURE.md](../spec/NODE_ARCHITECTURE.md)** - Node architecture details

---

**Next:** [Gaffer API Reference](gaffer_api_reference.md)

