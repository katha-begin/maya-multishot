# Stream 6-E — Slate Batch: ScenePreparer, Frame Range Default

**Status:** Not Started
**Round:** 3 (after 6-D)
**Branch:** `feature/phase6-lock-slate`
**Dependencies:** Stream 6-D (SlateResolver.get_resolved_renderable_layers)

---

## Goal

Connect the Slate system into the batch render pipeline so shots automatically
render only the layers their slate declares as renderable. Also change the
Batch Render Configure tab's default frame range from full range to start+end
frame only, with a per-row control for artists to expand to full range.

---

## 1. `core/batch/scene_preparer.py` — Slate-Aware Layer Resolution

Read the file fully before editing. The current layer resolution block is:

```python
# Current logic (approx lines 94-101)
rs_mgr = RenderSetupManager()
if job.render_layers:
    job.resolved_layers = job.render_layers
else:
    job.resolved_layers = rs_mgr.get_layer_names(renderable_only=True)
    if not job.resolved_layers:
        job.resolved_layers = ['defaultRenderLayer']
```

Replace the `else` branch with slate-aware resolution:

```python
rs_mgr = RenderSetupManager()
if job.render_layers:
    # Explicit override always wins — no slate lookup
    job.resolved_layers = job.render_layers
    logger.debug(
        "Job %s: using explicit render layers: %s",
        job.shot_id, job.render_layers
    )
else:
    # Try slate resolution first
    slate_layers = None
    try:
        from core.slate.resolver import SlateResolver
        from core.nodes.wrappers import CTXShotNode
        # Find the CTXShotNode for this job
        all_shots = CTXShotNode.list_all()
        shot_node = None
        for sn in all_shots:
            if (sn.get_ep_code() == job.ep
                    and sn.get_seq_code() == job.seq
                    and sn.get_shot_code() == job.shot):
                shot_node = sn
                break
        if shot_node is not None:
            slate_layers = SlateResolver.get_resolved_renderable_layers(shot_node)
    except Exception as exc:
        logger.warning("Slate layer resolution failed for %s: %s", job.shot_id, exc)

    if slate_layers is not None:
        # Slate found and resolved — use its layer list
        job.resolved_layers = slate_layers if slate_layers else ['defaultRenderLayer']
        logger.info(
            "Job %s: slate resolved layers: %s",
            job.shot_id, job.resolved_layers
        )
    else:
        # No slate — fall back to all renderable layers in scene (existing behaviour)
        job.resolved_layers = rs_mgr.get_layer_names(renderable_only=True)
        if not job.resolved_layers:
            job.resolved_layers = ['defaultRenderLayer']
        logger.debug(
            "Job %s: no slate — using scene renderable layers: %s",
            job.shot_id, job.resolved_layers
        )
```

**Priority order (explicit in code):**
1. `job.render_layers` explicitly set → use those
2. Slate found → use slate-resolved renderable layers
3. No slate → all scene renderable layers (original behaviour)

---

## 2. `project_configs/ctx_config.json` — slateManager Section

Read the file before editing. Add after the `batchRender` section:

```json
"slateManager": {
    "defaultFrameRangeMode": "startEnd"
}
```

- `defaultFrameRangeMode`: `"startEnd"` = render start frame + end frame only (default).
  Future values: `"full"` = full frame range.

---

## 3. `config/project_config.py` — New Method

Read the file before editing. Add:

```python
def get_slate_manager_config(self):
    """Return full slateManager config dict."""
    return self.data.get('slateManager', {})

def get_default_frame_range_mode(self):
    """Return default frame range mode for batch render Configure tab.

    Returns:
        str: 'startEnd' (default) or 'full'.
    """
    return self.get_slate_manager_config().get('defaultFrameRangeMode', 'startEnd')
```

---

## 4. `ui/batch_render_dialog.py` — Frame Range Default

Read the file fully before editing. This change affects the Configure tab's
shot table rows, specifically the Start Frame and End Frame columns.

### Current behaviour

Frame range columns show the full shot frame range pulled from `CTXShotNode`:
`start_frame` → `end_frame` (e.g. `1001` → `1100`).
All frames in that range are rendered.

### New behaviour

Default mode: render start frame + end frame only.
- Start Frame column shows `1001` (unchanged)
- End Frame column shows `1001` (same as start — one frame)
- A `[...]` expand button or checkbox in each row lets the user switch to full range

When expanded:
- Start Frame = `1001`, End Frame = `1100` (full range)

### Shot row data model change

Each shot row dict adds a `frame_range_mode` field:

```python
# When building shot rows in _build_shot_row() or similar:
{
    'ep':               sn.get_ep_code(),
    'seq':              sn.get_seq_code(),
    'shot':             sn.get_shot_code(),
    'start_frame':      sn.get_start_frame(),
    'end_frame':        sn.get_end_frame(),
    'frame_range_mode': 'startEnd',  # default; user can change to 'full'
}
```

### Frame Range column display logic

```python
def _get_display_frame_range(self, row_data):
    """Return (start, end) to display and submit for a shot row.

    Args:
        row_data (dict): Shot row dict with frame_range_mode, start_frame, end_frame.

    Returns:
        tuple[int, int]: (start_frame, end_frame) to render.
    """
    mode = row_data.get('frame_range_mode', 'startEnd')
    start = row_data['start_frame']
    end = row_data['end_frame']
    if mode == 'startEnd':
        return (start, start)  # Only start frame (or start + end as two jobs)
    return (start, end)        # Full range
```

**Start + End as two jobs clarification:**
"Start and end frame" means TWO single-frame render jobs:
- Job 1: frame = `start_frame` only
- Job 2: frame = `end_frame` only

This matches the existing Quick Render behaviour from Phase 5
(`queue_quick_render_jobs()` creates two explicit single-frame jobs).

The `frame_range_mode='startEnd'` button in the Configure tab sets
`start_frame = end_frame = start_frame` for the first job, and
`start_frame = end_frame = end_frame` for the second job when submitting.

### Expand toggle button per row

In the Frame Range column of the Configure tab shot table, add a small
toggle button or checkbox:

```
[1001–1001]  [+]     ← startEnd mode, click [+] to expand
[1001–1100]  [-]     ← full mode, click [-] to collapse back
```

The `[+]` / `[-]` button is a `QPushButton` (16px wide) placed in the
Frame Range cell via `setCellWidget`. Clicking it toggles `frame_range_mode`
between `'startEnd'` and `'full'` and refreshes the cell display.

```python
def _make_frame_range_cell(self, row_index, row_data):
    """Return a widget for the Frame Range cell in the Configure tab.

    Shows current range and a toggle button to expand/collapse.
    """
    container = QtWidgets.QWidget()
    layout = QtWidgets.QHBoxLayout(container)
    layout.setContentsMargins(2, 0, 2, 0)
    layout.setSpacing(2)

    start, end = self._get_display_frame_range(row_data)
    range_label = QtWidgets.QLabel('{}-{}'.format(start, end))
    range_label.setFixedWidth(70)

    mode = row_data.get('frame_range_mode', 'startEnd')
    toggle_btn = QtWidgets.QPushButton('+' if mode == 'startEnd' else '-')
    toggle_btn.setFixedSize(16, 16)
    toggle_btn.setToolTip(
        'Expand to full frame range' if mode == 'startEnd'
        else 'Collapse to start+end frames only'
    )
    toggle_btn.clicked.connect(
        lambda checked=False, r=row_index: self._on_toggle_frame_range(r)
    )

    layout.addWidget(range_label)
    layout.addWidget(toggle_btn)
    return container

def _on_toggle_frame_range(self, row_index):
    """Toggle frame_range_mode for a Configure tab shot row."""
    row_data = self._configure_shots[row_index]
    current_mode = row_data.get('frame_range_mode', 'startEnd')
    row_data['frame_range_mode'] = 'full' if current_mode == 'startEnd' else 'startEnd'
    # Refresh this row's Frame Range cell
    cell = self._make_frame_range_cell(row_index, row_data)
    self._configure_table.setCellWidget(row_index, FRAME_RANGE_COL, cell)
```

### Submit uses resolved frame range

When the user clicks Render in the Configure tab, read `frame_range_mode`
from each row to set `start_frame` and `end_frame` on the `RenderJob`:

```python
for row_data in self._configure_shots:
    mode = row_data.get('frame_range_mode', 'startEnd')
    if mode == 'startEnd':
        # Two single-frame jobs
        jobs.append(RenderJob(
            ep=row_data['ep'], seq=row_data['seq'], shot=row_data['shot'],
            start_frame=row_data['start_frame'],
            end_frame=row_data['start_frame'],
            ...
        ))
        jobs.append(RenderJob(
            ep=row_data['ep'], seq=row_data['seq'], shot=row_data['shot'],
            start_frame=row_data['end_frame'],
            end_frame=row_data['end_frame'],
            ...
        ))
    else:
        # Full range — one job
        jobs.append(RenderJob(
            ep=row_data['ep'], seq=row_data['seq'], shot=row_data['shot'],
            start_frame=row_data['start_frame'],
            end_frame=row_data['end_frame'],
            ...
        ))
```

---

## 5. `tools/pipeline_api.py` — Slate Helper

Read the file. Add one new method to `PipelineAPI`:

```python
def get_shot_slate_layers(self, ep, seq, shot):
    """Return the resolved renderable layer list for a shot via its slate.

    Args:
        ep (str): Episode code.
        seq (str): Sequence code.
        shot (str): Shot code.

    Returns:
        list[str]|None: Renderable layer names, or None if no slate.
    """
    try:
        from core.nodes.wrappers import CTXShotNode
        from core.slate.resolver import SlateResolver
        all_shots = CTXShotNode.list_all()
        for sn in all_shots:
            if (sn.get_ep_code() == ep
                    and sn.get_seq_code() == seq
                    and sn.get_shot_code() == shot):
                return SlateResolver.get_resolved_renderable_layers(sn)
    except Exception as exc:
        self._logger.warning("get_shot_slate_layers failed: %s", exc)
    return None
```

---

## 6. `tools/cli.py` — --use-slate-layers Flag

Read the file. In the `batch-render` subcommand argument parser, add:

```python
batch_parser.add_argument(
    '--use-slate-layers',
    action='store_true',
    default=False,
    help='Resolve render layers from each shot\'s slate instead of --layers.',
)
```

In the `batch-render` handler, if `--use-slate-layers` is set, do not pass
`render_layers` to `pipeline_api.batch_render()` — let `ScenePreparer`
resolve via slate automatically (which it now does by default when
`job.render_layers` is None).

```python
if args.use_slate_layers:
    render_layers = None  # ScenePreparer will resolve from slate
elif args.layers:
    render_layers = args.layers
else:
    render_layers = None
```

---

## Completion Criteria

- [ ] `scene_preparer.py` resolves layers via slate when `job.render_layers` is None
- [ ] Explicit `job.render_layers` always takes precedence over slate
- [ ] `ctx_config.json` has `slateManager.defaultFrameRangeMode`
- [ ] `ProjectConfig` has `get_slate_manager_config()` and `get_default_frame_range_mode()`
- [ ] Configure tab defaults to start+end frame only (two single-frame jobs on submit)
- [ ] Per-row `[+]` / `[-]` toggle switches between `startEnd` and `full` mode
- [ ] `PipelineAPI.get_shot_slate_layers()` added
- [ ] CLI `--use-slate-layers` flag added
- [ ] No regressions in existing test suite
