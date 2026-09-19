# Maya diagnostics

Scripts in this folder run **inside Maya** (Script Editor, Python tab). They are
read-only probes for diagnosing a live scene -- none of them modifies anything.

They deliberately do **not** use the `test_*.py` name prefix.  `tests/` has no
`conftest.py` and no pytest config, so collection is purely name-based: a
`test_*.py` file that imports `maya.cmds` at module scope aborts the whole run
with

```
ERROR tests/test_display_layer_visibility.py -> ModuleNotFoundError: No module named 'maya'
!!! Interrupted: 2 errors during collection !!!
```

`tests/test_display_layer_visibility.py` and `tests/test_is_active_connection.py`
are existing examples of that problem.  Put new Maya-only scripts here instead.

## Running

```python
exec(open(r"T:\pipeline\development\maya\maya-multishot\tests\diagnostics\diag_sets_layer.py").read())
```

| Script | Purpose |
|---|---|
| `diag_sets_layer.py` | Why a SETS asset lands in `CTX_Inactive`: namespace membership, true top nodes, current layer wiring, stray per-component connections. |
| `preview_stale_records.py` | Dry run of `repair_scene_records()` -- lists CTX_Asset records each shot never published. Deletes nothing. |
| `repair_set_component_layers.py` | **Writes** (opt-in). Disconnects `drawOverride` on set pieces so they inherit the set's top transform again, and drops CTX_Asset records naming a nested piece. Dry run unless you call `repair(apply=True)`. Leaves your own display layers untouched. |

## The set-goes-invisible bug

An imported SETS asset references its pieces into namespaces nested under its
own (`SETS_X_001:TRLRWallA_0001`). The reconciler used to adopt those pieces
as CTX_Asset records of whichever shot was open, so every *other* shot
computed them as inactive and pinned each piece's `Geo_Grp` to `CTX_Inactive`.

A child carrying its own `drawOverride` connection stops inheriting its
parent's layer -- so the set's top transform sits in `CTX_Active` while every
piece is pinned inactive, and the set is invisible on all but one shot.

`core/display_layers.py` now skips nested namespaces, which stops new pins.
An already-affected scene still needs `repair_set_component_layers.py` to
undo the existing ones.
