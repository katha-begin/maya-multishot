# Vendor Directory - Third-Party Libraries

This directory contains vendored (bundled) third-party libraries for the CTX pipeline.

## Why Vendor Libraries?

**Vendoring** means including third-party libraries directly in your repository instead of requiring users to install them separately.

### Advantages:
- ✅ **Version Control** - Exact version locked in repo
- ✅ **No Internet Required** - Works in isolated studio networks
- ✅ **Consistency** - Everyone uses the same version
- ✅ **Fast Setup** - No pip install needed
- ✅ **Customization** - Can patch if needed
- ✅ **Reliability** - No dependency on external package servers

### Common in VFX/Animation Studios:
- Studios often have isolated networks (no internet access)
- Need exact version control for reproducibility
- Avoid dependency conflicts between projects

---

## Current Vendored Libraries

### NodeGraphQt (Optional)

**Status:** Not yet vendored (run setup script to vendor)

**License:** MIT License  
**Author:** Johnny Chan  
**Source:** https://github.com/jchanvfx/NodeGraphQt  
**Version:** 0.6.44 (recommended)  

**Purpose:** Professional node graph UI framework for CTX pipeline visualization

**To Vendor NodeGraphQt:**

```bash
# Method 1: Automatic (recommended)
python vendor_nodegraphqt.py

# Method 2: Manual
pip download NodeGraphQt --no-deps --dest ./vendor
# Then extract to vendor/NodeGraphQt/
```

**After Vendoring:**
```
vendor/
├── README.md                    # This file
├── NodeGraphQt/                 # ← Vendored library
│   ├── NodeGraphQt/             # ← Main package
│   ├── LICENSE.md               # ← MIT License
│   └── README.md
└── THIRD_PARTY_LICENSES.md      # ← Attribution
```

---

## How Vendoring Works

### 1. Library is Copied to vendor/

Instead of:
```
C:/Python/Lib/site-packages/NodeGraphQt/
```

Library is in:
```
E:/dev/maya-multishot/vendor/NodeGraphQt/
```

### 2. Python Path is Updated

The launcher adds vendor/ to Python path:

```python
import sys
import os

vendor_dir = 'E:/dev/maya-multishot/vendor'
sys.path.insert(0, vendor_dir)  # Add FIRST (highest priority)

# Now imports come from vendor/
from NodeGraphQt import NodeGraph  # Uses vendor/NodeGraphQt/
```

### 3. Version is Locked

The exact version in vendor/ is used, regardless of what's installed system-wide.

---

## License Compliance

All vendored libraries must include their original license files.

### MIT License (NodeGraphQt)

The MIT License allows:
- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ✅ Sublicense
- ✅ Private use

**Requirements:**
- ✅ Include original license file
- ✅ Include copyright notice

**See:** `THIRD_PARTY_LICENSES.md` for full attribution

---

## Updating Vendored Libraries

### To Update NodeGraphQt:

```bash
# Remove old version
rm -rf vendor/NodeGraphQt

# Download new version
python vendor_nodegraphqt.py

# Test thoroughly
python tests/test_nodegraphqt_ui.py

# Commit to version control
git add vendor/NodeGraphQt
git commit -m "Update NodeGraphQt to v0.6.45"
```

---

## Alternative: System Installation

If you prefer NOT to vendor libraries:

```bash
# Install system-wide
pip install NodeGraphQt

# The launcher will use system installation if vendor/ is empty
```

**Note:** This requires internet access and may cause version conflicts.

---

## .gitignore Considerations

### Option 1: Commit Vendored Libraries (Recommended)

**DO NOT** add vendor/ to .gitignore

**Advantages:**
- ✅ Clone and run (no setup needed)
- ✅ Exact version for everyone
- ✅ Works offline

**Disadvantages:**
- ⚠️ Larger repo size (~1-2 MB per library)

### Option 2: Ignore Vendored Libraries

**Add to .gitignore:**
```
vendor/NodeGraphQt/
```

**Advantages:**
- ✅ Smaller repo size

**Disadvantages:**
- ⚠️ Users must run setup script
- ⚠️ Requires internet access
- ⚠️ Version might differ

**For studios: Use Option 1 (commit vendored libraries)**

---

## Directory Structure

```
vendor/
├── README.md                       # This file
├── THIRD_PARTY_LICENSES.md         # License attribution
├── NodeGraphQt/                    # Vendored NodeGraphQt
│   ├── NodeGraphQt/                # Main package
│   │   ├── __init__.py
│   │   ├── base/
│   │   ├── widgets/
│   │   └── ...
│   ├── LICENSE.md                  # MIT License
│   └── README.md
└── (future libraries here)
```

---

## FAQ

### Q: Why not use pip install?

**A:** Studios often have:
- No internet access (isolated networks)
- Strict version requirements
- Need for reproducibility
- Firewall restrictions

### Q: Can I use system-installed NodeGraphQt instead?

**A:** Yes! The launcher checks vendor/ first, then falls back to system installation.

### Q: What if I want a different version?

**A:** Edit `vendor_nodegraphqt.py` and change the version, or download manually.

### Q: Is this legal?

**A:** Yes! MIT License explicitly allows redistribution. Just include the license file.

### Q: How much space does it take?

**A:** NodeGraphQt is ~1-2 MB. Very small compared to typical VFX assets.

---

## Support

For issues with vendoring:
- See: `tests/VENDORING_NodeGraphQt.md` (detailed guide)
- Run: `python vendor_nodegraphqt.py` (automatic setup)
- Manual: Download from https://github.com/jchanvfx/NodeGraphQt/releases

---

**Last Updated:** 2026-02-18

