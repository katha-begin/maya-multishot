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
        self.render_layers = render_layers
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
