# -*- coding: utf-8 -*-
"""Shot Metadata Loader - Load shot metadata from JSON sidecar files.

This module handles loading shot metadata (frame range, fps, etc.) from
JSON sidecar files stored alongside Maya scene files, and writing a custom
frame range back in the same format.

Author: Context Variables Pipeline Team
Date: 2026-02-17
"""

from __future__ import absolute_import, division, print_function

import collections
import json
import logging
import os
from core.compat import string_types

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
        logger.debug("build_json_path called with shot_id=%s, shot_root_path=%s", shot_id, shot_root_path)

        if not self.metadata_config:
            logger.debug("metadata_config is None")
            return None

        if not shot_root_path:
            logger.debug("shot_root_path is None or empty")
            return None

        filename_pattern = self.metadata_config.get('filenamePattern', '.{shot_id}.json')
        logger.debug("filenamePattern: %s", filename_pattern)

        filename = filename_pattern.replace('{shot_id}', shot_id)
        logger.debug("filename after replacement: %s", filename)

        json_path = os.path.join(shot_root_path, filename)
        logger.debug("Final json_path: %s", json_path)

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

            logger.debug("Loaded JSON data, top-level keys: %s", list(data.keys()))

            field_mapping = self.metadata_config.get('fieldMapping', {})
            frame_range_config = field_mapping.get('frameRange', {})

            json_field = frame_range_config.get('jsonField', 'sequence_frames')
            parse_format = frame_range_config.get('parseFormat', 'range')
            default_start = frame_range_config.get('defaultStart', 1001)
            default_end = frame_range_config.get('defaultEnd', 1100)

            logger.debug("json_field='%s', parse_format='%s'", json_field, parse_format)

            if parse_format == 'nested':
                # Nested object format: {"shot_info": {"start_frame": 1001, "end_frame": 1030}}
                start_field = frame_range_config.get('startField', 'start_frame')
                end_field = frame_range_config.get('endField', 'end_frame')

                logger.debug("Looking for nested field '%s' with start='%s', end='%s'",
                           json_field, start_field, end_field)

                if json_field not in data:
                    logger.debug("Field '%s' not found in JSON. Available keys: %s",
                                  json_field, list(data.keys()))
                    return None

                nested_obj = data[json_field]
                logger.debug("Found nested_obj, type=%s, keys=%s",
                           type(nested_obj).__name__,
                           list(nested_obj.keys()) if isinstance(nested_obj, dict) else 'N/A')

                if not isinstance(nested_obj, dict):
                    logger.warning("Field '%s' is not a dict: %s", json_field, type(nested_obj))
                    return None

                start = nested_obj.get(start_field, default_start)
                end = nested_obj.get(end_field, default_end)

                logger.debug("Extracted start=%s, end=%s", start, end)
                logger.debug("load_frame_range returned: ({}, {})".format(start, end))
                return (int(start), int(end))

            elif parse_format == 'range':
                # Parse "1001-1030" format
                if json_field not in data:
                    logger.debug("Field '%s' not found in JSON", json_field)
                    return None

                value = data[json_field]

                if isinstance(value, string_types):
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
        logger.debug("load_all_metadata called with shot_id=%s, shot_root_path=%s", shot_id, shot_root_path)

        if not self.metadata_config:
            logger.debug("Shot metadata not configured (metadata_config is None)")
            return {}

        json_path = self.build_json_path(shot_id, shot_root_path)
        logger.debug("Built JSON path: %s", json_path)

        if not json_path:
            logger.debug("json_path is None")
            return {}

        if not os.path.exists(json_path):
            logger.debug("JSON file does NOT exist: %s", json_path)
            return {}

        logger.debug("JSON file EXISTS, loading metadata from: %s", json_path)

        metadata = {}

        # Load frame range
        frame_range = self.load_frame_range(json_path)
        logger.debug("load_frame_range returned: %s", frame_range)
        if frame_range:
            metadata['frame_range'] = frame_range

        # Load FPS
        fps = self.load_fps(json_path)
        logger.debug("load_fps returned: %s", fps)
        if fps:
            metadata['fps'] = fps

        logger.debug("Final metadata dict: %s", metadata)
        return metadata

    def save_frame_range(self, json_path, start, end, fps=None):
        """Write a frame range to a shot JSON, in the format load_frame_range reads.

        An existing file keeps everything except the start and end frame: its
        other keys, including fps, are left untouched.  A missing file is
        created with the frame range and, when given, fps.  The shot folder
        itself is never created -- a missing folder means the path resolved
        somewhere unexpected.

        Args:
            json_path (str): Path to the shot JSON file.
            start (int): Start frame.
            end (int): End frame.
            fps (float): Written only when the file is being created.

        Returns:
            bool: True when the file was created, False when it was updated.

        Raises:
            ValueError: No shotMetadata config, end before start, or the
                existing file is not a JSON object in the expected shape.
            IOError: The shot folder does not exist.
        """
        if not self.metadata_config:
            raise ValueError("No shotMetadata configuration found in config")

        start = int(start)
        end = int(end)
        if end < start:
            raise ValueError(
                "End frame {} is before start frame {}".format(end, start))

        folder = os.path.dirname(json_path)
        if folder and not os.path.isdir(folder):
            raise IOError("Shot folder does not exist: {}".format(folder))

        created = not os.path.exists(json_path)
        if created:
            data = collections.OrderedDict()
        else:
            # Never rewrite a file that cannot be read back: that would
            # destroy whatever else it holds.
            with open(json_path, 'r') as f:
                data = json.load(f, object_pairs_hook=collections.OrderedDict)
            if not isinstance(data, dict):
                raise ValueError(
                    "Shot JSON is not an object: {}".format(json_path))

        field_mapping = self.metadata_config.get('fieldMapping', {})
        frame_range_config = field_mapping.get('frameRange', {})
        json_field = frame_range_config.get('jsonField', 'sequence_frames')
        parse_format = frame_range_config.get('parseFormat', 'range')
        start_field = frame_range_config.get('startField', 'start_frame')
        end_field = frame_range_config.get('endField', 'end_frame')

        if parse_format == 'nested':
            nested_obj = data.get(json_field)
            if nested_obj is None:
                nested_obj = collections.OrderedDict()
                data[json_field] = nested_obj
            elif not isinstance(nested_obj, dict):
                raise ValueError("Field '{}' in {} is not an object".format(
                    json_field, json_path))
            nested_obj[start_field] = start
            nested_obj[end_field] = end
        elif parse_format == 'range':
            data[json_field] = '{}-{}'.format(start, end)
        elif parse_format == 'separate':
            data[start_field] = start
            data[end_field] = end
        else:
            raise ValueError(
                "Unknown frameRange parseFormat '{}'".format(parse_format))

        if created and fps is not None:
            fps_field = field_mapping.get('fps', {}).get('jsonField', 'fps')
            data[fps_field] = float(fps)

        with open(json_path, 'w') as f:
            # Explicit separators: Python 2's default leaves a trailing space
            # after every comma when indenting.
            f.write(json.dumps(data, indent=4, separators=(',', ': ')))

        logger.info("%s shot JSON %s: frame range %d-%d",
                    'Created' if created else 'Updated', json_path, start, end)
        return created

    def save_shot_frame_range(self, shot_id, shot_root_path, start, end,
                              fps=None):
        """Write a shot's frame range to the JSON path built from config.

        Args:
            shot_id (str): Shot ID (e.g., "Ep04_sq0070_SH0180")
            shot_root_path (str): Shot root directory path
            start (int): Start frame
            end (int): End frame
            fps (float): Written only when the file is being created

        Returns:
            tuple: (json_path, created)

        Raises:
            ValueError, IOError: See save_frame_range; also ValueError when the
                JSON path cannot be built.
        """
        json_path = self.build_json_path(shot_id, shot_root_path)
        if not json_path:
            raise ValueError(
                "Cannot build shot JSON path for {}".format(shot_id))
        created = self.save_frame_range(json_path, start, end, fps=fps)
        return json_path, created

