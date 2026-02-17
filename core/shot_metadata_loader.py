# -*- coding: utf-8 -*-
"""Shot Metadata Loader - Load shot metadata from JSON sidecar files.

This module handles loading shot metadata (frame range, fps, etc.) from
JSON sidecar files stored alongside Maya scene files.

Author: Context Variables Pipeline Team
Date: 2026-02-17
"""

from __future__ import absolute_import, division, print_function

import json
import logging
import os

logger = logging.getLogger(__name__)


class ShotMetadataLoader(object):
    """Load shot metadata from JSON sidecar files.
    
    This class reads JSON files stored alongside shot directories and
    extracts metadata like frame range, fps, etc. based on configuration
    from ProjectConfig.
    
    Example:
        >>> from config.project_config import ProjectConfig
        >>> from core.shot_metadata_loader import ShotMetadataLoader
        >>> 
        >>> config = ProjectConfig('project_configs/ctx_config.json')
        >>> loader = ShotMetadataLoader(config)
        >>> 
        >>> metadata = loader.load_all_metadata('Ep04_sq0070_SH0180', 'v:/SWA/all/scene/Ep04/sq0070/SH0180')
        >>> print(metadata)
        {'frame_range': (1001, 1030), 'fps': 24.0}
    """
    
    def __init__(self, config):
        """Initialize with ProjectConfig instance.
        
        Args:
            config (ProjectConfig): Project configuration instance
        """
        self.config = config
        self.metadata_config = config.get_shot_metadata_config()
        
        if not self.metadata_config:
            logger.warning("No shotMetadata configuration found in config")
    
    def build_json_path(self, shot_id, shot_root_path):
        """Build path to JSON file based on config.

        Args:
            shot_id (str): Shot ID (e.g., "Ep04_sq0070_SH0180")
            shot_root_path (str): Shot root directory path

        Returns:
            str: Full path to JSON file

        Example:
            >>> loader.build_json_path('Ep04_sq0070_SH0180', 'v:/SWA/all/scene/Ep04/sq0070/SH0180')
            'v:/SWA/all/scene/Ep04/sq0070/SH0180/.Ep04_sq0070_SH0180.json'
        """
        logger.info("DEBUG: build_json_path called with shot_id=%s, shot_root_path=%s", shot_id, shot_root_path)

        if not self.metadata_config:
            logger.warning("DEBUG: metadata_config is None")
            return None

        if not shot_root_path:
            logger.warning("DEBUG: shot_root_path is None or empty")
            return None

        filename_pattern = self.metadata_config.get('filenamePattern', '.{shot_id}.json')
        logger.info("DEBUG: filenamePattern: %s", filename_pattern)

        filename = filename_pattern.replace('{shot_id}', shot_id)
        logger.info("DEBUG: filename after replacement: %s", filename)

        json_path = os.path.join(shot_root_path, filename)
        logger.info("DEBUG: Final json_path: %s", json_path)

        return json_path
    
    def load_frame_range(self, json_path):
        """Load frame range from JSON file.
        
        Args:
            json_path (str): Path to JSON file
            
        Returns:
            tuple: (start_frame, end_frame) or None if not found
        """
        if not os.path.exists(json_path):
            logger.debug("JSON file not found: %s", json_path)
            return None
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)

            logger.info("DEBUG: Loaded JSON data, top-level keys: %s", list(data.keys()))

            field_mapping = self.metadata_config.get('fieldMapping', {})
            frame_range_config = field_mapping.get('frameRange', {})

            json_field = frame_range_config.get('jsonField', 'sequence_frames')
            parse_format = frame_range_config.get('parseFormat', 'range')
            default_start = frame_range_config.get('defaultStart', 1001)
            default_end = frame_range_config.get('defaultEnd', 1100)

            logger.info("DEBUG: json_field='%s', parse_format='%s'", json_field, parse_format)

            if parse_format == 'nested':
                # Nested object format: {"shot_info": {"start_frame": 1001, "end_frame": 1030}}
                start_field = frame_range_config.get('startField', 'start_frame')
                end_field = frame_range_config.get('endField', 'end_frame')

                logger.info("DEBUG: Looking for nested field '%s' with start='%s', end='%s'",
                           json_field, start_field, end_field)

                if json_field not in data:
                    logger.warning("DEBUG: Field '%s' not found in JSON. Available keys: %s",
                                  json_field, list(data.keys()))
                    return None

                nested_obj = data[json_field]
                logger.info("DEBUG: Found nested_obj, type=%s, keys=%s",
                           type(nested_obj).__name__,
                           list(nested_obj.keys()) if isinstance(nested_obj, dict) else 'N/A')

                if not isinstance(nested_obj, dict):
                    logger.warning("Field '%s' is not a dict: %s", json_field, type(nested_obj))
                    return None

                start = nested_obj.get(start_field, default_start)
                end = nested_obj.get(end_field, default_end)

                logger.info("DEBUG: Extracted start=%s, end=%s", start, end)
                logger.info("DEBUG: load_frame_range returned: ({}, {})".format(start, end))
                return (int(start), int(end))

            elif parse_format == 'range':
                # Parse "1001-1030" format
                if json_field not in data:
                    logger.debug("Field '%s' not found in JSON", json_field)
                    return None

                value = data[json_field]

                if isinstance(value, (str, unicode if 'unicode' in dir(__builtins__) else str)):
                    value_str = str(value).strip()
                    if '-' in value_str:
                        parts = value_str.split('-')
                        if len(parts) == 2:
                            try:
                                start = int(parts[0].strip())
                                end = int(parts[1].strip())
                                logger.info("Loaded frame range from JSON: {}-{}".format(start, end))
                                return (start, end)
                            except ValueError:
                                logger.warning("Failed to parse frame range: %s", value_str)
                                return None

            elif parse_format == 'separate':
                # Separate start/end fields at root level
                start_field = frame_range_config.get('startField', 'start_frame')
                end_field = frame_range_config.get('endField', 'end_frame')

                start = data.get(start_field, default_start)
                end = data.get(end_field, default_end)

                return (int(start), int(end))

            return None
            
        except Exception as e:
            logger.warning("Failed to load frame range from %s: %s", json_path, e)
            return None
    
    def load_fps(self, json_path):
        """Load FPS from JSON file.
        
        Args:
            json_path (str): Path to JSON file
            
        Returns:
            float: FPS value or None if not found
        """
        if not os.path.exists(json_path):
            return None
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)

            field_mapping = self.metadata_config.get('fieldMapping', {})
            fps_config = field_mapping.get('fps', {})

            json_field = fps_config.get('jsonField', 'fps')
            default_fps = fps_config.get('default', 24.0)

            if json_field not in data:
                logger.debug("Field '%s' not found in JSON", json_field)
                return None

            fps_value = data[json_field]

            try:
                fps = float(fps_value)
                logger.info("Loaded FPS from JSON: %s", fps)
                return fps
            except (ValueError, TypeError):
                logger.warning("Failed to parse FPS value: %s", fps_value)
                return None

        except Exception as e:
            logger.warning("Failed to load FPS from %s: %s", json_path, e)
            return None

    def load_all_metadata(self, shot_id, shot_root_path):
        """Load all metadata for a shot.

        Args:
            shot_id (str): Shot ID (e.g., "Ep04_sq0070_SH0180")
            shot_root_path (str): Shot root directory path

        Returns:
            dict: Dictionary with loaded metadata
                  {'frame_range': (start, end), 'fps': 24.0, ...}
                  Empty dict if no metadata found
        """
        logger.info("DEBUG: load_all_metadata called with shot_id=%s, shot_root_path=%s", shot_id, shot_root_path)

        if not self.metadata_config:
            logger.warning("DEBUG: Shot metadata not configured (metadata_config is None)")
            return {}

        json_path = self.build_json_path(shot_id, shot_root_path)
        logger.info("DEBUG: Built JSON path: %s", json_path)

        if not json_path:
            logger.warning("DEBUG: json_path is None")
            return {}

        if not os.path.exists(json_path):
            logger.warning("DEBUG: JSON file does NOT exist: %s", json_path)
            return {}

        logger.info("DEBUG: JSON file EXISTS, loading metadata from: %s", json_path)

        metadata = {}

        # Load frame range
        frame_range = self.load_frame_range(json_path)
        logger.info("DEBUG: load_frame_range returned: %s", frame_range)
        if frame_range:
            metadata['frame_range'] = frame_range

        # Load FPS
        fps = self.load_fps(json_path)
        logger.info("DEBUG: load_fps returned: %s", fps)
        if fps:
            metadata['fps'] = fps

        logger.info("DEBUG: Final metadata dict: %s", metadata)
        return metadata

