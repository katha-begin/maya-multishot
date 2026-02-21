# CTX Tools - Quick Reference Card

**Version:** 1.0  
**Branch:** `feature/gaffer-system`

---

## Installation (One-Time Setup)

```python
# In Maya Script Editor (Python tab)
import sys
sys.path.append(r'E:/dev/maya-multishot')  # Update to your path

from tools import maya_menu
maya_menu.create_ctx_menu()
```

**Result:** "CTX Tools" menu appears in Maya's main menu bar

---

## Menu Access

**Location:** Maya Main Menu Bar → **CTX Tools**

**Menu Items:**
- Context Manager - Multi-shot management
- Gaffer Manager - Light management
- Asset Manager - Asset management
- Reload Menu - Reload menu (development)
- About - About CTX Tools

---

## Context Manager Quick Start

### Open
**Menu:** CTX Tools → Context Manager

### Create Shot
1. Click "Add Shots" button
2. Enter shot codes (e.g., SH0010, SH0020)
3. Click "Add"

### View Shots
- All shots appear in table
- Use search box to filter

---

## Gaffer Manager Quick Start

### Open
**Menu:** CTX Tools → Gaffer Manager

### Create Gaffer Chain
```python
# In Script Editor
from core.gaffer.chain_ops import ChainOperations

chain = ChainOperations.build_gaffer_chain(
    master_name='Master',
    sequence_name='sq0070',
    shot_name='SH0010'
)
```

### Add Light to Gaffer
1. Create light in Maya
2. Select gaffer from dropdown
3. Click "+ Add Light"
4. Select light
5. Click "Add Selected Lights"

### Create Override
1. Select child gaffer (e.g., Shot)
2. Click ">>" next to light
3. Type new value in override field
4. Click "Apply Changes"

### Apply to Scene
1. Click "Apply to Scene" button
2. All lights update in Maya

### Capture from Scene
1. Adjust lights in Maya
2. Click "Capture from Scene"
3. Values saved to gaffer

---

## Common Code Snippets

### Create Light
```python
import maya.cmds as cmds

# Create area light
light = cmds.shadingNode('aiAreaLight', asLight=True)
cmds.setAttr(light + '.intensity', 1.0)
cmds.setAttr(light + '.exposure', 0.0)
```

### Create Gaffer Chain
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

### Add Light to Gaffer
```python
from core.gaffer.manager import GafferManager

GafferManager.add_light_to_gaffer(
    master,
    'aiAreaLight1',
    light_name='Key Light',
    capture_values=True
)
```

### Create Override
```python
from core.gaffer.manager import GafferManager

GafferManager.add_override_to_gaffer(
    shot,
    'Key Light',
    'intensity',
    1.5
)
```

### Apply Gaffer to Scene
```python
from core.gaffer.light_ops import LightOperations

LightOperations.apply_gaffer_to_all_lights(shot)
```

### Resolve Attribute
```python
from core.gaffer.resolver import AttributeResolver

value, source = AttributeResolver.resolve_attribute(
    shot,
    'Key Light',
    'intensity'
)

print("Intensity: {} (from {})".format(value, source))
```

---

## Keyboard Shortcuts

**Context Manager:**
- Ctrl+F - Focus search box
- Delete - Delete selected shot

**Gaffer Manager:**
- F5 - Refresh gaffer list
- Ctrl+A - Select all lights

**Light Editor:**
- Ctrl+S - Apply changes
- Esc - Close panel

---

## Troubleshooting

### Menu Not Appearing
```python
# Check path
import os
path = r'E:/dev/maya-multishot'
print(os.path.exists(path))  # Should be True

# Recreate menu
from tools import maya_menu
maya_menu.remove_ctx_menu()
maya_menu.create_ctx_menu()
```

### Import Errors
```python
# Verify import
import sys
sys.path.append(r'E:/dev/maya-multishot')

try:
    from tools import maya_menu
    print("Import successful!")
except ImportError as e:
    print("Import failed: {}".format(e))
```

### Check Gaffer Exists
```python
import maya.cmds as cmds

# List all gaffers
gaffers = cmds.ls(type='network')
gaffer_nodes = [n for n in gaffers if 'CTX_LightGaffer' in n]
print("Gaffers: {}".format(gaffer_nodes))
```

### Check Light Context
```python
# List all light contexts
contexts = cmds.ls(type='network')
light_contexts = [n for n in contexts if 'CTX_LightContext' in n]
print("Light Contexts: {}".format(light_contexts))
```

---

## File Locations

**Installation:**
- Repository: `E:/dev/maya-multishot`
- Branch: `feature/gaffer-system`

**Documentation:**
- Installation: `docs/INSTALLATION.md`
- Testing Guide: `docs/TESTING_GUIDE.md`
- Gaffer Overview: `docs/gaffer_system_overview.md`
- API Reference: `docs/gaffer_api_reference.md`
- UI Guide: `docs/gaffer_ui_guide.md`
- Workflows: `docs/gaffer_workflows.md`

**Examples:**
- userSetup.py: `examples/userSetup.py`

---

## Support

**Documentation:** See `docs/` folder  
**Repository:** https://github.com/katha-begin/maya-multishot  
**Issues:** Report on GitHub Issues

---

**Quick Reference v1.0** | CTX Tools | 2026-02-21

