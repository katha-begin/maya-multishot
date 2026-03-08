# Production Readiness Analysis — Maya Multishot Pipeline

> Written: 2026-03-08
> Scope: Full codebase review following Phase 3 Gaffer System completion.
> Purpose: Decision document for next development priorities before mass-production deployment.

---

## Executive Summary

The core system is **production-capable for interactive use within a Maya session**. The architecture is sound, the gaffer inheritance model is well-designed, and the path resolver is solid. The gaps are not in correctness — they are in **automation reach**: the tool cannot currently be driven headlessly by a farm, a production tracker, or a TD automation script without significant boilerplate.

The P1 recommendations below are what separate this from being a **studio pipeline component** that runs reliably at scale.

---

## Strengths

### 1. Architecture is fundamentally sound

The schema → wrapper → unidirectional-connection pattern is the right model for Maya network nodes. It is predictable, queryable in either direction from a single connection, and survives scene saves and merges cleanly. This design avoids the most common failure modes in Maya studio pipelines (bidirectional connections, string attributes, `objExists` loops).

### 2. Gaffer inheritance model is elegant

The chain walk with per-attribute enable flags is the correct mental model for a non-destructive lighting override system. The distinction between `replace` and `additive` modes gives TDs precise control without hard-coding assumptions about light type. The snapshot/diff `EditMode` is clean — it captures artist intent from any editing surface (viewport, panel, table) uniformly without requiring real-time callbacks.

### 3. Renderer abstraction via `get_maya_attr()`

Centralizing renderer detection and attribute name mapping in `core/renderers/` keeps the gaffer, manager, and ops layer fully renderer-agnostic. Adding a new renderer requires one new file and one mapping dict — nothing else changes.

### 4. Cross-platform path resolution

The token-based resolver with named templates is production-safe. Artists and TDs call template names, never write raw paths. Auto-injected `projRoot`/`imgRoot` tokens handle Windows ↔ Linux transparently.

### 5. Maya-free testing

The `MockCmds` + `MAYA_AVAILABLE` guard pattern means business logic can be tested in CI without a Maya license. Thirty-plus test files covering core, gaffer, resolver, and integration is a real asset for a studio tool.

### 6. Clean error handling at the right boundaries

Custom exceptions (`TemplateNotFoundError`, `TokenExpansionError`) at the path layer, graceful degradation in the gaffer layer, and explicit `RuntimeError` when Maya is unavailable — the system fails loudly at the correct level.

---

## Weaknesses

### Critical for Mass Production

---

#### W1 — No headless / batch Python API

**Impact: P1**

Everything works through the UI or by constructing wrappers manually inside a Maya session. There is no single-entry-point function that a farm render script, a pre-render hook, or a TD automation script can call in one line. Every batch operation requires the caller to know internal wrapper classes, import chains, and the shot-switch apply order.

A `pipeline/api.py` facade does not require rewriting anything — it is a thin layer over existing code. Without it, every TD who wants to automate something must read the full codebase first.

---

#### W2 — No farm submission integration

**Impact: P1**

`PathResolver` can build all render output paths. Nothing translates a shot's resolved paths into a render farm job (Deadline, Tractor, Qube). The path layer is complete; the submission bridge is absent. Lighting TDs currently submit renders by hand, which does not scale past a handful of shots.

---

#### W3 — Gaffer attributes are hardcoded in Python

**Impact: P1**

The 13 tracked attributes (`SIMPLE_ATTRS`, `COMPOUND_GROUPS` in `edit_mode.py`) are fixed constants. A TD wanting to add `aiExposure`, `rsTemperature`, or any renderer-specific parameter must modify `edit_mode.py`, `light_editor_panel.py`, and the `CTXLightContextSchema` — three separate files. There is no configuration-driven way to extend the attribute set. At a studio level, different shows have different light attribute needs.

---

#### W4 — No gaffer export / import

**Impact: P1**

Gaffer state lives exclusively in Maya network nodes inside a specific scene file. There is no way to:

- Export a gaffer setup to JSON and import it into another Maya scene
- Share a master gaffer configuration between episodes or between shows
- Version-control lighting override data independently of the Maya scene
- Apply a studio lighting template from a shared library at shot-build time

In production, lighting setups are often established once per sequence and then propagated. Without export/import, every new scene starts from scratch.

---

#### W5 — No scene validation / health check

**Impact: P1**

No tool audits whether a scene is in a valid state. Problems that occur silently in production:

- `targetLight` connections pointing to deleted lights
- CTX nodes with no corresponding Maya reference
- Shots not wired to a sequence
- Sequences not wired to the manager
- Duplicate shot codes in the same scene
- `CTXLightOriginalsNode` missing or empty

In a long-running production, scenes accumulate drift. Without a validator, problems are discovered at render time when fixing them is most expensive.

---

#### W6 — No undo/redo integration

**Impact: P1**

The gaffer edit system bypasses Maya's undo stack entirely. `EditMode.cancel()` does a manual restore, but if the dialog is closed without cancelling, if Maya crashes mid-edit, or if an artist presses Ctrl+Z expecting to undo a gaffer operation, the scene is left in an undefined state. No `cmds.undoInfo(openChunk/closeChunk)` wrapping exists on any gaffer operation.

---

#### W7 — Production tracker not connected

**Impact: P1**

`shot_metadata_loader.py` reads shot data from a local JSON file. There is no integration with ShotGrid (Flow Production Tracking), FTrack, or any production database. Shot frame ranges, statuses, and assignments must be entered manually. At scale, this means:

- Shot creation cannot be automated from approved breakdowns
- Frame range changes made in the tracker do not propagate to the tool
- Shot status (approved, needs revision, locked) cannot be read or written back

---

### Significant Gaps

---

#### W8 — Asset scanner has no incremental update

**Impact: P2**

`AssetScanner` performs a full filesystem rescan every time it runs. For a production with hundreds of shots and thousands of assets, this blocks the UI. There is no dirty-flag mechanism, no filesystem-watch-based cache invalidation, and no partial update. In practice, artists avoid using it frequently because of the wait time.

---

#### W9 — Limited renderer coverage

**Impact: P2**

| Renderer | Support Level |
|---|---|
| Redshift | Solid (intensity, exposure, color, spread, contributions) |
| Arnold | Solid (intensity, exposure, color, aiSpread, float multipliers) |
| VRay | None |
| Karma / Hydra | None |
| Maya Software/Hardware | Partial (fallback, limited attributes) |
| USD light prims | Not considered |

VRay is common in TV animation and commercial work. Its absence is a hard blocker for some studios.

Additionally: Arnold contribution multipliers are floats (0.0–1.0), but the gaffer schema stores them as bools. This type mismatch does not crash at write time but produces incorrect values on apply.

---

#### W10 — No shot status / workflow states

**Impact: P2**

`CTXShotNode.is_active` is a boolean toggle, not a workflow state. There is no `locked`, `approved`, `needs-revision`, or `rendering` state. In production, lighting TDs need to know which shots are approved (should not be re-rendered) and which are in progress. Without this, the tool has no way to protect approved shots from accidental re-submission.

---

#### W11 — No multi-scene coordination

**Impact: P2**

If two artists open the same Maya scene (or a scene that references another), there is no locking or merge strategy for gaffer data. Maya network nodes are not diffable or mergeable via standard git tooling. A studio workflow where multiple TDs work on the same gaffer chain simultaneously has no safeguard.

---

#### W12 — `ctx_converter.py` still uses deprecated `custom_nodes`

**Impact: P2**

`core/ctx_converter.py::convert_to_ctx()` imports from `core.custom_nodes`, which is frozen for backward compatibility. This function is not currently in the active launch path, but if it is ever called, it creates nodes using the old system. Mixed node types in a single scene cause silent query failures. This should be migrated before Phase 3 is declared complete.

---

#### W13 — No progress reporting for long operations

**Impact: P2**

Batch operations (adding many lights, scanning assets, applying a gaffer chain across many shots) block the Qt event loop with no feedback. There is no `QProgressDialog`, no background thread worker, and no cancellable operation. In a scene with 50+ lights, the UI appears frozen.

---

#### W14 — `CTXLightOriginalsNode` is a single point of failure

**Impact: P2**

Original light values (the pre-gaffer baseline) are stored in a single Maya network node. If an artist deletes it during scene cleanup, the baseline is permanently gone. `restore_light_originals()` will silently have nothing to restore, and the shot-switch "no gaffer" path will apply no values. There is no way to reconstruct it from scene data after the fact.

---

### Technical Debt / Minor

---

#### W15 — No CI pipeline

**Impact: P3**

Tests run locally via `pytest`. There is no GitHub Actions or GitLab CI configuration to run the test suite on every push. Regressions can be introduced and not discovered until the next developer runs tests manually.

---

#### W16 — Orphaned UI files

**Impact: P3**

Five files in `ui/` are superseded but not removed:

- `ui/shot_widget.py` — superseded by main_window table
- `ui/asset_widget.py` — superseded by asset_manager_dialog
- `ui/filesystem_discovery.py` — absorbed by asset_scanner
- `ui/import_asset_dialog.py` — merged into asset_manager_dialog
- `ui/convert_scene_dialog.py` — no active caller

These add noise for anyone reading the codebase and are not tested.

---

#### W17 — Gaffer sharing has no UI visibility

**Impact: P3**

A gaffer can be shared between multiple shots, but there is no UI that shows which shots share a given gaffer. Artists cannot know whether editing a gaffer affects other shots until they look at each shot individually.

---

#### W18 — No structured logging

**Impact: P3**

`print()` statements are used throughout all modules for diagnostics (`print("EditMode.enter: ...")`). At production scale these produce unfiltered noise in the Script Editor. There is no way for a TD to set verbosity, redirect output to a log file, or filter by module. A `logging.getLogger(__name__)` refactor across ~15 files would fix this cleanly.

---

## Recommendations

Ordered by impact-to-effort ratio.

---

### R1 — Thin Pipeline API layer

**Priority: P1 | Effort: Low**

Create `pipeline/api.py` — a single-entry-point module that wraps the entire system into flat, easy-to-call functions. TDs and farm scripts call this; they do not need to know about wrappers or connection patterns.

```python
from pipeline.api import apply_shot, build_shot, resolve_path, validate_scene

# Switch active shot and apply its gaffer chain
apply_shot('Ep04', 'sq0070', 'SH0170')

# Create a new shot from scratch, wire to production hierarchy
build_shot('Ep04', 'sq0070', 'SH0170', config='lighting')

# Resolve a path without creating any nodes
resolve_path('publishPath', ep='Ep04', seq='sq0070', shot='SH0170', dept='lighting')

# Check scene health, return structured report
report = validate_scene()
```

This is a facade over existing code. No rewriting required.

---

### R2 — Scene validator

**Priority: P1 | Effort: Low**

Create `tools/scene_validator.py` with `SceneValidator.validate_scene()` returning a structured report:

```python
{
  'broken_target_lights': ['CTX_LightCtx_Master_key'],
  'shots_without_gaffer': ['SH0190', 'SH0200'],
  'orphaned_ctx_nodes': ['CTX_Shot_Ep04_sq0070_SH0170'],
  'duplicate_shot_codes': ['SH0170'],
  'missing_sequences': ['sq0080'],
  'originals_node_missing': True,
}
```

- Add a "Validate Scene" button to the main window
- Run automatically before any batch gaffer apply
- Log all findings via structured logging (see R6)

This would have caught the `targetLight` inconsistency bug during development automatically.

---

### R3 — Gaffer export / import (JSON)

**Priority: P1 | Effort: Medium**

Add `GafferManager.export_to_dict(gaffer)` and `GafferManager.import_from_dict(data, gaffer)`.

Export format:

```json
{
  "gaffer_name": "Master",
  "gaffer_type": "master",
  "exported": "2026-03-08T14:30:00",
  "lights": [
    {
      "name": "rsPhysicalLight1",
      "overrides": {
        "intensity": {"value": 3.5, "enabled": true, "mode": "replace"},
        "color": {"R": 1.0, "G": 0.9, "B": 0.8, "enabled": true, "mode": "replace"},
        "translate": {"X": 0.0, "Y": 200.0, "Z": 0.0, "enabled": true, "mode": "additive"}
      }
    }
  ]
}
```

This enables:
- Gaffer presets shared as files across scenes and shows
- Lighting setups version-controlled in git alongside the scene
- Farm-side gaffer application without opening Maya interactively
- Rollback to a previous gaffer state by re-importing a saved JSON

---

### R4 — Production tracker connector

**Priority: P1 | Effort: High**

Add `pipeline/tracker.py` with a `TrackerConnector` abstract base and a `ShotGridConnector` concrete implementation.

```python
class TrackerConnector:
    def get_shots(self, ep, seq) -> list[dict]: ...
    def get_shot_metadata(self, shot_code) -> dict: ...  # frame range, status, assignments
    def set_shot_status(self, shot_code, status: str) -> None: ...

class ShotGridConnector(TrackerConnector):
    # Uses shotgun_api3 (already a studio standard)
```

Wire into `ShotManager.create_shots_from_tracker(ep, seq)` for bulk shot creation from live production data. Wire shot status back so the tool can mark shots as "rendering" when submitted and "done" when the farm reports completion.

---

### R5 — Undo/redo integration

**Priority: P1 | Effort: Low**

Wrap all destructive gaffer operations in Maya undo chunks:

```python
cmds.undoInfo(openChunk=True, chunkName='CTX Gaffer: Commit Edit Mode')
try:
    # ... all setAttr calls in EditMode.commit() ...
finally:
    cmds.undoInfo(closeChunk=True)
```

The four entry points that need wrapping:

| Method | Chunk Name |
|---|---|
| `EditMode.commit()` | `CTX Gaffer: Commit Edit Mode` |
| `EditMode.cancel()` | `CTX Gaffer: Cancel Edit Mode` |
| `GafferManager.add_light_to_gaffer()` | `CTX Gaffer: Add Light` |
| `GafferManager.remove_light_from_gaffer()` | `CTX Gaffer: Remove Light` |

Artists expect Ctrl+Z to work on every operation in Maya. This is a one-day change.

---

### R6 — Replace print statements with structured logging

**Priority: P2 | Effort: Low**

Replace all `print(...)` diagnostic output with Python's `logging` module:

```python
import logging
logger = logging.getLogger(__name__)

# Before:
print("EditMode.enter: found {} lights in gaffer '{}'".format(len(lights), name))

# After:
logger.debug("enter: found %d lights in gaffer '%s'", len(lights), name)
```

Add `pipeline/logging_config.py` that reads a `CTX_LOG_LEVEL` environment variable and configures handlers once at startup. TDs can then do:

```bash
CTX_LOG_LEVEL=DEBUG mayapy launch_multishot_dockable.py 2>&1 | tee render.log
```

This is a mechanical refactor across approximately 15 files.

---

### R7 — Configurable attribute list

**Priority: P2 | Effort: Medium**

Move `SIMPLE_ATTRS` and `COMPOUND_GROUPS` from hardcoded Python constants into `ctx_config.json`:

```json
"gaffer_attributes": {
  "simple": ["intensity", "exposure", "temperature", "muted"],
  "compound": {
    "color":     ["colorR", "colorG", "colorB"],
    "translate": ["translateX", "translateY", "translateZ"],
    "rotate":    ["rotateX",    "rotateY",    "rotateZ"],
    "scale":     ["scaleX",     "scaleY",     "scaleZ"]
  },
  "renderer_extra": {
    "redshift": ["rsTemperature", "rsColorMode"],
    "arnold":   ["aiExposure", "aiSamples"]
  }
}
```

`EditMode`, `LightEditorPanel`, and `CTXLightContextSchema` all read from config at startup. TDs can add renderer-specific attributes for their show without touching Python source.

---

### R8 — Farm render hook

**Priority: P2 | Effort: Medium**

Create `pipeline/render_hook.py` — a pre-render Python script the farm executes before each render:

```python
# Called by Deadline/Tractor pre-render event plugin
# Environment vars: CTX_EP, CTX_SEQ, CTX_SHOT, CTX_DEPT

from pipeline.api import apply_shot, validate_scene

ep   = os.environ['CTX_EP']
seq  = os.environ['CTX_SEQ']
shot = os.environ['CTX_SHOT']

report = validate_scene()
if report['broken_target_lights'] or report['originals_node_missing']:
    raise RuntimeError("Scene validation failed: {}".format(report))

apply_shot(ep, seq, shot)
# Maya is now in the correct state for rendering shot
```

This is the bridge between the tool and the farm. Without it, applying the correct shot state before rendering requires a human to set the shot manually each time.

---

### R9 — Background threading for long operations

**Priority: P2 | Effort: Medium**

Add `QRunnable`-based workers for operations that take more than ~1 second:

- `AssetScanner.scan()` — full filesystem scan
- `GafferManager.apply_gaffer_to_all_lights()` — when many lights are present
- `SceneValidator.validate_scene()` — new validator (R2)

Pattern:

```python
class ScanWorker(QRunnable):
    def run(self):
        results = AssetScanner.scan(self._config)
        self.signals.finished.emit(results)
        self.signals.progress.emit(count, total)

pool = QThreadPool.globalInstance()
pool.start(worker)
```

Show `QProgressDialog` during any operation touching more than 10 nodes. Allow cancellation.

---

### R10 — `CTXLightOriginalsNode` resilience

**Priority: P2 | Effort: Low**

Three changes to harden the originals node against accidental deletion:

1. Add a `SceneValidator` check that flags a missing originals node (feeds into R2).
2. Add `CTXLightOriginalsNode.rebuild_from_scene()` — re-captures current Maya light values as a new baseline. Exposed as a "Reset Originals" button in the main window.
3. Lock the node after creation: `cmds.lockNode('CTX_LightOriginals', lock=True)` so Maya's scene cleanup operations cannot delete it without an explicit unlock.

---

### R11 — VRay renderer adapter

**Priority: P3 | Effort: Low**

Add `core/renderers/vray.py` with the VRay light attribute mapping, following the same pattern as `redshift.py` and `arnold.py`. VRay is the dominant renderer in TV animation and commercial work. The renderer detection in `core/renderers/__init__.py` already has the extension point for a third entry.

---

### R12 — CI pipeline

**Priority: P3 | Effort: Low**

Add `.github/workflows/test.yml` (or equivalent for the studio's git host) running:

```yaml
- pytest tests/ -v --ignore=tests/test_asset_manager.py
- pytest tests/test_asset_manager.py -v  # allowed to fail until Phase 3+ renderer work
```

This catches regressions on every push without requiring a Maya license (all tests use MockCmds).

---

### R13 — Remove orphaned UI files

**Priority: P3 | Effort: Low**

Delete or archive:

- `ui/shot_widget.py`
- `ui/asset_widget.py`
- `ui/filesystem_discovery.py`
- `ui/import_asset_dialog.py`
- `ui/convert_scene_dialog.py`

Verify no active import exists for each before deletion.

---

### R14 — Gaffer sharing visibility

**Priority: P3 | Effort: Low**

In `GafferManagerDialog`, add a read-only label below the gaffer selector showing:

```
Shared with: SH0170, SH0180, SH0190   (or "Not shared")
```

Populated by querying `cmds.listConnections(gaffer.message, destination=True)` and filtering for `CTX_Shot` nodes. This prevents artists from accidentally editing a shared gaffer without realising the change affects multiple shots.

---

## Priority Summary

| # | Recommendation | Priority | Effort |
|---|---|---|---|
| R1 | Pipeline API layer (headless entry point) | **P1** | Low |
| R2 | Scene validator | **P1** | Low |
| R3 | Gaffer JSON export / import | **P1** | Medium |
| R4 | Production tracker connector | **P1** | High |
| R5 | Undo/redo integration | **P1** | Low |
| R6 | Structured logging | **P2** | Low |
| R7 | Configurable attribute list (config-driven) | **P2** | Medium |
| R8 | Farm render hook | **P2** | Medium |
| R9 | Background threading for long operations | **P2** | Medium |
| R10 | Originals node resilience | **P2** | Low |
| R11 | VRay renderer adapter | **P3** | Low |
| R12 | CI pipeline | **P3** | Low |
| R13 | Remove orphaned UI files | **P3** | Low |
| R14 | Gaffer sharing visibility in UI | **P3** | Low |

---

## Suggested Sequencing

If starting Phase 4, the recommended order for maximum production impact with minimum risk:

**Sprint 1 — Reliability foundation**
- R5 (undo/redo) — prevents data loss, one day
- R10 (originals resilience) — prevents silent baseline loss, half a day
- R2 (scene validator) — catches drift before render, two days
- R6 (structured logging) — diagnosability, one day

**Sprint 2 — Automation reach**
- R1 (pipeline API) — headless entry point, two days
- R3 (gaffer export/import) — enables library sharing, three days
- R8 (farm render hook) — bridges tool to farm, depends on R1 + R3

**Sprint 3 — Scale**
- R9 (background threading) — removes UI blocking, three days
- R7 (configurable attributes) — TDs extend without code change, three days
- R4 (tracker connector) — bulk shot creation from production data, one week

**Sprint 4 — Polish**
- R11 (VRay), R12 (CI), R13 (dead files), R14 (gaffer sharing label)
