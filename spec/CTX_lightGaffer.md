# CTX Node Architecture Document

## Version History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | 2024 | - | Initial architecture |

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Node Type Summary](#2-node-type-summary)
3. [CTX_Manager Node](#3-ctx_manager-node)
4. [CTX_Shot Node](#4-ctx_shot-node)
5. [CTX_Asset Node](#5-ctx_asset-node)
6. [CTX_LightGaffer Node](#6-ctx_lightgaffer-node)
7. [CTX_LightContext Node](#7-ctx_lightcontext-node)
8. [Display Layer Integration](#8-display-layer-integration)
9. [Node Relationships](#9-node-relationships)
10. [Complete Scene Example](#10-complete-scene-example)
11. [Naming Conventions](#11-naming-conventions)

---

## 1. Architecture Overview

### 1.1 System Diagram

```
+===========================================================================+
|                          CTX PIPELINE SYSTEM                               |
+===========================================================================+
|                                                                           |
|                           CTX_Manager                                     |
|                               |                                           |
|           +-------------------+-------------------+                       |
|           |                   |                   |                       |
|           v                   v                   v                       |
|      CTX_Shot            CTX_Shot            CTX_Shot                    |
|      SH0010              SH0020              SH0030                      |
|           |                   |                   |                       |
|     +-----+-----+       +-----+-----+       +-----+-----+                |
|     |           |       |           |       |           |                |
|     v           v       v           v       v           v                |
| CTX_Asset  CTX_Light  CTX_Asset  CTX_Light  CTX_Asset  CTX_Light        |
| (proxies)  Gaffer     (proxies)  Gaffer    (proxies)  Gaffer            |
|              |                     |                     |               |
|              v                     v                     v               |
|         CTX_Light            CTX_Light            CTX_Light             |
|         Context              Context              Context               |
|                                                                           |
+===========================================================================+
|                                                                           |
|  MAYA SCENE OBJECTS                                                       |
|  +-----------------------------------------------------------------------+|
|  | aiStandIn | RedshiftProxy | Reference | aiAreaLight | aiSkyDome | ...|
|  +-----------------------------------------------------------------------+|
|                                                                           |
+===========================================================================+
```

### 1.2 Design Principles

| Principle | Description |
|-----------|-------------|
| Network Nodes | All CTX nodes are Maya network nodes (no custom plugins required) |
| Message Connections | Nodes linked via message attributes for relationships |
| Scene Persistence | All data stored in Maya scene file |
| Sparse Storage | Only store overrides and changes, not all data |
| Consistent API | Similar patterns across Asset and Light systems |

---

## 2. Node Type Summary

### 2.1 All Custom Nodes

| Node Type | Purpose | Count per Scene |
|-----------|---------|-----------------|
| CTX_Manager | Central controller, stores active context | 1 |
| CTX_Shot | Shot container, links assets and lights | N (one per shot) |
| CTX_Asset | Asset data per shot (proxy, reference) | N x M (shots x assets) |
| CTX_LightGaffer | Light container for scope (Master/Seq/Shot) | 1 + S + N (Master + Seqs + Shots) |
| CTX_LightContext | Light data within gaffer | Variable (sparse) |

### 2.2 Node Hierarchy

```
CTX_Manager (1)
|
+-- CTX_Shot (N)
|   |
|   +-- CTX_Asset (per shot, per asset)
|   |
|   +-- CTX_LightGaffer_Shot (per shot)
|       |
|       +-- CTX_LightContext (sparse)
|
+-- CTX_LightGaffer_Master (1)
|   |
|   +-- CTX_LightContext (all lights)
|
+-- CTX_LightGaffer_Seq (per sequence)
    |
    +-- CTX_LightContext (sparse)
```

### 2.3 Associated Maya Nodes

| CTX Node | Associated Maya Nodes |
|----------|----------------------|
| CTX_Shot | displayLayer (CTX_{shot_code}) |
| CTX_Asset | aiStandIn, RedshiftProxyMesh, reference |
| CTX_LightContext | aiAreaLight, aiSkyDomeLight, RedshiftPhysicalLight, etc. |

---

## 3. CTX_Manager Node

### 3.1 Purpose

Central controller for the context system. Stores project/episode/sequence/shot context and manages active state.

### 3.2 Node Name

```
CTX_Manager
```

Only one per scene.

### 3.3 Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| ctxVersion | string | "1.0" | System version for compatibility |
| project | string | "" | Project code (e.g., "SWA") |
| episode | string | "" | Episode code (e.g., "Ep04") |
| sequence | string | "" | Active sequence code (e.g., "sq0070") |
| activeShot | string | "" | Active shot code (e.g., "SH0010") |
| activeShotIndex | int | 0 | Index of active shot in list |
| configPath | string | "" | Path to project config file |
| autoApplyTransform | bool | false | Auto-apply light transform on shot switch |

### 3.4 Message Connections

| Attribute | Direction | Connected To |
|-----------|-----------|--------------|
| shots | outgoing | CTX_Shot nodes |
| masterGaffer | outgoing | CTX_LightGaffer_Master |
| seqGaffers | outgoing | CTX_LightGaffer_Seq_* nodes |

### 3.5 Attribute Definitions

```python
MANAGER_ATTRS = {
    "ctxVersion": {"type": "string", "default": "1.0"},
    "project": {"type": "string", "default": ""},
    "episode": {"type": "string", "default": ""},
    "sequence": {"type": "string", "default": ""},
    "activeShot": {"type": "string", "default": ""},
    "activeShotIndex": {"type": "long", "default": 0},
    "configPath": {"type": "string", "default": ""},
    "autoApplyTransform": {"type": "bool", "default": False},
}
```

---

## 4. CTX_Shot Node

### 4.1 Purpose

Container for shot-specific data. Links to assets and light gaffer for this shot.

### 4.2 Node Name Pattern

```
CTX_Shot_{shot_code}

Examples:
CTX_Shot_SH0010
CTX_Shot_SH0020
CTX_Shot_SH0030
```

### 4.3 Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| shotCode | string | "" | Shot code (e.g., "SH0010") |
| shotIndex | int | 0 | Index in shot list |
| frameStart | int | 1001 | Start frame |
| frameEnd | int | 1100 | End frame |
| displayLayer | string | "" | Associated display layer name |
| sequenceCode | string | "" | Parent sequence code |

### 4.4 Message Connections

| Attribute | Direction | Connected To |
|-----------|-----------|--------------|
| parentManager | incoming | CTX_Manager |
| assets | outgoing | CTX_Asset nodes |
| lightGaffer | outgoing | CTX_LightGaffer_Shot_* |

### 4.5 Attribute Definitions

```python
SHOT_ATTRS = {
    "shotCode": {"type": "string", "default": ""},
    "shotIndex": {"type": "long", "default": 0},
    "frameStart": {"type": "long", "default": 1001},
    "frameEnd": {"type": "long", "default": 1100},
    "displayLayer": {"type": "string", "default": ""},
    "sequenceCode": {"type": "string", "default": ""},
}
```

---

## 5. CTX_Asset Node

### 5.1 Purpose

Stores asset data (path template, version) for a specific shot. Links to actual Maya node (proxy, reference).

### 5.2 Node Name Pattern

```
CTX_Asset_{asset_type}_{asset_name}_{variant}_{shot_code}

Examples:
CTX_Asset_CHAR_CatStompie_001_SH0010
CTX_Asset_CHAR_CatStompie_001_SH0020
CTX_Asset_PROP_TreeBig_001_SH0010
```

### 5.3 Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| assetName | string | "" | Asset name (e.g., "CatStompie") |
| assetType | string | "" | Asset type (e.g., "CHAR", "PROP") |
| variant | string | "001" | Instance index |
| department | string | "" | Source department (e.g., "anim") |
| version | string | "v001" | Asset version |
| template | string | "" | Path template with tokens |
| extension | string | "abc" | File extension |
| nodeType | string | "" | Target node type |
| enabled | bool | true | Whether asset is active |

### 5.4 Message Connections

| Attribute | Direction | Connected To |
|-----------|-----------|--------------|
| parentShot | incoming | CTX_Shot |
| targetNode | outgoing | Actual Maya node (aiStandIn, etc.) |

### 5.5 Attribute Definitions

```python
ASSET_ATTRS = {
    "assetName": {"type": "string", "default": ""},
    "assetType": {"type": "string", "default": ""},
    "variant": {"type": "string", "default": "001"},
    "department": {"type": "string", "default": ""},
    "version": {"type": "string", "default": "v001"},
    "template": {"type": "string", "default": ""},
    "extension": {"type": "string", "default": "abc"},
    "nodeType": {"type": "string", "default": ""},
    "enabled": {"type": "bool", "default": True},
}
```

### 5.6 Supported Target Node Types

| nodeType Value | Maya Node Type | Path Attribute |
|----------------|----------------|----------------|
| aiStandIn | aiStandIn | dso |
| RedshiftProxyMesh | RedshiftProxyMesh | fileName |
| reference | reference | (Maya API) |

---

## 6. CTX_LightGaffer Node

### 6.1 Purpose

Container for light contexts at a specific scope (Master, Sequence, or Shot).

### 6.2 Node Name Pattern

```
CTX_LightGaffer_{scope}
CTX_LightGaffer_Seq_{seq_code}
CTX_LightGaffer_Shot_{shot_code}

Examples:
CTX_LightGaffer_Master
CTX_LightGaffer_Seq_sq0070
CTX_LightGaffer_Shot_SH0010
```

### 6.3 Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| gafferType | string | "master" | "master", "seq", or "shot" |
| gafferName | string | "" | Display name |
| scopeCode | string | "" | Sequence or shot code |
| enabled | bool | true | Whether gaffer is active |

### 6.4 Message Connections

| Attribute | Direction | Connected To |
|-----------|-----------|--------------|
| parentManager | incoming | CTX_Manager (for Master) |
| parentShot | incoming | CTX_Shot (for Shot gaffer) |
| parentGaffer | incoming | Parent gaffer (for inheritance) |
| lights | outgoing | CTX_LightContext nodes |

### 6.5 Attribute Definitions

```python
GAFFER_ATTRS = {
    "gafferType": {"type": "string", "default": "master"},
    "gafferName": {"type": "string", "default": ""},
    "scopeCode": {"type": "string", "default": ""},
    "enabled": {"type": "bool", "default": True},
}
```

### 6.6 Gaffer Hierarchy

```
CTX_LightGaffer_Master (base)
        ^
        | parentGaffer
        |
CTX_LightGaffer_Seq_sq0070 (inherits from Master)
        ^
        | parentGaffer
        |
CTX_LightGaffer_Shot_SH0010 (inherits from Seq)
```

---

## 7. CTX_LightContext Node

### 7.1 Purpose

Stores light attribute values for a single light within a gaffer. Sparse storage - only stores enabled overrides.

### 7.2 Node Name Pattern

```
CTX_LightContext_{light_name}_{scope}

Examples:
CTX_LightContext_keyLight1_Master
CTX_LightContext_keyLight1_sq0070
CTX_LightContext_keyLight1_SH0010
CTX_LightContext_fillLight1_Master
CTX_LightContext_skyDome_SH0020
```

### 7.3 Attributes

**Identity Attributes:**

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| lightName | string | "" | Light identifier |

**State Attributes:**

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| muted | bool | false | Disable light |
| mutedEnabled | bool | false | Override flag |

**Property Attributes:**

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| intensity | float | 1.0 | Light intensity |
| intensityEnabled | bool | false | Override flag |
| exposure | float | 0.0 | Exposure |
| exposureEnabled | bool | false | Override flag |
| colorR | float | 1.0 | Color red |
| colorG | float | 1.0 | Color green |
| colorB | float | 1.0 | Color blue |
| colorEnabled | bool | false | Override flag |
| temperature | float | 6500.0 | Color temperature |
| temperatureEnabled | bool | false | Override flag |
| samples | int | 1 | Render samples |
| samplesEnabled | bool | false | Override flag |

**Contribution Attributes:**

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| camera | float | 1.0 | Camera contribution |
| cameraEnabled | bool | false | Override flag |
| diffuse | float | 1.0 | Diffuse contribution |
| diffuseEnabled | bool | false | Override flag |
| specular | float | 1.0 | Specular contribution |
| specularEnabled | bool | false | Override flag |
| sss | float | 1.0 | SSS contribution |
| sssEnabled | bool | false | Override flag |
| indirect | float | 1.0 | Indirect contribution |
| indirectEnabled | bool | false | Override flag |
| volume | float | 1.0 | Volume contribution |
| volumeEnabled | bool | false | Override flag |

**Transform Attributes:**

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| translateX | float | 0.0 | Position X |
| translateY | float | 0.0 | Position Y |
| translateZ | float | 0.0 | Position Z |
| rotateX | float | 0.0 | Rotation X |
| rotateY | float | 0.0 | Rotation Y |
| rotateZ | float | 0.0 | Rotation Z |
| scaleX | float | 1.0 | Scale X |
| scaleY | float | 1.0 | Scale Y |
| scaleZ | float | 1.0 | Scale Z |
| transformEnabled | bool | false | Override flag |

### 7.4 Message Connections

| Attribute | Direction | Connected To |
|-----------|-----------|--------------|
| parentGaffer | incoming | CTX_LightGaffer |
| targetLight | outgoing | Actual Maya light shape |

### 7.5 Attribute Definitions

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
    "samples": {"type": "long", "default": 1},
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

## 8. Display Layer Integration

### 8.1 Purpose

Display layers control asset visibility per shot. Each shot has an associated display layer.

### 8.2 Naming Convention

```
CTX_{shot_code}

Examples:
CTX_SH0010
CTX_SH0020
CTX_SH0030
```

### 8.3 Display Layer Attributes

| Attribute | Value | Description |
|-----------|-------|-------------|
| displayType | 0 | Normal display |
| visibility | 0 or 1 | Controlled by shot activation |
| hideOnPlayback | 0 | Show during playback |
| texturing | 1 | Enable textures |

### 8.4 Visibility Logic

```
When shot SH0020 is active:

CTX_SH0010.visibility = 0 (hidden)
CTX_SH0020.visibility = 1 (visible)
CTX_SH0030.visibility = 0 (hidden)
```

### 8.5 Asset Layer Assignment

```
Asset CatStompie_001:
- Exists in SH0010, SH0020, SH0030
- Added to: CTX_SH0010, CTX_SH0020, CTX_SH0030

Asset TreeBig_001:
- Exists only in SH0020
- Added to: CTX_SH0020 only
```

---

## 9. Node Relationships

### 9.1 Message Connection Diagram

```
CTX_Manager
|
+-- [shots] -----------------> CTX_Shot_SH0010
|                              |
|                              +-- [assets] ---------> CTX_Asset_CHAR_CatStompie_001_SH0010
|                              |                       |
|                              |                       +-- [targetNode] --> aiStandIn1
|                              |
|                              +-- [lightGaffer] ----> CTX_LightGaffer_Shot_SH0010
|                                                      |
|                                                      +-- [lights] --> CTX_LightContext_keyLight1_SH0010
|                                                                       |
|                                                                       +-- [targetLight] --> aiAreaLight1
|
+-- [masterGaffer] ----------> CTX_LightGaffer_Master
|                              |
|                              +-- [lights] ---------> CTX_LightContext_keyLight1_Master
|                              |                       |
|                              |                       +-- [targetLight] --> aiAreaLight1
|                              |
|                              +-- [lights] ---------> CTX_LightContext_fillLight1_Master
|                                                      |
|                                                      +-- [targetLight] --> aiAreaLight2
|
+-- [seqGaffers] ------------> CTX_LightGaffer_Seq_sq0070
                               |
                               +-- [parentGaffer] --> CTX_LightGaffer_Master
                               |
                               +-- [lights] --------> CTX_LightContext_keyLight1_sq0070
```

### 9.2 Shared Node Concept

Multiple CTX nodes can reference the same Maya node:

```
aiAreaLight1 (actual light)
    ^
    |
    +-- CTX_LightContext_keyLight1_Master (base values)
    +-- CTX_LightContext_keyLight1_sq0070 (seq override)
    +-- CTX_LightContext_keyLight1_SH0010 (shot override)
    +-- CTX_LightContext_keyLight1_SH0020 (shot override)


aiStandIn1 (actual proxy)
    ^
    |
    +-- CTX_Asset_CHAR_CatStompie_001_SH0010 (shot data)
    +-- CTX_Asset_CHAR_CatStompie_001_SH0020 (shot data)
    +-- CTX_Asset_CHAR_CatStompie_001_SH0030 (shot data)
```

---

## 10. Complete Scene Example

### 10.1 Scenario

- Project: SWA
- Episode: Ep04
- Sequence: sq0070
- Shots: SH0010, SH0020
- Assets: CatStompie_001, TreeBig_001
- Lights: keyLight1, fillLight1, skyDome

### 10.2 Full Node Graph

```
+===========================================================================+
|  MAYA SCENE                                                               |
+===========================================================================+

CTX_Manager
|-- ctxVersion: "1.0"
|-- project: "SWA"
|-- episode: "Ep04"
|-- sequence: "sq0070"
|-- activeShot: "SH0010"
|-- activeShotIndex: 0
|
|-- [shots] --> CTX_Shot_SH0010
|               |-- shotCode: "SH0010"
|               |-- shotIndex: 0
|               |-- frameStart: 1001
|               |-- frameEnd: 1050
|               |-- displayLayer: "CTX_SH0010"
|               |
|               |-- [assets] --> CTX_Asset_CHAR_CatStompie_001_SH0010
|               |                |-- assetName: "CatStompie"
|               |                |-- assetType: "CHAR"
|               |                |-- variant: "001"
|               |                |-- version: "v003"
|               |                |-- template: "$root/.../SH0010/...abc"
|               |                |-- [targetNode] --> aiStandIn1
|               |
|               |-- [assets] --> CTX_Asset_PROP_TreeBig_001_SH0010
|               |                |-- assetName: "TreeBig"
|               |                |-- version: "v001"
|               |                |-- [targetNode] --> aiStandIn2
|               |
|               |-- [lightGaffer] --> CTX_LightGaffer_Shot_SH0010
|                                     |-- gafferType: "shot"
|                                     |-- [parentGaffer] --> CTX_LightGaffer_Seq_sq0070
|                                     |
|                                     |-- [lights] --> CTX_LightContext_keyLight1_SH0010
|                                                      |-- intensity: 1.2
|                                                      |-- intensityEnabled: true
|                                                      |-- [targetLight] --> aiAreaLight1
|
|-- [shots] --> CTX_Shot_SH0020
|               |-- shotCode: "SH0020"
|               |-- shotIndex: 1
|               |-- frameStart: 1001
|               |-- frameEnd: 1080
|               |-- displayLayer: "CTX_SH0020"
|               |
|               |-- [assets] --> CTX_Asset_CHAR_CatStompie_001_SH0020
|               |                |-- version: "v004"  <-- different version!
|               |                |-- [targetNode] --> aiStandIn1  <-- same node!
|               |
|               |-- [lightGaffer] --> CTX_LightGaffer_Shot_SH0020
|                                     |-- [lights] --> CTX_LightContext_keyLight1_SH0020
|                                     |                |-- intensity: 1.5
|                                     |                |-- exposure: 0.3
|                                     |
|                                     |-- [lights] --> CTX_LightContext_fillLight1_SH0020
|                                                      |-- muted: true
|                                                      |-- mutedEnabled: true
|
|-- [masterGaffer] --> CTX_LightGaffer_Master
|                      |-- gafferType: "master"
|                      |
|                      |-- [lights] --> CTX_LightContext_keyLight1_Master
|                      |                |-- intensity: 1.0
|                      |                |-- intensityEnabled: true
|                      |                |-- exposure: 0.0
|                      |                |-- exposureEnabled: true
|                      |                |-- [targetLight] --> aiAreaLight1
|                      |
|                      |-- [lights] --> CTX_LightContext_fillLight1_Master
|                      |                |-- intensity: 0.5
|                      |                |-- [targetLight] --> aiAreaLight2
|                      |
|                      |-- [lights] --> CTX_LightContext_skyDome_Master
|                                       |-- intensity: 1.0
|                                       |-- [targetLight] --> aiSkyDomeLight1
|
|-- [seqGaffers] --> CTX_LightGaffer_Seq_sq0070
                     |-- gafferType: "seq"
                     |-- scopeCode: "sq0070"
                     |-- [parentGaffer] --> CTX_LightGaffer_Master
                     |
                     |-- [lights] --> CTX_LightContext_keyLight1_sq0070
                                      |-- colorR: 0.8
                                      |-- colorG: 0.85
                                      |-- colorB: 1.0
                                      |-- colorEnabled: true


+-- DISPLAY LAYERS --+

CTX_SH0010 (displayLayer)
|-- visibility: 1  <-- active shot
|-- members: aiStandIn1, aiStandIn2

CTX_SH0020 (displayLayer)
|-- visibility: 0  <-- inactive
|-- members: aiStandIn1


+-- MAYA OBJECTS --+

aiStandIn1 (CatStompie_001)
|-- dso: "V:/SWA/.../SH0010/.../CatStompie_001.abc"

aiStandIn2 (TreeBig_001)
|-- dso: "V:/SWA/.../SH0010/.../TreeBig_001.abc"

aiAreaLight1 (keyLight1)
|-- intensity: 1.2  <-- from Shot gaffer
|-- color: (0.8, 0.85, 1.0)  <-- from Seq gaffer

aiAreaLight2 (fillLight1)
|-- intensity: 0.5  <-- from Master gaffer

aiSkyDomeLight1 (skyDome)
|-- intensity: 1.0  <-- from Master gaffer
```

---

## 11. Naming Conventions

### 11.1 Node Naming Summary

| Node Type | Pattern | Example |
|-----------|---------|---------|
| Manager | CTX_Manager | CTX_Manager |
| Shot | CTX_Shot_{shot} | CTX_Shot_SH0010 |
| Asset | CTX_Asset_{type}_{name}_{var}_{shot} | CTX_Asset_CHAR_CatStompie_001_SH0010 |
| Light Gaffer | CTX_LightGaffer_{scope} | CTX_LightGaffer_Master |
| Light Gaffer (Seq) | CTX_LightGaffer_Seq_{seq} | CTX_LightGaffer_Seq_sq0070 |
| Light Gaffer (Shot) | CTX_LightGaffer_Shot_{shot} | CTX_LightGaffer_Shot_SH0010 |
| Light Context | CTX_LightContext_{light}_{scope} | CTX_LightContext_keyLight1_Master |
| Display Layer | CTX_{shot} | CTX_SH0010 |

### 11.2 Maya Object Naming (Created by System)

| Object Type | Pattern | Example |
|-------------|---------|---------|
| StandIn Transform | {name}_{variant} | CatStompie_001 |
| StandIn Shape | {name}_{variant}_AIS | CatStompie_001_AIS |
| RS Proxy Transform | {name}_{variant} | CatStompie_001 |
| RS Proxy Shape | {name}_{variant}_RSP | CatStompie_001_RSP |
| Reference | {name}_{variant}RN | CatStompie_001RN |

### 11.3 Attribute Naming Pattern

For paired value/enabled attributes:

```
{attribute}         - The value (e.g., intensity)
{attribute}Enabled  - Override flag (e.g., intensityEnabled)
```

---

## Document End