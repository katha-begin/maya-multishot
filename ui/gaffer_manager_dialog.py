# -*- coding: utf-8 -*-
"""Gaffer Manager Dialog - Manage light gaffers and overrides.

Provides UI for:
- Selecting gaffers (Master/Sequence/Shot)
- Viewing lights with resolved values
- Adding/removing lights
- Creating overrides
- Applying/syncing values
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
from core.gaffer.resolver import AttributeResolver
from core.gaffer.light_ops import LightOperations
from core.gaffer.chain_ops import ChainOperations
from core.nodes.wrappers.gaffer import CTXLightGafferNode

logger = logging.getLogger(__name__)


class GafferManagerDialog(QtWidgets.QDialog):
    """Dialog for managing light gaffers."""
    
    def __init__(self, parent=None):
        """Initialize gaffer manager dialog.
        
        Args:
            parent: Parent widget (optional)
        """
        super(GafferManagerDialog, self).__init__(parent)
        
        # Make dialog non-modal
        self.setWindowModality(QtCore.Qt.NonModal)
        
        # Set window flags
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowMinimizeButtonHint |
            QtCore.Qt.WindowMaximizeButtonHint
        )
        
        self.setWindowTitle("Light Gaffer Manager")
        self.setMinimumSize(900, 600)
        
        # Current gaffer
        self._current_gaffer = None
        self._lights_data = []  # List of light info dicts
        
        self._setup_ui()
        self._connect_signals()
        self._refresh_gaffer_list()
    
    def _setup_ui(self):
        """Set up the user interface."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Title
        title_label = QtWidgets.QLabel("LIGHT GAFFER MANAGER")
        title_font = QtGui.QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)
        
        # Gaffer selection section
        gaffer_group = QtWidgets.QGroupBox("Gaffer Selection")
        gaffer_layout = QtWidgets.QVBoxLayout(gaffer_group)
        
        # Gaffer dropdown
        gaffer_select_layout = QtWidgets.QHBoxLayout()
        gaffer_select_layout.addWidget(QtWidgets.QLabel("Select Gaffer:"))
        
        self._gaffer_combo = QtWidgets.QComboBox()
        self._gaffer_combo.setMinimumWidth(200)
        gaffer_select_layout.addWidget(self._gaffer_combo)
        
        self._refresh_button = QtWidgets.QPushButton("Refresh")
        self._refresh_button.setMaximumWidth(80)
        gaffer_select_layout.addWidget(self._refresh_button)
        
        gaffer_select_layout.addStretch()
        gaffer_layout.addLayout(gaffer_select_layout)
        
        # Inheritance chain label
        self._chain_label = QtWidgets.QLabel("Inheritance Chain: -")
        self._chain_label.setStyleSheet("color: #888; font-style: italic;")
        gaffer_layout.addWidget(self._chain_label)
        
        main_layout.addWidget(gaffer_group)
        
        # Lights table section
        lights_group = QtWidgets.QGroupBox("Lights in Gaffer")
        lights_layout = QtWidgets.QVBoxLayout(lights_group)
        
        # Create lights table
        self._lights_table = QtWidgets.QTableWidget()
        self._lights_table.setColumnCount(8)
        self._lights_table.setHorizontalHeaderLabels([
            "Light", "Mute", "Intensity", "Exposure", "Color", "Source", "Select", "Details"
        ])
        
        # Set column widths
        header = self._lights_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)  # Light name
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(6, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(7, QtWidgets.QHeaderView.Fixed)
        
        self._lights_table.setColumnWidth(1, 60)   # Mute
        self._lights_table.setColumnWidth(2, 80)   # Intensity
        self._lights_table.setColumnWidth(3, 80)   # Exposure
        self._lights_table.setColumnWidth(4, 100)  # Color
        self._lights_table.setColumnWidth(5, 100)  # Source
        self._lights_table.setColumnWidth(6, 70)   # Select
        self._lights_table.setColumnWidth(7, 70)   # Details
        
        self._lights_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._lights_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        lights_layout.addWidget(self._lights_table)

        # Action buttons
        button_layout = QtWidgets.QHBoxLayout()

        self._add_light_button = QtWidgets.QPushButton("+ Add Light")
        self._add_light_button.setMinimumWidth(100)
        button_layout.addWidget(self._add_light_button)

        self._remove_light_button = QtWidgets.QPushButton("- Remove Light")
        self._remove_light_button.setMinimumWidth(100)
        button_layout.addWidget(self._remove_light_button)

        button_layout.addStretch()

        self._apply_button = QtWidgets.QPushButton("Apply to Scene")
        self._apply_button.setMinimumWidth(120)
        button_layout.addWidget(self._apply_button)

        self._capture_button = QtWidgets.QPushButton("Capture from Scene")
        self._capture_button.setMinimumWidth(140)
        button_layout.addWidget(self._capture_button)

        lights_layout.addLayout(button_layout)

        main_layout.addWidget(lights_group)

    def _connect_signals(self):
        """Connect UI signals to handlers."""
        self._gaffer_combo.currentIndexChanged.connect(self._on_gaffer_changed)
        self._refresh_button.clicked.connect(self._on_refresh_clicked)
        self._add_light_button.clicked.connect(self._on_add_light_clicked)
        self._remove_light_button.clicked.connect(self._on_remove_light_clicked)
        self._apply_button.clicked.connect(self._on_apply_clicked)
        self._capture_button.clicked.connect(self._on_capture_clicked)

    def _refresh_gaffer_list(self):
        """Refresh the gaffer dropdown list."""
        if not cmds:
            logger.warning("Maya not available, cannot refresh gaffer list")
            return

        try:
            # Get all gaffers in scene
            all_gaffers = ChainOperations.list_all_gaffers()

            # Clear combo box
            self._gaffer_combo.clear()

            if not all_gaffers:
                self._gaffer_combo.addItem("No gaffers found", None)
                self._current_gaffer = None
                self._update_chain_label()
                self._populate_lights_table()
                return

            # Group gaffers by type
            master_gaffers = []
            seq_gaffers = []
            shot_gaffers = []
            custom_gaffers = []

            for gaffer_info in all_gaffers:
                gaffer_type = gaffer_info.get('type', 'custom')
                if gaffer_type == 'master':
                    master_gaffers.append(gaffer_info)
                elif gaffer_type == 'sequence':
                    seq_gaffers.append(gaffer_info)
                elif gaffer_type == 'shot':
                    shot_gaffers.append(gaffer_info)
                else:
                    custom_gaffers.append(gaffer_info)

            # Add gaffers to combo box
            for gaffer_info in master_gaffers:
                display_name = "Master: {}".format(gaffer_info['name'])
                self._gaffer_combo.addItem(display_name, gaffer_info['wrapper'])

            for gaffer_info in seq_gaffers:
                display_name = "Seq: {}".format(gaffer_info['name'])
                self._gaffer_combo.addItem(display_name, gaffer_info['wrapper'])

            for gaffer_info in shot_gaffers:
                display_name = "Shot: {}".format(gaffer_info['name'])
                self._gaffer_combo.addItem(display_name, gaffer_info['wrapper'])

            for gaffer_info in custom_gaffers:
                display_name = "Custom: {}".format(gaffer_info['name'])
                self._gaffer_combo.addItem(display_name, gaffer_info['wrapper'])

            # Select first gaffer
            if self._gaffer_combo.count() > 0:
                self._gaffer_combo.setCurrentIndex(0)

        except Exception as e:
            logger.error("Failed to refresh gaffer list: {}".format(e))
            self._gaffer_combo.clear()
            self._gaffer_combo.addItem("Error loading gaffers", None)

    def _update_chain_label(self):
        """Update the inheritance chain label."""
        if not self._current_gaffer:
            self._chain_label.setText("Inheritance Chain: -")
            return

        try:
            # Build chain
            chain = self._current_gaffer.build_chain()

            # Create chain text
            chain_names = []
            for gaffer in chain:
                chain_names.append(gaffer.get_gaffer_name())

            chain_text = " → ".join(reversed(chain_names))
            self._chain_label.setText("Inheritance Chain: {}".format(chain_text))

        except Exception as e:
            logger.error("Failed to build chain: {}".format(e))
            self._chain_label.setText("Inheritance Chain: Error")

    def _populate_lights_table(self):
        """Populate the lights table with current gaffer's lights."""
        # Clear table
        self._lights_table.setRowCount(0)
        self._lights_data = []

        if not self._current_gaffer:
            return

        if not cmds:
            logger.warning("Maya not available, cannot populate lights")
            return

        try:
            # Get all lights in gaffer (direct + inherited)
            lights = GafferManager.get_lights_in_gaffer(self._current_gaffer, include_inherited=True)

            if not lights:
                return

            # Populate table
            for light_context in lights:
                self._add_light_row(light_context)

        except Exception as e:
            logger.error("Failed to populate lights table: {}".format(e))

    def _add_light_row(self, light_context):
        """Add a light row to the table.

        Args:
            light_context: CTXLightContextNode instance
        """
        try:
            # Get light name
            light_name = light_context.get_light_name()

            # Resolve all attributes
            resolved = AttributeResolver.resolve_all_attributes(self._current_gaffer, light_name)

            # Get attribute sources
            sources = AttributeResolver.get_all_attribute_sources(self._current_gaffer, light_name)

            # Add row
            row = self._lights_table.rowCount()
            self._lights_table.insertRow(row)

            # Light name
            name_item = QtWidgets.QTableWidgetItem(light_name)
            self._lights_table.setItem(row, 0, name_item)

            # Mute status
            muted = resolved.get('muted', False)
            mute_text = "MUTE" if muted else "-"
            mute_item = QtWidgets.QTableWidgetItem(mute_text)
            mute_item.setTextAlignment(QtCore.Qt.AlignCenter)
            if muted:
                mute_item.setForeground(QtGui.QColor("#888"))
            self._lights_table.setItem(row, 1, mute_item)

            # Intensity
            intensity = resolved.get('intensity', 1.0)
            intensity_item = QtWidgets.QTableWidgetItem("{:.2f}".format(intensity))
            intensity_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self._lights_table.setItem(row, 2, intensity_item)

            # Exposure
            exposure = resolved.get('exposure', 0.0)
            exposure_item = QtWidgets.QTableWidgetItem("{:.2f}".format(exposure))
            exposure_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self._lights_table.setItem(row, 3, exposure_item)

            # Color
            color_r = resolved.get('colorR', 1.0)
            color_g = resolved.get('colorG', 1.0)
            color_b = resolved.get('colorB', 1.0)
            color_text = "{:.1f},{:.1f},{:.1f}".format(color_r, color_g, color_b)
            color_item = QtWidgets.QTableWidgetItem(color_text)
            color_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self._lights_table.setItem(row, 4, color_item)

            # Source (which gaffer provides the value)
            # Use intensity source as representative
            source_gaffer = sources.get('intensity')
            source_text = source_gaffer.get_gaffer_name() if source_gaffer else "-"
            source_item = QtWidgets.QTableWidgetItem(source_text)
            source_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self._lights_table.setItem(row, 5, source_item)

            # Select button
            select_button = QtWidgets.QPushButton("Select")
            select_button.clicked.connect(lambda checked, ln=light_name: self._on_select_light_clicked(ln))
            self._lights_table.setCellWidget(row, 6, select_button)

            # Details button
            details_button = QtWidgets.QPushButton(">>")
            details_button.clicked.connect(lambda checked, lc=light_context: self._on_details_clicked(lc))
            self._lights_table.setCellWidget(row, 7, details_button)

            # Store light data
            self._lights_data.append({
                'light_context': light_context,
                'light_name': light_name,
                'resolved': resolved,
                'sources': sources
            })

        except Exception as e:
            logger.error("Failed to add light row for {}: {}".format(light_context, e))

    def _on_gaffer_changed(self, index):
        """Handle gaffer selection change."""
        if index < 0:
            return

        # Get selected gaffer
        gaffer_wrapper = self._gaffer_combo.itemData(index)
        self._current_gaffer = gaffer_wrapper

        # Update UI
        self._update_chain_label()
        self._populate_lights_table()

    def _on_refresh_clicked(self):
        """Handle refresh button click."""
        self._refresh_gaffer_list()

    def _on_add_light_clicked(self):
        """Handle add light button click."""
        if not self._current_gaffer:
            QtWidgets.QMessageBox.warning(
                self,
                "No Gaffer Selected",
                "Please select a gaffer first."
            )
            return

        # TODO: Open add light dialog
        QtWidgets.QMessageBox.information(
            self,
            "Add Light",
            "Add Light dialog not yet implemented.\n\nThis will allow you to select Maya lights and add them to the gaffer."
        )

    def _on_remove_light_clicked(self):
        """Handle remove light button click."""
        if not self._current_gaffer:
            QtWidgets.QMessageBox.warning(
                self,
                "No Gaffer Selected",
                "Please select a gaffer first."
            )
            return

        # Get selected row
        selected_rows = self._lights_table.selectionModel().selectedRows()
        if not selected_rows:
            QtWidgets.QMessageBox.warning(
                self,
                "No Light Selected",
                "Please select a light to remove."
            )
            return

        row = selected_rows[0].row()
        light_data = self._lights_data[row]
        light_name = light_data['light_name']

        # Confirm removal
        reply = QtWidgets.QMessageBox.question(
            self,
            "Remove Light",
            "Remove light '{}' from gaffer '{}'?\n\nThis will delete the CTX_LightContext node but not the Maya light.".format(
                light_name,
                self._current_gaffer.get_gaffer_name()
            ),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            try:
                GafferManager.remove_light_from_gaffer(self._current_gaffer, light_name)
                self._populate_lights_table()
                logger.info("Removed light '{}' from gaffer".format(light_name))
            except Exception as e:
                logger.error("Failed to remove light: {}".format(e))
                QtWidgets.QMessageBox.critical(
                    self,
                    "Error",
                    "Failed to remove light:\n{}".format(e)
                )

    def _on_apply_clicked(self):
        """Handle apply to scene button click."""
        if not self._current_gaffer:
            QtWidgets.QMessageBox.warning(
                self,
                "No Gaffer Selected",
                "Please select a gaffer first."
            )
            return

        try:
            # Apply gaffer to all lights
            results = LightOperations.apply_gaffer_to_all_lights(self._current_gaffer)

            # Show results
            success_count = len([r for r in results.values() if r])
            total_count = len(results)

            QtWidgets.QMessageBox.information(
                self,
                "Apply Complete",
                "Applied gaffer '{}' to {} of {} lights.".format(
                    self._current_gaffer.get_gaffer_name(),
                    success_count,
                    total_count
                )
            )

            logger.info("Applied gaffer to {} lights".format(success_count))

        except Exception as e:
            logger.error("Failed to apply gaffer: {}".format(e))
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                "Failed to apply gaffer:\n{}".format(e)
            )

    def _on_capture_clicked(self):
        """Handle capture from scene button click."""
        if not self._current_gaffer:
            QtWidgets.QMessageBox.warning(
                self,
                "No Gaffer Selected",
                "Please select a gaffer first."
            )
            return

        try:
            # Sync all lights from Maya
            results = LightOperations.sync_all_lights(self._current_gaffer)

            # Show results
            success_count = len([r for r in results.values() if r])
            total_count = len(results)

            QtWidgets.QMessageBox.information(
                self,
                "Capture Complete",
                "Captured values from {} of {} lights into gaffer '{}'.".format(
                    success_count,
                    total_count,
                    self._current_gaffer.get_gaffer_name()
                )
            )

            # Refresh table
            self._populate_lights_table()

            logger.info("Captured values from {} lights".format(success_count))

        except Exception as e:
            logger.error("Failed to capture from scene: {}".format(e))
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                "Failed to capture from scene:\n{}".format(e)
            )

    def _on_select_light_clicked(self, light_name):
        """Handle select light button click.

        Args:
            light_name: Name of the light to select
        """
        if not cmds:
            logger.warning("Maya not available, cannot select light")
            return

        try:
            # Find the target light shape
            # Light name in context might be the shape or transform
            if cmds.objExists(light_name):
                cmds.select(light_name, replace=True)
                logger.info("Selected light: {}".format(light_name))
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Light Not Found",
                    "Light '{}' not found in scene.".format(light_name)
                )

        except Exception as e:
            logger.error("Failed to select light: {}".format(e))
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                "Failed to select light:\n{}".format(e)
            )

    def _on_details_clicked(self, light_context):
        """Handle details button click.

        Args:
            light_context: CTXLightContextNode instance
        """
        if not self._current_gaffer:
            QtWidgets.QMessageBox.warning(
                self,
                "No Gaffer Selected",
                "Please select a gaffer first."
            )
            return

        try:
            # Import here to avoid circular imports
            from ui.light_editor_panel import LightEditorPanel

            # Create and show light editor panel
            editor = LightEditorPanel(self._current_gaffer, light_context, parent=self)
            editor.show()

            logger.info("Opened light editor for: {}".format(light_context.get_light_name()))

        except Exception as e:
            logger.error("Failed to open light editor: {}".format(e))
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                "Failed to open light editor:\n{}".format(e)
            )

