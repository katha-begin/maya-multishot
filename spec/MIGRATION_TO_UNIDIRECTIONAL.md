 # Migration Plan: Bidirectional → Unidirectional Connections

**Date:** 2026-02-22  
**Status:** Proposed  
**Impact:** Medium (code changes, no data loss)

---

## Overview

Migrate from bidirectional connections to unidirectional connections for cleaner, simpler code.

**Current (Bidirectional):**
```python
# Two connections per relationship
cmds.connectAttr("shot.message", "sequence.shots[0]")
cmds.connectAttr("sequence.message", "shot.parentSequence")
```

**Target (Unidirectional):**
```python
# One connection per relationship
cmds.connectAttr("shot.message", "sequence.shots[0]", nextAvailable=True)
```

---

## Phase 1: Update Schemas (Remove Redundant Connections)

### Files to Update

1. **`core/nodes/schemas/sequence.py`**
   - ✅ Keep: `shots` (INPUT MULTI) - receives from shots
   - ❌ Remove: `parentManager` (INPUT SINGLE) - redundant

2. **`core/nodes/schemas/shot.py`**
   - ✅ Keep: `assets` (INPUT MULTI) - receives from assets
   - ✅ Keep: `gaffer` (INPUT SINGLE) - receives from gaffer
   - ❌ Remove: `parentSequence` (INPUT SINGLE) - redundant
   - ❌ Remove: `manager` (INPUT SINGLE) - redundant

3. **`core/nodes/schemas/asset.py`**
   - ❌ Remove: `parentShot` (INPUT SINGLE) - redundant

4. **`core/nodes/schemas/gaffer.py`**
   - ✅ Keep: `parentGaffer` (INPUT SINGLE) - inheritance chain
   - ✅ Keep: `childGaffers` (OUTPUT MULTI) - for querying children
   - ✅ Keep: `lights` (OUTPUT MULTI) - for querying lights
   - ❌ Remove: `parentNode` (INPUT SINGLE) - redundant

5. **`core/nodes/schemas/light_context.py`**
   - ❌ Remove: `parentGaffer` (INPUT SINGLE) - redundant

---

## Phase 2: Update Wrapper Methods

### Connection Methods (Simplify)

#### **Before (Bidirectional):**

```python
# core/nodes/wrappers/shot.py
def set_parent_sequence(self, sequence):
    sequence_node = sequence.node_name if hasattr(sequence, 'node_name') else sequence
    
    # Connect: Shot.message → Sequence.shots[i]
    cmds.connectAttr(
        "{}.message".format(self.node_name),
        "{}.shots".format(sequence_node),
        nextAvailable=True
    )
    
    # Connect: Sequence.message → Shot.parentSequence
    cmds.connectAttr(
        "{}.message".format(sequence_node),
        "{}.parentSequence".format(self.node_name),
        force=True
    )
```

#### **After (Unidirectional):**

```python
# core/nodes/wrappers/shot.py
def set_parent_sequence(self, sequence):
    sequence_node = sequence.node_name if hasattr(sequence, 'node_name') else sequence
    
    # Connect: Shot.message → Sequence.shots[i]
    cmds.connectAttr(
        "{}.message".format(self.node_name),
        "{}.shots".format(sequence_node),
        nextAvailable=True
    )
```

**Files to update:**
- `core/nodes/wrappers/shot.py` - `set_parent_sequence()`, `set_manager()`, `set_gaffer()`
- `core/nodes/wrappers/sequence.py` - `set_parent_manager()`, `set_gaffer()`
- `core/nodes/wrappers/asset.py` - `set_parent_shot()`
- `core/nodes/wrappers/gaffer.py` - `set_parent_gaffer()`
- `core/nodes/wrappers/light_context.py` - `set_parent_gaffer()`

---

### Query Methods (Fix Direction)

#### **Before (Queries redundant attribute):**

```python
# core/nodes/wrappers/shot.py
def get_parent_sequence(self):
    connections = cmds.listConnections(
        "{}.parentSequence".format(self.node_name),
        source=True,
        destination=False
    ) or []
    return connections[0] if connections else None
```

#### **After (Queries .message with destination=True):**

```python
# core/nodes/wrappers/shot.py
def get_parent_sequence(self):
    connections = cmds.listConnections(
        "{}.message".format(self.node_name),
        source=False,
        destination=True,
        type='network'
    ) or []
    
    # Filter for CTX_Sequence nodes
    for conn in connections:
        if cmds.attributeQuery('ctx_node_type', node=conn, exists=True):
            node_type = cmds.getAttr('{}.ctx_node_type'.format(conn))
            if node_type == 'CTX_Sequence':
                return conn
    return None
```

**Files to update:**
- `core/nodes/wrappers/shot.py` - `get_parent_sequence()`, `get_manager()`
- `core/nodes/wrappers/sequence.py` - `get_parent_manager()`
- `core/nodes/wrappers/asset.py` - `get_parent_shot()`
- `core/nodes/wrappers/gaffer.py` - `get_parent_node()`
- `core/nodes/wrappers/light_context.py` - `get_parent_gaffer()`

---

## Phase 3: Update Tests

### Files to Update

1. **`tests/test_full_chain_connection.py`**
   - Update connection verification logic
   - Remove checks for redundant attributes

2. **`tests/node_creation_flow/test_node_creation_from_json.py`**
   - Already uses correct pattern (one method per relationship)
   - No changes needed

3. **`tests/test_node_schemas.py`**
   - Update schema validation tests
   - Remove tests for redundant attributes

---

## Phase 4: Update Documentation

### Files to Update

1. **`core/nodes/AGENTS.md`**
   - Update "Message Attribute System" section
   - Update "Connection Patterns" section
   - Remove references to bidirectional connections

2. **`AGENTS.md`**
   - Update "Data Flow Architecture" section
   - Update "Message Attributes" section

3. **`tests/node_creation_flow/CONNECTION_PATTERNS.md`**
   - Rewrite to reflect unidirectional pattern
   - Update all examples

4. **`spec/spec.md`**
   - Update "Message Attribute Linking Strategy" section
   - Remove references to bidirectional connections

---

## Phase 5: Backward Compatibility

### Handling Existing Scenes

**Option 1: Migration Script** (Recommended)

Create `tools/migrate_connections.py` to:
1. Find all CTX nodes in scene
2. Remove redundant connections (e.g., `sequence.message → shot.parentSequence`)
3. Keep primary connections (e.g., `shot.message → sequence.shots[0]`)

**Option 2: Graceful Degradation**

Update query methods to check BOTH patterns:
```python
def get_parent_sequence(self):
    # Try new pattern first
    parent = self._get_parent_via_message()
    if parent:
        return parent
    
    # Fall back to old pattern
    return self._get_parent_via_attribute()
```

---

## Rollout Plan

1. **Week 1:** Update schemas and wrapper methods
2. **Week 2:** Update tests and verify all pass
3. **Week 3:** Update documentation
4. **Week 4:** Create migration script for existing scenes
5. **Week 5:** Deploy to production

---

**Maintainer:** CTX Pipeline Team  
**Last Updated:** 2026-02-22

