# Manual Node Creation and Wiring Guide

**Version:** 1.1
**Date:** 2026-03-06
**Purpose:** Guide for manually creating and wiring CTX nodes

---

## Overview

This guide shows how to manually create and wire CTX nodes using the schema-based system.

**Key Principles:**
- ✅ Create nodes individually
- ✅ Wire connections manually
- ✅ Full control over node hierarchy
- ✅ Compatible with legacy Context Manager

---

## Node Types

### All Schema-Based Nodes (use `core.nodes.wrappers` for all new code)

| Node Type | Schema | Wrapper | Purpose |
|-----------|--------|---------|---------|
| CTX_Manager | `CTXManagerSchema` | `CTXManagerNode` | Root manager (singleton) |
| CTX_Sequence | `CTXSequenceSchema` | `CTXSequenceNode` | Sequence container |
| CTX_Shot | `CTXShotSchema` | `CTXShotNode` | Shot context |
| CTX_Asset | `CTXAssetSchema` | `CTXAssetNode` | Asset metadata |
| CTX_LightGaffer | `CTXLightGafferSchema` | `CTXLightGafferNode` | Light gaffer |
| CTX_LightContext | `CTXLightContextSchema` | `CTXLightContextNode` | Light attribute storage |

**Correct import:**

```python
from core.nodes.wrappers import (
    CTXManagerNode, CTXSequenceNode, CTXShotNode, CTXAssetNode,
    CTXLightGafferNode, CTXLightContextNode
)
```

> **DO NOT** import from `core.custom_nodes` — it is deprecated and kept only for backward compatibility with existing Maya scenes.

---

## Example 1: Create Sequence Manually

```python
from core.nodes.wrappers import CTXSequenceNode

# Create sequence node
seq = CTXSequenceNode.create(
    sequenceCode='sq0070',
    sequenceName='Sequence 70',
    frameStart=1001,
    frameEnd=1200
)

print("Created sequence:", seq.node_name)
# Output: Created sequence: CTX_Sequence1
```

---

## Example 2: Create Gaffer Manually

```python
from core.nodes.wrappers import CTXLightGafferNode

# Create master gaffer
master = CTXLightGafferNode.create(
    gafferName='Master',
    gafferType='master',
    scopeCode='',
    enabled=True
)

# Create sequence gaffer
seq_gaffer = CTXLightGafferNode.create(
    gafferName='sq0070',
    gafferType='sequence',
    scopeCode='sq0070',
    enabled=True
)

# Create shot gaffer
shot_gaffer = CTXLightGafferNode.create(
    gafferName='SH0010',
    gafferType='shot',
    scopeCode='SH0010',
    enabled=True
)

print("Created gaffers:")
print("  Master:", master.node_name)
print("  Sequence:", seq_gaffer.node_name)
print("  Shot:", shot_gaffer.node_name)
```

---

## Example 3: Wire Gaffer Chain Manually

```python
from core.nodes.wrappers import CTXLightGafferNode

# Assume gaffers already created (from Example 2)
master = CTXLightGafferNode('CTX_LightGaffer_Master')
seq_gaffer = CTXLightGafferNode('CTX_LightGaffer_sq0070')
shot_gaffer = CTXLightGafferNode('CTX_LightGaffer_SH0010')

# Wire inheritance chain: Shot → Sequence → Master
shot_gaffer.set_parent_gaffer(seq_gaffer)
seq_gaffer.set_parent_gaffer(master)

print("Gaffer chain wired:")
print("  Shot parent:", shot_gaffer.get_parent_gaffer().node_name)
print("  Seq parent:", seq_gaffer.get_parent_gaffer().node_name)
# Output:
#   Shot parent: CTX_LightGaffer_sq0070
#   Seq parent: CTX_LightGaffer_Master
```

---

## Example 4: Wire Sequence to Manager

```python
from core.nodes.wrappers import CTXManagerNode, CTXSequenceNode

# Get existing manager (DO NOT create new one)
manager = CTXManagerNode.get_manager()
if not manager:
    raise RuntimeError("No CTX_Manager found in scene")

# Create sequence
seq = CTXSequenceNode.create(
    sequenceCode='sq0070',
    sequenceName='Sequence 70'
)

# Wire to manager
seq.set_parent_manager(manager)

print("Sequence wired to manager")
print("  Manager:", manager.node_name)
print("  Sequence:", seq.node_name)
```

---

## Example 5: Wire Gaffer to Sequence

```python
from core.nodes.wrappers import CTXSequenceNode, CTXLightGafferNode

# Assume sequence and gaffer already created
seq = CTXSequenceNode('CTX_Sequence_sq0070')
seq_gaffer = CTXLightGafferNode('CTX_LightGaffer_sq0070')

# Wire gaffer to sequence
seq.set_gaffer(seq_gaffer)

print("Gaffer wired to sequence")
print("  Sequence:", seq.node_name)
print("  Gaffer:", seq.get_gaffer())
```

---

## Example 6: Complete Hierarchy Setup

```python
from core.nodes.wrappers import CTXManagerNode, CTXSequenceNode, CTXLightGafferNode

# Step 1: Get manager (existing)
manager = CTXManagerNode.get_manager()

# Step 2: Create sequence
seq = CTXSequenceNode.create(
    sequenceCode='sq0070',
    sequenceName='Sequence 70',
    frameStart=1001,
    frameEnd=1200
)

# Step 3: Create gaffers
master = CTXLightGafferNode.create(
    gafferName='Master',
    gafferType='master',
    scopeCode=''
)

seq_gaffer = CTXLightGafferNode.create(
    gafferName='sq0070',
    gafferType='sequence',
    scopeCode='sq0070'
)

# Step 4: Wire everything together
seq.set_parent_manager(manager)      # Sequence → Manager
seq.set_gaffer(seq_gaffer)           # Gaffer → Sequence
seq_gaffer.set_parent_gaffer(master) # Seq Gaffer → Master Gaffer

print("Complete hierarchy created:")
print("  Manager:", manager.node_name)
print("  Sequence:", seq.node_name)
print("  Seq Gaffer:", seq_gaffer.node_name)
print("  Master Gaffer:", master.node_name)
```

---

## Example 7: Find Existing Nodes

```python
from core.nodes.wrappers import CTXSequenceNode, CTXLightGafferNode

# Find sequence by code
seq = CTXSequenceNode.find_by_code('sq0070')
if seq:
    print("Found sequence:", seq.node_name)
    print("  Code:", seq.get_sequence_code())
    print("  Name:", seq.get_sequence_name())
    print("  Frame range:", seq.get_frame_range())

# List all sequences
all_sequences = CTXSequenceNode.list_all()
print("\nAll sequences in scene:")
for seq in all_sequences:
    print("  -", seq.get_sequence_code(), ":", seq.get_sequence_name())

# List all gaffers
all_gaffers = CTXLightGafferNode.list_all()
print("\nAll gaffers in scene:")
for gaffer in all_gaffers:
    print("  -", gaffer.get_gaffer_name(), ":", gaffer.get_gaffer_type())
```

---

## Example 8: Query Connections

```python
from core.nodes.wrappers import CTXSequenceNode, CTXLightGafferNode

# Get sequence
seq = CTXSequenceNode.find_by_code('sq0070')

# Query connections
manager = seq.get_parent_manager()
gaffer = seq.get_gaffer()
shots = seq.get_shots()

print("Sequence connections:")
print("  Parent manager:", manager)
print("  Gaffer:", gaffer)
print("  Shots:", shots)

# Query gaffer chain
gaffer_node = CTXLightGafferNode(gaffer)
parent = gaffer_node.get_parent_gaffer()
chain = gaffer_node.build_chain()

print("\nGaffer chain:")
for g in chain:
    print("  -", g.get_gaffer_name())
```

---

## Important Notes

### CTX_Manager is a Singleton

❌ **DO NOT** create more than one CTX_Manager per scene
✅ **DO** use `CTXManagerNode.get_manager()` to retrieve the existing manager
✅ **DO** use `CTXManagerNode.create(...)` only when initializing a fresh scene

### All 6 Node Types Use Schema-Based Wrappers

All CTX node types (Manager, Sequence, Shot, Asset, LightGaffer, LightContext) are schema-based.
Use `core.nodes.wrappers` for all creation and wiring. `core.custom_nodes` is deprecated.

### Node Naming Convention

- **CTX_Manager**: `CTX_Manager` (singleton)
- **CTX_Sequence**: `CTX_Sequence_{sequenceCode}` (e.g., `CTX_Sequence_sq0070`)
- **CTX_Shot**: `CTX_Shot_{ep}_{seq}_{shot}` (e.g., `CTX_Shot_Ep04_sq0070_SH0170`)
- **CTX_Asset**: `CTX_Asset_{namespace}`
- **CTX_LightGaffer**: `CTX_LightGaffer_{name}` (e.g., `CTX_LightGaffer_Master`)
- **CTX_LightContext**: `CTX_LightContext_{lightName}_{gafferName}`

### Connection Pattern (Unidirectional)

All connections are **unidirectional**: `child.message → parent.attribute`.
Never create a second reverse connection.

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

Gaffer inheritance chain (for attribute resolution):
    Master CTX_LightGaffer
        ↑ parentGaffer   (SeqGaffer.message → MasterGaffer.parentGaffer)
    Sequence CTX_LightGaffer
        ↑ parentGaffer   (ShotGaffer.message → SeqGaffer.parentGaffer)
    Shot CTX_LightGaffer
```

---

## Testing Your Setup

```python
# Test script to verify manual wiring
from core.nodes.wrappers import CTXManagerNode, CTXSequenceNode, CTXLightGafferNode

def test_manual_setup():
    """Test manual node creation and wiring."""

    # Get manager
    manager = CTXManagerNode.get_manager()
    assert manager is not None, "No manager found"

    # Create sequence
    seq = CTXSequenceNode.create(
        sequenceCode='test_seq',
        sequenceName='Test Sequence'
    )
    seq.set_parent_manager(manager)

    # Create gaffers
    master = CTXLightGafferNode.create(
        gafferName='Master',
        gafferType='master'
    )

    seq_gaffer = CTXLightGafferNode.create(
        gafferName='test_seq',
        gafferType='sequence',
        scopeCode='test_seq'
    )

    # Wire gaffer chain
    seq_gaffer.set_parent_gaffer(master)
    seq.set_gaffer(seq_gaffer)

    # Verify
    assert seq.get_parent_manager() == manager.node_name
    assert seq.get_gaffer() == seq_gaffer.node_name
    assert seq_gaffer.get_parent_gaffer().node_name == master.node_name

    print("All tests passed!")

# Run test
test_manual_setup()
```

---

**Next Steps:**
1. Review this guide
2. Test manual node creation in Maya
3. Verify connections work correctly
4. Update UI to use manual creation pattern

