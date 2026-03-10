# Stream 3 — Render Queue, Pipeline API Extension, CLI Command

**Status:** Not Started
**Round:** 3 (after Round 2)
**Branch:** `feature/batch-render`
**Dependencies:** Streams 1A, 1B, 2A, 2B

---

## Goal

Tie all batch render components together into a `RenderQueue`, expose via
`PipelineAPI.batch_render()`, and add a `batch-render` CLI command.

---

## `core/batch/render_queue.py`

```python
class RenderQueue(object):
    """Manages a queue of RenderJob objects and dispatches them across GPUs.

    Usage::

        queue = RenderQueue(config, platform_config)
        queue.add_shot('Ep04', 'sq0070', 'SH0170', scene_file='scene.ma')
        queue.add_shot('Ep04', 'sq0070', 'SH0180', scene_file='scene.ma')
        queue.start(on_progress=my_callback)
        queue.wait()
    """

    def __init__(self, config, platform_config=None):
        self.config = config
        self.platform_config = platform_config
        self._jobs = []

    def add_shot(self, ep, seq, shot, scene_file=None,
                 start_frame=None, end_frame=None,
                 render_layers=None, camera=None):
        """Add a shot to the render queue. Returns the RenderJob."""

    def add_shots_from_list(self, shots, scene_file=None):
        """Add multiple shots. shots = list of (ep, seq, shot) tuples."""

    def start(self, on_progress=None):
        """Prepare all jobs and dispatch across available GPUs.

        Preparation (ScenePreparer) runs serially.
        Dispatch (JobDispatcher) runs in parallel threads.
        """

    def wait(self):
        """Block until all dispatched jobs complete."""

    def get_summary(self):
        """Return dict with total, done, failed, cancelled counts."""
```

---

## `tools/pipeline_api.py` — New Method

```python
def batch_render(self, shots, scene_file=None,
                 render_layers=None, start_frame=None, end_frame=None,
                 on_progress=None):
    """Render multiple shots in batch using available GPUs.

    No Maya required for queuing. Maya required for prepare + render steps.

    Args:
        shots (list): List of (ep, seq, shot) tuples or dicts.
        scene_file (str|None): Scene to open. None = current scene.
        render_layers (list[str]|None): Layers to render. None = all renderable.
        start_frame (int|None): Override start. None = from CTXShotNode.
        end_frame (int|None): Override end. None = from CTXShotNode.
        on_progress (callable|None): Called with (job, layer, status, message).

    Returns:
        dict: {
            'success': bool,
            'total': int,
            'done': int,
            'failed': int,
            'jobs': list[dict],
        }
    """
```

---

## `tools/cli.py` — New Command `batch-render`

```bash
# Render specific shots
python tools/cli.py batch-render \
    --scene file.ma \
    --shots Ep04_sq0070_SH0170 Ep04_sq0070_SH0180 \
    --layers beauty shadow

# Render all shots in scene
python tools/cli.py batch-render --scene file.ma --all-shots

# Dry run (prepare only, no render)
python tools/cli.py batch-render --scene file.ma --all-shots --dry-run

# Reserve 0 GPUs (farm mode)
python tools/cli.py batch-render --scene file.ma --all-shots --reserve-gpus 0

# JSON output
python tools/cli.py --json batch-render --scene file.ma --all-shots
```

Flags:
- `--scene FILE` — scene file
- `--shots SHOT [SHOT ...]` — shot IDs as `ep_seq_shot`
- `--all-shots` — use all CTX shots in scene
- `--layers LAYER [LAYER ...]` — render layers (default: all renderable)
- `--start-frame N` — override start frame
- `--end-frame N` — override end frame
- `--reserve-gpus N` — GPUs to reserve (default: from config)
- `--dry-run` — prepare scenes but do not render
- `--no-save` — do not save temp scenes after render

---

## Completion Criteria

- [ ] `core/batch/render_queue.py` with `add_shot`, `add_shots_from_list`, `start`, `wait`, `get_summary`
- [ ] `PipelineAPI.batch_render()` implemented
- [ ] `batch-render` CLI command with all flags
- [ ] `--json` output supported
- [ ] `--dry-run` mode works (prepare only)
- [ ] `--all-shots` discovers shots from CTXShotNode.list_all()
- [ ] Tests pass
