# Stream 4 — Batch Render UI Dialog

**Status:** Complete
**Round:** 4 (after Round 3)
**Branch:** `feature/batch-render`
**Dependencies:** All previous streams

---

## Goal

`ui/batch_render_dialog.py` — a non-modal dialog launched from the Context Manager
menu. Shows shot queue, GPU status, render layer selection, frame range controls,
and a live progress table.

---

## Layout

```
┌─ Batch Render ──────────────────────────────────────────────────────┐
│                                                                      │
│  GPU Status                                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ GPU 0  NVIDIA T4  16GB  [====      ] 38%   [Reserved]       │   │
│  │ GPU 1  NVIDIA T4  16GB  [          ]  0%   [Available]      │   │
│  │ GPU 2  NVIDIA T4  16GB  [          ]  0%   [Available]      │   │
│  │ GPU 3  NVIDIA T4  16GB  [          ]  0%   [Available]      │   │
│  │                           Reserve for interactive: [1] (spin)│   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Shot Queue                               Render Layers              │
│  ┌──────────────────────────────────┐    ┌───────────────────────┐  │
│  │ [x] Ep04_sq0070_SH0170  1001-1080│    │ [x] beauty            │  │
│  │ [x] Ep04_sq0070_SH0180  1001-1060│    │ [x] shadow            │  │
│  │ [ ] Ep04_sq0070_SH0190  1001-1100│    │ [ ] depth             │  │
│  │                                  │    └───────────────────────┘  │
│  │ [Add Shot]  [Remove]  [Select All]│                               │
│  └──────────────────────────────────┘                               │
│                                                                      │
│  Frame Range  [Auto from shot]  Start [____] End [____]            │
│  Temp Scenes  Max count [5]  Dir [________________________] [Browse]│
│  Output       [W:/SWA/all/scene/Ep04/sq0070/SH0170/lighting/v001/] │
│                                                                      │
│  Progress                                                            │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Shot           │ Layer  │ GPU │ Frames  │ Status             │   │
│  │ SH0170         │ beauty │  1  │ 45/80   │ [====      ] 56%  │   │
│  │ SH0180         │ beauty │  2  │  0/60   │ Queued            │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  [ Dry Run ]  [ Start Render ]  [ Pause ]  [ Cancel ]              │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Key Behaviours

- **GPU panel** — refreshes every 5s via `QTimer`. Reserved GPU rows shown greyed out.
- **Shot queue** — pre-populated from `CTXShotNode.list_all()` in current scene.
  Frame range shown per shot from `get_frame_range()`.
- **Render layers** — populated from `RenderSetupManager.get_all_layers()`.
  Greyed out if not renderable (still checkable to force-include).
- **Frame range** — "Auto from shot" checkbox. When checked, overrides disabled.
  When unchecked, user can enter start/end to apply to ALL selected shots.
- **Temp scene settings** — max count spinbox + dir browser.
  Saved to config on change.
- **Progress table** — one row per shot × layer. Updated via Qt signal/slot
  from `on_progress` callback (thread-safe via `QMetaObject.invokeMethod`).
- **Start Render** — calls `PipelineAPI.batch_render()` in a background thread.
  Button disabled during render. Pause/Cancel enabled.
- **Dry Run** — calls `batch_render()` with `dry_run=True` (prepares scenes only).

---

## Class Structure

```python
class BatchRenderDialog(BaseDialog):

    # Signals
    progress_updated = QtCore.Signal(object, str, str, str)  # job, layer, status, msg

    def _setup_ui(self):
        # Build all widgets

    def _connect_signals(self):
        # Connect all signals/slots
        self.progress_updated.connect(self._on_progress_updated)

    def _refresh_gpu_panel(self):
        # Called by QTimer every 5s

    def _populate_shot_table(self):
        # From CTXShotNode.list_all()

    def _populate_layer_list(self):
        # From RenderSetupManager

    def _on_start_render(self):
        # Build job list, call PipelineAPI.batch_render() in QThread

    def _on_progress(self, job, layer, status, message):
        # Thread-safe: emit signal
        self.progress_updated.emit(job, layer, status, message)

    def _on_progress_updated(self, job, layer, status, message):
        # Qt main thread: update progress table row
```

---

## MainWindow Integration

In `tools/maya_menu.py` or `ui/main_window.py`, add menu item:

```python
cmds.menuItem(
    label='Batch Render...',
    parent=ctx_menu,
    command=lambda *_: _open_batch_render_dialog(),
)

def _open_batch_render_dialog():
    from ui.batch_render_dialog import BatchRenderDialog
    if not BatchRenderDialog._instance:
        BatchRenderDialog._instance = BatchRenderDialog(parent=maya_main_window())
    BatchRenderDialog._instance.show()
    BatchRenderDialog._instance.raise_()
```

---

## Completion Criteria

- [x] `ui/batch_render_dialog.py` created with all panels
- [x] GPU panel with QTimer refresh
- [x] Shot table pre-populated from scene
- [x] Render layer list from RenderSetupManager
- [x] Frame range auto/manual toggle
- [x] Temp scene max count + dir settings
- [x] Progress table updated thread-safely via signal
- [x] Start / Dry Run / Pause / Cancel wired
- [x] Menu item added to Context Manager menu
- [ ] `docs/batch_render.md` user guide written
