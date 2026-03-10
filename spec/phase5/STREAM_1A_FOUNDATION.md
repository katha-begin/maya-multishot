# Stream 1A — Foundation: Config, RenderJob, GPU Inventory, Temp Scene Manager

**Status:** Not Started
**Round:** 1 (parallel with 1B)
**Branch:** `feature/batch-render`
**Dependencies:** None

---

## Goal

Build the data layer for batch render. No Maya required for any of this.
Four deliverables: config extension, RenderJob dataclass, GPU detector, temp scene FIFO manager.

---

## 1. Config — `project_configs/ctx_config.json`

Add top-level `batchRender` section:

```json
"batchRender": {
    "reservedGpus": 1,
    "tempSceneMaxCount": 5,
    "tempSceneDir": null,
    "logDir": null,
    "frameHandles": 0,
    "redshift": {
        "gpuEnvVar": "REDSHIFT_GPUDEVICES"
    }
}
```

- `reservedGpus` — GPUs held back for interactive use (default 1 on workstation, 0 on farm)
- `tempSceneMaxCount` — FIFO max. When N+1 scene saved, oldest deleted. 0 = unlimited.
- `tempSceneDir` — null = auto (same dir as original scene + `/batch_temp/`)
- `logDir` — null = same as tempSceneDir
- `frameHandles` — extra frames before/after shot range (0 = no handles)

---

## 2. `config/project_config.py` — New Methods

Read the file first. Add after existing methods:

```python
def get_batch_render_config(self):
    """Return full batchRender config dict."""
    return self.data.get('batchRender', {})

def get_reserved_gpus(self):
    """Return number of GPUs reserved for interactive use."""
    return int(self.get_batch_render_config().get('reservedGpus', 1))

def get_temp_scene_max_count(self):
    """Return max number of temp scenes to keep (0 = unlimited)."""
    return int(self.get_batch_render_config().get('tempSceneMaxCount', 5))

def get_temp_scene_dir(self):
    """Return configured temp scene directory or None (auto)."""
    return self.get_batch_render_config().get('tempSceneDir')

def get_batch_log_dir(self):
    """Return configured log directory or None (auto)."""
    return self.get_batch_render_config().get('logDir')

def get_frame_handles(self):
    """Return extra handle frames to add around shot range."""
    return int(self.get_batch_render_config().get('frameHandles', 0))
```

---

## 3. `core/batch/__init__.py`

```python
"""Batch render package for CTX Tools multi-shot rendering."""

from core.batch.render_job import RenderJob, JobStatus
from core.batch.gpu_inventory import GPUInfo, detect_gpus, get_available_gpus
from core.batch.temp_scene_manager import TempSceneManager
```

---

## 4. `core/batch/render_job.py`

```python
"""RenderJob dataclass and JobStatus enum."""


class JobStatus(object):
    QUEUED = 'queued'
    PREPARING = 'preparing'
    RENDERING = 'rendering'
    DONE = 'done'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class RenderJob(object):
    """Represents a single shot render job.

    One RenderJob per shot. Each job may produce multiple subprocesses
    (one per render layer). All layers share the same prepared temp scene.
    """

    def __init__(self, ep, seq, shot,
                 scene_file=None,
                 start_frame=None,
                 end_frame=None,
                 render_layers=None,
                 camera=None,
                 gpu_index=None,
                 renderer='redshift'):
        """
        Args:
            ep (str): Episode code.
            seq (str): Sequence code.
            shot (str): Shot code.
            scene_file (str|None): Path to original .ma/.mb file.
            start_frame (int|None): Override start frame (None = from CTXShotNode).
            end_frame (int|None): Override end frame (None = from CTXShotNode).
            render_layers (list[str]|None): Layer names to render. None = all renderable.
            camera (str|None): Camera shape name. None = auto-detect from CAM asset.
            gpu_index (int|None): Assigned GPU index.
            renderer (str): Renderer name ('redshift', 'arnold').
        """
        self.ep = ep
        self.seq = seq
        self.shot = shot
        self.scene_file = scene_file
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.render_layers = render_layers  # None = all
        self.camera = camera
        self.gpu_index = gpu_index
        self.renderer = renderer

        # Set during prepare phase
        self.temp_scene_path = None
        self.resolved_start = None
        self.resolved_end = None
        self.resolved_layers = []
        self.resolved_camera = None
        self.output_dir = None

        # Runtime state
        self.status = JobStatus.QUEUED
        self.return_code = None
        self.error_message = None
        self.log_path = None

    @property
    def shot_id(self):
        """Return formatted shot ID string."""
        return '%s_%s_%s' % (self.ep, self.seq, self.shot)

    def to_dict(self):
        """Return JSON-serializable representation."""
        return {
            'ep': self.ep,
            'seq': self.seq,
            'shot': self.shot,
            'shot_id': self.shot_id,
            'scene_file': self.scene_file,
            'start_frame': self.start_frame,
            'end_frame': self.end_frame,
            'render_layers': self.render_layers,
            'camera': self.camera,
            'gpu_index': self.gpu_index,
            'renderer': self.renderer,
            'temp_scene_path': self.temp_scene_path,
            'resolved_start': self.resolved_start,
            'resolved_end': self.resolved_end,
            'resolved_layers': self.resolved_layers,
            'resolved_camera': self.resolved_camera,
            'output_dir': self.output_dir,
            'status': self.status,
            'return_code': self.return_code,
            'error_message': self.error_message,
            'log_path': self.log_path,
        }
```

---

## 5. `core/batch/gpu_inventory.py`

```python
"""GPU detection via nvidia-smi subprocess.

Works without any extra Python packages. nvidia-smi ships with the
NVIDIA driver and is available on AWS EC2 G4dn instances.
"""

import subprocess
import os

from core.logging_config import get_logger

logger = get_logger(__name__)


class GPUInfo(object):
    """Holds information about a single GPU."""

    def __init__(self, index, name, vram_total_mb, vram_free_mb, util_pct):
        self.index = index
        self.name = name
        self.vram_total_mb = vram_total_mb
        self.vram_free_mb = vram_free_mb
        self.util_pct = util_pct

    def __repr__(self):
        return 'GPUInfo(index=%d, name=%r, vram=%dMB)' % (
            self.index, self.name, self.vram_total_mb)

    def to_dict(self):
        return {
            'index': self.index,
            'name': self.name,
            'vram_total_mb': self.vram_total_mb,
            'vram_free_mb': self.vram_free_mb,
            'util_pct': self.util_pct,
        }


def detect_gpus():
    """Detect NVIDIA GPUs via nvidia-smi.

    Returns:
        list[GPUInfo]: Detected GPUs. Empty list if nvidia-smi unavailable.
    """
    try:
        result = subprocess.run(
            [
                'nvidia-smi',
                '--query-gpu=index,name,memory.total,memory.free,utilization.gpu',
                '--format=csv,noheader,nounits',
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            logger.warning("nvidia-smi returned non-zero: %s", result.stderr)
            return []

        gpus = []
        for line in result.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 5:
                continue
            try:
                gpus.append(GPUInfo(
                    index=int(parts[0]),
                    name=parts[1],
                    vram_total_mb=int(parts[2]),
                    vram_free_mb=int(parts[3]),
                    util_pct=int(parts[4]),
                ))
            except (ValueError, IndexError) as exc:
                logger.warning("Failed to parse GPU line %r: %s", line, exc)

        logger.info("Detected %d GPU(s): %s", len(gpus), [g.name for g in gpus])
        return gpus

    except FileNotFoundError:
        logger.info("nvidia-smi not found — no NVIDIA GPUs detected")
        return []
    except subprocess.TimeoutExpired:
        logger.warning("nvidia-smi timed out")
        return []
    except Exception as exc:
        logger.warning("GPU detection failed: %s", exc)
        return []


def get_available_gpus(reserved=1, config=None):
    """Return GPUs available for rendering after reserving some for interactive use.

    Args:
        reserved (int): Number of GPUs to reserve (not used for rendering).
                        Overridden by config.get_reserved_gpus() if config provided.
        config: Optional ProjectConfig instance.

    Returns:
        list[GPUInfo]: GPUs available for render (may be empty).
    """
    if config is not None:
        try:
            reserved = config.get_reserved_gpus()
        except Exception:
            pass

    all_gpus = detect_gpus()
    available = all_gpus[reserved:] if reserved < len(all_gpus) else []

    logger.info(
        "GPUs: total=%d reserved=%d available=%d",
        len(all_gpus), reserved, len(available)
    )
    return available
```

---

## 6. `core/batch/temp_scene_manager.py`

FIFO ring buffer for temp scene files. Keeps at most N files.
When a new file is registered and count exceeds max, the oldest is deleted.

```python
"""Temp scene file manager with FIFO cleanup.

Keeps at most max_count temp scene files. When a new file is registered
and the count would exceed max_count, the oldest file is deleted first.
Manifest stored as JSON alongside the temp files.
"""

import json
import os
import time

from core.logging_config import get_logger

logger = get_logger(__name__)

MANIFEST_FILENAME = 'batch_temp_manifest.json'


class TempSceneManager(object):

    def __init__(self, temp_dir, max_count=5):
        """
        Args:
            temp_dir (str): Directory where temp scenes are stored.
            max_count (int): Maximum number of temp scenes to keep. 0 = unlimited.
        """
        self.temp_dir = temp_dir
        self.max_count = max_count
        self._manifest_path = os.path.join(temp_dir, MANIFEST_FILENAME)
        self._entries = []  # list of dicts, oldest first
        self._load_manifest()

    def _load_manifest(self):
        """Load existing manifest from disk."""
        if os.path.exists(self._manifest_path):
            try:
                with open(self._manifest_path, 'r') as f:
                    self._entries = json.load(f)
                # Remove entries whose files no longer exist
                self._entries = [
                    e for e in self._entries
                    if os.path.exists(e.get('path', ''))
                ]
            except Exception as exc:
                logger.warning("Failed to load temp manifest: %s", exc)
                self._entries = []

    def _save_manifest(self):
        """Write current manifest to disk."""
        os.makedirs(self.temp_dir, exist_ok=True)
        try:
            with open(self._manifest_path, 'w') as f:
                json.dump(self._entries, f, indent=2)
        except Exception as exc:
            logger.warning("Failed to save temp manifest: %s", exc)

    def register(self, path, shot_id, job_id=None):
        """Register a new temp scene file.

        If max_count > 0 and adding this file would exceed the limit,
        the oldest file is deleted first.

        Args:
            path (str): Absolute path to the temp scene file.
            shot_id (str): Shot identifier for the manifest entry.
            job_id (str|None): Optional job identifier.

        Returns:
            str: The registered path.
        """
        entry = {
            'path': path,
            'shot_id': shot_id,
            'job_id': job_id or '',
            'created': time.strftime('%Y-%m-%dT%H:%M:%S'),
        }

        # Enforce max_count: evict oldest until we are under limit
        if self.max_count > 0:
            while len(self._entries) >= self.max_count:
                self._evict_oldest()

        self._entries.append(entry)
        self._save_manifest()
        logger.info("Registered temp scene: %s (total=%d)", path, len(self._entries))
        return path

    def _evict_oldest(self):
        """Delete the oldest temp scene file and remove its manifest entry."""
        if not self._entries:
            return
        oldest = self._entries.pop(0)
        path = oldest.get('path', '')
        if path and os.path.exists(path):
            try:
                os.remove(path)
                logger.info("Evicted temp scene: %s", path)
            except Exception as exc:
                logger.warning("Failed to delete temp scene %s: %s", path, exc)

    def make_path(self, shot_id, suffix='.ma'):
        """Generate a unique temp scene path for a shot.

        Args:
            shot_id (str): Shot identifier (used in filename).
            suffix (str): File extension including dot.

        Returns:
            str: Full path (file does not exist yet).
        """
        os.makedirs(self.temp_dir, exist_ok=True)
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = 'batch_%s_%s%s' % (shot_id, timestamp, suffix)
        return os.path.join(self.temp_dir, filename)

    def list_entries(self):
        """Return copy of current manifest entries (oldest first)."""
        return list(self._entries)

    def clear_all(self):
        """Delete all tracked temp scene files and clear the manifest."""
        for entry in list(self._entries):
            path = entry.get('path', '')
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as exc:
                    logger.warning("Failed to delete %s: %s", path, exc)
        self._entries = []
        self._save_manifest()
        logger.info("Cleared all temp scenes in %s", self.temp_dir)

    @classmethod
    def from_config(cls, config, scene_file=None):
        """Create a TempSceneManager from ProjectConfig.

        Args:
            config: ProjectConfig instance.
            scene_file (str|None): Original scene file (used to auto-derive temp_dir).

        Returns:
            TempSceneManager
        """
        temp_dir = config.get_temp_scene_dir()
        if not temp_dir:
            if scene_file:
                temp_dir = os.path.join(os.path.dirname(scene_file), 'batch_temp')
            else:
                temp_dir = os.path.join(os.path.expanduser('~'), 'maya_batch_temp')
        max_count = config.get_temp_scene_max_count()
        return cls(temp_dir, max_count)
```

---

## Tests — `tests/test_batch_foundation.py`

```python
# test_get_batch_render_config — returns dict from config
# test_get_reserved_gpus_default — default = 1
# test_get_temp_scene_max_count — default = 5
# test_render_job_shot_id — ep_seq_shot format
# test_render_job_to_dict — JSON serializable
# test_job_status_values — constants exist
# test_temp_scene_manager_make_path — generates unique path
# test_temp_scene_manager_register_and_evict — FIFO eviction at max_count
# test_temp_scene_manager_clear_all — deletes files
# test_temp_scene_manager_from_config — uses config values
# test_temp_scene_manifest_persists — survives reload
# test_detect_gpus_no_nvidia_smi — returns [] gracefully
# test_get_available_gpus_reserved — removes reserved from list
```

---

## Completion Criteria

- [ ] `batchRender` section added to `ctx_config.json`
- [ ] All new `ProjectConfig` methods added
- [ ] `core/batch/__init__.py` created
- [ ] `core/batch/render_job.py` created — `RenderJob` + `JobStatus`
- [ ] `core/batch/gpu_inventory.py` created — `detect_gpus()` + `get_available_gpus()`
- [ ] `core/batch/temp_scene_manager.py` created — FIFO with manifest
- [ ] All tests pass
- [ ] No regressions in existing test suite
