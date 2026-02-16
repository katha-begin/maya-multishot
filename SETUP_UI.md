# UI Setup Guide

## Quick Answer

**No installation needed if you're using Maya!** Maya already includes PySide2/PySide6.

**For standalone testing outside Maya:** You need to install PySide2 or PySide6.

---

## Setup Instructions

### Option 1: Launch in Maya (Recommended)

Maya already has PySide2/PySide6 built-in, so **no installation needed**!

#### Step 1: Open Maya Script Editor

1. Open Maya
2. Go to **Windows → General Editors → Script Editor**
3. Click the **Python** tab

#### Step 2: Add Project to Python Path

```python
import sys
import os

# Add your project directory to Python path
project_path = r"E:\dev\maya-multishot"
if project_path not in sys.path:
    sys.path.insert(0, project_path)

print("Project path added:", project_path)
```

#### Step 3: Launch the UI

```python
from ui import main_window

# Launch the UI
window = main_window.show()
print("UI launched successfully!")
```

**That's it!** The UI should open as a dockable window in Maya.

---

### Option 2: Standalone Testing (Outside Maya)

If you want to test the UI outside Maya, you need to install PySide2 or PySide6.

#### Step 1: Install PySide2 or PySide6

**Using pip:**

```bash
# For Python 3.6-3.11 (Maya 2022-2024)
pip install PySide2

# OR for Python 3.9+ (Maya 2025+)
pip install PySide6
```

**Using conda:**

```bash
# For PySide2
conda install -c conda-forge pyside2

# OR for PySide6
conda install -c conda-forge pyside6
```

#### Step 2: Run the Test Script

```bash
cd E:\dev\maya-multishot
python test_ui_launch.py
```

The UI should open in a standalone window.

---

## Maya Version Compatibility

| Maya Version | PySide Version | Python Version |
|--------------|----------------|----------------|
| Maya 2022    | PySide2        | Python 3.7     |
| Maya 2023    | PySide2        | Python 3.9     |
| Maya 2024    | PySide2        | Python 3.10    |
| Maya 2025+   | PySide6        | Python 3.11    |

**Good news:** The UI code automatically detects and uses the correct version!

```python
try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
```

---

## Troubleshooting

### Issue 1: "No module named 'ui'"

**Solution:** Add project path to `sys.path`:

```python
import sys
sys.path.insert(0, r"E:\dev\maya-multishot")
```

### Issue 2: "No module named 'PySide2'" (Standalone only)

**Solution:** Install PySide2:

```bash
pip install PySide2
```

### Issue 3: "No module named 'config.project_config'"

**Solution:** Make sure you're running from the project root directory, or add it to `sys.path`.

### Issue 4: Config file not found

**Expected behavior:** The UI will show a warning in the status bar but will still open. The filesystem discovery will work, but you won't see project-specific data.

**To fix:** Make sure `project_configs/ctx_config.json` exists (it should already exist in your project).

---

## Quick Test Commands

### In Maya:

```python
# One-liner to launch UI
import sys; sys.path.insert(0, r"E:\dev\maya-multishot"); from ui import main_window; main_window.show()
```

### Standalone:

```bash
cd E:\dev\maya-multishot
python test_ui_launch.py
```

---

## What to Expect

When the UI launches, you should see:

1. **Main Window** titled "Context Manager (Filesystem Mode)"
2. **Header** with Project/Episode/Sequence dropdowns
3. **Shot List** (empty until you select Ep/Seq)
4. **Asset Table** (empty until you select a shot)
5. **Status Bar** at the bottom

### To Test Functionality:

1. Select an **Episode** (e.g., "Ep04")
2. Select a **Sequence** (e.g., "sq0070")
3. Click **Refresh** button
4. If shots exist in your filesystem, they'll appear in the shot list
5. Click a shot to see its assets

### To Test Dialogs:

- Click **"+ Add Shot"** → Opens Add Shot Dialog
- Click **"+ Import"** → Opens Import Asset Dialog
- Click **"Convert"** → Opens Convert Scene Dialog
- Click **"Settings"** → Opens Settings Dialog

All dialogs will show "Not implemented yet" messages when you click OK/Apply.

---

## Summary

**For Maya users:** Just add the project path to `sys.path` and launch!

**For standalone testing:** Install PySide2/PySide6 first.

**No other dependencies needed!** The UI uses only standard Python libraries and Qt (which Maya provides).

---

## Next Steps

Once you've tested the UI and are happy with the design:

1. Provide feedback on layout, colors, functionality
2. Request any changes or improvements
3. Approve for Phase 4B (CTX integration)

Then I'll implement the backend functionality to make all the buttons work!

