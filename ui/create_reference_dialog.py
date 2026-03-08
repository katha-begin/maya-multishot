# -*- coding: utf-8 -*-
"""Create Reference Dialog - Dialog for creating reference with shader/groom options.

This dialog allows users to create a Maya reference with optional shader
and groom assignment.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui

import logging

logger = logging.getLogger(__name__)


class CreateReferenceDialog(QtWidgets.QDialog):
    """Dialog for creating reference with shader/groom options."""
    
    def __init__(self, asset_data, shader_files, parent=None):
        """Initialize create reference dialog.
        
        Args:
            asset_data (dict): Asset information with keys:
                - asset_type: Asset type (CHAR, PROP, etc.)
                - asset_name: Asset name
                - variant: Variant code
                - geometry_file: Path to geometry file
                - namespace: Asset namespace
            shader_files (dict): Shader/groom file paths with keys:
                - shader: Path to shader file or None
                - groom: Path to groom file or None
            parent (QWidget, optional): Parent widget
        """
        super(CreateReferenceDialog, self).__init__(parent)
        
        self.setWindowTitle("Create Reference")
        self.setMinimumSize(500, 300)
        self.setModal(True)
        
        self._asset_data = asset_data
        self._shader_files = shader_files
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the user interface."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(15)
        
        # Header
        namespace = self._asset_data.get('namespace', 'Unknown')
        header_label = QtWidgets.QLabel("Create Reference: {}".format(namespace))
        header_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        main_layout.addWidget(header_label)
        
        # Geometry file section
        geo_group = QtWidgets.QGroupBox("Geometry File")
        geo_layout = QtWidgets.QVBoxLayout(geo_group)
        
        geo_file = self._asset_data.get('geometry_file', '')
        geo_exists = os.path.exists(geo_file) if geo_file else False
        
        geo_status = u"✓ " if geo_exists else u"✗ "
        geo_label = QtWidgets.QLabel(geo_status + geo_file)
        geo_label.setWordWrap(True)
        if geo_exists:
            geo_label.setStyleSheet("color: #00AA00;")
        else:
            geo_label.setStyleSheet("color: #CC0000;")
        geo_layout.addWidget(geo_label)
        
        main_layout.addWidget(geo_group)
        
        # Shader section
        shader_group = QtWidgets.QGroupBox("Shader")
        shader_layout = QtWidgets.QVBoxLayout(shader_group)
        
        self.shader_checkbox = QtWidgets.QCheckBox("Assign Shader")
        shader_file = self._shader_files.get('shader')
        shader_exists = os.path.exists(shader_file) if shader_file else False
        
        if shader_exists:
            self.shader_checkbox.setChecked(True)
            shader_status = u"✓ "
            shader_label = QtWidgets.QLabel(shader_status + shader_file)
            shader_label.setStyleSheet("color: #00AA00;")
        else:
            self.shader_checkbox.setEnabled(False)
            shader_status = u"✗ "
            shader_label = QtWidgets.QLabel(shader_status + "Shader file not found")
            shader_label.setStyleSheet("color: #888888;")
        
        shader_label.setWordWrap(True)
        shader_layout.addWidget(self.shader_checkbox)
        shader_layout.addWidget(shader_label)
        
        main_layout.addWidget(shader_group)
        
        # Groom section
        groom_group = QtWidgets.QGroupBox("Groom")
        groom_layout = QtWidgets.QVBoxLayout(groom_group)
        
        self.groom_checkbox = QtWidgets.QCheckBox("Reference Groom")
        groom_file = self._shader_files.get('groom')
        groom_exists = os.path.exists(groom_file) if groom_file else False
        
        if groom_exists:
            self.groom_checkbox.setChecked(True)
            groom_status = u"✓ "
            groom_label = QtWidgets.QLabel(groom_status + groom_file)
            groom_label.setStyleSheet("color: #00AA00;")
        else:
            self.groom_checkbox.setEnabled(False)
            groom_status = u"✗ "
            groom_label = QtWidgets.QLabel(groom_status + "Groom file not found")
            groom_label.setStyleSheet("color: #888888;")
        
        groom_label.setWordWrap(True)
        groom_layout.addWidget(self.groom_checkbox)
        groom_layout.addWidget(groom_label)
        
        main_layout.addWidget(groom_group)
        
        main_layout.addStretch()
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setMinimumWidth(80)
        button_layout.addWidget(self.cancel_btn)
        
        self.create_btn = QtWidgets.QPushButton("Create")
        self.create_btn.setMinimumWidth(80)
        self.create_btn.setDefault(True)
        button_layout.addWidget(self.create_btn)
        
        main_layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.cancel_btn.clicked.connect(self.reject)
        self.create_btn.clicked.connect(self.accept)
    
    def get_options(self):
        """Get user-selected options.
        
        Returns:
            dict: Options with keys:
                - assign_shader: bool
                - reference_groom: bool
        """
        return {
            'assign_shader': self.shader_checkbox.isChecked(),
            'reference_groom': self.groom_checkbox.isChecked()
        }

