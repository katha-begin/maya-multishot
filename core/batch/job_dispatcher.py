"""Job dispatcher: launches Render subprocesses with GPU isolation.

One threading.Semaphore per GPU ensures at most one render process per GPU.
Each RenderJob may produce multiple subprocess calls (one per render layer).
"""

import os
import subprocess
import threading

from core.logging_config import get_logger

logger = get_logger(__name__)

# Path to Maya's Render executable -- override via MAYA_RENDER_BIN env var
DEFAULT_RENDER_BINS = [
    r'C:\Program Files\Autodesk\Maya2022\bin\Render.exe',
    r'C:\Program Files\Autodesk\Maya2024\bin\Render.exe',
    '/usr/autodesk/maya2022/bin/Render',
    '/usr/autodesk/maya2024/bin/Render',
]


def _find_render_bin():
    """Locate the Maya Render executable."""
    env_bin = os.environ.get('MAYA_RENDER_BIN')
    if env_bin and os.path.exists(env_bin):
        return env_bin
    for path in DEFAULT_RENDER_BINS:
        if os.path.exists(path):
            return path
    return 'Render'  # fall back to PATH


class JobDispatcher(object):
    """Dispatches render jobs across available GPUs.

    Usage::

        dispatcher = JobDispatcher(gpu_list, on_progress=my_callback)
        dispatcher.dispatch(job)   # non-blocking, runs in thread
        dispatcher.wait_all()      # block until all jobs done
    """

    def __init__(self, gpu_list, on_progress=None, renderer=None, config=None):
        """
        Args:
            gpu_list (list[GPUInfo]): Available GPUs from gpu_inventory.
            on_progress (callable|None): Called with (job, layer, status, message).
            renderer (str|None): Renderer name for -r flag. None = auto-detect at dispatch time.
            config: Optional ProjectConfig instance for GPU env var lookup.
        """
        self.gpu_list = gpu_list
        self.on_progress = on_progress
        self.renderer = renderer
        self.config = config
        self._render_bin = _find_render_bin()

        # One semaphore per GPU -- ensures single render per GPU
        self._semaphores = {
            gpu.index: threading.Semaphore(1)
            for gpu in gpu_list
        }
        self._threads = []
        self._lock = threading.Lock()

    def dispatch(self, job):
        """Dispatch a job asynchronously in a background thread.

        Args:
            job (RenderJob): Prepared job (must have temp_scene_path set).
        """
        t = threading.Thread(target=self._run_job, args=(job,), daemon=True)
        with self._lock:
            self._threads.append(t)
        t.start()

    def wait_all(self):
        """Block until all dispatched jobs complete."""
        with self._lock:
            threads = list(self._threads)
        for t in threads:
            t.join()

    def _run_job(self, job):
        """Execute all render layers for one job sequentially on one GPU."""
        from core.batch.render_job import JobStatus
        from core.batch import render_state as rs

        gpu_index = job.gpu_index if job.gpu_index is not None else 0
        sem = self._semaphores.get(gpu_index)
        if sem is None:
            # Fallback: use first available semaphore
            sem = next(iter(self._semaphores.values())) if self._semaphores else threading.Semaphore(1)

        logger.info("Job %s waiting for GPU %d", job.shot_id, gpu_index)
        sem.acquire()
        try:
            job.status = JobStatus.RENDERING
            rs.set_status(job.shot_id, rs.RENDERING)
            layers = job.resolved_layers or ['defaultRenderLayer']
            all_ok = True

            for layer in layers:
                ok = self._render_layer(job, layer, gpu_index)
                if not ok:
                    all_ok = False
                    break

            job.status = JobStatus.DONE if all_ok else JobStatus.FAILED
            rs.set_status(job.shot_id, rs.DONE if all_ok else rs.FAILED)
            self._notify(job, None, job.status, job.error_message or 'Complete')
        finally:
            sem.release()
            logger.info("GPU %d released by job %s", gpu_index, job.shot_id)

    def _render_layer(self, job, layer_name, gpu_index):
        """Run Render subprocess for one layer. Returns True on success."""
        from core.renderers import get_active_renderer, get_gpu_env_var

        renderer_name = self.renderer or get_active_renderer()

        cmd = [
            self._render_bin,
            '-r', renderer_name,
            '-s', str(job.resolved_start),
            '-e', str(job.resolved_end),
            '-rl', layer_name,
        ]
        if job.resolved_camera:
            cmd += ['-cam', job.resolved_camera]
        if job.output_dir:
            cmd += ['-rd', job.output_dir]
        cmd.append(job.temp_scene_path)

        env = os.environ.copy()
        gpu_env_var = get_gpu_env_var(renderer_name, self.config)
        if gpu_env_var:
            env[gpu_env_var] = str(gpu_index)
        env['MAYA_APP_DIR'] = os.path.join(
            os.path.expanduser('~'), '.maya_render_gpu%d' % gpu_index
        )

        log_path = self._get_log_path(job, layer_name)
        job.log_path = log_path

        logger.info(
            "Launching render: GPU=%d shot=%s layer=%s frames=%d-%d",
            gpu_index, job.shot_id, layer_name, job.resolved_start, job.resolved_end
        )
        self._notify(job, layer_name, 'rendering', 'Started')

        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            popen_kwargs = {'env': env, 'stderr': subprocess.STDOUT}
            if os.name == 'nt':
                popen_kwargs['creationflags'] = 0x08000000  # CREATE_NO_WINDOW
            with open(log_path, 'w') as log_file:
                popen_kwargs['stdout'] = log_file
                proc = subprocess.Popen(cmd, **popen_kwargs)
                job.return_code = proc.wait()

            success = job.return_code == 0
            if not success:
                job.error_message = 'Render exited with code %d' % job.return_code
                self._notify(job, layer_name, 'failed', job.error_message)
                logger.error("Render failed: %s layer=%s code=%d",
                             job.shot_id, layer_name, job.return_code)
            else:
                self._notify(job, layer_name, 'done', 'Layer complete')
                logger.info("Render complete: %s layer=%s", job.shot_id, layer_name)
            return success

        except Exception as exc:
            job.error_message = str(exc)
            self._notify(job, layer_name, 'failed', str(exc))
            logger.exception("Render exception: %s layer=%s: %s",
                             job.shot_id, layer_name, exc)
            return False

    def _get_log_path(self, job, layer_name):
        """Build log file path for a job+layer."""
        if job.log_path:
            base = os.path.dirname(job.log_path)
        elif job.temp_scene_path:
            base = os.path.join(os.path.dirname(job.temp_scene_path), 'logs')
        else:
            base = os.path.join(os.path.expanduser('~'), 'maya_batch_logs')
        filename = '%s_%s.log' % (job.shot_id, layer_name)
        return os.path.join(base, filename)

    def _notify(self, job, layer, status, message):
        """Invoke progress callback if set."""
        if self.on_progress:
            try:
                self.on_progress(job, layer, status, message)
            except Exception as exc:
                logger.warning("Progress callback error: %s", exc)
