# CFX Asset Type -- Design

Date: 2026-08-27
Branch: `feature/cfx-asset-type`
Status: Approved (Sections 1-2 reviewed with user; Sections 3-6 authored under
delegated approval)

---

## 1. Problem

The pipeline must handle a new asset type code, `CFX`, whose publish is an
**Arnold `.ass` frame sequence stored in a directory**, not a single file.

Example publish:

```
X:\EGA\all\scene\Ep02\sq0210\SH1180\cfx\publish\v009\
  Ep02_sq0210_SH1180__CFX_botgroomevelyn001_ass\
    Ep02_sq0210_SH1180__CFX_botgroomevelyn001.####.ass
```

Example scene structure (three levels, shape hidden in the Outliner):

```
Cfx_Grp
  Ep02_sq0220_SH1350__CFX_botgroomSamS001                     transform
    Ep02_sq0220_SH1350__CFX_botgroomSamS001_aiStandIn         transform
      Ep02_sq0220_SH1350__CFX_botgroomSamS001_aiStandInShape  aiStandIn
```

CFX differs from every existing type on four axes:

| Axis | Existing types | CFX |
|---|---|---|
| Publish unit | one file | a directory of per-frame files |
| Variant separator | `TYPE_Name_Var` | `TYPE_NameVar` (no separator) |
| Shot switch | repath `.dso` / reload reference | display-layer visibility only |
| Node identity | shot-agnostic namespace | shot-unique namespace |

## 2. Current-state findings

Established by reading the code; each is a constraint on the design.

**Two independent path pipelines exist.**

- Pipeline A -- `PathResolver.resolve_path(template_name, ctx)`
  (`core/resolver.py:143`) looks a template up by name. Used only for
  `imgPath`, `shotRoot`, `shotWork`, and `core/path_builder.py`.
- Pipeline B -- `NodeManager.resolve_asset_path()` (`core/nodes.py:274-350`)
  does all asset repathing. It does not look templates up by name; it expands
  the template **string** stored on `CTX_Asset.template` and re-implements
  root/staticPath/project injection inline.

Pipeline B's context is a fixed set: roots, static paths, `project`, `ep`,
`seq`, `shot`, `assetType`, `assetName`, `variant`, `dept`, `ext`, `ver`.
An unknown token is left unexpanded with a **warning only**
(`core/nodes.py:338-342`) -- a silent broken path. The CFX templates therefore
use only tokens from this set.

**Discovery rejects CFX twice**, before any other code runs:

- `core/asset_scanner.py:218` matches `filename.endswith('.ass')`; a CFX
  publish directory ends `_ass`.
- `core/asset_scanner.py:389-392` splits the asset part on `_`, requires 3+
  parts, and returns `None` for `CFX_botgroomSamS001`.

**Display layers are namespace-keyed.** `switch_shot_layers`
(`core/display_layers.py:359`) uses `asset.get_namespace()` as the global
identity key across all shots; empty namespaces are silently skipped at
`:409`. `_get_namespace_root` (`:491-494`) resolves objects via
`cmds.ls('<ns>:*')` and so requires a real Maya namespace.

**The reconciler only sees Maya references.** `core/asset_reconciler.py`
scans scene references; CFX standins are created nodes, so it cannot see
them at all. `_parse_namespace` (`:42-53`) also mis-parses the CFX basename.

**Dead code -- do not build on it.** `tools/asset_manager.py::AssetManager`
is referenced only by its own tests, and reads legacy attributes (`.path`,
`.maya_node`) that no longer exist on the schema. The live import path is
`ui/asset_manager_dialog.py`. The module-level functions in that same file
(`import_sets_asset`, `_connect_decomp_matrix`) *are* live.

**Config templates `assetHeroPath`, `assetShaderPath`, `assetGroomPath`,
`assetSearchPath` have zero Python references.** Hero paths come at runtime
from the `snow__pub_location` attribute on alembic locators.

**Latent bug.** `core/asset_scanner.py:165-166` hardcodes `'V:/'` and
`'SWA'` as fallbacks -- wrong for project EGA.

## 3. Naming and path contract (Section 1, approved)

Stated once, consumed by discovery, import, adopt and validation alike so the
four cannot drift apart.

| Field | Value |
|---|---|
| basename | `{ep}_{seq}_{shot}__CFX_{assetName}{variant}` |
| publish dir | `{basename}_ass` |
| frame files | `{basename}.####.ass` |
| Maya namespace | `{basename}` |
| top transform | `{basename}` |
| standin transform | `{basename}_aiStandIn` |
| standin shape | `{basename}_aiStandInShape` |
| `CTX_Asset.namespace` | `{basename}` |
| `CTX_Asset.targetNode` | the **shape** |

New templates:

| Template | Value |
|---|---|
| `assetSeqDir` | `$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish/$ver/$ep_$seq_$shot__$assetType_$assetName$variant_$ext` |
| `assetSeqPath` | `<assetSeqDir>/$ep_$seq_$shot__$assetType_$assetName$variant.####.$ext` |

Both use only Pipeline-B-injected tokens, so shot-switch repathing works with
no change to `core/nodes.py`. `####` contains no `$`, so `TokenExpander`'s
`\$([a-zA-Z][a-zA-Z0-9]*)` regex passes it through untouched -- which is what
Arnold requires.

Because the namespace equals the basename and the basename carries the shot
code, each shot's CFX gets a distinct identity key. This is what makes the
display-layer visibility toggle discriminate between shots.

**Known risk:** splitting `botgroomSamS001` into name + trailing 3-digit
variant misfires on a name genuinely ending in digits (`bot2000` -> `bot2` +
`000`). The variant pattern is config-driven (`\d{3}$`) so it is tunable
without a code change. Inherent to the no-separator convention.

## 4. Discovery and import (Section 2, approved)

### 4.1 `core/asset_types.py` -- naming/discovery policy

Replaces the scattered `if asset_type == 'CAM'` branches
(`asset_scanner.py` x2, `asset_manager_dialog.py:427`,
`asset_reconciler.py:42`). Answers three questions per type, config-backed:

| Question | CHAR/PROP/SDRS/VEH | CAM | CFX |
|---|---|---|---|
| `parse_asset_part()` | `TYPE_Name_Var` | `_camera` suffix | `TYPE_Name` + trailing `\d{3}` |
| `publish_shape()` | `file` | `file` | `sequenceDir` |
| `namespace_for()` | `TYPE_Name_Var` | name only | full basename |

CAM moves into this module as part of the work: the change *removes* the
existing scatter rather than adding a third instance. Node-building stays
out -- the per-kind menu handlers already cover it, and a builder registry
would be speculative.

### 4.2 Scanner

`_scan_department` iterates version-dir entries as both files and
directories. A directory matching `{basename}_{ext}` whose type has
`publish_shape == 'sequenceDir'` is recorded with `file_path` set to the
`####` frame path built from `assetSeqPath`.

**Never `os.listdir()` the sequence directory.** A CFX publish holds one
`.ass` per frame -- potentially thousands -- and the scanner already walks
every version of every department. Detect by directory name, construct the
`####` path from the template, existence-check the directory only.

### 4.3 Import

New handler `_on_create_asset_cfx(row)` in `ui/asset_manager_dialog.py`,
mirroring `_on_create_asset_standin` (`:1889`) and gated to CFX rows the way
SETS is:

1. Resolve `assetSeqDir`; error cleanly if absent.
2. Run the `CFXNamespaceCheck` pre-flight. **Abort on conflict** -- never
   auto-rename.
3. Build nodes via a new `create_standin_sequence()` in `core/nodes.py`,
   added alongside the existing builders rather than modifying them
   (`create_standin_with_namespace` hardcodes `...AIS`/`...AISShape`, which
   does not match CFX's three-level shape).
4. Set `.dso` to the `####` path and `.useFrameExtension = 1`.
5. Parent under a global `Cfx_Grp`, creating it if missing.
6. Create the `CTX_Asset` via `_create_and_link_ctx_asset` (`:656`), with
   `namespace` = basename and `targetNode` -> the **shape**.

MtoA attribute names (`dso`, `useFrameExtension`, `frameNumber`,
`frameOffset`, draw mode) live in config, not literals -- they have drifted
across MtoA versions.

**Open item:** the `Frame` field is driven (yellow in the Attribute Editor),
most likely `time1.outTime -> frameNumber`. Implemented behind a config flag
`cfx.frameDriver` (default `"time"`); to be confirmed against a live node.
Adopt never touches `frameNumber`.

## 5. Adopt and reconcile (Section 3)

The reconciler cannot see CFX today: it scans Maya references only, and CFX
standins are created nodes.

**`core/cfx_adopter.py`** -- a standin-aware discovery pass, kept separate
from the reference-based reconciler rather than entangled with it:

1. List `aiStandIn` shapes under `Cfx_Grp`.
2. For each, read `.dso` and parse it back to
   `(ep, seq, shot, assetType, assetName, variant, ver)` using the same
   `core/asset_types.py` contract used to build it.
3. Match against existing `CTX_Asset` nodes by `namespace`.
4. Create and wire missing `CTX_Asset` nodes for the shot the `.dso` names --
   not necessarily the active shot, since all shots' CFX coexist.

Adopt is **non-destructive**: it never renames a node, never adds a
namespace, never touches `frameNumber` or `.dso`. It only creates the
`CTX_Asset` records that make existing scene content visible to the tool.

`CTX_Asset.namespace` is set to the basename in both the created and adopted
cases. For created assets it is a real Maya namespace; for adopted flat-named
ones it is an identity string that happens to equal the node name. Section 6
bridges the difference.

## 6. Shot switch (Section 4)

CFX is the first **static-path** type: `.dso` is set once at import, and shot
switch changes only display-layer membership.

No change is required to `_on_set_shot`. `update_shot_paths`
(`core/nodes.py:520`) iterates only the *active* shot's assets, and each CFX
`CTX_Asset` belongs to exactly one shot, so re-resolving its path yields the
same value it already has. The operation is idempotent and self-correcting
after a version change; CFX is therefore left in Pipeline B rather than
special-cased out of it.

**Required fix -- `_get_namespace_root` fallback.** For adopted flat-named
nodes, `cmds.ls('<ns>:*')` returns empty, the asset is skipped at
`display_layers.py:409`, and visibility toggling silently does nothing. Add a
fallback: when the namespace lookup yields no transforms, resolve through
`_get_top_nodes_from_asset(asset.get_target_node())`, which already exists at
`:530`.

This also repairs the pre-existing `"No top node found for namespace"`
warnings for *any* namespace-less asset, not only CFX.

## 7. Versioning (Section 5)

CFX reuses the existing version machinery unchanged. Version discovery scans
`.../{ep}/{seq}/{shot}/{dept}/publish/` for `v\d{3}` directories and sorts
lexicographically descending -- correct for zero-padded versions.

The only CFX-specific requirement: the "latest version" probe must
existence-check the **sequence directory**, not a file, for types whose
`publish_shape` is `sequenceDir`.

Changing a CFX version rewrites `.dso` to the new version's `####` path via
the existing `_on_apply_version` flow (`asset_manager_dialog.py:1013`), which
already routes through `_apply_path_to_maya_node` -> `aiStandIn` -> `.dso`.
No new code path.

`useFrameExtension` and `frameNumber` are untouched by a version change.

## 8. Validation (Section 6)

`CFXNamespaceCheck`, a `BaseCheck` subclass registered with `SceneValidator`
(`core/validator/`). Read-only; it never mutates the scene.

| Condition | Severity |
|---|---|
| Un-namespaced CFX standin under `Cfx_Grp` | info |
| Target namespace exists and holds non-CFX content | error (blocks import) |
| Two CFX publishes resolving to the same basename | error |
| `aiStandIn` under `Cfx_Grp` with no backing `CTX_Asset` | warning (adopt candidate) |
| `CTX_Asset` of type CFX whose `targetNode` is dead | warning |

Migration of existing flat-named nodes into namespaces is an **explicit,
opt-in action**, never automatic. This repo has no undo for any of these
operations (a known Phase 4 gap), so an unintended migration is not
recoverable.

## 9. Decisions and rationale

| Decision | Rationale |
|---|---|
| Tolerant dual-mode (create namespaced, adopt as-is) | Never rewrites a scene the user did not ask to change; old scenes keep working |
| Namespace = full publish basename | Shot-unique, so display-layer keying discriminates between shots; name on disk matches name in scene |
| `name` + trailing-3-digit `variant` | Keeps CFX semantically consistent with CHAR/PROP |
| Visibility toggle, not repath | All shots' CFX coexist; matches observed scene structure |
| Templates use only Pipeline-B tokens | Avoids the silent-unexpanded-token failure mode |
| CAM folded into `asset_types.py` | Removes existing scatter instead of adding a third instance |
| No builder registry | YAGNI -- per-kind menu handlers already cover node building |

## 10. Out of scope

- Creating the EGA project config (CFX templates are added to the existing
  config; templates are project-agnostic).
- Fixing the `'V:/'`/`'SWA'` hardcoded fallbacks at
  `core/asset_scanner.py:165-166` -- noted, tracked separately.
- Removing dead `tools/asset_manager.py::AssetManager`.
- Wiring the unused `assetHeroPath` family of templates.
- Undo/redo support.

## 11. Constraints

- Python 2.7-3.x compatible: `from __future__ import absolute_import,
  division, print_function`; no f-strings, no type hints, no `pathlib`;
  `super(ClassName, self)`; `.format()` for interpolation.
- ASCII only in `.py` files.
- Schema-based wrappers from `core/nodes/wrappers/` only.
- Unidirectional connections: `child.message -> parent.attribute`.
- `isinstance(x, str)` guard style, never `isinstance(x, WrapperClass)`.
