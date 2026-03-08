#!/usr/bin/env python
"""Update CTX_lightGaffer_spec.md to reference CTX_gaffer_UI.md"""

import re

# Read the file
with open('spec/CTX_lightGaffer_spec.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Find section 9 and section 10
section9_pattern = r'## 9\. UI Specification.*?(?=## 10\. API Reference)'
new_section9 = '''## 9. UI Specification

**Note:** The UI specification has been moved to a separate document for better organization.

**See:** [CTX_gaffer_UI.md](CTX_gaffer_UI.md) for complete UI specification including:
- Gaffer Manager UI with gaffer selection dropdown
- Light list table with source and override indicators
- Light Editor panel with detailed attribute editing
- Workflows for adding lights, creating overrides, and editing values
- UI mockups and visual examples

---

'''

# Replace section 9
content = re.sub(section9_pattern, new_section9, content, flags=re.DOTALL)

# Write back
with open('spec/CTX_lightGaffer_spec.md', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Updated CTX_lightGaffer_spec.md - Section 9 now references CTX_gaffer_UI.md")

