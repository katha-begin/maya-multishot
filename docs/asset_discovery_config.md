# Asset Discovery Configuration

## Overview

The asset discovery system has been updated to use flexible, template-based configuration that's ready for TokenExpander integration. All path resolution now uses the config file instead of hardcoded values.

## Configuration Structure

### 1. New Templates (lines 29-32)

```json
"templates": {
  "assetHeroPath": "$projRoot$project/$assetBase/$assetCategory/$assetSubdir/$assetName/$heroSubdir/$assetName.$ext",
  "assetShaderPath": "$projRoot$project/$assetBase/$assetCategory/$assetSubdir/$assetName/$heroSubdir/$assetName$shaderSuffix",
  "assetGroomPath": "$projRoot$project/$assetBase/$assetCategory/$assetSubdir/$assetName/$heroSubdir/$assetName$groomSuffix",
  "assetSearchPath": "$projRoot$project/$assetBase/$assetCategory/$assetSubdir/$assetName/$heroSubdir"
}
```

**Purpose:**
- `assetHeroPath` - Full path to hero asset file
- `assetShaderPath` - Full path to shader file
- `assetGroomPath` - Full path to groom file
- `assetSearchPath` - Directory to search for shader/groom files

### 2. Asset Discovery Section (lines 38-60)

```json
"assetDiscovery": {
  "heroSubdir": "hero",
  "shaderFileSuffix": "_rsshade.ma",
  "groomFileSuffix": "_groom.ma",
  "categoryMappings": {
    "CHAR": {
      "directory": "Character",
      "subdirs": ["Main", "object"]
    },
    "PROP": {
      "directory": "Props",
      "subdirs": ["Main", "object"]
    },
    "SETS": {
      "directory": "Sets",
      "subdirs": ["Exterior", "Interior"]
    },
    "SDRS": {
      "directory": "Setdress",
      "subdirs": ["interior", "exterior", "Main", "object"]
    }
  }
}
```

**Purpose:**
- Defines how to map asset types (CHAR, PROP, etc.) to directory structures
- Specifies which subdirectories to search for each asset type
- Configurable file suffixes for shader and groom files

### 3. New Tokens (lines 95-147)

```json
"tokens": {
  "assetCategory": {
    "description": "Asset category directory name",
    "example": "Character",
    "mapping": {
      "CHAR": "Character",
      "PROP": "Props",
      "SETS": "Sets",
      "SDRS": "Setdress"
    }
  },
  "assetSubdir": {
    "description": "Asset subdirectory (Main, object, Exterior, etc.)",
    "example": "Main"
  },
  "heroSubdir": {
    "description": "Hero subdirectory for asset files",
    "default": "hero"
  },
  "shaderSuffix": {
    "description": "Shader file suffix",
    "default": "_rsshade.ma"
  },
  "groomSuffix": {
    "description": "Groom file suffix",
    "default": "_groom.ma"
  }
}
```

## Path Examples

### Sample Paths Verified

```
V:\SWA\all\asset\Character\Main\Ajay\hero\Ajay_rsshade.ma
V:\SWA\all\asset\Props\object\AjayArmL\hero\AjayArmL_rsshade.ma
V:\SWA\all\asset\Setdress\exterior\CBDAExtAreaLowD\hero\CBDAExtAreaLowD_rsshade.ma
```

### Token Expansion Example

For asset: `CHAR` / `Ajay` / `001`

**Context:**
```python
{
  'projRoot': 'V:/',
  'project': 'SWA',
  'assetBase': 'all/asset',
  'assetCategory': 'Character',  # Mapped from CHAR
  'assetSubdir': 'Main',         # From categoryMappings
  'assetName': 'Ajay',
  'heroSubdir': 'hero',
  'shaderSuffix': '_rsshade.ma'
}
```

**Expanded Path:**
```
V:/SWA/all/asset/Character/Main/Ajay/hero/Ajay_rsshade.ma
```

## Usage in Code

### Using shader_discovery.py

```python
from core.shader_discovery import discover_shader_files
from config.project_config import ProjectConfig

# Load config
config = ProjectConfig('project_configs/ctx_config.json')

# Discover shader files (will use config automatically)
result = discover_shader_files('CHAR', 'Ajay', 'V:/SWA', config)
# Returns: {'shader': 'V:/SWA/.../Ajay_rsshade.ma', 'groom': None}
```

### Future: Using TokenExpander

```python
from core.tokens import TokenExpander
from config.project_config import ProjectConfig

# Load config
config = ProjectConfig('project_configs/ctx_config.json')
expander = TokenExpander(config)

# Build context
context = {
    'assetType': 'CHAR',
    'assetName': 'Ajay',
    'assetCategory': 'Character',  # Or map from assetType
    'assetSubdir': 'Main',
    'shaderSuffix': '_rsshade.ma'
}

# Expand template
shader_path = expander.expand('assetShaderPath', context)
# Returns: 'V:/SWA/all/asset/Character/Main/Ajay/hero/Ajay_rsshade.ma'
```

## Benefits

✅ **Flexible** - Change directory structure without modifying code
✅ **Configurable** - Different projects can have different structures
✅ **Token-based** - Ready for TokenExpander integration
✅ **Maintainable** - All path logic in one config file
✅ **Extensible** - Easy to add new asset types or subdirectories

