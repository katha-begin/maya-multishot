# CTX Light Gaffer - UI Specification

**Version:** 1.0  
**Last Updated:** 2026-02-21  
**Status:** Design Specification  
**Related Docs:** [CTX_lightGaffer.md](CTX_lightGaffer.md), [CTX_lightGaffer_spec.md](CTX_lightGaffer_spec.md)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Gaffer Manager UI](#2-gaffer-manager-ui)
3. [Light Editor Panel](#3-light-editor-panel)
4. [Workflows](#4-workflows)
5. [UI Mockups](#5-ui-mockups)

---

## 1. Overview

### 1.1 Purpose

The Gaffer Manager UI provides artists with an intuitive interface to:
- Select which gaffer to view/edit (Master, Sequence, Shot)
- View all lights with their resolved values
- Add/remove lights from gaffers
- Create overrides in child gaffers
- Edit light attributes with immediate visual feedback

### 1.2 Key Features

✅ **Gaffer Selection Dropdown** - Choose Master/Seq/Shot gaffer  
✅ **Light List Table** - View all lights with source and override indicators  
✅ **User-Editable Values** - Direct editing in active shot creates overrides automatically  
✅ **Add/Remove Lights** - Convert existing Maya lights or remove from gaffer  
✅ **Light Editor Detail Panel** - Detailed attribute editing with inheritance visualization  
✅ **Follow Active Shot** - Auto-select shot gaffer when shot switches  

---

## 2. Gaffer Manager UI

### 2.1 Main Window Layout

```
+================================================================================+
|  LIGHT GAFFER MANAGER                                          [?] [Settings] |
+================================================================================+
|                                                                                |
|  GAFFER SELECTION                                                              |
|  +--------------------------------------------------------------------------+  |
|  | Select Gaffer: [Master ▼]                                                |  |
|  |                                                                          |  |
|  | Inheritance Chain: Master                                                |  |
|  +--------------------------------------------------------------------------+  |
|                                                                                |
|  LIGHTS IN GAFFER                                                              |
|  +--------+------+-------+--------+---------+---------+--------+-----------+  |
|  | Light  | Mute | Inten | Expose | Color   | Source  | Select | Details   |  |
|  +--------+------+-------+--------+---------+---------+--------+-----------+  |
|  | keyL1  |  -   | 1.0   |  0.0   | 1,1,1   | Master  | [Sel]  |   [>>]    |  |
|  | fillL1 |  -   | 0.8   |  0.0   | 1,1,1   | Master  | [Sel]  |   [>>]    |  |
|  | rimL_L |  -   | 1.0   |  0.0   | 1,1,1   | Master  | [Sel]  |   [>>]    |  |
|  | rimL_R |  -   | 1.0   |  0.0   | 1,1,1   | Master  | [Sel]  |   [>>]    |  |
|  | skyDm  |  -   | 1.0   | -0.5   | 1,1,1   | Master  | [Sel]  |   [>>]    |  |
|  +--------+------+-------+--------+---------+---------+--------+-----------+  |
|                                                                                |
|  [+ Add Light]  [- Remove Light]  [Apply to Scene]  [Capture from Scene]      |
|                                                                                |
+================================================================================+
```

### 2.2 Gaffer Selection Dropdown

**Options:**
- `Master` - Global gaffer (all shots inherit from this)
- `Seq: sq0070` - Sequence gaffer (all shots in sequence inherit)
- `Shot: SH0010` - Shot-specific gaffer (highest priority)
- `Shot: SH0020` - Another shot gaffer
- `Custom: myGaffer` - User-created custom gaffer

**Behavior:**
- Dropdown shows all available gaffers in the scene
- Selecting a gaffer updates the light list to show lights in that gaffer
- Inheritance chain is displayed below dropdown (e.g., "Shot SH0010 → Seq sq0070 → Master")

### 2.3 Light List Table

**Columns:**
- **Light** - Light name (from CTX_LightContext)
- **Mute** - Mute status (`-` = not muted, `MUTE` = muted)
- **Inten** - Intensity value (resolved from chain)
- **Expose** - Exposure value (resolved from chain)
- **Color** - Color value (R,G,B resolved from chain)
- **Source** - Which gaffer provides this value (Master/Seq/Shot)
- **Select** - Button to select light in Maya scene
- **Details** - Button to open Light Editor panel

**Visual Indicators:**
- **Bold text** - Value is overridden in current gaffer
- **Normal text** - Value is inherited from parent gaffer
- **Gray text** - Light is muted

**Example:**
```
| keyL1  |  -   | **1.5** |  0.0   | 1,1,1   | Shot    | [Sel]  |   [>>]    |
```
- `**1.5**` (bold) means intensity is overridden in Shot gaffer
- `0.0` (normal) means exposure is inherited from parent
- `Source: Shot` means the resolved value comes from Shot gaffer

### 2.4 Action Buttons

**[+ Add Light]**
- Opens dialog to select existing Maya lights
- Converts selected lights to CTX_LightContext nodes
- Captures current values from Maya light
- Adds to current gaffer

**[- Remove Light]**
- Removes selected light from current gaffer
- Deletes CTX_LightContext node
- Does NOT delete the Maya light itself

**[Apply to Scene]**
- Applies all resolved values to Maya lights
- Updates all lights in the scene based on gaffer chain

**[Capture from Scene]**
- Reads current values from Maya lights
- Updates CTX_LightContext nodes with current values
- Creates overrides in current gaffer

---

## 3. Light Editor Panel

### 3.1 Detailed Attribute Editor

```
+================================================================================+
|  LIGHT EDITOR: keyLight1                                               [Close] |
+================================================================================+
|                                                                                |
|  Target Light: aiAreaLight1                                                   |
|  Light Type: aiAreaLight                                                      |
|  Current Gaffer: Shot SH0010                                                  |
|  Inheritance Chain: Shot SH0010 → Seq sq0070 → Master                        |
|                                                                                |
+--------------------------------------------------------------------------------+
|                                                                                |
|  LIGHT ATTRIBUTES                                                             |
|  +-------------------------------------------------------------------------+  |
|  | Attribute      | Override  | Enable | Inherited | Source              |  |
|  +----------------|-----------|--------|-----------|---------------------|  |
|  | intensity      | [1.5____] |  [x]   | 1.0       | Master              |  |
|  | exposure       | [0.3____] |  [x]   | 0.0       | Master              |  |
|  | color R        | [_______] |  [ ]   | 1.0       | Master              |  |
|  | color G        | [_______] |  [ ]   | 1.0       | Master              |  |
|  | color B        | [_______] |  [ ]   | 1.0       | Master              |  |
|  | temperature    | [_______] |  [ ]   | 5500      | Master              |  |
|  | muted          | [_______] |  [ ]   | false     | Master              |  |
|  +-------------------------------------------------------------------------+  |
|                                                                                |
|  TRANSFORM                                                                    |
|  +-------------------------------------------------------------------------+  |
|  | Attribute      | Override  | Enable | Inherited | Source              |  |
|  +----------------|-----------|--------|-----------|---------------------|  |
|  | translateX     | [2.5____] |  [x]   | 0.0       | Master              |  |
|  | translateY     | [4.0____] |  [x]   | 5.0       | Master              |  |
|  | translateZ     | [3.0____] |  [x]   | 0.0       | Master              |  |
|  | rotateX        | [_______] |  [ ]   | -45.0     | Master              |  |
|  | rotateY        | [45.0___] |  [x]   | 0.0       | Master              |  |
|  | rotateZ        | [_______] |  [ ]   | 0.0       | Master              |  |
|  +-------------------------------------------------------------------------+  |
|                                                                                |
|  [Apply Changes]  [Revert]  [Capture Current]  [Select Light in Maya]        |
|                                                                                |
+================================================================================+
```

### 3.2 Attribute Editing Behavior

**Override Field:**
- Empty if not overridden in current gaffer
- Shows value if overridden in current gaffer
- Editing the field automatically checks the "Enable" checkbox

**Enable Checkbox:**
- Checked = This attribute is overridden in current gaffer
- Unchecked = This attribute is inherited from parent gaffer
- Checking the box enables the override (uses value from Override field)
- Unchecking the box disables the override (uses inherited value)

**Inherited Column:**
- Shows the value that would be used if override is disabled
- Read-only (for reference only)

**Source Column:**
- Shows which gaffer in the chain provides the inherited value
- Examples: "Master", "Seq sq0070", "Shot SH0010"

---

## 4. Workflows

### 4.1 Add Existing Maya Light to Gaffer

1. Open Gaffer Manager UI
2. Select gaffer (e.g., "Master")
3. Click **[+ Add Light]**
4. Select Maya light from scene (e.g., `aiAreaLight1`)
5. System creates `CTX_LightContext_areaLight1_Master`
6. System captures current values from Maya light
7. Light appears in light list table

### 4.2 Create Override in Shot Gaffer

1. Open Gaffer Manager UI
2. Select shot gaffer (e.g., "Shot: SH0010")
3. Select light in table (e.g., `keyL1`)
4. Click **[>>]** to open Light Editor
5. Edit attribute value (e.g., change intensity to 1.5)
6. System automatically checks "Enable" checkbox
7. Click **[Apply Changes]**
8. Override is created in Shot gaffer

### 4.3 Edit Values in Active Shot (Direct Editing)

1. Switch to shot (e.g., SH0010) in Multishot Manager
2. Open Gaffer Manager UI (auto-selects Shot: SH0010)
3. Edit values directly in Light Editor
4. System automatically creates overrides in shot gaffer
5. Changes are immediately visible in Maya viewport

### 4.4 Remove Override (Revert to Inherited)

1. Open Light Editor for a light
2. Uncheck "Enable" checkbox for attribute
3. Click **[Apply Changes]**
4. Override is removed, inherited value is used

---

## 5. UI Mockups

### 5.1 Gaffer Selection with Sequence Gaffer

```
+================================================================================+
|  LIGHT GAFFER MANAGER                                                          |
+================================================================================+
|  GAFFER SELECTION                                                              |
|  +--------------------------------------------------------------------------+  |
|  | Select Gaffer: [Seq: sq0070 ▼]                                           |  |
|  |                                                                          |  |
|  | Inheritance Chain: Seq sq0070 → Master                                   |  |
|  +--------------------------------------------------------------------------+  |
|                                                                                |
|  LIGHTS IN GAFFER                                                              |
|  +--------+------+-------+--------+---------+---------+--------+-----------+  |
|  | Light  | Mute | Inten | Expose | Color   | Source  | Select | Details   |  |
|  +--------+------+-------+--------+---------+---------+--------+-----------+  |
|  | keyL1  |  -   | **0.8** | 0.0  | **.8,.9,1** | Seq | [Sel]  |   [>>]    |  |
|  | fillL1 | MUTE |  -    |   -    |    -    | Seq     | [Sel]  |   [>>]    |  |
|  | rimL_L |  -   | 1.0   |  0.0   | 1,1,1   | Master  | [Sel]  |   [>>]    |  |
|  | rimL_R |  -   | 1.0   |  0.0   | 1,1,1   | Master  | [Sel]  |   [>>]    |  |
|  | skyDm  |  -   | 1.0   | -0.5   | 1,1,1   | Master  | [Sel]  |   [>>]    |  |
|  +--------+------+-------+--------+---------+---------+--------+-----------+  |
```

**Notes:**
- `**0.8**` (bold) = overridden in Seq gaffer
- `1.0` (normal) = inherited from Master
- `MUTE` = light is muted in Seq gaffer

---

**Maintainer:** CTX Pipeline Team  
**Last Review:** 2026-02-21

