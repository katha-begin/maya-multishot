# CTX Light Specification Document

## Version History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | 2024 | - | Initial specification |

---

## Table of Contents

1. [Overview](#1-overview)
2. [3-Layer Gaffer System](#2-3-layer-gaffer-system)
3. [Node Specifications](#3-node-specifications)
4. [Resolution Logic](#4-resolution-logic)
5. [Supported Light Types](#5-supported-light-types)
6. [Light Attributes](#6-light-attributes)
7. [Transform Handling](#7-transform-handling)
8. [Workflows](#8-workflows)
9. [UI Specification](#9-ui-specification)
10. [API Reference](#10-api-reference)

---

## 1. Overview

### 1.1 Purpose

The CTX Light system provides a layered approach to managing light values across multiple shots within a Maya scene. Similar to Foundry Katana's Gaffer, it allows artists to:

- Define base light rigs (Master)
- Create sequence-wide adjustments (Seq)
- Apply shot-specific tweaks (Shot)
- Switch between shots with automatic light value updates

### 1.2 Core Concepts

| Concept | Description |
|---------|-------------|
| Gaffer | A container that holds light context nodes for a specific scope |
| Light Context | Stores attribute values and overrides for a single light |
| Inheritance | Lower priority gaffers provide default values for higher priority gaffers |
| Sparse Storage | Only override values are stored, not all attributes |
| Resolution | Process of determining final light value from gaffer stack |

### 1.3 Design Principles

| Principle | Description |
|-----------|-------------|
| Non-destructive | Original light values preserved, overrides stored separately |
| Sparse | Only store what changes, inherit the rest |
| Predictable | Clear priority order (Shot > Seq > Master) |
| Viewport-friendly | Transform not connected, allows free manipulation |
| Scene-persistent | All data stored in Maya scene via network nodes |

---

## 2. Dynamic Gaffer Chain System

### 2.1 Unified Hierarchy Structure

The gaffer system is integrated into the hierarchy nodes (Manager → Sequence → Shot) with dynamic inheritance chains:

```
CTX_Manager
    ├─ masterGaffer → CTX_LightGaffer_Master
    └─ sequences → CTX_Sequence
                      ├─ gaffer → CTX_LightGaffer_Seq
                      └─ shots → CTX_Shot
                                    ├─ gaffer → CTX_LightGaffer_Shot
                                    └─ assets → CTX_Asset
```

**Key Design:** Gaffer and Assets are siblings under CTX_Shot - both are "content" of the shot.

### 2.2 Default 3-Layer Chain

```
+------------------+
|   SHOT GAFFER    |  Priority: HIGH (shot-specific overrides)
+------------------+
        ↑ parentGaffer
+------------------+
|   SEQ GAFFER     |  Priority: MEDIUM (sequence-wide look)
+------------------+
        ↑ parentGaffer
+------------------+
|  MASTER GAFFER   |  Priority: LOW (base light rig)
+------------------+
```

### 2.3 Dynamic Chain with Custom Gaffers

```
+------------------+
|   SHOT GAFFER    |  Priority: HIGHEST (shot-specific)
+------------------+
        ↑ parentGaffer
+------------------+
|  CUSTOM GAFFER   |  Priority: HIGH (e.g., TimeOfDay_Morning)
+------------------+
        ↑ parentGaffer
+------------------+
|   SEQ GAFFER     |  Priority: MEDIUM (sequence-wide)
+------------------+
        ↑ parentGaffer
+------------------+
|  MASTER GAFFER   |  Priority: LOW (base rig)
+------------------+
```

### 2.4 Gaffer Type Definitions

| Type | Scope | Node Name Pattern | Purpose |
|------|-------|-------------------|---------|
| master | Episode/Project | CTX_LightGaffer_Master | Base light rig with all lights and default values |
| seq | Sequence | CTX_LightGaffer_Seq_{seq_code} | Sequence-wide adjustments |
| shot | Shot | CTX_LightGaffer_Shot_{shot_code} | Shot-specific tweaks |
| custom | Variable | CTX_LightGaffer_Custom_{name} | Custom layers (time of day, mood, etc.) |

### 2.5 Dual Connection Pattern

Each gaffer has two types of connections:

| Connection | Purpose | Example |
|------------|---------|---------|
| parentNode | Hierarchy ownership | Shot gaffer → CTX_Shot |
| parentGaffer | Inheritance chain | Shot gaffer → Seq gaffer |
| childGaffers | Inheritance chain | Master gaffer → [Seq gaffer, Custom gaffer] |

### 2.5.1 Ownership vs Inheritance

The gaffer system uses a **dual-connection pattern** that combines direct ownership with inheritance:

**Direct Ownership (Parent-Child):**
- Sequence owns its gaffer via `Sequence.gaffer` connection
- Shot owns its gaffer via `Shot.gaffer` connection (NEW!)
- Similar to how Sequence owns shots, Shot owns assets
- Provides clear parent-child relationship and direct access

**Inheritance Chain (Hierarchical):**
- Shot gaffer inherits from Sequence gaffer via `parentGaffer` connection
- Sequence gaffer inherits from Master gaffer via `parentGaffer` connection
- Attribute resolution walks up the chain checking enabled flags
- Allows flexible override control at each level

**Benefits of This Design:**
- ✅ **Symmetry** - Both Sequence and Shot directly own their gaffers
- ✅ **Clarity** - Clear parent-child relationship (like Sequence→Shots, Shot→Assets)
- ✅ **Direct Access** - Can query `shot.get_gaffer()` directly
- ✅ **Consistency** - Follows same pattern as other parent-child relationships
- ✅ **Inheritance Still Works** - Shot gaffer's `parentGaffer` still points to Sequence gaffer for attribute resolution
- ✅ **Flexible Chains** - Not hardcoded by type (Master/Sequence/Shot), supports custom chains

**Visual Representation:**

```
CTX_Sequence
    ↓ gaffer (INPUT SINGLE) - Sequence owns its gaffer
CTX_LightGaffer (Sequence-level)
    ↓ parentGaffer (INPUT) - Inherits from Master
    ↓ lights (OUTPUT MULTI)
CTX_LightContext (per-light storage)

CTX_Shot
    ↓ gaffer (INPUT SINGLE) - Shot owns its gaffer (NEW!)
CTX_LightGaffer (Shot-level)
    ↓ parentGaffer (INPUT) - Inherits from Sequence
    ↓ lights (OUTPUT MULTI)
CTX_LightContext (per-light storage)
```

### 2.6 Resolution Priority

```
Smallest scope wins (walk chain from highest to lowest priority):

1. Check Shot gaffer       --> if found and enabled, USE THIS
2. Check Custom gaffer(s)  --> if found and enabled, USE THIS
3. Check Seq gaffer        --> if found and enabled, USE THIS
4. Check Master gaffer     --> if found and enabled, USE THIS
5. No value found          --> attribute not managed
```

---

## 3. Node Specifications

### 3.1 CTX_Sequence Node

Container for sequence-level organization. Groups shots within a sequence and owns the sequence-level light gaffer.

**Node Naming:**
```
CTX_Sequence_{sequenceCode}

Example:
CTX_Sequence_sq0070
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| sequenceCode | string | Sequence code (e.g., "sq0070") |
| sequenceName | string | Human-readable sequence name |
| frameStart | int | Sequence start frame |
| frameEnd | int | Sequence end frame |
| parentManager | message | Connection to CTX_Manager |
| shots | message[] | Connections to CTX_Shot nodes |
| gaffer | message | Connection to CTX_LightGaffer_Seq |

**Attribute Definitions:**

```python
SEQUENCE_ATTRS = {
    "sequenceCode": {"type": "string", "default": ""},
    "sequenceName": {"type": "string", "default": ""},
    "frameStart": {"type": "long", "default": 1001},
    "frameEnd": {"type": "long", "default": 2000},
}
```

### 3.2 CTX_Shot Node

Container for shot-level organization. Groups assets within a shot and owns the shot-level light gaffer.

**Node Naming:**
```
CTX_Shot_{episodeCode}_{sequenceCode}_{shotCode}

Example:
CTX_Shot_Ep04_sq0070_SH0170
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| ep_code | string | Episode code (e.g., "Ep04") |
| seq_code | string | Sequence code (e.g., "sq0070") |
| shot_code | string | Shot code (e.g., "SH0170") |
| start_frame | int | Shot start frame |
| end_frame | int | Shot end frame |
| is_active | bool | Whether this shot is currently active |
| parentSequence | message | Connection to CTX_Sequence |
| assets | message[] | Connections to CTX_Asset nodes |
| gaffer | message | Connection to CTX_LightGaffer_Shot (NEW!) |
| display_layer_link | message | Connection to Maya display layer |

**Gaffer Connection (NEW):**

The `gaffer` attribute enables direct ownership of the shot-level gaffer:

```python
# Wire shot gaffer to shot node (direct ownership)
shot = CTXShotNode.find_by_code('Ep04', 'sq0070', 'SH0170')
shot_gaffer = CTXLightGafferNode.create(
    gafferName='SH0170',
    gafferType='shot',
    scopeCode='SH0170'
)
shot.set_gaffer(shot_gaffer)  # Direct ownership

# Wire shot gaffer to sequence gaffer (inheritance chain)
shot_gaffer.set_parent_gaffer(seq_gaffer)  # Inheritance chain
```

**Attribute Definitions:**

```python
SHOT_ATTRS = {
    "ep_code": {"type": "string", "default": ""},
    "seq_code": {"type": "string", "default": ""},
    "shot_code": {"type": "string", "default": ""},
    "start_frame": {"type": "long", "default": 1001},
    "end_frame": {"type": "long", "default": 1100},
    "is_active": {"type": "bool", "default": False},
}
```

### 3.3 CTX_LightGaffer Node

Network node that contains a collection of light contexts for a specific scope. Supports dynamic gaffer chains with dual connection pattern.

**Node Naming:**
```
CTX_LightGaffer_Master
CTX_LightGaffer_Seq_sq0070
CTX_LightGaffer_Shot_SH0010
CTX_LightGaffer_Custom_Morning
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| gafferName | string | Display name |
| gafferType | string | "master", "seq", "shot", or "custom" |
| scopeCode | string | Sequence or shot code (empty for Master) |
| enabled | bool | Whether this gaffer is active |
| priority | int | Manual priority override |
| description | string | Human-readable description |
| color | float3 | UI color coding |
| parentNode | message | Connection to hierarchy node (Manager/Sequence/Shot) |
| parentGaffer | message | Connection to parent gaffer (inheritance chain) |
| childGaffers | message[] | Connections to child gaffers (inheritance chain) |
| lights | message[] | Connections to CTX_LightContext nodes |

**Attribute Definitions:**

```python
GAFFER_ATTRS = {
    "gafferName": {"type": "string", "default": ""},
    "gafferType": {"type": "string", "default": "custom"},
    "scopeCode": {"type": "string", "default": ""},
    "enabled": {"type": "bool", "default": True},
    "priority": {"type": "long", "default": 0},
    "description": {"type": "string", "default": ""},
    "color": {"type": "float3", "default": (0.5, 0.5, 0.5)},
}
```

### 3.4 CTX_LightContext Node

Network node that stores attribute values for a single light within a gaffer.

**Node Naming:**
```
CTX_LightContext_{light_name}_{gaffer_scope}

Examples:
CTX_LightContext_keyLight1_Master
CTX_LightContext_keyLight1_sq0070
CTX_LightContext_keyLight1_SH0010
```

**Attributes:**

| Category | Attribute | Type | Description |
|----------|-----------|------|-------------|
| Identity | lightName | string | Friendly name for the light |
| Identity | targetLight | message | Connection to actual Maya light shape |
| Identity | parentGaffer | message | Connection to parent CTX_LightGaffer |
| State | muted | bool | Disable light for this scope |
| State | mutedEnabled | bool | Whether muted is overridden |
| Property | intensity | float | Light intensity |
| Property | intensityEnabled | bool | Whether intensity is overridden |
| Property | exposure | float | Light exposure |
| Property | exposureEnabled | bool | Whether exposure is overridden |
| Property | colorR | float | Color red component |
| Property | colorG | float | Color green component |
| Property | colorB | float | Color blue component |
| Property | colorEnabled | bool | Whether color is overridden |
| Property | temperature | float | Color temperature (Kelvin) |
| Property | temperatureEnabled | bool | Whether temperature is overridden |
| Property | samples | int | Render samples |
| Property | samplesEnabled | bool | Whether samples is overridden |
| Contribution | camera | float | Camera ray contribution (0-1) |
| Contribution | cameraEnabled | bool | Whether camera is overridden |
| Contribution | diffuse | float | Diffuse contribution (0-1) |
| Contribution | diffuseEnabled | bool | Whether diffuse is overridden |
| Contribution | specular | float | Specular contribution (0-1) |
| Contribution | specularEnabled | bool | Whether specular is overridden |
| Contribution | sss | float | SSS contribution (0-1) |
| Contribution | sssEnabled | bool | Whether sss is overridden |
| Contribution | indirect | float | Indirect contribution (0-1) |
| Contribution | indirectEnabled | bool | Whether indirect is overridden |
| Contribution | volume | float | Volume contribution (0-1) |
| Contribution | volumeEnabled | bool | Whether volume is overridden |
| Transform | translateX | float | Position X |
| Transform | translateY | float | Position Y |
| Transform | translateZ | float | Position Z |
| Transform | rotateX | float | Rotation X |
| Transform | rotateY | float | Rotation Y |
| Transform | rotateZ | float | Rotation Z |
| Transform | scaleX | float | Scale X |
| Transform | scaleY | float | Scale Y |
| Transform | scaleZ | float | Scale Z |
| Transform | transformEnabled | bool | Whether transform is overridden |

**Attribute Definitions:**

```python
LIGHT_CONTEXT_ATTRS = {
    # Identity
    "lightName": {"type": "string", "default": ""},
    
    # State
    "muted": {"type": "bool", "default": False},
    "mutedEnabled": {"type": "bool", "default": False},
    
    # Properties
    "intensity": {"type": "float", "default": 1.0},
    "intensityEnabled": {"type": "bool", "default": False},
    "exposure": {"type": "float", "default": 0.0},
    "exposureEnabled": {"type": "bool", "default": False},
    "colorR": {"type": "float", "default": 1.0},
    "colorG": {"type": "float", "default": 1.0},
    "colorB": {"type": "float", "default": 1.0},
    "colorEnabled": {"type": "bool", "default": False},
    "temperature": {"type": "float", "default": 6500.0},
    "temperatureEnabled": {"type": "bool", "default": False},
    "samples": {"type": "int", "default": 1},
    "samplesEnabled": {"type": "bool", "default": False},
    
    # Contribution
    "camera": {"type": "float", "default": 1.0},
    "cameraEnabled": {"type": "bool", "default": False},
    "diffuse": {"type": "float", "default": 1.0},
    "diffuseEnabled": {"type": "bool", "default": False},
    "specular": {"type": "float", "default": 1.0},
    "specularEnabled": {"type": "bool", "default": False},
    "sss": {"type": "float", "default": 1.0},
    "sssEnabled": {"type": "bool", "default": False},
    "indirect": {"type": "float", "default": 1.0},
    "indirectEnabled": {"type": "bool", "default": False},
    "volume": {"type": "float", "default": 1.0},
    "volumeEnabled": {"type": "bool", "default": False},
    
    # Transform
    "translateX": {"type": "float", "default": 0.0},
    "translateY": {"type": "float", "default": 0.0},
    "translateZ": {"type": "float", "default": 0.0},
    "rotateX": {"type": "float", "default": 0.0},
    "rotateY": {"type": "float", "default": 0.0},
    "rotateZ": {"type": "float", "default": 0.0},
    "scaleX": {"type": "float", "default": 1.0},
    "scaleY": {"type": "float", "default": 1.0},
    "scaleZ": {"type": "float", "default": 1.0},
    "transformEnabled": {"type": "bool", "default": False},
}
```

---

## 4. Resolution Logic

### 4.1 Building Gaffer Chain

The gaffer chain is built by walking up the hierarchy from shot to manager:

```python
def build_gaffer_chain_from_shot(shot_node):
    """
    Build gaffer chain by walking up hierarchy.

    Args:
        shot_node (CTXShotNode): Current shot

    Returns:
        list: [Shot_Gaffer, Seq_Gaffer, Master_Gaffer] (highest priority first)
    """
    chain = []

    # 1. Get shot gaffer
    shot_gaffer = shot_node.get_gaffer()
    if shot_gaffer:
        chain.append(shot_gaffer)

    # 2. Get sequence gaffer
    sequence = shot_node.get_parent_sequence()
    if sequence:
        seq_gaffer = sequence.get_gaffer()
        if seq_gaffer:
            chain.append(seq_gaffer)

        # 3. Get master gaffer
        manager = sequence.get_parent_manager()
        if manager:
            master_gaffer = manager.get_master_gaffer()
            if master_gaffer:
                chain.append(master_gaffer)

    return chain


def build_gaffer_chain_with_custom(shot_node):
    """
    Build gaffer chain including custom gaffers by walking parentGaffer chain.

    Returns:
        list: [Shot, Custom1, Custom2, Seq, Master] (highest priority first)
    """
    chain = []

    # Start with shot gaffer
    current_gaffer = shot_node.get_gaffer()

    # Walk up parentGaffer chain
    while current_gaffer:
        chain.append(current_gaffer)
        current_gaffer = current_gaffer.get_parent_gaffer()

    return chain
```

### 4.2 Resolution Algorithm

```python
def resolve_light_attribute(light_name, attr_name, shot_node):
    """
    Resolve the final value for a light attribute using dynamic gaffer chain.

    Args:
        light_name (str): Light identifier
        attr_name (str): Attribute name (e.g., "intensity")
        shot_node (CTXShotNode): Current shot node

    Returns:
        tuple: (value, source_gaffer) or (None, None)
    """
    # Build gaffer chain (highest priority first)
    gaffer_chain = build_gaffer_chain_from_shot(shot_node)

    # Walk through chain, find first enabled override
    for gaffer in gaffer_chain:
        if not gaffer.is_enabled():
            continue

        light_ctx = gaffer.get_light_context(light_name)
        if light_ctx is None:
            continue

        # Check if attribute is enabled (overridden) in this context
        enabled_attr = attr_name + "Enabled"
        if light_ctx.get_attr(enabled_attr):
            value = light_ctx.get_attr(attr_name)
            return value, gaffer

    # No override found
    return None, None


def resolve_all_light_attributes(light_name, shot_node):
    """
    Resolve all attributes for a light using dynamic gaffer chain.

    Returns:
        dict: {attr_name: (value, source_gaffer)}
    """
    result = {}

    for attr_name in LIGHT_ATTRIBUTES:
        value, source = resolve_light_attribute(
            light_name, attr_name, shot_node
        )
        if value is not None:
            result[attr_name] = {"value": value, "source": source}

    return result
```

### 4.3 Resolution Example (with Dynamic Chain)

```
Context:
    Shot: SH0020
    Sequence: sq0070
    Custom Gaffer: Morning (inserted between Seq and Master)

Light: keyLight1

Gaffer Chain (highest priority first):
Shot_SH0020 → Seq_sq0070 → Custom_Morning → Master

+------------------+------------------+------------------+------------------+
| Master           | Morning (Custom) | Seq (sq0070)     | Shot (SH0020)    |
+------------------+------------------+------------------+------------------+

Attribute: intensity
| Master: 1.0 (E)  | Morning: - (D)   | Seq: 0.8 (E)     | Shot: 1.5 (E)    |
Result: 1.5 (from Shot_SH0020)

Attribute: exposure
| Master: 0.0 (E)  | Morning: - (D)   | Seq: - (D)       | Shot: 0.3 (E)    |
Result: 0.3 (from Shot_SH0020)

Attribute: colorR
| Master: 1.0 (E)  | Morning: 1.0 (E) | Seq: - (D)       | Shot: - (D)      |
Result: 1.0 (from Custom_Morning)

Attribute: colorG
| Master: 1.0 (E)  | Morning: 0.9 (E) | Seq: - (D)       | Shot: - (D)      |
Result: 0.9 (from Custom_Morning)

Attribute: samples
| Master: 2 (E)    | Morning: - (D)   | Seq: - (D)       | Shot: - (D)      |
Result: 2 (from Master)

(E) = Enabled    (D) = Disabled/Not set
```

### 4.4 Mute Resolution

Mute is a special attribute that disables the light entirely.

```python
def is_light_muted(light_name, shot_node):
    """
    Check if light is muted for current context using dynamic chain.
    """
    muted, source = resolve_light_attribute(
        light_name, "muted", shot_node
    )
    return muted is True
```

---

## 5. Supported Light Types

### 5.1 Arnold Lights

| Light Type | Node Type | Supported |
|------------|-----------|-----------|
| Area Light | aiAreaLight | Yes |
| Skydome Light | aiSkyDomeLight | Yes |
| Mesh Light | aiMeshLight | Yes |
| Photometric Light | aiPhotometricLight | Yes |
| Physical Sky | aiPhysicalSky | Yes |
| Light Portal | aiLightPortal | Yes |

### 5.2 Redshift Lights

| Light Type | Node Type | Supported |
|------------|-----------|-----------|
| Physical Light | RedshiftPhysicalLight | Yes |
| Dome Light | RedshiftDomeLight | Yes |
| IES Light | RedshiftIESLight | Yes |
| Portal Light | RedshiftPortalLight | Yes |
| Physical Sun | RedshiftPhysicalSun | Yes |

### 5.3 Maya Native Lights

| Light Type | Node Type | Supported |
|------------|-----------|-----------|
| Directional Light | directionalLight | Yes |
| Point Light | pointLight | Yes |
| Spot Light | spotLight | Yes |
| Area Light | areaLight | Yes |
| Ambient Light | ambientLight | Yes |

---

## 6. Light Attributes

### 6.1 Common Attributes (All Renderers)

| Attribute | Type | Range | Description |
|-----------|------|-------|-------------|
| intensity | float | 0+ | Light brightness |
| exposure | float | -inf to +inf | Exposure adjustment (stops) |
| color | float3 | 0-1 | Light color RGB |
| temperature | float | 1000-40000 | Color temperature (Kelvin) |

### 6.2 Arnold-Specific Attributes

| Attribute | Type | Range | Description |
|-----------|------|-------|-------------|
| samples | int | 0+ | Sampling quality |
| normalize | bool | - | Normalize intensity by area |
| camera | float | 0-1 | Camera ray contribution |
| diffuse | float | 0-1 | Diffuse contribution |
| specular | float | 0-1 | Specular contribution |
| sss | float | 0-1 | Subsurface contribution |
| indirect | float | 0-1 | Indirect lighting contribution |
| volume | float | 0-1 | Volume contribution |

### 6.3 Redshift-Specific Attributes

| Attribute | Type | Range | Description |
|-----------|------|-------|-------------|
| samples | int | 1+ | Sampling quality |
| affectDiffuse | bool | - | Affect diffuse |
| affectSpecular | bool | - | Affect specular |
| affectGI | bool | - | Affect global illumination |

### 6.4 Attribute Categories

| Category | Attributes | Connection Method |
|----------|------------|-------------------|
| State | muted | Script-based |
| Properties | intensity, exposure, color, temperature, samples | Script-based |
| Contribution | camera, diffuse, specular, sss, indirect, volume | Script-based |
| Transform | translate, rotate, scale | Script-based (manual apply) |

---

## 7. Transform Handling

### 7.1 Design Decision

Light transform attributes (translate, rotate, scale) are handled via **script-based apply**, NOT Maya connections.

**Reason:** Connecting transform prevents:
- Look Through Selected
- Interactive viewport manipulation
- Using manipulators to aim lights

### 7.2 Transform Workflow

```
1. User positions light in viewport (free manipulation)
2. User clicks [Capture Transform]
3. Script stores position in CTX_LightContext node
4. When switching shots:
   - If transformEnabled = true, script applies stored transform
   - If transformEnabled = false, light stays at current position
```

### 7.3 Transform Storage

```
CTX_LightContext_keyLight1_SH0020
|
+-- translateX: 2.5
+-- translateY: 4.0
+-- translateZ: 3.0
+-- rotateX: -35.0
+-- rotateY: 45.0
+-- rotateZ: 0.0
+-- scaleX: 1.0
+-- scaleY: 1.0
+-- scaleZ: 1.0
+-- transformEnabled: true
```

### 7.4 Auto-Apply Option

| Setting | Behavior |
|---------|----------|
| Auto-Apply ON | Transform applied automatically when switching shots |
| Auto-Apply OFF | User manually clicks [Apply Transform] |

---

## 8. Workflows

### 8.1 Initial Setup

```
1. User opens Context Manager
2. User selects Project/Episode
3. System creates or finds CTX_LightGaffer_Master
4. User adds lights to Master gaffer:
   a. Select light in viewport
   b. Click [Add Light to Master]
   c. System creates CTX_LightContext with current values
5. Repeat for all lights in rig
6. Master gaffer now contains base light rig
```

### 8.2 Create Sequence Look

```
1. User selects sequence (sq0070)
2. System creates CTX_LightGaffer_Seq_sq0070 (if not exists)
3. User clicks [Add Override] for lights that need adjustment
4. System creates CTX_LightContext nodes (sparse)
5. User adjusts values in Gaffer Table
6. Values inherit from Master unless overridden
```

### 8.2.1 Wire Sequence Gaffer to Sequence Node (Code Example)

```python
from core.nodes.wrappers import CTXSequenceNode, CTXLightGafferNode

# 1. Create sequence gaffer
seq_gaffer = CTXLightGafferNode.create(
    gafferName='sq0070',
    gafferType='sequence',
    scopeCode='sq0070'
)

# 2. Wire sequence gaffer to sequence node (direct ownership)
seq = CTXSequenceNode.find_by_code('sq0070')
seq.set_gaffer(seq_gaffer)

# 3. Wire sequence gaffer to master gaffer (inheritance chain)
master = CTXLightGafferNode.find_by_type('master')
seq_gaffer.set_parent_gaffer(master)

print("Sequence gaffer created and wired:")
print(f"  - Owned by: {seq.node_name}")
print(f"  - Inherits from: {master.node_name}")
```

### 8.3 Create Shot Override

```
1. User selects shot (SH0020)
2. System creates CTX_LightGaffer_Shot_SH0020 (if not exists)
3. User clicks [Add Override] for lights that need adjustment
4. User adjusts values in Gaffer Table
5. Values inherit from Seq (or Master) unless overridden
```

### 8.3.1 Wire Shot Gaffer to Shot Node (Code Example - NEW!)

```python
from core.nodes.wrappers import CTXShotNode, CTXLightGafferNode

# 1. Create shot gaffer
shot_gaffer = CTXLightGafferNode.create(
    gafferName='SH0020',
    gafferType='shot',
    scopeCode='SH0020'
)

# 2. Wire shot gaffer to shot node (direct ownership - NEW!)
shot = CTXShotNode.find_by_code('Ep04', 'sq0070', 'SH0020')
shot.set_gaffer(shot_gaffer)

# 3. Wire shot gaffer to sequence gaffer (inheritance chain)
seq = shot.get_parent_sequence()
seq_gaffer = seq.get_gaffer()
shot_gaffer.set_parent_gaffer(seq_gaffer)

print("Shot gaffer created and wired:")
print(f"  - Owned by: {shot.node_name}")
print(f"  - Inherits from: {seq_gaffer.node_name}")
print(f"  - Which inherits from: Master gaffer")
```

**Key Difference from Previous Design:**
- ✅ **Previous:** Shot gaffer only connected via inheritance chain (no direct shot.gaffer)
- ✅ **New:** Shot gaffer directly owned by shot (shot.gaffer) + inheritance chain (parentGaffer)

### 8.4 Switch Shots

```
1. User changes active shot: SH0010 -> SH0020
2. System resolves all light values for SH0020:
   - Check Shot gaffer (SH0020)
   - Check Seq gaffer (sq0070)
   - Check Master gaffer
3. System applies resolved values to actual lights
4. If Auto-Apply Transform is ON, applies transforms too
5. Viewport updates with new light values
```

### 8.5 Capture from Scene

```
1. User adjusts light in viewport/Attribute Editor
2. User clicks [Capture from Scene]
3. Dialog shows changed values vs. current override
4. User selects which changes to capture
5. System updates CTX_LightContext node
6. System enables relevant *Enabled flags
```

---

## 9. UI Specification

**Note:** The UI specification has been moved to a separate document for better organization.

**See:** [CTX_gaffer_UI.md](CTX_gaffer_UI.md) for complete UI specification including:
- Gaffer Manager UI with gaffer selection dropdown
- Light list table with source and override indicators
- Light Editor panel with detailed attribute editing
- Workflows for adding lights, creating overrides, and editing values
- UI mockups and visual examples

---

## 10. API Reference

### 10.1 CTXLightGaffer Class

```python
class CTXLightGaffer(object):
    """
    Wrapper for CTX_LightGaffer network node.
    """
    
    @classmethod
    def create(cls, gaffer_type, scope_code=""):
        """
        Create new gaffer node.
        
        Args:
            gaffer_type (str): "master", "seq", or "shot"
            scope_code (str): Sequence or shot code
        
        Returns:
            CTXLightGaffer: New instance
        """
        pass
    
    @classmethod
    def get_master(cls):
        """
        Get Master gaffer.
        
        Returns:
            CTXLightGaffer: Master gaffer or None
        """
        pass
    
    @classmethod
    def get_seq(cls, seq_code):
        """
        Get Sequence gaffer.
        
        Args:
            seq_code (str): Sequence code
        
        Returns:
            CTXLightGaffer: Seq gaffer or None
        """
        pass
    
    @classmethod
    def get_shot(cls, shot_code):
        """
        Get Shot gaffer.
        
        Args:
            shot_code (str): Shot code
        
        Returns:
            CTXLightGaffer: Shot gaffer or None
        """
        pass
    
    def get_type(self):
        """Get gaffer type."""
        pass
    
    def is_enabled(self):
        """Check if gaffer is enabled."""
        pass
    
    def set_enabled(self, enabled):
        """Set gaffer enabled state."""
        pass
    
    def get_parent_gaffer(self):
        """Get parent gaffer for inheritance."""
        pass
    
    def get_light_contexts(self):
        """
        Get all light contexts in this gaffer.
        
        Returns:
            list: CTXLightContext instances
        """
        pass
    
    def get_light_context(self, light_name):
        """
        Get light context by name.
        
        Args:
            light_name (str): Light identifier
        
        Returns:
            CTXLightContext: Light context or None
        """
        pass
    
    def add_light(self, light_name, light_node, capture_current=True):
        """
        Add light to gaffer.
        
        Args:
            light_name (str): Light identifier
            light_node (str): Maya light node
            capture_current (bool): Capture current values
        
        Returns:
            CTXLightContext: New light context
        """
        pass
    
    def remove_light(self, light_name):
        """Remove light from gaffer."""
        pass
```

### 10.2 CTXLightContext Class

```python
class CTXLightContext(object):
    """
    Wrapper for CTX_LightContext network node.
    """
    
    @classmethod
    def create(cls, gaffer, light_name, light_node):
        """
        Create new light context.
        
        Args:
            gaffer (CTXLightGaffer): Parent gaffer
            light_name (str): Light identifier
            light_node (str): Maya light node
        
        Returns:
            CTXLightContext: New instance
        """
        pass
    
    def get_light_name(self):
        """Get light identifier."""
        pass
    
    def get_target_light(self):
        """Get Maya light node name."""
        pass
    
    def get_parent_gaffer(self):
        """Get parent gaffer."""
        pass
    
    def is_attr_enabled(self, attr_name):
        """Check if attribute is overridden."""
        pass
    
    def set_attr_enabled(self, attr_name, enabled):
        """Set attribute override state."""
        pass
    
    def get_attr(self, attr_name):
        """Get attribute value."""
        pass
    
    def set_attr(self, attr_name, value):
        """Set attribute value and enable override."""
        pass
    
    def capture_from_light(self, attributes=None):
        """
        Capture current values from Maya light.
        
        Args:
            attributes (list, optional): Specific attributes, or all
        """
        pass
    
    def apply_to_light(self, attributes=None):
        """
        Apply values to Maya light.
        
        Args:
            attributes (list, optional): Specific attributes, or all
        """
        pass
    
    def capture_transform(self):
        """Capture current transform from light."""
        pass
    
    def apply_transform(self):
        """Apply stored transform to light."""
        pass
```

### 10.2.1 CTXShotNode Class (NEW!)

```python
class CTXShotNode(NodeWrapper):
    """
    Shot context node with gaffer ownership.
    """

    SCHEMA = CTXShotSchema

    # Manual wiring - Gaffer (NEW)
    def set_gaffer(self, gaffer):
        """
        Wire to shot-level gaffer (direct ownership).

        Args:
            gaffer (CTXLightGafferNode): Shot-level gaffer

        Returns:
            bool: True if successful
        """
        pass

    # Query methods - Gaffer (NEW)
    def get_gaffer(self):
        """
        Get connected shot-level gaffer.

        Returns:
            CTXLightGafferNode: Shot gaffer or None
        """
        pass

    # Other existing methods
    def get_parent_sequence(self):
        """Get parent sequence."""
        pass

    def get_assets(self):
        """Get all connected assets."""
        pass

    def get_shot_id(self):
        """Get shot ID (e.g., 'Ep04_sq0070_SH0170')."""
        pass

    @staticmethod
    def find_by_code(ep_code, seq_code, shot_code):
        """Find shot by codes."""
        pass
```

### 10.3 LightResolver Class

```python
class LightResolver(object):
    """
    Resolves light values from gaffer stack.
    """
    
    def __init__(self, shot_code, seq_code):
        """
        Initialize resolver.
        
        Args:
            shot_code (str): Current shot
            seq_code (str): Current sequence
        """
        pass
    
    def resolve_attribute(self, light_name, attr_name):
        """
        Resolve single attribute.
        
        Returns:
            tuple: (value, source_gaffer_type)
        """
        pass
    
    def resolve_light(self, light_name):
        """
        Resolve all attributes for light.
        
        Returns:
            dict: {attr_name: {"value": v, "source": s}}
        """
        pass
    
    def resolve_all_lights(self):
        """
        Resolve all managed lights.
        
        Returns:
            dict: {light_name: {attr_name: {...}}}
        """
        pass
    
    def apply_to_scene(self, include_transform=False):
        """
        Apply resolved values to Maya lights.
        
        Args:
            include_transform (bool): Apply transform too
        """
        pass
    
    def get_all_light_names(self):
        """Get all managed light names."""
        pass
    
    def is_light_muted(self, light_name):
        """Check if light is muted."""
        pass
```

---

## Document End