# Context Variables Pipeline - Design Document

**Version:** 2.1
**Last Updated:** 2026-02-14
**Status:** Active Development
**Repository:** https://github.com/katha-begin/maya-multishot.git

---

## Table of Contents

0. [Repository Setup](#0-repository-setup)
1. [Project Overview](#1-project-overview)
2. [Path Structure and Tokens](#2-path-structure-and-tokens)
3. [Multi-Shot Data Model](#3-multi-shot-data-model)
4. [Display Layer Management](#4-display-layer-management)
5. [Project Configuration Schema](#5-project-configuration-schema)
6. [Code Architecture](#6-code-architecture)
7. [Core Modules Specification](#7-core-modules-specification)
8. [UI Specification](#8-ui-specification)
9. [Use Cases and Workflows](#9-use-cases-and-workflows)
10. [File Naming Conventions](#10-file-naming-conventions)
11. [Compatibility Requirements](#11-compatibility-requirements)

---

## 0. Repository Setup

### 0.1 Repository Information

**GitHub Repository:** https://github.com/katha-begin/maya-multishot.git
**Owner:** katha-begin
**Project Name:** maya-multishot

### 0.2 Initial Repository Structure

Before starting implementation, set up the repository with the following structure:

```
maya-multishot/
├── .git/                          # Git repository
├── .gitignore                     # Git ignore rules
├── README.md                      # Project overview and quick start
├── LICENSE                        # License file
├── requirements.txt               # Python dependencies
├── setup.py                       # Package installation script
│
├── spec/                          # Specification documents
│   ├── spec.md                    # This document
│   ├── tasks.md                   # Implementation task list
│   ├── CHANGELOG_spec_update.md   # Specification changelog
│   ├── POC_vs_SPEC_alignment_report.md
│   ├── maya_context_tools_sample.py  # POC reference
│   └── igl_shot_build.py          # Build system reference
│
├── config/                        # Configuration module
│   ├── __init__.py
│   ├── platform.py                # Platform detection and path mapping
│   ├── project_config.py          # Configuration loader
│   └── templates.py               # Template manager
│
├── core/                          # Core functionality
│   ├── __init__.py
│   ├── context.py                 # Context management API
│   ├── tokens.py                  # Token expansion engine
│   ├── resolver.py                # Path resolver
│   ├── path_builder.py            # Path builder engine
│   ├── nodes.py                   # Node operations
│   ├── custom_nodes.py            # Custom Maya nodes (CTX_Manager, CTX_Shot, CTX_Asset)
│   ├── display_layers.py          # Display layer management
│   └── cache.py                   # Version cache system
│
├── tools/                         # User-facing tools
│   ├── __init__.py
│   ├── shot_manager.py            # Shot management tool
│   ├── asset_manager.py           # Asset management tool
│   ├── importer.py                # Asset importer
│   ├── converter.py               # Scene converter (POC/legacy to production)
│   ├── validator.py               # Scene validator
│   └── saver.py                   # Scene saver with validation
│
├── ui/                            # User interface
│   ├── __init__.py
│   ├── main_window.py             # Main dockable window
│   ├── shot_widget.py             # Shot list widget
│   ├── asset_widget.py            # Asset list widget
│   ├── browser_dialog.py          # Asset browser dialog
│   └── settings_dialog.py         # Settings dialog
│
├── farm/                          # Render farm integration
│   ├── __init__.py
│   ├── callbacks.py               # Pre-render callbacks
│   └── export.py                  # Export utilities
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── test_config.py             # Config module tests
│   ├── test_core.py               # Core module tests
│   ├── test_path_resolution.py    # Path resolution tests
│   ├── test_display_layers.py     # Display layer tests
│   ├── test_integration.py        # Integration tests
│   ├── test_performance.py        # Performance tests
│   └── test_data/                 # Test data directory
│       ├── configs/               # Sample config files
│       ├── scenes/                # Sample Maya scenes
│       └── caches/                # Sample cache files
│
├── docs/                          # Documentation
│   ├── user_guide.md              # User documentation
│   ├── api_reference.md           # API documentation
│   ├── migration_guide.md         # Migration guide
│   └── deployment_guide.md        # Deployment guide
│
└── examples/                      # Example configurations and scripts
    ├── ctx_config.json            # Sample project configuration
    └── sample_workflow.py         # Example usage script
```

### 0.3 Git Setup Instructions

#### Step 1: Initialize Repository (if not already done)

```bash
# Clone the repository
git clone https://github.com/katha-begin/maya-multishot.git
cd maya-multishot

# Or if starting fresh
git init
git remote add origin https://github.com/katha-begin/maya-multishot.git
```

#### Step 2: Create .gitignore

Create `.gitignore` file with the following content:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Maya
*.swatches
*.mb.swatches
*.ma.swatches

# IDEs
.vscode/
.idea/
*.sublime-project
*.sublime-workspace

# OS
.DS_Store
Thumbs.db
*.tmp

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Documentation
docs/_build/
```

#### Step 3: Create Initial Directory Structure

```bash
# Create all directories
mkdir -p config core tools ui farm tests/test_data/{configs,scenes,caches} docs examples spec

# Create __init__.py files for Python packages
touch config/__init__.py
touch core/__init__.py
touch tools/__init__.py
touch ui/__init__.py
touch farm/__init__.py
touch tests/__init__.py
```

#### Step 4: Create README.md

Create `README.md` with project overview:

```markdown
# Maya Multi-Shot Context Variables Pipeline

A Maya pipeline tool for managing context-aware file paths across multiple shots within a single scene.

## Features

- **Multi-shot support**: Work on multiple shots in one Maya scene
- **Token-based paths**: Template paths with automatic resolution
- **Display layer management**: Shot-specific visibility control
- **Cross-platform**: Windows and Linux support
- **Version management**: Independent asset versions per shot

## Quick Start

See [User Guide](docs/user_guide.md) for detailed instructions.

## Repository Structure

See [spec/spec.md](spec/spec.md) for complete technical specification.

## Development

See [spec/tasks.md](spec/tasks.md) for implementation task list.

## License

[Add license information]
```

#### Step 5: Create requirements.txt

Create `requirements.txt`:

```
# Testing
pytest>=6.0.0
pytest-cov>=2.10.0

# Documentation (optional)
sphinx>=3.0.0
sphinx-rtd-theme>=0.5.0

# Note: Maya's Python environment includes:
# - PySide2 (Maya 2022-2023)
# - PySide6 (Maya 2024+)
# - maya.cmds, maya.OpenMaya (Maya API)
```

#### Step 6: Initial Commit

```bash
# Stage all files
git add .

# Create initial commit
git commit -m "Initial repository structure

- Add directory structure for all modules
- Add .gitignore for Python and Maya files
- Add README.md with project overview
- Add requirements.txt for dependencies
- Add spec/ directory with documentation"

# Push to GitHub
git push -u origin main
```

### 0.4 Branch Strategy

#### Main Branches

- **`main`** - Production-ready code, protected branch
- **`develop`** - Integration branch for features

#### Feature Branches

Use the following naming convention for feature branches:

```
feature/P{phase}-{module}-{task-id}-{short-description}
```

Examples:
- `feature/P1-config-01-project-config-loader`
- `feature/P2-token-01-token-expansion-engine`
- `feature/P3-layer-01-display-layer-creation`

#### Workflow

1. **Create feature branch from `develop`:**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/P1-config-01-project-config-loader
   ```

2. **Implement task with commits:**
   ```bash
   git add config/project_config.py
   git commit -m "[P1-CONFIG-01] Implement ProjectConfig class

   - Add JSON config loading
   - Add schema validation
   - Add getter methods for templates and roots
   - Add error handling for missing configs"
   ```

3. **Push feature branch:**
   ```bash
   git push -u origin feature/P1-config-01-project-config-loader
   ```

4. **Create Pull Request:**
   - Go to https://github.com/katha-begin/maya-multishot/pulls
   - Click "New Pull Request"
   - Base: `develop`, Compare: `feature/P1-config-01-project-config-loader`
   - Add description referencing task ID and acceptance criteria
   - Request review

5. **After PR approval and merge:**
   ```bash
   git checkout develop
   git pull origin develop
   git branch -d feature/P1-config-01-project-config-loader
   ```

### 0.5 Commit Message Convention

Use the following format for commit messages:

```
[TASK-ID] Short description (50 chars or less)

Detailed explanation of changes:
- Bullet point 1
- Bullet point 2
- Bullet point 3

Refs: #issue-number (if applicable)
```

Examples:
```
[P1-CONFIG-01] Implement ProjectConfig class

- Add JSON config loading from repository and workspace
- Add schema validation with version checking
- Add getter methods for templates, roots, and patterns
- Add error handling for missing/invalid configs
- Add unit tests with 95% coverage

Refs: #1
```

### 0.6 Pull Request Template

Create `.github/pull_request_template.md`:

```markdown
## Task Information

**Task ID:** [P#-MODULE-##]
**Task Name:** [Task name from tasks.md]
**Phase:** [Phase number and name]

## Changes

### Summary
[Brief description of changes]

### Acceptance Criteria
- [ ] Criterion 1 from tasks.md
- [ ] Criterion 2 from tasks.md
- [ ] Criterion 3 from tasks.md
- [ ] Criterion 4 from tasks.md
- [ ] Criterion 5 from tasks.md

## Testing

### Unit Tests
- [ ] All unit tests pass
- [ ] New tests added for new functionality
- [ ] Code coverage: ___%

### Manual Testing
- [ ] Tested in Maya 2022
- [ ] Tested in Maya 2023
- [ ] Tested in Maya 2024 (if applicable)

## Documentation

- [ ] Code comments added
- [ ] Docstrings updated
- [ ] User documentation updated (if applicable)
- [ ] API documentation updated (if applicable)

## Checklist

- [ ] Code follows project style guidelines
- [ ] No merge conflicts with develop branch
- [ ] All tests pass
- [ ] Documentation is complete
- [ ] Ready for review

## Related Issues

Closes #[issue number]
Related to #[issue number]

## Screenshots (if applicable)

[Add screenshots for UI changes]
```

### 0.7 Development Workflow Summary

1. ✅ **Setup Repository** - Clone and create directory structure
2. ✅ **Create Feature Branch** - Branch from `develop` with proper naming
3. ✅ **Implement Task** - Follow acceptance criteria from `tasks.md`
4. ✅ **Write Tests** - Achieve 90%+ coverage
5. ✅ **Commit Changes** - Use proper commit message format
6. ✅ **Push Branch** - Push to GitHub
7. ✅ **Create PR** - Use PR template, reference task ID
8. ✅ **Code Review** - Address review comments
9. ✅ **Merge** - Merge to `develop` after approval
10. ✅ **Cleanup** - Delete feature branch

---

## 1. Project Overview

### 1.1 Purpose

A Maya pipeline tool for managing context-aware file paths across multiple shots within a single scene. The tool resolves template paths with tokens to actual file paths, enabling artists to switch between shots without manual path editing.

### 1.2 Core Concept

```
TEMPLATE PATH (stored)
    |
    v
TOKEN EXPANSION (runtime)
    |
    v
RESOLVED PATH (applied to Maya node)
```

### 1.3 Key Principles

| Principle | Description |
|-----------|-------------|
| Path-only | Tool modifies file paths only, never scene hierarchy |
| Shared nodes | Same proxy/reference node serves multiple shots |
| Per-shot versioning | Each shot can have different version of same asset |
| Display layer visibility | Shot visibility controlled via display layers |
| Scene persistence | All data stored in scene file via custom nodes |
| Cross-platform | Windows and Linux path resolution |
| Legacy support | Python 2.7 and Maya 2022 compatible |

### 1.4 Supported Node Types

| Node Type | Maya Type | Path Attribute |
|-----------|-----------|----------------|
| Arnold StandIn | aiStandIn | dso |
| Redshift Proxy | RedshiftProxyMesh | fileName |
| Maya Reference | reference | (API) |

---

## 2. Path Structure and Tokens

### 2.1 Folder Structure Analysis

```
V:\SWA\all\scene\Ep04\sq0070\SH0170\anim\publish\v001\Ep04_sq0070_SH0170__CHAR_CatStompie_002.abc
|   |   |    |    |     |      |     |      |     |              |
|   |   |    |    |     |      |     |      |     |              +-- Filename
|   |   |    |    |     |      |     |      |     +-- Version
|   |   |    |    |     |      |     |      +-- Publish type
|   |   |    |    |     |      |     +-- Department
|   |   |    |    |     |      +-- Shot
|   |   |    |    |     +-- Sequence
|   |   |    |    +-- Episode
|   |   |    +-- Scene data (shot work)
|   |   +-- Static shared directory
|   +-- Project code
+-- Drive (Windows)
```

### 2.2 Platform Root Mapping

| Platform | Pattern | Example |
|----------|---------|---------|
| Windows | `{DRIVE}:\{PROJECT}` | `V:\SWA` |
| Linux | `/mnt/{client}_{project}_{drive}/{PROJECT}` | `/mnt/igloo_swa_v/SWA` |

### 2.3 Token Definitions

**Context Tokens (Scene-level)**

| Token | Description | Example | Storage |
|-------|-------------|---------|---------|
| `$project` | Project code | SWA | CTX_Manager node |
| `$ep` | Episode | Ep04 | CTX_Manager node |
| `$seq` | Sequence | sq0070 | CTX_Manager node |
| `$root` | Platform root path | V:/SWA | Resolved at runtime |

**Shot Tokens (Shot-level)**

| Token | Description | Example | Storage |
|-------|-------------|---------|---------|
| `$shot` | Shot code | SH0170 | CTX_Shot node |

**Asset Tokens (Asset-level)**

| Token | Description | Example | Storage |
|-------|-------------|---------|---------|
| `$dept` | Department | anim | CTX_Asset node |
| `$ver` | Version | v001 | CTX_Asset node |
| `$assetType` | Asset type | CHAR | CTX_Asset node |
| `$assetName` | Asset name | CatStompie | CTX_Asset node |
| `$variant` | Instance index | 002 | CTX_Asset node |
| `$ext` | File extension | abc | CTX_Asset node |

### 2.4 File Naming and Namespace Convention

**File Naming Pattern:**
```
$ep_$seq_$shot__$assetType_$assetName_$variant.$ext
{shotContext}__{namespace}.{ext}
```

**Namespace Definition:**

The namespace is defined as: `$assetType_$assetName_$variant`

The double underscore (`__`) separates shot context from namespace.

**Examples:**
- Full filename: `Ep04_sq0070_SH0170__CHAR_CatStompie_002.abc`
  - Shot context: `Ep04_sq0070_SH0170`
  - Namespace: `CHAR_CatStompie_002`
- When creating assets in Maya, use the namespace format for node naming

### 2.5 Template Examples

**Shot Cache Template**
```
$root/all/scene/$ep/$seq/$shot/$dept/publish/$ver/$ep_$seq_$shot__$assetType_$assetName_$variant.$ext
```

**Resolved Path (Windows)**
```
V:/SWA/all/scene/Ep04/sq0070/SH0170/anim/publish/v001/Ep04_sq0070_SH0170__CHAR_CatStompie_002.abc
```

**Resolved Path (Linux)**
```
/mnt/igloo_swa_v/SWA/all/scene/Ep04/sq0070/SH0170/anim/publish/v001/Ep04_sq0070_SH0170__CHAR_CatStompie_002.abc
```

---

## 3. Multi-Shot Data Model

### 3.1 Custom Node Hierarchy

```
CTX_Manager (network node)
    |
    +-- CTX_Shot_SH0170 (network node)
    |       |
    |       +-- CTX_Asset_CHAR_CatStompie_001 (network node)
    |       +-- CTX_Asset_CHAR_CatStompie_002 (network node)
    |       +-- CTX_Asset_PROP_TreeBig_001 (network node)
    |
    +-- CTX_Shot_SH0180 (network node)
            |
            +-- CTX_Asset_CHAR_CatStompie_001 (network node)
            +-- CTX_Asset_CHAR_DogBounce_001 (network node)
```

### 3.2 CTX_Manager Node Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| ctxVersion | string | Tool version for compatibility |
| project | string | Project code |
| episode | string | Episode code |
| sequence | string | Sequence code |
| activeShot | string | Currently active shot code |
| templateCache | string | JSON string of path templates |
| configPath | string | Path to project config file |

### 3.3 CTX_Shot Node Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| shotCode | string | Shot code (e.g., SH0170) |
| frameStart | long | Start frame |
| frameEnd | long | End frame |
| displayLayer | string | Associated display layer name |
| parentManager | message | Connection to CTX_Manager |

### 3.4 CTX_Asset Node Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| assetName | string | Asset name (e.g., CatStompie) |
| assetType | string | Asset type (e.g., CHAR) |
| variant | string | Instance index (e.g., 001) |
| department | string | Source department (e.g., anim) |
| version | string | Version (e.g., v001) |
| template | string | Path template with tokens |
| extension | string | File extension (e.g., abc) |
| nodeType | string | Target node type (aiStandIn, RedshiftProxyMesh, reference) |
| targetNode | message | Connection to actual Maya node |
| parentShot | message | Connection to CTX_Shot |
| enabled | bool | Whether asset is active |

### 3.5 Node Relationship Diagram

```
+------------------+
|   CTX_Manager    |
|------------------|
| project          |
| episode          |       +---------------------------+
| sequence         |       |  Display Layer            |
| activeShot ------+------>|  CTX_Ep04_sq0070_SH0170   |
+--------+---------+       +---------------------------+
         |
         | (parent)
         v
+------------------+       +------------------+
|  CTX_Shot_SH0170 |       |  aiStandIn       |
|------------------|       |  CatStompie_001  |
| shotCode         |       +--------+---------+
| displayLayer ----+------>         ^
+--------+---------+                |
         |                          | (targetNode)
         | (parent)                 |
         v                          |
+------------------+                |
| CTX_Asset_...    |----------------+
|------------------|
| assetName        |
| version          |
| template         |
+------------------+
```

### 3.6 Shared Node Concept

One Maya node (StandIn/Proxy/Reference) can be referenced by multiple CTX_Asset nodes across different shots:

```
CTX_Shot_SH0170
    +-- CTX_Asset_CHAR_CatStompie_001
            targetNode --> CatStompie_001_AIS (aiStandIn)
            version = v003

CTX_Shot_SH0180
    +-- CTX_Asset_CHAR_CatStompie_001
            targetNode --> CatStompie_001_AIS (same aiStandIn)
            version = v004  <-- Different version!
```

When switching from SH0170 to SH0180:
1. Find CTX_Asset for CatStompie_001 in SH0180
2. Get version (v004) and template
3. Resolve path with SH0180 context
4. Apply resolved path to CatStompie_001_AIS node

---

## 4. Display Layer Management

### 4.1 Naming Convention

```
CTX_{epCode}_{seqCode}_{shotCode}

Examples:
- CTX_Ep04_sq0070_SH0170
- CTX_Ep04_sq0070_SH0180
- CTX_Ep05_sq0010_SH0010
```

**Benefits:**
- Clear hierarchy when working across multiple episodes
- Easier to identify which episode/sequence a shot belongs to
- Better organization in outliner

### 4.2 Display Layer Behavior

| Action | Display Layer State |
|--------|---------------------|
| Add shot to scene | Create display layer CTX_{ep}_{seq}_{shot} |
| Remove shot from scene | Delete display layer CTX_{ep}_{seq}_{shot} |
| Switch active shot | Set active shot layer visible, others invisible |
| Add asset to shot | Add asset node to shot's display layer |
| Remove asset from shot | Remove asset node from shot's display layer |

### 4.3 Display Layer Attributes

| Attribute | Value | Purpose |
|-----------|-------|---------|
| displayType | 0 | Normal display |
| visibility | 1/0 | Controlled by shot activation |
| hideOnPlayback | 0 | Show during playback |
| texturing | 1 | Enable textures |

### 4.4 Asset Visibility Logic

```
For each asset node:
    If asset exists in active shot:
        Add to active shot display layer (visible)
    Else if asset exists in other shots:
        Add to those shot display layers (invisible)
    Else:
        Not managed by context system
```

---

## 5. Project Configuration Schema

### 5.1 Config File Location

**Repository Location (Recommended):**
```
{code_repository}/config/ctx_config.json
```

**Project Workspace Location (Legacy):**
```
{project_root}/config/ctx_config.json

Windows: V:/SWA/config/ctx_config.json
Linux:   /mnt/igloo_swa_v/SWA/config/ctx_config.json
```

**Rationale:**
- Config should be version controlled in code repository
- Separates code/configuration from production data
- Allows for environment-specific overrides
- Project workspace path can be specified in config

### 5.2 Configuration Schema

**Configuration Structure:**

The configuration is organized into three layers:

1. **`roots`** - Filesystem root paths only (e.g., `PROJ_ROOT: "V:/"`)
2. **`project`** - Project identifier (e.g., `"SWA"`)
3. **`static_paths`** - Static path segments (e.g., `scene_base: "all/scene"`)

**Path Construction:**
```
Full Path = $PROJ_ROOT + $project + $static_path + dynamic_tokens
Example:   V:/         + SWA      + all/scene    + Ep04/sq0070/SH0170/anim/publish
```

**Configuration JSON:**

```json
{
    "schema_version": "1.0",

    "project": {
        "code": "SWA",
        "name": "Super Wizard Adventure",
        "client": "igloo"
    },

    "roots": {
        "PROJ_ROOT": "V:/"
    },

    "static_paths": {
        "scene_base": "all/scene",
        "asset_base": "all/asset",
        "config_base": "config"
    },

    "templates": {
        "shot_cache": "$PROJ_ROOT/$project/$scene_base/$ep/$seq/$shot/$dept/publish/$ver/$ep_$seq_$shot__$assetType_$assetName_$variant.$ext",
        "shot_work": "$PROJ_ROOT/$project/$scene_base/$ep/$seq/$shot/$dept/work",
        "shot_publish": "$PROJ_ROOT/$project/$scene_base/$ep/$seq/$shot/$dept/publish/$ver"
    },

    "platform_mapping": {
        "windows": {
            "PROJ_ROOT": "V:/"
        },
        "linux": {
            "PROJ_ROOT": "/mnt/igloo_swa_v/"
        }
    },
    
    "departments": [
        {"code": "anim", "name": "Animation"},
        {"code": "layout", "name": "Layout"},
        {"code": "light", "name": "Lighting"},
        {"code": "fx", "name": "Effects"}
    ],
    
    "asset_types": [
        {"code": "CHAR", "name": "Character"},
        {"code": "PROP", "name": "Prop"},
        {"code": "ENV", "name": "Environment"},
        {"code": "VEH", "name": "Vehicle"}
    ],
    
    "file_extensions": {
        "cache": ["abc", "usd", "usda", "usdc"],
        "proxy_arnold": ["ass"],
        "proxy_redshift": ["rs"],
        "scene": ["ma", "mb"]
    },
    
    "patterns": {
        "episode": "Ep\\d+",
        "sequence": "sq\\d+",
        "shot": "SH\\d+",
        "version": "v\\d{3,4}"
    },
    
    "cache": {
        "last_updated": "2024-01-15T10:30:00",
        "episodes": [],
        "sequences": {},
        "shots": {},
        "assets": {}
    }
}
```

### 5.3 Cache Structure

```json
{
    "cache": {
        "last_updated": "2024-01-15T10:30:00",

        "episodes": ["Ep01", "Ep02", "Ep03", "Ep04"],

        "sequences": {
            "Ep04": ["sq0010", "sq0020", "sq0070"]
        },

        "shots": {
            "Ep04/sq0070": ["SH0170", "SH0180", "SH0190", "SH0200"]
        },

        "assets": {
            "CHAR": [
                "CHAR_CatStompie_001",
                "CHAR_CatStompie_002",
                "CHAR_DogBounce_001",
                "CHAR_WizardOld_001"
            ],
            "PROP": [
                "PROP_TreeBig_001",
                "PROP_RockMedium_001",
                "PROP_ChestWooden_001"
            ],
            "ENV": [
                "ENV_ForestDay_001",
                "ENV_CastleInterior_001"
            ],
            "VEH": [
                "VEH_CartHorse_001",
                "VEH_ShipFlying_001"
            ]
        },

        "versions": {
            "V:/SWA/all/scene/Ep04/sq0070/SH0170/anim/publish": {
                "CHAR_CatStompie_001": ["v001", "v002", "v003"],
                "CHAR_CatStompie_002": ["v001", "v002"],
                "CHAR_DogBounce_001": ["v001", "v002"]
            },
            "V:/SWA/all/scene/Ep04/sq0070/SH0180/anim/publish": {
                "CHAR_CatStompie_001": ["v001", "v002", "v003", "v004"],
                "CHAR_DogBounce_001": ["v001"]
            }
        }
    }
}
```

**Key Changes:**
1. **Assets**: Now store full asset names including type, name, and variant (e.g., `CHAR_CatStompie_001`)
2. **Versions**: Keyed by full publish directory path, not partial path
3. **Asset names**: Support both full format (`Ep04_sq0070_SH0170__CHAR_CatStompie_001`) and namespace format (`CHAR_CatStompie_001`)

### 5.4 Path Builder Engine

The path builder engine resolves file paths from asset names and context.

**Input Formats:**
1. Full filename: `Ep04_sq0070_SH0170__CHAR_CatStompie_002.abc`
2. Namespace only: `CHAR_CatStompie_002` (requires context)

**Resolution Process:**
```python
def build_path(asset_name, context, version, extension):
    """
    Build full path from asset name and context.

    Args:
        asset_name: Full name or namespace format
        context: {ep, seq, shot, dept}
        version: Version string (e.g., 'v003')
        extension: File extension (e.g., 'abc')

    Returns:
        Resolved file path
    """
    # Parse asset name
    if '__' in asset_name:
        # Full format: extract both context and namespace
        shot_context, namespace = asset_name.split('__')
        # Validate against provided context
    else:
        # Namespace only: use provided context
        namespace = asset_name

    # Parse namespace
    parts = namespace.split('_')
    asset_type = parts[0]
    asset_name = '_'.join(parts[1:-1])
    variant = parts[-1]

    # Build path using template
    template = "$root/all/scene/$ep/$seq/$shot/$dept/publish/$ver/$ep_$seq_$shot__$assetType_$assetName_$variant.$ext"

    return resolve_template(template, context, asset_type, asset_name, variant, version, extension)
```

**Examples:**
```python
# Example 1: Full filename
build_path(
    "Ep04_sq0070_SH0170__CHAR_CatStompie_002.abc",
    context={},  # Extracted from filename
    version="v003",
    extension="abc"
)
# Returns: V:/SWA/all/scene/Ep04/sq0070/SH0170/anim/publish/v003/Ep04_sq0070_SH0170__CHAR_CatStompie_002.abc

# Example 2: Namespace only
build_path(
    "CHAR_CatStompie_002",
    context={"ep": "Ep04", "seq": "sq0070", "shot": "SH0170", "dept": "anim"},
    version="v003",
    extension="abc"
)
# Returns: V:/SWA/all/scene/Ep04/sq0070/SH0170/anim/publish/v003/Ep04_sq0070_SH0170__CHAR_CatStompie_002.abc
```

---

## 6. Code Architecture

### 6.1 Package Structure

```
ctx_manager/
|
+-- __init__.py
|
+-- config/
|   +-- __init__.py
|   +-- project_config.py      # Project configuration loader
|   +-- platform.py            # OS detection and path mapping
|   +-- templates.py           # Path template definitions
|
+-- core/
|   +-- __init__.py
|   +-- context.py             # Context management (scene-level)
|   +-- tokens.py              # Token expansion engine
|   +-- resolver.py            # Path resolution
|   +-- nodes.py               # Maya node operations (proxy, reference)
|   +-- custom_nodes.py        # CTX_Manager, CTX_Shot, CTX_Asset
|   +-- display_layers.py      # Display layer management
|   +-- cache.py               # Version cache management
|
+-- tools/
|   +-- __init__.py
|   +-- shot_manager.py        # Add/remove/switch shots
|   +-- asset_manager.py       # Add/remove/update assets
|   +-- importer.py            # Import assets to shot
|   +-- converter.py           # Convert existing scene to context
|   +-- validator.py           # Validate paths and data
|   +-- saver.py               # Save scene to shot
|
+-- ui/
|   +-- __init__.py
|   +-- main_window.py         # Main dockable panel
|   +-- shot_widget.py         # Shot list widget
|   +-- asset_widget.py        # Asset list widget
|   +-- browser_dialog.py      # Asset browser dialog
|   +-- settings_dialog.py     # Settings dialog
|   +-- utils.py               # UI utilities
|
+-- farm/
|   +-- __init__.py
|   +-- callbacks.py           # Pre-render callbacks
|   +-- export.py              # Export scene per shot
|
+-- tests/
|   +-- __init__.py
|   +-- test_tokens.py
|   +-- test_resolver.py
|   +-- test_custom_nodes.py
|
+-- resources/
|   +-- default_config.json    # Default project config template
```

### 6.2 Module Dependency Diagram

```
                    +-------------+
                    |   config/   |
                    +------+------+
                           |
              +------------+------------+
              |            |            |
              v            v            v
        +---------+  +---------+  +-----------+
        | tokens  |  | platform|  | templates |
        +----+----+  +----+----+  +-----+-----+
             |            |             |
             +------------+-------------+
                          |
                          v
                    +-----------+
                    | resolver  |
                    +-----+-----+
                          |
         +----------------+----------------+
         |                |                |
         v                v                v
   +-----------+   +-------------+   +---------------+
   |   nodes   |   | custom_nodes|   | display_layers|
   +-----+-----+   +------+------+   +-------+-------+
         |                |                  |
         +----------------+------------------+
                          |
                          v
                    +-----------+
                    |   tools/  |
                    +-----+-----+
                          |
                          v
                    +-----------+
                    |    ui/    |
                    +-----------+
```

---

## 7. Core Modules Specification

### 7.1 config/platform.py

```python
"""
Platform detection and path mapping.

Handles cross-platform path resolution between Windows and Linux.
"""

# Constants
PLATFORM_WINDOWS = "windows"
PLATFORM_LINUX = "linux"

def get_current_platform():
    """
    Detect current operating system.
    
    Returns:
        str: PLATFORM_WINDOWS or PLATFORM_LINUX
    """
    pass

def get_root_path(project_config, platform=None):
    """
    Get project root path for specified platform.
    
    Args:
        project_config (dict): Project configuration dictionary
        platform (str, optional): Target platform. Defaults to current.
    
    Returns:
        str: Root path for the platform
    """
    pass

def convert_path(path, source_platform, target_platform, project_config):
    """
    Convert path between platforms.
    
    Args:
        path (str): Source path
        source_platform (str): Source platform
        target_platform (str): Target platform
        project_config (dict): Project configuration
    
    Returns:
        str: Converted path
    """
    pass

def normalize_path(path):
    """
    Normalize path separators for current platform.
    
    Args:
        path (str): Input path
    
    Returns:
        str: Normalized path with correct separators
    """
    pass
```

### 7.2 config/project_config.py

```python
"""
Project configuration management.

Loads, saves, and validates project configuration files.
"""

CONFIG_FILENAME = "ctx_config.json"
SCHEMA_VERSION = "1.0"

class ProjectConfig(object):
    """
    Project configuration manager.
    
    Attributes:
        config_path (str): Path to configuration file
        data (dict): Configuration data
    """
    
    def __init__(self, config_path=None):
        """
        Initialize project configuration.
        
        Args:
            config_path (str, optional): Path to config file
        """
        pass
    
    def load(self, config_path):
        """
        Load configuration from file.
        
        Args:
            config_path (str): Path to config file
        
        Returns:
            bool: True if successful
        
        Raises:
            IOError: If file cannot be read
            ValueError: If JSON is invalid
        """
        pass
    
    def save(self):
        """
        Save configuration to file.
        
        Returns:
            bool: True if successful
        """
        pass
    
    def get_template(self, template_name):
        """
        Get path template by name.
        
        Args:
            template_name (str): Template name (e.g., 'shot_cache')
        
        Returns:
            str: Template string or None
        """
        pass
    
    def get_root(self, platform=None):
        """
        Get project root for platform.
        
        Args:
            platform (str, optional): Target platform
        
        Returns:
            str: Root path
        """
        pass
    
    def update_cache(self, cache_type, data):
        """
        Update cache section.
        
        Args:
            cache_type (str): Cache type (episodes, sequences, etc.)
            data: Cache data
        """
        pass
    
    def validate(self):
        """
        Validate configuration integrity.
        
        Returns:
            tuple: (is_valid, list of errors)
        """
        pass
```

### 7.3 core/tokens.py

```python
"""
Token expansion engine.

Handles parsing and expanding tokens in path templates.
"""

# Token prefix
TOKEN_PREFIX = "$"

# Token categories
CONTEXT_TOKENS = ["project", "ep", "seq", "root"]
SHOT_TOKENS = ["shot"]
ASSET_TOKENS = ["dept", "ver", "assetType", "assetName", "variant", "ext"]

ALL_TOKENS = CONTEXT_TOKENS + SHOT_TOKENS + ASSET_TOKENS

def extract_tokens(template):
    """
    Extract all tokens from a template string.
    
    Args:
        template (str): Template string with $tokens
    
    Returns:
        list: List of token names (without $ prefix)
    
    Example:
        >>> extract_tokens("$root/$ep/$shot/file.abc")
        ['root', 'ep', 'shot']
    """
    pass

def expand_tokens(template, token_values):
    """
    Expand tokens in template with provided values.
    
    Args:
        template (str): Template string with $tokens
        token_values (dict): Dictionary of token: value pairs
    
    Returns:
        str: Expanded string
    
    Example:
        >>> expand_tokens("$root/$shot/file.abc", {"root": "V:/SWA", "shot": "SH0170"})
        'V:/SWA/SH0170/file.abc'
    """
    pass

def create_template_from_path(resolved_path, token_values):
    """
    Convert resolved path back to template by replacing values with tokens.
    
    Args:
        resolved_path (str): Fully resolved path
        token_values (dict): Dictionary of token: value pairs
    
    Returns:
        str: Template string with $tokens
    
    Example:
        >>> create_template_from_path(
        ...     "V:/SWA/Ep04/SH0170/file.abc",
        ...     {"root": "V:/SWA", "ep": "Ep04", "shot": "SH0170"}
        ... )
        '$root/$ep/$shot/file.abc'
    """
    pass

def detect_tokens_from_path(path, patterns):
    """
    Auto-detect token values from a path using regex patterns.
    
    Args:
        path (str): File path to analyze
        patterns (dict): Dictionary of token: regex_pattern
    
    Returns:
        dict: Detected token values
    
    Example:
        >>> patterns = {"ep": r"(Ep\d+)", "shot": r"(SH\d+)"}
        >>> detect_tokens_from_path("V:/SWA/Ep04/SH0170/file.abc", patterns)
        {'ep': 'Ep04', 'shot': 'SH0170'}
    """
    pass

def validate_token_values(token_values, required_tokens):
    """
    Validate that all required tokens have values.
    
    Args:
        token_values (dict): Token values to validate
        required_tokens (list): List of required token names
    
    Returns:
        tuple: (is_valid, list of missing tokens)
    """
    pass
```

### 7.4 core/resolver.py

```python
"""
Path resolution engine.

Resolves template paths to actual file paths using context.
"""

class PathResolver(object):
    """
    Resolves template paths using context and configuration.
    
    Attributes:
        config (ProjectConfig): Project configuration
        context (dict): Current context values
    """
    
    def __init__(self, config):
        """
        Initialize resolver with configuration.
        
        Args:
            config (ProjectConfig): Project configuration
        """
        pass
    
    def set_context(self, **kwargs):
        """
        Set context values.
        
        Args:
            **kwargs: Token values (project, ep, seq, shot, etc.)
        """
        pass
    
    def get_context(self):
        """
        Get current context values.
        
        Returns:
            dict: Current context
        """
        pass
    
    def resolve(self, template, asset_data=None):
        """
        Resolve template to actual path.
        
        Args:
            template (str): Path template with tokens
            asset_data (dict, optional): Asset-specific token values
        
        Returns:
            str: Resolved path
        """
        pass
    
    def resolve_for_shot(self, template, shot_code, asset_data=None):
        """
        Resolve template for specific shot.
        
        Args:
            template (str): Path template
            shot_code (str): Shot code
            asset_data (dict, optional): Asset-specific data
        
        Returns:
            str: Resolved path for shot
        """
        pass
    
    def create_template(self, resolved_path):
        """
        Create template from resolved path.
        
        Args:
            resolved_path (str): Fully resolved path
        
        Returns:
            str: Template with tokens
        """
        pass
    
    def detect_context(self, path):
        """
        Detect context from path.
        
        Args:
            path (str): File path
        
        Returns:
            dict: Detected context values
        """
        pass
    
    def validate_path(self, path):
        """
        Check if resolved path exists.
        
        Args:
            path (str): Path to validate
        
        Returns:
            bool: True if path exists
        """
        pass
```

### 7.5 core/custom_nodes.py

```python
"""
Custom Maya network nodes for context data storage.

Defines CTX_Manager, CTX_Shot, and CTX_Asset node types.
"""

# Node type identifiers
NODE_TYPE_MANAGER = "CTX_Manager"
NODE_TYPE_SHOT = "CTX_Shot"
NODE_TYPE_ASSET = "CTX_Asset"

# Attribute definitions
MANAGER_ATTRS = {
    "ctxVersion": {"type": "string", "default": "1.0"},
    "project": {"type": "string", "default": ""},
    "episode": {"type": "string", "default": ""},
    "sequence": {"type": "string", "default": ""},
    "activeShot": {"type": "string", "default": ""},
    "configPath": {"type": "string", "default": ""},
}

SHOT_ATTRS = {
    "shotCode": {"type": "string", "default": ""},
    "frameStart": {"type": "long", "default": 1001},
    "frameEnd": {"type": "long", "default": 1100},
    "displayLayer": {"type": "string", "default": ""},
}

ASSET_ATTRS = {
    "assetName": {"type": "string", "default": ""},
    "assetType": {"type": "string", "default": ""},
    "variant": {"type": "string", "default": "001"},
    "department": {"type": "string", "default": ""},
    "version": {"type": "string", "default": "v001"},
    "template": {"type": "string", "default": ""},
    "extension": {"type": "string", "default": "abc"},
    "nodeType": {"type": "string", "default": ""},
    "enabled": {"type": "bool", "default": True},
}


class CTXManagerNode(object):
    """
    Wrapper for CTX_Manager network node.
    
    Attributes:
        node_name (str): Maya node name
    """
    
    @classmethod
    def create(cls):
        """
        Create new CTX_Manager node in scene.
        
        Returns:
            CTXManagerNode: New manager instance
        
        Raises:
            RuntimeError: If manager already exists
        """
        pass
    
    @classmethod
    def get(cls):
        """
        Get existing CTX_Manager node.
        
        Returns:
            CTXManagerNode: Existing manager or None
        """
        pass
    
    @classmethod
    def get_or_create(cls):
        """
        Get existing or create new CTX_Manager.
        
        Returns:
            CTXManagerNode: Manager instance
        """
        pass
    
    def get_project(self):
        """Get project code."""
        pass
    
    def set_project(self, value):
        """Set project code."""
        pass
    
    def get_episode(self):
        """Get episode code."""
        pass
    
    def set_episode(self, value):
        """Set episode code."""
        pass
    
    def get_sequence(self):
        """Get sequence code."""
        pass
    
    def set_sequence(self, value):
        """Set sequence code."""
        pass
    
    def get_active_shot(self):
        """Get active shot code."""
        pass
    
    def set_active_shot(self, shot_code):
        """
        Set active shot and trigger path updates.
        
        Args:
            shot_code (str): Shot code to activate
        """
        pass
    
    def get_shots(self):
        """
        Get all CTX_Shot nodes connected to this manager.
        
        Returns:
            list: List of CTXShotNode instances
        """
        pass
    
    def add_shot(self, shot_code):
        """
        Add new shot to scene.
        
        Args:
            shot_code (str): Shot code
        
        Returns:
            CTXShotNode: New shot node
        """
        pass
    
    def remove_shot(self, shot_code):
        """
        Remove shot from scene.
        
        Args:
            shot_code (str): Shot code to remove
        """
        pass
    
    def get_context(self):
        """
        Get full context dictionary.
        
        Returns:
            dict: Context values
        """
        pass


class CTXShotNode(object):
    """
    Wrapper for CTX_Shot network node.
    
    Attributes:
        node_name (str): Maya node name
    """
    
    @classmethod
    def create(cls, manager, shot_code):
        """
        Create new CTX_Shot node.
        
        Args:
            manager (CTXManagerNode): Parent manager
            shot_code (str): Shot code
        
        Returns:
            CTXShotNode: New shot instance
        """
        pass
    
    def get_shot_code(self):
        """Get shot code."""
        pass
    
    def get_frame_range(self):
        """
        Get frame range.
        
        Returns:
            tuple: (start_frame, end_frame)
        """
        pass
    
    def set_frame_range(self, start, end):
        """Set frame range."""
        pass
    
    def get_display_layer(self):
        """Get associated display layer name."""
        pass
    
    def get_assets(self):
        """
        Get all CTX_Asset nodes for this shot.
        
        Returns:
            list: List of CTXAssetNode instances
        """
        pass
    
    def add_asset(self, asset_data):
        """
        Add asset to this shot.
        
        Args:
            asset_data (dict): Asset data dictionary
        
        Returns:
            CTXAssetNode: New asset node
        """
        pass
    
    def remove_asset(self, asset_node):
        """
        Remove asset from shot.
        
        Args:
            asset_node (CTXAssetNode): Asset to remove
        """
        pass
    
    def get_asset_by_target(self, target_node):
        """
        Find CTX_Asset by its target Maya node.
        
        Args:
            target_node (str): Maya node name
        
        Returns:
            CTXAssetNode: Asset node or None
        """
        pass


class CTXAssetNode(object):
    """
    Wrapper for CTX_Asset network node.
    
    Attributes:
        node_name (str): Maya node name
    """
    
    @classmethod
    def create(cls, shot, asset_data):
        """
        Create new CTX_Asset node.
        
        Args:
            shot (CTXShotNode): Parent shot
            asset_data (dict): Asset data
        
        Returns:
            CTXAssetNode: New asset instance
        """
        pass
    
    def get_asset_name(self):
        """Get asset name."""
        pass
    
    def get_asset_type(self):
        """Get asset type."""
        pass
    
    def get_variant(self):
        """Get variant/index."""
        pass
    
    def get_department(self):
        """Get source department."""
        pass
    
    def get_version(self):
        """Get version."""
        pass
    
    def set_version(self, version):
        """
        Set version and update path.
        
        Args:
            version (str): Version string (e.g., 'v001')
        """
        pass
    
    def get_template(self):
        """Get path template."""
        pass
    
    def set_template(self, template):
        """Set path template."""
        pass
    
    def get_target_node(self):
        """
        Get connected Maya node name.
        
        Returns:
            str: Maya node name or None
        """
        pass
    
    def set_target_node(self, node_name):
        """
        Connect to Maya node.
        
        Args:
            node_name (str): Maya node name
        """
        pass
    
    def get_node_type(self):
        """Get target node type (aiStandIn, etc.)."""
        pass
    
    def is_enabled(self):
        """Check if asset is enabled."""
        pass
    
    def set_enabled(self, enabled):
        """Set enabled state."""
        pass
    
    def get_identifier(self):
        """
        Get unique asset identifier.
        
        Returns:
            str: Identifier (e.g., 'CHAR_CatStompie_001')
        """
        pass
    
    def get_token_values(self):
        """
        Get all token values for this asset.
        
        Returns:
            dict: Token values
        """
        pass
```

### 7.6 core/display_layers.py

```python
"""
Display layer management for shot visibility.

Handles creation, modification, and visibility of shot display layers.
"""

# Naming pattern
DISPLAY_LAYER_PREFIX = "CTX_"

def get_layer_name(ep_code, seq_code, shot_code):
    """
    Get display layer name for shot.

    Args:
        ep_code (str): Episode code
        seq_code (str): Sequence code
        shot_code (str): Shot code

    Returns:
        str: Display layer name

    Example:
        >>> get_layer_name("Ep04", "sq0070", "SH0170")
        'CTX_Ep04_sq0070_SH0170'
    """
    pass

def create_display_layer(ep_code, seq_code, shot_code):
    """
    Create display layer for shot.

    Args:
        ep_code (str): Episode code
        seq_code (str): Sequence code
        shot_code (str): Shot code

    Returns:
        str: Created layer name
    """
    pass

def delete_display_layer(ep_code, seq_code, shot_code):
    """
    Delete display layer for shot.

    Args:
        ep_code (str): Episode code
        seq_code (str): Sequence code
        shot_code (str): Shot code
    """
    pass

def layer_exists(ep_code, seq_code, shot_code):
    """
    Check if display layer exists.

    Args:
        ep_code (str): Episode code
        seq_code (str): Sequence code
        shot_code (str): Shot code

    Returns:
        bool: True if exists
    """
    pass

def add_to_layer(ep_code, seq_code, shot_code, node_name):
    """
    Add node to shot display layer.

    Args:
        ep_code (str): Episode code
        seq_code (str): Sequence code
        shot_code (str): Shot code
        node_name (str): Maya node name
    """
    pass

def remove_from_layer(ep_code, seq_code, shot_code, node_name):
    """
    Remove node from shot display layer.

    Args:
        ep_code (str): Episode code
        seq_code (str): Sequence code
        shot_code (str): Shot code
        node_name (str): Maya node name
    """
    pass

def set_layer_visibility(ep_code, seq_code, shot_code, visible):
    """
    Set display layer visibility.

    Args:
        ep_code (str): Episode code
        seq_code (str): Sequence code
        shot_code (str): Shot code
        visible (bool): Visibility state
    """
    pass

def set_active_shot_visible(active_shot_context, all_shot_contexts):
    """
    Set active shot visible, hide others.

    Args:
        active_shot_context (dict): Active shot context {ep, seq, shot}
        all_shot_contexts (list): All shot contexts in scene
    """
    pass

def get_layer_members(ep_code, seq_code, shot_code):
    """
    Get all nodes in shot display layer.

    Args:
        ep_code (str): Episode code
        seq_code (str): Sequence code
        shot_code (str): Shot code

    Returns:
        list: Node names
    """
    pass

def get_all_ctx_layers():
    """
    Get all CTX display layers in scene.
    
    Returns:
        list: Layer names
    """
    pass
```

### 7.7 core/nodes.py

```python
"""
Maya node operations for proxies and references.

Handles reading and writing paths to Arnold StandIn,
Redshift Proxy, and Maya Reference nodes.
"""

# Supported node types
NODE_TYPES = {
    "aiStandIn": {
        "name": "Arnold StandIn",
        "path_attr": "dso",
    },
    "RedshiftProxyMesh": {
        "name": "Redshift Proxy",
        "path_attr": "fileName",
    },
    "reference": {
        "name": "Reference",
        "path_attr": None,
    },
}

def get_supported_types():
    """
    Get list of supported node types.
    
    Returns:
        list: Node type names
    """
    pass

def get_node_type_info(node_name):
    """
    Get type info for a Maya node.
    
    Args:
        node_name (str): Maya node name
    
    Returns:
        dict: Node type info or None
    """
    pass

def get_all_proxy_nodes():
    """
    Get all proxy nodes in scene.
    
    Returns:
        list: Node names
    """
    pass

def get_all_reference_nodes():
    """
    Get all valid reference nodes in scene.
    
    Returns:
        list: Reference node names
    """
    pass

def get_all_managed_nodes():
    """
    Get all nodes that can be managed.
    
    Returns:
        list: Node names
    """
    pass

def get_node_path(node_name):
    """
    Get current file path from node.
    
    Args:
        node_name (str): Maya node name
    
    Returns:
        str: File path or empty string
    """
    pass

def set_node_path(node_name, path, reload_reference=True):
    """
    Set file path on node.
    
    Args:
        node_name (str): Maya node name
        path (str): File path
        reload_reference (bool): Reload if reference
    
    Returns:
        bool: True if successful
    """
    pass

def reload_reference(ref_node, new_path):
    """
    Reload reference with new path.
    
    Args:
        ref_node (str): Reference node name
        new_path (str): New file path
    
    Returns:
        bool: True if successful
    """
    pass

def get_node_transform(node_name):
    """
    Get transform parent of shape node.
    
    Args:
        node_name (str): Shape node name
    
    Returns:
        str: Transform name or None
    """
    pass
```

---

## 8. UI Specification

### 8.1 Main Window Layout

```
+===========================================================================+
|  Context Manager                                              [_] [X]     |
+===========================================================================+
|  PROJECT [SWA______v]  EP [Ep04___v]  SEQ [sq0070_v]   [Settings] [Help] |
+---------------------------------------------------------------------------+
|                                                                           |
|  SHOTS IN SCENE                                            [+ Add Shot]   |
|  +-----------------------------------------------------------------------+|
|  | (*) SH0170   [1001-1050]   12 assets    [Edit] [Remove]              ||
|  | ( ) SH0180   [1001-1062]    8 assets    [Edit] [Remove]              ||
|  | ( ) SH0190   [1001-1045]    5 assets    [Edit] [Remove]              ||
|  +-----------------------------------------------------------------------+|
|                                                                           |
+---------------------------------------------------------------------------+
|                                                                           |
|  ASSETS IN SH0170                            [+ Import] [Convert Scene]   |
|  +-----------------------------------------------------------------------+|
|  | Type  | Name           | Var | Dept | Ver  | Status  | Actions       ||
|  |-------|----------------|-----|------|------|---------|---------------||
|  | CHAR  | CatStompie     | 001 | anim | v003 | Valid   | [^][v][X]     ||
|  | CHAR  | CatStompie     | 002 | anim | v003 | Valid   | [^][v][X]     ||
|  | CHAR  | DogBounce      | 001 | anim | v002 | Update  | [^][v][X]     ||
|  | PROP  | TreeBig        | 001 | anim | v001 | Missing | [^][v][X]     ||
|  +-----------------------------------------------------------------------+|
|                                                                           |
|  [^] Version Up   [v] Version Down   [X] Remove from shot                 |
|                                                                           |
+---------------------------------------------------------------------------+
|                                                                           |
|  ACTIONS                                                                  |
|  [Save to Shot]  [Validate All]  [Refresh Cache]  [Export for Farm]      |
|                                                                           |
+---------------------------------------------------------------------------+
|  Status: Ready                                                            |
+===========================================================================+
```

### 8.2 Widget Specifications

**Project Selector**
- Type: QComboBox
- Data source: Scanned project configs
- On change: Load project config, update EP/SEQ lists

**Episode/Sequence Selector**
- Type: QComboBox
- Data source: Project config cache
- On change: Update available shots

**Shot List**
- Type: QListWidget with custom item widget
- Features: Radio button for active shot
- Actions: Add, Edit, Remove
- Double-click: Set as active shot

**Asset Table**
- Type: QTableWidget
- Columns: Type, Name, Variant, Department, Version, Status, Actions
- Status colors: Green (Valid), Yellow (Update available), Red (Missing)
- Row selection: Multi-select enabled

### 8.3 Dialog Specifications

**Add Shot Dialog**
```
+------------------------------------------+
|  Add Shot to Scene                       |
+------------------------------------------+
|                                          |
|  Shot Code: [SH0200_______]              |
|                                          |
|  Frame Range:                            |
|  Start: [1001___]  End: [1100___]        |
|                                          |
|  [ ] Copy assets from: [SH0170___v]      |
|                                          |
|  [Add]  [Cancel]                         |
|                                          |
+------------------------------------------+
```

**Import Asset Dialog**
```
+------------------------------------------+
|  Import Asset                            |
+------------------------------------------+
|                                          |
|  Department: [anim_______v]              |
|  Asset Type: [CHAR_______v]              |
|  Asset:      [CatStompie_v]              |
|  Variant:    [001________]               |
|                                          |
|  Available Versions:                     |
|  +------------------------------------+  |
|  | (*) v003  (latest)                 |  |
|  | ( ) v002                           |  |
|  | ( ) v001                           |  |
|  +------------------------------------+  |
|                                          |
|  Preview:                                |
|  V:/.../SH0170/.../CHAR_CatStompie_001.. |
|  [Valid - File exists]                   |
|                                          |
|  Import as: (*) StandIn  ( ) Reference   |
|                                          |
|  [Import]  [Cancel]                      |
|                                          |
+------------------------------------------+
```

**Convert Scene Dialog**
```
+------------------------------------------+
|  Convert Scene to Context Mode           |
+------------------------------------------+
|                                          |
|  Discovered Nodes:                       |
|  +------------------------------------+  |
|  | [x] aiStandIn    CatStompie_001   |  |
|  | [x] aiStandIn    DogBounce_001    |  |
|  | [x] RSProxyMesh  TreeBig_001      |  |
|  | [x] reference    WizardRigRN      |  |
|  +------------------------------------+  |
|                                          |
|  Detected Context:                       |
|  Project: SWA                            |
|  Episode: Ep04                           |
|  Sequence: sq0070                        |
|  Shot: SH0170                            |
|                                          |
|  [Convert Selected]  [Cancel]            |
|                                          |
+------------------------------------------+
```

---

## 9. Use Cases and Workflows

### 9.1 UC01: Initial Setup

**Precondition:** New scene, no context data

**Steps:**
1. User opens Context Manager panel
2. User selects Project from dropdown
3. Tool loads project config
4. User selects Episode and Sequence
5. User clicks "Add Shot"
6. User enters shot code (e.g., SH0170)
7. Tool creates:
   - CTX_Manager node (if not exists)
   - CTX_Shot_SH0170 node
   - CTX_Ep04_sq0070_SH0170 display layer
8. Shot appears in shot list as active

### 9.2 UC02: Import Asset to Shot

**Precondition:** Scene has active shot

**Steps:**
1. User clicks "Import Asset"
2. Import dialog opens
3. User selects Department, Asset Type, Asset Name
4. Tool scans for available versions
5. User selects version
6. User selects import type (StandIn/Reference)
7. User clicks "Import"
8. Tool:
   - Creates Maya node (StandIn/Reference)
   - Creates CTX_Asset node
   - Links CTX_Asset to Maya node
   - Adds Maya node to shot display layer
   - Resolves path and applies to Maya node

### 9.3 UC03: Switch Active Shot

**Precondition:** Scene has multiple shots

**Steps:**
1. User clicks radio button for different shot (e.g., SH0180)
2. Tool:
   - Updates CTX_Manager.activeShot
   - Sets CTX_Ep04_sq0070_SH0180 display layer visible
   - Sets other display layers invisible
   - For each asset in SH0180:
     - Gets CTX_Asset data
     - Resolves path with SH0180 context
     - Updates Maya node path

### 9.4 UC04: Convert Existing Scene

**Precondition:** Scene has proxies/references without context data

**Steps:**
1. User clicks "Convert Scene"
2. Tool scans for proxy and reference nodes
3. Dialog shows discovered nodes
4. Tool auto-detects context from paths
5. User confirms context values
6. User selects nodes to convert
7. User clicks "Convert"
8. Tool:
   - Creates CTX_Manager with detected context
   - Creates CTX_Shot for detected shot
   - For each selected node:
     - Creates CTX_Asset
     - Generates template from resolved path
     - Links CTX_Asset to Maya node
     - Adds to display layer

### 9.5 UC05: Version Up Asset

**Precondition:** New version published

**Steps:**
1. User clicks "Refresh Cache"
2. Tool scans disk for new versions
3. Asset status updates to "Update Available"
4. User selects asset
5. User clicks "Version Up"
6. Tool:
   - Updates CTX_Asset.version
   - Resolves new path
   - Updates Maya node path

### 9.6 UC06: Save Scene to Shot

**Precondition:** Scene modified, ready to save

**Steps:**
1. User clicks "Save to Shot"
2. Dialog shows save options
3. User confirms target shot
4. User selects version (auto-increment or manual)
5. Tool:
   - Resolves save path from template
   - Creates directory if needed
   - Saves Maya scene
   - Updates status

### 9.7 UC07: Add Same Asset to Different Shot

**Precondition:** Asset exists in SH0170, user adds SH0180

**Steps:**
1. User adds SH0180 to scene
2. User switches to SH0180
3. User clicks "Import Asset"
4. User selects same asset (CatStompie_001)
5. User selects version (can be different from SH0170)
6. Tool:
   - Finds existing Maya node (CHAR_CatStompie_001_AIS)
   - Creates new CTX_Asset under SH0180
   - Links to same Maya node
   - Adds Maya node to CTX_Ep04_sq0070_SH0180 display layer
   - Does NOT create duplicate Maya node

---

## 10. File Naming Conventions

### 10.1 Maya Nodes

| Node Type | Pattern | Example |
|-----------|---------|---------|
| Manager | `CTX_Manager` | `CTX_Manager` |
| Shot | `CTX_Shot_{shot_code}` | `CTX_Shot_SH0170` |
| Asset | `CTX_Asset_{type}_{name}_{variant}_{shot}` | `CTX_Asset_CHAR_CatStompie_001_SH0170` |
| Display Layer | `CTX_{ep}_{seq}_{shot}` | `CTX_Ep04_sq0070_SH0170` |

### 10.2 Maya Node Naming (Created by Import)

**Namespace Format:** `{assetType}_{assetName}_{variant}`

| Node Type | Pattern | Example |
|-----------|---------|---------|
| StandIn Transform | `{assetType}_{assetName}_{variant}` | `CHAR_CatStompie_001` |
| StandIn Shape | `{assetType}_{assetName}_{variant}_AIS` | `CHAR_CatStompie_001_AIS` |
| RS Proxy Transform | `{assetType}_{assetName}_{variant}` | `CHAR_CatStompie_001` |
| RS Proxy Shape | `{assetType}_{assetName}_{variant}_RSP` | `CHAR_CatStompie_001_RSP` |
| Reference | `{assetType}_{assetName}_{variant}RN` | `CHAR_CatStompie_001RN` |

**Note:** When creating assets, the namespace `$assetType_$assetName_$variant` is used for Maya node naming.

### 10.3 Config Files

| File | Location | Purpose |
|------|----------|---------|
| Project Config | `{root}/config/ctx_config.json` | Project settings |
| User Prefs | `{maya_prefs}/ctx_manager_prefs.json` | User preferences |

---

## 11. Compatibility Requirements

### 11.1 Python Version

- Python 2.7 (Maya 2022 and earlier)
- Python 3.x (Maya 2023+)

**Compatibility Guidelines:**
```python
# Use future imports
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

# String handling
import sys
if sys.version_info[0] >= 3:
    string_types = str
else:
    string_types = basestring

# Use .format() instead of f-strings
# Bad:  f"Hello {name}"
# Good: "Hello {}".format(name)

# Dict iteration
# Bad:  for k, v in dict.items():  # Python 3 only efficient
# Good: for k in dict:
#           v = dict[k]

# Print function
# Always: print("message")
# Never:  print "message"
```

### 11.2 Maya Version

- Maya 2022 (minimum)
- Maya 2023
- Maya 2024
- Maya 2025

### 11.3 Qt Version

```python
# Qt import compatibility
try:
    from PySide2 import QtWidgets, QtCore, QtGui
    from shiboken2 import wrapInstance
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui
    from shiboken6 import wrapInstance
```

### 11.4 Character Encoding

- All strings: ASCII or UTF-8
- No emoji or special Unicode characters in UI
- File paths: ASCII only

### 11.5 OS Compatibility

| OS | Version | Notes |
|----|---------|-------|
| Windows | 10, 11 | Primary development |
| Linux | CentOS 7+, Rocky 8+ | Render farm |

---
