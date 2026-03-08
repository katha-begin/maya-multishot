# CTX Light Gaffer System - API Reference

**Version:** 1.0  
**Last Updated:** 2026-02-21

---

## Table of Contents

1. [GafferManager](#gaffermanager)
2. [AttributeResolver](#attributeresolver)
3. [LightOperations](#lightoperations)
4. [ChainOperations](#chainoperations)
5. [Node Wrappers](#node-wrappers)

---

## GafferManager

**Module:** `core.gaffer.manager`

High-level API for managing lights and overrides in gaffers.

### Methods

#### `add_light_to_gaffer(gaffer, light_shape, light_name=None, capture_values=True)`

Add a Maya light to a gaffer.

**Parameters:**
- `gaffer` (CTXLightGafferNode): Target gaffer
- `light_shape` (str): Maya light shape node name
- `light_name` (str, optional): Display name for the light
- `capture_values` (bool): Whether to capture current Maya values (default: True)

**Returns:** `CTXLightContextNode` - Created light context

**Example:**
```python
from core.gaffer.manager import GafferManager
from core.nodes.wrappers.gaffer import CTXLightGafferNode

gaffer = CTXLightGafferNode('CTX_LightGaffer_Master')
light_ctx = GafferManager.add_light_to_gaffer(
    gaffer, 
    'keyLight1Shape',
    light_name='Key Light',
    capture_values=True
)
```

---

#### `remove_light_from_gaffer(gaffer, light_name)`

Remove a light from a gaffer.

**Parameters:**
- `gaffer` (CTXLightGafferNode): Target gaffer
- `light_name` (str): Light name to remove

**Returns:** `bool` - True if removed successfully

**Example:**
```python
GafferManager.remove_light_from_gaffer(gaffer, 'keyLight1')
```

---

#### `add_override_to_gaffer(gaffer, light_name, attribute, value)`

Add or update an attribute override for a light.

**Parameters:**
- `gaffer` (CTXLightGafferNode): Target gaffer
- `light_name` (str): Light name
- `attribute` (str): Attribute name (e.g., 'intensity', 'exposure')
- `value` (float/tuple): Attribute value

**Returns:** `bool` - True if override added successfully

**Supported Attributes:**
- `intensity` (float)
- `exposure` (float)
- `color` (tuple: R, G, B)
- `temperature` (float)
- `muted` (bool)
- `translate` (tuple: X, Y, Z)
- `rotate` (tuple: X, Y, Z)

**Example:**
```python
# Set intensity override
GafferManager.add_override_to_gaffer(shot_gaffer, 'keyLight1', 'intensity', 1.5)

# Set color override
GafferManager.add_override_to_gaffer(shot_gaffer, 'keyLight1', 'color', (1.0, 0.8, 0.6))
```

---

#### `get_lights_in_gaffer(gaffer, include_inherited=True)`

Get all lights in a gaffer.

**Parameters:**
- `gaffer` (CTXLightGafferNode): Target gaffer
- `include_inherited` (bool): Include lights from parent gaffers (default: True)

**Returns:** `list[CTXLightContextNode]` - List of light contexts

**Example:**
```python
# Get only direct lights
direct_lights = GafferManager.get_lights_in_gaffer(gaffer, include_inherited=False)

# Get all lights (including inherited)
all_lights = GafferManager.get_lights_in_gaffer(gaffer, include_inherited=True)
```

---

#### `capture_light_values(light_ctx)`

Capture current Maya light values into light context.

**Parameters:**
- `light_ctx` (CTXLightContextNode): Light context to update

**Returns:** `dict` - Captured values

**Example:**
```python
values = GafferManager.capture_light_values(light_ctx)
# Returns: {'intensity': 1.5, 'exposure': 0.0, 'color': (1, 1, 1), ...}
```

---

## AttributeResolver

**Module:** `core.gaffer.resolver`

Resolve attribute values by walking the gaffer chain.

### Methods

#### `resolve_attribute(gaffer, light_name, attribute)`

Resolve a single attribute value for a light.

**Parameters:**
- `gaffer` (CTXLightGafferNode): Starting gaffer (usually child)
- `light_name` (str): Light name
- `attribute` (str): Attribute name

**Returns:** `tuple` - (value, source_gaffer_name) or (None, None) if not found

**Example:**
```python
from core.gaffer.resolver import AttributeResolver

# Resolve intensity for keyLight1 in shot gaffer
value, source = AttributeResolver.resolve_attribute(
    shot_gaffer, 
    'keyLight1', 
    'intensity'
)

if value is not None:
    print(f"Intensity: {value} (from {source})")
```

---

#### `resolve_all_attributes(gaffer, light_name)`

Resolve all attributes for a light.

**Parameters:**
- `gaffer` (CTXLightGafferNode): Starting gaffer
- `light_name` (str): Light name

**Returns:** `dict` - Attribute values with sources

**Example:**
```python
resolved = AttributeResolver.resolve_all_attributes(shot_gaffer, 'keyLight1')
# Returns:
# {
#     'intensity': {'value': 1.5, 'source': 'Shot SH0010'},
#     'exposure': {'value': 0.0, 'source': 'Seq sq0070'},
#     'color': {'value': (1, 1, 1), 'source': 'Master'},
#     ...
# }
```

---

#### `get_attribute_source(gaffer, light_name, attribute)`

Get the source gaffer for an attribute.

**Parameters:**
- `gaffer` (CTXLightGafferNode): Starting gaffer
- `light_name` (str): Light name
- `attribute` (str): Attribute name

**Returns:** `str` - Source gaffer name or None

**Example:**
```python
source = AttributeResolver.get_attribute_source(shot_gaffer, 'keyLight1', 'intensity')
print(f"Intensity comes from: {source}")
```

---

## LightOperations

**Module:** `core.gaffer.light_ops`

Apply gaffer values to Maya lights and sync from Maya.

### Methods

#### `apply_gaffer_to_light(gaffer, light_name)`

Apply resolved gaffer values to a Maya light.

**Parameters:**
- `gaffer` (CTXLightGafferNode): Source gaffer
- `light_name` (str): Light name

**Returns:** `bool` - True if applied successfully

**Example:**
```python
from core.gaffer.light_ops import LightOperations

# Apply shot gaffer values to keyLight1
LightOperations.apply_gaffer_to_light(shot_gaffer, 'keyLight1')
```

---

#### `apply_gaffer_to_all_lights(gaffer)`

Apply gaffer values to all lights in the gaffer.

**Parameters:**
- `gaffer` (CTXLightGafferNode): Source gaffer

**Returns:** `dict` - Results with success/failure counts

**Example:**
```python
results = LightOperations.apply_gaffer_to_all_lights(shot_gaffer)
print(f"Applied: {results['success']}, Failed: {results['failed']}")
```

---

#### `sync_light_from_maya(light_ctx)`

Sync light context values from Maya scene.

**Parameters:**
- `light_ctx` (CTXLightContextNode): Light context to sync

**Returns:** `bool` - True if synced successfully

**Example:**
```python
# Capture current Maya values into light context
LightOperations.sync_light_from_maya(light_ctx)
```

---

## ChainOperations

**Module:** `core.gaffer.chain_ops`

Build and manage gaffer chains.

### Methods

#### `build_gaffer_chain(master_name, sequence_name=None, shot_name=None)`

Build a complete gaffer chain.

**Parameters:**
- `master_name` (str): Master gaffer name
- `sequence_name` (str, optional): Sequence gaffer name
- `shot_name` (str, optional): Shot gaffer name

**Returns:** `dict` - Created gaffers

**Example:**
```python
from core.gaffer.chain_ops import ChainOperations

chain = ChainOperations.build_gaffer_chain(
    master_name='Master',
    sequence_name='sq0070',
    shot_name='SH0010'
)

master = chain['master']
sequence = chain['sequence']
shot = chain['shot']
```

---

**Next:** [Gaffer UI Guide](gaffer_ui_guide.md)

