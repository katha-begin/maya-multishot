"""Scene preparer for batch render.

Applies shot context to a Maya scene and saves a render-ready temp copy.
Runs inside Maya (interactive or standalone). Not a subprocess itself.
"""

from __future__ import absolute_import, division, print_function

import os

from core.logging_config import get_logger

logger = get_logger(__name__)


class ScenePreparer(object):
    """Prepares a Maya scene for batch rendering.

    Operations performed:
    1. Open scene (if scene_file provided and not already open)
    2. Apply CTX shot context via PipelineAPI.set_active_shot()
    3. Resolve frame range from CTXShotNode (+ handles)
    4. Resolve render camera from CAM assets
    5. Set defaultRenderGlobals (startFrame, endFrame, imageFilePrefix)
    6. Resolve and set render output path from imgPath template
    7. Save to temp scene path via TempSceneManager

    Usage::

        preparer = ScenePreparer(config, platform_config)
        result = preparer.prepare(job)
        # result['temp_scene_path'] is the ready scene file
    """

    def __init__(self, config, platform_config=None):
        self.config = config
        self.platform_config = platform_config

    def prepare(self, job):
        """Prepare a scene for a single RenderJob.

        Sets job.temp_scene_path, job.resolved_start, job.resolved_end,
        job.resolved_layers, job.resolved_camera, job.output_dir on success.

        Args:
            job (RenderJob): Job to prepare. Modified in place.

        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            import maya.cmds as cmds
            from core.batch.temp_scene_manager import TempSceneManager
            from core.batch.render_setup_manager import RenderSetupManager

            job.status = 'preparing'

            # Step 1: Open scene if needed
            if job.scene_file:
                current = cmds.file(query=True, sceneName=True) or ''
                if os.path.normpath(current) != os.path.normpath(job.scene_file):
                    logger.info("Opening scene: %s", job.scene_file)
                    cmds.file(job.scene_file, open=True, force=True)

            # Step 2: Apply shot context
            from tools.pipeline_api import PipelineAPI
            api = PipelineAPI()
            api._config = self.config
            api._platform_config = self.platform_config
            result = api.set_active_shot(
                job.ep, job.seq, job.shot,
                save=False,
                apply_paths=True,
                apply_gaffer=True,
                apply_slate=True,
            )
            if not result.get('success'):
                raise RuntimeError("set_active_shot failed: %s" % result.get('message'))

            # Step 3: Resolve frame range
            from core.nodes.wrappers import CTXShotNode
            shot_node = CTXShotNode.find_by_code(job.ep, job.seq, job.shot)
            if shot_node:
                start, end = shot_node.get_frame_range()
                handles = self.config.get_frame_handles() if self.config else 0
                job.resolved_start = (job.start_frame if job.start_frame is not None
                                      else start - handles)
                job.resolved_end   = (job.end_frame   if job.end_frame   is not None
                                      else end + handles)
            else:
                job.resolved_start = job.start_frame or 1001
                job.resolved_end   = job.end_frame   or 1100

            # Step 4: Resolve camera
            job.resolved_camera = self._resolve_camera(job, shot_node)

            # Step 5: Resolve render layers
            rs_mgr = RenderSetupManager()
            if job.render_layers:
                # Explicit override always wins -- no slate lookup
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
                    from core.nodes.wrappers import CTXShotNode as _CTXShotNode
                    all_shots = _CTXShotNode.list_all()
                    shot_node_for_slate = None
                    for sn in all_shots:
                        if (sn.get_ep_code() == job.ep
                                and sn.get_seq_code() == job.seq
                                and sn.get_shot_code() == job.shot):
                            shot_node_for_slate = sn
                            break
                    if shot_node_for_slate is not None:
                        slate_layers = SlateResolver.get_resolved_renderable_layers(
                            shot_node_for_slate
                        )
                except Exception as exc:
                    logger.warning(
                        "Slate layer resolution failed for %s: %s", job.shot_id, exc
                    )

                if slate_layers is not None:
                    # Slate found and resolved -- use its layer list
                    job.resolved_layers = slate_layers if slate_layers else ['defaultRenderLayer']
                    logger.info(
                        "Job %s: slate resolved layers: %s",
                        job.shot_id, job.resolved_layers
                    )
                else:
                    # No slate -- fall back to all renderable layers in scene
                    job.resolved_layers = rs_mgr.get_layer_names(renderable_only=True)
                    if not job.resolved_layers:
                        logger.warning(
                            "Job %s: no renderable layers found via Render Setup"
                            " (is_available=%s) -- falling back to defaultRenderLayer",
                            job.shot_id, rs_mgr.is_available()
                        )
                        job.resolved_layers = ['defaultRenderLayer']
                    else:
                        logger.info(
                            "Job %s: no slate -- using scene renderable layers: %s",
                            job.shot_id, job.resolved_layers
                        )

            # Step 6: Set defaultRenderGlobals
            self._set_render_globals(job)

            # Step 7: Resolve output path
            job.output_dir = self._resolve_output_dir(job)

            # Step 8: Save temp scene
            tsm = TempSceneManager.from_config(self.config, job.scene_file)
            temp_path = tsm.make_path(job.shot_id)
            cmds.file(rename=temp_path)
            cmds.file(save=True, type='mayaAscii' if temp_path.endswith('.ma') else 'mayaBinary')
            # Re-open original name to restore scene state
            if job.scene_file:
                cmds.file(job.scene_file, open=True, force=True)

            tsm.register(temp_path, job.shot_id)
            job.temp_scene_path = temp_path
            logger.info("Prepared temp scene: %s", temp_path)
            return {'success': True, 'message': 'Scene prepared for %s' % job.shot_id}

        except Exception as exc:
            logger.exception("Scene prepare failed for %s: %s", job.shot_id, exc)
            job.status = 'failed'
            job.error_message = str(exc)
            return {'success': False, 'message': str(exc)}

    def _resolve_camera(self, job, shot_node):
        """Resolve the render camera for this shot."""
        if job.camera:
            return job.camera
        if shot_node:
            try:
                from core.nodes import NodeManager
                nm = NodeManager()
                cam_assets = nm.get_assets_by_type(shot_node, 'CAM')
                if cam_assets:
                    ns = cam_assets[0].get_namespace()
                    import maya.cmds as cmds
                    cams = cmds.ls('%s:*' % ns, type='camera') if ns else []
                    if cams:
                        return cams[0]
            except Exception as exc:
                logger.warning("Camera resolve failed: %s", exc)
        return None

    def _set_render_globals(self, job):
        """Apply frame range and output prefix to defaultRenderGlobals."""
        import maya.cmds as cmds
        cmds.setAttr('defaultRenderGlobals.startFrame', job.resolved_start)
        cmds.setAttr('defaultRenderGlobals.endFrame',   job.resolved_end)
        logger.debug(
            "Set render range %d-%d for %s",
            job.resolved_start, job.resolved_end, job.shot_id
        )

    def _resolve_output_dir(self, job):
        """Resolve the render output directory for this shot."""
        try:
            from core.resolver import PathResolver
            from config.platform_config import PlatformConfig

            platform_config = self.platform_config or PlatformConfig(self.config)
            resolver = PathResolver(self.config, platform_config)

            rs_cfg = self.config.get_render_settings_config() if self.config else {}
            out_cfg = rs_cfg.get('outputPath', {})
            dept = out_cfg.get('deptFallback', 'lighting')
            ver  = out_cfg.get('versionFallback', 'v001')

            context = {
                'ep':   job.ep,
                'seq':  job.seq,
                'shot': job.shot,
                'dept': dept,
                'ver':  ver,
            }
            # imgPath ends with <RenderLayer>/<RenderLayer> -- get parent dir
            img_path = resolver.resolve_path('imgPath', context)
            # Strip the two <RenderLayer> segments to get the base output dir
            output_dir = os.path.dirname(os.path.dirname(img_path))

            # Set prefix on defaultRenderGlobals (Maya substitutes <RenderLayer>)
            import maya.cmds as cmds
            prefix = img_path
            cmds.setAttr('defaultRenderGlobals.imageFilePrefix', prefix, type='string')
            logger.info("Set render output prefix: %s", prefix)
            return output_dir

        except Exception as exc:
            logger.warning("Output path resolution failed: %s", exc)
            return None
