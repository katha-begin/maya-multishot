# Department Discovery and Data Storage

**Version:** 1.0  
**Date:** 2026-02-14

---

## Overview

This document explains how departments are defined, discovered, and stored in the Context Variables Pipeline system.

---

## 1. Department Definition (Static)

### Configuration

Departments are **predefined** in the project configuration file:

```json
{
  "tokens": {
    "dept": {
      "description": "Department",
      "example": "anim",
      "values": ["anim", "layout", "fx", "lighting", "comp", "render"]
    }
  }
}
```

### Why Static?

- **Pipeline Structure**: Departments are part of your pipeline's organizational structure
- **Path Construction**: Used to build paths before data exists
- **Validation**: Ensures only valid departments are used
- **Consistency**: Same departments across all projects

### Common Departments

| Code | Name | Description |
|------|------|-------------|
| `anim` | Animation | Character animation |
| `layout` | Layout | Camera and blocking |
| `fx` | Effects | Visual effects (particles, fluids) |
| `lighting` | Lighting | Lighting and rendering |
| `comp` | Compositing | Final compositing |
| `render` | Render | Render outputs |

---

## 2. Department Discovery (Dynamic)

### Purpose

While departments are predefined, we need to **discover which departments have actual data** for each shot.

### Filesystem Structure

```
V:/SWA/all/scene/Ep04/sq0070/SH0170/
├── anim/              ← Department directory
│   ├── work/
│   └── publish/
│       ├── v001/      ← Version directory
│       │   ├── Ep04_sq0070_SH0170__CHAR_CatStompie_001.abc
│       │   └── Ep04_sq0070_SH0170__PROP_TreeBig_001.abc
│       ├── v002/
│       └── v003/
├── layout/
│   └── publish/
│       └── v001/
│           └── Ep04_sq0070_SH0170__CHAR_CatStompie_001.abc
└── fx/
    └── publish/
        └── v001/
            └── Ep04_sq0070_SH0170__ENV_ForestDay_001.vdb
```

### Discovery Process

**Step 1: Scan Shot Directory**
```python
shot_path = "V:/SWA/all/scene/Ep04/sq0070/SH0170"
departments = []

for item in os.listdir(shot_path):
    dept_path = os.path.join(shot_path, item)
    if os.path.isdir(dept_path):
        # Check if it's a valid department
        if item in config.get_token('dept')['values']:
            departments.append(item)
```

**Step 2: Scan Publish Directories**
```python
for dept in departments:
    publish_path = os.path.join(shot_path, dept, "publish")
    if os.path.exists(publish_path):
        # Scan for versions and assets
        scan_publish_directory(publish_path)
```

**Step 3: Extract Asset Information**
```python
def scan_publish_directory(publish_path):
    """Scan publish directory for versions and assets."""
    versions = {}
    
    # List version directories (v001, v002, etc.)
    for ver_dir in os.listdir(publish_path):
        if re.match(r'v\d{3}', ver_dir):
            ver_path = os.path.join(publish_path, ver_dir)
            
            # Scan for cache files
            for filename in os.listdir(ver_path):
                if filename.endswith(('.abc', '.vdb', '.ma', '.mb')):
                    # Parse filename
                    asset_info = parse_filename(filename)
                    if asset_info:
                        # Store in cache
                        store_asset_version(publish_path, asset_info, ver_dir)
```

---

## 3. Data Storage in Cache

### Cache Structure

The cache is stored in the configuration JSON file and updated dynamically:

```json
{
  "cache": {
    "last_updated": "2026-02-14T10:30:00",
    
    "episodes": ["Ep01", "Ep02", "Ep03", "Ep04"],
    
    "sequences": {
      "Ep04": ["sq0010", "sq0020", "sq0070"]
    },
    
    "shots": {
      "Ep04/sq0070": ["SH0170", "SH0180", "SH0190"]
    },
    
    "departments": {
      "Ep04/sq0070/SH0170": ["anim", "layout", "fx"],
      "Ep04/sq0070/SH0180": ["anim", "layout"]
    },
    
    "assets": {
      "CHAR": [
        "CHAR_CatStompie_001",
        "CHAR_CatStompie_002",
        "CHAR_DogBounce_001"
      ],
      "PROP": [
        "PROP_TreeBig_001",
        "PROP_RockMedium_001"
      ]
    },
    
    "versions": {
      "V:/SWA/all/scene/Ep04/sq0070/SH0170/anim/publish": {
        "CHAR_CatStompie_001": ["v001", "v002", "v003"],
        "CHAR_CatStompie_002": ["v001", "v002"],
        "PROP_TreeBig_001": ["v001"]
      },
      "V:/SWA/all/scene/Ep04/sq0070/SH0170/layout/publish": {
        "CHAR_CatStompie_001": ["v001"]
      },
      "V:/SWA/all/scene/Ep04/sq0070/SH0170/fx/publish": {
        "ENV_ForestDay_001": ["v001"]
      }
    }
  }
}
```

### Cache Sections Explained

| Section | Purpose | Example |
|---------|---------|---------|
| `last_updated` | Timestamp of last cache refresh | `"2026-02-14T10:30:00"` |
| `episodes` | List of discovered episodes | `["Ep01", "Ep04"]` |
| `sequences` | Sequences per episode | `{"Ep04": ["sq0070"]}` |
| `shots` | Shots per sequence | `{"Ep04/sq0070": ["SH0170"]}` |
| `departments` | Departments per shot | `{"Ep04/sq0070/SH0170": ["anim", "fx"]}` |
| `assets` | Assets per type | `{"CHAR": ["CHAR_CatStompie_001"]}` |
| `versions` | Versions per publish path | See above |

---

## 4. Implementation (Phase 1, Task P1-CACHE-02)

### Module: `core/cache.py`

```python
class CacheManager(object):
    """Manages asset and version cache."""
    
    def scan_shot(self, ep, seq, shot):
        """
        Scan shot directory for departments and assets.
        
        Args:
            ep (str): Episode code (e.g., 'Ep04')
            seq (str): Sequence code (e.g., 'sq0070')
            shot (str): Shot code (e.g., 'SH0170')
        
        Returns:
            dict: Discovered data
        """
        shot_path = self._build_shot_path(ep, seq, shot)
        departments = self._discover_departments(shot_path)
        
        result = {
            'departments': departments,
            'assets': {},
            'versions': {}
        }
        
        for dept in departments:
            publish_path = os.path.join(shot_path, dept, 'publish')
            dept_data = self._scan_publish_directory(publish_path)
            result['assets'].update(dept_data['assets'])
            result['versions'][publish_path] = dept_data['versions']
        
        return result
    
    def _discover_departments(self, shot_path):
        """Discover departments in shot directory."""
        valid_depts = self.config.get_token('dept')['values']
        departments = []
        
        if not os.path.exists(shot_path):
            return departments
        
        for item in os.listdir(shot_path):
            if item in valid_depts:
                dept_path = os.path.join(shot_path, item)
                if os.path.isdir(dept_path):
                    departments.append(item)
        
        return sorted(departments)
```

---

## 5. Usage Examples

### Example 1: Get Departments for a Shot

```python
from core.cache import CacheManager

cache = CacheManager(config)

# Discover departments
departments = cache.get_shot_departments('Ep04', 'sq0070', 'SH0170')
# Returns: ['anim', 'layout', 'fx']
```

### Example 2: Get Assets for a Department

```python
# Get assets in anim department
assets = cache.get_department_assets('Ep04', 'sq0070', 'SH0170', 'anim')
# Returns: ['CHAR_CatStompie_001', 'CHAR_CatStompie_002', 'PROP_TreeBig_001']
```

### Example 3: Get Versions for an Asset

```python
# Get versions for specific asset
versions = cache.get_asset_versions(
    'Ep04', 'sq0070', 'SH0170', 'anim', 'CHAR_CatStompie_001'
)
# Returns: ['v001', 'v002', 'v003']
```

---

## 6. Cache Refresh Strategy

### When to Refresh

1. **On Scene Open** - Refresh cache when opening Maya scene
2. **Manual Refresh** - User clicks "Refresh" button in UI
3. **After Import** - Refresh after importing new assets
4. **Scheduled** - Auto-refresh every N minutes (optional)

### Refresh Process

```python
def refresh_cache(self):
    """Refresh entire cache."""
    self.cache_data = {
        'last_updated': datetime.now().isoformat(),
        'episodes': [],
        'sequences': {},
        'shots': {},
        'departments': {},
        'assets': {},
        'versions': {}
    }
    
    # Scan filesystem
    self._scan_all_episodes()
    
    # Save to config file
    self._save_cache()
```

---

## Summary

**Department Definition:**
- ✅ Static list in configuration
- ✅ Predefined by pipeline structure
- ✅ Used for path construction and validation

**Department Discovery:**
- ✅ Dynamic scanning of shot directories
- ✅ Discovers which departments have data
- ✅ Scans publish directories for assets and versions

**Data Storage:**
- ✅ Hierarchical cache structure
- ✅ Stored in configuration JSON
- ✅ Updated on refresh
- ✅ Keyed by full publish paths

**Implementation:**
- 🔄 Phase 1, Task [P1-CACHE-02]
- 🔄 Module: `core/cache.py`
- 🔄 Estimated: 3-5 days

