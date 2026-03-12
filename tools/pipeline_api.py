# -*- coding: utf-8 -*-
"""Headless pipeline API for CTX Tools.

Provides programmatic access to pipeline operations without requiring
Maya UI. Some operations require Maya (standalone or interactive).

Usage::

    from tools.pipeline_api import PipelineAPI

    api = PipelineAPI(config_path='project_configs/ctx_config.json')
    assets = api.scan_assets('Ep04', 'sq0070', 'SH0170')
    for a in assets:
        print(a['type'], a['name'], a['file_path'])
"""

from __future__ import absolute_import
from __future__ import print_function

import os

from core.logging_config import get_logger, setup_logging

logger = get_logger(__name__)

CONFIG_ENV_VAR = 'CTX_CONFIG'
DEFAULT_CONFIG_PATH = 'project_configs/ctx_config.json'


class PipelineAPI(object):
    """Headless API for the CTX Multishot Pipeline.

    All methods that interact with Maya nodes require Maya to be importable.
    Pure filesystem methods (e.g. scan_assets) work without Maya.
    """

    def __init__(self, config_path=None, maya_standalone=False):
        """Initialise the API.

        Args:
            config_path (str|None): Path to ctx_config.json.
                Falls back to the CTX_CONFIG environment variable, then to
                DEFAULT_CONFIG_PATH ('project_configs/ctx_config.json').
            maya_standalone (bool): When True, calls
                maya.standalone.initialize() before the first Maya operation.
        """
        self._config_path = (
            config_path
            or os.environ.get(CONFIG_ENV_VAR)
            or DEFAULT_CONFIG_PATH
        )
        self._maya_standalone = maya_standalone
        self._config = None
        self._platform_config = None
        self._maya_initialized = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_config(self):
        """Return a cached ProjectConfig instance.

        Returns:
            ProjectConfig
        """
        if self._config is None:
            from config.project_config import ProjectConfig
            self._config = ProjectConfig(self._config_path)
        return self._config

    def _get_platform_config(self):
        """Return a cached PlatformConfig instance.

        Returns:
            PlatformConfig
        """
        if self._platform_config is None:
            from config.platform_config import PlatformConfig
            self._platform_config = PlatformConfig(self._get_config())
        return self._platform_config

    def _require_maya(self):
        """Assert that Maya is importable.

        If maya_standalone=True was passed at construction, also calls
        maya.standalone.initialize() once.

        Raises:
            RuntimeError: If maya.cmds cannot be imported.
        """
        try:
            import maya.cmds  # noqa: F401
        except ImportError:
            raise RuntimeError(
                "This operation requires Maya. "
                "Run inside Maya or use maya_standalone=True."
            )
        if self._maya_standalone and not self._maya_initialized:
            import maya.standalone
            maya.standalone.initialize(name='python')
            self._maya_initialized = True

    def _open_scene(self, scene_file):
        """Open a Maya scene file.

        Args:
            scene_file (str): Path to .ma or .mb file.

        Raises:
            RuntimeError: If the file cannot be opened.
        """
        import maya.cmds as cmds
        try:
            cmds.file(scene_file, open=True, force=True)
        except Exception as exc:
            raise RuntimeError("Could not open scene '%s': %s" % (scene_file, exc))

    def _find_shot_node(self, ep, seq, shot):
        """Locate a CTXShotNode by codes.

        Args:
            ep (str): Episode code.
            seq (str): Sequence code.
            shot (str): Shot code.

        Returns:
            CTXShotNode

        Raises:
            ValueError: If the shot cannot be found in the scene.
        """
        from core.nodes.wrappers import CTXShotNode
        node = CTXShotNode.find_by_code(ep, seq, shot)
        if node is None:
            raise ValueError(
                "Shot not found in scene: %s_%s_%s" % (ep, seq, shot)
            )
        return node

    # ------------------------------------------------------------------
    # Public methods — no Maya required
    # ------------------------------------------------------------------

    def scan_assets(self, ep, seq, shot, departments=None):
        """Scan the filesystem for published assets for a given shot.

        Does NOT require Maya. Pure filesystem operation.

        Args:
            ep (str): Episode code, e.g. 'Ep04'.
            seq (str): Sequence code, e.g. 'sq0070'.
            shot (str): Shot code, e.g. 'SH0170'.
            departments (list|None): Departments to scan.
                None means all departments listed in config.

        Returns:
            list[dict]: Each dict has keys:
                type, name, variant, dept, version, file_path, ext
        """
        from core.asset_scanner import AssetScanner

        config = self._get_config()
        scanner = AssetScanner(config)

        if departments is None:
            try:
                departments = config.get_token_values('dept') or []
            except Exception:
                departments = []
            if not departments:
                departments = ['anim', 'layout', 'fx', 'lighting']

        results = []
        for dept in departments:
            try:
                discovered = scanner._discover_assets_in_dept(ep, seq, shot, dept)
            except Exception as exc:
                logger.warning(
                    "scan_assets: error scanning dept %s for %s_%s_%s: %s",
                    dept, ep, seq, shot, exc
                )
                continue

            for (asset_type, asset_name, variant), asset_data in discovered.items():
                ext = ''
                info = asset_data.get('info', {})
                if isinstance(info, dict):
                    ext = info.get('ext', '')
                results.append({
                    'type': asset_type,
                    'name': asset_name,
                    'variant': variant,
                    'dept': dept,
                    'version': asset_data.get('version', ''),
                    'file_path': asset_data.get('file_path', ''),
                    'ext': ext,
                })

        logger.info(
            "scan_assets: found %d assets for %s_%s_%s across %d departments",
            len(results), ep, seq, shot, len(departments)
        )
        return results

    # ------------------------------------------------------------------
    # Public methods — Maya required
    # ------------------------------------------------------------------

    def validate_scene(self, scene_file, ep, seq, shot):
        """Run the scene validator on a Maya scene file.

        Opens the file, runs all checks, returns a ValidatorReport.
        Requires Maya.

        Args:
            scene_file (str): Path to .ma or .mb file.
            ep (str): Episode code.
            seq (str): Sequence code.
            shot (str): Shot code.

        Returns:
            ValidatorReport

        Raises:
            RuntimeError: If Maya is not available.
        """
        self._require_maya()
        self._open_scene(scene_file)

        from core.validator import SceneValidator
        validator = SceneValidator(self._get_config(), self._get_platform_config())
        return validator.validate_shot_by_code(ep, seq, shot)

    def apply_shot(self, scene_file, ep, seq, shot, save=True):
        """Open a Maya scene, apply the specified shot context, optionally save.

        Requires Maya.

        Args:
            scene_file (str): Path to .ma or .mb file.
            ep (str): Episode code.
            seq (str): Sequence code.
            shot (str): Shot code.
            save (bool): If True, save the scene after applying.

        Returns:
            dict: {'success': bool, 'message': str, 'output_file': str|None}
        """
        self._require_maya()
        import maya.cmds as cmds

        try:
            self._open_scene(scene_file)
            shot_node = self._find_shot_node(ep, seq, shot)

            from core.nodes import NodeManager
            nm = NodeManager()
            nm.update_shot_paths(shot_node, self._get_config(), self._get_platform_config())

            output_file = None
            if save:
                cmds.file(save=True, force=True)
                output_file = scene_file

            return {
                'success': True,
                'message': 'Shot applied: %s_%s_%s' % (ep, seq, shot),
                'output_file': output_file,
            }
        except Exception as exc:
            logger.exception("apply_shot failed: %s", exc)
            return {
                'success': False,
                'message': str(exc),
                'output_file': None,
            }

    def set_active_shot(self, ep, seq, shot, scene_file=None, save=True,
                        apply_paths=True, apply_gaffer=True, apply_slate=True):
        """Set a shot as the active shot in a Maya scene.

        Performs the same operations as clicking "Set" in the Context Manager UI:
        marks the shot active on the CTX_Manager node, updates all asset paths,
        applies the gaffer chain, and applies slate render-layer renderable flags.

        Requires Maya.

        Args:
            ep (str): Episode code.
            seq (str): Sequence code.
            shot (str): Shot code.
            scene_file (str|None): Optional scene file to open first.
            save (bool): If True, save the scene after applying.
            apply_paths (bool): If True, update asset file paths via NodeManager.
            apply_gaffer (bool): If True, apply gaffer chain to Maya lights.
            apply_slate (bool): If True, apply slate render-layer renderable flags
                via SlateResolver.apply_to_scene(). Restores originals if no slate
                found at shot or sequence level.

        Returns:
            dict: {
                'success': bool,
                'message': str,
                'output_file': str|None,
                'assets_updated': int,
                'gaffer_applied': bool,
                'slate_applied': bool,
            }
        """
        self._require_maya()
        import maya.cmds as cmds

        try:
            if scene_file:
                self._open_scene(scene_file)

            shot_node = self._find_shot_node(ep, seq, shot)

            # Deactivate all other shots, activate this one
            from core.nodes.wrappers import CTXShotNode, CTXManagerNode
            all_shots = CTXShotNode.list_all()
            for s in all_shots:
                if isinstance(s, str):
                    from core.nodes.wrappers.shot import CTXShotNode as _ShotCls
                    s = _ShotCls(s)
                try:
                    s.set_active(s.node_name == shot_node.node_name)
                except Exception:
                    pass

            # Record active shot on the manager node
            managers = CTXManagerNode.list_all()
            if managers:
                mgr = managers[0]
                if isinstance(mgr, str):
                    from core.nodes.wrappers.manager import CTXManagerNode as _MgrCls
                    mgr = _MgrCls(mgr)
                try:
                    shot_id = shot_node.get_shot_id()
                    mgr.set_active_shot_id(shot_id)
                except Exception:
                    pass

            # Update asset paths
            assets_updated = 0
            if apply_paths:
                from core.nodes import NodeManager
                nm = NodeManager()
                assets_updated = nm.update_shot_paths(
                    shot_node, self._get_config(), self._get_platform_config()
                )

            # Apply gaffer chain (shot gaffer → sequence gaffer → restore originals)
            gaffer_applied = False
            if apply_gaffer:
                try:
                    from core.nodes.wrappers.gaffer import CTXLightGafferNode
                    from core.nodes.wrappers.sequence import CTXSequenceNode
                    from core.gaffer.light_ops import LightOperations

                    active_gaffer = None
                    shot_gaffer_name = shot_node.get_gaffer()
                    if shot_gaffer_name:
                        active_gaffer = CTXLightGafferNode(shot_gaffer_name)
                    else:
                        seq_name = shot_node.get_parent_sequence()
                        if seq_name:
                            seq = CTXSequenceNode(seq_name)
                            seq_gaffer_name = seq.get_gaffer()
                            if seq_gaffer_name:
                                active_gaffer = CTXLightGafferNode(seq_gaffer_name)

                    if active_gaffer:
                        LightOperations.apply_gaffer_to_all_lights(active_gaffer)
                        gaffer_applied = True
                    else:
                        LightOperations.restore_originals()
                except Exception as exc:
                    logger.warning("set_active_shot: gaffer apply failed: %s", exc)

            # Apply slate render-layer renderable flags
            slate_applied = False
            if apply_slate:
                try:
                    from core.slate.resolver import SlateResolver
                    slate = SlateResolver._get_slate_for_node(shot_node)
                    if slate is not None:
                        SlateResolver.apply_to_scene(shot_node)
                        slate_applied = True
                    else:
                        SlateResolver.restore_originals()
                except Exception as exc:
                    logger.warning("set_active_shot: slate apply failed: %s", exc)

            output_file = None
            if save:
                cmds.file(save=True, force=True)
                output_file = scene_file

            return {
                'success': True,
                'message': 'Active shot set: %s_%s_%s' % (ep, seq, shot),
                'output_file': output_file,
                'assets_updated': assets_updated,
                'gaffer_applied': gaffer_applied,
                'slate_applied': slate_applied,
            }

        except Exception as exc:
            logger.exception("set_active_shot failed: %s", exc)
            return {
                'success': False,
                'message': str(exc),
                'output_file': None,
                'assets_updated': 0,
                'gaffer_applied': False,
            }

    def export_gaffer(self, ep, seq, shot, output_path, scene_file=None):
        """Export the gaffer chain for a shot to a JSON file.

        If scene_file is provided, opens it first. Otherwise operates on the
        currently-loaded Maya scene.

        Requires Maya.

        Args:
            ep (str): Episode code.
            seq (str): Sequence code.
            shot (str): Shot code.
            output_path (str): Path to write the .json file.
            scene_file (str|None): Optional scene file to open first.

        Returns:
            dict: {'success': bool, 'message': str, 'lights_exported': int}
        """
        self._require_maya()

        try:
            if scene_file:
                self._open_scene(scene_file)

            shot_node = self._find_shot_node(ep, seq, shot)

            from core.gaffer.serializer import GafferSerializer
            serializer = GafferSerializer()
            data = serializer.export_shot(shot_node, self._get_config())
            serializer.to_json(data, output_path)

            lights_count = sum(
                len(g.get('lights', [])) for g in data.get('gaffers', [])
            )
            return {
                'success': True,
                'message': 'Exported %d lights to %s' % (lights_count, output_path),
                'lights_exported': lights_count,
            }
        except Exception as exc:
            logger.exception("export_gaffer failed: %s", exc)
            return {
                'success': False,
                'message': str(exc),
                'lights_exported': 0,
            }

    def batch_render(self, shots, scene_file=None,
                     render_layers=None, start_frame=None, end_frame=None,
                     on_progress=None, dry_run=False, reserved_gpus=None):
        """Render multiple shots in batch using available GPUs.

        No Maya required for queuing. Maya required for prepare + render steps.

        Args:
            shots (list): List of (ep, seq, shot) tuples or dicts with ep/seq/shot keys.
            scene_file (str|None): Scene to open. None = current scene.
            render_layers (list[str]|None): Layers to render. None = all renderable.
            start_frame (int|None): Override start. None = from CTXShotNode.
            end_frame (int|None): Override end. None = from CTXShotNode.
            on_progress (callable|None): Called with (job, layer, status, message).
            dry_run (bool): If True, prepare scenes but do not render.
            reserved_gpus (int|None): GPUs to reserve. None = from config.

        Returns:
            dict: {
                'success': bool,
                'total': int,
                'done': int,
                'failed': int,
                'jobs': list[dict],
            }
        """
        from core.batch.render_queue import RenderQueue

        orig = None
        try:
            config = self._get_config()
            platform_config = self._get_platform_config()

            if reserved_gpus is not None:
                # Temporarily override reserved GPUs in config
                orig = config.data.get('batchRender', {}).get('reservedGpus', 1)
                config.data.setdefault('batchRender', {})['reservedGpus'] = reserved_gpus

            queue = RenderQueue(config, platform_config)

            for item in shots:
                if isinstance(item, dict):
                    ep = item['ep']
                    seq = item['seq']
                    shot = item['shot']
                else:
                    ep, seq, shot = item[0], item[1], item[2]
                queue.add_shot(
                    ep, seq, shot,
                    scene_file=scene_file,
                    start_frame=start_frame,
                    end_frame=end_frame,
                    render_layers=render_layers,
                )

            queue.start(on_progress=on_progress, dry_run=dry_run)
            queue.wait()

            summary = queue.get_summary()
            summary['success'] = summary['failed'] == 0

            return summary

        except Exception as exc:
            logger.exception("batch_render failed: %s", exc)
            return {
                'success': False,
                'total': len(shots),
                'done': 0,
                'failed': len(shots),
                'jobs': [],
            }

        finally:
            # Restore original reserved_gpus if we overrode it
            if reserved_gpus is not None and orig is not None:
                try:
                    config.data['batchRender']['reservedGpus'] = orig
                except Exception:
                    pass

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
            logger.warning("get_shot_slate_layers failed: %s", exc)
        return None

    def import_gaffer(self, ep, seq, shot, json_path, scene_file=None, save=True):
        """Load gaffer JSON and apply it to a shot in a Maya scene.

        Requires Maya.

        Args:
            ep (str): Episode code.
            seq (str): Sequence code.
            shot (str): Shot code.
            json_path (str): Path to the gaffer .json file.
            scene_file (str|None): Optional scene file to open first.
            save (bool): If True, save the scene after import.

        Returns:
            dict: {'success': bool, 'message': str, 'lights_imported': int}
        """
        self._require_maya()
        import maya.cmds as cmds

        try:
            if scene_file:
                self._open_scene(scene_file)

            shot_node = self._find_shot_node(ep, seq, shot)

            from core.gaffer.serializer import GafferSerializer
            serializer = GafferSerializer()
            data = serializer.from_json(json_path)
            count = serializer.import_shot(shot_node, data, self._get_config())

            if save:
                cmds.file(save=True, force=True)

            return {
                'success': True,
                'message': 'Imported %d lights' % count,
                'lights_imported': count,
            }
        except Exception as exc:
            logger.exception("import_gaffer failed: %s", exc)
            return {
                'success': False,
                'message': str(exc),
                'lights_imported': 0,
            }
