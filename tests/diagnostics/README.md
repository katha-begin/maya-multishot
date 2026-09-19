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
