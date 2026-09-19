# Project Memory — Maya Multishot Pipeline

> AI agent session log. Update this file at the end of every work session.
> Format: newest entries first. Keep entries concise.

---

## Project Identity

- **Name:** Maya Multishot Pipeline
- **Repo:** https://github.com/katha-begin/maya-multishot.git
- **Purpose:** Multi-shot context management for Maya artists (no scene open/close cycling)
- **Stack:** Python 2.7 and 3.x (Maya 2019+, incl. Maya 2022 in Python 2 mode), PySide2/PySide6, Maya cmds API, custom network nodes

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

## CFX Asset Type (2026-08-27) -- branch `feature/cfx-asset-type`

New asset type: Arnold `.ass` **frame sequence**, published as a DIRECTORY.
Design doc: `docs/superpowers/specs/2026-08-27-cfx-asset-type-design.md`

Path shape (project EGA, root `X:/`):
```
{proj}/all/scene/{ep}/{seq}/{shot}/cfx/publish/{ver}/
  {ep}_{seq}_{shot}__CFX_{name}{variant}_ass/          <- directory
    {ep}_{seq}_{shot}__CFX_{name}{variant}.####.ass    <- frame files
```

### Key decisions (do not revert)
- **`core/asset_types.py` is the single source of truth** for per-type naming:
  `parse_asset_part`, `publish_shape`, `namespace_for`. CAM was folded into it,
  removing the old scattered `if asset_type == 'CAM'` branches. Register any new
  type HERE, not in scanner/dialog/reconciler.
- CFX variant has **no underscore separator**: `CFX_botgroomSamS001` ->
  name=`botgroomSamS`, variant=`001`. Pattern is config-driven (`\d{3}$`).
  Known risk: a name ending in digits mis-splits (`bot2000` -> `bot2`+`000`).
- **CFX namespace = full publish basename** (carries the shot code). Must be
  shot-unique because `switch_shot_layers` keys on namespace as a GLOBAL
  identity across all shots.
- **CFX is static-path**: `.dso` set once at import; shot switch only moves
  display layers. All shots' CFX coexist under one global `Cfx_Grp`.
- Node structure is THREE levels:
  `{basename}` / `{basename}_aiStandIn` / `{basename}_aiStandInShape`.
  `CTX_Asset.targetNode` -> the SHAPE; display layers use the TOP transform.
- Templates `assetSeqDir` / `assetSeqPath` use ONLY tokens Pipeline B injects
  (`core/nodes.py:329-334`). An unknown token is only WARNED about, producing a
  silently broken path -- never add a token Pipeline B does not supply.
- Adopt is non-destructive: never renames, never re-namespaces, never touches
  dso/frameNumber. Migration is opt-in only (no undo exists in this repo).

### Bugs fixed along the way
- `core/nodes/__init__.py` shadows `core/nodes.py` and did NOT re-export the
  creation helpers -> Asset Manager "Create StandIn"/"Create Proxy" raised
  ImportError at click time. Anything reachable via `from core.nodes import X`
  MUST be re-exported there.
- `_create_ctx_asset_node` + `_check_asset_in_scene` each rebuilt the namespace
  as `TYPE_Name_Var` (drift). Now both call `self._asset_namespace()`.
- Asset Manager has its OWN version scan separate from `AssetScanner`; it also
  skipped directories.
- `AssetPathExistsCheck` used `os.path.exists()` on a `####` path (never exists).
- Scanner's `.replace('\\','/')` matched a literal double backslash; fixed.

### Gotchas discovered
- **`.gitignore` ignores `tests/` wholesale** but 31 test files are tracked.
  New tests MUST be added with `git add -f` or they vanish silently.
- `tests/test_qt_compatibility.py` CRASHES python (0xC0000409) headless --
  exclude it alongside the other three known exclusions.
- Test baseline: **51 failures on main** are pre-existing (asset_manager,
  display_layers, nodes, logging_config, shot_switching, pipeline_api).
  Branch: 792 passed / 51 failed, failure set IDENTICAL to main.

### Open / next
- `frameNumber` driver unconfirmed (AE shows it driven). Implemented as
  `time1.outTime -> frameNumber` behind config `cfx.frameDriver`.
- Standin suffix casing `_aiStandIn` vs `_aiStandin` -- config `cfx.standinSuffix`.
- No live Maya testing yet for import / adopt / shot switch.
- EGA project config not created (templates live in the SWA config; they are
  project-agnostic).

## Multi-project config (2026-08-28) -- same branch `feature/cfx-asset-type`

Was: ONE config (`ctx_config.json`) with SWA + `V:/` baked in, and FOUR loaders
that disagreed. Now: base + per-project overlay, one resolution order.

```
project_configs/
  base.json        shared: templates, patterns, tokens, gafferAttributes,
                   batchRender, slateManager, assetTypePolicies, cfx
  SWA.json         {"extends":"base.json"} + project + roots
  EGA.json         {"extends":"base.json"} + project + roots   <- values are TODO
  ctx_config.json  {"extends":"SWA.json"}  <- default pointer; NOT a copy
```

- `ProjectConfig` understands `"extends"` (relative to the file's own dir).
  `deep_merge`: **dicts recurse, lists REPLACE**. Validation runs on the MERGED
  result, so an overlay declares only what it changes. No `extends` key ->
  loads exactly as before (full back-compat).
- `config/config_resolver.resolve_config_path()` is THE way to find a config:
  `explicit > CTX_Manager.config_path > SCENE LOCATION > $CTX_CONFIG > default`.
  Use `use_scene=False` at Maya startup (no scene open yet).
- **Scene-location detection**: `detect_config_from_scene()` matches the open
  scene against each config's `projRoot + project + sceneBase` prefix (longest
  wins; case-insensitive on Windows). `X:/EGA/all/scene/...` -> EGA. This works
  because every shot path comes from `$projRoot$project/$sceneBase/...`.
  It sits ABOVE `$CTX_CONFIG` on purpose: env is per-session, the scene is the
  specific thing being worked on.
- **UI picker**: Multishot Manager `Tools > Project Config...` lists projects
  with roots, marks active + detected, and offers `Browse...` (opens at the
  scene's directory). Selection is stored on `CTX_Manager.config_path` and
  triggers a shot reload.
- `ctx_config.json` merged == old file exactly (verified), except a repaired
  mojibake em dash in `deptPriority.description`.

### Do not revert
- `main_window._load_config` stamps `CTX_Manager.config_path` ONLY when unset
  or missing. Unconditional stamping rebinds an EGA scene to SWA.
- `_reload_config_for_scene()` runs on kAfterOpen/kAfterNew BEFORE shots load.
  Without it a second scene from another project resolves against stale roots.
- A nonexistent `$CTX_CONFIG` is honoured, NOT ignored -- a typo must fail
  loudly rather than silently load another project's roots. (Two pipeline_api
  tests encode this; they were right and my first cut was wrong.)
- Env var comes BEFORE the repo path in `_get_default_search_paths`;
  `find_config()` returns the first hit, so the old order made it dead code.

### Still TODO for EGA
`project_configs/EGA.json` has a `_todo` key listing the unknowns: dept list +
deptPriority, assetType list, renderer. Confirmed by the user (2026-09-15):
code `EGA`, `projRoot` `X:/`, render output `imgRoot` `Y:/`, and the Linux
mount convention `/mnt/{client}_{project}_{winDrive}/` -> `/mnt/igloo_ega_x/`,
`/mnt/igloo_ega_y/`.
`tokens.assetType.values` currently holds the union (incl. CFX) in base --
split per project once the real lists are known.

## Install anywhere + Python 2.7 runtime (2026-09-10) -- same branch `feature/cfx-asset-type`

Trigger: studio Maya 2022 in Python 2 mode, repo copied to
`X:\EGA\_temp\rich\script\maya-multishot`, raised "cannot import name
get_maya_attr". Cause: that copy mixed versions (tools/maya_menu.py from
a127e53, core/gaffer from >= 885169c), and Reload on Python 2 never reloaded
anything (`importlib.reload` does not exist on 2.7). HEAD itself imports
cleanly under mayapy2 and mayapy -- but RUNNING code on 2.7 exposed much more.

- `ctx_bootstrap.py` (repo root): find this checkout, purge its modules BY FILE
  LOCATION (plus any older CTX checkout already loaded), clear __pycache__ and
  orphaned .pyc, run launchers with their own `__file__`.
- Launchers: no `E:/dev` fallback; find the repo from their own folder or
  sys.path and put it first. The menu runs them via `ctx_bootstrap.run_script()`.
- Menu Reload / `reload_all_modules()` / main window "Reload All Tools" purge
  instead of `importlib.reload`.
- `core/compat.py`: `string_types` (47 `isinstance(x, str)` checks -- on 2.7
  maya.cmds/Qt/json return unicode, so gaffer/slate calls and even config
  template loading failed), `makedirs`, `is_main_thread`.
- Batch: thread `daemon` as attribute; nvidia-smi via Popen + timer kill;
  `str()` GPU env var name for Popen; Render.exe from `MAYA_LOCATION` first.
- `core/nodes/__init__.py` no longer puts `core/` on sys.path.

Verified: maya.standalone smoke under mayapy2 -- HEAD fails 8 of 10 runtime
checks, new code passes 10/10 (also 10/10 under mayapy 3.7); launchers from a
copied install in 6 modes x 2 interpreters; test suite has no regressions vs
HEAD (all remaining failures pre-exist on HEAD).

Open: if a studio tool imports its own top-level `core`/`ui`/`tools`/`config`
before ours, our packages still need a unique namespace. Confirm first by
printing `sys.modules['core'].__file__` in the failing session.

## Regression review + frame range JSON (2026-09-15) -- on `main`

Review of old main 2d15856 vs 638dc79 (CFX + multi-project + py2) found no
change to SWA workflows (test suite per-test diff: 0 regressions; maya.standalone
smoke of scan / CTX_Asset / display layers / gaffer / validator identical), but
four real issues, now fixed:

1. Batch/Quick Render built `PipelineAPI()` inside the render thread; its
   `__init__` now calls maya.cmds via `resolve_config_path()`. Built on the main
   thread in `BatchRenderDialog._create_pipeline_api()`.
2. Old Multishot Manager stamped `ctx_config.json` on EVERY scene, so EGA scenes
   touched by it stayed bound to SWA. `config_resolver.is_default_binding()`:
   detection beats a ctx_config.json binding; `_load_config` restamps it.
3. `CAM_<name>_<var>` publishes stopped parsing -> fall back to standard split.
4. Scene open/new with the window open created CTX_Manager ->
   `_load_config(create_manager=False)` on reload.

Feature: Edit Frame Range (single + multi) checkbox "Save frame range to shot
JSON" (default on, only when shotMetadata.enabled). User decisions: existing
JSON -> update ONLY start/end frame (keep fps + all other keys); missing JSON ->
create in the config format (frame range + fps); write on OK/Apply.
`ShotMetadataLoader.save_frame_range()` writes the inverse of
`load_frame_range()` per parseFormat; never creates the shot folder, never
overwrites unparseable JSON. Tests: `tests/test_shot_metadata_writer.py`
(plain unittest, passes under mayapy2).

Testing notes: the user's Maya `userSetup.py` loads CTX tools from E:/dev during
`maya.standalone.initialize()` -- set `MAYA_SKIP_USERSETUP_PY=1` or a "baseline"
run silently imports the dev checkout. Headless Maya crashes creating Qt widgets:
test dialogs in mayapy WITHOUT standalone (PySide + stand-in shot node).

## Add Shots empty on the studio deploy (2026-09-15) -- fixed, not yet pushed at time of writing

Report: Multishot Manager on the EC2 deploy (`T:\pipeline\development\maya\maya-multishot`
= `/mnt/ppr_dev_t/pipeline/development/maya/maya-multishot`, a git checkout pulled
from origin main) showed
"Failed to load config" and an empty Add Shots tree. User expects SWA AND EGA listed.

Evidence: deploy reflog -- pulled 2d15856 at 05:02 UTC, scene saved 05:56 (stamped
ctx_config.json), pulled 033d762 at 06:19 while Maya stayed open. The 2d15856 Reload
(menu `reload_all_modules` and window "Reload All Tools") only reloads core/ui/tools/utils,
never `config`, so the new ui ran with the OLD ProjectConfig, which rejects "extends"
configs ("Missing required keys ..."). `_load_config` swallowed it -> `_config` None ->
AddShotDialog returned silently. HEAD code with the real scene loads EGA fine
(reproduced in mayapy 2 and 3). Share mounts on EC2: /mnt/igloo_swa_v, _swa_w,
_ega_x, _ega_y, /mnt/ppr_dev_t. Real counts: EGA 611 shots, SWA 342.

Fix: Add Shots lists every project (core/shot_discovery.py), explains missing
projects, one project per scene guard, `_load_config` shows the reason + "restart
Maya" hint for stale config code. Users who update while Maya is open must restart
Maya once (old Reload cannot pick up the config package). Pushed as 46a8c69.

## Set Shot runs out of memory; Script Editor floods (2026-09-15)

Reports after 46a8c69: "print a lot ... and crash", "a lot slower", "eat all memory
and crash when set shot".

Root cause (reproduced in mayapy 2 + 3): `NodeManager._apply_path_to_maya_node`
did `cmds.file(path, loadReference=RN)` for every referenced asset on EVERY shot
switch; Maya reloads even when the path is unchanged (kAfterLoadReference fires).
In the morning EGA scenes resolved to non-existent V:/SWA paths, so the call
failed; with the EGA config the paths resolve, so every Set Shot re-read every EGA
Alembic cache. Second finding: a non-existent path leaves the reference UNLOADED and
repointed. Also: display-layer targetNode fallback walked referenceQuery(nodes=True)
over whole references; Add Shots printed ~2,900 lines per open (morning ~1,000);
display_layers logged ~25 INFO lines per asset per switch; MGlobal was called from
batch job threads.

Fix (not yet pushed at time of writing): `_swap_reference` skips unchanged / missing
paths; layer fallback uses the reference's namespace; logging demoted to DEBUG and UI
prints removed (Add Shots open: 0 lines, 0.06s vs 0.53s); Maya log handler defers
off-main-thread records. Tests: tests/test_reference_swap.py,
tests/test_maya_log_handler_threads.py (plain unittest, pass under mayapy2).
Not verified: a real EGA scene with its caches loaded (X: not reachable here).

Follow-up the same day on the deployed 46a8c69: Add Shots flooded the Script Editor
with `AttributeError: ... Qt has no attribute 'Transparent'` (old bug in
`_on_item_changed`; 46a8c69 made it fire for every shot while building the tree) plus
the per-shot debug prints. User asked for Add Shots to list only a selected project:
added a Project combo (scene's project selected, one project scanned at a time).
Offscreen check under mayapy 2 + 3: 10/10.

## 2026-09-19 -- SWA shot assets resolved no path (asset reconciler records)

Reported: "the last update broke SWA -- setting an asset shot in the Context
Manager does not resolve the path to the shot asset". Scene dump from the artist
showed every CTX_Asset except the ones for the ACTIVE shot carried a template;
the active shot's two (`CTX_Asset_CAM_SWA_Ep20_SH0130_camera_SH0030`,
`CTX_Asset_CHAR_Ajay_001_SH0030`) had `template: None`.

Root cause: `core/asset_reconciler.py` creates records with
`CTXAssetNode.create(type/name/variant/shot/namespace)` and nothing else -- no
template, department, version or extension. `NodeManager.resolve_asset_path`
starts from the record's template and returns None without one ("No template on
..." then "Could not resolve path for ..."). d3d6bf8 made `_get_shot_code` read
`shot_code`, so reconcile stopped skipping schema-based shots and started
creating these template-less records on SWA scenes -- the regression.

Two more bugs in the same file: its own `_parse_namespace` split on `_` and took
the last part as the variant, so the shader namespace `CHAR_Ajay_001_Shade`
(config `namespaceShader`) became an asset named `Ajay_001` variant `Shade`; and
every reference was adopted into the active shot, including another shot's
camera, whose publish filename repeats its own shot code and can never resolve.

Fix: `asset_types.get_asset_path_template()` (shared with `asset_scanner`, keeps
the camera form `$ep_$seq_$shot__$assetName.$ext`); the reconciler fills
template/department/version/extension on create AND on existing records missing
them (repair of already-saved scenes, counted as `repaired` in the stats),
reads department/version/extension from the reference's publish path, parses
namespaces through `core.asset_types`, skips `_Shade`/`_Groom` namespaces and
references naming another shot. `reconcile_assets_for_shot(shot_node,
config=None)` -- callers in `tools/pipeline_api.py` and
`ui/asset_manager_dialog.py` pass their config.

Tests: `tests/test_asset_reconciler.py::TestReconciledRecordFields` (5, written
first and failing). Suite: 163 passed; the 8 `tests/test_asset_manager.py`
failures are pre-existing (same set with the change stashed). Not verified in
Maya: no Maya here.

## 2026-09-19 -- active shot's camera was hidden (CTX_Inactive)

Reported alongside the asset-path fix: "active and inactive is broken". Scene
probe: `CTX_Inactive` held `CAM_SWA_Ep20_SH0080_camera_001:cam` while SH0080
was the active shot, plus five `CHAR_*_001_Shade:Place3dTexture_Grp`.

Root cause: one camera reference serves the whole scene
(`SWA_Ep20_SH0060_cameraRN`, repathed per shot) and EVERY shot's camera record
targetNodes to it. `switch_shot_layers` subtracts NAMESPACES (inactive = all -
active), but an inactive shot's camera namespace does not exist in Maya, so
`_resolve_top_node` falls back to targetNode and returns the one camera the
active shot is using. Step 5 runs after step 4, so the active shot's camera was
connected to CTX_Inactive last and disappeared.

Fix: step 4 collects the nodes it made active; step 5 skips any node already in
that set (counted as `shared_with_active`). Namespace subtraction alone cannot
see that several records resolve to one node.
Tests: `tests/test_shot_layer_switch.py` (4, written first; 3 failed before).

Still open (user is testing before we touch it): Set Shot not repointing assets
to the new shot, and the bogus records the old reconciler left in SWA scenes --
shader namespaces (`CHAR_Ajay_001_Shade`) and another shot's camera
(`CTX_Asset_CAM_SWA_Ep20_SH0130_camera_SH0030`). 46f16ff stops new ones being
created; nothing deletes the existing ones yet.

## 2026-09-19 (later) -- records must describe a publish the shot has

Set Shot on SWA Ep20/sq0010/SH0050 resolved 5 of 31 assets. SH0050's publish
holds one version (v002) with 6 assets, but its CTX_Shot claimed 31: the
reconciler adopts EVERY reference in the scene into whichever shot is set, so
each shot claimed assets it never published (SH0030 had 60). Two symptoms in
the log, both from those records: "... does not exist" (CHAR_Ajay, CHAR_Kit,
PROP_BoardGame -- no SH0050 publish; the stored $ver came from another shot,
SDRS_TRLRWallB even asked v001 while the rest asked v002) and "Unexpanded
tokens: dept, ver" (references nested inside the SETS assembly, which are not
shot publishes at all and had no dept/version).

Fix: `AssetScanner.discover_shot_assets(ep, seq, shot)` -- pass 1 of
`scan_shot_assets`, extracted -- is now what the reconciler consults. A
reference only gets a record when the shot published that identity, and the
record takes the shot's own dept/version/ext from that publish (no longer
guessed from the reference's current path). `_names_other_shot` and the
publish-path parsing are gone; the publish lookup subsumes them.
Tests: TestReconciledRecordFields (7); the wiring tests stub `_shot_publishes`
with AnyPublishes. 181 passed across the reconciler/layer/cfx/config suites.

Note: existing scenes still carry the adopted records (SH0050 has 25 of them),
so the errors persist there until something removes them -- cleanup not written
yet, and it should report before deleting.

## 2026-09-19 (later) -- Repair Scene Records

Scenes built before the publish check carry records the old reconciler adopted
from any reference in the scene. SH0050 held 25 of them (the shot publishes 6
assets); they log "does not exist" or "Unexpanded tokens: dept, ver" on every
shot switch, and the ~23 `SDRS_*_Shade` records log "No top node found".
Nothing removed them, so the scene stayed broken after the code fix.

`core/asset_reconciler`:
- `find_stale_records(shot_node, config=None)` -- records wired to a shot whose
  namespace is not an asset namespace (shader/groom, set pieces) or whose
  identity is not in the shot's publishes. Reports nothing when the publish
  scan came back empty, so a failed scan never condemns a scene.
- `remove_records(nodes)`, `repair_scene_records(config=None, remove_stale=False)`
  -- reconciles every CTX_Shot (adding the records its publishes need, filling
  template/dept/version on older ones) and reports the stale ones.
CTX Tools -> "Repair Scene Records..." (`tools/maya_menu.open_record_repair`)
runs it, lists what it found and deletes only on confirmation.

Display layers confirmed correct in Maya afterwards: CTX_Active holds
SETS_ToriiLivingRoomInt_001:Main_Grp (the whole set follows that one member --
every piece is under it) plus the SDRS Geo_Grps the shot published. SH0070 now
resolves 6/7 assets, against 5/31 on SH0050 before.

Still open: `No Maya node linked to CTX_Asset_SETS_..._SH0070`. A SETS cache is
imported, not referenced (5aed186: import_sets_asset creates one CTX_Asset per
SETS abc), and update_shot_paths only repaths references, aiStandIns and
Redshift proxies -- so a set does not follow the shot. Long-standing, not from
these changes.
