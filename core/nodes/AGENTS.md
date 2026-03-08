# CTX Node System - Comprehensive Reference

**Version:** 1.0  
**Last Updated:** 2026-02-22  
**Purpose:** Detailed technical reference for all CTX node types in the schema-based node system  

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Data Flow Architecture](#data-flow-architecture)
3. [CTX_Manager Node](#ctx_manager-node)
4. [CTX_Sequence Node](#ctx_sequence-node)
5. [CTX_Shot Node](#ctx_shot-node)
6. [CTX_Asset Node](#ctx_asset-node)
7. [CTX_LightGaffer Node](#ctx_lightgaffer-node)
8. [CTX_LightContext Node](#ctx_lightcontext-node)
9. [Connection Patterns](#connection-patterns)
10. [Common Workflows](#common-workflows)

---

## System Overview

### Schema-Based Architecture

The CTX node system uses a **three-layer architecture**:

```
NodeSchema (Definition)
    ↓
NodeFactory (Creation) → Maya Network Node
    ↓
NodeWrapper (High-level API)
```

**Key Concepts:**

- **Schema** - Declarative definition of node structure (ATTRIBUTES + CONNECTIONS)
- **Factory** - Creates Maya nodes from schema definitions
- **Wrapper** - Provides high-level Python API for node operations
- **Message Attributes** - Maya's connection system for node relationships

### Node Hierarchy

**Context Hierarchy (Parent-Child Ownership):**
```
CTX_Manager (singleton)
    ↓ sequences (multi)
CTX_Sequence
    ↓ shots (multi)
CTX_Shot
    ↓ assets (multi)
CTX_Asset
```

**Light Gaffer Hierarchy (Ownership + Inheritance):**
```
CTX_Sequence
    ↓ gaffer (single) - Sequence owns its gaffer
CTX_LightGaffer (Sequence-level)
    ↓ lights (multi)
CTX_LightContext (per-light attribute storage)

CTX_Shot
    ↓ gaffer (single) - Shot owns its gaffer
CTX_LightGaffer (Shot-level)
    ↓ parentGaffer (single) - Inherits from Sequence gaffer
CTX_LightGaffer (Sequence-level)
    ↓ parentGaffer (single) - Inherits from Master gaffer
CTX_LightGaffer (Master-level)
```

### Message Attribute System

**Connection Pattern (Unidirectional):**
```python
# Source node has .message attribute (OUTPUT)
# Target node has custom message attribute (INPUT)
# Connection: source.message → target.customAttr (ONE direction only)

cmds.connectAttr("source.message", "target.customAttr")
```

**Key Principle:** Use **unidirectional connections** (child → parent) for hierarchy.

**Why Unidirectional?**
- ✅ Single source of truth (parent owns children)
- ✅ Simpler code (one connection, not two)
- ✅ No "already connected" errors
- ✅ Better performance (half the connections)
- ✅ Can query in BOTH directions from ONE connection using `listConnections()`

**Direction Types:**
- **INPUT** - Receives connections (e.g., `shots[0]`, `gaffer`, `sequences[0]`)
- **OUTPUT** - Sends connections (e.g., `.message`, `lights[0]`, `childGaffers[0]`)

**Multi vs Single:**
- **MULTI** - Array attribute, accepts multiple connections (e.g., `shots[0]`, `shots[1]`, ...)
- **SINGLE** - Single connection only (e.g., `gaffer`)

**Querying Connections:**
```python
# Query FROM PARENT (get children)
children = cmds.listConnections("parent.children", source=True, destination=False)

# Query FROM CHILD (get parent)
parent = cmds.listConnections("child.message", source=False, destination=True)
```

**Note:** Maya's `listConnections()` can traverse in BOTH directions from a SINGLE connection. The `source`/`destination` flags control which direction to traverse, NOT which connections exist.

### Gaffer Architecture: Ownership + Inheritance

The gaffer system uses a **dual-connection pattern** that combines direct ownership with inheritance:

**Direct Ownership (Parent-Child):**
- Sequence owns its gaffer via `Sequence.gaffer` connection
- Shot owns its gaffer via `Shot.gaffer` connection (NEW!)
- Similar to how Sequence owns shots, Shot owns assets

**Inheritance Chain (Hierarchical):**
- Shot gaffer inherits from Sequence gaffer via `parentGaffer` connection
- Sequence gaffer inherits from Master gaffer via `parentGaffer` connection
- Attribute resolution walks up the chain checking enabled flags

**Benefits of This Design:**
- ✅ **Symmetry** - Both Sequence and Shot directly own their gaffers
- ✅ **Clarity** - Clear parent-child relationship (like Sequence→Shots, Shot→Assets)
- ✅ **Direct Access** - Can query `shot.get_gaffer()` directly
- ✅ **Consistency** - Follows same pattern as other parent-child relationships
- ✅ **Inheritance Still Works** - Shot gaffer's `parentGaffer` still points to Sequence gaffer for attribute resolution
- ✅ **Flexible Chains** - Not hardcoded by type (Master/Sequence/Shot), supports custom chains

---

## Data Flow Architecture

### Context Hierarchy Data Flow

```
┌─────────────────┐
│  CTX_Manager    │ (Singleton)
│  - config_path  │
│  - project_root │
└────────┬────────┘
         │ sequences[i] (INPUT MULTI)
         ↓
┌─────────────────┐
│ CTX_Sequence    │
│ - sequenceCode  │
│ - frameStart    │
└────────┬────────┘
         │ shots[i] (INPUT MULTI)
         ↓
┌─────────────────┐
│   CTX_Shot      │
│ - ep_code       │
│ - seq_code      │
│ - shot_code     │
└────────┬────────┘
         │ assets[i] (INPUT MULTI)
         ↓
┌─────────────────┐
│  CTX_Asset      │
│ - asset_type    │
│ - asset_name    │
│ - file_path     │
└─────────────────┘
```

### Light Gaffer Data Flow

**Sequence-Level Gaffer (Ownership):**
```
┌─────────────────┐
│ CTX_Sequence    │
└────────┬────────┘
         │ gaffer (INPUT SINGLE)
         ↓
┌─────────────────┐
│ CTX_LightGaffer │ (Sequence-level)
│ - gafferName    │
│ - gafferType    │
└────────┬────────┘
         │ lights[i] (OUTPUT MULTI)
         ↓
┌─────────────────┐
│CTX_LightContext │ (Per-light storage)
│ - lightName     │
│ - intensity     │
│ - intensityEn.. │
└─────────────────┘
```

**Shot-Level Gaffer (Ownership + Inheritance):**
```
┌─────────────────┐
│   CTX_Shot      │
└────────┬────────┘
         │ gaffer (INPUT SINGLE)
         ↓
┌─────────────────┐
│ CTX_LightGaffer │ (Shot-level)
│ - gafferName    │
│ - gafferType    │
└────────┬────────┘
         │ parentGaffer (INPUT SINGLE)
         │ lights[i] (OUTPUT MULTI)
         ↓
┌─────────────────┐
│ CTX_LightGaffer │ (Sequence-level - parent)
│ - gafferName    │
│ - gafferType    │
└─────────────────┘
```

### Gaffer Inheritance Chain

```
Master Gaffer (gafferType='master')
    ↓ childGaffers[0] (OUTPUT MULTI)
    ↑ parentGaffer (INPUT) - None (root)
Sequence Gaffer (gafferType='sequence')
    ↓ childGaffers[0] (OUTPUT MULTI)
    ↑ parentGaffer (INPUT) - Points to Master
Shot Gaffer (gafferType='shot')
    ↓ childGaffers[0] (OUTPUT MULTI)
    ↑ parentGaffer (INPUT) - Points to Sequence
```

**Attribute Resolution:**
1. Query light attribute (e.g., intensity)
2. Check Shot gaffer → enabled? Use value : Continue
3. Check Sequence gaffer → enabled? Use value : Continue
4. Check Master gaffer → enabled? Use value : Continue
5. Use light's current value (fallback)

---

## CTX_Manager Node

### 1. Schema Definition

**File:** `core/nodes/schemas/manager.py`

```python
class CTXManagerSchema(NodeSchema):
    NODE_TYPE = "network"
    NODE_PREFIX = "CTX_Manager"
    CATEGORY = "Context"
    DESCRIPTION = "Root context manager (singleton)"

    ATTRIBUTES = {
        'ctx_type': {
            'type': 'string',
            'default': 'CTX_Manager',
            'description': 'CTX node type identifier'
        },
        'config_path': {
            'type': 'string',
            'default': '',
            'description': 'Path to project configuration file'
        },
        'project_root': {
            'type': 'string',
            'default': '',
            'description': 'Project root directory'
        },
        'active_shot_id': {
            'type': 'string',
            'default': '',
            'description': 'ID of currently active shot (e.g., "Ep04_sq0070_SH0170")'
        },
    }

    CONNECTIONS = {
        'sequences': {
            'type': 'message',
            'multi': True,
            'direction': 'input',
            'accepts': ['CTX_Sequence'],
            'description': 'Input connections from CTX_Sequence nodes (Sequence.message → Manager.sequences[i])'
        },
        'shots': {
            'type': 'message',
            'multi': True,
            'direction': 'input',
            'accepts': ['CTX_Shot'],
            'description': 'Input connections from CTX_Shot nodes (Shot.message → Manager.shots[i]) - backward compatibility'
        },
    }
```

### 2. Purpose

**What Problem Does This Solve?**

The CTX_Manager is the **root node** of the entire context system. It provides:
- **Global project configuration** - Stores config file path and project root
- **Centralized shot tracking** - Tracks which shot is currently active
- **Hierarchy root** - All sequences and shots connect to this node
- **Singleton pattern** - Only one manager allowed per scene

**Where Does It Fit in the Hierarchy?**

```
CTX_Manager (ROOT - singleton)
    ↓ sequences[0], sequences[1], ...
    ↓ shots[0], shots[1], ... (backward compatibility)
```

**When Should It Be Used?**

- **Scene initialization** - Create manager first before any other CTX nodes
- **Project setup** - Store project-wide configuration
- **Shot switching** - Update `active_shot_id` when switching shots
- **Hierarchy queries** - Query all sequences/shots in the scene

### 3. Wrapper API

**File:** `core/nodes/wrappers/manager.py`

**Key Methods:**

```python
class CTXManagerNode(NodeWrapper):
    SCHEMA = CTXManagerSchema

    # Creation (singleton)
    @classmethod
    def create(cls, **kwargs):
        """Create manager node (singleton check).

        Raises:
            RuntimeError: If manager already exists
        """

    # Manual wiring
    def add_sequence(self, sequence):
        """Wire a sequence to this manager.

        Connects:
            Sequence.message → Manager.sequences[i]
            Manager.message → Sequence.parentManager
        """

    def add_shot(self, shot):
        """Wire a shot to this manager (backward compatibility).

        Connects:
            Shot.message → Manager.shots[i]
            Manager.message → Shot.manager
        """

    # Query methods
    def get_sequences(self):
        """Get all connected sequences.

        Returns:
            list: List of CTXSequenceNode instances
        """

    def get_shots(self):
        """Get all connected shots.

        Returns:
            list: List of CTXShotNode instances
        """

    # Discovery
    @staticmethod
    def get_manager():
        """Get the manager node (singleton getter).

        Returns:
            CTXManagerNode or None: Manager instance if exists
        """
```

**Usage Examples:**

```python
from core.nodes.wrappers import CTXManagerNode, CTXSequenceNode

# Create manager (singleton)
manager = CTXManagerNode.create(
    config_path='/path/to/config.json',
    project_root='/path/to/project'
)

# Create sequence
seq = CTXSequenceNode.create(sequenceCode='sq0070')

# Wire sequence to manager
manager.add_sequence(seq)

# Query sequences
sequences = manager.get_sequences()
print("Sequences:", [s.get_sequence_code() for s in sequences])

# Get existing manager
existing_manager = CTXManagerNode.get_manager()
```

### 4. Node Behavior

**Creation:**
- ✅ Enforces singleton pattern (only one manager per scene)
- ✅ Creates Maya network node with `CTX_Manager` prefix
- ✅ Adds `sequences` and `shots` message attributes (multi)
- ✅ Sets default attribute values from schema

**Connection:**
- When sequence connects → Unidirectional connection (child → parent)
  - `Sequence.message → Manager.sequences[i]`
- When shot connects → Unidirectional connection (backward compatibility)
  - `Shot.message → Manager.shots[i]`

**Querying:**
- Get sequences: `cmds.listConnections("manager.sequences", source=True, destination=False)`
- Get manager from sequence: `cmds.listConnections("sequence.message", source=False, destination=True)`

**Attribute Changes:**
- `config_path` change → No automatic side effects (user must reload config)
- `project_root` change → No automatic side effects (user must update paths)
- `active_shot_id` change → No automatic side effects (user must switch shot manually)

**Deletion:**
- ⚠️ Deleting manager breaks all sequence/shot connections
- ⚠️ Orphaned sequences/shots remain in scene but lose hierarchy
- ⚠️ Recommended: Delete all sequences/shots before deleting manager

### 5. Node Actions

**Operations Performed ON This Node:**
- `create()` - Create new manager (singleton check)
- `add_sequence()` - Wire sequence to manager
- `add_shot()` - Wire shot to manager
- `get_sequences()` - Query connected sequences
- `get_shots()` - Query connected shots
- `set_attribute()` - Update config_path, project_root, active_shot_id

**Operations This Node Performs ON Other Nodes:**
- None - Manager is passive, does not modify other nodes

**Side Effects:**
- Creating manager → Enables sequence/shot creation
- Deleting manager → Orphans all sequences/shots

**State Changes:**
- `active_shot_id` → Tracks current shot (for UI updates)

### 6. Node UI Integration

**Context Manager UI** (`ui/main_window.py`):
- **Shot List** - Displays all shots connected to manager
- **Active Shot Indicator** - Highlights shot matching `active_shot_id`
- **Switch Shot Button** - Updates `active_shot_id` attribute
- **Project Settings** - Edits `config_path` and `project_root`

**UI Actions → Node Operations:**
- User clicks "Switch Shot" → Updates `manager.active_shot_id`
- User edits project settings → Updates `manager.config_path`, `manager.project_root`

**Node Changes → UI Updates:**
- `active_shot_id` changes → UI highlights new active shot
- New sequence connected → UI refreshes sequence list
- New shot connected → UI refreshes shot list

### 7. Node Limitations

**Known Constraints:**
- ✅ **Singleton only** - Only one manager per scene (enforced)
- ⚠️ **No automatic config reload** - Changing `config_path` requires manual reload
- ⚠️ **No cascading delete** - Deleting manager orphans sequences/shots
- ⚠️ **No validation** - Does not validate `config_path` or `project_root` exist

**Performance Considerations:**
- ✅ Lightweight - Manager has minimal overhead
- ✅ Fast queries - `get_sequences()` and `get_shots()` use Maya's connection queries

**Edge Cases:**
- Creating manager when one exists → Raises RuntimeError ✅
- Deleting manager → Orphans all sequences/shots ⚠️
- Invalid `config_path` → No error, but config won't load ⚠️

**Future Improvements:**
- 🔲 Auto-reload config when `config_path` changes
- 🔲 Cascading delete (delete sequences/shots when manager deleted)
- 🔲 Path validation (check if `config_path` and `project_root` exist)
- 🔲 Event callbacks (notify UI when attributes change)

**Development Status:**
- ✅ Schema complete
- ✅ Wrapper complete
- ✅ Manual wiring complete
- ✅ Maya menu integration complete
- 🚧 UI integration (Context Manager uses legacy nodes)
- ⏳ Event system (future)

---

## CTX_Sequence Node

### 1. Schema Definition

**File:** `core/nodes/schemas/sequence.py`

```python
class CTXSequenceSchema(NodeSchema):
    NODE_TYPE = "network"
    NODE_PREFIX = "CTX_Sequence"
    CATEGORY = "Context"
    DESCRIPTION = "Sequence container with gaffer connection"

    ATTRIBUTES = {
        'ctx_node_type': {
            'type': 'string',
            'default': 'CTX_Sequence',
            'description': 'CTX node type identifier'
        },
        'sequenceCode': {
            'type': 'string',
            'default': '',
            'description': 'Sequence code (e.g., "sq0070")'
        },
        'sequenceName': {
            'type': 'string',
            'default': '',
            'description': 'Human-readable sequence name'
        },
        'frameStart': {
            'type': 'int',
            'default': 1001,
            'description': 'Sequence start frame'
        },
        'frameEnd': {
            'type': 'int',
            'default': 2000,
            'description': 'Sequence end frame'
        },
        'notes': {
            'type': 'string',
            'default': '',
            'description': 'User notes about this sequence'
        },
    }

    CONNECTIONS = {
        'parentManager': {
            'type': 'message',
            'multi': False,
            'direction': 'input',
            'accepts': ['CTX_Manager'],
            'description': 'Input connection from CTX_Manager'
        },
        'shots': {
            'type': 'message',
            'multi': True,
            'direction': 'input',
            'accepts': ['CTX_Shot'],
            'description': 'Input connections from CTX_Shot nodes'
        },
        'gaffer': {
            'type': 'message',
            'multi': False,
            'direction': 'input',
            'accepts': ['CTX_LightGaffer'],
            'description': 'Input connection from CTX_LightGaffer'
        },
    }
```

### 2. Purpose

**What Problem Does This Solve?**

The CTX_Sequence node provides **sequence-level organization** for shots. It:
- **Groups shots** - Organizes shots within a sequence (e.g., sq0070 contains SH0010, SH0020, ...)
- **Sequence metadata** - Stores sequence code, name, frame range
- **Gaffer connection** - Owns a sequence-level light gaffer for sequence-wide lighting
- **Hierarchy bridge** - Connects manager to shots

**Where Does It Fit in the Hierarchy?**

```
CTX_Manager
    ↓ sequences[i]
CTX_Sequence (MIDDLE LAYER)
    ↓ shots[i]
CTX_Shot
    ↓ gaffer (single)
CTX_LightGaffer (Sequence-level)
```

**When Should It Be Used?**

- **Sequence organization** - Group shots by sequence
- **Sequence-level lighting** - Apply lighting adjustments to all shots in sequence
- **Frame range management** - Define sequence-wide frame range
- **Batch operations** - Perform operations on all shots in sequence

### 3. Wrapper API

**File:** `core/nodes/wrappers/sequence.py`

**Key Methods:**

```python
class CTXSequenceNode(NodeWrapper):
    SCHEMA = CTXSequenceSchema

    # Attribute getters
    def get_sequence_code(self):
        """Get sequence code (e.g., 'sq0070')."""

    def get_sequence_name(self):
        """Get human-readable sequence name."""

    def get_frame_range(self):
        """Get frame range.

        Returns:
            tuple: (start_frame, end_frame)
        """

    # Manual wiring
    def set_parent_manager(self, manager):
        """Connect to parent manager.

        Connects:
            Sequence.message → Manager.sequences[i]
        """

    def set_gaffer(self, gaffer):
        """Connect to gaffer.

        Connects:
            Gaffer.message → Sequence.gaffer
        """

    def add_shot(self, shot):
        """Add shot to this sequence.

        Connects:
            Shot.message → Sequence.shots[i]
        """

    # Query methods
    def get_parent_manager(self):
        """Get parent manager.

        Returns:
            CTXManagerNode or None
        """

    def get_gaffer(self):
        """Get connected gaffer.

        Returns:
            CTXLightGafferNode or None
        """

    def get_shots(self):
        """Get all connected shots.

        Returns:
            list: List of CTXShotNode instances
        """

    # Discovery
    @staticmethod
    def find_by_code(sequence_code):
        """Find sequence by code.

        Returns:
            CTXSequenceNode or None
        """

    @staticmethod
    def list_all():
        """List all sequences in scene.

        Returns:
            list: List of CTXSequenceNode instances
        """
```

**Usage Examples:**

```python
from core.nodes.wrappers import CTXManagerNode, CTXSequenceNode, CTXShotNode, CTXLightGafferNode

# Create sequence
seq = CTXSequenceNode.create(
    sequenceCode='sq0070',
    sequenceName='Sequence 70',
    frameStart=1001,
    frameEnd=1200
)

# Wire to manager
manager = CTXManagerNode.get_manager()
seq.set_parent_manager(manager)

# Create sequence-level gaffer
gaffer = CTXLightGafferNode.create(
    gafferName='sq0070',
    gafferType='sequence'
)
seq.set_gaffer(gaffer)

# Add shots
shot1 = CTXShotNode.create(shot_code='SH0010')
shot2 = CTXShotNode.create(shot_code='SH0020')
seq.add_shot(shot1)
seq.add_shot(shot2)

# Query
shots = seq.get_shots()
print("Shots:", [s.get_attribute('shot_code') for s in shots])
```

### 4. Node Behavior

**Creation:**
- ✅ Creates Maya network node with `CTX_Sequence` prefix
- ✅ Adds `parentManager`, `shots`, `gaffer` message attributes
- ✅ Sets default frame range (1001-2000)
- ✅ No automatic connections (manual wiring required)

**Connection:**
- When manager connects → Unidirectional connection (child → parent)
  - `Sequence.message → Manager.sequences[i]`
- When shot connects → Unidirectional connection (child → parent)
  - `Shot.message → Sequence.shots[i]`
- When gaffer connects → Unidirectional connection (child → parent)
  - `Gaffer.message → Sequence.gaffer`

**Querying:**
- Get shots: `cmds.listConnections("sequence.shots", source=True, destination=False)`
- Get parent manager: `cmds.listConnections("sequence.message", source=False, destination=True)`
- Get gaffer: `cmds.listConnections("sequence.gaffer", source=True, destination=False)`

**Attribute Changes:**
- `sequenceCode` change → No automatic side effects
- `frameStart`/`frameEnd` change → No automatic propagation to shots
- `notes` change → No side effects

**Deletion:**
- ⚠️ Deleting sequence orphans all connected shots
- ⚠️ Deleting sequence orphans connected gaffer
- ⚠️ Recommended: Delete shots and gaffer before deleting sequence

### 5. Node Actions

**Operations Performed ON This Node:**
- `create()` - Create new sequence
- `set_parent_manager()` - Wire to manager
- `set_gaffer()` - Wire to gaffer
- `add_shot()` - Wire shot to sequence
- `get_shots()` - Query connected shots
- `get_gaffer()` - Query connected gaffer

**Operations This Node Performs ON Other Nodes:**
- None - Sequence is passive, does not modify other nodes

**Side Effects:**
- Creating sequence → Enables shot creation for this sequence
- Deleting sequence → Orphans all shots and gaffer

**State Changes:**
- No internal state changes (all data stored in attributes)

### 6. Node UI Integration

**Context Manager UI** (`ui/main_window.py`):
- **Sequence List** - Displays all sequences (if implemented)
- **Shot List** - Groups shots by sequence
- **Gaffer Manager** - Shows sequence-level gaffers

**Gaffer Manager UI** (`ui/gaffer_manager_dialog.py`):
- **Sequence Gaffer Tab** - Shows gaffers connected to sequences
- **Create Sequence Gaffer** - Creates gaffer and wires to sequence

**UI Actions → Node Operations:**
- User creates sequence → Calls `CTXSequenceNode.create()`
- User adds shot to sequence → Calls `sequence.add_shot(shot)`
- User creates sequence gaffer → Creates gaffer and calls `sequence.set_gaffer(gaffer)`

**Node Changes → UI Updates:**
- New shot connected → UI refreshes shot list
- Gaffer connected → UI shows gaffer in Gaffer Manager

### 7. Node Limitations

**Known Constraints:**
- ⚠️ **No automatic frame range propagation** - Changing sequence frame range does not update shots
- ⚠️ **No cascading delete** - Deleting sequence orphans shots and gaffer
- ⚠️ **No validation** - Does not validate sequenceCode format

**Performance Considerations:**
- ✅ Lightweight - Minimal overhead
- ✅ Fast queries - Uses Maya's connection queries

**Edge Cases:**
- Sequence without manager → Valid but not recommended ⚠️
- Sequence without gaffer → Valid (gaffer is optional) ✅
- Sequence without shots → Valid (empty sequence) ✅
- Duplicate sequenceCode → No validation, user must ensure uniqueness ⚠️

**Future Improvements:**
- 🔲 Auto-propagate frame range to shots
- 🔲 Cascading delete (delete shots when sequence deleted)
- 🔲 Validate sequenceCode format
- 🔲 Prevent duplicate sequenceCode
- 🔲 Auto-create gaffer when sequence created

**Development Status:**
- ✅ Schema complete
- ✅ Wrapper complete
- ✅ Manual wiring complete
- ✅ Maya menu integration complete
- 🚧 UI integration (Context Manager uses legacy nodes)
- ⏳ Frame range propagation (future)

---

## CTX_Shot Node

### 1. Schema Definition

**File:** `core/nodes/schemas/shot.py`

```python
class CTXShotSchema(NodeSchema):
    NODE_TYPE = "network"
    NODE_PREFIX = "CTX_Shot"
    CATEGORY = "Context"
    DESCRIPTION = "Shot context with asset management"

    ATTRIBUTES = {
        'ctx_type': {'type': 'string', 'default': 'CTX_Shot'},
        'ep_code': {'type': 'string', 'default': '', 'description': 'Episode code (e.g., "Ep04")'},
        'seq_code': {'type': 'string', 'default': '', 'description': 'Sequence code (e.g., "sq0070")'},
        'shot_code': {'type': 'string', 'default': '', 'description': 'Shot code (e.g., "SH0170")'},
        'display_layer_name': {'type': 'string', 'default': '', 'description': 'Associated display layer'},
        'is_active': {'type': 'bool', 'default': False, 'description': 'Currently active shot'},
        'start_frame': {'type': 'int', 'default': 1001},
        'end_frame': {'type': 'int', 'default': 1100},
        'frame_offset': {'type': 'int', 'default': 0},
        'fps': {'type': 'float', 'default': 24.0},
        'handles': {'type': 'int', 'default': 10},
    }

    CONNECTIONS = {
        # Hierarchy connections
        'parentSequence': {
            'type': 'message', 'multi': False, 'direction': 'input',
            'accepts': ['CTX_Sequence'],
            'description': 'Input from CTX_Sequence (parent ownership)'
        },
        'manager': {
            'type': 'message', 'multi': False, 'direction': 'input',
            'accepts': ['CTX_Manager'],
            'description': 'Input from CTX_Manager (backward compatibility)'
        },
        'assets': {
            'type': 'message', 'multi': True, 'direction': 'input',
            'accepts': ['CTX_Asset'],
            'description': 'Input from CTX_Asset nodes (child ownership)'
        },

        # Gaffer connection (NEW - Shot now owns its gaffer)
        'gaffer': {
            'type': 'message', 'multi': False, 'direction': 'input',
            'accepts': ['CTX_LightGaffer'],
            'description': 'Input from CTX_LightGaffer (shot-level gaffer ownership)'
        },

        # Display layer connection
        'display_layer_link': {
            'type': 'message', 'multi': False, 'direction': 'output',
            'description': 'Output to Maya display layer'
        },
    }
```

### 2. Purpose

**What Problem Does This Solve?**

The CTX_Shot node stores **shot-specific context** and manages assets for that shot. It:
- **Shot identification** - Stores ep/seq/shot codes for unique identification
- **Frame range management** - Defines shot timing (start, end, offset, fps, handles)
- **Display layer control** - Links to Maya display layer for shot-specific visibility
- **Asset management** - Connects to all assets used in this shot
- **Active state tracking** - Tracks if this shot is currently active

**Where Does It Fit in the Hierarchy?**

```
CTX_Sequence
    ↓ shots[i]
CTX_Shot (SHOT CONTEXT)
    ↓ assets[i]
CTX_Asset
    ↓ display_layer_link (output)
Maya Display Layer
```

**When Should It Be Used?**

- **Shot creation** - Create shot node for each shot in sequence
- **Asset loading** - Load assets and connect to shot
- **Shot switching** - Activate shot and show its display layer
- **Frame range setup** - Define shot timing for animation/rendering

### 3. Wrapper API

**Key Methods:**

```python
class CTXShotNode(NodeWrapper):
    SCHEMA = CTXShotSchema

    # Manual wiring - Hierarchy
    def set_parent_sequence(self, sequence):
        """Wire to parent sequence."""

    def set_manager(self, manager):
        """Wire to manager (backward compatibility)."""

    def add_asset(self, asset):
        """Add asset to this shot."""

    # Manual wiring - Gaffer (NEW)
    def set_gaffer(self, gaffer):
        """Wire to shot-level gaffer (direct ownership)."""

    # Query methods - Hierarchy
    def get_parent_sequence(self):
        """Get parent sequence."""

    def get_manager(self):
        """Get manager (backward compatibility)."""

    def get_assets(self):
        """Get all connected assets."""

    def get_shot_id(self):
        """Get shot ID (e.g., 'Ep04_sq0070_SH0170')."""

    # Query methods - Gaffer (NEW)
    def get_gaffer(self):
        """Get connected shot-level gaffer."""

    # Discovery
    @staticmethod
    def find_by_code(ep_code, seq_code, shot_code):
        """Find shot by codes."""

    @staticmethod
    def list_all():
        """List all shots in scene."""
```

**Usage Example:**

```python
from core.nodes.wrappers import CTXShotNode, CTXAssetNode, CTXLightGafferNode

# Create shot
shot = CTXShotNode.create(
    ep_code='Ep04',
    seq_code='sq0070',
    shot_code='SH0170',
    start_frame=1001,
    end_frame=1100
)

# Wire to sequence
seq = CTXSequenceNode.find_by_code('sq0070')
shot.set_parent_sequence(seq)

# Wire to shot-level gaffer (NEW)
shot_gaffer = CTXLightGafferNode.create(
    gafferName='SH0170',
    gafferType='shot',
    scopeCode='SH0170'
)
shot.set_gaffer(shot_gaffer)

# Add assets
asset1 = CTXAssetNode.create(asset_name='CatStompie')
shot.add_asset(asset1)

# Query
shot_id = shot.get_shot_id()  # "Ep04_sq0070_SH0170"
assets = shot.get_assets()
gaffer = shot.get_gaffer()  # Get shot-level gaffer (NEW)
```

### 4. Node Behavior

**Creation:**
- ✅ Creates Maya network node with `CTX_Shot` prefix
- ✅ Adds connection attributes (parentSequence, manager, assets, gaffer, display_layer_link)
- ✅ Sets default frame range (1001-1100)
- ✅ No automatic display layer creation (manual setup required)
- ✅ No automatic gaffer creation (manual setup required)

**Connection:**
- When sequence connects → Unidirectional connection (child → parent)
  - `Shot.message → Sequence.shots[i]`
- When asset connects → Unidirectional connection (child → parent)
  - `Asset.message → Shot.assets[i]`
- When gaffer connects → Unidirectional connection (child → parent)
  - `Gaffer.message → Shot.gaffer`
- When display layer connects → One-way output connection

**Querying:**
- Get assets: `cmds.listConnections("shot.assets", source=True, destination=False)`
- Get parent sequence: `cmds.listConnections("shot.message", source=False, destination=True, type='network')`
- Get gaffer: `cmds.listConnections("shot.gaffer", source=True, destination=False)`

**Attribute Changes:**
- `is_active` change → Should trigger display layer visibility (not automatic)
- `start_frame`/`end_frame` change → Should update timeline (not automatic)
- `display_layer_name` change → Should update display layer link (not automatic)

**Deletion:**
- ⚠️ Deleting shot orphans all connected assets
- ⚠️ Deleting shot orphans connected gaffer (gaffer not auto-deleted)
- ⚠️ Display layer remains in scene (not auto-deleted)

### 5. Node Limitations

**Known Constraints:**
- ⚠️ **No automatic display layer creation** - User must create and link manually
- ⚠️ **No automatic gaffer creation** - User must create and link manually
- ⚠️ **No automatic timeline update** - Changing frame range does not update Maya timeline
- ⚠️ **No cascading delete** - Deleting shot orphans assets and gaffer

**Future Improvements:**
- 🔲 Auto-create display layer when shot created
- 🔲 Auto-create gaffer when shot created
- 🔲 Auto-update timeline when frame range changes
- 🔲 Cascading delete (delete assets and gaffer when shot deleted)

**Development Status:**
- ✅ Schema complete (with gaffer connection)
- ✅ Wrapper complete (with gaffer methods)
- ✅ Manual wiring complete
- ✅ Maya menu integration complete
- ✅ Gaffer ownership (NEW - direct shot.gaffer connection)
- 🚧 Display layer integration (manual setup required)
- ⏳ Timeline integration (future)

---

## CTX_Asset Node

### 1. Schema Definition

**File:** `core/nodes/schemas/asset.py`

```python
class CTXAssetSchema(NodeSchema):
    NODE_TYPE = "network"
    NODE_PREFIX = "CTX_Asset"
    CATEGORY = "Context"
    DESCRIPTION = "Asset metadata and file path management"

    ATTRIBUTES = {
        'ctx_type': {'type': 'string', 'default': 'CTX_Asset'},
        'asset_type': {'type': 'string', 'default': '', 'description': 'Asset type (CHAR/PROP/CAM)'},
        'asset_name': {'type': 'string', 'default': '', 'description': 'Asset name'},
        'variant': {'type': 'string', 'default': '001', 'description': 'Asset variant'},
        'namespace': {'type': 'string', 'default': '', 'description': 'Maya namespace'},
        'file_path': {'type': 'string', 'default': '', 'description': 'Path to asset file'},
        'template': {'type': 'string', 'default': '', 'description': 'Path template with tokens (e.g., "$projRoot$project/$sceneBase/...")'},
        'extension': {'type': 'string', 'default': '', 'description': 'File extension (e.g., "abc", "ma", "mb")'},
        'version': {'type': 'string', 'default': '', 'description': 'Asset version (v003)'},
        'is_loaded': {'type': 'bool', 'default': False, 'description': 'Currently loaded'},
    }

    CONNECTIONS = {
        # NOTE: parentShot removed - redundant with unidirectional pattern
        # To query parent shot: cmds.listConnections("asset.message", source=False, destination=True, type='network')
        # Then filter for ctx_type == 'CTX_Shot'
    }
```

### 2. Purpose

**What Problem Does This Solve?**

The CTX_Asset node stores **asset-specific metadata** for a particular asset instance in a shot. It:
- **Asset identification** - Stores type, name, variant
- **File path tracking** - Stores path to asset file (.abc, .ma, etc.)
- **Version management** - Tracks asset version
- **Namespace management** - Stores Maya namespace for this instance
- **Load state tracking** - Tracks if asset is currently loaded

**Where Does It Fit in the Hierarchy?**

```
CTX_Shot
    ↓ assets[i]
CTX_Asset (LEAF NODE - no children)
```

**When Should It Be Used?**

- **Asset loading** - Create asset node when loading asset into shot
- **Version tracking** - Update version when asset is updated
- **Namespace management** - Track namespace for asset instance
- **Asset queries** - Query all assets in shot

### 3. Wrapper API

**Key Methods:**

```python
class CTXAssetNode(NodeWrapper):
    SCHEMA = CTXAssetSchema

    # Manual wiring
    def set_parent_shot(self, shot):
        """Wire to parent shot."""

    # Query methods
    def get_parent_shot(self):
        """Get parent shot."""

    def get_asset_id(self):
        """Get asset ID (e.g., 'CHAR_CatStompie_001')."""

    # Discovery
    @staticmethod
    def find_by_name(asset_name):
        """Find assets by name."""

    @staticmethod
    def list_all():
        """List all assets in scene."""
```

**Usage Example:**

```python
# Create asset
asset = CTXAssetNode.create(
    asset_type='CHAR',
    asset_name='CatStompie',
    variant='001',
    file_path='/path/to/CatStompie_v003.abc',
    version='v003',
    namespace='CatStompie_001'
)

# Wire to shot
shot = CTXShotNode.find_by_code('Ep04', 'sq0070', 'SH0170')
asset.set_parent_shot(shot)

# Mark as loaded
asset.set_attribute('is_loaded', True)

# Query
asset_id = asset.get_asset_id()  # "CHAR_CatStompie_001"
```

### 4. Node Behavior

**Creation:**
- ✅ Creates Maya network node with `CTX_Asset` prefix
- ✅ Adds parentShot connection attribute
- ✅ Sets default variant ('001')
- ✅ No automatic file loading (manual load required)

**Connection:**
- When shot connects → Unidirectional connection (child → parent)
  - `Asset.message → Shot.assets[i]`

**Querying:**
- Get parent shot: `cmds.listConnections("asset.message", source=False, destination=True, type='network')`

**Attribute Changes:**
- `file_path` change → No automatic reload (user must reload manually)
- `version` change → No automatic reload
- `is_loaded` change → No side effects (tracking only)

**Deletion:**
- ✅ Deleting asset does not affect shot
- ⚠️ Asset file remains on disk (not deleted)

### 5. Node Limitations

**Known Constraints:**
- ⚠️ **No automatic file loading** - User must load file manually
- ⚠️ **No automatic reload** - Changing file_path does not reload asset
- ⚠️ **No file validation** - Does not check if file_path exists

**Future Improvements:**
- 🔲 Auto-load file when asset created
- 🔲 Auto-reload when file_path changes
- 🔲 Validate file_path exists
- 🔲 Asset type handlers (Arnold, Redshift, USD)

**Development Status:**
- ✅ Schema complete
- ✅ Wrapper complete
- ✅ Manual wiring complete
- ✅ Maya menu integration complete
- 🚧 File loading integration (manual)
- ⏳ Asset type handlers (future)

---

## CTX_LightGaffer Node

### 1. Schema Definition

**File:** `core/nodes/schemas/gaffer.py`

```python
class CTXLightGafferSchema(NodeSchema):
    NODE_TYPE = "network"
    NODE_PREFIX = "CTX_LightGaffer"
    CATEGORY = "Lighting"
    DESCRIPTION = "Light gaffer with hierarchical inheritance"

    ATTRIBUTES = {
        'ctx_type': {'type': 'string', 'default': 'CTX_LightGaffer'},
        'gafferName': {'type': 'string', 'default': '', 'description': 'Gaffer name'},
        'gafferType': {'type': 'string', 'default': 'custom', 'description': 'Type (master/sequence/shot/custom)'},
        'scopeCode': {'type': 'string', 'default': '', 'description': 'Scope identifier'},
        'enabled': {'type': 'bool', 'default': True, 'description': 'Active state'},
        'notes': {'type': 'string', 'default': '', 'description': 'User notes'},
    }

    CONNECTIONS = {
        'parentNode': {
            'type': 'message', 'multi': False, 'direction': 'input',
            'accepts': ['CTX_Shot', 'CTX_Sequence', 'CTX_Manager'],
            'description': 'Parent context node (Gaffer.message → Sequence/Shot.gaffer)'
        },
        'parentGaffer': {
            'type': 'message', 'multi': False, 'direction': 'input',
            'accepts': ['CTX_LightGaffer'],
            'description': 'Parent gaffer in inheritance chain (ChildGaffer.message → ParentGaffer.parentGaffer)'
        },
        'childGaffers': {
            'type': 'message', 'multi': True, 'direction': 'output',
            'description': 'Child gaffers that inherit from this (ChildGaffer.message → ParentGaffer.childGaffers[i])'
        },
        'lights': {
            'type': 'message', 'multi': True, 'direction': 'output',
            'description': 'Light context nodes managed by this gaffer (LightContext.message → Gaffer.lights[i])'
        },
    }
```

### 2. Purpose

**What Problem Does This Solve?**

The CTX_LightGaffer node provides **hierarchical light management** with inheritance-based overrides. It:
- **Light collection** - Groups light contexts for a specific scope (Master/Sequence/Shot)
- **Hierarchical inheritance** - Supports parent → child gaffer chains
- **Per-attribute overrides** - Each light attribute can be independently enabled/disabled
- **Flexible architecture** - Not hardcoded by type, supports custom chains

**Where Does It Fit in the Hierarchy?**

```
CTX_Sequence
    ↓ gaffer (single)
CTX_LightGaffer (Sequence-level)
    ↓ parentGaffer (single)
CTX_LightGaffer (Master-level)
    ↓ lights[i] (multi)
CTX_LightContext (per-light storage)
```

**Inheritance Chain Example:**

```
Master Gaffer (gafferType='master')
    ↓ parentGaffer
Sequence Gaffer (gafferType='sequence', scopeCode='sq0070')
    ↓ parentGaffer
Shot Gaffer (gafferType='shot', scopeCode='SH0170')
```

**When Should It Be Used?**

- **Master lighting** - Create master gaffer for project-wide lighting
- **Sequence lighting** - Create sequence gaffer for sequence-specific adjustments
- **Shot lighting** - Create shot gaffer for shot-specific tweaks
- **Custom lighting** - Create custom gaffers for special cases

### 3. Wrapper API

**Key Methods:**

```python
class CTXLightGafferNode(NodeWrapper):
    SCHEMA = CTXLightGafferSchema

    # Manual wiring
    def set_parent_node(self, parent):
        """Wire to parent context node (Sequence/Shot/Manager)."""

    def set_parent_gaffer(self, parent_gaffer):
        """Wire to parent gaffer in inheritance chain."""

    def add_light_context(self, light_context):
        """Add light context to this gaffer."""

    # Query methods
    def get_parent_node(self):
        """Get parent context node."""

    def get_parent_gaffer(self):
        """Get parent gaffer."""

    def get_child_gaffers(self):
        """Get child gaffers."""

    def get_light_contexts(self):
        """Get all light contexts."""

    # Discovery
    @staticmethod
    def list_all():
        """List all gaffers in scene."""
```

**Usage Example:**

```python
# Create master gaffer
master = CTXLightGafferNode.create(
    gafferName='Master',
    gafferType='master'
)

# Create sequence gaffer
seq_gaffer = CTXLightGafferNode.create(
    gafferName='sq0070',
    gafferType='sequence',
    scopeCode='sq0070'
)

# Wire sequence gaffer to master (inheritance chain)
seq_gaffer.set_parent_gaffer(master)

# Wire sequence gaffer to sequence node
seq = CTXSequenceNode.find_by_code('sq0070')
seq.set_gaffer(seq_gaffer)

# Add light contexts
light_ctx = CTXLightContextNode.create(lightName='keyLight1')
seq_gaffer.add_light_context(light_ctx)
```

### 4. Node Behavior

**Creation:**
- ✅ Creates Maya network node with `CTX_LightGaffer` prefix
- ✅ Adds connection attributes (parentNode, parentGaffer, childGaffers, lights)
- ✅ Sets default enabled state (True)
- ✅ No automatic light context creation (manual setup required)

**Connection:**
- When parent gaffer connects → Establishes inheritance chain
- When light context connects → Adds light to gaffer
- When child gaffer connects → Adds child to inheritance chain

**Attribute Changes:**
- `enabled` change → Should affect light attribute resolution (handled by resolver)
- `gafferType` change → No side effects (for UI organization only)

**Deletion:**
- ⚠️ Deleting gaffer orphans all light contexts
- ⚠️ Deleting gaffer breaks inheritance chain for child gaffers

### 5. Node Limitations

**Known Constraints:**
- ⚠️ **No automatic light context creation** - User must create and add manually
- ⚠️ **No cascading delete** - Deleting gaffer orphans light contexts
- ⚠️ **No validation** - Does not validate inheritance chain integrity

**Future Improvements:**
- 🔲 Auto-create light contexts when lights added
- 🔲 Cascading delete (delete light contexts when gaffer deleted)
- 🔲 Validate inheritance chain (prevent cycles)

**Development Status:**
- ✅ Schema complete
- ✅ Wrapper complete
- ✅ Manual wiring complete
- ✅ Maya menu integration complete
- ✅ Gaffer Manager UI complete
- ✅ Attribute resolver complete
- ✅ Light operations complete

---

## CTX_LightContext Node

### 1. Schema Definition

**File:** `core/nodes/schemas/light_context.py`

```python
class CTXLightContextSchema(NodeSchema):
    NODE_TYPE = "network"
    NODE_PREFIX = "CTX_LightContext"
    CATEGORY = "Lighting"
    DESCRIPTION = "Light attribute context with per-attribute overrides"

    ATTRIBUTES = {
        'ctx_type': {'type': 'string', 'default': 'CTX_LightContext'},
        'lightName': {'type': 'string', 'default': '', 'description': 'Maya light name'},

        # Per-attribute storage with enable flags
        'intensity': {'type': 'float', 'default': 1.0},
        'intensityEnabled': {'type': 'bool', 'default': False},

        'exposure': {'type': 'float', 'default': 0.0},
        'exposureEnabled': {'type': 'bool', 'default': False},

        'colorR': {'type': 'float', 'default': 1.0},
        'colorG': {'type': 'float', 'default': 1.0},
        'colorB': {'type': 'float', 'default': 1.0},
        'colorEnabled': {'type': 'bool', 'default': False},

        'temperature': {'type': 'float', 'default': 6500.0},
        'temperatureEnabled': {'type': 'bool', 'default': False},

        'muted': {'type': 'bool', 'default': False},
        'mutedEnabled': {'type': 'bool', 'default': False},

        'translateX': {'type': 'float', 'default': 0.0},
        'translateY': {'type': 'float', 'default': 0.0},
        'translateZ': {'type': 'float', 'default': 0.0},
        'translateEnabled': {'type': 'bool', 'default': False},

        'rotateX': {'type': 'float', 'default': 0.0},
        'rotateY': {'type': 'float', 'default': 0.0},
        'rotateZ': {'type': 'float', 'default': 0.0},
        'rotateEnabled': {'type': 'bool', 'default': False},
    }

    CONNECTIONS = {
        'parentGaffer': {
            'type': 'message', 'multi': False, 'direction': 'input',
            'accepts': ['CTX_LightGaffer'],
            'description': 'Gaffer that owns this light context (LightContext.message → Gaffer.lights[i])'
        },
        'targetLight': {
            'type': 'message', 'multi': False, 'direction': 'output',
            'description': 'Maya light shape node (LightContext.message → Light.shape)'
        },
    }
```

### 2. Purpose

**What Problem Does This Solve?**

The CTX_LightContext node stores **per-gaffer overrides** for a specific light. It:
- **Per-attribute storage** - Stores values for intensity, color, exposure, etc.
- **Per-attribute enable flags** - Each attribute has independent enabled flag
- **Flexible inheritance** - Enabled attributes override parent, disabled attributes inherit
- **Light linking** - Links to Maya light shape node

**Where Does It Fit in the Hierarchy?**

```
CTX_LightGaffer
    ↓ lights[i]
CTX_LightContext (LEAF NODE - stores attribute values)
    ↓ targetLight (output)
Maya Light Shape Node
```

**When Should It Be Used?**

- **Light override** - Store gaffer-specific overrides for a light
- **Attribute inheritance** - Control which attributes inherit from parent gaffer
- **Light tracking** - Track which lights are managed by gaffer

### 3. Wrapper API

**Key Methods:**

```python
class CTXLightContextNode(NodeWrapper):
    SCHEMA = CTXLightContextSchema

    # Manual wiring
    def set_parent_gaffer(self, gaffer):
        """Wire to parent gaffer."""

    def set_target_light(self, light):
        """Wire to Maya light shape node."""

    # Query methods
    def get_parent_gaffer(self):
        """Get parent gaffer."""

    def get_target_light(self):
        """Get Maya light shape node."""

    # Discovery
    @staticmethod
    def list_all():
        """List all light contexts in scene."""
```

**Usage Example:**

```python
# Create light context
light_ctx = CTXLightContextNode.create(
    lightName='keyLight1'
)

# Wire to gaffer
gaffer = CTXLightGafferNode.list_all()[0]
light_ctx.set_parent_gaffer(gaffer)

# Wire to Maya light
light_ctx.set_target_light('keyLight1Shape')

# Set attribute overrides
light_ctx.set_attribute('intensity', 2.0)
light_ctx.set_attribute('intensityEnabled', True)  # Enable override

light_ctx.set_attribute('colorR', 1.0)
light_ctx.set_attribute('colorG', 0.8)
light_ctx.set_attribute('colorB', 0.6)
light_ctx.set_attribute('colorEnabled', False)  # Inherit from parent
```

### 4. Node Behavior

**Creation:**
- ✅ Creates Maya network node with `CTX_LightContext` prefix
- ✅ Adds connection attributes (parentGaffer, targetLight)
- ✅ Sets default attribute values
- ✅ All enable flags default to False (inherit from parent)

**Connection:**
- When gaffer connects → Adds light context to gaffer
- When light connects → Links to Maya light shape

**Attribute Changes:**
- Attribute value change → No automatic application (user must apply manually)
- Enable flag change → Affects attribute resolution in inheritance chain

**Deletion:**
- ✅ Deleting light context does not affect gaffer or Maya light
- ✅ Safe to delete

### 5. Node Limitations

**Known Constraints:**
- ⚠️ **No automatic attribute application** - User must apply values to Maya light manually
- ⚠️ **No automatic capture** - User must capture values from Maya light manually
- ⚠️ **Fixed attribute set** - Cannot add custom attributes dynamically

**Future Improvements:**
- 🔲 Auto-apply attributes when values change
- 🔲 Auto-capture attributes from Maya light
- 🔲 Dynamic attribute system (add custom attributes)
- 🔲 Renderer-specific attributes (Arnold, Redshift)

**Development Status:**
- ✅ Schema complete
- ✅ Wrapper complete
- ✅ Manual wiring complete
- ✅ Maya menu integration complete
- ✅ Light Editor UI complete
- ✅ Capture/apply operations complete
- ⏳ Auto-apply (future)

---

## Connection Patterns

### Pattern 1: Manager → Sequence → Shot → Asset

**Full Hierarchy Setup:**

```python
from core.nodes.wrappers import (
    CTXManagerNode, CTXSequenceNode, CTXShotNode, CTXAssetNode
)

# 1. Create manager (singleton)
manager = CTXManagerNode.create(
    config_path='/path/to/config.json',
    project_root='/path/to/project'
)

# 2. Create sequence
seq = CTXSequenceNode.create(
    sequenceCode='sq0070',
    sequenceName='Sequence 70'
)

# 3. Wire sequence to manager
manager.add_sequence(seq)
# OR: seq.set_parent_manager(manager)

# 4. Create shot
shot = CTXShotNode.create(
    ep_code='Ep04',
    seq_code='sq0070',
    shot_code='SH0170'
)

# 5. Wire shot to sequence
seq.add_shot(shot)
# OR: shot.set_parent_sequence(seq)

# 6. Create asset
asset = CTXAssetNode.create(
    asset_type='CHAR',
    asset_name='CatStompie',
    file_path='/path/to/CatStompie_v003.abc'
)

# 7. Wire asset to shot
shot.add_asset(asset)
# OR: asset.set_parent_shot(shot)
```

**Connection Diagram:**

```
CTX_Manager
    ↓ sequences[0] (INPUT MULTI)
    ↑ parentManager (INPUT SINGLE)
CTX_Sequence
    ↓ shots[0] (INPUT MULTI)
    ↑ parentSequence (INPUT SINGLE)
CTX_Shot
    ↓ assets[0] (INPUT MULTI)
    ↑ parentShot (INPUT SINGLE)
CTX_Asset
```

**Message Attribute Connections (Unidirectional):**

```python
# Manager ← Sequence (child → parent)
cmds.connectAttr("seq.message", "manager.sequences[0]", nextAvailable=True)

# Sequence ← Shot (child → parent)
cmds.connectAttr("shot.message", "seq.shots[0]", nextAvailable=True)

# Shot ← Asset (child → parent)
cmds.connectAttr("asset.message", "shot.assets[0]", nextAvailable=True)
```

**Querying (Both Directions from ONE Connection):**

```python
# Get children from parent
sequences = cmds.listConnections("manager.sequences", source=True, destination=False)
shots = cmds.listConnections("sequence.shots", source=True, destination=False)
assets = cmds.listConnections("shot.assets", source=True, destination=False)

# Get parent from child
manager = cmds.listConnections("sequence.message", source=False, destination=True, type='network')
sequence = cmds.listConnections("shot.message", source=False, destination=True, type='network')
shot = cmds.listConnections("asset.message", source=False, destination=True, type='network')
```

---

### Pattern 2: Gaffer Inheritance Chain with Direct Ownership

**Master → Sequence → Shot Gaffer Chain (with direct shot ownership):**

```python
from core.nodes.wrappers import CTXLightGafferNode, CTXSequenceNode, CTXShotNode

# 1. Create master gaffer
master = CTXLightGafferNode.create(
    gafferName='Master',
    gafferType='master'
)

# 2. Create sequence gaffer
seq_gaffer = CTXLightGafferNode.create(
    gafferName='sq0070',
    gafferType='sequence',
    scopeCode='sq0070'
)

# 3. Wire sequence gaffer to master (inheritance chain)
seq_gaffer.set_parent_gaffer(master)

# 4. Wire sequence gaffer to sequence node (direct ownership)
seq = CTXSequenceNode.find_by_code('sq0070')
seq.set_gaffer(seq_gaffer)

# 5. Create shot gaffer
shot_gaffer = CTXLightGafferNode.create(
    gafferName='SH0170',
    gafferType='shot',
    scopeCode='SH0170'
)

# 6. Wire shot gaffer to shot node (direct ownership - NEW!)
shot = CTXShotNode.find_by_code('Ep04', 'sq0070', 'SH0170')
shot.set_gaffer(shot_gaffer)

# 7. Wire shot gaffer to sequence gaffer (inheritance chain)
shot_gaffer.set_parent_gaffer(seq_gaffer)
```

**Connection Diagram:**

```
Master Gaffer (gafferType='master')
    ↓ childGaffers[0] (OUTPUT MULTI)
    ↑ parentGaffer (INPUT SINGLE) - None (root)

Sequence Gaffer (gafferType='sequence')
    ↓ childGaffers[0] (OUTPUT MULTI)
    ↑ parentGaffer (INPUT SINGLE) - Points to Master
    ↑ parentNode (INPUT SINGLE) - Points to CTX_Sequence

Shot Gaffer (gafferType='shot')
    ↓ childGaffers[0] (OUTPUT MULTI)
    ↑ parentGaffer (INPUT SINGLE) - Points to Sequence
    ↑ parentNode (INPUT SINGLE) - Points to CTX_Shot (NEW!)
```

**Key Difference from Previous Design:**
- ✅ **Previous:** Shot gaffer only connected via inheritance chain (no direct shot.gaffer)
- ✅ **New:** Shot gaffer directly owned by shot (shot.gaffer) + inheritance chain (parentGaffer)

**Attribute Resolution Flow:**

```
Query: light.intensity

1. Check Shot Gaffer
   - intensityEnabled? → Use shot_gaffer.intensity
   - Not enabled → Continue to parent

2. Check Sequence Gaffer
   - intensityEnabled? → Use seq_gaffer.intensity
   - Not enabled → Continue to parent

3. Check Master Gaffer
   - intensityEnabled? → Use master.intensity
   - Not enabled → Continue to fallback

4. Use Light's Current Value (fallback)
```

---

### Pattern 3: Light Context Management

**Adding Lights to Gaffer:**

```python
from core.nodes.wrappers import CTXLightGafferNode, CTXLightContextNode

# 1. Get gaffer
gaffer = CTXLightGafferNode.list_all()[0]

# 2. Create light context for each light
light_ctx1 = CTXLightContextNode.create(lightName='keyLight1')
light_ctx2 = CTXLightContextNode.create(lightName='fillLight1')

# 3. Wire light contexts to gaffer
gaffer.add_light_context(light_ctx1)
gaffer.add_light_context(light_ctx2)

# 4. Wire light contexts to Maya lights
light_ctx1.set_target_light('keyLight1Shape')
light_ctx2.set_target_light('fillLight1Shape')

# 5. Set attribute overrides
light_ctx1.set_attribute('intensity', 2.0)
light_ctx1.set_attribute('intensityEnabled', True)  # Override

light_ctx2.set_attribute('intensity', 0.5)
light_ctx2.set_attribute('intensityEnabled', False)  # Inherit
```

**Connection Diagram:**

```
CTX_LightGaffer
    ↓ lights[0] (OUTPUT MULTI)
    ↑ parentGaffer (INPUT SINGLE)
CTX_LightContext
    ↓ targetLight (OUTPUT SINGLE)
Maya Light Shape Node
```

---

## Common Workflows

### Workflow 1: Create Complete Shot Hierarchy

**Goal:** Create manager, sequence, shot, and assets from scratch.

```python
from core.nodes.wrappers import (
    CTXManagerNode, CTXSequenceNode, CTXShotNode, CTXAssetNode
)

# Step 1: Create manager (if not exists)
manager = CTXManagerNode.get_manager()
if manager is None:
    manager = CTXManagerNode.create(
        config_path='/path/to/config.json',
        project_root='/path/to/project'
    )

# Step 2: Create sequence
seq = CTXSequenceNode.create(
    sequenceCode='sq0070',
    sequenceName='Sequence 70',
    frameStart=1001,
    frameEnd=1200
)
manager.add_sequence(seq)

# Step 3: Create multiple shots
shots = []
for shot_num in range(10, 31, 10):  # SH0010, SH0020, SH0030
    shot = CTXShotNode.create(
        ep_code='Ep04',
        seq_code='sq0070',
        shot_code='SH{:04d}'.format(shot_num),
        start_frame=1001 + (shot_num * 10),
        end_frame=1100 + (shot_num * 10)
    )
    seq.add_shot(shot)
    shots.append(shot)

# Step 4: Add assets to each shot
for shot in shots:
    # Add character
    char_asset = CTXAssetNode.create(
        asset_type='CHAR',
        asset_name='CatStompie',
        variant='001',
        file_path='/path/to/CatStompie_v003.abc',
        version='v003'
    )
    shot.add_asset(char_asset)

    # Add camera
    cam_asset = CTXAssetNode.create(
        asset_type='CAM',
        asset_name='shotCam',
        variant='001',
        file_path='/path/to/shotCam_v001.abc',
        version='v001'
    )
    shot.add_asset(cam_asset)

print("Created {} shots with {} assets each".format(len(shots), 2))
```

---

### Workflow 2: Create Gaffer Inheritance Chain

**Goal:** Create Master → Sequence → Shot gaffer chain with light overrides.

```python
from core.nodes.wrappers import (
    CTXLightGafferNode, CTXLightContextNode, CTXSequenceNode
)

# Step 1: Create master gaffer
master = CTXLightGafferNode.create(
    gafferName='Master',
    gafferType='master'
)

# Step 2: Add lights to master gaffer
lights = ['keyLight1', 'fillLight1', 'rimLight1']
for light_name in lights:
    light_ctx = CTXLightContextNode.create(lightName=light_name)
    master.add_light_context(light_ctx)
    light_ctx.set_target_light(light_name + 'Shape')

    # Set master values (all enabled)
    light_ctx.set_attribute('intensity', 1.0)
    light_ctx.set_attribute('intensityEnabled', True)
    light_ctx.set_attribute('colorR', 1.0)
    light_ctx.set_attribute('colorG', 1.0)
    light_ctx.set_attribute('colorB', 1.0)
    light_ctx.set_attribute('colorEnabled', True)

# Step 3: Create sequence gaffer
seq = CTXSequenceNode.find_by_code('sq0070')
seq_gaffer = CTXLightGafferNode.create(
    gafferName='sq0070',
    gafferType='sequence',
    scopeCode='sq0070'
)
seq_gaffer.set_parent_gaffer(master)  # Inherit from master
seq.set_gaffer(seq_gaffer)

# Step 4: Add lights to sequence gaffer (override some attributes)
for light_name in lights:
    light_ctx = CTXLightContextNode.create(lightName=light_name)
    seq_gaffer.add_light_context(light_ctx)
    light_ctx.set_target_light(light_name + 'Shape')

    # Override intensity, inherit color
    light_ctx.set_attribute('intensity', 1.5)
    light_ctx.set_attribute('intensityEnabled', True)  # Override
    light_ctx.set_attribute('colorEnabled', False)  # Inherit from master

# Step 5: Create shot gaffer
shot_gaffer = CTXLightGafferNode.create(
    gafferName='SH0170',
    gafferType='shot',
    scopeCode='SH0170'
)

# Step 6: Wire shot gaffer to shot node (direct ownership - NEW!)
shot = CTXShotNode.find_by_code('Ep04', 'sq0070', 'SH0170')
shot.set_gaffer(shot_gaffer)

# Step 7: Wire shot gaffer to sequence gaffer (inheritance chain)
shot_gaffer.set_parent_gaffer(seq_gaffer)  # Inherit from sequence

# Step 8: Add lights to shot gaffer (override specific lights)
# Only override keyLight, inherit others
key_light_ctx = CTXLightContextNode.create(lightName='keyLight1')
shot_gaffer.add_light_context(key_light_ctx)
key_light_ctx.set_target_light('keyLight1Shape')

# Override color, inherit intensity
key_light_ctx.set_attribute('colorR', 1.0)
key_light_ctx.set_attribute('colorG', 0.8)
key_light_ctx.set_attribute('colorB', 0.6)
key_light_ctx.set_attribute('colorEnabled', True)  # Override
key_light_ctx.set_attribute('intensityEnabled', False)  # Inherit from sequence

print("Created gaffer chain: Master → Sequence → Shot")
print("  - Sequence gaffer owned by CTX_Sequence")
print("  - Shot gaffer owned by CTX_Shot (NEW!)")
print("  - Shot gaffer inherits from Sequence gaffer")
```

---

### Workflow 3: Query Node Hierarchy

**Goal:** Query all nodes in hierarchy and print structure.

```python
from core.nodes.wrappers import (
    CTXManagerNode, CTXSequenceNode, CTXShotNode, CTXAssetNode
)

# Get manager
manager = CTXManagerNode.get_manager()
if manager is None:
    print("No manager found")
else:
    print("Manager: {}".format(manager.node_name))
    print("  config_path: {}".format(manager.get_attribute('config_path')))
    print("  project_root: {}".format(manager.get_attribute('project_root')))

    # Get sequences
    sequences = manager.get_sequences()
    print("\n  Sequences ({})".format(len(sequences)))
    for seq in sequences:
        print("    - {} ({})".format(
            seq.get_sequence_name(),
            seq.get_sequence_code()
        ))

        # Get shots
        shots = seq.get_shots()
        print("      Shots ({})".format(len(shots)))
        for shot in shots:
            shot_id = shot.get_shot_id()
            print("        - {}".format(shot_id))

            # Get assets
            assets = shot.get_assets()
            print("          Assets ({})".format(len(assets)))
            for asset in assets:
                asset_id = asset.get_asset_id()
                print("            - {}".format(asset_id))
```

**Example Output:**

```
Manager: CTX_Manager1
  config_path: /path/to/config.json
  project_root: /path/to/project

  Sequences (1)
    - Sequence 70 (sq0070)
      Shots (3)
        - Ep04_sq0070_SH0010
          Assets (2)
            - CHAR_CatStompie_001
            - CAM_shotCam_001
        - Ep04_sq0070_SH0020
          Assets (2)
            - CHAR_CatStompie_001
            - CAM_shotCam_001
        - Ep04_sq0070_SH0030
          Assets (2)
            - CHAR_CatStompie_001
            - CAM_shotCam_001
```

---

### Workflow 4: Resolve Light Attributes Through Inheritance Chain

**Goal:** Query light attribute values through gaffer inheritance chain.

```python
from core.gaffer.resolver import AttributeResolver
from core.nodes.wrappers import CTXLightGafferNode

# Get shot gaffer
shot_gaffer = CTXLightGafferNode.list_all()[0]

# Create resolver
resolver = AttributeResolver()

# Resolve intensity for keyLight1
intensity = resolver.resolve_attribute(
    gaffer_node=shot_gaffer.node_name,
    light_name='keyLight1',
    attribute_name='intensity'
)

print("Resolved intensity: {}".format(intensity))

# Resolve color for keyLight1
color = resolver.resolve_attribute(
    gaffer_node=shot_gaffer.node_name,
    light_name='keyLight1',
    attribute_name='color'
)

print("Resolved color: {}".format(color))
```

**Resolution Process:**

```
1. Check Shot Gaffer (SH0170)
   - keyLight1 exists?
   - intensityEnabled? → No → Continue to parent
   - colorEnabled? → Yes → Use shot color [1.0, 0.8, 0.6]

2. Check Sequence Gaffer (sq0070)
   - keyLight1 exists?
   - intensityEnabled? → Yes → Use sequence intensity 1.5

3. Result:
   - intensity: 1.5 (from sequence gaffer)
   - color: [1.0, 0.8, 0.6] (from shot gaffer)
```

---

## Summary

This document provides a comprehensive reference for all CTX node types in the schema-based node system. Each node section includes:

✅ **Schema Definition** - Complete ATTRIBUTES and CONNECTIONS
✅ **Purpose** - Problem solved, hierarchy position, use cases
✅ **Wrapper API** - Key methods and usage examples
✅ **Node Behavior** - Creation, connection, attribute changes, deletion
✅ **Node Actions** - Operations performed on/by the node
✅ **UI Integration** - How node interacts with UI
✅ **Node Limitations** - Constraints, edge cases, future improvements
✅ **Development Status** - Current implementation status

**Connection Patterns** demonstrate how nodes connect to each other using message attributes.

**Common Workflows** provide practical examples for:
- Creating complete shot hierarchies
- Setting up gaffer inheritance chains
- Querying node hierarchies
- Resolving light attributes through inheritance

---

**Maintainer:** CTX Pipeline Team
**Repository:** https://github.com/katha-begin/maya-multishot.git
**Last Updated:** 2026-02-22
**Related Documents:**
- [AGENT.md](../../AGENT.md) - Project overview
- [NODE_ARCHITECTURE.md](../../spec/NODE_ARCHITECTURE.md) - Schema-based architecture
- [ARCHITECTURE_SUMMARY.md](../../spec/ARCHITECTURE_SUMMARY.md) - Repository structure

