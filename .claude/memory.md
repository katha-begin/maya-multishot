# Project Memory — Maya Multishot Pipeline

> AI agent session log. Update this file at the end of every work session.
> Format: newest entries first. Keep entries concise.

---

## Project Identity

- **Name:** Maya Multishot Pipeline
- **Repo:** https://github.com/katha-begin/maya-multishot.git
- **Purpose:** Multi-shot context management for Maya artists (no scene open/close cycling)
- **Stack:** Python 3.7+ (Maya 2022+), PySide2/PySide6, Maya cmds API, custom network nodes

---

## Current State

**Updated:** 2026-03-08
**Active Branch:** `feature/ui-tools-framework`
**Current Phase:** Phase 3 complete. Phase 4 (Production & Automation) — decision pending.

### Phase 3 — Complete

All gaffer engine + UI shipped and tested in Maya. No outstanding Phase 3 tasks.

**Known remaining issues (not blocking Phase 4):**
- `tests/test_asset_manager.py` — 10 pre-existing failures (renderer work, not gaffer)
- `core/ctx_converter.py::convert_to_ctx()` — still uses `core.custom_nodes`, not in active path

### Phase 4 — Pending Decision

Full gap analysis written to `spec/PRODUCTION_READINESS.md`.

**P1 gaps (blocking mass production):**
- No headless pipeline API for farm / TD automation
- No scene validator (drift found at render time, not before)
- No gaffer JSON export/import (can't share presets between scenes)
- No production tracker integration (ShotGrid / FTrack)
- No undo/redo on gaffer operations

**P2 gaps (significant at scale):**
- Print statements throughout (no structured logging)
- Gaffer attributes hardcoded (not config-driven)
- No farm render hook (no pre-render shot-apply)
- No background threading (UI blocks on long ops)
- CTXLightOriginalsNode fragile (no recovery if deleted)

### Completed Phases (DO NOT REVISIT)

- ✅ Phase 0: Repository setup
- ✅ Phase 1–4: Core nodes, paths, display layers, basic UI
- ✅ Phase 5: Light Gaffer System (63 tests passing)
- ✅ Phase 1-schema: Schema-based node system (all 6 node types complete)

---

## Key Decisions & Architecture

### Node System Decision (FINAL)
- **Primary:** `core/nodes/wrappers/` — schema-based, use for ALL new code
- **Legacy:** `core/custom_nodes.py` — FROZEN, backward compat only, do NOT modify
- **Attribute name:** `ctx_type` (snake_case) — NOT `ctx_node_type`

### Connection Pattern Decision (FINAL)
- **Unidirectional ONLY:** `child.message → parent.attribute`
- Never create bidirectional connections
- Query in both directions from a single connection using `source=True/False`

### Gaffer Architecture (FINAL — confirmed with user 2026-03-07)

**Gaffer is optional.** No gaffer = lights use original Maya values.

**Connections:**
```
gaffer.message         → CTX_Sequence.gaffer       (sequence owns this gaffer)
gaffer.message         → CTX_Shot.gaffer            (shot owns this gaffer)
parent_gaffer.message  → child_gaffer.parentGaffer  (inheritance chain)
light_ctx.message      → gaffer.lights[i]           (light belongs to gaffer)
```

**Inheritance rules:**
- Child inherits ALL lights from parent. Can override values and/or add new lights.
- Same light cannot be in same gaffer twice. Same light CAN be in parent AND child (child = override).
- A gaffer can be shared between multiple shots.

**Shot-switch apply order:**
1. Shot has gaffer → apply it (chain walks parent automatically)
2. No shot gaffer → use sequence gaffer if available
3. No gaffer anywhere → restore original light values (snapshot from window open)

**`isinstance` anti-pattern — NEVER use wrapper class for isinstance after reload:**
```python
# WRONG (stale class after reload):
gaffer_node = gaffer.node_name if isinstance(gaffer, CTXLightGafferNode) else gaffer
# CORRECT:
gaffer_node = gaffer if isinstance(gaffer, str) else gaffer.node_name
```
Fixed in: `light_context.py:set_parent_gaffer`, `gaffer.py:set_parent_gaffer`

### Path Resolution (CRITICAL — easy to get wrong)
- Config: `project_configs/ctx_config.json` — single source of truth for templates, roots, tokens
- Templates are **named keys** in config (`publishPath`, `assetPath`, etc.) — never write template strings by hand
- All tokens are **camelCase**: `$projRoot`, `$assetType`, `$assetName`, `$variant` — NOT `$asset_type`
- `_` in templates is a separator, NOT part of token names: `$ep_$seq_$shot` = three tokens
- Resolver auto-injects `projRoot`, `imgRoot`, `project`, `sceneBase`, `assetBase` from config
- Real example: `"publishPath"` → `$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish`
  → Windows result: `V:\SWA\all\scene\Ep04\sq0070\SH0170\lighting\publish`

### BaseManager Pattern (COMPLETE — Phase 2)
- `MAYA_AVAILABLE` flag for Maya-free testing
- `MockCmds` for test isolation
- Dependency injection: pass `cmds` to constructors

---

## Known Issues / Watchpoints

| Issue | File | Notes |
|---|---|---|
| Pre-existing test failures | `tests/test_asset_manager.py` | `add_asset()` imports `create_standin_with_namespace` from `core.nodes` which doesn't exist — renderer handlers not yet implemented (Phase 3+) |

---

## Session Log

### 2026-03-08 — Session 9
**Done: Bug fix + production readiness analysis**

Bug fix:
- `core/nodes/wrappers/light_context.py:set_target_light()` — now normalizes input to shape node. If a transform is passed, resolves to first child shape (direct then `allDescendants`). Previously stored the transform node when editing inherited lights, causing inconsistent `targetLight` connections.
- `core/gaffer/manager.py:add_light_to_gaffer()` — normalized `light_shape` to `resolved_shape` at entry point. Ensures `lightName` defaults to the shape name, and all downstream calls (`create`, `set_target_light`, `capture_light_values`, originals storage) consistently use the shape node.

Analysis + docs:
- Full production readiness analysis written to `spec/PRODUCTION_READINESS.md` — strengths, 18 weaknesses, 14 recommendations with priority and effort ratings, suggested sprint sequencing.
- `CLAUDE.md` section 2 updated: Phase 3 marked complete, Phase 4 gaps summarised.
- `.claude/memory.md` current state updated.

**Next session should start with:**
- User decision on Phase 4 priority (read `spec/PRODUCTION_READINESS.md` first)
- Suggested starting point if approved: R5 (undo/redo, 1 day) + R2 (scene validator, 2 days) + R6 (logging, 1 day) — Sprint 1 reliability foundation

### 2026-03-06 — Session 3
**Done:**
- Completed Phase 2 — all 8 migration tasks done
- Fixed `core/ctx_linker.py`: added try/except guard around `from maya import cmds` (was causing ImportError in non-Maya test environments)
- Fixed `tests/test_node_schemas.py`: updated stale assertions — `ctx_node_type` → `ctx_type`; removed `parentNode` (deleted from gaffer schema); removed `parentGaffer` from LightContext connections (also deleted per unidirectional pattern)
- All schema tests and shot manager tests passing: 39/39

**Remaining pre-existing failure (NOT caused by Phase 2):**
- `tests/test_asset_manager.py` (10 failures) — `tools/asset_manager.py:87` imports `create_standin_with_namespace` from `core.nodes` which doesn't exist; renderer handlers are Phase 3+ work

**Next session should start with:**
- Phase 3: Asset type handlers (Arnold StandIn, Redshift Proxy, USD)
- Or: Fix `test_asset_manager.py` by stubbing or removing the renderer-specific import in `add_asset()`

### 2026-03-07 — Session 8
**Done: Gaffer architecture clarification + bug fixes from Maya testing**

Gaffer architecture confirmed with user (Katana-inspired model):
- Gaffer is optional; no gaffer = original Maya light values
- Child gaffer inherits all lights from parent + can add/override
- Same light cannot be in same gaffer twice; CAN be in parent + child (child = override)
- Gaffer can be shared between multiple shots
- Shot-switch apply order: shot gaffer → sequence gaffer → restore originals

Bug fixes:
- `light_context.py:set_parent_gaffer` — `isinstance(gaffer, CTXLightGafferNode)` fails after module reload (stale class); fixed to `isinstance(gaffer, str)` pattern
- `gaffer.py:set_parent_gaffer` — same fix
- `_on_set_shot` in `main_window.py` — rewrote gaffer-apply block: shot gaffer → seq gaffer → restore originals
- `_on_gaffer_click` in `main_window.py` — when no sequence gaffer, now auto-wires shot gaffer to master gaffer
- `gaffer_manager_dialog.py:_on_commit_edit_mode` — re-applies gaffer to lights after commit so viewport updates immediately
- `MainWindow.__init__` — `_light_original_values` captured on open via `_capture_all_light_originals()`
- Added `_capture_all_light_originals()` and `_restore_light_originals()` to `MainWindow`

### 2026-03-07 — Session 7
**Done: Phase 3 Gaffer — Tasks 1–9 (all UI/schema/engine gaffer work except Edit Mode)**

Tasks 1–6 (earlier in session):
- Task 1: `add_light_dialog.py` — added RedshiftPhysicalLight, RedshiftDomeLight, RedshiftIESLight to filter combo + scan list
- Task 2: `CTXLightContextSchema` — added spread/spreadEnabled, scaleX/Y/Z/scaleEnabled, affectDiffuse/Specular/GI/shadowEnable + their Enabled flags
- Task 3: `core/renderers/` — new package: `__init__.py` (get_maya_attr renderer detection), `redshift.py`, `arnold.py` (attr name maps, note: Arnold uses aiSpread, aiCastShadows, aiDiffuse/Specular/Indirect float multipliers)
- Task 4: `resolver.py` SUPPORTED_ATTRIBUTES + `_get_attribute_value` (scale compound); `light_ops.py` `_apply_attribute_to_light` (spread/contributions/scale, bool→float coercion for Arnold); `manager.py` `capture_light_values` (spread, contributions, scale)
- Task 5: `CTXLightContextNode` wrapper — added get_spread(), get_scale(), get_affect_diffuse/specular/gi(), get_shadow_enable(); updated get_enabled_attributes() with all 6 new groups
- Task 6: `light_editor_panel.py` — fixed addLine→addWidget bug (line 122); added spread to Light Attributes group; added scaleX/Y/Z to Transform group; added new _create_contribution_group() (affectDiffuse/Specular/GI, shadowEnable)

Tasks 7–8 (this session):
- Task 7: `main_window.py` — added column 5 "Gaffer" to shot_table; _add_shot_to_table adds Gaffer button (blue if has gaffer, "+ Gaffer" if not); _on_gaffer_click creates shot gaffer + auto-wires to seq gaffer + opens Gaffer Manager; _open_gaffer_manager_for pre-selects gaffer; _gaffer_manager_dialog tracked as singleton
- Task 8: `gaffer_manager_dialog.py` — added select_gaffer(gaffer) and refresh() methods; `main_window.py` — _on_set_shot refreshes Gaffer Manager dialog on shot switch

Task 9: **Already implemented** — Add Light, Remove Light, Apply, Capture buttons were all wired in gaffer_manager_dialog.py

Task 10 (also this session):
- `core/gaffer/edit_mode.py` — EditMode class: enter() snapshots all lights from Maya; commit() diffs + stores changed attrs as overrides (handles compound groups: color/translate/rotate/scale + simple scalars); cancel() restores snapshot to Maya without storing; FLOAT_THRESHOLD=0.0001 for noise
- `gaffer_manager_dialog.py` — Enter Edit Mode / Commit / Discard buttons; disables gaffer switching during edit; refresh() guards against disrupting active edit

**Phase 3 ALL 10 TASKS DONE. Ready for Maya testing.**

### 2026-03-07 — Session 6
**Done: CTX_Asset per-shot naming, bulk namespace linking, asset manager dialog migration**

CTX_Asset naming redesign:
- Old: `CTX_Asset_CHAR_CatStompie_001` (namespace-based, caused Maya auto-increment collisions)
- New: `CTX_Asset_{assetType}_{assetName}_{shotCode}` e.g. `CTX_Asset_CHAR_CatStompie_SH0140`
- Each shot gets its own CTX_Asset node; all sharing same Maya ref linked via `ReferenceNode.message → CTX_Asset.targetNode`
- `CTXAssetNode.create()` now takes `shot_code=` kwarg (popped before NodeFactory, drives node naming)
- Added `targetNode` to `CTXAssetSchema.CONNECTIONS` so NodeFactory creates it at node creation

Bulk namespace linking:
- `CTXConverter.link_all_by_namespace(namespace)` — canonical bulk-linking method
  1. Finds Maya reference via `cmds.referenceQuery(ref, namespace=True)` attribute-based lookup
  2. Finds all CTX_Asset nodes by querying their `namespace` attribute value
  3. Connects `reference.message → CTX_Asset.targetNode` for ALL of them with `force=True`
- Fixed `referenceQuery` bug in `core/ctx_linker.py`: only call `referenceQuery(referenceNode=True)` when `node_type != 'reference'`
- `asset_scanner.py`: replaced per-node `link_ctx_asset_to_scene` with single `link_all_by_namespace` call
- `CTXManagerNode.get_active_shot_id()` added
- `CTXAssetNode.get_version()` added

Dialog migration — `ui/asset_manager_dialog.py`:
- All `core.custom_nodes` imports replaced with `core.nodes.wrappers`
- `_create_ctx_asset_node()`: uses `CTXShotNode.create(ep_code, seq_code, shot_code)` + `CTXAssetNode.create(..., shot_code=)` + `link_all_by_namespace`
- `_auto_link_if_needed()`: rewrote to use `link_all_by_namespace` via namespace attribute lookup

Tool migration — `tools/asset_manager.py::add_asset()`:
- Replaced `from core.custom_nodes import CTXAssetNode, CTXShotNode` with `core.nodes.wrappers`
- `CTXAssetNode.create_asset()` → `CTXAssetNode.create(..., shot_code=)` + `shot_node_obj.add_asset()`
- `link_to_maya_node()` → `CTXConverter().link_all_by_namespace(namespace)`
- Fixed attribute reads: `.ep`/`.seq`/`.shot` → `get_ep_code()`/`get_seq_code()`/`get_shot_code()`
- Phase 3 renderer imports (standin, proxy) moved to inline deferred imports to avoid failure at function entry

**Known remaining legacy usage:**
- `core/ctx_converter.py::convert_to_ctx()` — still uses `core.custom_nodes` + `create_asset()`, but NOT called from any current dialog/tool path
- `tests/test_asset_manager.py`: 10 pre-existing failures — `create_standin_with_namespace` Phase 3 work

Also fixed in this session: added `get_template()`, `get_extension()`, `get_file_path()` to `CTXAssetNode` wrapper.
These were missing, causing `NodeManager.resolve_asset_path()` to raise `AttributeError` silently swallowed
by `update_shot_paths`, so Set Shot never resolved asset paths.

### 2026-03-07 — Session 5
**Done: Full migration of `launch_multishot_dockable.py` dependency chain to new node system**

Wrapper additions:
- `CTXShotNode`: added `get_frame_range()`, `set_frame_range()`, `set_fps()`, `get_ep_code()`, `get_seq_code()`, `get_shot_code()`, `is_active()`, `set_active()`
- `CTXAssetNode`: added `get_asset_type()`, `get_asset_name()`, `get_variant()`, `get_namespace()`, `get_department()`, `set_department()`, `set_version()`, `set_template()`, `set_extension()`, `set_file_path()`
- `CTXAssetSchema`: added `department` attribute

Core fixes:
- `core/shot_switching.py`: `_deactivate_other_shots()` now scans all network nodes for `ctx_type == 'CTX_Shot'` instead of querying `manager.shots` (which is empty in new Manager→Sequence→Shot hierarchy)
- `core/asset_scanner.py`: migrated from `core.custom_nodes.CTXAssetNode` to `core.nodes.wrappers.CTXAssetNode`; `create_asset()` → `create()` + `shot_node.add_asset()`
- `core/nodes.py`: migrated `CTXAssetNode` imports + creation; replaced legacy `cmds` mock import with inline `_MockCmds`

**Remaining legacy `core.custom_nodes` users (NOT in main launch path):**
- `ui/asset_manager_dialog.py` — separate dialog, Phase 3+
- `tools/asset_manager.py` — not in main path
- `core/ctx_converter.py` — path utility, not in main path
- `core/shader_assignment.py` — just imports `cmds` mock, not a node migration issue
- `core/reference_manager.py` — same, just `cmds` mock

### 2026-03-06 — Session 4
**Done:**
- Fixed `core/nodes/wrappers/shot.py`: added `get_ep_code()`, `get_seq_code()`, `get_shot_code()`, `is_active()`, `set_active()`; fixed `get_assets()` to return `CTXAssetNode` instances; fixed `list_all()` to return `[]` (not raise) when Maya absent
- Fixed `core/nodes/wrappers/manager.py`: fixed `get_sequences()`/`get_shots()` to return wrapper instances; added `set_active_shot_id()`, `set_config_path()`; fixed `get_manager()` to return `None` (not raise) when Maya absent
- Fixed `core/nodes/wrappers/sequence.py`: fixed `get_parent_manager()` bug (`ctx_node_type` → `ctx_type`); fixed `get_shots()` to return `CTXShotNode` instances
- Migrated `core/context.py`: replaced `core.custom_nodes` import with `core.nodes.wrappers`; `create_manager()` → `create()`; added `_get_or_create_sequence()` helper; rewrote `create_shot()` for `Manager → Sequence → Shot` hierarchy; `get_all_shots()` now uses `CTXShotNode.list_all()`
- Added `MAYA_AVAILABLE` to `core/nodes/wrappers/__init__.py`
- Updated `tests/test_context.py`: imports from `core.nodes.wrappers`; Maya-requiring tests decorated with `@unittest.skipUnless(MAYA_AVAILABLE, "Requires Maya")`
- Result: 30 passed, 9 skipped (correctly skip without Maya), 0 failed

### 2026-03-05 — Session 1
**Done:**
- Reviewed entire project architecture and code
- Created `CLAUDE.md` (project root) — AI agent quick reference
- Created `.claude/memory.md` (this file) — session persistence

---

## Quick Command Reference

```bash
# Run tests
pytest tests/ -v
pytest --cov=core --cov-report=html tests/

# Git
git checkout feature/ui-tools-framework
git status
git log --oneline -10
```

```python
# Maya: Launch main UI
exec(open(r'E:/dev/maya-multishot/launch_multishot_dockable.py').read())

# Create nodes (correct pattern)
from core.nodes.wrappers import CTXManagerNode, CTXSequenceNode, CTXShotNode
manager = CTXManagerNode.create(projectName='MyProject')
seq = CTXSequenceNode.create(sequenceCode='sq0070')
shot = CTXShotNode.create(ep='Ep04', seq='sq0070', shot='SH0170')
manager.add_sequence(seq)
seq.add_shot(shot)
```
