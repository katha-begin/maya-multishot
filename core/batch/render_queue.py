# -*- coding: utf-8 -*-
"""Render queue: manages a list of RenderJob objects and dispatches them across GPUs."""

from core.logging_config import get_logger

logger = get_logger(__name__)


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
        from core.batch.render_job import RenderJob
        job = RenderJob(
            ep=ep, seq=seq, shot=shot,
            scene_file=scene_file,
            start_frame=start_frame,
            end_frame=end_frame,
            render_layers=render_layers,
            camera=camera,
        )
        self._jobs.append(job)
        logger.info("Added shot to queue: %s (total=%d)", job.shot_id, len(self._jobs))
        return job

    def add_shots_from_list(self, shots, scene_file=None):
        """Add multiple shots. shots = list of (ep, seq, shot) tuples."""
        added = []
        for item in shots:
            if isinstance(item, dict):
                ep = item['ep']
                seq = item['seq']
                shot = item['shot']
            else:
                ep, seq, shot = item[0], item[1], item[2]
            job = self.add_shot(ep, seq, shot, scene_file=scene_file)
            added.append(job)
        return added

    def start(self, on_progress=None, dry_run=False):
        """Prepare all jobs and dispatch across available GPUs.

        Preparation (ScenePreparer) runs serially.
        Dispatch (JobDispatcher) runs in parallel threads.

        Args:
            on_progress (callable|None): Called with (job, layer, status, message).
            dry_run (bool): If True, prepare scenes but do not render.
        """
        from core.batch.gpu_inventory import get_available_gpus
        from core.batch.scene_preparer import ScenePreparer
        from core.batch.job_dispatcher import JobDispatcher
        from core.batch.render_job import JobStatus

        # Get available GPUs
        gpu_list = get_available_gpus(config=self.config)
        if not gpu_list:
            logger.warning("No GPUs available for rendering")

        # Assign GPU indices round-robin
        for i, job in enumerate(self._jobs):
            if gpu_list:
                job.gpu_index = gpu_list[i % len(gpu_list)].index
            else:
                job.gpu_index = 0

        # Prepare phase (serial)
        preparer = ScenePreparer(self.config, self.platform_config)
        for job in self._jobs:
            if on_progress:
                on_progress(job, None, 'preparing', 'Preparing scene')
            result = preparer.prepare(job)
            if not result.get('success'):
                logger.error("Prepare failed for %s: %s", job.shot_id, result.get('message'))

        if dry_run:
            logger.info("Dry run complete -- skipping dispatch")
            return

        # Dispatch phase (parallel via JobDispatcher)
        if gpu_list:
            dispatcher = JobDispatcher(gpu_list, on_progress=on_progress)
        else:
            # No GPU info -- create a dummy GPUInfo-like object
            from core.batch.gpu_inventory import GPUInfo
            dummy_gpu = GPUInfo(index=0, name='CPU', vram_total_mb=0, vram_free_mb=0, util_pct=0)
            dispatcher = JobDispatcher([dummy_gpu], on_progress=on_progress)

        self._dispatcher = dispatcher
        for job in self._jobs:
            if job.status != 'failed':
                dispatcher.dispatch(job)

    def wait(self):
        """Block until all dispatched jobs complete."""
        if hasattr(self, '_dispatcher'):
            self._dispatcher.wait_all()

    def get_summary(self):
        """Return dict with total, done, failed, cancelled counts."""
        from core.batch.render_job import JobStatus
        total = len(self._jobs)
        done = sum(1 for j in self._jobs if j.status == JobStatus.DONE)
        failed = sum(1 for j in self._jobs if j.status == JobStatus.FAILED)
        cancelled = sum(1 for j in self._jobs if j.status == JobStatus.CANCELLED)
        return {
            'total': total,
            'done': done,
            'failed': failed,
            'cancelled': cancelled,
            'jobs': [j.to_dict() for j in self._jobs],
        }
