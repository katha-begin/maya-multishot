# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Sources of truth**
> - Architecture: `spec/ARCHITECTURE_SUMMARY.md`
> - Project overview / patterns: `AGENTS.md`
> - Schema node system: `core/nodes/AGENTS.md`
> - Persistent session state: `.claude/memory.md` (update as you work)

---

## What this is

Maya plugin that lets artists work on multiple shots in a single Maya scene. Three pillars:

1. **Custom Maya network nodes** in a hierarchy `CTX_Manager → CTX_Sequence → CTX_Shot → CTX_Asset` connected via message attributes. All new code uses the **schema-based** wrappers in `core/nodes/wrappers/`; the older `core/custom_nodes.py` is frozen for backward compatibility (do not modify, do not import in new code).
2. **Named-template path resolver** — templates live in `project_configs/ctx_config.json`, tokens are camelCase (`$ep`, `$seq`, `$shot`, `$assetType`, `$assetName`, `$variant`, etc.). Resolve via name (`PathResolver.resolve_path('publishPath', ctx)`), never hand-build template strings.
3. **Hierarchical light gaffer system** — Master → Sequence → Shot, per-attribute enable flags, snapshot/diff edit-mode commit. Plus the **slate manager** (Phase 6) which mirrors gaffer patterns for renderable-layer overrides.

---

## Common commands

```bash
# Run tests (the project uses MockCmds + MAYA_AVAILABLE so most tests run without Maya)
pytest tests/ -v
pytest --cov=core --cov-report=html tests/
pytest tests/test_gaffer_manager.py -v          # single file
pytest tests/ -k "slate_resolver"               # single test by keyword

# CLI (headless — needs mayapy or a Maya-compatible Python on PATH)
python tools/cli.py --help
python tools/cli.py batch-render --shots SH0170 --all-layers --dry-run
```

```python
# Launch the dockable Multishot Manager inside Maya
exec(open(r'E:/dev/maya-multishot/launch_multishot_dockable.py').read())

# Other launchers
exec(open(r'.../launch_batch_render_dockable.py').read())   # Batch Render
exec(open(r'.../launch_slate_manager.py').read())           # Slate Manager
```

**Known test gaps:** `tests/test_asset_manager.py` has 10 pre-existing failures tied to renderer work (Phase 4+); not blocking.

---

## Non-negotiable rules

### Code style

- **No emoji in `.py` files** (comments, docstrings, prints, logger messages, names). Markdown is fine.
- Python 3.7+ syntax only (Maya 2022 constraint).
- Use `core.logging_config.get_logger(__name__)`, not `print()`. Stream C of Phase 4 replaced every `print()` in the active path.

### Node system

```python
# CORRECT
from core.nodes.wrappers import (
    CTXManagerNode, CTXSequenceNode, CTXShotNode, CTXAssetNode,
    CTXLightGafferNode, CTXLightContextNode,
    CTXSlateNode, CTXSlateLayerNode, CTXSlateOriginalsNode,
)

# WRONG — deprecated, do not import in new code
from core.custom_nodes import CTXManagerNode
```

- Attribute name is **`ctx_type`** (not `ctx_node_type`).
- Connections are **unidirectional**: `child.message → parent.attribute` only. Never wire both directions.
- `CTXShotNode` accessors: `get_ep_code()`, `get_seq_code()`, `get_shot_code()` — never `.ep`, `.seq`, `.shot`.
- Wrapper-or-string pattern: when a method accepts `(wrapper | str)`, do `node if isinstance(node, str) else node.node_name` — never `isinstance(node, CTXFooNode)`, which breaks after Maya module reload due to stale class objects.
- New node type: add schema in `core/nodes/schemas/`, wrapper in `core/nodes/wrappers/`, export from `core/nodes/wrappers/__init__.py`, write tests.

### Frozen / off-limits

- `core/custom_nodes.py` — backward-compat shim, do not modify.
- `vendor/` — vendored third-party (NodeGraphQt).
- `core/ctx_converter.py::convert_to_ctx()` — still references `core.custom_nodes` but is not in any active dialog/tool path; leave it.

### Window / dock lifecycle (`cmds.dockControl` is brittle)

This bit the project repeatedly; follow the ordering exactly:

1. Delete old `dockControl` first.
2. `QtWidgets.QApplication.processEvents()`.
3. Create the new `QMainWindow`.
4. `processEvents()` again.
5. `OpenMayaUI.MQtUtil.findControl(...)`.
6. `cmds.dockControl(..., content=...)`.

Skipping any step causes second-launch docking to fail silently. Don't call `dlg.show()` before `dockControl` — you get two windows.

`closeEvent` / `showEvent` overrides in any `QMainWindow` subclass: call **`QtWidgets.QMainWindow.closeEvent(self, event)` explicitly** — never `super()`. After a Maya module reload `super()` resolves to a stale class object and crashes.

Launchers clear `__pycache__` on launch to avoid stale bytecode on remote machines.

---

## Architecture cheat-sheet

### Node hierarchy and connections

```
CTX_Manager (singleton)
  ↑ sequences[i]   (Sequence.message → Manager.sequences[i])
CTX_Sequence
  ↑ shots[i]       (Shot.message → Sequence.shots[i])
  ↑ gaffer         (SeqGaffer.message → Sequence.gaffer)
  ↑ slate          (SeqSlate.message  → Sequence.slate)
CTX_Shot
  ↑ assets[i]      (Asset.message → Shot.assets[i])
  ↑ gaffer         (ShotGaffer.message → Shot.gaffer)
  ↑ slate          (ShotSlate.message  → Shot.slate)
CTX_Asset
  ↑ targetNode     (ReferenceNode.message → Asset.targetNode)

Inheritance chains (walked by resolvers, enabled flag controls override vs inherit):
  Master Gaffer → Sequence Gaffer → Shot Gaffer    (CTXLightGaffer.parentGaffer)
  Master Slate  → Sequence Slate  → Shot Slate     (CTXSlate.parentSlate)
```

### Path resolution

`project_configs/ctx_config.json` defines templates, roots, tokens, static paths. The resolver auto-injects platform-aware roots — callers only provide shot/asset context:

```python
from config.project_config import ProjectConfig
from config.platform_config import PlatformConfig
from core.resolver import PathResolver

resolver = PathResolver(ProjectConfig('project_configs/ctx_config.json'),
                        PlatformConfig(ProjectConfig(...)))
path = resolver.resolve_path('publishPath',
                             {'ep': 'Ep04', 'seq': 'sq0070', 'shot': 'SH0170', 'dept': 'lighting'})
```

Auto-injected (do not pass): `projRoot`, `imgRoot`, `project`, `sceneBase`, `assetBase`. Template names are listed in `core/resolver.py`; key ones are `publishPath`, `assetPath`, `assetHeroPath`, `imgPath`, `cachePath`, `namespace`.

Token patterns to honour: `$ep` = `Ep\d+`, `$seq` = `sq\d+`, `$shot` = `SH\d+`, `$ver` = `v\d{3}`, `$variant` = `\d{3}`, `$assetType` ∈ `{CHAR, PROP, SETS, SDRS, VEH, CAM}`. Underscore is a path separator, not part of token names.

### Gaffer system rules

- **Gaffer is optional.** No gaffer anywhere → lights restore to original Maya values from `MainWindow._light_original_values` (snapshot taken on window open).
- **Apply order on shot switch:** shot gaffer (if any) → else sequence gaffer (if any) → else restore originals.
- **Resolver walk order:** `[shot_gaffer, seq_gaffer, master_gaffer]`. First gaffer where `{attr}Enabled == True` wins.
- **Edit-mode commit pattern:** all edits apply live to Maya via `cmds.setAttr()` during edit mode; commit captures changes via snapshot-diff. CTX_Light values are written **only** via `EditMode.commit()`, never directly from UI widgets.
- **`set_target_light()` always resolves to the light shape node.** Pass a transform → it resolves to the first child shape.
- **Attribute enable-flag naming:** simple attrs add `Enabled` (`intensity` → `intensityEnabled`); compound attrs same (`color` → `colorEnabled`, `translate` → `translateEnabled`, `shadowEnable` → `shadowEnableEnabled`).
- **Additive mode was removed** in the May 2026 refactor — gaffer now operates strictly in override mode. The viewport HUD shows current gaffer / slate state.

### Slate system (Phase 6)

Mirrors gaffer patterns: per-shot/sequence/master with `parentSlate` inheritance, snapshot/diff edit mode, originals capture/restore (`CTXSlateOriginalsNode` singleton). Naming convention: `seq_{seq_code}` and `{seq_code}_{shot_code}`. UI (`ui/slate_manager_dialog.py`) is intentionally a near-clone of `gaffer_manager_dialog.py` — keep the parallel structure when changing either.

Pre-Phase-6 Maya nodes lack the slate attributes — every slate wrapper uses an `_ensure_*_attr()` guard for safe upgrade. Don't remove these guards.

### Batch render (Phase 5)

Lives in `core/batch/`. Key design constraints — do not regress:

- **Renderer auto-detected at dispatch time** via `core/renderers.get_active_renderer()`. No UI dropdown, no hardcoding.
- **GPU env var resolved from config only** (`get_gpu_env_var(renderer_name, config)`). If the renderer isn't in `batchRender.gpuEnvVar`, no var is set — CPU / unknown renderers work fine.
- **`MAYA_APP_DIR` unique per GPU** to avoid prefs collisions across concurrent dispatches.
- **One semaphore per GPU** (`threading.Semaphore(1)`); round-robin assignment.
- **`BatchRenderDialog` is a `QMainWindow`** (not `QDialog`) — required for `cmds.dockControl` compatibility.
- **`PipelineAPI.batch_render()` must call lazy loaders** `self._get_config()` / `self._get_platform_config()`, never the underscore-prefixed attributes (both `None` until loaded).
- **Layer priority in `scene_preparer`:** explicit layers > slate > scene fallback.
- **Task table layer placeholder:** use `'-'` for auto-resolved jobs, fill in actual layer on the first progress callback.

### Lock system (Phase 6)

`LockSchemaMixin` on Shot/Sequence/Gaffer/Asset schemas adds `is_locked`, `locked_by`, `locked_at`. `LockManager` static class is the only API; sequence locks cascade to all shots via `is_effectively_locked()`. UI: `Lck` column in Multishot Manager + an enforcement banner in Gaffer Manager that disables Edit Mode.

### Asset reconciliation

`core/asset_reconciler.py::reconcile_assets_for_shot(shot)` repairs CTX_Asset linkage on shot-switch and Validate-All: scans scene references, parses namespaces (`TYPE_Name[_Sub]_Variant`), auto-creates missing `CTX_Asset` nodes, and wires `ReferenceNode.message → CTX_Asset.targetNode`. Returns `{'created', 'linked', 'skipped'}` stats. Called from shot-switch and from the "Link to Shot" / "Validate All" context menu actions.

Asset namespace linking goes through `CTXConverter.link_all_by_namespace(namespace)` — never per-node `link_ctx_asset_to_scene`. This is the canonical bulk-link method.

CTX_Asset naming: `CTX_Asset_{assetType}_{assetName}_{shotCode}` (e.g. `CTX_Asset_CHAR_CatStompie_SH0170`) — one per shot, all sharing the same Maya reference via `targetNode`. The old namespace-based name caused Maya auto-increment collisions.

### SETS import + decomposeMatrix

SETS asset import (`tools/asset_manager.py`): one Maya reference per locator, merges on re-import, shader-only on existing geo. CHAR asset import wires `decomposeMatrix` from geo transforms to shader `place3dTexture` nodes — unlocks TRS, snaps before connect, existence-checks, auto-renames namespaces. `ShadingAttr_Grp.snow__*` buffer attributes wire through to shader `UserData` nodes (May 2026 feature).

---

## Key file locations

| What | Where |
|---|---|
| Project config (templates, roots, tokens, batchRender, slateManager) | `project_configs/ctx_config.json` |
| Config + platform loaders | `config/project_config.py`, `config/platform_config.py` |
| Path resolver + token expander | `core/resolver.py`, `core/tokens.py` |
| Node schemas / wrappers (current) | `core/nodes/schemas/`, `core/nodes/wrappers/` |
| Legacy nodes (frozen, do not modify) | `core/custom_nodes.py` |
| Gaffer system | `core/gaffer/` |
| Slate system | `core/slate/` |
| Batch render | `core/batch/` |
| Lock system | `core/lock_manager.py`, `core/nodes/schemas/lock_mixin.py` |
| Asset reconciliation / linking | `core/asset_reconciler.py`, `core/ctx_linker.py`, `core/ctx_converter.py` |
| Headless API / CLI | `tools/pipeline_api.py`, `tools/cli.py` |
| Validator | `core/validator/` |
| Logging | `core/logging_config.py` |
| Main UI | `ui/main_window.py` |
| Dock launchers | `launch_*.py` at repo root |

---

## Testing without Maya

`tools/base_manager.py` provides `MockCmds` + the `MAYA_AVAILABLE` flag. Tests gate Maya-required logic with `@unittest.skipUnless(MAYA_AVAILABLE, "Requires Maya")`. Always write new tests so they pass in both modes (or skip cleanly without Maya); never assume Maya is present at import time.

---

## Memory / session continuity

After non-trivial work, append to `.claude/memory.md` (newest first): what was done, what's next, decisions made. The next session resumes from there without re-reading every doc.
