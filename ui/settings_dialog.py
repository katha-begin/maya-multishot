# -*- coding: utf-8 -*-
"""Settings Dialog for Context Variables Pipeline.

This dialog allows users to configure preferences and project settings.
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


class SettingsDialog(QtWidgets.QDialog):
    """Dialog for configuring settings and preferences."""
    
    def __init__(self, parent=None):
        """Initialize settings dialog.
        
        Args:
            parent (QWidget, optional): Parent widget
        """
        super(SettingsDialog, self).__init__(parent)
        
        self.setWindowTitle("Settings")
        self.setMinimumSize(600, 500)
        self.setModal(True)
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the user interface."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(10)
        
        # Tab widget
        self.tab_widget = QtWidgets.QTabWidget()
        
        # General tab
        general_tab = self._create_general_tab()
        self.tab_widget.addTab(general_tab, "General")
        
        # Project tab
        project_tab = self._create_project_tab()
        self.tab_widget.addTab(project_tab, "Project")
        
        # Paths tab
        paths_tab = self._create_paths_tab()
        self.tab_widget.addTab(paths_tab, "Paths")
        
        # Advanced tab
        advanced_tab = self._create_advanced_tab()
        self.tab_widget.addTab(advanced_tab, "Advanced")
        
        main_layout.addWidget(self.tab_widget)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        
        self.reset_btn = QtWidgets.QPushButton("Reset to Defaults")
        button_layout.addWidget(self.reset_btn)
        
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setMinimumWidth(80)
        button_layout.addWidget(self.cancel_btn)
        
        self.apply_btn = QtWidgets.QPushButton("Apply")
        self.apply_btn.setMinimumWidth(80)
        button_layout.addWidget(self.apply_btn)
        
        self.ok_btn = QtWidgets.QPushButton("OK")
        self.ok_btn.setMinimumWidth(80)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)
        
        main_layout.addLayout(button_layout)
    
    def _create_general_tab(self):
        """Create general settings tab.
        
        Returns:
            QWidget: General tab widget
        """
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # UI preferences
        ui_group = QtWidgets.QGroupBox("UI Preferences")
        ui_layout = QtWidgets.QFormLayout(ui_group)
        
        self.auto_refresh_check = QtWidgets.QCheckBox("Auto-refresh on scene open")
        self.auto_refresh_check.setChecked(True)
        ui_layout.addRow("", self.auto_refresh_check)
        
        self.show_tooltips_check = QtWidgets.QCheckBox("Show tooltips")
        self.show_tooltips_check.setChecked(True)
        ui_layout.addRow("", self.show_tooltips_check)
        
        self.confirm_actions_check = QtWidgets.QCheckBox("Confirm destructive actions")
        self.confirm_actions_check.setChecked(True)
        ui_layout.addRow("", self.confirm_actions_check)
        
        layout.addWidget(ui_group)
        
        # Auto-save preferences
        autosave_group = QtWidgets.QGroupBox("Auto-Save")
        autosave_layout = QtWidgets.QFormLayout(autosave_group)
        
        self.autosave_check = QtWidgets.QCheckBox("Enable auto-save")
        self.autosave_check.setChecked(False)
        autosave_layout.addRow("", self.autosave_check)
        
        self.autosave_interval_spin = QtWidgets.QSpinBox()
        self.autosave_interval_spin.setRange(1, 60)
        self.autosave_interval_spin.setValue(10)
        self.autosave_interval_spin.setSuffix(" minutes")
        autosave_layout.addRow("Interval:", self.autosave_interval_spin)
        
        layout.addWidget(autosave_group)
        
        layout.addStretch()
        
        return tab
    
    def _create_project_tab(self):
        """Create project settings tab.
        
        Returns:
            QWidget: Project tab widget
        """
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # Config file
        config_group = QtWidgets.QGroupBox("Configuration File")
        config_layout = QtWidgets.QVBoxLayout(config_group)
        
        file_layout = QtWidgets.QHBoxLayout()
        
        self.config_path_edit = QtWidgets.QLineEdit()
        self.config_path_edit.setPlaceholderText("Path to project_config.json")
        self.config_path_edit.setText("E:/dev/maya-multishot/config/project_config.json")
        self.config_path_edit.setReadOnly(True)
        file_layout.addWidget(self.config_path_edit)
        
        self.browse_config_btn = QtWidgets.QPushButton("Browse...")
        self.browse_config_btn.setMaximumWidth(80)
        file_layout.addWidget(self.browse_config_btn)
        
        config_layout.addLayout(file_layout)
        
        self.reload_config_btn = QtWidgets.QPushButton("Reload Configuration")
        self.reload_config_btn.setMaximumWidth(150)
        config_layout.addWidget(self.reload_config_btn)
        
        layout.addWidget(config_group)
        
        # Project info (read-only)
        info_group = QtWidgets.QGroupBox("Project Information")
        info_layout = QtWidgets.QFormLayout(info_group)
        
        self.project_code_label = QtWidgets.QLabel("SWA")
        info_layout.addRow("Project Code:", self.project_code_label)
        
        self.project_root_label = QtWidgets.QLabel("V:/")
        info_layout.addRow("Project Root:", self.project_root_label)
        
        self.scene_base_label = QtWidgets.QLabel("all/scene")
        info_layout.addRow("Scene Base:", self.scene_base_label)
        
        layout.addWidget(info_group)
        
        layout.addStretch()
        
        return tab
    
    def _create_paths_tab(self):
        """Create paths settings tab.
        
        Returns:
            QWidget: Paths tab widget
        """
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # Platform mapping
        platform_group = QtWidgets.QGroupBox("Platform Path Mapping")
        platform_layout = QtWidgets.QFormLayout(platform_group)
        
        instructions = QtWidgets.QLabel(
            "Configure path mappings for cross-platform compatibility."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #888; margin-bottom: 10px;")
        platform_layout.addRow(instructions)
        
        self.windows_path_edit = QtWidgets.QLineEdit()
        self.windows_path_edit.setText("V:/")
        platform_layout.addRow("Windows:", self.windows_path_edit)
        
        self.linux_path_edit = QtWidgets.QLineEdit()
        self.linux_path_edit.setText("/mnt/projects/")
        platform_layout.addRow("Linux:", self.linux_path_edit)
        
        layout.addWidget(platform_group)
        
        layout.addStretch()
        
        return tab
    
    def _create_advanced_tab(self):
        """Create advanced settings tab.
        
        Returns:
            QWidget: Advanced tab widget
        """
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # Logging
        logging_group = QtWidgets.QGroupBox("Logging")
        logging_layout = QtWidgets.QFormLayout(logging_group)
        
        self.log_level_combo = QtWidgets.QComboBox()
        self.log_level_combo.addItems(['DEBUG', 'INFO', 'WARNING', 'ERROR'])
        self.log_level_combo.setCurrentText('INFO')
        logging_layout.addRow("Log Level:", self.log_level_combo)
        
        self.log_to_file_check = QtWidgets.QCheckBox("Log to file")
        logging_layout.addRow("", self.log_to_file_check)
        
        layout.addWidget(logging_group)
        
        # Performance
        perf_group = QtWidgets.QGroupBox("Performance")
        perf_layout = QtWidgets.QFormLayout(perf_group)
        
        self.cache_size_spin = QtWidgets.QSpinBox()
        self.cache_size_spin.setRange(10, 1000)
        self.cache_size_spin.setValue(100)
        self.cache_size_spin.setSuffix(" MB")
        perf_layout.addRow("Cache Size:", self.cache_size_spin)
        
        self.parallel_load_check = QtWidgets.QCheckBox("Enable parallel loading")
        self.parallel_load_check.setChecked(True)
        perf_layout.addRow("", self.parallel_load_check)
        
        layout.addWidget(perf_group)
        
        layout.addStretch()
        
        return tab
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.browse_config_btn.clicked.connect(self._on_browse_config)
        self.reload_config_btn.clicked.connect(self._on_reload_config)
        self.reset_btn.clicked.connect(self._on_reset)
        self.cancel_btn.clicked.connect(self.reject)
        self.apply_btn.clicked.connect(self._on_apply)
        self.ok_btn.clicked.connect(self._on_ok)
    
    def _on_browse_config(self):
        """Handle browse config button click."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Configuration File",
            "",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if file_path:
            self.config_path_edit.setText(file_path)
    
    def _on_reload_config(self):
        """Handle reload config button click."""
        QtWidgets.QMessageBox.information(
            self,
            "Not Implemented",
            "Reload Configuration functionality will be implemented in Phase 4B."
        )
    
    def _on_reset(self):
        """Handle reset button click."""
        reply = QtWidgets.QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            QtWidgets.QMessageBox.information(
                self,
                "Not Implemented",
                "Reset Settings functionality will be implemented in Phase 4B."
            )
    
    def _on_apply(self):
        """Handle apply button click."""
        QtWidgets.QMessageBox.information(
            self,
            "Not Implemented",
            "Apply Settings functionality will be implemented in Phase 4B."
        )
    
    def _on_ok(self):
        """Handle OK button click."""
        self._on_apply()
        self.accept()

