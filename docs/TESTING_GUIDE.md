# CTX Tools - Testing Guide

**Version:** 1.1
**Last Updated:** 2026-03-06
**Branch:** `feature/ui-tools-framework`

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Menu Integration Testing](#menu-integration-testing)
3. [Context Manager Testing](#context-manager-testing)
4. [Gaffer Manager Testing](#gaffer-manager-testing)
5. [Integration Testing](#integration-testing)
6. [Reporting Issues](#reporting-issues)

---

## Quick Start

### Step 1: Load CTX Tools Menu

Open Maya Script Editor (Python tab) and run:

```python
import sys
sys.path.append(r'E:/dev/maya-multishot')  # Update to your path

from tools import maya_menu
maya_menu.create_ctx_menu()
```

You should see "CTX Tools" appear in Maya's main menu bar.

### Step 2: Verify Menu Items

Click "CTX Tools" menu and verify you see:
- ✓ Context Manager
- ✓ Gaffer Manager
- ✓ Asset Manager
- ✓ (separator)
- ✓ Reload Menu
- ✓ About

---

## Menu Integration Testing

### Test 1: Create Menu

**Steps:**
1. Run the Quick Start code above
2. Check Maya's main menu bar

**Expected:**
- "CTX Tools" menu appears in menu bar
- Menu is positioned after standard Maya menus
- No error messages in Script Editor

**Pass/Fail:** ___________

---

### Test 2: Menu Items

**Steps:**
1. Click "CTX Tools" menu
2. Verify all menu items are present

**Expected:**
- All 6 menu items visible
- Separators in correct positions
- Menu items have annotations (hover to see)

**Pass/Fail:** ___________

---

### Test 3: About Dialog

**Steps:**
1. Click "CTX Tools → About"

**Expected:**
- Dialog appears with CTX Tools information
- Shows version, tools list, features, repository URL
- "OK" button closes dialog

**Pass/Fail:** ___________

---

### Test 4: Reload Menu

**Steps:**
1. Click "CTX Tools → Reload Menu"

**Expected:**
- Menu disappears briefly
- Menu reappears in same position
- All menu items still present
- No error messages

**Pass/Fail:** ___________

---

## Context Manager Testing

### Test 5: Open Context Manager

**Steps:**
1. Click "CTX Tools → Context Manager"

**Expected:**
- Main window opens as dockable panel
- Window shows shot table interface
- Window can be docked/undocked
- No error messages

**Pass/Fail:** ___________

---

### Test 6: Context Manager Functionality

**Steps:**
1. Open Context Manager
2. Try basic operations:
   - Add shots
   - View shot list
   - Search shots
   - Delete shots

**Expected:**
- All operations work correctly
- UI updates properly
- No crashes or errors

**Pass/Fail:** ___________

---

## Gaffer Manager Testing

### Test 7: Open Gaffer Manager

**Steps:**
1. Click "CTX Tools → Gaffer Manager"

**Expected:**
- Gaffer Manager dialog opens
- Dialog is non-modal (can interact with Maya)
- Shows gaffer selection dropdown
- Shows empty lights table
- No error messages

**Pass/Fail:** ___________

---

### Test 8: Create Gaffer Chain

**Steps:**
1. Open Gaffer Manager
2. In Maya Script Editor, run:

```python
from core.gaffer.chain_ops import ChainOperations

chain = ChainOperations.build_gaffer_chain(
    master_name='Master',
    sequence_name='sq0070',
    shot_name='SH0010'
)
```

3. Click "Refresh" in Gaffer Manager

**Expected:**
- Three gaffers created in Maya scene
- Gaffer dropdown shows: Master, Seq: sq0070, Shot: SH0010
- Chain display shows hierarchy
- No error messages

**Pass/Fail:** ___________

---

### Test 9: Add Light to Gaffer

**Steps:**
1. Create a light in Maya: `cmds.shadingNode('aiAreaLight', asLight=True)`
2. Select "Master" gaffer in dropdown
3. Click "+ Add Light" button
4. Select the light from the list
5. Click "Add Selected Lights"

**Expected:**
- Add Light Dialog opens
- Light appears in the list
- Light is added successfully
- Lights table updates with the light
- Success message appears

**Pass/Fail:** ___________

---

### Test 10: Light Editor Panel

**Steps:**
1. With light in gaffer, click ">>" button next to light
2. Light Editor Panel should open

**Expected:**
- Light Editor opens
- Shows light info (target, type, gaffer, chain)
- Shows all attributes with current values
- Shows inherited values
- All controls are functional

**Pass/Fail:** ___________

---

### Test 11: Create Override

**Steps:**
1. Open Light Editor for a light
2. Select "Shot: SH0010" gaffer
3. Type "1.5" in intensity override field
4. Click "Apply Changes"

**Expected:**
- Checkbox auto-enables when typing
- "Apply Changes" saves the override
- Success message appears
- Lights table updates to show "1.5" for intensity
- Source shows "Shot SH0010" (bold)

**Pass/Fail:** ___________

---

### Test 12: Apply to Scene

**Steps:**
1. With overrides created, click "Apply to Scene"

**Expected:**
- All lights in Maya update to gaffer values
- Maya light attributes match gaffer values
- Success message appears
- No errors

**Pass/Fail:** ___________

---

### Test 13: Capture from Scene

**Steps:**
1. Manually adjust a light in Maya (change intensity)
2. Click "Capture from Scene" in Gaffer Manager

**Expected:**
- Gaffer captures new values from Maya
- Lights table updates with new values
- Success message appears
- No errors

**Pass/Fail:** ___________

---

## Integration Testing

### Test 14: Multi-Tool Workflow

**Steps:**
1. Open Context Manager
2. Create a shot
3. Open Gaffer Manager
4. Create gaffer chain for the shot
5. Add lights to gaffer
6. Create overrides
7. Apply to scene

**Expected:**
- All tools work together
- No conflicts between tools
- Data persists in Maya scene
- No crashes or errors

**Pass/Fail:** ___________

---

### Test 15: Scene Save/Load

**Steps:**
1. Create gaffers with lights and overrides
2. Save Maya scene
3. Close Maya
4. Reopen Maya
5. Load the scene
6. Open Gaffer Manager

**Expected:**
- All gaffers persist in scene
- All lights persist
- All overrides persist
- Gaffer Manager shows correct data
- No data loss

**Pass/Fail:** ___________

---

### Test 16: Multiple Sessions

**Steps:**
1. Open Context Manager
2. Open Gaffer Manager
3. Open Asset Manager
4. Use all three tools simultaneously

**Expected:**
- All tools open without conflicts
- All tools remain functional
- No performance issues
- No crashes

**Pass/Fail:** ___________

---

## Reporting Issues

### Issue Template

When reporting issues, please include:

**Issue Title:** Brief description

**Steps to Reproduce:**
1. Step 1
2. Step 2
3. Step 3

**Expected Behavior:**
What should happen

**Actual Behavior:**
What actually happened

**Error Messages:**
Copy any error messages from Script Editor

**Environment:**
- Maya Version: ___________
- OS: ___________
- CTX Tools Branch: feature/ui-tools-framework
- Commit: ___________

**Screenshots:**
Attach screenshots if applicable

---

## Test Results Summary

**Date:** ___________  
**Tester:** ___________  
**Maya Version:** ___________  
**OS:** ___________

**Results:**
- Menu Integration: ___ / 4 tests passed
- Context Manager: ___ / 2 tests passed
- Gaffer Manager: ___ / 7 tests passed
- Integration: ___ / 3 tests passed

**Total:** ___ / 16 tests passed

**Critical Issues:** ___________

**Minor Issues:** ___________

**Notes:** ___________

---

## Next Steps After Testing

1. **If all tests pass:**
   - Report success
   - Continue with Phase 2 UI & Tools Framework migration

2. **If issues found:**
   - Report issues with details
   - Developer will fix issues
   - Retest after fixes

3. **Suggestions:**
   - Document any suggestions for improvements
   - Note any missing features
   - Provide feedback on UI/UX

---

**Happy Testing!**

