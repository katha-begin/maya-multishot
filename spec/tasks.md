# Context Variables Pipeline - Implementation Task List

**Version:** 1.1
**Last Updated:** 2026-02-14
**Status:** Planning Phase
**Repository:** https://github.com/katha-begin/maya-multishot.git

---

## Table of Contents

0. [Phase 0: Repository Setup](#phase-0-repository-setup)
1. [Quick Reference](#quick-reference)
2. [Pre-Implementation Checklist](#pre-implementation-checklist)
3. [Phase 1: Core Architecture & Data Model](#phase-1-core-architecture--data-model)
4. [Phase 2: Path Resolution & Token System](#phase-2-path-resolution--token-system)
5. [Phase 3: Display Layer Management](#phase-3-display-layer-management)
6. [Phase 4: Tools & UI](#phase-4-tools--ui)
7. [Phase 5: Testing, Validation & Documentation](#phase-5-testing-validation--documentation)
8. [Migration Strategy](#migration-strategy)
9. [Risk Assessment](#risk-assessment)
10. [Testing Strategy](#testing-strategy)

---

## Phase 0: Repository Setup

**Duration:** 1-2 days
**Focus:** Set up Git repository, directory structure, and development environment

⚠️ **IMPORTANT:** Complete Phase 0 before starting any implementation tasks.

---

### [P0-REPO-01] Clone Repository and Create Directory Structure

**Priority:** HIGH (Critical Path - Must Complete First)
**Complexity:** Simple (1-2 hours)
**Dependencies:** None

**Description:**
Clone the GitHub repository and create the complete directory structure for all modules as specified in spec.md Section 0.2.

**Spec Reference:** [spec.md Section 0.2, 0.3](spec/spec.md#02-initial-repository-structure)

**Acceptance Criteria:**
- [ ] Repository cloned from https://github.com/katha-begin/maya-multishot.git
- [ ] All directories created: `config/`, `core/`, `tools/`, `ui/`, `farm/`, `tests/`, `docs/`, `examples/`, `spec/`
- [ ] All `__init__.py` files created for Python packages
- [ ] `.gitignore` file created with Python and Maya exclusions
- [ ] `README.md` created with project overview
- [ ] `requirements.txt` created with dependencies
- [ ] Directory structure matches spec.md Section 0.2

**Implementation Steps:**
```bash
# Clone repository
git clone https://github.com/katha-begin/maya-multishot.git
cd maya-multishot

# Create directory structure
mkdir -p config core tools ui farm tests/test_data/{configs,scenes,caches} docs examples

# Create __init__.py files
touch config/__init__.py core/__init__.py tools/__init__.py ui/__init__.py farm/__init__.py tests/__init__.py

# Create .gitignore (see spec.md Section 0.3 for content)
# Create README.md (see spec.md Section 0.3 for content)
# Create requirements.txt (see spec.md Section 0.3 for content)
```

---

### [P0-REPO-02] Create Pull Request Template

**Priority:** HIGH
**Complexity:** Simple (30 minutes)
**Dependencies:** `[P0-REPO-01]`

**Description:**
Create GitHub Pull Request template to standardize PR submissions.

**Spec Reference:** [spec.md Section 0.6](spec/spec.md#06-pull-request-template)

**Acceptance Criteria:**
- [ ] `.github/` directory created
- [ ] `.github/pull_request_template.md` created
- [ ] Template includes task information section
- [ ] Template includes acceptance criteria checklist
- [ ] Template includes testing checklist
- [ ] Template includes documentation checklist

**Implementation Steps:**
```bash
mkdir -p .github
# Create pull_request_template.md (see spec.md Section 0.6 for content)
```

---

### [P0-REPO-03] Initial Commit and Push

**Priority:** HIGH
**Complexity:** Simple (15 minutes)
**Dependencies:** `[P0-REPO-01]`, `[P0-REPO-02]`

**Description:**
Create initial commit with repository structure and push to GitHub.

**Spec Reference:** [spec.md Section 0.3](spec/spec.md#03-git-setup-instructions)

**Acceptance Criteria:**
- [ ] All files staged for commit
- [ ] Initial commit created with proper message format
- [ ] Commit pushed to `main` branch
- [ ] Repository visible on GitHub with all files

**Implementation Steps:**
```bash
git add .
git commit -m "Initial repository structure

- Add directory structure for all modules
- Add .gitignore for Python and Maya files
- Add README.md with project overview
- Add requirements.txt for dependencies
- Add .github/pull_request_template.md
- Add spec/ directory with documentation"

git push -u origin main
```

---

### [P0-REPO-04] Create Develop Branch

**Priority:** HIGH
**Complexity:** Simple (5 minutes)
**Dependencies:** `[P0-REPO-03]`

**Description:**
Create `develop` branch for feature integration.

**Spec Reference:** [spec.md Section 0.4](spec/spec.md#04-branch-strategy)

**Acceptance Criteria:**
- [ ] `develop` branch created from `main`
- [ ] `develop` branch pushed to GitHub
- [ ] Branch protection rules set (optional but recommended)

**Implementation Steps:**
```bash
git checkout -b develop
git push -u origin develop
```

**Optional: Set Branch Protection on GitHub**
- Go to repository Settings → Branches
- Add rule for `main` branch:
  - Require pull request reviews before merging
  - Require status checks to pass
  - Require branches to be up to date

---

### [P0-REPO-05] Verify Development Environment

**Priority:** HIGH
**Complexity:** Simple (30 minutes)
**Dependencies:** `[P0-REPO-04]`

**Description:**
Verify that development environment is properly set up for Maya development.

**Spec Reference:** [spec.md Section 11](spec/spec.md#11-compatibility-requirements)

**Acceptance Criteria:**
- [ ] Maya 2022+ installed and accessible
- [ ] Python 2.7 and/or 3.x available
- [ ] Maya Python environment tested (import maya.cmds works)
- [ ] PySide2/PySide6 available in Maya
- [ ] Git configured with user name and email
- [ ] Code editor/IDE set up (VS Code, PyCharm, etc.)

**Verification Steps:**
```bash
# Check Git configuration
git config --global user.name
git config --global user.email

# Test Maya Python (run in Maya Script Editor)
import maya.cmds as cmds
print(cmds.about(version=True))

import sys
print(sys.version)

try:
    from PySide2 import QtWidgets
    print("PySide2 available")
except ImportError:
    from PySide6 import QtWidgets
    print("PySide6 available")
```

---

## Quick Reference

### Project Overview

**Repository:** https://github.com/katha-begin/maya-multishot.git
**Total Tasks:** 92 (87 implementation + 5 setup)
**Estimated Timeline:** 12-16 weeks
**Critical Path Tasks:** 28 (includes Phase 0)

### Phase Breakdown

| Phase | Tasks | Duration | Status |
|-------|-------|----------|--------|
| Phase 0: Repository Setup | 5 | 1-2 days | ⬜ Not Started |
| Phase 1: Core Architecture | 18 | 3-4 weeks | ⬜ Not Started |
| Phase 2: Path Resolution | 15 | 2-3 weeks | ⬜ Not Started |
| Phase 3: Display Layers | 12 | 2 weeks | ⬜ Not Started |
| Phase 4: Tools & UI | 28 | 4-5 weeks | ⬜ Not Started |
| Phase 5: Testing & Docs | 14 | 2-3 weeks | ⬜ Not Started |

### Critical Path Tasks

These tasks are blocking and must be completed in order:

**Phase 0: Setup (Must Complete First)**
1. `[P0-REPO-01]` - Clone repository and create directory structure
2. `[P0-REPO-02]` - Create pull request template
3. `[P0-REPO-03]` - Initial commit and push
4. `[P0-REPO-04]` - Create develop branch
5. `[P0-REPO-05]` - Verify development environment

**Phase 1-5: Implementation**
6. `[P1-CONFIG-01]` - Project configuration loader
7. `[P1-CORE-01]` - CTX_Manager custom node
8. `[P1-CORE-02]` - CTX_Shot custom node
9. `[P1-CORE-03]` - CTX_Asset custom node
10. `[P2-TOKEN-01]` - Token expansion engine
11. `[P2-RESOLVE-01]` - Path resolver core
12. `[P3-LAYER-01]` - Display layer creation
13. `[P4-SHOT-01]` - Shot manager tool
14. `[P4-ASSET-01]` - Asset manager tool
15. `[P4-UI-01]` - Main window UI

### Key Deliverables

- ✅ Hierarchical data model (CTX nodes)
- ✅ Multi-shot support with independent versioning
- ✅ Display layer visibility management
- ✅ Token-based path resolution
- ✅ Cross-platform path mapping (Windows/Linux)
- ✅ Asset browser and importer
- ✅ Scene conversion tool
- ✅ Pre-render callback system

---

## Pre-Implementation Checklist

### Environment Setup

- [ ] **DEV-01:** Set up Python 2.7 and 3.x test environments
- [ ] **DEV-02:** Install Maya 2022, 2023, 2024 for compatibility testing
- [ ] **DEV-03:** Set up version control (Git) with proper .gitignore
- [ ] **DEV-04:** Create project directory structure matching spec Section 6.1
- [ ] **DEV-05:** Set up virtual environments for dependency isolation

### Dependencies

- [ ] **DEP-01:** Install PySide2/PySide6 for Qt compatibility
- [ ] **DEP-02:** Verify Maya API access (maya.cmds, maya.OpenMaya)
- [ ] **DEP-03:** Set up JSON schema validation library (optional)
- [ ] **DEP-04:** Install pytest for unit testing
- [ ] **DEP-05:** Set up code linting (pylint, flake8) for Python 2.7 compatibility

### Test Data

- [ ] **DATA-01:** Create sample project structure: `V:/SWA/all/scene/Ep04/sq0070/SH0170/`
- [ ] **DATA-02:** Generate test cache files with proper naming: `Ep04_sq0070_SH0170__CHAR_CatStompie_001.abc`
- [ ] **DATA-03:** Create sample config file: `config/ctx_config.json`
- [ ] **DATA-04:** Set up test assets in multiple categories (CHAR, PROP, ENV, VEH)
- [ ] **DATA-05:** Create test scenes with existing references for conversion testing

### Documentation

- [ ] **DOC-01:** Review spec.md thoroughly
- [ ] **DOC-02:** Review POC alignment report
- [ ] **DOC-03:** Review build system reference (igl_shot_build.py)
- [ ] **DOC-04:** Set up API documentation framework (Sphinx or similar)
- [ ] **DOC-05:** Create developer onboarding guide

---

## Phase 1: Core Architecture & Data Model

**Duration:** 3-4 weeks  
**Focus:** Build the foundational hierarchical node structure and configuration system

### Phase 1 Summary

| Module | Tasks | Priority | Complexity |
|--------|-------|----------|------------|
| config/ | 5 | HIGH | Medium |
| core/custom_nodes.py | 3 | HIGH | Complex |
| core/context.py | 2 | HIGH | Medium |
| core/nodes.py | 4 | HIGH | Medium |
| core/cache.py | 4 | MEDIUM | Medium |

---

### Module: config/

#### [P1-CONFIG-01] Implement ProjectConfig Class

**Priority:** HIGH (Critical Path)  
**Complexity:** Medium (3-5 days)  
**Dependencies:** None

**Description:**  
Create the `ProjectConfig` class to load, validate, and manage project configuration from JSON files. This is the foundation for all path resolution and template management.

**Spec Reference:** [spec.md Section 5.2, 7.2](spec.md#52-configuration-schema)

**POC Comparison:**  
🆕 **New Feature** - POC has no configuration system; patterns are hardcoded.

**Acceptance Criteria:**
- [ ] Load configuration from JSON file (both repository and workspace locations)
- [ ] Validate schema version and required fields
- [ ] Provide getter methods for templates, roots, patterns
- [ ] Handle missing/invalid config files gracefully with defaults
- [ ] Support environment-specific overrides (Windows vs Linux)

**Implementation Notes:**
- Use patterns from `igl_shot_build.py` for directory validation (`_validate_directory`)
- Support both repository location (recommended) and workspace location (legacy)
- Cache loaded config in memory for performance

---

#### [P1-CONFIG-02] Implement Platform Detection

**Priority:** HIGH (Critical Path)
**Complexity:** Simple (1-2 days)
**Dependencies:** None

**Description:**
Create platform detection module to identify OS and map paths between Windows and Linux. Essential for cross-platform compatibility.

**Spec Reference:** [spec.md Section 5.2.2, 7.2](spec.md#522-platform-mapping)

**POC Comparison:**
🆕 **New Feature** - POC has no platform mapping.

**Acceptance Criteria:**
- [ ] Detect current platform (Windows/Linux)
- [ ] Map Windows paths to Linux equivalents and vice versa
- [ ] Handle edge cases (network drives, UNC paths)
- [ ] Provide utility functions: `get_platform()`, `map_path(path, target_platform)`
- [ ] Unit tests for all path mapping scenarios

---

#### [P1-CONFIG-03] Implement Template Manager

**Priority:** HIGH
**Complexity:** Medium (3-5 days)
**Dependencies:** `[P1-CONFIG-01]`

**Description:**
Create template management system to load, validate, and provide access to path templates from configuration.

**Spec Reference:** [spec.md Section 5.2.3, 7.2](spec.md#523-path-templates)

**POC Comparison:**
⚠️ **POC Divergence** - POC uses hardcoded template strings; spec requires JSON-based templates.

**Acceptance Criteria:**
- [ ] Load templates from ProjectConfig
- [ ] Validate template syntax (check for required tokens)
- [ ] Provide template lookup by name: `get_template(name)`
- [ ] Support template inheritance/composition
- [ ] Handle missing templates with fallback defaults

**Implementation Notes:**
- Templates should support all tokens: `$root`, `$ep`, `$seq`, `$shot`, `$dept`, `$ver`, `$assetType`, `$assetName`, `$variant`

---

#### [P1-CONFIG-04] Implement Pattern Definitions

**Priority:** MEDIUM
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P1-CONFIG-01]`

**Description:**
Define and load regex patterns for parsing filenames, namespaces, and version strings from configuration.

**Spec Reference:** [spec.md Section 5.2.4, 7.2](spec.md#524-patterns)

**POC Comparison:**
🆕 **New Feature** - POC has no pattern configuration.

**Acceptance Criteria:**
- [ ] Load patterns from ProjectConfig
- [ ] Provide compiled regex patterns for: filename parsing, namespace extraction, version parsing
- [ ] Validate pattern syntax on load
- [ ] Support pattern testing/debugging utilities
- [ ] Document pattern format and examples

**Implementation Notes:**
- Use patterns from `igl_shot_build.py::_parse_cache_filename()` as reference
- Pattern for full filename: `^(Ep\d+)_(sq\d+)_(SH\d+)__([A-Z]+)_(.+)_(\d+)\.(abc|ma|mb)$`
- Pattern for namespace: `^([A-Z]+)_(.+)_(\d+)$`

---

#### [P1-CONFIG-05] Configuration Validation and Error Handling

**Priority:** MEDIUM
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P1-CONFIG-01]`, `[P1-CONFIG-02]`, `[P1-CONFIG-03]`, `[P1-CONFIG-04]`

**Description:**
Implement comprehensive validation and error handling for configuration loading and usage.

**Spec Reference:** [spec.md Section 5.2, 7.2](spec.md#52-configuration-schema)

**POC Comparison:**
🆕 **New Feature** - POC has no configuration validation.

**Acceptance Criteria:**
- [ ] Validate JSON schema on load
- [ ] Check for required fields and valid values
- [ ] Provide detailed error messages for invalid configs
- [ ] Support config migration from older versions
- [ ] Log warnings for deprecated fields

---

### Module: core/custom_nodes.py

#### [P1-CORE-01] Implement CTX_Manager Custom Node

**Priority:** HIGH (Critical Path)
**Complexity:** Complex (1-2 weeks)
**Dependencies:** `[P1-CONFIG-01]`

**Description:**
Create the root `CTX_Manager` custom network node that stores global context and manages all shots in the scene. This is the top of the hierarchical data model.

**Spec Reference:** [spec.md Section 3.2, 7.5](spec.md#32-hierarchical-data-model)

**POC Comparison:**
⚠️ **POC Divergence** - POC uses flat `fileInfo` storage; spec requires hierarchical custom nodes.

**Acceptance Criteria:**
- [ ] Define custom node type `CTX_Manager` with Maya API
- [ ] Store attributes: `config_path`, `project_root`, `active_shot_id`
- [ ] Implement node creation: `create_manager()`
- [ ] Implement node query: `get_manager()` (singleton pattern)
- [ ] Support multiple shots as child connections
- [ ] Add callbacks for attribute changes

**Implementation Notes:**
- Use `maya.OpenMaya.MFnDependencyNode` for custom node creation
- Store as network node (non-renderable, non-transformable)
- Ensure only one CTX_Manager exists per scene

---

#### [P1-CORE-02] Implement CTX_Shot Custom Node

**Priority:** HIGH (Critical Path)
**Complexity:** Complex (1-2 weeks)
**Dependencies:** `[P1-CORE-01]`

**Description:**
Create the `CTX_Shot` custom network node that stores shot-specific context (ep, seq, shot codes) and manages assets for that shot.

**Spec Reference:** [spec.md Section 3.2, 7.5](spec.md#32-hierarchical-data-model)

**POC Comparison:**
⚠️ **POC Divergence** - POC stores context in `fileInfo`; spec requires per-shot nodes.

**Acceptance Criteria:**
- [ ] Define custom node type `CTX_Shot` with Maya API
- [ ] Store attributes: `ep_code`, `seq_code`, `shot_code`, `display_layer_name`, `is_active`
- [ ] Implement node creation: `create_shot(ep, seq, shot)`
- [ ] Connect to parent CTX_Manager node
- [ ] Support multiple assets as child connections
- [ ] Implement shot activation/deactivation logic

**Implementation Notes:**
- Each shot node represents one shot context in the scene
- Display layer name follows format: `CTX_{ep}_{seq}_{shot}`
- Active shot determines which context is used for path resolution

---

#### [P1-CORE-03] Implement CTX_Asset Custom Node

**Priority:** HIGH (Critical Path)
**Complexity:** Complex (1-2 weeks)
**Dependencies:** `[P1-CORE-02]`

**Description:**
Create the `CTX_Asset` custom network node that stores asset-specific data (type, name, variant, version, paths) for each asset in a shot.

**Spec Reference:** [spec.md Section 3.2, 7.5](spec.md#32-hierarchical-data-model)

**POC Comparison:**
⚠️ **POC Divergence** - POC uses proxy nodes with custom attributes; spec requires dedicated asset nodes.

**Acceptance Criteria:**
- [ ] Define custom node type `CTX_Asset` with Maya API
- [ ] Store attributes: `asset_type`, `asset_name`, `variant`, `version`, `template_path`, `resolved_path`, `node_type`
- [ ] **NEW:** Add `targetNode` (message) attribute for bidirectional linking
- [ ] **NEW:** Add `targetNodeStr` (string) attribute as fallback for locked references
- [ ] Implement node creation: `create_asset(shot_node, asset_type, name, variant)`
- [ ] Connect to parent CTX_Shot node using message attributes
- [ ] **NEW:** Implement `link_to_maya_node()` method with message attribute connection
- [ ] **NEW:** Implement fallback to string attribute for locked reference nodes
- [ ] **NEW:** Implement `get_linked_maya_node()` method to query connections
- [ ] Support version updates and path re-resolution

**Implementation Notes:**
- Asset node acts as metadata container for actual Maya nodes
- Store both template path and resolved path for debugging
- Support node types: `aiStandIn`, `RedshiftProxyMesh`, `reference`
- **NEW:** Use message attributes for bidirectional linking (primary method)
- **NEW:** Fall back to string attributes for locked references
- **NEW:** Query message connections first, then string fallback
- **NEW:** Message connections auto-cleanup when nodes deleted

#### [P1-CORE-04] Implement Message Attribute Linking for CTX_Asset

**Priority:** HIGH (Critical Path)
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P1-CORE-03]`

**Description:**
Implement bidirectional message attribute linking between CTX_Asset nodes and Maya asset nodes (aiStandIn, RedshiftProxyMesh, reference). Includes fallback strategy for locked reference nodes.

**Spec Reference:** [spec.md Section 3.4.1, 3.7](spec.md#341-message-attribute-linking-strategy)

**Acceptance Criteria:**
- [ ] Implement `link_to_maya_node(ctx_asset, maya_node)` helper function
- [ ] Add `targetNode` (message) attribute to CTX_Asset nodes
- [ ] Add `ctx_metadata` (message) attribute to Maya nodes (when possible)
- [ ] Implement try/except for locked reference nodes
- [ ] Add `targetNodeStr` (string) fallback for locked references
- [ ] Implement `get_linked_maya_node(ctx_asset)` query function
- [ ] Implement `get_linked_ctx_assets(maya_node)` reverse query function
- [ ] Update `convert_to_ctx()` to use message attributes instead of string
- [ ] Add validation to check if connection exists before creating
- [ ] Add unit tests for message attribute linking

**Implementation Notes:**
- **Primary method:** Message attributes (bidirectional, auto-cleanup)
- **Fallback method:** String attributes (for locked references only)
- **Query order:** Always check message connection first, then string fallback
- **Special handling:** Reference nodes may be locked - use `referenceQuery()` to get reference node
- **Multi-shot support:** One Maya node can have multiple CTX_Asset connections
- **Cleanup:** Message connections auto-break on node deletion; string attributes need manual validation

**Code Structure:**
```python
# In core/ctx_converter.py or new core/ctx_linker.py

def link_to_maya_node(ctx_asset_node, maya_node):
    """Link CTX_Asset to Maya node using message attributes."""
    # 1. Add targetNode message attribute to CTX_Asset
    # 2. Try to add ctx_metadata message attribute to Maya node
    # 3. Create connection
    # 4. If locked, fall back to targetNodeStr string attribute

def get_linked_maya_node(ctx_asset_node):
    """Get Maya node linked to CTX_Asset."""
    # 1. Try message connection first
    # 2. Fall back to string attribute
    # 3. Validate node exists

def get_linked_ctx_assets(maya_node):
    """Get all CTX_Assets linked to Maya node."""
    # Query reverse connection via ctx_metadata attribute
```

---

### Module: core/context.py

#### [P1-CONTEXT-01] Implement Context Manager API

**Priority:** HIGH (Critical Path)
**Complexity:** Medium (3-5 days)
**Dependencies:** `[P1-CORE-01]`, `[P1-CORE-02]`, `[P1-CORE-03]`

**Description:**
Create high-level API for managing context: creating shots, switching active shot, querying current context.

**Spec Reference:** [spec.md Section 7.3](spec.md#73-context-management)

**POC Comparison:**
✅ **Can Adapt POC Code** - POC's `ContextManager` class provides good foundation, but needs multi-shot support.

**Acceptance Criteria:**
- [ ] Implement `get_or_create_manager()` - Get/create CTX_Manager node
- [ ] Implement `create_shot(ep, seq, shot)` - Create new shot in scene
- [ ] Implement `set_active_shot(shot_node)` - Switch active shot
- [ ] Implement `get_active_shot()` - Get current active shot node
- [ ] Implement `get_all_shots()` - List all shots in scene
- [ ] Implement `get_shot_context(shot_node)` - Get ep/seq/shot dict

**Implementation Notes:**
- Reuse POC's callback notification pattern for context changes
- Add multi-shot support (POC only supports single shot)
- Ensure thread-safe access to context data

---

#### [P1-CONTEXT-02] Implement Context Change Callbacks

**Priority:** HIGH
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P1-CONTEXT-01]`

**Description:**
Implement callback system to notify listeners when context changes (shot switch, version update).

**Spec Reference:** [spec.md Section 7.3](spec.md#73-context-management)

**POC Comparison:**
✅ **Can Reuse POC Code** - POC's `_notify_change()` and callback registration system works well.

**Acceptance Criteria:**
- [ ] Implement `register_callback(callback_fn)` - Register listener
- [ ] Implement `unregister_callback(callback_fn)` - Remove listener
- [ ] Implement `_notify_change(event_type, data)` - Notify all listeners
- [ ] Support event types: `shot_switched`, `version_updated`, `asset_added`, `asset_removed`
- [ ] Prevent callback loops with silent mode flag

**Implementation Notes:**
- Reuse POC's callback pattern from `maya_context_tools_sample.py`
- Add event type parameter for more granular control
- Ensure callbacks are called in registration order

---

### Module: core/nodes.py

#### [P1-NODES-01] Implement Node Manager for Proxy/Reference Operations

**Priority:** HIGH
**Complexity:** Medium (3-5 days)
**Dependencies:** `[P1-CORE-03]`, `[P1-CONTEXT-01]`

**Description:**
Create node manager to handle operations on Arnold StandIns, Redshift Proxies, and Maya References.

**Spec Reference:** [spec.md Section 7.6](spec.md#76-node-operations)

**POC Comparison:**
✅ **Can Adapt POC Code** - POC's `NodeManager` class provides good foundation.

**Acceptance Criteria:**
- [ ] Implement `get_node_type(node)` - Detect node type (aiStandIn, RedshiftProxyMesh, reference)
- [ ] Implement `get_path(node)` - Get current file path from node
- [ ] Implement `set_path(node, path)` - Update file path on node
- [ ] Implement `is_valid_node(node)` - Check if node exists and is supported type
- [ ] Support all three node types with unified API

**Implementation Notes:**
- Reuse POC's node type detection logic
- Handle locked reference nodes using `fileInfo` pattern from POC
- Add error handling for missing/invalid nodes

---

#### [P1-NODES-02] Implement Asset Registration

**Priority:** HIGH
**Complexity:** Medium (3-5 days)
**Dependencies:** `[P1-NODES-01]`, `[P1-CORE-03]`

**Description:**
Implement system to register existing Maya nodes as CTX assets, linking them to CTX_Asset nodes.

**Spec Reference:** [spec.md Section 7.6](spec.md#76-node-operations)

**POC Comparison:**
⚠️ **POC Divergence** - POC stores data in `fileInfo`; spec requires CTX_Asset nodes.

**Acceptance Criteria:**
- [ ] Implement `register_asset(shot_node, maya_node, asset_type, name, variant)` - Create CTX_Asset and link to Maya node
- [ ] Parse namespace from Maya node to extract asset info
- [ ] Store template path and resolved path in CTX_Asset
- [ ] Handle duplicate registrations gracefully
- [ ] Support batch registration for multiple nodes

**Implementation Notes:**
- Use namespace format: `$assetType_$assetName_$variant`
- Extract asset info from node namespace if available
- Validate Maya node exists before registration

---

#### [P1-NODES-03] Implement Asset Query Functions

**Priority:** MEDIUM
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P1-NODES-02]`

**Description:**
Provide query functions to find assets by various criteria (shot, type, name, Maya node).

**Spec Reference:** [spec.md Section 7.6](spec.md#76-node-operations)

**POC Comparison:**
🆕 **New Feature** - POC has no asset query system.

**Acceptance Criteria:**
- [ ] Implement `get_assets_for_shot(shot_node)` - Get all assets in shot
- [ ] Implement `get_asset_by_maya_node(maya_node)` - Find CTX_Asset for Maya node
- [ ] Implement `get_assets_by_type(shot_node, asset_type)` - Filter by type
- [ ] Implement `find_asset(shot_node, name, variant)` - Find specific asset
- [ ] Return empty list if no matches found

---

#### [P1-NODES-04] Implement Path Update Operations

**Priority:** HIGH
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P1-NODES-01]`, `[P1-CONTEXT-02]`

**Description:**
Implement operations to update paths on Maya nodes when context or version changes.

**Spec Reference:** [spec.md Section 7.6](spec.md#76-node-operations)

**POC Comparison:**
✅ **Can Adapt POC Code** - POC's auto-update logic works well.

**Acceptance Criteria:**
- [ ] Implement `update_asset_path(asset_node)` - Re-resolve and update path
- [ ] Implement `update_shot_paths(shot_node)` - Update all assets in shot
- [ ] Implement `update_all_paths()` - Update all assets in scene
- [ ] Handle errors gracefully (missing files, locked nodes)
- [ ] Log all path updates for debugging

**Implementation Notes:**
- Trigger updates on context change callbacks
- Use silent mode to prevent callback loops
- Validate resolved paths exist before updating

---

### Module: core/cache.py

#### [P1-CACHE-01] Implement Version Cache Structure

**Priority:** MEDIUM
**Complexity:** Medium (3-5 days)
**Dependencies:** `[P1-CONFIG-01]`

**Description:**
Create version cache system to store discovered asset versions and paths for quick lookup.

**Spec Reference:** [spec.md Section 5.3, 7.7](spec.md#53-cache-structure)

**POC Comparison:**
🆕 **New Feature** - POC has no version caching.

**Acceptance Criteria:**
- [ ] Implement cache structure: `{publish_path: {asset_name: [versions]}}`
- [ ] Store full publish paths as keys (e.g., `V:/SWA/all/scene/Ep04/sq0070/SH0170/anim/publish`)
- [ ] Store full asset names (e.g., `CHAR_CatStompie_001`)
- [ ] Implement `build_cache(shot_context)` - Scan filesystem and build cache
- [ ] Implement `get_versions(publish_path, asset_name)` - Query cache
- [ ] Support cache persistence to JSON file

**Implementation Notes:**
- Use patterns from `igl_shot_build.py::_list_versions()` for version discovery
- Cache should be per-shot to avoid conflicts
- Sort versions with latest first

---

#### [P1-CACHE-02] Implement Asset Discovery

**Priority:** MEDIUM
**Complexity:** Medium (3-5 days)
**Dependencies:** `[P1-CACHE-01]`, `[P1-CONFIG-04]`

**Description:**
Implement filesystem scanning to discover available assets and versions in publish directories.

**Spec Reference:** [spec.md Section 7.7](spec.md#77-cache-management)

**POC Comparison:**
🆕 **New Feature** - POC has no asset discovery.

**Acceptance Criteria:**
- [ ] Implement `scan_publish_directory(path)` - Scan for .abc/.ma/.mb files
- [ ] Parse filenames using regex patterns from config
- [ ] Extract asset metadata: type, name, variant, version
- [ ] Handle invalid/unparseable filenames gracefully
- [ ] Return structured data: `[{filename, asset_type, name, variant, full_path}]`

**Implementation Notes:**
- Use patterns from `igl_shot_build.py::_parse_cache_filename()` as reference
- Support multiple file extensions: `.abc`, `.ma`, `.mb`
- Log warnings for unparseable files

---

#### [P1-CACHE-03] Implement Cache Refresh and Invalidation

**Priority:** MEDIUM
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P1-CACHE-01]`, `[P1-CACHE-02]`

**Description:**
Implement cache refresh logic to update cache when filesystem changes or on user request.

**Spec Reference:** [spec.md Section 7.7](spec.md#77-cache-management)

**POC Comparison:**
🆕 **New Feature** - POC has no cache management.

**Acceptance Criteria:**
- [ ] Implement `refresh_cache(shot_node)` - Rebuild cache for shot
- [ ] Implement `invalidate_cache(shot_node)` - Clear cache for shot
- [ ] Implement `is_cache_valid(shot_node)` - Check if cache is up-to-date
- [ ] Support manual and automatic refresh modes
- [ ] Log cache refresh operations

---

#### [P1-CACHE-04] Implement Latest Version Resolution

**Priority:** MEDIUM
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P1-CACHE-01]`

**Description:**
Implement logic to resolve "latest" version from cache for a given asset.

**Spec Reference:** [spec.md Section 7.7](spec.md#77-cache-management)

**POC Comparison:**
🆕 **New Feature** - POC has no version resolution.

**Acceptance Criteria:**
- [ ] Implement `get_latest_version(publish_path, asset_name)` - Get highest version number
- [ ] Support version format: `v001`, `v002`, etc.
- [ ] Handle missing versions gracefully (return None)
- [ ] Support version comparison (v010 > v002)
- [ ] Unit tests for version sorting edge cases

**Implementation Notes:**
- Use patterns from `igl_shot_build.py::_list_versions()` for version sorting
- Sort versions numerically, not alphabetically
- Handle non-standard version formats with warnings

---

## Phase 2: Path Resolution & Token System

**Duration:** 2-3 weeks
**Focus:** Build token expansion, path resolution, and path builder engine

### Phase 2 Summary

| Module | Tasks | Priority | Complexity |
|--------|-------|----------|------------|
| core/tokens.py | 3 | HIGH | Medium |
| core/resolver.py | 5 | HIGH | Complex |
| core/path_builder.py | 4 | HIGH | Complex |
| config/templates.py | 3 | MEDIUM | Medium |

---

### Module: core/tokens.py

#### [P2-TOKEN-01] Implement Token Expansion Engine

**Priority:** HIGH (Critical Path)
**Complexity:** Medium (3-5 days)
**Dependencies:** `[P1-CONTEXT-01]`

**Description:**
Create token expansion engine to replace tokens in template paths with actual values from context.

**Spec Reference:** [spec.md Section 2.3, 7.4](spec.md#23-token-system)

**POC Comparison:**
✅ **Can Reuse POC Code** - POC's `expand_tokens()` method works well.

**Acceptance Criteria:**
- [ ] Implement `expand_tokens(template, context, version_override=None)` - Replace all tokens
- [ ] Support all tokens: `$root`, `$ep`, `$seq`, `$shot`, `$dept`, `$ver`, `$assetType`, `$assetName`, `$variant`
- [ ] Handle missing context values gracefully (leave token unexpanded or use default)
- [ ] Support version override for "latest" resolution
- [ ] Unit tests for all token combinations

**Implementation Notes:**
- Reuse POC's token expansion logic from `maya_context_tools_sample.py::expand_tokens()`
- Add support for nested tokens if needed
- Validate expanded paths for invalid characters

---

#### [P2-TOKEN-02] Implement Token Validation

**Priority:** MEDIUM
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P2-TOKEN-01]`

**Description:**
Validate template strings to ensure they contain valid tokens and syntax.

**Spec Reference:** [spec.md Section 2.3, 7.4](spec.md#23-token-system)

**POC Comparison:**
🆕 **New Feature** - POC has no token validation.

**Acceptance Criteria:**
- [ ] Implement `validate_template(template)` - Check for valid token syntax
- [ ] Detect invalid tokens (e.g., `$invalid_token`)
- [ ] Check for required tokens in specific template types
- [ ] Return validation errors with helpful messages
- [ ] Unit tests for valid and invalid templates

---

#### [P2-TOKEN-03] Implement Token Extraction

**Priority:** LOW
**Complexity:** Simple (1 day)
**Dependencies:** `[P2-TOKEN-01]`

**Description:**
Extract tokens from template strings for analysis and debugging.

**Spec Reference:** [spec.md Section 7.4](spec.md#74-token-system)

**POC Comparison:**
🆕 **New Feature** - POC has no token extraction.

**Acceptance Criteria:**
- [ ] Implement `extract_tokens(template)` - Return list of tokens in template
- [ ] Return tokens in order of appearance
- [ ] Handle duplicate tokens
- [ ] Support debugging utilities to show token values

---

### Module: core/resolver.py

#### [P2-RESOLVE-01] Implement Path Resolver Core

**Priority:** HIGH (Critical Path)
**Complexity:** Complex (1 week)
**Dependencies:** `[P2-TOKEN-01]`, `[P1-CONFIG-03]`, `[P1-CONTEXT-01]`

**Description:**
Create core path resolver that combines templates, tokens, and context to resolve full file paths.

**Spec Reference:** [spec.md Section 7.4](spec.md#74-path-resolution)

**POC Comparison:**
✅ **Can Adapt POC Code** - POC's path resolution logic provides foundation.

**Acceptance Criteria:**
- [ ] Implement `resolve_path(template_name, context, asset_data, version='latest')` - Full resolution
- [ ] Load template from config by name
- [ ] Expand tokens using context and asset data
- [ ] Handle "latest" version resolution via cache
- [ ] Map paths to current platform (Windows/Linux)
- [ ] Return resolved absolute path

**Implementation Notes:**
- Combine template manager, token expansion, and platform mapping
- Support version override for specific version or "latest"
- Validate resolved paths exist (optional, with flag)

---

#### [P2-RESOLVE-02] Implement Batch Path Resolution

**Priority:** MEDIUM
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P2-RESOLVE-01]`

**Description:**
Implement batch resolution for multiple assets to improve performance.

**Spec Reference:** [spec.md Section 7.4](spec.md#74-path-resolution)

**POC Comparison:**
🆕 **New Feature** - POC resolves paths one at a time.

**Acceptance Criteria:**
- [ ] Implement `resolve_paths_batch(assets, context)` - Resolve multiple assets
- [ ] Cache template lookups to avoid repeated loads
- [ ] Return dict mapping asset to resolved path
- [ ] Handle errors per-asset without failing entire batch
- [ ] Log batch resolution statistics (time, success/failure counts)

---

#### [P2-RESOLVE-03] Implement Path Validation

**Priority:** MEDIUM
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P2-RESOLVE-01]`

**Description:**
Validate resolved paths to ensure they exist and are accessible.

**Spec Reference:** [spec.md Section 7.4](spec.md#74-path-resolution)

**POC Comparison:**
🆕 **New Feature** - POC has no path validation.

**Acceptance Criteria:**
- [ ] Implement `validate_path(path)` - Check if file exists and is readable
- [ ] Implement `validate_paths_batch(paths)` - Validate multiple paths
- [ ] Return validation results with error messages
- [ ] Support optional validation (flag to skip for performance)
- [ ] Log validation failures with helpful diagnostics

**Implementation Notes:**
- Use patterns from `igl_shot_build.py::_validate_directory()` for validation
- Handle network path delays gracefully
- Support async validation for large batches

---

#### [P2-RESOLVE-04] Implement Path Caching

**Priority:** LOW
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P2-RESOLVE-01]`

**Description:**
Cache resolved paths to improve performance for repeated resolutions.

**Spec Reference:** [spec.md Section 7.4](spec.md#74-path-resolution)

**POC Comparison:**
🆕 **New Feature** - POC has no path caching.

**Acceptance Criteria:**
- [ ] Implement in-memory cache for resolved paths
- [ ] Cache key: (template_name, context, asset_data, version)
- [ ] Implement cache invalidation on context change
- [ ] Implement cache size limits (LRU eviction)
- [ ] Provide cache statistics for debugging

---

#### [P2-RESOLVE-05] Implement Resolver Error Handling

**Priority:** MEDIUM
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P2-RESOLVE-01]`

**Description:**
Comprehensive error handling for path resolution failures.

**Spec Reference:** [spec.md Section 7.4](spec.md#74-path-resolution)

**POC Comparison:**
🆕 **New Feature** - POC has minimal error handling.

**Acceptance Criteria:**
- [ ] Define custom exceptions: `TemplateNotFoundError`, `TokenExpansionError`, `PathValidationError`
- [ ] Provide detailed error messages with context
- [ ] Log all resolution errors
- [ ] Support fallback resolution strategies
- [ ] Unit tests for all error scenarios

---

### Module: core/path_builder.py

#### [P2-BUILDER-01] Implement Path Builder Engine Core

**Priority:** HIGH (Critical Path)
**Complexity:** Complex (1 week)
**Dependencies:** `[P1-CONFIG-04]`, `[P1-CONTEXT-01]`

**Description:**
Create path builder engine to resolve paths from two input formats: full filename or namespace only.

**Spec Reference:** [spec.md Section 5.4, 7.4](spec.md#54-path-builder-engine)

**POC Comparison:**
🆕 **New Feature** - POC has no path builder engine.

**Acceptance Criteria:**
- [ ] Implement `build_path(input, context=None, version='latest')` - Main entry point
- [ ] Detect input format: full filename vs namespace only
- [ ] Parse full filename: `Ep04_sq0070_SH0170__CHAR_CatStompie_002.abc`
- [ ] Parse namespace: `CHAR_CatStompie_002` (requires context)
- [ ] Resolve to full path using templates and cache
- [ ] Support version override

**Implementation Notes:**
- Use patterns from `igl_shot_build.py::_parse_cache_filename()` for filename parsing
- Namespace format: `$assetType_$assetName_$variant`
- Full filename format: `$ep_$seq_$shot__$assetType_$assetName_$variant.$ext`

---

#### [P2-BUILDER-02] Implement Filename Parser

**Priority:** HIGH
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P2-BUILDER-01]`, `[P1-CONFIG-04]`

**Description:**
Parse full filenames to extract shot context and asset metadata.

**Spec Reference:** [spec.md Section 5.4, 7.4](spec.md#54-path-builder-engine)

**POC Comparison:**
🆕 **New Feature** - POC has no filename parsing.

**Acceptance Criteria:**
- [ ] Implement `parse_filename(filename)` - Extract all components
- [ ] Return dict: `{ep, seq, shot, asset_type, asset_name, variant, extension}`
- [ ] Handle invalid filenames gracefully (return None)
- [ ] Support multiple extensions: `.abc`, `.ma`, `.mb`
- [ ] Unit tests for valid and invalid filenames

**Implementation Notes:**
- Use regex pattern from config: `^(Ep\d+)_(sq\d+)_(SH\d+)__([A-Z]+)_(.+)_(\d+)\.(abc|ma|mb)$`
- Reuse logic from `igl_shot_build.py::_parse_cache_filename()`

---

#### [P2-BUILDER-03] Implement Namespace Parser

**Priority:** HIGH
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P2-BUILDER-01]`, `[P1-CONFIG-04]`

**Description:**
Parse namespace-only input to extract asset metadata.

**Spec Reference:** [spec.md Section 5.4, 7.4](spec.md#54-path-builder-engine)

**POC Comparison:**
🆕 **New Feature** - POC has no namespace parsing.

**Acceptance Criteria:**
- [ ] Implement `parse_namespace(namespace)` - Extract asset components
- [ ] Return dict: `{asset_type, asset_name, variant}`
- [ ] Handle invalid namespaces gracefully (return None)
- [ ] Validate namespace format: `$assetType_$assetName_$variant`
- [ ] Unit tests for valid and invalid namespaces

**Implementation Notes:**
- Use regex pattern from config: `^([A-Z]+)_(.+)_(\d+)$`
- Namespace requires context (ep/seq/shot) to build full path

---

#### [P2-BUILDER-04] Implement Path Builder Integration

**Priority:** MEDIUM
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P2-BUILDER-01]`, `[P2-BUILDER-02]`, `[P2-BUILDER-03]`, `[P2-RESOLVE-01]`

**Description:**
Integrate path builder with resolver and cache for complete path resolution.

**Spec Reference:** [spec.md Section 5.4, 7.4](spec.md#54-path-builder-engine)

**POC Comparison:**
🆕 **New Feature** - POC has no path builder integration.

**Acceptance Criteria:**
- [ ] Connect path builder to path resolver
- [ ] Use cache for version lookup when version='latest'
- [ ] Support both input formats seamlessly
- [ ] Return full resolved path or None if not found
- [ ] Log path builder operations for debugging

---

### Module: config/templates.py

#### [P2-TEMPLATE-01] Implement Template Inheritance

**Priority:** LOW
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P1-CONFIG-03]`

**Description:**
Support template inheritance to reduce duplication in configuration.

**Spec Reference:** [spec.md Section 5.2.3](spec.md#523-path-templates)

**POC Comparison:**
🆕 **New Feature** - POC has no template system.

**Acceptance Criteria:**
- [ ] Support `extends` field in template definitions
- [ ] Merge parent and child templates
- [ ] Handle circular inheritance gracefully
- [ ] Validate inheritance chains
- [ ] Unit tests for inheritance scenarios

---

#### [P2-TEMPLATE-02] Implement Template Composition

**Priority:** LOW
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P1-CONFIG-03]`

**Description:**
Support template composition to build complex paths from reusable components.

**Spec Reference:** [spec.md Section 5.2.3](spec.md#523-path-templates)

**POC Comparison:**
🆕 **New Feature** - POC has no template system.

**Acceptance Criteria:**
- [ ] Support `includes` field to reference other templates
- [ ] Compose templates at load time
- [ ] Handle missing includes gracefully
- [ ] Validate composed templates
- [ ] Unit tests for composition scenarios

---

#### [P2-TEMPLATE-03] Implement Template Debugging Tools

**Priority:** LOW
**Complexity:** Simple (1 day)
**Dependencies:** `[P1-CONFIG-03]`, `[P2-TOKEN-01]`

**Description:**
Provide debugging tools to visualize template expansion and token values.

**Spec Reference:** [spec.md Section 7.4](spec.md#74-path-resolution)

**POC Comparison:**
🆕 **New Feature** - POC has no debugging tools.

**Acceptance Criteria:**
- [ ] Implement `debug_template(template_name, context)` - Show expansion steps
- [ ] Display token values and expanded result
- [ ] Highlight missing/invalid tokens
- [ ] Support interactive debugging in UI
- [ ] Log debugging output

---

## Phase 3: Display Layer Management

**Duration:** 2 weeks
**Focus:** Build display layer system for shot-specific visibility control

### Phase 3 Summary

| Module | Tasks | Priority | Complexity |
|--------|-------|----------|------------|
| core/display_layers.py | 8 | HIGH | Medium |
| core/shot_switching.py | 4 | HIGH | Medium |

---

### Module: core/display_layers.py

#### [P3-LAYER-01] Implement Display Layer Creation

**Priority:** HIGH (Critical Path)
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P1-CORE-02]`

**Description:**
Create display layers for shots using hierarchical naming convention.

**Spec Reference:** [spec.md Section 4.1, 7.8](spec.md#41-display-layer-management)

**POC Comparison:**
⚠️ **POC Divergence** - POC has no display layer management.

**Acceptance Criteria:**
- [ ] Implement `create_display_layer(ep_code, seq_code, shot_code)` - Create layer
- [ ] Use naming format: `CTX_{ep}_{seq}_{shot}` (e.g., `CTX_Ep04_sq0070_SH0170`)
- [ ] Store layer name in CTX_Shot node
- [ ] Handle existing layers gracefully (reuse if exists)
- [ ] Set layer visibility to visible by default

**Implementation Notes:**
- Use `cmds.createDisplayLayer()` for layer creation
- Updated naming from POC's `CTX_{shot}` to `CTX_{ep}_{seq}_{shot}`
- Ensure layer names are unique per shot

---

#### [P3-LAYER-02] Implement Asset-to-Layer Assignment

**Priority:** HIGH
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P3-LAYER-01]`, `[P1-NODES-02]`

**Description:**
Assign Maya nodes to their shot's display layer automatically.

**Spec Reference:** [spec.md Section 4.1, 7.8](spec.md#41-display-layer-management)

**POC Comparison:**
🆕 **New Feature** - POC has no display layer management.

**Acceptance Criteria:**
- [ ] Implement `assign_to_layer(maya_node, layer_name)` - Add node to layer
- [ ] Automatically assign assets when registered to shot
- [ ] Handle nodes already in other layers (move to new layer)
- [ ] Support batch assignment for multiple nodes
- [ ] Log layer assignments

---

#### [P3-LAYER-03] Implement Layer Visibility Control

**Priority:** HIGH
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P3-LAYER-01]`

**Description:**
Control visibility of display layers to show/hide shots.

**Spec Reference:** [spec.md Section 4.1, 7.8](spec.md#41-display-layer-management)

**POC Comparison:**
🆕 **New Feature** - POC has no display layer management.

**Acceptance Criteria:**
- [ ] Implement `set_layer_visibility(layer_name, visible)` - Show/hide layer
- [ ] Implement `show_layer(layer_name)` - Convenience method
- [ ] Implement `hide_layer(layer_name)` - Convenience method
- [ ] Support visibility states: visible, hidden, reference
- [ ] Update layer visibility on shot switch

---

#### [P3-LAYER-04] Implement Layer Query Functions

**Priority:** MEDIUM
**Complexity:** Simple (1 day)
**Dependencies:** `[P3-LAYER-01]`

**Description:**
Query display layers and their contents.

**Spec Reference:** [spec.md Section 7.8](spec.md#78-display-layer-management)

**POC Comparison:**
🆕 **New Feature** - POC has no display layer management.

**Acceptance Criteria:**
- [ ] Implement `get_layer_for_shot(shot_node)` - Get layer name
- [ ] Implement `get_layer_members(layer_name)` - Get nodes in layer
- [ ] Implement `get_all_ctx_layers()` - List all CTX layers
- [ ] Implement `is_in_layer(maya_node, layer_name)` - Check membership
- [ ] Return empty list if layer doesn't exist

---

#### [P3-LAYER-05] Implement Layer Cleanup

**Priority:** MEDIUM
**Complexity:** Simple (1 day)
**Dependencies:** `[P3-LAYER-01]`

**Description:**
Clean up empty or orphaned display layers.

**Spec Reference:** [spec.md Section 7.8](spec.md#78-display-layer-management)

**POC Comparison:**
🆕 **New Feature** - POC has no display layer management.

**Acceptance Criteria:**
- [ ] Implement `cleanup_empty_layers()` - Remove layers with no members
- [ ] Implement `cleanup_orphaned_layers()` - Remove layers not linked to shots
- [ ] Prompt user before deletion
- [ ] Log cleanup operations
- [ ] Support dry-run mode

---

#### [P3-LAYER-06] Implement Layer Isolation Mode

**Priority:** LOW
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P3-LAYER-03]`

**Description:**
Isolate a single shot by hiding all other shot layers.

**Spec Reference:** [spec.md Section 7.8](spec.md#78-display-layer-management)

**POC Comparison:**
🆕 **New Feature** - POC has no display layer management.

**Acceptance Criteria:**
- [ ] Implement `isolate_shot(shot_node)` - Show only this shot's layer
- [ ] Hide all other CTX layers
- [ ] Store previous visibility state for restoration
- [ ] Implement `unisolate_all()` - Restore previous state
- [ ] Support toggle isolation mode

---

#### [P3-LAYER-07] Implement Layer Color Coding

**Priority:** LOW
**Complexity:** Simple (1 day)
**Dependencies:** `[P3-LAYER-01]`

**Description:**
Assign colors to display layers for visual distinction.

**Spec Reference:** [spec.md Section 7.8](spec.md#78-display-layer-management)

**POC Comparison:**
🆕 **New Feature** - POC has no display layer management.

**Acceptance Criteria:**
- [ ] Implement `set_layer_color(layer_name, color)` - Set layer color
- [ ] Auto-assign colors to new layers (cycle through palette)
- [ ] Support custom color per shot
- [ ] Provide color palette configuration
- [ ] Update layer color in UI

---

#### [P3-LAYER-08] Implement Layer Error Handling

**Priority:** MEDIUM
**Complexity:** Simple (1 day)
**Dependencies:** `[P3-LAYER-01]`, `[P3-LAYER-02]`

**Description:**
Handle errors in display layer operations gracefully.

**Spec Reference:** [spec.md Section 7.8](spec.md#78-display-layer-management)

**POC Comparison:**
🆕 **New Feature** - POC has no display layer management.

**Acceptance Criteria:**
- [ ] Handle missing layers gracefully
- [ ] Handle invalid node assignments
- [ ] Handle locked layers
- [ ] Provide detailed error messages
- [ ] Log all layer errors

---

### Module: core/shot_switching.py

#### [P3-SWITCH-01] Implement Shot Switching Logic

**Priority:** HIGH (Critical Path)
**Complexity:** Medium (3-5 days)
**Dependencies:** `[P1-CONTEXT-01]`, `[P3-LAYER-03]`

**Description:**
Implement shot switching to change active shot and update visibility.

**Spec Reference:** [spec.md Section 4.2, 7.9](spec.md#42-shot-switching)

**POC Comparison:**
⚠️ **POC Divergence** - POC is single-shot only; spec requires multi-shot switching.

**Acceptance Criteria:**
- [ ] Implement `switch_to_shot(shot_node)` - Change active shot
- [ ] Update CTX_Manager's `active_shot_id` attribute
- [ ] Show active shot's display layer
- [ ] Hide inactive shots' display layers (optional)
- [ ] Trigger context change callbacks
- [ ] Update UI to reflect active shot

**Implementation Notes:**
- This is a critical feature not present in POC
- Switching should be fast (< 1 second for typical scenes)
- Support undo/redo for shot switching

---

#### [P3-SWITCH-02] Implement Shot Switching UI Feedback

**Priority:** MEDIUM
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P3-SWITCH-01]`

**Description:**
Provide visual feedback during shot switching operations.

**Spec Reference:** [spec.md Section 7.9](spec.md#79-shot-switching)

**POC Comparison:**
🆕 **New Feature** - POC has no shot switching.

**Acceptance Criteria:**
- [ ] Show progress indicator during switch
- [ ] Display active shot name in UI
- [ ] Highlight active shot in shot list
- [ ] Show notification on successful switch
- [ ] Handle switch failures gracefully

---

#### [P3-SWITCH-03] Implement Shot Switching History

**Priority:** LOW
**Complexity:** Simple (1 day)
**Dependencies:** `[P3-SWITCH-01]`

**Description:**
Track shot switching history for quick navigation.

**Spec Reference:** [spec.md Section 7.9](spec.md#79-shot-switching)

**POC Comparison:**
🆕 **New Feature** - POC has no shot switching.

**Acceptance Criteria:**
- [ ] Store last N shot switches in memory
- [ ] Implement `switch_to_previous_shot()` - Go back
- [ ] Implement `switch_to_next_shot()` - Go forward
- [ ] Provide history list in UI
- [ ] Clear history on scene close

---

#### [P3-SWITCH-04] Implement Shot Switching Performance Optimization

**Priority:** MEDIUM
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P3-SWITCH-01]`

**Description:**
Optimize shot switching for scenes with many assets.

**Spec Reference:** [spec.md Section 7.9](spec.md#79-shot-switching)

**POC Comparison:**
🆕 **New Feature** - POC has no shot switching.

**Acceptance Criteria:**
- [ ] Batch layer visibility updates
- [ ] Defer UI updates until switch complete
- [ ] Cache layer membership for fast lookup
- [ ] Profile switching performance
- [ ] Target < 1 second for typical scenes

---

## Phase 4: Tools & UI

**Duration:** 4-5 weeks
**Focus:** Build user-facing tools, dialogs, and main UI

### Phase 4A: UI with Filesystem Discovery (CURRENT FOCUS)

**Duration:** 2-3 weeks
**Focus:** Implement UI that works with filesystem discovery only (no CTX nodes yet)

**Scope:**
- ✅ Integrate with `config/project_config.py` only
- ✅ Implement filesystem scanning for shots and assets
- ❌ No CTX node integration (future phase)
- ❌ No ShotManager/AssetManager integration (future phase)

**Goal:** Create working "read-only" UI for browsing filesystem

| Module | Tasks | Priority | Status |
|--------|-------|----------|--------|
| ui/filesystem_discovery.py | 1 | HIGH | ⏳ TODO |
| ui/main_window.py | 1 | HIGH | ⏳ TODO |
| ui/shot_widget.py | 1 | HIGH | ⏳ TODO |
| ui/asset_widget.py | 1 | HIGH | ⏳ TODO |
| tests/test_ui_integration.py | 1 | HIGH | ⏳ TODO |

**Tasks:** [P4-UI-01] through [P4-UI-05] (5 tasks)

---

### Phase 4B: Tools & CTX Integration (FUTURE)

**Duration:** 2-3 weeks
**Focus:** Implement tools and integrate UI with CTX nodes

| Module | Tasks | Priority | Complexity |
|--------|-------|----------|------------|
| tools/shot_manager.py | 5 | HIGH | Complex |
| tools/asset_manager.py | 6 | HIGH | Complex |
| tools/importer.py | 4 | HIGH | Medium |
| tools/converter.py | 3 | MEDIUM | Complex |
| tools/validator.py | 3 | MEDIUM | Medium |
| tools/saver.py | 2 | LOW | Simple |
| ui/ (CTX integration) | 5 | HIGH | Complex |

**Tasks:** [P4-SHOT-01] through [P4-UI-10] (30+ tasks)

---

### Module: tools/shot_manager.py

#### [P4-SHOT-01] Implement Shot Manager Core

**Priority:** HIGH (Critical Path)
**Complexity:** Complex (1 week)
**Dependencies:** `[P1-CONTEXT-01]`, `[P3-SWITCH-01]`

**Description:**
Create shot manager tool to create, edit, and manage shots in the scene.

**Spec Reference:** [spec.md Section 8.1, 7.10](spec.md#81-shot-manager)

**POC Comparison:**
🆕 **New Feature** - POC has no shot management.

**Acceptance Criteria:**
- [ ] Implement `create_shot(ep, seq, shot)` - Create new shot
- [ ] Implement `delete_shot(shot_node)` - Remove shot and assets
- [ ] Implement `duplicate_shot(shot_node, new_shot_code)` - Copy shot
- [ ] Implement `get_shot_info(shot_node)` - Get shot metadata
- [ ] Implement `list_all_shots()` - Get all shots in scene
- [ ] Validate shot codes (format: Ep##, sq####, SH####)

---

#### [P4-SHOT-02] Implement Shot Import/Export

**Priority:** MEDIUM
**Complexity:** Medium (3-5 days)
**Dependencies:** `[P4-SHOT-01]`

**Description:**
Export shot configuration to JSON and import from JSON.

**Spec Reference:** [spec.md Section 8.1](spec.md#81-shot-manager)

**POC Comparison:**
🆕 **New Feature** - POC has no import/export.

**Acceptance Criteria:**
- [ ] Implement `export_shot(shot_node, filepath)` - Save to JSON
- [ ] Implement `import_shot(filepath)` - Load from JSON
- [ ] Include all shot metadata and asset list
- [ ] Support batch export (all shots)
- [ ] Validate JSON schema on import

---

#### [P4-SHOT-03] Implement Shot Comparison

**Priority:** LOW
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P4-SHOT-01]`

**Description:**
Compare two shots to see differences in assets and versions.

**Spec Reference:** [spec.md Section 8.1](spec.md#81-shot-manager)

**POC Comparison:**
🆕 **New Feature** - POC has no comparison.

**Acceptance Criteria:**
- [ ] Implement `compare_shots(shot_node_a, shot_node_b)` - Return diff
- [ ] Show added/removed/modified assets
- [ ] Show version differences
- [ ] Display comparison in UI table
- [ ] Support export comparison to report

---

#### [P4-SHOT-04] Implement Shot Validation

**Priority:** MEDIUM
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P4-SHOT-01]`

**Description:**
Validate shot configuration and asset paths.

**Spec Reference:** [spec.md Section 8.1](spec.md#81-shot-manager)

**POC Comparison:**
🆕 **New Feature** - POC has no validation.

**Acceptance Criteria:**
- [ ] Implement `validate_shot(shot_node)` - Check shot integrity
- [ ] Validate all asset paths exist
- [ ] Check for missing display layers
- [ ] Validate shot code format
- [ ] Return validation report with errors/warnings

---

#### [P4-SHOT-05] Implement Shot Statistics

**Priority:** LOW
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P4-SHOT-01]`

**Description:**
Gather statistics about shots (asset counts, file sizes, etc.).

**Spec Reference:** [spec.md Section 8.1](spec.md#81-shot-manager)

**POC Comparison:**
🆕 **New Feature** - POC has no statistics.

**Acceptance Criteria:**
- [ ] Implement `get_shot_stats(shot_node)` - Return statistics dict
- [ ] Count assets by type (CHAR, PROP, ENV, VEH)
- [ ] Calculate total file sizes
- [ ] Show version distribution
- [ ] Display stats in UI

---

### Module: tools/asset_manager.py

#### [P4-ASSET-01] Implement Asset Manager Core

**Priority:** HIGH (Critical Path)
**Complexity:** Complex (1 week)
**Dependencies:** `[P1-NODES-02]`, `[P2-RESOLVE-01]`

**Description:**
Create asset manager tool to add, remove, and update assets in shots.

**Spec Reference:** [spec.md Section 8.2, 7.11](spec.md#82-asset-manager)

**POC Comparison:**
⚠️ **POC Divergence** - POC has basic node management; spec requires full asset lifecycle.

**Acceptance Criteria:**
- [ ] Implement `add_asset(shot_node, asset_type, name, variant, version)` - Add asset to shot
- [ ] Implement `remove_asset(asset_node)` - Remove asset from shot
- [ ] Implement `update_asset_version(asset_node, new_version)` - Change version
- [ ] Implement `get_asset_info(asset_node)` - Get asset metadata
- [ ] Implement `list_assets_for_shot(shot_node)` - Get all assets
- [ ] Create Maya node (StandIn/Proxy/Reference) when adding asset

---

#### [P4-ASSET-02] Implement Asset Browser

**Priority:** HIGH
**Complexity:** Complex (1 week)
**Dependencies:** `[P1-CACHE-02]`, `[P4-ASSET-01]`

**Description:**
Create asset browser dialog to discover and select assets from filesystem.

**Spec Reference:** [spec.md Section 8.2](spec.md#82-asset-manager)

**POC Comparison:**
🆕 **New Feature** - POC has no asset browser.

**Acceptance Criteria:**
- [ ] Browse publish directories by shot context
- [ ] Display available assets in tree/table view
- [ ] Filter by asset type (CHAR, PROP, ENV, VEH)
- [ ] Show available versions for each asset
- [ ] Preview asset metadata (file size, date, etc.)
- [ ] Multi-select assets for batch import

**Implementation Notes:**
- Use patterns from `igl_shot_build.py` for directory navigation and asset discovery
- Support dropdown navigation: Episode → Sequence → Shot → Version
- Display asset table similar to `igl_shot_build.py::ShotBuildTab`

---

#### [P4-ASSET-03] Implement Asset Version Management

**Priority:** HIGH
**Complexity:** Medium (3-5 days)
**Dependencies:** `[P4-ASSET-01]`, `[P1-CACHE-01]`

**Description:**
Manage asset versions: update, rollback, compare versions.

**Spec Reference:** [spec.md Section 8.2](spec.md#82-asset-manager)

**POC Comparison:**
⚠️ **POC Divergence** - POC has basic version override; spec requires full version management.

**Acceptance Criteria:**
- [ ] Implement `update_to_latest(asset_node)` - Update to latest version
- [ ] Implement `rollback_version(asset_node, target_version)` - Revert to older version
- [ ] Implement `compare_versions(asset_node, version_a, version_b)` - Show differences
- [ ] Implement `get_version_history(asset_node)` - List all versions
- [ ] Support batch version updates for multiple assets

---

#### [P4-ASSET-04] Implement Asset Replacement

**Priority:** MEDIUM
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P4-ASSET-01]`

**Description:**
Replace one asset with another (different asset, same type).

**Spec Reference:** [spec.md Section 8.2](spec.md#82-asset-manager)

**POC Comparison:**
🆕 **New Feature** - POC has no asset replacement.

**Acceptance Criteria:**
- [ ] Implement `replace_asset(asset_node, new_name, new_variant)` - Replace asset
- [ ] Preserve transform/attributes from original node
- [ ] Update CTX_Asset node with new metadata
- [ ] Update display layer assignment
- [ ] Support undo/redo

---

#### [P4-ASSET-05] Implement Asset Duplication

**Priority:** LOW
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P4-ASSET-01]`

**Description:**
Duplicate an asset within the same shot (create instance with different variant).

**Spec Reference:** [spec.md Section 8.2](spec.md#82-asset-manager)

**POC Comparison:**
🆕 **New Feature** - POC has no asset duplication.

**Acceptance Criteria:**
- [ ] Implement `duplicate_asset(asset_node, new_variant)` - Create copy
- [ ] Create new CTX_Asset node
- [ ] Create new Maya node with unique namespace
- [ ] Assign to same display layer
- [ ] Copy transform from original

---

#### [P4-ASSET-06] Implement Asset Validation

**Priority:** MEDIUM
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P4-ASSET-01]`

**Description:**
Validate asset integrity and paths.

**Spec Reference:** [spec.md Section 8.2](spec.md#82-asset-manager)

**POC Comparison:**
🆕 **New Feature** - POC has no asset validation.

**Acceptance Criteria:**
- [ ] Implement `validate_asset(asset_node)` - Check asset integrity
- [ ] Validate file path exists and is readable
- [ ] Check Maya node exists and is valid
- [ ] Validate namespace format
- [ ] Return validation report with errors/warnings

---

### Module: tools/importer.py

#### [P4-IMPORT-01] Implement Asset Importer Core

**Priority:** HIGH
**Complexity:** Medium (3-5 days)
**Dependencies:** `[P4-ASSET-01]`, `[P2-BUILDER-01]`

**Description:**
Import assets into shots using path builder engine.

**Spec Reference:** [spec.md Section 8.3](spec.md#83-asset-importer)

**POC Comparison:**
⚠️ **POC Divergence** - POC has basic import; spec requires path builder integration.

**Acceptance Criteria:**
- [ ] Implement `import_asset(shot_node, input, version='latest')` - Import using path builder
- [ ] Support full filename input: `Ep04_sq0070_SH0170__CHAR_CatStompie_002.abc`
- [ ] Support namespace input: `CHAR_CatStompie_002` (requires context)
- [ ] Create CTX_Asset node and Maya node
- [ ] Assign to display layer
- [ ] Return created asset node

**Implementation Notes:**
- Use path builder engine to resolve paths from both input formats
- Auto-detect node type from file extension (.abc → StandIn, .ma/.mb → Reference)

---

#### [P4-IMPORT-02] Implement Batch Asset Import

**Priority:** MEDIUM
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P4-IMPORT-01]`

**Description:**
Import multiple assets in batch with progress feedback.

**Spec Reference:** [spec.md Section 8.3](spec.md#83-asset-importer)

**POC Comparison:**
🆕 **New Feature** - POC has no batch import.

**Acceptance Criteria:**
- [ ] Implement `import_assets_batch(shot_node, asset_list)` - Import multiple assets
- [ ] Show progress bar during import
- [ ] Handle errors per-asset without failing entire batch
- [ ] Log import statistics (success/failure counts, time)
- [ ] Support cancellation

**Implementation Notes:**
- Use patterns from `igl_shot_build.py` for batch processing workflows
- Process assets in parallel if possible (thread-safe)

---

#### [P4-IMPORT-03] Implement Import Options

**Priority:** LOW
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P4-IMPORT-01]`

**Description:**
Provide import options (namespace, grouping, etc.).

**Spec Reference:** [spec.md Section 8.3](spec.md#83-asset-importer)

**POC Comparison:**
🆕 **New Feature** - POC has no import options.

**Acceptance Criteria:**
- [ ] Support custom namespace override
- [ ] Support parent group assignment
- [ ] Support import mode (reference vs import)
- [ ] Support version override
- [ ] Store import options in preferences

---

#### [P4-IMPORT-04] Implement Import Validation

**Priority:** MEDIUM
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P4-IMPORT-01]`

**Description:**
Validate assets before import to prevent errors.

**Spec Reference:** [spec.md Section 8.3](spec.md#83-asset-importer)

**POC Comparison:**
🆕 **New Feature** - POC has no import validation.

**Acceptance Criteria:**
- [ ] Validate file paths exist before import
- [ ] Check for namespace conflicts
- [ ] Validate file format compatibility
- [ ] Warn about large file sizes
- [ ] Provide pre-import report

---

### Module: tools/converter.py

#### [P4-CONVERT-01] Implement POC Scene Converter

**Priority:** MEDIUM
**Complexity:** Complex (1 week)
**Dependencies:** `[P1-CORE-01]`, `[P1-CORE-02]`, `[P1-CORE-03]`, `[P4-ASSET-01]`

**Description:**
Convert scenes using POC's flat storage to new hierarchical node structure.

**Spec Reference:** [spec.md Section 9.1](spec.md#91-migration-from-poc)

**POC Comparison:**
🆕 **New Feature** - Migration tool for POC users.

**Acceptance Criteria:**
- [ ] Read context from `fileInfo` (POC format)
- [ ] Create CTX_Manager, CTX_Shot, CTX_Asset nodes
- [ ] Migrate proxy nodes with custom attributes to CTX_Asset nodes
- [ ] Migrate reference data from `fileInfo` to CTX_Asset nodes
- [ ] Create display layers for shots
- [ ] Preserve all asset paths and versions
- [ ] Provide conversion report

**Implementation Notes:**
- This is critical for POC users to migrate to production system
- Support dry-run mode to preview changes
- Backup scene before conversion

---

#### [P4-CONVERT-02] Implement Legacy Scene Converter

**Priority:** LOW
**Complexity:** Medium (3-5 days)
**Dependencies:** `[P4-CONVERT-01]`

**Description:**
Convert legacy scenes (non-POC) to CTX system.

**Spec Reference:** [spec.md Section 9.2](spec.md#92-migration-from-legacy)

**POC Comparison:**
🆕 **New Feature** - Migration tool for legacy users.

**Acceptance Criteria:**
- [ ] Detect existing references/proxies in scene
- [ ] Parse namespaces to extract asset info
- [ ] Create CTX nodes for detected assets
- [ ] Prompt user for missing context (ep/seq/shot)
- [ ] Provide conversion report

---

#### [P4-CONVERT-03] Implement Conversion Validation

**Priority:** MEDIUM
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P4-CONVERT-01]`, `[P4-CONVERT-02]`

**Description:**
Validate converted scenes to ensure data integrity.

**Spec Reference:** [spec.md Section 9](spec.md#9-migration-strategy)

**POC Comparison:**
🆕 **New Feature** - Validation for conversions.

**Acceptance Criteria:**
- [ ] Compare asset counts before/after conversion
- [ ] Validate all paths still resolve correctly
- [ ] Check for missing CTX nodes
- [ ] Verify display layer assignments
- [ ] Provide validation report

---

### Module: tools/validator.py

#### [P4-VALID-01] Implement Scene Validator

**Priority:** MEDIUM
**Complexity:** Medium (3-5 days)
**Dependencies:** `[P4-SHOT-04]`, `[P4-ASSET-06]`

**Description:**
Validate entire scene for CTX system integrity.

**Spec Reference:** [spec.md Section 8.4](spec.md#84-scene-validator)

**POC Comparison:**
🆕 **New Feature** - POC has no scene validation.

**Acceptance Criteria:**
- [ ] Validate CTX_Manager exists and is valid
- [ ] Validate all shots have valid context
- [ ] Validate all assets have valid paths
- [ ] Check for orphaned nodes
- [ ] Check for missing display layers
- [ ] Generate comprehensive validation report

---

#### [P4-VALID-02] Implement Auto-Fix

**Priority:** LOW
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P4-VALID-01]`

**Description:**
Automatically fix common validation errors.

**Spec Reference:** [spec.md Section 8.4](spec.md#84-scene-validator)

**POC Comparison:**
🆕 **New Feature** - POC has no auto-fix.

**Acceptance Criteria:**
- [ ] Fix missing display layers
- [ ] Remove orphaned CTX nodes
- [ ] Repair broken node connections
- [ ] Update outdated paths
- [ ] Log all auto-fix operations

---

#### [P4-VALID-03] Implement Validation Reports

**Priority:** LOW
**Complexity:** Simple (1 day)
**Dependencies:** `[P4-VALID-01]`

**Description:**
Generate and export validation reports.

**Spec Reference:** [spec.md Section 8.4](spec.md#84-scene-validator)

**POC Comparison:**
🆕 **New Feature** - POC has no reporting.

**Acceptance Criteria:**
- [ ] Generate HTML report
- [ ] Generate JSON report
- [ ] Include error/warning/info messages
- [ ] Include fix suggestions
- [ ] Support email/Slack notifications

---

### Module: tools/saver.py

#### [P4-SAVE-01] Implement Pre-Save Validation

**Priority:** LOW
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P4-VALID-01]`

**Description:**
Validate scene before saving to catch errors early.

**Spec Reference:** [spec.md Section 8.5](spec.md#85-scene-saver)

**POC Comparison:**
🆕 **New Feature** - POC has no pre-save validation.

**Acceptance Criteria:**
- [ ] Run validation before save
- [ ] Warn user of errors/warnings
- [ ] Allow user to proceed or cancel save
- [ ] Log validation results
- [ ] Support auto-fix before save

---

#### [P4-SAVE-02] Implement Scene Metadata

**Priority:** LOW
**Complexity:** Simple (1 day)
**Dependencies:** None

**Description:**
Store CTX system metadata in scene file.

**Spec Reference:** [spec.md Section 8.5](spec.md#85-scene-saver)

**POC Comparison:**
🆕 **New Feature** - POC has no metadata.

**Acceptance Criteria:**
- [ ] Store CTX system version in `fileInfo`
- [ ] Store last validation timestamp
- [ ] Store shot count and asset count
- [ ] Store config file path
- [ ] Query metadata on scene open

---

### Module: ui/ (Filesystem Discovery Phase)

**IMPORTANT:** This phase implements UI with filesystem discovery ONLY. No CTX node integration yet.

**Integration Scope:**
- ✅ Integrate with `config/project_config.py` (ProjectConfig class)
- ✅ Implement filesystem scanning for shots and assets
- ❌ Do NOT integrate with CTX custom nodes (not implemented yet)
- ❌ Do NOT integrate with ShotManager/AssetManager (not implemented yet)

**Goal:** Create a working "read-only" UI that can browse the filesystem and display shots and assets correctly.

---

#### [P4-UI-01] Implement Filesystem Discovery Module

**Priority:** HIGH (Critical Path - Must complete first)
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P1-CONFIG-01]` (ProjectConfig)

**Description:**
Create filesystem discovery module to scan directory structure and discover shots and assets without relying on CTX nodes.

**Spec Reference:** [spec/ui.md Section 4.2](spec/ui.md#42-import-asset-flow-detailed)

**New Module:** `ui/filesystem_discovery.py`

**Acceptance Criteria:**
- [ ] Implement `scan_shots_from_filesystem(base_path, ep, seq)` function
  - Scans directory: `{base_path}/{ep}/{seq}/SH####/`
  - Returns list of shot codes (e.g., ['SH0170', 'SH0180', 'SH0190'])
  - Handles missing directories gracefully
- [ ] Implement `scan_assets_from_filesystem(publish_path, pattern_manager)` function
  - Scans directory: `{publish_path}/v###/`
  - Parses filenames using pattern_manager
  - Returns list of dicts: `[{type, name, variant, version, path, ext}, ...]`
  - Handles invalid filenames gracefully
- [ ] Implement `get_available_versions(publish_path, asset_id)` function
  - Scans for version directories: `v001/`, `v002/`, `v003/`
  - Returns sorted list: `['v003', 'v002', 'v001']` (descending)
- [ ] Implement `get_shot_asset_count(shot_path)` function
  - Counts assets in shot's publish directories
  - Returns integer count
- [ ] Add comprehensive error handling and logging
- [ ] Write 10+ unit tests for discovery functions

**Data Structures:**

```python
# Shot data structure
{
    'shot_code': 'SH0170',
    'ep': 'Ep04',
    'seq': 'sq0070',
    'path': 'V:/SWA/all/scene/Ep04/sq0070/SH0170',
    'asset_count': 12
}

# Asset data structure
{
    'asset_type': 'CHAR',
    'asset_name': 'CatStompie',
    'variant': '001',
    'version': 'v003',
    'dept': 'anim',
    'path': 'V:/SWA/all/scene/Ep04/sq0070/SH0170/anim/publish/v003/Ep04_sq0070_SH0170__CHAR_CatStompie_001.abc',
    'ext': 'abc',
    'filename': 'Ep04_sq0070_SH0170__CHAR_CatStompie_001.abc'
}
```

**Implementation Notes:**
- Use `os.walk()` or `os.listdir()` for directory scanning
- Use `PatternManager` from `config/pattern_manager.py` for filename parsing
- Cache scan results to avoid repeated filesystem access
- Support both Windows and Linux paths

---

#### [P4-UI-02] Implement Main Window UI (Filesystem Mode)

**Priority:** HIGH (Critical Path)
**Complexity:** Medium (3-5 days)
**Dependencies:** `[P4-UI-01]` (Filesystem Discovery)

**Description:**
Create main dockable UI window with header, shot list, and asset table. Uses filesystem discovery only.

**Spec Reference:** [spec/ui.md Section 1](spec/ui.md#1-main-window-architecture)

**New Module:** `ui/main_window.py`

**Acceptance Criteria:**
- [ ] Create dockable Maya window using `QMainWindow`
- [ ] Implement header section with:
  - Project selector (QComboBox) - loads from ProjectConfig
  - Episode selector (QComboBox) - populated from config
  - Sequence selector (QComboBox) - populated from config
  - Settings button (QPushButton) - placeholder for now
  - Help button (QPushButton) - placeholder for now
- [ ] Integrate ShotWidget (from [P4-UI-03])
- [ ] Integrate AssetWidget (from [P4-UI-04])
- [ ] Implement status bar with message display
- [ ] Support PySide2/PySide6 compatibility
- [ ] Make window dockable in Maya workspace
- [ ] Implement `refresh_ui()` method to reload data from filesystem

**Data Flow:**
```
User selects Project/Episode/Sequence
    ↓
MainWindow calls scan_shots_from_filesystem()
    ↓
ShotWidget displays discovered shots
    ↓
User selects shot
    ↓
MainWindow calls scan_assets_from_filesystem()
    ↓
AssetWidget displays discovered assets
```

**Implementation Notes:**
- Window size: 800x600 pixels (initial)
- Window title: "Context Manager (Filesystem Mode)"
- Use QVBoxLayout for main layout
- Store selected project/ep/seq in instance variables
- Emit signals when selections change

---

#### [P4-UI-03] Implement Shot Widget (Filesystem Mode)

**Priority:** HIGH
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P4-UI-01]` (Filesystem Discovery)

**Description:**
Create shot widget to display shots discovered from filesystem with radio button selection.

**Spec Reference:** [spec/ui.md Section 1.3](spec/ui.md#13-shot-management-section)

**New Module:** `ui/shot_widget.py`

**Acceptance Criteria:**
- [ ] Create custom QWidget with QListWidget
- [ ] Display shot list with custom item widgets containing:
  - Radio button for selection (only one active)
  - Shot code label (e.g., "SH0170")
  - Asset count label (e.g., "12 assets")
  - Frame range label (placeholder: "[1001-1050]")
- [ ] Implement `load_shots(shots_data)` method
  - Takes list of shot dicts from filesystem discovery
  - Populates list widget
  - First shot selected by default
- [ ] Implement `get_selected_shot()` method
  - Returns selected shot code or None
- [ ] Emit `shot_selected` signal when selection changes
- [ ] Support double-click to select shot
- [ ] Add "Add Shot" button (disabled for now - placeholder)

**Widget Layout:**
```
+-----------------------------------------------------------------------+
|  SHOTS IN SCENE                                            [+ Add]    |
|  +-------------------------------------------------------------------+|
|  | (*) SH0170   12 assets    [1001-1050]                            ||
|  | ( ) SH0180    8 assets    [1001-1062]                            ||
|  | ( ) SH0190    5 assets    [1001-1045]                            ||
|  +-------------------------------------------------------------------+|
+-----------------------------------------------------------------------+
```

**Implementation Notes:**
- Use QListWidget with custom item widgets
- Radio buttons implemented using QRadioButton in QButtonGroup
- Frame range is placeholder (hardcoded or from config)
- Asset count from `get_shot_asset_count()` function

---

#### [P4-UI-04] Implement Asset Widget (Filesystem Mode)

**Priority:** HIGH
**Complexity:** Medium (3-5 days)
**Dependencies:** `[P4-UI-01]` (Filesystem Discovery)

**Description:**
Create asset widget to display assets discovered from filesystem in a table with columns.

**Spec Reference:** [spec/ui.md Section 1.4](spec/ui.md#14-asset-management-section)

**New Module:** `ui/asset_widget.py`

**Acceptance Criteria:**
- [ ] Create custom QWidget with QTableWidget
- [ ] Implement table with columns:
  - Type (str): Asset type (CHAR, PROP, SET, etc.)
  - Name (str): Asset name (CatStompie, DogBounce, etc.)
  - Var (str): Variant (001, 002, etc.)
  - Dept (str): Department (anim, model, rig, etc.)
  - Ver (str): Version (v001, v002, v003, etc.)
  - Status (widget): Color indicator (green/yellow/red)
- [ ] Implement `load_assets(assets_data)` method
  - Takes list of asset dicts from filesystem discovery
  - Populates table rows
  - Sets status colors based on file existence
- [ ] Implement `get_selected_assets()` method
  - Returns list of selected asset dicts
- [ ] Support multi-row selection (Ctrl+Click, Shift+Click)
- [ ] Support sortable columns (click header to sort)
- [ ] Add "Import" button (disabled for now - placeholder)
- [ ] Add "Convert Scene" button (disabled for now - placeholder)

**Widget Layout:**
```
+-----------------------------------------------------------------------+
|  ASSETS IN SH0170                            [+ Import] [Convert]     |
|  +-------------------------------------------------------------------+|
|  | Type  | Name           | Var | Dept | Ver  | Status              ||
|  |-------|----------------|-----|------|------|---------------------||
|  | CHAR  | CatStompie     | 001 | anim | v003 | ● Valid             ||
|  | CHAR  | DogBounce      | 001 | anim | v002 | ● Valid             ||
|  | PROP  | TreeBig        | 001 | anim | v001 | ● Valid             ||
|  +-------------------------------------------------------------------+|
+-----------------------------------------------------------------------+
```

**Status Colors:**
- 🟢 Green: File exists at resolved path
- 🟡 Yellow: Newer version available (future enhancement)
- 🔴 Red: File not found at resolved path

**Implementation Notes:**
- Use QTableWidget with 6 columns
- Status column uses QLabel with colored circle (●)
- Validate file existence using `os.path.exists()`
- Store full asset dict in row's UserRole data

---

#### [P4-UI-05] Implement UI Integration Tests

**Priority:** HIGH
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P4-UI-02]`, `[P4-UI-03]`, `[P4-UI-04]`

**Description:**
Write integration tests to verify UI components work together correctly with filesystem discovery.

**New Module:** `tests/test_ui_integration.py`

**Acceptance Criteria:**
- [ ] Test MainWindow initialization
- [ ] Test project/episode/sequence selection flow
- [ ] Test shot list population from filesystem
- [ ] Test asset table population from filesystem
- [ ] Test shot selection updates asset table
- [ ] Test UI refresh after filesystem changes
- [ ] Mock filesystem for consistent test results
- [ ] Achieve 80%+ code coverage for UI modules

**Test Scenarios:**
```python
def test_main_window_loads_projects():
    """Test that main window loads projects from config."""

def test_shot_widget_displays_discovered_shots():
    """Test that shot widget displays shots from filesystem."""

def test_asset_widget_displays_discovered_assets():
    """Test that asset widget displays assets from filesystem."""

def test_shot_selection_updates_asset_table():
    """Test that selecting a shot updates the asset table."""

def test_status_colors_reflect_file_existence():
    """Test that status colors are correct based on file existence."""
```

---

### UI Implementation Summary (Filesystem Discovery Phase)

**Modules Created:**
1. `ui/__init__.py` - Package initialization
2. `ui/filesystem_discovery.py` - Filesystem scanning functions
3. `ui/main_window.py` - Main dockable window
4. `ui/shot_widget.py` - Shot list widget
5. `ui/asset_widget.py` - Asset table widget
6. `tests/test_ui_integration.py` - UI integration tests

**Total Tasks:** 5 tasks (P4-UI-01 through P4-UI-05)
**Estimated Duration:** 2-3 weeks
**Dependencies:** Only ProjectConfig and PatternManager

**Data Flow Diagram:**
```
Filesystem
    ↓
scan_shots_from_filesystem() → Shot Data
    ↓
ShotWidget displays shots
    ↓
User selects shot
    ↓
scan_assets_from_filesystem() → Asset Data
    ↓
AssetWidget displays assets
```

**Key Features:**
- ✅ Browse filesystem without CTX nodes
- ✅ Display shots discovered from directory structure
- ✅ Display assets discovered from publish directories
- ✅ Color-coded status based on file existence
- ✅ Project/Episode/Sequence navigation
- ✅ Shot selection with radio buttons
- ✅ Asset table with sortable columns
- ❌ No CTX node integration (future phase)
- ❌ No import/export functionality (future phase)
- ❌ No shot/asset creation (future phase)

**Success Criteria:**
- [ ] UI opens as dockable Maya window
- [ ] Project selector loads from config
- [ ] Shot list displays shots from filesystem
- [ ] Asset table displays assets from filesystem
- [ ] Selecting shot updates asset table
- [ ] Status colors reflect file existence
- [ ] All tests pass (80%+ coverage)
- [ ] No errors in Maya script editor

---

### Module: ui/ (Future: CTX Node Integration Phase)

**NOTE:** These tasks will be implemented AFTER the filesystem discovery phase is complete and CTX nodes are implemented.

---

#### [P4-UI-06] Integrate CTX Nodes with UI (FUTURE)

**Priority:** HIGH (After CTX nodes implemented)
**Complexity:** Complex (1 week)
**Dependencies:** `[P4-SHOT-01]`, `[P4-ASSET-01]`, `[P3-SWITCH-01]`, `[P4-UI-02]`

**Description:**
Integrate UI with CTX custom nodes for full read/write functionality.

**Spec Reference:** [spec/ui.md Section 4](spec/ui.md#4-data-flow)

**Acceptance Criteria:**
- [ ] Replace filesystem discovery with CTX node queries
- [ ] Implement shot creation via ShotManager
- [ ] Implement asset import via AssetManager
- [ ] Implement shot switching via DisplayLayerManager
- [ ] Update UI when CTX nodes change
- [ ] Support Maya undo/redo for all operations
- [ ] Add callbacks for node creation/deletion

**Implementation Notes:**
- This task bridges filesystem mode to full CTX mode
- Keep filesystem discovery as fallback for scenes without CTX nodes
- Use Maya callbacks to keep UI in sync with scene changes

---

#### [P4-UI-07] Implement Import Asset Dialog (FUTURE)

**Priority:** HIGH (After CTX nodes implemented)
**Complexity:** Medium (3-5 days)
**Dependencies:** `[P4-UI-06]`, `[P4-ASSET-02]`

**Description:**
Create import asset dialog for adding assets to shots.

**Spec Reference:** [spec/ui.md Section 2.2](spec/ui.md#22-import-asset-dialog)

**Acceptance Criteria:**
- [ ] Create modal dialog with department/type/asset selectors
- [ ] Display available versions from filesystem
- [ ] Show path preview and validation
- [ ] Support StandIn/Reference import types
- [ ] Call AssetManager.import_asset() on confirm
- [ ] Update main window after import

---

#### [P4-UI-08] Implement Add Shot Dialog (FUTURE)

**Priority:** HIGH (After CTX nodes implemented)
**Complexity:** Simple (2-3 days)
**Dependencies:** `[P4-UI-06]`, `[P4-SHOT-01]`

**Description:**
Create add shot dialog for adding shots to scene.

**Spec Reference:** [spec/ui.md Section 2.1](spec/ui.md#21-add-shot-dialog)

**Acceptance Criteria:**
- [ ] Create modal dialog with shot code and frame range inputs
- [ ] Validate shot code format (SH####)
- [ ] Support "Copy assets from" option
- [ ] Call ShotManager.create_shot() on confirm
- [ ] Update main window after shot creation

---

#### [P4-UI-09] Implement Convert Scene Dialog (FUTURE)

**Priority:** MEDIUM (After CTX nodes implemented)
**Complexity:** Medium (3-5 days)
**Dependencies:** `[P4-UI-06]`, `[P4-CONVERT-01]`

**Description:**
Create convert scene dialog for migrating existing scenes to CTX system.

**Spec Reference:** [spec/ui.md Section 2.3](spec/ui.md#23-convert-scene-dialog)

**Acceptance Criteria:**
- [ ] Scan for existing aiStandIn/RSProxyMesh/reference nodes
- [ ] Auto-detect context from paths
- [ ] Allow user to select nodes to convert
- [ ] Call Converter.convert_scene() on confirm
- [ ] Show conversion report

---

#### [P4-UI-10] Implement Settings Dialog (FUTURE)

**Priority:** LOW
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P4-UI-02]`, `[P1-CONFIG-01]`

**Description:**
Create settings dialog for user preferences and configuration.

**Spec Reference:** [spec/ui.md Section 2.4](spec/ui.md#24-settings-dialog)

**Acceptance Criteria:**
- [ ] Display current configuration path
- [ ] Allow config file selection
- [ ] Show platform mapping settings
- [ ] Provide template editor
- [ ] Support preference save/load
- [ ] Validate settings before applying

---

## Phase 5: Testing, Validation & Documentation

**Duration:** 2-3 weeks
**Focus:** Comprehensive testing, documentation, and deployment preparation

### Phase 5 Summary

| Module | Tasks | Priority | Complexity |
|--------|-------|----------|------------|
| tests/ | 8 | HIGH | Medium |
| docs/ | 4 | MEDIUM | Simple |
| farm/ | 2 | MEDIUM | Medium |

---

### Module: tests/

#### [P5-TEST-01] Implement Unit Tests for Config Module

**Priority:** HIGH
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P1-CONFIG-01]`, `[P1-CONFIG-02]`, `[P1-CONFIG-03]`, `[P1-CONFIG-04]`

**Description:**
Write comprehensive unit tests for configuration loading and validation.

**Spec Reference:** [spec.md Section 11.1](spec.md#111-unit-tests)

**POC Comparison:**
🆕 **New Feature** - POC has no tests.

**Acceptance Criteria:**
- [ ] Test config loading from JSON
- [ ] Test platform detection and path mapping
- [ ] Test template loading and validation
- [ ] Test pattern compilation
- [ ] Test error handling for invalid configs
- [ ] Achieve 90%+ code coverage for config module

---

#### [P5-TEST-02] Implement Unit Tests for Core Module

**Priority:** HIGH
**Complexity:** Medium (3-5 days)
**Dependencies:** `[P1-CORE-01]`, `[P1-CORE-02]`, `[P1-CORE-03]`, `[P1-CONTEXT-01]`, `[P1-NODES-01]`

**Description:**
Write comprehensive unit tests for custom nodes and context management.

**Spec Reference:** [spec.md Section 11.1](spec.md#111-unit-tests)

**POC Comparison:**
🆕 **New Feature** - POC has no tests.

**Acceptance Criteria:**
- [ ] Test CTX node creation and attributes
- [ ] Test context management API
- [ ] Test node operations (get/set paths)
- [ ] Test asset registration
- [ ] Test callback system
- [ ] Achieve 90%+ code coverage for core module

---

#### [P5-TEST-03] Implement Unit Tests for Path Resolution

**Priority:** HIGH
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P2-TOKEN-01]`, `[P2-RESOLVE-01]`, `[P2-BUILDER-01]`

**Description:**
Write comprehensive unit tests for token expansion and path resolution.

**Spec Reference:** [spec.md Section 11.1](spec.md#111-unit-tests)

**POC Comparison:**
🆕 **New Feature** - POC has no tests.

**Acceptance Criteria:**
- [ ] Test token expansion with all token types
- [ ] Test path resolution with various templates
- [ ] Test path builder with full filename and namespace inputs
- [ ] Test filename and namespace parsing
- [ ] Test error handling for invalid inputs
- [ ] Achieve 90%+ code coverage for path resolution modules

---

#### [P5-TEST-04] Implement Unit Tests for Display Layers

**Priority:** MEDIUM
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P3-LAYER-01]`, `[P3-LAYER-02]`, `[P3-LAYER-03]`

**Description:**
Write unit tests for display layer management.

**Spec Reference:** [spec.md Section 11.1](spec.md#111-unit-tests)

**POC Comparison:**
🆕 **New Feature** - POC has no tests.

**Acceptance Criteria:**
- [ ] Test layer creation with correct naming
- [ ] Test asset-to-layer assignment
- [ ] Test layer visibility control
- [ ] Test layer query functions
- [ ] Achieve 90%+ code coverage for display layer module

---

#### [P5-TEST-05] Implement Integration Tests

**Priority:** HIGH
**Complexity:** Medium (3-5 days)
**Dependencies:** All Phase 1-4 tasks

**Description:**
Write integration tests for end-to-end workflows.

**Spec Reference:** [spec.md Section 11.2](spec.md#112-integration-tests)

**POC Comparison:**
🆕 **New Feature** - POC has no tests.

**Acceptance Criteria:**
- [ ] Test complete shot creation workflow
- [ ] Test asset import workflow
- [ ] Test shot switching workflow
- [ ] Test version update workflow
- [ ] Test scene conversion workflow
- [ ] Test multi-shot scene scenarios

---

#### [P5-TEST-06] Implement Performance Tests

**Priority:** MEDIUM
**Complexity:** Medium (2-3 days)
**Dependencies:** All Phase 1-4 tasks

**Description:**
Write performance tests to ensure system meets performance targets.

**Spec Reference:** [spec.md Section 11.3](spec.md#113-performance-tests)

**POC Comparison:**
🆕 **New Feature** - POC has no performance tests.

**Acceptance Criteria:**
- [ ] Test shot switching performance (target: < 1 second)
- [ ] Test path resolution performance (target: < 100ms per asset)
- [ ] Test cache building performance
- [ ] Test batch operations performance
- [ ] Profile memory usage for large scenes
- [ ] Generate performance reports

---

#### [P5-TEST-07] Implement Maya Version Compatibility Tests

**Priority:** MEDIUM
**Complexity:** Medium (2-3 days)
**Dependencies:** All Phase 1-4 tasks

**Description:**
Test compatibility across Maya versions (2022, 2023, 2024).

**Spec Reference:** [spec.md Section 11.4](spec.md#114-compatibility-tests)

**POC Comparison:**
🆕 **New Feature** - POC has no compatibility tests.

**Acceptance Criteria:**
- [ ] Test on Maya 2022 (Python 2.7)
- [ ] Test on Maya 2023 (Python 3.9)
- [ ] Test on Maya 2024 (Python 3.10)
- [ ] Test PySide2/PySide6 compatibility
- [ ] Document version-specific issues
- [ ] Ensure all features work across versions

---

#### [P5-TEST-08] Implement Test Data Generation

**Priority:** LOW
**Complexity:** Simple (1-2 days)
**Dependencies:** None

**Description:**
Create utilities to generate test data (scenes, configs, assets).

**Spec Reference:** [spec.md Section 11.5](spec.md#115-test-utilities)

**POC Comparison:**
🆕 **New Feature** - POC has no test utilities.

**Acceptance Criteria:**
- [ ] Generate sample project structure
- [ ] Generate sample cache files with correct naming
- [ ] Generate sample config files
- [ ] Generate test scenes with CTX nodes
- [ ] Provide cleanup utilities

---

### Module: docs/

#### [P5-DOC-01] Write User Documentation

**Priority:** MEDIUM
**Complexity:** Simple (2-3 days)
**Dependencies:** All Phase 1-4 tasks

**Description:**
Write comprehensive user documentation for artists and TDs.

**Spec Reference:** [spec.md Section 12.1](spec.md#121-user-documentation)

**POC Comparison:**
🆕 **New Feature** - POC has no documentation.

**Acceptance Criteria:**
- [ ] Write getting started guide
- [ ] Document all UI features with screenshots
- [ ] Write workflow tutorials (shot creation, asset import, etc.)
- [ ] Document common troubleshooting scenarios
- [ ] Provide FAQ section
- [ ] Generate HTML/PDF documentation

---

#### [P5-DOC-02] Write API Documentation

**Priority:** MEDIUM
**Complexity:** Simple (2-3 days)
**Dependencies:** All Phase 1-4 tasks

**Description:**
Write API documentation for developers and pipeline TDs.

**Spec Reference:** [spec.md Section 12.2](spec.md#122-api-documentation)

**POC Comparison:**
🆕 **New Feature** - POC has no API docs.

**Acceptance Criteria:**
- [ ] Document all public APIs with docstrings
- [ ] Generate API reference with Sphinx or similar
- [ ] Provide code examples for common operations
- [ ] Document custom node attributes
- [ ] Document configuration schema
- [ ] Generate HTML API documentation

---

#### [P5-DOC-03] Write Migration Guide

**Priority:** MEDIUM
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P4-CONVERT-01]`, `[P4-CONVERT-02]`

**Description:**
Write migration guide for POC and legacy users.

**Spec Reference:** [spec.md Section 12.3](spec.md#123-migration-guide)

**POC Comparison:**
🆕 **New Feature** - POC has no migration guide.

**Acceptance Criteria:**
- [ ] Document POC to production migration steps
- [ ] Document legacy scene conversion steps
- [ ] Provide migration checklist
- [ ] Document common migration issues
- [ ] Provide rollback procedures

---

#### [P5-DOC-04] Write Deployment Guide

**Priority:** LOW
**Complexity:** Simple (1 day)
**Dependencies:** All Phase 1-4 tasks

**Description:**
Write deployment guide for pipeline administrators.

**Spec Reference:** [spec.md Section 12.4](spec.md#124-deployment-guide)

**POC Comparison:**
🆕 **New Feature** - POC has no deployment guide.

**Acceptance Criteria:**
- [ ] Document installation steps
- [ ] Document configuration setup
- [ ] Document environment variables
- [ ] Document Maya module setup
- [ ] Provide deployment checklist

---

### Module: farm/

#### [P5-FARM-01] Implement Pre-Render Callback

**Priority:** MEDIUM
**Complexity:** Medium (2-3 days)
**Dependencies:** `[P1-CONTEXT-01]`, `[P2-RESOLVE-01]`

**Description:**
Implement pre-render callback to resolve paths before render farm submission.

**Spec Reference:** [spec.md Section 13.1](spec.md#131-render-farm-integration)

**POC Comparison:**
✅ **Can Adapt POC Code** - POC has pre-render callback; needs multi-shot support.

**Acceptance Criteria:**
- [ ] Register Maya pre-render callback
- [ ] Resolve all asset paths for active shot
- [ ] Update Maya nodes with resolved paths
- [ ] Log all path resolutions
- [ ] Handle errors gracefully

**Implementation Notes:**
- Reuse POC's callback registration pattern
- Add multi-shot support (resolve only active shot's assets)
- Ensure callback is fast (< 5 seconds for typical scenes)

---

#### [P5-FARM-02] Implement Export Utilities

**Priority:** LOW
**Complexity:** Simple (1-2 days)
**Dependencies:** `[P5-FARM-01]`

**Description:**
Provide utilities to export scene metadata for render farm.

**Spec Reference:** [spec.md Section 13.2](spec.md#132-export-utilities)

**POC Comparison:**
🆕 **New Feature** - POC has no export utilities.

**Acceptance Criteria:**
- [ ] Export shot context to JSON
- [ ] Export asset list with resolved paths
- [ ] Export render settings
- [ ] Support batch export for multiple shots
- [ ] Validate exported data

---

## Migration Strategy

### From POC to Production

**Timeline:** 1-2 weeks (can be done in parallel with Phase 5)

#### Key Differences

| Aspect | POC | Production Spec |
|--------|-----|-----------------|
| **Data Storage** | Flat `fileInfo` | Hierarchical CTX nodes |
| **Multi-Shot** | Single shot only | Multiple shots per scene |
| **Display Layers** | None | Shot-specific layers |
| **Configuration** | Hardcoded | JSON-based |
| **Path Builder** | None | Full/namespace input support |
| **Version Cache** | None | Filesystem scanning |

#### Migration Steps

1. **Backup Scenes** - Create backups of all POC scenes before conversion
2. **Run Converter** - Use `[P4-CONVERT-01]` tool to convert scenes
3. **Validate Conversion** - Use `[P4-CONVERT-03]` to validate converted scenes
4. **Test Workflows** - Test all workflows in converted scenes
5. **Deploy Configuration** - Set up project configuration files
6. **Train Users** - Provide training on new features (multi-shot, display layers)
7. **Monitor** - Monitor for issues during first week of production use

#### Reusable POC Code

The following POC code can be adapted for production:

- ✅ **Token Expansion** - `expand_tokens()` method works well
- ✅ **Callback System** - `_notify_change()` and callback registration
- ✅ **Node Type Detection** - `get_node_type()` logic
- ✅ **UI Structure** - Qt compatibility layer and basic layout
- ✅ **Pre-Render Callback** - Callback registration pattern

---

## Risk Assessment

### High-Risk Tasks

| Task ID | Risk | Mitigation |
|---------|------|------------|
| `[P1-CORE-01/02/03]` | Custom node implementation complexity | Prototype early, test thoroughly, consult Maya API docs |
| `[P3-SWITCH-01]` | Shot switching performance | Profile early, optimize layer operations, use caching |
| `[P4-CONVERT-01]` | POC conversion data loss | Extensive testing, backup requirement, dry-run mode |
| `[P4-UI-01]` | UI complexity and responsiveness | Incremental development, user testing, performance profiling |
| `[P5-FARM-01]` | Render farm callback reliability | Extensive testing, error handling, logging |

### Medium-Risk Tasks

| Task ID | Risk | Mitigation |
|---------|------|------------|
| `[P2-BUILDER-01]` | Path builder edge cases | Comprehensive unit tests, regex validation |
| `[P1-CACHE-02]` | Asset discovery performance | Async scanning, caching, progress feedback |
| `[P4-ASSET-02]` | Browser UI complexity | Use proven patterns from igl_shot_build.py |

### Dependencies on External Systems

- **Filesystem Performance** - Network path access speed affects cache building and validation
- **Maya API Stability** - Custom nodes depend on Maya API behavior across versions
- **Qt Version Compatibility** - PySide2/PySide6 differences may cause UI issues

---

## Testing Strategy

### Test Pyramid

```
        /\
       /  \      E2E Tests (10%)
      /____\     - Full workflows
     /      \    - User scenarios
    /________\   Integration Tests (30%)
   /          \  - Module interactions
  /____________\ Unit Tests (60%)
                 - Individual functions
```

### Test Coverage Targets

- **Unit Tests:** 90%+ coverage for all modules
- **Integration Tests:** All critical workflows covered
- **Performance Tests:** All performance targets validated
- **Compatibility Tests:** All supported Maya versions tested

### Test Execution

- **Local Development:** Run unit tests on every commit
- **CI/CD Pipeline:** Run all tests on pull requests
- **Pre-Release:** Full test suite + manual QA
- **Production:** Smoke tests after deployment

### Test Data

- **Sample Project:** `V:/SWA_TEST/` with realistic structure
- **Sample Assets:** 50+ test cache files across all types
- **Sample Scenes:** 10+ test scenes covering various scenarios
- **Sample Configs:** Multiple config variations for testing

---

## Appendix: Task Dependencies Graph

### Critical Path (Must Complete in Order)

```
[P1-CONFIG-01] → [P1-CORE-01] → [P1-CORE-02] → [P1-CORE-03]
                                                      ↓
[P2-TOKEN-01] → [P2-RESOLVE-01] → [P2-BUILDER-01]   ↓
                                                      ↓
[P3-LAYER-01] → [P3-SWITCH-01] ←──────────────────────
                      ↓
[P4-SHOT-01] → [P4-ASSET-01] → [P4-UI-01]
                      ↓
                [P5-TEST-05] → [P5-DOC-01]
```

### Parallel Work Streams

**Stream 1: Core Architecture**
- Phase 1 config and core modules
- Can start immediately

**Stream 2: Path Resolution**
- Phase 2 token and resolver modules
- Depends on `[P1-CONFIG-01]` and `[P1-CONTEXT-01]`

**Stream 3: Display Layers**
- Phase 3 layer management
- Depends on `[P1-CORE-02]`

**Stream 4: Tools & UI**
- Phase 4 tools and UI
- Depends on Phase 1-3 completion

**Stream 5: Testing & Docs**
- Phase 5 testing and documentation
- Can start unit tests early, integration tests after Phase 4

---

## Conclusion

This task list provides a comprehensive roadmap for implementing the Context Variables Pipeline system. The 92 tasks are organized into 6 phases (0-5) with clear dependencies, acceptance criteria, and POC comparisons.

**Key Success Factors:**
1. **Start with Phase 0** - Complete repository setup before any implementation
2. Complete critical path tasks in order
3. Maintain 90%+ test coverage
4. Validate conversions thoroughly
5. Provide comprehensive documentation
6. Monitor performance continuously

**Estimated Timeline:** 12-16 weeks with 2-3 developers (plus 1-2 days for Phase 0)

**Next Steps:**
1. ✅ Review and approve task list
2. ⬜ **START HERE:** Complete Phase 0 (Repository Setup) - Tasks `[P0-REPO-01]` through `[P0-REPO-05]`
3. ⬜ Complete Pre-Implementation Checklist
4. ⬜ Begin Phase 1: Core Architecture
5. ⬜ Establish weekly progress reviews

**Development Workflow:**
1. Complete Phase 0 repository setup
2. For each task, create feature branch from `develop`
3. Implement task following acceptance criteria
4. Write tests (90%+ coverage)
5. Create Pull Request using template
6. Code review and merge to `develop`
7. Periodically merge `develop` to `main` for releases

---

**Document Status:** ✅ Complete
**Repository:** https://github.com/katha-begin/maya-multishot.git
**Total Tasks:** 92 (5 setup + 87 implementation)
**Ready for Implementation:** Yes - Start with Phase 0


