# -*- coding: utf-8 -*-
"""Asset scanner for discovering and registering assets from filesystem.

This module scans publish directories and creates CTX_Asset nodes for discovered assets.
Department priority is applied so that the same asset in multiple departments produces
exactly ONE CTX_Asset node, using the highest-priority department.

Author: Context Variables Pipeline
Date: 2026-02-15
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import re

from core.logging_config import get_logger
from core.renderers import get_active_renderer, get_preferred_extensions

logger = get_logger(__name__)


class AssetScanner(object):
    """Scanner for discovering assets from filesystem and creating CTX nodes.

    Example:
        >>> scanner = AssetScanner(config)
        >>> assets = scanner.scan_shot_assets(shot_node)
        >>> print("Found {} assets".format(len(assets)))
    """

    def __init__(self, config, layer_manager=None):
        """Initialize asset scanner.

        Args:
            config: ProjectConfig instance
            layer_manager (DisplayLayerManager, optional): Display layer manager for assigning assets to layers
        """
        self.config = config
        self.layer_manager = layer_manager

    def scan_shot_assets(self, shot_node, departments=None):
        """Scan filesystem for assets and create CTX_Asset nodes.

        Uses department priority to create ONE CTX_Asset node per unique asset
        identity (type, name, variant). When the same asset exists in multiple
        departments the highest-priority department wins (priority defined in
        config deptPriority, index 0 = highest priority).

        Args:
            shot_node: CTXShotNode instance
            departments (list, optional): Departments to scan.
                                         If None, all departments from config are used.

        Returns:
            list: List of created CTXAssetNode instances
        """
        if not self.config:
            logger.warning("No config available for asset scanning")
            return []

        ep = shot_node.get_ep_code()
        seq = shot_node.get_seq_code()
        shot = shot_node.get_shot_code()

        # Resolve departments list
        if departments is None:
            try:
                if hasattr(self.config, 'get_token_values'):
                    departments = self.config.get_token_values('dept')
                else:
                    departments = self.config.data.get('tokens', {}).get('dept', {}).get('values')
                if not departments:
                    departments = ['anim', 'layout', 'fx', 'lighting']
            except Exception as e:
                logger.warning("Failed to get departments from config: %s", e)
                departments = ['anim', 'layout', 'fx', 'lighting']

        # Resolve department priority (index 0 = highest priority)
        if hasattr(self.config, 'get_dept_priority'):
            priority_order = self.config.get_dept_priority()
        else:
            priority_order = ['lighting', 'fx', 'cfx', 'anim', 'layout']
        priority_rank = {dept: i for i, dept in enumerate(priority_order)}

        # PASS 1: Discover assets in every department.
        # Iterate from LOWEST priority to HIGHEST so later entries overwrite earlier ones.
        # Result: each asset identity (type, name, variant) maps to its winning dept.
        depts_scan_order = sorted(
            departments,
            key=lambda d: priority_rank.get(d, len(priority_order)),
            reverse=True,  # highest index (lowest priority) first
        )

        # master: {(type, name, variant): {'dept': str, 'version': str, 'file_path': str, 'info': dict}}
        master_assets = {}
        for dept in depts_scan_order:
            discovered = self._discover_assets_in_dept(ep, seq, shot, dept)
            for asset_key, asset_data in discovered.items():
                entry = dict(asset_data)
                entry['dept'] = dept
                master_assets[asset_key] = entry

        logger.info(
            "Priority scan: %d unique assets for %s_%s_%s across %d departments",
            len(master_assets), ep, seq, shot, len(departments)
        )

        # PASS 2: Create one CTX_Asset node per winning (type, name, variant) entry.
        created_assets = []
        existing_shot_assets = shot_node.get_assets()

        for asset_key, asset_data in master_assets.items():
            asset_type, asset_name, variant = asset_key

            # Check by identity only (no dept) -- any previously created node blocks duplicates
            already_linked = any(
                a.get_asset_type() == asset_type and
                a.get_asset_name() == asset_name and
                a.get_variant() == variant
                for a in existing_shot_assets
            )
            if already_linked:
                logger.info(
                    "Asset already linked to this shot, skipping: %s %s %s",
                    asset_type, asset_name, variant
                )
                continue

            new_node = self._create_ctx_asset(
                shot_node, shot,
                asset_data['dept'], asset_type, asset_name, variant,
                asset_data['version'], asset_data['file_path'], asset_data['info'],
                len(created_assets)
            )
            if new_node:
                created_assets.append(new_node)

        logger.info(
            "Created %d CTX_Asset nodes for shot %s_%s_%s",
            len(created_assets), ep, seq, shot
        )
        return created_assets

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _discover_assets_in_dept(self, ep, seq, shot, dept):
        """Scan a department publish directory and return discovered assets.

        Pure filesystem discovery -- does NOT create CTX nodes.

        Args:
            ep (str): Episode code
            seq (str): Sequence code
            shot (str): Shot code
            dept (str): Department name

        Returns:
            dict: {(asset_type, asset_name, variant): {'version': str, 'file_path': str, 'info': dict}}
        """
        proj_root = self.config.get_root('projRoot') or 'V:/'
        project = self.config.get_project_code() or 'SWA'
        scene_base = self.config.get_static_path('sceneBase') or 'all/scene'

        publish_path = os.path.join(
            proj_root, project, scene_base, ep, seq, shot, dept, 'publish'
        ).replace('\\', '/')

        if not os.path.exists(publish_path):
            logger.debug("Publish path does not exist: %s", publish_path)
            return {}

        logger.info("Scanning department: %s at %s", dept, publish_path)

        # Collect version directories, sort latest first
        ver_pattern = self.config.get_token_pattern('ver') if self.config else None
        ver_pattern = ver_pattern or r'^v\d+$'
        version_dirs = []
        for item in os.listdir(publish_path):
            item_path = os.path.join(publish_path, item)
            if os.path.isdir(item_path) and re.match(ver_pattern, item):
                version_dirs.append((item, item_path))

        if not version_dirs:
            logger.debug("No version directories found in %s", publish_path)
            return {}

        version_dirs.sort(reverse=True)
        logger.info("Found %d versions: %s", len(version_dirs), [v[0] for v in version_dirs])

        # First occurrence per key = latest version (versions sorted latest first)
        config_exts = self.config.get_extensions() if self.config else []
        if config_exts:
            extensions = tuple('.' + e for e in config_exts)
        else:
            extensions = ('.abc', '.rs', '.ma', '.mb', '.vdb', '.ass')
        # Determine renderer-preferred extension order once (outside version loop)
        try:
            _renderer = get_active_renderer()
            _preferred = get_preferred_extensions(_renderer, self.config)
        except Exception:
            _renderer = 'unknown'
            _preferred = []

        def _ext_rank(fname):
            ext = os.path.splitext(fname)[1].lstrip('.')
            try:
                return _preferred.index(ext)
            except ValueError:
                return len(_preferred)

        unique_assets = {}
        for version, version_path in version_dirs:
            filenames = sorted(os.listdir(version_path), key=_ext_rank)
            for filename in filenames:
                if not filename.endswith(extensions):
                    continue
                asset_info = self._parse_filename(filename)
                if not asset_info:
                    continue
                asset_key = (asset_info['type'], asset_info['name'], asset_info['variant'])
                if asset_key not in unique_assets:
                    file_path = os.path.join(version_path, filename).replace('\\\\', '/')
                    unique_assets[asset_key] = {
                        'version': version,
                        'file_path': file_path,
                        'info': asset_info,
                    }
                    logger.debug(
                        "Found asset: %s %s %s in version %s",
                        asset_info['type'], asset_info['name'], asset_info['variant'], version
                    )

        logger.info("Found %d unique assets in department %s", len(unique_assets), dept)
        return unique_assets

    def _create_ctx_asset(self, shot_node, shot_code, dept,
                          asset_type, asset_name, variant,
                          version, file_path, asset_info, asset_index):
        """Create a single CTX_Asset node and link it to the shot.

        Args:
            shot_node: CTXShotNode instance
            shot_code (str): Shot code string (e.g. 'SH0170')
            dept (str): Winning department
            asset_type (str): Asset type code (e.g. 'CHAR')
            asset_name (str): Asset name
            variant (str): Variant string (e.g. '001')
            version (str): Version string (e.g. 'v003')
            file_path (str): Resolved file path
            asset_info (dict): Parsed filename info dict (must contain 'ext')
            asset_index (int): Zero-based index for log messages

        Returns:
            CTXAssetNode or None
        """
        from core.nodes.wrappers import CTXAssetNode

        logger.info(
            "Creating CTX_Asset node: %s %s %s (dept: %s, version: %s)",
            asset_type, asset_name, variant, dept, version
        )

        asset_node = CTXAssetNode.create(
            asset_type=asset_type,
            asset_name=asset_name,
            variant=variant,
            namespace='{}_{}_{}'.format(asset_type, asset_name, variant),
            shot_code=shot_code
        )
        shot_node.add_asset(asset_node)

        asset_node.set_department(dept)
        asset_node.set_version(version)

        # Resolve template path (camera assets use a simplified template)
        if asset_type == 'CAM':
            base_template = self.config.get_template('assetPath')
            if base_template:
                asset_path_template = base_template.replace(
                    '$ep_$seq_$shot__$assetType_$assetName_$variant.$ext',
                    '$ep_$seq_$shot__$assetName.$ext'
                )
                logger.info("Using camera-specific template: %s", asset_path_template)
            else:
                asset_path_template = None
        else:
            asset_path_template = self.config.get_template('assetPath')

        if asset_path_template:
            asset_node.set_template(asset_path_template)
        else:
            logger.warning("No 'assetPath' template in config, storing absolute path")

        asset_node.set_extension(asset_info['ext'])
        asset_node.set_file_path(file_path)

        # Link to matching Maya reference node(s) by namespace
        from core.ctx_converter import CTXConverter
        converter = CTXConverter()
        namespace_val = asset_node.get_namespace()
        logger.info("=" * 80)
        logger.info(
            "ASSET #%d - Linking all CTX_Asset nodes for namespace '%s'",
            asset_index + 1, namespace_val
        )
        logger.info("=" * 80)
        linked_count = converter.link_all_by_namespace(namespace_val)
        linked = linked_count > 0

        if linked:
            logger.info("+" * 80)
            logger.info("DISPLAY LAYER ASSIGNMENT FOR ASSET #%d", asset_index + 1)
            logger.info("  Asset node: %s", asset_node.node_name)
            logger.info("  Namespace: %s", namespace_val)
            logger.info("  Layer manager: %s", self.layer_manager)
            logger.info("+" * 80)

            if self.layer_manager:
                logger.info("Layer manager available - assigning to display layer...")
                try:
                    logger.info(
                        "CALLING assign_to_layer_from_ctx_asset(%s, %s)",
                        asset_node.node_name, shot_node.node_name
                    )
                    self.layer_manager.assign_to_layer_from_ctx_asset(asset_node, shot_node)
                    logger.info("SUCCESS! Assigned %s to display layer", asset_node.node_name)
                except Exception as e:
                    logger.error("FAILED to assign %s to layer: %s", asset_node.node_name, e)
                    import traceback
                    logger.error("Traceback: %s", traceback.format_exc())
            else:
                logger.warning("No layer_manager available")

            logger.info("+" * 80)
        else:
            logger.info(
                "No matching Maya reference found for %s (will link when asset is loaded)",
                asset_node.node_name
            )

        logger.info("Created asset node: %s for file: %s", asset_node.node_name, file_path)
        return asset_node

    def _parse_filename(self, filename):
        """Parse asset filename to extract metadata.

        Expected formats:
        1. Standard: Ep04_sq0070_SH0140__CHAR_CatStompie_001.abc
           Pattern: {ep}_{seq}_{shot}__{assetType}_{assetName}_{variant}.{ext}

        2. Camera: Ep04_sq0070_SH0170__SWA_Ep04_SH0170_camera.abc
           Pattern: {ep}_{seq}_{shot}__{project}_{ep}_{shot}_camera.{ext}

        Args:
            filename (str): Asset filename

        Returns:
            dict: Asset info with keys: type, name, variant, ext
                  Returns None if parsing fails
        """
        # Remove extension
        name_part, ext = os.path.splitext(filename)

        # Split by double underscore to separate shot from asset
        parts = name_part.split('__')
        if len(parts) != 2:
            logger.debug("Filename does not match pattern (missing __): %s", filename)
            return None

        shot_part, asset_part = parts

        # Check if this is a camera asset (ends with camera suffix)
        cam_suffix = self.config.get_camera_file_suffix() if self.config else '_camera'
        if asset_part.endswith(cam_suffix):
            return {
                'type': 'CAM',
                'name': asset_part,   # Full name: SWA_Ep04_SH0170_camera
                'variant': '001',     # Default variant for cameras
                'ext': ext.lstrip('.')
            }

        # Parse standard asset part: CHAR_CatStompie_001
        asset_parts = asset_part.split('_')
        if len(asset_parts) < 3:
            logger.debug("Asset part does not have enough components: %s", asset_part)
            return None

        asset_type = asset_parts[0]
        variant = asset_parts[-1]
        asset_name = '_'.join(asset_parts[1:-1])

        return {
            'type': asset_type,
            'name': asset_name,
            'variant': variant,
            'ext': ext.lstrip('.')
        }
