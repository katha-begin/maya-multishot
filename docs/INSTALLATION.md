# CTX Tools - Installation Guide

**Version:** 1.1
**Last Updated:** 2026-03-06

---

## Table of Contents

1. [Requirements](#requirements)
2. [Installation Methods](#installation-methods)
3. [Automatic Menu Installation](#automatic-menu-installation)
4. [Manual Menu Installation](#manual-menu-installation)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)

---

## Requirements

### Software Requirements

- **Maya:** 2022 or later
- **Python:** 3.7+ (Maya 2022+)
- **Qt:** PySide2 (Maya 2022-2023) or PySide6 (Maya 2024+)

### Python Dependencies

All dependencies are included with Maya, no additional installation required:
- PySide2/PySide6 (included with Maya)
- maya.cmds (included with Maya)
- maya.mel (included with Maya)

---

## Installation Methods

### Method 1: Clone Repository (Recommended)

```bash
# Clone the repository
cd E:/dev  # Or your preferred location
git clone https://github.com/katha-begin/maya-multishot.git

# Switch to current development branch
cd maya-multishot
git checkout feature/ui-tools-framework
```

### Method 2: Download ZIP

1. Download ZIP from GitHub
2. Extract to your preferred location (e.g., `E:/dev/maya-multishot`)
3. Note the full path for configuration

---

## Automatic Menu Installation

The easiest way to use CTX Tools is to set up automatic loading via `userSetup.py`.

### Step 1: Locate Maya Scripts Directory

**Windows:**
```
C:/Users/<username>/Documents/maya/<version>/scripts/
```

**Linux:**
```
~/maya/<version>/scripts/
```

**Mac:**
```
~/Library/Preferences/Autodesk/maya/<version>/scripts/
```

Example: `C:/Users/JohnDoe/Documents/maya/2024/scripts/`

### Step 2: Copy userSetup.py

1. Navigate to `maya-multishot/examples/`
2. Copy `userSetup.py` to your Maya scripts directory
3. If you already have a `userSetup.py`, append the contents instead

### Step 3: Configure Path

Edit `userSetup.py` and update the path:

```python
# Update this line to match your installation
CTX_TOOLS_PATH = r"E:/dev/maya-multishot"
```

**Important:** Use raw string (`r"..."`) or forward slashes to avoid path issues.

### Step 4: Restart Maya

1. Close Maya completely
2. Restart Maya
3. Look for "CTX Tools" menu in the main menu bar

---

## Manual Menu Installation

If you prefer not to use `userSetup.py`, you can manually create the menu each session.

### Method 1: Python Script

```python
# In Maya Script Editor (Python tab)
import sys
sys.path.append(r'E:/dev/maya-multishot')  # Update path

from tools import maya_menu
maya_menu.create_ctx_menu()
```

### Method 2: Create Shelf Button

1. Open Maya Script Editor
2. Paste the code above
3. Select all the code
4. Middle-mouse drag to a shelf
5. Click the shelf button to create the menu

---

## Verification

### Check Menu Installation

1. Look for "CTX Tools" in Maya's main menu bar
2. Click "CTX Tools" to see the menu items:
   - Context Manager
   - Gaffer Manager
   - Asset Manager
   - Reload Menu
   - About

### Test Context Manager

1. Click **CTX Tools → Context Manager**
2. Main window should open as a dockable panel
3. You should see the shot table interface

### Test Gaffer Manager

1. Click **CTX Tools → Gaffer Manager**
2. Gaffer Manager dialog should open
3. You should see gaffer selection and lights table

### Test Asset Manager

1. Click **CTX Tools → Asset Manager**
2. Asset Manager dialog should open
3. You should see asset management interface

---

## Menu Features

### CTX Tools Menu Items

```
CTX Tools
├── Context Manager       # Multi-shot context management
├── Gaffer Manager        # Hierarchical light management
├── Asset Manager         # Asset reference management
├── ─────────────────
├── Reload Menu          # Reload menu (for development)
└── About                # About CTX Tools
```

### Context Manager

- Multi-shot support in single scene
- Token-based path resolution
- Display layer management
- Shot creation and management

### Gaffer Manager

- Hierarchical light management
- Master → Sequence → Shot inheritance
- Per-attribute overrides
- Apply/capture operations

### Asset Manager

- Asset reference management
- Version control
- Shader assignment
- Display layer integration

---

## Troubleshooting

### Issue 1: Menu Not Appearing

**Symptoms:** CTX Tools menu doesn't appear after restart

**Solutions:**
1. Check `userSetup.py` is in correct location
2. Verify path in `userSetup.py` is correct
3. Check Maya Script Editor for error messages
4. Try manual installation method to test

**Verify Path:**
```python
import os
path = r"E:/dev/maya-multishot"
print(os.path.exists(path))  # Should print True
```

### Issue 2: Import Errors

**Symptoms:** Error messages about missing modules

**Solutions:**
1. Verify path is added to `sys.path`
2. Check repository structure is intact
3. Ensure all files are present

**Check Import:**
```python
import sys
sys.path.append(r'E:/dev/maya-multishot')

try:
    from tools import maya_menu
    print("Import successful!")
except ImportError as e:
    print("Import failed: {}".format(e))
```

### Issue 3: Tools Not Opening

**Symptoms:** Menu appears but clicking items does nothing

**Solutions:**
1. Check Maya Script Editor for error messages
2. Verify UI files are present in `ui/` folder
3. Try opening tools manually:

```python
# Test Context Manager
from ui.dockable_window import show_dockable_window
show_dockable_window()

# Test Gaffer Manager
from ui.gaffer_manager_dialog import GafferManagerDialog
dialog = GafferManagerDialog()
dialog.show()
```

### Issue 4: Menu Appears Multiple Times

**Symptoms:** Multiple "CTX Tools" menus in menu bar

**Solutions:**
1. Click **CTX Tools → Reload Menu** to clean up
2. Or manually remove:

```python
from tools import maya_menu
maya_menu.remove_ctx_menu()
maya_menu.create_ctx_menu()
```

---

## Advanced Configuration

### Environment Variable Method

Instead of hardcoding the path, use an environment variable:

**Windows (System Environment Variables):**
```
Variable: CTX_TOOLS_PATH
Value: E:\dev\maya-multishot
```

**userSetup.py:**
```python
import os
CTX_TOOLS_PATH = os.environ.get('CTX_TOOLS_PATH', r'E:/dev/maya-multishot')
```

### Studio Pipeline Integration

For studio pipelines, you can integrate CTX Tools into your existing pipeline:

```python
# In your studio's userSetup.py or pipeline initialization
import sys
import os

# Get path from studio environment
ctx_path = os.environ.get('STUDIO_CTX_TOOLS_PATH')
if ctx_path and os.path.exists(ctx_path):
    sys.path.insert(0, ctx_path)
    
    from tools import maya_menu
    maya_menu.install()
```

---

## Uninstallation

### Remove Menu

```python
from tools import maya_menu
maya_menu.remove_ctx_menu()
```

### Remove from userSetup.py

1. Open your `userSetup.py`
2. Remove or comment out the CTX Tools section
3. Restart Maya

---

## Next Steps

After installation:

1. **Read Documentation:**
   - [Gaffer System Overview](gaffer_system_overview.md)
   - [Gaffer UI Guide](gaffer_ui_guide.md)
   - [Gaffer Workflows](gaffer_workflows.md)

2. **Try Tutorials:**
   - Create a test scene
   - Open Context Manager
   - Create some shots
   - Open Gaffer Manager
   - Set up lighting

3. **Explore Features:**
   - Multi-shot management
   - Light gaffer system
   - Asset management

---

**Support:**
- GitHub: https://github.com/katha-begin/maya-multishot
- Documentation: See `docs/` folder
- Issues: Report on GitHub Issues

---

**Installation Complete!**

You should now see the "CTX Tools" menu in Maya's main menu bar.

