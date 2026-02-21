# CTX Light Gaffer System - Workflows

**Version:** 1.0  
**Last Updated:** 2026-02-21

---

## Table of Contents

1. [Setting Up a New Show](#setting-up-a-new-show)
2. [Creating Sequence Overrides](#creating-sequence-overrides)
3. [Creating Shot Overrides](#creating-shot-overrides)
4. [Batch Operations](#batch-operations)
5. [Troubleshooting](#troubleshooting)

---

## Setting Up a New Show

### Scenario

You're starting a new show and need to set up the master lighting rig that all shots will inherit from.

### Steps

#### 1. Create Master Gaffer

```python
from core.gaffer.chain_ops import ChainOperations

# Create master gaffer
chain = ChainOperations.build_gaffer_chain(master_name='Master')
master = chain['master']
```

Or use UI: Tools → Gaffer Manager → Gaffer will be created automatically

#### 2. Set Up Lighting in Maya

Create your lighting rig in Maya:
- Key light
- Fill light
- Rim light
- Environment light
- Any other lights

Position and adjust lights to your liking.

#### 3. Add Lights to Master Gaffer

**UI Method:**
1. Open Gaffer Manager
2. Select "Master" gaffer
3. Click "+ Add Light"
4. Select all lights
5. Click "Add Selected Lights"

**Python Method:**
```python
from core.gaffer.manager import GafferManager

lights = ['keyLight1Shape', 'fillLightShape', 'rimLightShape']
for light in lights:
    GafferManager.add_light_to_gaffer(master, light, capture_values=True)
```

#### 4. Verify Setup

1. Check lights table in Gaffer Manager
2. All lights should show with "Master" as source
3. Values should match Maya scene

**Result:** Master gaffer now contains your base lighting setup that all shots will inherit.

---

## Creating Sequence Overrides

### Scenario

Sequence sq0070 needs darker lighting than the master setup.

### Steps

#### 1. Create Sequence Gaffer

```python
from core.gaffer.chain_ops import ChainOperations

# Create sequence gaffer linked to master
chain = ChainOperations.build_gaffer_chain(
    master_name='Master',
    sequence_name='sq0070'
)

master = chain['master']
sequence = chain['sequence']
```

#### 2. View Inherited Lights

**UI Method:**
1. Open Gaffer Manager
2. Select "Seq: sq0070" from dropdown
3. View lights table
4. All lights show with "Master" as source (inherited)

#### 3. Create Intensity Override

**UI Method:**
1. Click ">>" next to "keyLight1"
2. Light Editor opens
3. In "Intensity" section:
   - Type "0.8" in Override field
   - Checkbox auto-enables
4. Click "Apply Changes"

**Python Method:**
```python
from core.gaffer.manager import GafferManager

# Reduce key light intensity for sequence
GafferManager.add_override_to_gaffer(sequence, 'keyLight1', 'intensity', 0.8)
```

#### 4. Apply to Scene

**UI Method:**
1. Click "Apply to Scene" in Gaffer Manager

**Python Method:**
```python
from core.gaffer.light_ops import LightOperations

LightOperations.apply_gaffer_to_all_lights(sequence)
```

#### 5. Verify Override

1. Check lights table
2. "keyLight1" intensity should show "0.8"
3. Source should show "Seq sq0070" (bold = overridden)
4. Other attributes still show "Master" (inherited)

**Result:** Sequence has darker key light, all other attributes inherited from master.

---

## Creating Shot Overrides

### Scenario

Shot SH0010 in sequence sq0070 needs a warmer color temperature.

### Steps

#### 1. Create Shot Gaffer

```python
from core.gaffer.chain_ops import ChainOperations

# Create complete chain
chain = ChainOperations.build_gaffer_chain(
    master_name='Master',
    sequence_name='sq0070',
    shot_name='SH0010'
)

master = chain['master']
sequence = chain['sequence']
shot = chain['shot']
```

#### 2. View Inheritance Chain

**UI Method:**
1. Select "Shot: SH0010" from dropdown
2. Chain display shows: "Shot SH0010 → Seq sq0070 → Master"
3. Lights table shows:
   - keyLight1 intensity: 0.8 (from Seq sq0070)
   - Other attributes: (from Master)

#### 3. Create Color Temperature Override

**UI Method:**
1. Click ">>" next to "keyLight1"
2. In "Temperature" section:
   - Type "4500" in Override field
   - Enable checkbox
3. Click "Apply Changes"

**Python Method:**
```python
from core.gaffer.manager import GafferManager

# Warmer color temperature for shot
GafferManager.add_override_to_gaffer(shot, 'keyLight1', 'temperature', 4500)
```

#### 4. Verify Complete Chain

Check lights table for "keyLight1":
- **Intensity**: 0.8 (from Seq sq0070) - inherited
- **Temperature**: 4500 (from Shot SH0010) - overridden
- **Color**: 1,1,1 (from Master) - inherited
- **Exposure**: 0.0 (from Master) - inherited

**Result:** Shot has warm key light with sequence intensity, all other attributes from master.

---

## Batch Operations

### Scenario 1: Apply Gaffer to Multiple Shots

You've updated the master gaffer and want to apply it to all shots.

```python
from core.gaffer.chain_ops import ChainOperations
from core.gaffer.light_ops import LightOperations

# Get all shot gaffers
all_gaffers = ChainOperations.list_all_gaffers()
shot_gaffers = [g for g in all_gaffers if g.get_gaffer_type() == 'Shot']

# Apply each shot gaffer to its lights
for shot_gaffer in shot_gaffers:
    results = LightOperations.apply_gaffer_to_all_lights(shot_gaffer)
    print(f"{shot_gaffer.get_gaffer_name()}: {results['success']} lights updated")
```

### Scenario 2: Capture Values from Multiple Lights

You've adjusted multiple lights in Maya and want to capture them all.

**UI Method:**
1. Open Gaffer Manager
2. Select gaffer
3. Click "Capture from Scene"
4. All lights captured at once

**Python Method:**
```python
from core.gaffer.manager import GafferManager
from core.gaffer.light_ops import LightOperations

# Get all lights in gaffer
lights = GafferManager.get_lights_in_gaffer(gaffer, include_inherited=False)

# Sync each light from Maya
for light_ctx in lights:
    LightOperations.sync_light_from_maya(light_ctx)
    print(f"Captured {light_ctx.get_light_name()}")
```

### Scenario 3: Copy Overrides Between Gaffers

Copy overrides from one shot to another.

```python
from core.gaffer.resolver import AttributeResolver
from core.gaffer.manager import GafferManager

source_gaffer = CTXLightGafferNode('CTX_LightGaffer_SH0010')
target_gaffer = CTXLightGafferNode('CTX_LightGaffer_SH0020')

# Get lights in source
lights = GafferManager.get_lights_in_gaffer(source_gaffer, include_inherited=False)

for light_ctx in lights:
    light_name = light_ctx.get_light_name()
    
    # Get enabled attributes
    enabled_attrs = light_ctx.get_enabled_attributes()
    
    # Copy each enabled attribute
    for attr in enabled_attrs:
        value = light_ctx.get_attribute_value(attr)
        GafferManager.add_override_to_gaffer(target_gaffer, light_name, attr, value)
    
    print(f"Copied {len(enabled_attrs)} overrides for {light_name}")
```

---

## Troubleshooting

### Issue 1: Light Not Updating in Maya

**Symptoms:** Changed value in gaffer but Maya light doesn't update

**Solutions:**
1. Click "Apply to Scene" in Gaffer Manager
2. Or use: `LightOperations.apply_gaffer_to_light(gaffer, light_name)`
3. Check if light exists in Maya scene
4. Check if light shape name is correct

### Issue 2: Override Not Taking Effect

**Symptoms:** Created override but still seeing inherited value

**Solutions:**
1. Check if enable checkbox is checked
2. Verify you're viewing the correct gaffer
3. Check chain display to confirm hierarchy
4. Use Light Editor to see which gaffer provides the value

### Issue 3: Light Not Appearing in Gaffer

**Symptoms:** Added light but it doesn't show in lights table

**Solutions:**
1. Click "Refresh" button in Gaffer Manager
2. Check if light was added to correct gaffer
3. Verify light exists in Maya scene
4. Check if `include_inherited` is set correctly

### Issue 4: Chain Not Resolving Correctly

**Symptoms:** Values coming from wrong gaffer in chain

**Solutions:**
1. Verify chain with: `gaffer.build_chain()`
2. Check parent connections: `gaffer.get_parent_gaffer()`
3. Validate chain: `ChainOperations.validate_chain(gaffer)`
4. Check for circular references

### Issue 5: Cannot Add Light to Gaffer

**Symptoms:** Error when trying to add light

**Solutions:**
1. Verify light exists: `cmds.objExists(light_shape)`
2. Check if light is already in gaffer
3. Verify gaffer is valid: `cmds.objExists(gaffer.node)`
4. Check Maya console for error messages

---

## Best Practices

### 1. Naming Conventions

- **Master Gaffer**: "Master" or "Global"
- **Sequence Gaffer**: "sq0070", "sq0080", etc.
- **Shot Gaffer**: "SH0010", "SH0020", etc.

### 2. Override Strategy

- Keep master gaffer as base setup
- Use sequence gaffers for sequence-wide changes
- Use shot gaffers only for shot-specific tweaks
- Minimize overrides to maintain consistency

### 3. Version Control

- Gaffer data is stored in Maya scene
- Save scene after making gaffer changes
- Use meaningful commit messages
- Document major lighting changes

### 4. Performance

- Apply gaffers only when needed
- Use batch operations for multiple shots
- Capture values before making changes
- Test on single shot before batch applying

---

**Related Documentation:**
- [Gaffer System Overview](gaffer_system_overview.md)
- [Gaffer API Reference](gaffer_api_reference.md)
- [Gaffer UI Guide](gaffer_ui_guide.md)

