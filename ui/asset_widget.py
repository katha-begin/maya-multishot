# -*- coding: utf-8 -*-
"""Asset widget for Context Variables Pipeline.

This widget displays a table of assets with status indicators.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

try:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtCore import Signal, Qt
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtCore import Signal, Qt

import os
import logging

logger = logging.getLogger(__name__)


class AssetWidget(QtWidgets.QWidget):
    """Widget for displaying assets in a table."""
    
    def __init__(self, parent=None):
        """Initialize asset widget.
        
        Args:
            parent (QWidget, optional): Parent widget
        """
        super(AssetWidget, self).__init__(parent)
        
        self._assets_data = []
        self._current_shot = None
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the user interface."""
        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        
        # Header with title and buttons
        header_layout = QtWidgets.QHBoxLayout()
        
        self.title_label = QtWidgets.QLabel("ASSETS IN SHOT")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        self.import_btn = QtWidgets.QPushButton("+ Import")
        self.import_btn.setMaximumWidth(80)
        header_layout.addWidget(self.import_btn)
        
        self.convert_btn = QtWidgets.QPushButton("Convert")
        self.convert_btn.setMaximumWidth(80)
        header_layout.addWidget(self.convert_btn)
        
        main_layout.addLayout(header_layout)
        
        # Asset table
        self.asset_table = QtWidgets.QTableWidget()
        self.asset_table.setColumnCount(6)
        self.asset_table.setHorizontalHeaderLabels(['Type', 'Name', 'Var', 'Dept', 'Ver', 'Status'])
        
        # Set column widths
        header = self.asset_table.horizontalHeader()
        header.setStretchLastSection(True)
        self.asset_table.setColumnWidth(0, 60)   # Type
        self.asset_table.setColumnWidth(1, 150)  # Name
        self.asset_table.setColumnWidth(2, 50)   # Var
        self.asset_table.setColumnWidth(3, 60)   # Dept
        self.asset_table.setColumnWidth(4, 50)   # Ver
        
        # Enable sorting
        self.asset_table.setSortingEnabled(True)
        
        # Enable multi-selection
        self.asset_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.asset_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        
        # Alternating row colors
        self.asset_table.setAlternatingRowColors(True)
        
        main_layout.addWidget(self.asset_table)
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.import_btn.clicked.connect(self._on_import_clicked)
        self.convert_btn.clicked.connect(self._on_convert_clicked)
    
    def set_current_shot(self, shot_code):
        """Set the current shot.
        
        Args:
            shot_code (str): Shot code
        """
        self._current_shot = shot_code
        self.title_label.setText("ASSETS IN {}".format(shot_code))
    
    def load_assets(self, assets_data):
        """Load assets from data.
        
        Args:
            assets_data (list): List of asset dicts
        """
        self._assets_data = assets_data
        self.asset_table.setRowCount(0)
        self.asset_table.setSortingEnabled(False)
        
        # Add assets to table
        for asset_data in assets_data:
            self._add_asset_row(asset_data)
        
        self.asset_table.setSortingEnabled(True)
        logger.info("Loaded {} assets".format(len(assets_data)))
    
    def _add_asset_row(self, asset_data):
        """Add an asset row to the table.
        
        Args:
            asset_data (dict): Asset data dict
        """
        row = self.asset_table.rowCount()
        self.asset_table.insertRow(row)
        
        # Type
        type_item = QtWidgets.QTableWidgetItem(asset_data.get('asset_type', ''))
        type_item.setFlags(type_item.flags() & ~Qt.ItemIsEditable)
        self.asset_table.setItem(row, 0, type_item)
        
        # Name
        name_item = QtWidgets.QTableWidgetItem(asset_data.get('asset_name', ''))
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
        self.asset_table.setItem(row, 1, name_item)
        
        # Variant
        var_item = QtWidgets.QTableWidgetItem(asset_data.get('variant', ''))
        var_item.setFlags(var_item.flags() & ~Qt.ItemIsEditable)
        self.asset_table.setItem(row, 2, var_item)
        
        # Department
        dept_item = QtWidgets.QTableWidgetItem(asset_data.get('dept', ''))
        dept_item.setFlags(dept_item.flags() & ~Qt.ItemIsEditable)
        self.asset_table.setItem(row, 3, dept_item)
        
        # Version
        ver_item = QtWidgets.QTableWidgetItem(asset_data.get('version', ''))
        ver_item.setFlags(ver_item.flags() & ~Qt.ItemIsEditable)
        self.asset_table.setItem(row, 4, ver_item)
        
        # Status (with colored indicator)
        status_widget = self._create_status_widget(asset_data.get('path', ''))
        self.asset_table.setCellWidget(row, 5, status_widget)
        
        # Store full asset data in first column
        type_item.setData(Qt.UserRole, asset_data)
    
    def _create_status_widget(self, file_path):
        """Create status widget with colored indicator.
        
        Args:
            file_path (str): Path to asset file
        
        Returns:
            QWidget: Status widget
        """
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(5, 0, 5, 0)
        
        # Check if file exists
        file_exists = os.path.exists(file_path) if file_path else False
        
        # Create colored circle label
        if file_exists:
            status_label = QtWidgets.QLabel("● Valid")
            status_label.setStyleSheet("color: #00AA00;")  # Green
        else:
            status_label = QtWidgets.QLabel("● Missing")
            status_label.setStyleSheet("color: #AA0000;")  # Red
        
        layout.addWidget(status_label)
        layout.addStretch()
        
        return widget
    
    def _on_import_clicked(self):
        """Handle import button click."""
        QtWidgets.QMessageBox.information(
            self,
            "Not Implemented",
            "Import Asset functionality will be implemented in Phase 4B (CTX Integration)."
        )
    
    def _on_convert_clicked(self):
        """Handle convert button click."""
        QtWidgets.QMessageBox.information(
            self,
            "Not Implemented",
            "Convert Scene functionality will be implemented in Phase 4B (CTX Integration)."
        )
    
    def get_selected_assets(self):
        """Get selected assets.
        
        Returns:
            list: List of selected asset dicts
        """
        selected_assets = []
        selected_rows = set(index.row() for index in self.asset_table.selectedIndexes())
        
        for row in selected_rows:
            type_item = self.asset_table.item(row, 0)
            if type_item:
                asset_data = type_item.data(Qt.UserRole)
                if asset_data:
                    selected_assets.append(asset_data)
        
        return selected_assets

