# -*- coding: utf-8 -*-
"""Import Asset Dialog for Context Variables Pipeline.

This dialog allows users to import an asset into the active shot.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui

import logging

logger = logging.getLogger(__name__)


class ImportAssetDialog(QtWidgets.QDialog):
    """Dialog for importing an asset into the active shot."""
    
    def __init__(self, parent=None, shot_code=None):
        """Initialize import asset dialog.
        
        Args:
            parent (QWidget, optional): Parent widget
            shot_code (str, optional): Active shot code
        """
        super(ImportAssetDialog, self).__init__(parent)
        
        self.setWindowTitle("Import Asset to Shot")
        self.setMinimumSize(500, 600)
        self.setModal(True)
        
        self._shot_code = shot_code
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the user interface."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(15)
        
        # Header with shot info
        if self._shot_code:
            header_label = QtWidgets.QLabel("Import asset to: {}".format(self._shot_code))
            header_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
            main_layout.addWidget(header_label)
        
        # Instructions
        instructions = QtWidgets.QLabel(
            "Select an asset to import. The asset will be added to the shot "
            "with the selected version and import type."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #888;")
        main_layout.addWidget(instructions)
        
        # Form layout
        form_layout = QtWidgets.QFormLayout()
        form_layout.setSpacing(10)
        
        # Department selector
        self.dept_combo = QtWidgets.QComboBox()
        self.dept_combo.addItems(['anim', 'fx', 'layout', 'lighting', 'model'])
        form_layout.addRow("Department:", self.dept_combo)
        
        # Asset type selector
        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItems(['CHAR', 'PROP', 'SET', 'VEH', 'FX'])
        form_layout.addRow("Asset Type:", self.type_combo)
        
        # Asset name input
        self.asset_input = QtWidgets.QLineEdit()
        self.asset_input.setPlaceholderText("CatStompie")
        form_layout.addRow("Asset Name:", self.asset_input)
        
        # Variant input
        self.variant_input = QtWidgets.QLineEdit()
        self.variant_input.setPlaceholderText("001")
        self.variant_input.setMaxLength(3)
        form_layout.addRow("Variant:", self.variant_input)
        
        main_layout.addLayout(form_layout)
        
        # Version selection
        version_group = QtWidgets.QGroupBox("Version")
        version_layout = QtWidgets.QVBoxLayout(version_group)
        
        # Version list
        self.version_list = QtWidgets.QListWidget()
        self.version_list.setMaximumHeight(150)
        self.version_list.addItems(['v003 (latest)', 'v002', 'v001'])
        self.version_list.setCurrentRow(0)
        version_layout.addWidget(self.version_list)
        
        main_layout.addWidget(version_group)
        
        # Import type
        import_type_group = QtWidgets.QGroupBox("Import Type")
        import_type_layout = QtWidgets.QVBoxLayout(import_type_group)
        
        self.standin_radio = QtWidgets.QRadioButton("StandIn (aiStandIn)")
        self.standin_radio.setChecked(True)
        import_type_layout.addWidget(self.standin_radio)
        
        self.reference_radio = QtWidgets.QRadioButton("Reference (Maya Reference)")
        import_type_layout.addWidget(self.reference_radio)
        
        self.proxy_radio = QtWidgets.QRadioButton("Proxy (RSProxyMesh)")
        import_type_layout.addWidget(self.proxy_radio)
        
        main_layout.addWidget(import_type_group)
        
        # Path preview
        preview_group = QtWidgets.QGroupBox("Path Preview")
        preview_layout = QtWidgets.QVBoxLayout(preview_group)
        
        self.path_preview = QtWidgets.QTextEdit()
        self.path_preview.setReadOnly(True)
        self.path_preview.setMaximumHeight(80)
        self.path_preview.setPlainText("V:/SWA/all/scene/Ep04/sq0070/SH0170/anim/publish/v003/Ep04_sq0070_SH0170__CHAR_CatStompie_001.abc")
        preview_layout.addWidget(self.path_preview)
        
        # Validation status
        self.validation_label = QtWidgets.QLabel("✓ File exists")
        self.validation_label.setStyleSheet("color: #00AA00;")
        preview_layout.addWidget(self.validation_label)
        
        main_layout.addWidget(preview_group)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setMinimumWidth(80)
        button_layout.addWidget(self.cancel_btn)
        
        self.import_btn = QtWidgets.QPushButton("Import")
        self.import_btn.setMinimumWidth(80)
        self.import_btn.setDefault(True)
        button_layout.addWidget(self.import_btn)
        
        main_layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.dept_combo.currentTextChanged.connect(self._update_preview)
        self.type_combo.currentTextChanged.connect(self._update_preview)
        self.asset_input.textChanged.connect(self._update_preview)
        self.variant_input.textChanged.connect(self._update_preview)
        self.version_list.currentTextChanged.connect(self._update_preview)
        self.cancel_btn.clicked.connect(self.reject)
        self.import_btn.clicked.connect(self._on_import_clicked)
    
    def _update_preview(self):
        """Update path preview."""
        # This is a placeholder - real implementation would build actual path
        dept = self.dept_combo.currentText()
        asset_type = self.type_combo.currentText()
        asset_name = self.asset_input.text() or "AssetName"
        variant = self.variant_input.text() or "001"
        version = self.version_list.currentItem().text().split()[0] if self.version_list.currentItem() else "v001"
        
        preview_path = "V:/SWA/all/scene/Ep04/sq0070/{}/{}/ publish/{}/Ep04_sq0070_{}__{}_{}_{}. abc".format(
            self._shot_code or "SH0170",
            dept,
            version,
            self._shot_code or "SH0170",
            asset_type,
            asset_name,
            variant
        )
        
        self.path_preview.setPlainText(preview_path)
    
    def _on_import_clicked(self):
        """Handle import button click."""
        import_type = "StandIn"
        if self.reference_radio.isChecked():
            import_type = "Reference"
        elif self.proxy_radio.isChecked():
            import_type = "Proxy"
        
        QtWidgets.QMessageBox.information(
            self,
            "Not Implemented",
            "Import Asset functionality will be implemented in Phase 4B (CTX Integration).\n\n"
            "This will:\n"
            "- Create CTX_Asset node with asset metadata\n"
            "- Import asset as {} node\n"
            "- Link asset to shot's display layer\n"
            "- Update version cache".format(import_type)
        )
        self.accept()
    
    def get_asset_data(self):
        """Get asset data from dialog.
        
        Returns:
            dict: Asset data
        """
        version_text = self.version_list.currentItem().text() if self.version_list.currentItem() else "v001"
        version = version_text.split()[0]
        
        import_type = "standin"
        if self.reference_radio.isChecked():
            import_type = "reference"
        elif self.proxy_radio.isChecked():
            import_type = "proxy"
        
        return {
            'dept': self.dept_combo.currentText(),
            'asset_type': self.type_combo.currentText(),
            'asset_name': self.asset_input.text(),
            'variant': self.variant_input.text(),
            'version': version,
            'import_type': import_type
        }

