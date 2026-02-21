# CTX Light Gaffer System - UI Guide

**Version:** 1.0  
**Last Updated:** 2026-02-21

---

## Table of Contents

1. [Opening the Gaffer Manager](#opening-the-gaffer-manager)
2. [Gaffer Manager Dialog](#gaffer-manager-dialog)
3. [Light Editor Panel](#light-editor-panel)
4. [Add Light Dialog](#add-light-dialog)
5. [Common Workflows](#common-workflows)

---

## Opening the Gaffer Manager

### Method 1: From Main Window

1. Open the CTX Main Window
2. Click **Tools** menu
3. Select **Gaffer Manager**

### Method 2: Python Script

```python
from ui.gaffer_manager_dialog import GafferManagerDialog

dialog = GafferManagerDialog()
dialog.show()
```

---

## Gaffer Manager Dialog

The main interface for managing light gaffers.

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Gaffer Manager                                         [X]  │
├─────────────────────────────────────────────────────────────┤
│ Select Gaffer: [Master ▼] [Refresh]                        │
│ Chain: Master                                               │
├─────────────────────────────────────────────────────────────┤
│ Lights in Gaffer                                            │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Light    │Mute│Int │Exp │Color  │Source │Sel│Details  │ │
│ ├──────────┼────┼────┼────┼───────┼───────┼───┼─────────┤ │
│ │keyLight1 │ No │1.5 │0.0 │1,1,1  │Master │[S]│  [>>]  │ │
│ │fillLight │ No │0.8 │0.0 │1,1,1  │Master │[S]│  [>>]  │ │
│ └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ [+ Add Light] [- Remove Light] [Apply to Scene] [Capture]  │
└─────────────────────────────────────────────────────────────┘
```

### Components

#### 1. Gaffer Selection

**Dropdown:** Select which gaffer to view/edit
- Groups gaffers by type (Master, Seq, Shot, Custom)
- Shows gaffer name and type

**Refresh Button:** Reload gaffer list from scene

**Chain Display:** Shows inheritance chain
- Example: "Shot SH0010 → Seq sq0070 → Master"

#### 2. Lights Table

Displays all lights in the selected gaffer with resolved values.

**Columns:**
- **Light**: Light name (from CTX_LightContext)
- **Mute**: Mute status (Yes/No)
- **Intensity**: Resolved intensity value
- **Exposure**: Resolved exposure value
- **Color**: Resolved color (R,G,B)
- **Source**: Which gaffer provides the value
- **Select**: Button to select light in Maya viewport
- **Details**: Button to open Light Editor Panel

**Color Coding:**
- **Bold**: Value is overridden in current gaffer
- **Normal**: Value is inherited from parent

#### 3. Action Buttons

**+ Add Light**
- Opens Add Light Dialog
- Select Maya lights to add to gaffer

**- Remove Light**
- Remove selected light from gaffer
- Confirmation dialog appears

**Apply to Scene**
- Apply all resolved values to Maya lights
- Updates all lights in the gaffer

**Capture from Scene**
- Capture current Maya values into gaffer
- Updates all light contexts

---

## Light Editor Panel

Detailed per-attribute editing for a single light.

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Light Editor - keyLight1                               [X]  │
├─────────────────────────────────────────────────────────────┤
│ Light Info                                                  │
│   Target Light: keyLight1Shape                              │
│   Light Type: aiAreaLight                                   │
│   Current Gaffer: Shot SH0010                               │
│   Chain: Shot SH0010 → Seq sq0070 → Master                 │
├─────────────────────────────────────────────────────────────┤
│ Light Attributes                                            │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Intensity                                               │ │
│ │   Override: [1.5    ] [✓] Enable                       │ │
│ │   Inherited: 1.0 (from Master)                          │ │
│ │                                                         │ │
│ │ Exposure                                                │ │
│ │   Override: [0.0    ] [ ] Enable                       │ │
│ │   Inherited: 0.0 (from Seq sq0070)                     │ │
│ │                                                         │ │
│ │ Color R                                                 │ │
│ │   Override: [1.0    ] [ ] Enable                       │ │
│ │   Inherited: 1.0 (from Master)                          │ │
│ └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ [Apply Changes] [Revert] [Capture Current] [Select Light]  │
└─────────────────────────────────────────────────────────────┘
```

### Components

#### 1. Light Info Section

Displays read-only information about the light:
- **Target Light**: Maya light shape node
- **Light Type**: Type of light (aiAreaLight, spotLight, etc.)
- **Current Gaffer**: Which gaffer you're editing
- **Chain**: Full inheritance chain

#### 2. Attributes Section

Scrollable area with all editable attributes.

**Per-Attribute Controls:**

**Override Field**
- Editable text field for the override value
- Auto-enables checkbox when you type

**Enable Checkbox**
- Check to enable override in current gaffer
- Uncheck to inherit from parent

**Inherited Value**
- Read-only display of inherited value
- Shows source gaffer name

**Attribute Groups:**

**Light Attributes:**
- intensity (float)
- exposure (float)
- colorR, colorG, colorB (float)
- temperature (float)
- muted (bool)

**Transform Attributes:**
- translateX, translateY, translateZ (float)
- rotateX, rotateY, rotateZ (float)

#### 3. Action Buttons

**Apply Changes**
- Save overrides to gaffer
- Apply to Maya light

**Revert**
- Discard unsaved changes
- Reload from gaffer

**Capture Current**
- Capture current Maya values
- Update override fields

**Select Light in Maya**
- Select the light in Maya viewport
- Useful for visual reference

---

## Add Light Dialog

Select Maya lights to add to a gaffer.

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Add Lights to Gaffer: Master                           [X]  │
├─────────────────────────────────────────────────────────────┤
│ Filter by type: [All Lights ▼] [Refresh]                   │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Light Name  │ Type         │ Intensity │ In Gaffer    │ │
│ ├─────────────┼──────────────┼───────────┼──────────────┤ │
│ │ keyLight1   │ aiAreaLight  │ 1.50      │ No           │ │
│ │ fillLight   │ aiAreaLight  │ 0.80      │ No           │ │
│ │ rimLight    │ spotLight    │ 2.00      │ Yes          │ │
│ └─────────────────────────────────────────────────────────┘ │
│ Select lights to add (Ctrl+Click for multiple)              │
├─────────────────────────────────────────────────────────────┤
│ [Select All] [Deselect All]  [Add Selected Lights] [Cancel]│
└─────────────────────────────────────────────────────────────┘
```

### Components

#### 1. Filter Section

**Filter Dropdown:** Filter lights by type
- All Lights
- Area Lights
- Spot Lights
- Point Lights
- Directional Lights
- Volume Lights

**Refresh Button:** Reload lights from scene

#### 2. Lights Table

**Columns:**
- **Light Name**: Maya light transform name
- **Type**: Light type
- **Intensity**: Current intensity value
- **Already in Gaffer**: Yes/No indicator

**Selection:**
- Click to select single light
- Ctrl+Click to select multiple lights
- Lights already in gaffer are grayed out

#### 3. Action Buttons

**Select All:** Select all available lights

**Deselect All:** Clear selection

**Add Selected Lights:** Add selected lights to gaffer

**Cancel:** Close dialog without adding

---

## Common Workflows

### Workflow 1: View Light Values

1. Open Gaffer Manager
2. Select gaffer from dropdown
3. View lights table with resolved values
4. Check "Source" column to see where values come from

### Workflow 2: Create Override

1. Open Gaffer Manager
2. Select child gaffer (e.g., Shot)
3. Click ">>" next to light
4. Light Editor opens
5. Type new value in override field
6. Checkbox auto-enables
7. Click "Apply Changes"
8. Override saved and applied

### Workflow 3: Add New Light

1. Create light in Maya
2. Open Gaffer Manager
3. Select gaffer
4. Click "+ Add Light"
5. Select light from list
6. Click "Add Selected Lights"
7. Light added with current values

### Workflow 4: Batch Apply

1. Adjust lights in Maya viewport
2. Open Gaffer Manager
3. Select gaffer
4. Click "Capture from Scene"
5. All values captured
6. Switch to child gaffer
7. Click "Apply to Scene"
8. Child gaffer values applied

---

**Next:** [Gaffer Workflows](gaffer_workflows.md)

