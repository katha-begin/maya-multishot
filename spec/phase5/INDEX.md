# Phase 5 — Multi-Shot Batch Render: Task Index

**Branch:** `feature/batch-render`
**Started:** 2026-03-10
**Status:** In Progress

---

## Target Environment
- AWS EC2 G4dn (NVIDIA T4, 16GB VRAM each)
- G4dn.12xlarge: 4x T4 | G4dn.24xlarge: 8x T4
- Renderer: Redshift (primary)
- Render layers: Maya Render Setup (modern API)
- Maya licenses: not a constraint

---

## Streams

| Stream | Document | Round | Status |
|--------|----------|-------|--------|
| 1A | [Foundation — Config, RenderJob, GPU, TempScene](./STREAM_1A_FOUNDATION.md) | 1 | Not Started |
| 1B | [Render Setup Manager](./STREAM_1B_RENDER_SETUP.md) | 1 | Not Started |
| 2A | [Scene Preparer](./STREAM_2A_SCENE_PREPARER.md) | 2 | Not Started |
| 2B | [Job Dispatcher](./STREAM_2B_JOB_DISPATCHER.md) | 2 | Not Started |
| 3  | [Render Queue + API + CLI](./STREAM_3_QUEUE_API_CLI.md) | 3 | Not Started |
| 4  | [Batch Render UI Dialog](./STREAM_4_UI.md) | 4 | Complete |

---

## Execution Order

```
Round 1 (parallel):  1A + 1B
Round 2 (parallel):  2A + 2B   (after Round 1)
Round 3 (serial):    3          (after Round 2)
Round 4 (serial):    4          (after Round 3)
```

---

## New Files

```
core/batch/
  __init__.py                 ← 1A
  gpu_inventory.py            ← 1A
  render_job.py               ← 1A
  temp_scene_manager.py       ← 1A
  render_setup_manager.py     ← 1B
  scene_preparer.py           ← 2A
  job_dispatcher.py           ← 2B
  render_queue.py             ← 3

ui/batch_render_dialog.py     ← 4
tools/pipeline_api.py         ← 3 (extend)
tools/cli.py                  ← 3 (extend)
docs/batch_render.md          ← 4
```

---

## Completion Checklist

- [ ] Stream 1A complete + tests passing
- [ ] Stream 1B complete + tests passing
- [ ] Stream 2A complete + tests passing
- [ ] Stream 2B complete + tests passing
- [ ] Stream 3 complete + tests passing
- [x] Stream 4 complete
- [ ] CLAUDE.md updated
- [ ] MEMORY.md updated
- [ ] Branch merged to main
