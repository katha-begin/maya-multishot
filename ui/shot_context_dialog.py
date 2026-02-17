# -*- coding: utf-8 -*-
"""Shot Context Manager Dialog - Edit shot properties and frame range.

This dialog allows editing shot-specific properties:
- Frame range (start/end)
- FPS
- Handles
- Frame offset
- Camera assignment (future)
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging

try:
    from PySide6 import QtWidgets, QtCore
except ImportError:
    from PySide2 import QtWidgets, QtCore

logger = logging.getLogger(__name__)


class ShotContextDialog(QtWidgets.QDialog):
    """Dialog for editing shot context properties."""

    def __init__(self, shot_node, parent=None):
        """Initialize shot context dialog.

        Args:
            shot_node (CTXShotNode): Shot node to edit
            parent (QWidget, optional): Parent widget
        """
        super(ShotContextDialog, self).__init__(parent)
        self._shot_node = shot_node
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        """Setup dialog UI."""
        shot_id = self._shot_node.get_shot_id()
        self.setWindowTitle("Shot Context Manager - {}".format(shot_id))
        self.setModal(True)
        self.resize(400, 300)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Shot info label
        info_label = QtWidgets.QLabel("Edit shot properties for: <b>{}</b>".format(shot_id))
        layout.addWidget(info_label)

        # Form layout for properties
        form_layout = QtWidgets.QFormLayout()
        form_layout.setSpacing(10)

        # Frame range
        frame_range_layout = QtWidgets.QHBoxLayout()
        self.start_frame_spin = QtWidgets.QSpinBox()
        self.start_frame_spin.setRange(1, 999999)
        self.start_frame_spin.setValue(1001)
        frame_range_layout.addWidget(self.start_frame_spin)

        frame_range_layout.addWidget(QtWidgets.QLabel(" to "))

        self.end_frame_spin = QtWidgets.QSpinBox()
        self.end_frame_spin.setRange(1, 999999)
        self.end_frame_spin.setValue(1100)
        frame_range_layout.addWidget(self.end_frame_spin)

        frame_range_layout.addStretch()
        form_layout.addRow("Frame Range:", frame_range_layout)

        # FPS
        self.fps_combo = QtWidgets.QComboBox()
        self.fps_combo.addItems(["23.976", "24", "25", "29.97", "30", "60"])
        self.fps_combo.setEditable(True)
        form_layout.addRow("FPS:", self.fps_combo)

        # Handles
        self.handles_spin = QtWidgets.QSpinBox()
        self.handles_spin.setRange(0, 100)
        self.handles_spin.setValue(10)
        form_layout.addRow("Handles:", self.handles_spin)

        # Frame offset
        self.offset_spin = QtWidgets.QSpinBox()
        self.offset_spin.setRange(-999999, 999999)
        self.offset_spin.setValue(0)
        form_layout.addRow("Frame Offset:", self.offset_spin)

        layout.addLayout(form_layout)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        self.apply_btn = QtWidgets.QPushButton("Apply")
        self.apply_btn.clicked.connect(self._on_apply)
        button_layout.addWidget(self.apply_btn)

        self.ok_btn = QtWidgets.QPushButton("OK")
        self.ok_btn.clicked.connect(self._on_ok)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def _load_values(self):
        """Load current values from shot node."""
        try:
            # Frame range
            start, end = self._shot_node.get_frame_range()
            self.start_frame_spin.setValue(start)
            self.end_frame_spin.setValue(end)

            # FPS
            fps = self._shot_node.get_fps()
            self.fps_combo.setCurrentText(str(fps))

            # Handles
            handles = self._shot_node.get_handles()
            self.handles_spin.setValue(handles)

            # Frame offset
            offset = self._shot_node.get_frame_offset()
            self.offset_spin.setValue(offset)

        except Exception as e:
            logger.error("Failed to load shot values: %s", e)

    def _save_values(self):
        """Save values to shot node."""
        try:
            # Frame range
            start = self.start_frame_spin.value()
            end = self.end_frame_spin.value()
            self._shot_node.set_frame_range(start, end)

            # FPS
            fps = float(self.fps_combo.currentText())
            self._shot_node.set_fps(fps)

            # Handles
            handles = self.handles_spin.value()
            self._shot_node.set_handles(handles)

            # Frame offset
            offset = self.offset_spin.value()
            self._shot_node.set_frame_offset(offset)

            logger.info("Saved shot context for: %s", self._shot_node.get_shot_id())
            return True

        except Exception as e:
            logger.error("Failed to save shot values: %s", e)
            QtWidgets.QMessageBox.warning(self, "Error", "Failed to save: {}".format(e))
            return False

    def _on_apply(self):
        """Handle Apply button click."""
        self._save_values()

    def _on_ok(self):
        """Handle OK button click."""
        if self._save_values():
            self.accept()

