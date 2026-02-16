# -*- coding: utf-8 -*-
"""Asset scanner for discovering and registering assets from filesystem.

This module scans publish directories and creates CTX_Asset nodes for discovered assets.

Author: Context Variables Pipeline
Date: 2026-02-15
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import re
import logging

logger = logging.getLogger(__name__)


class AssetScanner(object):
    """Scanner for discovering assets from filesystem and creating CTX nodes.
    
    Example:
        >>> scanner = AssetScanner(config)
        >>> assets = scanner.scan_shot_assets(shot_node)
        >>> print("Found {} assets".format(len(assets)))
    """
    
    def __init__(self, config):
        """Initialize asset scanner.
        
        Args:
            config: ProjectConfig instance
        """
        self.config = config
    
    def scan_shot_assets(self, shot_node, departments=None):
        """Scan filesystem for assets and create CTX_Asset nodes.
        
        Args:
            shot_node: CTXShotNode instance
            departments (list, optional): List of departments to scan. 
                                         If None, scans all departments.
        
        Returns:
            list: List of created CTXAssetNode instances
        """
        from core.custom_nodes import CTXAssetNode
        
        if not self.config:
            logger.warning("No config available for asset scanning")
            return []
        
        # Get shot info
        ep = shot_node.get_ep_code()
        seq = shot_node.get_seq_code()
        shot = shot_node.get_shot_code()
        
        # Get departments to scan
        if departments is None:
            # Try to get from config, fallback to defaults
            try:
                if hasattr(self.config, 'get_token_values'):
                    departments = self.config.get_token_values('dept')
                else:
                    # Fallback: read directly from config data
                    departments = self.config.data.get('tokens', {}).get('dept', {}).get('values')

                # If still None, use defaults
                if not departments:
                    departments = ['anim', 'layout', 'fx', 'lighting']
            except Exception as e:
                logger.warning("Failed to get departments from config: %s", e)
                departments = ['anim', 'layout', 'fx', 'lighting']
        
        created_assets = []
        
        # Scan each department
        for dept in departments:
            dept_assets = self._scan_department(ep, seq, shot, dept, shot_node)
            created_assets.extend(dept_assets)
        
        logger.info("Created {} CTX_Asset nodes for shot {}_{}_{}".format(
            len(created_assets), ep, seq, shot))
        
        return created_assets
    
    def _scan_department(self, ep, seq, shot, dept, shot_node):
        """Scan a specific department for assets.
        
        Args:
            ep (str): Episode code
            seq (str): Sequence code
            shot (str): Shot code
            dept (str): Department name
            shot_node: CTXShotNode instance
        
        Returns:
            list: List of created CTXAssetNode instances
        """
        from core.custom_nodes import CTXAssetNode

        # Build publish path manually from config
        # Template: $projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish
        proj_root = self.config.get_root('projRoot') or 'V:/'
        project = self.config.get_project_code() or 'SWA'
        scene_base = self.config.get_static_path('sceneBase') or 'all/scene'

        publish_path = os.path.join(
            proj_root,
            project,
            scene_base,
            ep,
            seq,
            shot,
            dept,
            'publish'
        ).replace('\\', '/')
        
        if not os.path.exists(publish_path):
            logger.debug("Publish path does not exist: {}".format(publish_path))
            return []
        
        logger.info("Scanning department: {} at {}".format(dept, publish_path))

        # Find all version directories
        version_dirs = []
        for item in os.listdir(publish_path):
            item_path = os.path.join(publish_path, item)
            if os.path.isdir(item_path) and re.match(r'^v\d+$', item):
                version_dirs.append((item, item_path))

        if not version_dirs:
            logger.debug("No version directories found in {}".format(publish_path))
            return []

        # Sort versions (latest first)
        version_dirs.sort(reverse=True)
        logger.info("Found {} versions: {}".format(len(version_dirs), [v[0] for v in version_dirs]))

        # Track unique assets across ALL versions
        # Key: (asset_type, asset_name, variant) -> (latest_version, file_path)
        unique_assets = {}

        # Scan ALL versions to find all unique assets
        for version, version_path in version_dirs:
            all_files = os.listdir(version_path)
            logger.debug("Scanning version {} - found {} files".format(version, len(all_files)))

            for filename in all_files:
                if not filename.endswith(('.abc', '.rs', '.ma', '.mb', '.vdb', '.ass')):
                    continue

                # Parse filename: Ep04_sq0070_SH0140__CHAR_CatStompie_001.abc
                asset_info = self._parse_filename(filename)
                if not asset_info:
                    continue

                # Create unique key for this asset
                asset_key = (asset_info['type'], asset_info['name'], asset_info['variant'])

                # Track this asset with its latest version
                # Since versions are sorted latest first, first occurrence is the latest
                if asset_key not in unique_assets:
                    file_path = os.path.join(version_path, filename).replace('\\\\', '/')
                    unique_assets[asset_key] = {
                        'version': version,
                        'file_path': file_path,
                        'info': asset_info
                    }
                    logger.debug("Found asset: {} {} {} in version {}".format(
                        asset_info['type'], asset_info['name'], asset_info['variant'], version))

        logger.info("Found {} unique assets across all versions".format(len(unique_assets)))

        # Now create CTX_Asset nodes for all unique assets
        created_assets = []
        existing_assets = shot_node.get_assets()

        for asset_key, asset_data in unique_assets.items():
            asset_type, asset_name, variant = asset_key
            asset_info = asset_data['info']

            # Check if asset already exists
            asset_exists = False
            for existing in existing_assets:
                if (existing.get_asset_type() == asset_type and
                    existing.get_asset_name() == asset_name and
                    existing.get_variant() == variant and
                    existing.get_department() == dept):
                    asset_exists = True
                    logger.info("Asset already exists, skipping: {} {} {}".format(
                        asset_type, asset_name, variant))
                    break

            if asset_exists:
                continue

            # Create CTX_Asset node
            logger.info("Creating CTX_Asset node: {} {} {} (version: {})".format(
                asset_type, asset_name, variant, asset_data['version']))

            asset_node = CTXAssetNode.create_asset(
                asset_type,
                asset_name,
                variant,
                shot_node
            )

            # Set additional attributes
            asset_node.set_department(dept)
            asset_node.set_version(asset_data['version'])

            # Store template path from config (token-based path resolution)
            # Special handling for cameras: use custom template without $assetType and $variant
            if asset_type == 'CAM':
                # Camera template: no type prefix, no variant in filename
                # Build custom template: $projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish/$ver/$ep_$seq_$shot__$assetName.$ext
                base_template = self.config.get_template('assetPath')
                if base_template:
                    # Replace the filename portion to exclude $assetType and $variant
                    # Original: ...$ver/$ep_$seq_$shot__$assetType_$assetName_$variant.$ext
                    # Camera:   ...$ver/$ep_$seq_$shot__$assetName.$ext
                    asset_path_template = base_template.replace(
                        '$ep_$seq_$shot__$assetType_$assetName_$variant.$ext',
                        '$ep_$seq_$shot__$assetName.$ext'
                    )
                    logger.info("Using camera-specific template: %s", asset_path_template)
                else:
                    asset_path_template = None
            else:
                # Standard assets: use default template
                asset_path_template = self.config.get_template('assetPath')

            if asset_path_template:
                asset_node.set_template(asset_path_template)
            else:
                logger.warning("No 'assetPath' template in config, storing absolute path")

            # Store file extension
            asset_node.set_extension(asset_data['info']['ext'])

            # Cache the resolved file_path (for display / initial state)
            asset_node.set_file_path(asset_data['file_path'])

            # Auto-link to Maya reference by namespace
            # The namespace attribute (e.g., 'CHAR_CatStompie_001') matches
            # the Maya reference namespace exactly
            from core.ctx_converter import CTXConverter
            converter = CTXConverter()
            linked = converter.link_ctx_asset_to_scene(asset_node.node_name)
            if linked:
                logger.info("Auto-linked {} to Maya reference by namespace".format(
                    asset_node.node_name))
            else:
                logger.info("No matching Maya reference found for {} (will link when asset is loaded)".format(
                    asset_node.node_name))

            created_assets.append(asset_node)
            logger.info("Created asset node: {} for file: {}".format(
                asset_node.node_name, asset_data['file_path']))

        logger.info("Created {} assets in department {}".format(len(created_assets), dept))
        return created_assets

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
            logger.debug("Filename does not match pattern (missing __): {}".format(filename))
            return None

        shot_part, asset_part = parts

        # Check if this is a camera asset (ends with _camera)
        if asset_part.endswith('_camera'):
            # Camera format: SWA_Ep04_SH0170_camera
            # Extract: type=CAM, name=full_name, variant=001
            return {
                'type': 'CAM',
                'name': asset_part,  # Full name: SWA_Ep04_SH0170_camera
                'variant': '001',    # Default variant for cameras
                'ext': ext.lstrip('.')
            }

        # Parse standard asset part: CHAR_CatStompie_001
        asset_parts = asset_part.split('_')
        if len(asset_parts) < 3:
            logger.debug("Asset part does not have enough components: {}".format(asset_part))
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

