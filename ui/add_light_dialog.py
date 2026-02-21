# -*- coding: utf-8 -*-
"""Add Light Dialog - Select Maya lights to add to gaffer.

Provides UI for:
- Listing all Maya lights in scene
- Filtering by light type
- Multi-select capability
- Preview current values
- Add to current gaffer
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui

try:
    from maya import cmds
except ImportError:
    cmds = None

from core.gaffer.manager import GafferManager

logger = logging.getLogger(__name__)


class AddLightDialog(QtWidgets.QDialog):
    """Dialog for adding Maya lights to a gaffer."""
    
    def __init__(self, gaffer, parent=None):
        """Initialize add light dialog.
        
        Args:
            gaffer: CTXLightGafferNode instance
            parent: Parent widget (optional)
        """
        super(AddLightDialog, self).__init__(parent)
        
        self._gaffer = gaffer
        self._lights = []  # List of light info dicts
        
        self.setWindowTitle("Add Lights to Gaffer")
        self.setMinimumSize(600, 400)
        
        self._setup_ui()
        self._load_lights()
    
    def _setup_ui(self):
        """Set up the user interface."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Title
        title_label = QtWidgets.QLabel("Add Lights to Gaffer: {}".format(
            self._gaffer.get_gaffer_name()
        ))
        title_font = QtGui.QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)
        
        # Filter section
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.addWidget(QtWidgets.QLabel("Filter by type:"))
        
        self._filter_combo = QtWidgets.QComboBox()
        self._filter_combo.addItem("All Lights", None)
        self._filter_combo.addItem("Area Lights", "aiAreaLight")
        self._filter_combo.addItem("Spot Lights", "spotLight")
        self._filter_combo.addItem("Point Lights", "pointLight")
        self._filter_combo.addItem("Directional Lights", "directionalLight")
        self._filter_combo.addItem("Volume Lights", "volumeLight")
        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self._filter_combo)
        
        filter_layout.addStretch()
        
        self._refresh_button = QtWidgets.QPushButton("Refresh")
        self._refresh_button.clicked.connect(self._load_lights)
        filter_layout.addWidget(self._refresh_button)
        
        main_layout.addLayout(filter_layout)
        
        # Lights table
        self._lights_table = QtWidgets.QTableWidget()
        self._lights_table.setColumnCount(4)
        self._lights_table.setHorizontalHeaderLabels([
            "Light Name", "Type", "Intensity", "Already in Gaffer"
        ])
        
        # Set column widths
        header = self._lights_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)
        
        self._lights_table.setColumnWidth(1, 150)  # Type
        self._lights_table.setColumnWidth(2, 100)  # Intensity
        self._lights_table.setColumnWidth(3, 120)  # Already in Gaffer
        
        self._lights_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._lights_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        
        main_layout.addWidget(self._lights_table)
        
        # Info label
        self._info_label = QtWidgets.QLabel("Select lights to add (Ctrl+Click for multiple)")
        self._info_label.setStyleSheet("color: #888; font-style: italic;")
        main_layout.addWidget(self._info_label)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        self._select_all_button = QtWidgets.QPushButton("Select All")
        self._select_all_button.clicked.connect(self._on_select_all_clicked)
        button_layout.addWidget(self._select_all_button)
        
        self._deselect_all_button = QtWidgets.QPushButton("Deselect All")
        self._deselect_all_button.clicked.connect(self._on_deselect_all_clicked)
        button_layout.addWidget(self._deselect_all_button)
        
        button_layout.addStretch()
        
        self._add_button = QtWidgets.QPushButton("Add Selected Lights")
        self._add_button.setMinimumWidth(150)
        self._add_button.clicked.connect(self._on_add_clicked)
        button_layout.addWidget(self._add_button)
        
        self._cancel_button = QtWidgets.QPushButton("Cancel")
        self._cancel_button.setMinimumWidth(100)
        self._cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self._cancel_button)
        
        main_layout.addLayout(button_layout)

    def _load_lights(self):
        """Load all lights from Maya scene."""
        if not cmds:
            logger.warning("Maya not available, cannot load lights")
            return

        try:
            # Clear table
            self._lights_table.setRowCount(0)
            self._lights = []

            # Get all light types
            light_types = [
                'aiAreaLight', 'spotLight', 'pointLight',
                'directionalLight', 'volumeLight', 'aiSkyDomeLight',
                'aiPhotometricLight', 'aiLightPortal'
            ]

            # Get existing lights in gaffer
            existing_lights = GafferManager.get_lights_in_gaffer(self._gaffer, include_inherited=False)
            existing_light_names = set()
            for light_ctx in existing_lights:
                existing_light_names.add(light_ctx.get_light_name())

            # Find all lights in scene
            for light_type in light_types:
                lights = cmds.ls(type=light_type) or []
                for light_shape in lights:
                    # Get transform
                    transforms = cmds.listRelatives(light_shape, parent=True, fullPath=False) or []
                    if not transforms:
                        continue

                    light_transform = transforms[0]

                    # Get intensity (if available)
                    intensity = "-"
                    if cmds.attributeQuery('intensity', node=light_shape, exists=True):
                        try:
                            intensity = "{:.2f}".format(cmds.getAttr("{}.intensity".format(light_shape)))
                        except:
                            pass

                    # Check if already in gaffer
                    already_in_gaffer = light_shape in existing_light_names or light_transform in existing_light_names

                    # Store light info
                    light_info = {
                        'shape': light_shape,
                        'transform': light_transform,
                        'type': light_type,
                        'intensity': intensity,
                        'in_gaffer': already_in_gaffer
                    }
                    self._lights.append(light_info)

            # Populate table
            self._populate_table()

            # Update info label
            self._info_label.setText("Found {} lights in scene".format(len(self._lights)))

        except Exception as e:
            logger.error("Failed to load lights: {}".format(e))
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                "Failed to load lights:\n{}".format(e)
            )

    def _populate_table(self):
        """Populate the lights table."""
        # Get filter
        filter_type = self._filter_combo.currentData()

        # Clear table
        self._lights_table.setRowCount(0)

        # Add lights
        for light_info in self._lights:
            # Apply filter
            if filter_type and light_info['type'] != filter_type:
                continue

            row = self._lights_table.rowCount()
            self._lights_table.insertRow(row)

            # Light name
            name_item = QtWidgets.QTableWidgetItem(light_info['transform'])
            self._lights_table.setItem(row, 0, name_item)

            # Type
            type_item = QtWidgets.QTableWidgetItem(light_info['type'])
            type_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self._lights_table.setItem(row, 1, type_item)

            # Intensity
            intensity_item = QtWidgets.QTableWidgetItem(light_info['intensity'])
            intensity_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self._lights_table.setItem(row, 2, intensity_item)

            # Already in gaffer
            in_gaffer_text = "Yes" if light_info['in_gaffer'] else "No"
            in_gaffer_item = QtWidgets.QTableWidgetItem(in_gaffer_text)
            in_gaffer_item.setTextAlignment(QtCore.Qt.AlignCenter)
            if light_info['in_gaffer']:
                in_gaffer_item.setForeground(QtGui.QColor("#888"))
            self._lights_table.setItem(row, 3, in_gaffer_item)

            # Disable row if already in gaffer
            if light_info['in_gaffer']:
                for col in range(4):
                    item = self._lights_table.item(row, col)
                    if item:
                        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsSelectable)
                        item.setForeground(QtGui.QColor("#888"))

    def _on_filter_changed(self, index):
        """Handle filter combo box change."""
        self._populate_table()

    def _on_select_all_clicked(self):
        """Handle select all button click."""
        self._lights_table.selectAll()

    def _on_deselect_all_clicked(self):
        """Handle deselect all button click."""
        self._lights_table.clearSelection()

    def _on_add_clicked(self):
        """Handle add button click."""
        if not cmds:
            QtWidgets.QMessageBox.warning(
                self,
                "Maya Not Available",
                "Maya is not available."
            )
            return

        # Get selected rows
        selected_rows = set()
        for item in self._lights_table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QtWidgets.QMessageBox.warning(
                self,
                "No Lights Selected",
                "Please select at least one light to add."
            )
            return

        try:
            # Add lights to gaffer
            added_count = 0
            failed_lights = []

            for row in sorted(selected_rows):
                light_name = self._lights_table.item(row, 0).text()

                # Find light info
                light_info = None
                for info in self._lights:
                    if info['transform'] == light_name:
                        light_info = info
                        break

                if not light_info:
                    continue

                # Skip if already in gaffer
                if light_info['in_gaffer']:
                    continue

                # Add light to gaffer
                try:
                    GafferManager.add_light_to_gaffer(
                        self._gaffer,
                        light_info['shape'],
                        light_name=light_name
                    )
                    added_count += 1
                except Exception as e:
                    logger.error("Failed to add light {}: {}".format(light_name, e))
                    failed_lights.append(light_name)

            # Show results
            if added_count > 0:
                message = "Added {} light(s) to gaffer '{}'.".format(
                    added_count,
                    self._gaffer.get_gaffer_name()
                )
                if failed_lights:
                    message += "\n\nFailed to add: {}".format(", ".join(failed_lights))

                QtWidgets.QMessageBox.information(
                    self,
                    "Add Complete",
                    message
                )

                # Close dialog
                self.accept()
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "No Lights Added",
                    "No lights were added. They may already be in the gaffer."
                )

        except Exception as e:
            logger.error("Failed to add lights: {}".format(e))
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                "Failed to add lights:\n{}".format(e)
            )

