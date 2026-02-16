# -*- coding: utf-8 -*-
"""Convert Scene Dialog for Context Variables Pipeline.

This dialog allows users to convert an existing scene to use the CTX system.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

try:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtCore import Qt
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtCore import Qt

import logging

logger = logging.getLogger(__name__)


class ConvertSceneDialog(QtWidgets.QDialog):
    """Dialog for converting existing scene to CTX system."""
    
    def __init__(self, parent=None):
        """Initialize convert scene dialog.
        
        Args:
            parent (QWidget, optional): Parent widget
        """
        super(ConvertSceneDialog, self).__init__(parent)
        
        self.setWindowTitle("Convert Scene to Context System")
        self.setMinimumSize(700, 500)
        self.setModal(True)
        
        self._setup_ui()
        self._connect_signals()
        self._scan_scene()
    
    def _setup_ui(self):
        """Setup the user interface."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(15)
        
        # Header
        header_label = QtWidgets.QLabel("Convert Existing Scene")
        header_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        main_layout.addWidget(header_label)
        
        # Instructions
        instructions = QtWidgets.QLabel(
            "This tool will scan your scene for existing aiStandIn, RSProxyMesh, and "
            "reference nodes, and convert them to use the Context Variables system.\n\n"
            "Select the nodes you want to convert below:"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #888;")
        main_layout.addWidget(instructions)
        
        # Scan results
        scan_group = QtWidgets.QGroupBox("Detected Nodes")
        scan_layout = QtWidgets.QVBoxLayout(scan_group)
        
        # Node table
        self.node_table = QtWidgets.QTableWidget()
        self.node_table.setColumnCount(5)
        self.node_table.setHorizontalHeaderLabels(['Select', 'Node Name', 'Type', 'Path', 'Detected Context'])
        
        # Set column widths
        header = self.node_table.horizontalHeader()
        header.setStretchLastSection(True)
        self.node_table.setColumnWidth(0, 50)   # Select
        self.node_table.setColumnWidth(1, 150)  # Node Name
        self.node_table.setColumnWidth(2, 100)  # Type
        self.node_table.setColumnWidth(3, 200)  # Path
        
        # Enable sorting
        self.node_table.setSortingEnabled(True)
        
        # Alternating row colors
        self.node_table.setAlternatingRowColors(True)
        
        scan_layout.addWidget(self.node_table)
        
        # Select all/none buttons
        select_layout = QtWidgets.QHBoxLayout()
        
        self.select_all_btn = QtWidgets.QPushButton("Select All")
        self.select_all_btn.setMaximumWidth(100)
        select_layout.addWidget(self.select_all_btn)
        
        self.select_none_btn = QtWidgets.QPushButton("Select None")
        self.select_none_btn.setMaximumWidth(100)
        select_layout.addWidget(self.select_none_btn)
        
        select_layout.addStretch()
        
        self.rescan_btn = QtWidgets.QPushButton("Rescan Scene")
        self.rescan_btn.setMaximumWidth(100)
        select_layout.addWidget(self.rescan_btn)
        
        scan_layout.addLayout(select_layout)
        
        main_layout.addWidget(scan_group)
        
        # Conversion options
        options_group = QtWidgets.QGroupBox("Conversion Options")
        options_layout = QtWidgets.QVBoxLayout(options_group)
        
        self.create_shots_check = QtWidgets.QCheckBox("Create CTX_Shot nodes for detected shots")
        self.create_shots_check.setChecked(True)
        options_layout.addWidget(self.create_shots_check)
        
        self.create_layers_check = QtWidgets.QCheckBox("Create display layers for shots")
        self.create_layers_check.setChecked(True)
        options_layout.addWidget(self.create_layers_check)
        
        self.backup_check = QtWidgets.QCheckBox("Create backup before conversion")
        self.backup_check.setChecked(True)
        options_layout.addWidget(self.backup_check)
        
        main_layout.addWidget(options_group)
        
        # Status label
        self.status_label = QtWidgets.QLabel()
        self.status_label.setStyleSheet("color: #888; font-style: italic;")
        main_layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setMinimumWidth(80)
        button_layout.addWidget(self.cancel_btn)
        
        self.convert_btn = QtWidgets.QPushButton("Convert")
        self.convert_btn.setMinimumWidth(80)
        self.convert_btn.setDefault(True)
        button_layout.addWidget(self.convert_btn)
        
        main_layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.select_all_btn.clicked.connect(self._on_select_all)
        self.select_none_btn.clicked.connect(self._on_select_none)
        self.rescan_btn.clicked.connect(self._scan_scene)
        self.cancel_btn.clicked.connect(self.reject)
        self.convert_btn.clicked.connect(self._on_convert_clicked)
    
    def _scan_scene(self):
        """Scan scene for convertible nodes."""
        self.node_table.setRowCount(0)
        self.node_table.setSortingEnabled(False)
        
        # Sample data - in real implementation, this would scan Maya scene
        sample_nodes = [
            {
                'name': 'CatStompie_001_aiStandIn',
                'type': 'aiStandIn',
                'path': 'V:/SWA/.../Ep04_sq0070_SH0170__CHAR_CatStompie_001.abc',
                'context': 'Ep04/sq0070/SH0170'
            },
            {
                'name': 'DogBuddy_001_aiStandIn',
                'type': 'aiStandIn',
                'path': 'V:/SWA/.../Ep04_sq0070_SH0170__CHAR_DogBuddy_001.abc',
                'context': 'Ep04/sq0070/SH0170'
            },
            {
                'name': 'TreeSet_RSProxy',
                'type': 'RSProxyMesh',
                'path': 'V:/SWA/.../Ep04_sq0070_SH0180__SET_TreeSet_001.rs',
                'context': 'Ep04/sq0070/SH0180'
            },
        ]
        
        for node_data in sample_nodes:
            self._add_node_row(node_data)
        
        self.node_table.setSortingEnabled(True)
        self.status_label.setText("Found {} convertible nodes".format(len(sample_nodes)))
    
    def _add_node_row(self, node_data):
        """Add a node row to the table.
        
        Args:
            node_data (dict): Node data dict
        """
        row = self.node_table.rowCount()
        self.node_table.insertRow(row)
        
        # Select checkbox
        check_widget = QtWidgets.QWidget()
        check_layout = QtWidgets.QHBoxLayout(check_widget)
        check_layout.setContentsMargins(0, 0, 0, 0)
        check_layout.setAlignment(Qt.AlignCenter)
        
        checkbox = QtWidgets.QCheckBox()
        checkbox.setChecked(True)
        check_layout.addWidget(checkbox)
        
        self.node_table.setCellWidget(row, 0, check_widget)
        
        # Node name
        name_item = QtWidgets.QTableWidgetItem(node_data['name'])
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
        self.node_table.setItem(row, 1, name_item)
        
        # Type
        type_item = QtWidgets.QTableWidgetItem(node_data['type'])
        type_item.setFlags(type_item.flags() & ~Qt.ItemIsEditable)
        self.node_table.setItem(row, 2, type_item)
        
        # Path
        path_item = QtWidgets.QTableWidgetItem(node_data['path'])
        path_item.setFlags(path_item.flags() & ~Qt.ItemIsEditable)
        self.node_table.setItem(row, 3, path_item)
        
        # Context
        context_item = QtWidgets.QTableWidgetItem(node_data['context'])
        context_item.setFlags(context_item.flags() & ~Qt.ItemIsEditable)
        self.node_table.setItem(row, 4, context_item)
    
    def _on_select_all(self):
        """Select all nodes."""
        for row in range(self.node_table.rowCount()):
            widget = self.node_table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QtWidgets.QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)
    
    def _on_select_none(self):
        """Deselect all nodes."""
        for row in range(self.node_table.rowCount()):
            widget = self.node_table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QtWidgets.QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)
    
    def _on_convert_clicked(self):
        """Handle convert button click."""
        selected_count = sum(
            1 for row in range(self.node_table.rowCount())
            if self.node_table.cellWidget(row, 0).findChild(QtWidgets.QCheckBox).isChecked()
        )
        
        QtWidgets.QMessageBox.information(
            self,
            "Not Implemented",
            "Convert Scene functionality will be implemented in Phase 4B (CTX Integration).\n\n"
            "This will convert {} selected nodes to use CTX system:\n"
            "- Create CTX_Shot nodes\n"
            "- Create CTX_Asset nodes\n"
            "- Update node connections\n"
            "- Create display layers\n"
            "- Backup original scene".format(selected_count)
        )
        self.accept()

