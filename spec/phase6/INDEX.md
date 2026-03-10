# Phase 6 — Lock System & Slate Manager: Task Index

**Branch:** `feature/phase6-lock-slate`
**Started:** 2026-03-11
**Status:** Not Started

---

## Features

### Feature 1 — Lock / Read-Only System
Leads can lock CTX nodes (sequence, shot, gaffer, asset) to prevent artists from
overriding published values. Sequence lock cascades to all shots under it.
Attribute-level Maya locks applied on key fields as secondary enforcement.

### Feature 2 — Slate Manager
Per-shot and per-sequence control of which render layers are renderable.
Inherits from a parent slate chain (Master → Sequence → Shot), identical
inheritance model to the Gaffer system. UI mirrors Gaffer Manager 100%.

---

## Streams

| Stream | Document | Round | Status |
|--------|----------|-------|--------|
| 6-A | [Lock Core — Mixin, LockManager, Schema Changes](./STREAM_6A_LOCK_CORE.md) | 1 | Complete |
| 6-B | [Lock UI — Column, Context Menu, Gaffer Banner](./STREAM_6B_LOCK_UI.md) | 2 | Complete |
| 6-C | [Slate Nodes — Schemas, Wrappers, Connections](./STREAM_6C_SLATE_NODES.md) | 1 | Complete |
| 6-D | [Slate Core — SlateManager, SlateResolver, Shot-Switch](./STREAM_6D_SLATE_CORE.md) | 2 | Complete |
| 6-E | [Slate Batch — ScenePreparer, Frame Range Default](./STREAM_6E_SLATE_BATCH.md) | 3 | Complete |
| 6-F | [Slate UI — SlateManagerDialog, +SLT Column](./STREAM_6F_SLATE_UI.md) | 4 | In Progress (spec revised) |
| 6-G | [Slate Originals — CTXSlateOriginalsNode, restore_originals()](./STREAM_6G_SLATE_ORIGINALS.md) | 4 | Not Started |

---

## Execution Order

```
Round 1 (parallel):  6-A + 6-C         (no dependencies)
Round 2 (parallel):  6-B + 6-D         (6-B needs 6-A; 6-D needs 6-C)
Round 3 (parallel):  6-E + 6-F         (6-E needs 6-D; 6-F needs 6-D)
Round 4 (parallel):  6-F fixes + 6-G   (6-G needs 6-D; 6-F Round 4 needs 6-G spec)
```

---

## Final Column Layout — Multishot Manager Shot Table

After both features are implemented, the shot table has 9 columns:

```
Col 0: #           (20px)   — row number
Col 1: Lck         (20px)   — lock icon [NEW in 6-B]
Col 2: Shot        (stretch) — shot label
Col 3: Frame Range (fixed)  — start–end
Col 4: Set         (fixed)  — set active shot button
Col 5: Ver         (38px)   — version button
Col 6: Gaf         (38px)   — +GAF / GAF button (unchanged)
Col 7: Slt         (38px)   — +SLT / SLT button [NEW in 6-F]
Col 8: Rnd         (28px)   — render status badge
```

---

## New Files

```
core/nodes/schemas/lock_mixin.py          <- 6-A
core/lock_manager.py                      <- 6-A
core/nodes/schemas/slate.py               <- 6-C
core/nodes/schemas/slate_layer.py         <- 6-C
core/nodes/wrappers/slate.py              <- 6-C
core/nodes/wrappers/slate_layer.py        <- 6-C
core/slate/__init__.py                    <- 6-D
core/slate/manager.py                     <- 6-D
core/slate/resolver.py                    <- 6-D
core/nodes/schemas/slate_originals.py     <- 6-G
core/nodes/wrappers/slate_originals.py    <- 6-G
ui/slate_manager_dialog.py                <- 6-F
tests/test_lock_manager.py                <- 6-A
tests/test_slate_nodes.py                 <- 6-C
tests/test_slate_resolver.py              <- 6-D
tests/test_slate_originals.py             <- 6-G
```

## Modified Files

```
core/nodes/schemas/shot.py                <- 6-A (lock mixin) + 6-C (slate connection)
core/nodes/schemas/sequence.py            <- 6-A (lock mixin) + 6-C (slate connection)
core/nodes/schemas/gaffer.py              <- 6-A (lock mixin)
core/nodes/schemas/asset.py               <- 6-A (lock mixin)
core/nodes/wrappers/__init__.py           <- 6-C (export CTXSlateNode, CTXSlateLayerNode)
ui/main_window.py                         <- 6-B (lock col) + 6-F (+SLT col, shot-switch)
ui/gaffer_manager_dialog.py               <- 6-B (lock banner + enforcement)
core/batch/scene_preparer.py              <- 6-E (slate-aware layer resolution)
ui/batch_render_dialog.py                 <- 6-E (frame range default: start+end)
tools/pipeline_api.py                     <- 6-E (get_shot_slate_layers helper)
tools/cli.py                              <- 6-E (--use-slate-layers flag)
tools/maya_menu.py                        <- 6-F (Slate Manager menu item)
project_configs/ctx_config.json           <- 6-E (slateManager config section)
```

---

## Completion Checklist

- [ ] Stream 6-A complete + tests passing
- [ ] Stream 6-B complete + tests passing
- [ ] Stream 6-C complete + tests passing
- [ ] Stream 6-D complete + tests passing
- [ ] Stream 6-E complete + tests passing
- [ ] Stream 6-F complete
- [ ] CLAUDE.md updated
- [ ] MEMORY.md updated
- [ ] Branch merged to main
