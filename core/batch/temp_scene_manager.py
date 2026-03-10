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
        self._entries = []
        self._load_manifest()

    def _load_manifest(self):
        """Load existing manifest from disk."""
        if os.path.exists(self._manifest_path):
            try:
                with open(self._manifest_path, 'r') as f:
                    self._entries = json.load(f)
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
