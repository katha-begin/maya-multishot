# -*- coding: utf-8 -*-
"""Multishot Manager - Main window for managing multiple shots in Maya scene.

Based on Nuke Multishot Manager design pattern.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import os

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui

from config.project_config import ProjectConfig
from config.platform_config import PlatformConfig
from core.context import ContextManager
from core.custom_nodes import CTXManagerNode, CTXShotNode
from core.asset_scanner import AssetScanner
from core.nodes import NodeManager

logger = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    """Multishot Manager main window."""

    # Class variable to track existing instance
    _instance = None

    def __init__(self, parent=None):
        # Close existing instance if it exists
        if MainWindow._instance is not None:
            try:
                logger.info("Closing existing Multishot Manager window")
                old_instance = MainWindow._instance
                MainWindow._instance = None

                # Hide first for immediate visual feedback
                old_instance.hide()

                # Close and delete the old window
                old_instance.close()
                old_instance.deleteLater()

                # Process events to ensure deletion happens
                QtWidgets.QApplication.processEvents()

            except Exception as e:
                logger.warning("Error closing existing window: %s", e)
                MainWindow._instance = None

        super(MainWindow, self).__init__(parent)

        # Store this instance
        MainWindow._instance = self

        self._config = None
        self._context_manager = ContextManager()
        self._shots = []  # List of dicts with shot data + CTX node reference
        self._active_shot_index = None
        self._asset_manager_dialogs = {}  # Store references to prevent garbage collection

        self._setup_ui()
        self._connect_signals()
        self._load_config()
        self._load_existing_shots()

        # Register context change callback for path resolution
        self._context_manager.register_callback(self._on_context_changed)

    def closeEvent(self, event):
        """Handle window close event."""
        # Unregister context callback
        self._context_manager.unregister_callback(self._on_context_changed)
        # Clear instance reference when window is closed
        MainWindow._instance = None
        super(MainWindow, self).closeEvent(event)
    
    def _setup_ui(self):
        self.setWindowTitle("Multishot Manager")
        self.setObjectName("MultishotManagerWindow")

        # Make window floatable and not always on top
        # User can work with other Maya windows while this is open
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowMinimizeButtonHint |
            QtCore.Qt.WindowMaximizeButtonHint
        )

        # Set initial size based on content (will resize after table is populated)
        self.resize(900, 400)
        
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        self.current_shot_label = QtWidgets.QLabel("Current Shot: None")
        self.current_shot_label.setStyleSheet("font-weight: bold; font-size: 12pt; padding: 5px;")
        main_layout.addWidget(self.current_shot_label)
        
        controller_label = QtWidgets.QLabel("SHOT CONTEXT CONTROLLER")
        controller_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        main_layout.addWidget(controller_label)
        
        self.shot_table = QtWidgets.QTableWidget()
        self.shot_table.setColumnCount(6)
        self.shot_table.setHorizontalHeaderLabels(["#", "Shot", "Set Shot", "Version", "Remove", "Save"])

        # Set column widths
        header = self.shot_table.horizontalHeader()
        header.setStretchLastSection(False)

        # Column 0: # - Small, just enough for row numbers (30px)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self.shot_table.setColumnWidth(0, 30)

        # Column 1: Shot - Stretch to fill available space
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

        # Column 2: Set Shot button - Fixed width (80px)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        self.shot_table.setColumnWidth(2, 80)

        # Column 3: Version button - Fixed width (80px)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)
        self.shot_table.setColumnWidth(3, 80)

        # Column 4: Remove button - Fixed width (70px)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.Fixed)
        self.shot_table.setColumnWidth(4, 70)

        # Column 5: Save button - Fixed width (80px)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.Fixed)
        self.shot_table.setColumnWidth(5, 80)

        self.shot_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.shot_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.shot_table.setAlternatingRowColors(True)

        # Set size policy to expand with window
        self.shot_table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        main_layout.addWidget(self.shot_table)
        
        button_layout = QtWidgets.QHBoxLayout()
        
        self.add_shots_btn = QtWidgets.QPushButton("Add Shots")
        self.add_shots_btn.setMinimumHeight(30)
        button_layout.addWidget(self.add_shots_btn)
        
        self.update_versions_btn = QtWidgets.QPushButton("Update All Versions")
        self.update_versions_btn.setMinimumHeight(30)
        button_layout.addWidget(self.update_versions_btn)
        
        self.validate_all_btn = QtWidgets.QPushButton("Validate All")
        self.validate_all_btn.setMinimumHeight(30)
        button_layout.addWidget(self.validate_all_btn)
        
        self.save_all_btn = QtWidgets.QPushButton("Save All")
        self.save_all_btn.setMinimumHeight(30)
        button_layout.addWidget(self.save_all_btn)
        
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        self.statusBar().showMessage("Ready")
    
    def _connect_signals(self):
        self.add_shots_btn.clicked.connect(self._on_add_shots)
    
    def _load_config(self):
        """Load project configuration."""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'project_configs', 'ctx_config.json')
            config_path = os.path.abspath(config_path)

            if not os.path.exists(config_path):
                self.statusBar().showMessage("Config file not found")
                return

            self._config = ProjectConfig(config_path)

            # Set config path in CTX_Manager node
            manager = self._context_manager.get_or_create_manager()
            manager.set_config_path(config_path)

            self.statusBar().showMessage("Config loaded")
            logger.info("Config loaded from: %s", config_path)
        except Exception as e:
            logger.error("Failed to load config: %s", e)
            self.statusBar().showMessage("Failed to load config")

    def _load_existing_shots(self):
        """Load existing CTX_Shot nodes from scene."""
        try:
            # Get all existing shots from scene
            existing_shots = self._context_manager.get_all_shots()

            if not existing_shots:
                logger.info("No existing shots found in scene")
                return

            logger.info("Found %d existing shots in scene", len(existing_shots))

            # Clear current table
            self.shot_table.setRowCount(0)
            self._shots = []

            # Add each shot to table
            for shot_node in existing_shots:
                shot_data = {
                    'project': self._config.get_project_code() if self._config else 'SWA',
                    'ep': shot_node.get_ep_code(),
                    'seq': shot_node.get_seq_code(),
                    'shot': shot_node.get_shot_code(),
                    'ctx_node': shot_node,  # Store reference to CTX node
                    'version': 'v001',  # TODO: Get from shot node
                    'is_active': shot_node.is_active()
                }

                self._add_shot_to_table(shot_data)

            # Find and set active shot
            for idx, shot_data in enumerate(self._shots):
                if shot_data['is_active']:
                    self._active_shot_index = idx
                    self._update_current_shot_display()
                    self._update_set_button(idx)
                    break

            logger.info("Loaded %d shots from scene", len(self._shots))

            # Adjust window size to fit content
            self._adjust_window_size()

        except Exception as e:
            logger.error("Failed to load existing shots: %s", e)
            self.statusBar().showMessage("Failed to load existing shots")
    
    def _on_add_shots(self):
        """Handle Add Shots button click."""
        from ui.add_shot_dialog import AddShotDialog

        dialog = AddShotDialog(self._config, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected_shots = dialog.get_selected_shots()
            self._add_shots_to_table(selected_shots)

    def _check_shot_version_status(self, shot_data):
        """Check if shot has any outdated assets.

        Args:
            shot_data: Dict with keys: project, ep, seq, shot

        Returns:
            dict: {'status': 'latest'|'outdated'|'unknown', 'text': 'Latest'|'Outdated'|'Unknown'}
        """
        import re

        if not self._config:
            return {'status': 'unknown', 'text': 'Unknown'}

        try:
            # Get base publish path for this shot
            proj_root = self._config.get_root('projRoot')
            project_code = self._config.get_project_code()
            scene_base = self._config.get_static_path('sceneBase')

            if not all([proj_root, project_code, scene_base]):
                return {'status': 'unknown', 'text': 'Unknown'}

            shot_base = os.path.join(
                proj_root,
                project_code,
                scene_base,
                shot_data['ep'],
                shot_data['seq'],
                shot_data['shot']
            )

            if not os.path.exists(shot_base):
                return {'status': 'unknown', 'text': 'Unknown'}

            # Quick scan: check if any department has multiple versions
            has_assets = False
            has_outdated = False

            departments = ['anim', 'layout', 'fx', 'lighting']
            for dept in departments:
                dept_path = os.path.join(shot_base, dept, 'publish')
                if not os.path.exists(dept_path):
                    continue

                # Get all version directories
                versions = []
                for item in os.listdir(dept_path):
                    item_path = os.path.join(dept_path, item)
                    if os.path.isdir(item_path) and re.match(r'v\d{3}', item):
                        versions.append(item)

                if versions:
                    has_assets = True
                    # If there are multiple versions, assume some might be outdated
                    if len(versions) > 1:
                        has_outdated = True
                        break

            if not has_assets:
                return {'status': 'unknown', 'text': 'No Assets'}

            if has_outdated:
                return {'status': 'outdated', 'text': 'Outdated'}
            else:
                return {'status': 'latest', 'text': 'Latest'}

        except Exception as e:
            logger.error("Failed to check version status: %s", e)
            return {'status': 'unknown', 'text': 'Unknown'}

    def _add_shots_to_table(self, selected_shots):
        """Add selected shots to the table and create CTX_Shot nodes.

        Args:
            selected_shots: List of shot dicts with keys: project, ep, seq, shot
        """
        for shot_data in selected_shots:
            # Check if shot already exists in UI table
            shot_id = "{}_{}_{}" .format(shot_data['ep'], shot_data['seq'], shot_data['shot'])
            exists_in_table = False
            for existing in self._shots:
                existing_id = "{}_{}_{}" .format(existing['ep'], existing['seq'], existing['shot'])
                if existing_id == shot_id:
                    exists_in_table = True
                    logger.warning("Shot %s already exists in table, skipping", shot_id)
                    break

            if exists_in_table:
                continue

            # Check if CTX_Shot node already exists in scene
            try:
                existing_shots = self._context_manager.get_all_shots()
                ctx_shot = None

                for existing_shot in existing_shots:
                    if (existing_shot.get_ep_code() == shot_data['ep'] and
                        existing_shot.get_seq_code() == shot_data['seq'] and
                        existing_shot.get_shot_code() == shot_data['shot']):
                        ctx_shot = existing_shot
                        logger.info("Found existing CTX_Shot node: %s", ctx_shot.node_name)
                        break

                # Create new CTX_Shot node if not found
                if not ctx_shot:
                    ctx_shot = self._context_manager.create_shot(
                        shot_data['ep'],
                        shot_data['seq'],
                        shot_data['shot']
                    )
                    logger.info("Created new CTX_Shot node: %s", ctx_shot.node_name)

                    # Scan filesystem and create CTX_Asset nodes for new shots only
                    if self._config:
                        scanner = AssetScanner(self._config)
                        created_assets = scanner.scan_shot_assets(ctx_shot)
                        logger.info("Created {} CTX_Asset nodes for shot {}".format(
                            len(created_assets), shot_id))

                shot_data['ctx_node'] = ctx_shot

            except Exception as e:
                logger.error("Failed to create/find CTX_Shot node: %s", e)
                QtWidgets.QMessageBox.warning(
                    self,
                    "Error",
                    "Failed to create shot node for {}: {}".format(shot_id, e)
                )
                continue

            # Add to table
            self._add_shot_to_table(shot_data)

        # Set first shot as active if no active shot
        if self._shots and self._active_shot_index is None:
            self._on_set_shot(0)

        # Adjust window size to fit new content
        self._adjust_window_size()

    def _add_shot_to_table(self, shot_data):
        """Add a single shot to the table.

        Args:
            shot_data: Dict with keys: project, ep, seq, shot, ctx_node
        """
        row = self.shot_table.rowCount()
        self.shot_table.insertRow(row)

        # Column 0: Row number
        self.shot_table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(row + 1)))

        # Column 1: Shot path (PROJECT_EPISODE_SEQUENCE_SHOT)
        shot_path = "{}_{}_{}_{}".format(
            shot_data['project'], shot_data['ep'], shot_data['seq'], shot_data['shot']
        )
        self.shot_table.setItem(row, 1, QtWidgets.QTableWidgetItem(shot_path))

        # Column 2: Set Shot button
        set_btn = QtWidgets.QPushButton("Set")
        set_btn.clicked.connect(lambda checked=False, r=row: self._on_set_shot(r))
        self.shot_table.setCellWidget(row, 2, set_btn)

        # Column 3: Version button - check asset status
        version_status = self._check_shot_version_status(shot_data)
        version_btn = QtWidgets.QPushButton(version_status['text'])
        if version_status['status'] == 'latest':
            version_btn.setStyleSheet("background-color: #2E7D32; color: white;")  # Green
        elif version_status['status'] == 'outdated':
            version_btn.setStyleSheet("background-color: #F57C00; color: white;")  # Orange
        else:
            version_btn.setStyleSheet("")  # Default
        version_btn.clicked.connect(lambda checked=False, r=row: self._on_version_click(r))
        self.shot_table.setCellWidget(row, 3, version_btn)

        # Column 4: Remove button
        remove_btn = QtWidgets.QPushButton("X")
        remove_btn.clicked.connect(lambda checked=False, r=row: self._on_remove_shot(r))
        self.shot_table.setCellWidget(row, 4, remove_btn)

        # Column 5: Save button
        save_btn = QtWidgets.QPushButton("Save")
        save_btn.clicked.connect(lambda checked=False, r=row: self._on_save_shot(r))
        self.shot_table.setCellWidget(row, 5, save_btn)

        # Store shot data
        if 'version' not in shot_data:
            shot_data['version'] = 'v001'
        if 'is_active' not in shot_data:
            shot_data['is_active'] = False
        shot_data['version_status'] = version_status
        self._shots.append(shot_data)

    def _adjust_window_size(self):
        """Adjust window height to fit table content."""
        # Calculate required height based on number of rows
        row_count = self.shot_table.rowCount()
        if row_count == 0:
            return

        # Get row height (including header)
        row_height = self.shot_table.rowHeight(0) if row_count > 0 else 30
        header_height = self.shot_table.horizontalHeader().height()

        # Calculate table height needed
        table_height = header_height + (row_height * row_count) + 4  # +4 for borders

        # Add heights of other widgets
        current_shot_height = self.current_shot_label.sizeHint().height()
        controller_label_height = 30  # Approximate
        button_layout_height = 50  # Approximate
        status_bar_height = self.statusBar().height()

        # Calculate total height with margins
        total_height = (current_shot_height + controller_label_height +
                       table_height + button_layout_height +
                       status_bar_height + 60)  # +60 for margins and spacing

        # Limit maximum height to 80% of screen
        try:
            from maya import OpenMayaUI as omui
            from shiboken2 import wrapInstance
            maya_main_window_ptr = omui.MQtUtil.mainWindow()
            maya_main_window = wrapInstance(int(maya_main_window_ptr), QtWidgets.QWidget)
            screen_height = maya_main_window.screen().availableGeometry().height()
            max_height = int(screen_height * 0.8)
        except:
            max_height = 800

        # Set height (but keep current width)
        new_height = min(total_height, max_height)
        current_width = self.width()
        self.resize(current_width, new_height)

    def _on_set_shot(self, row):
        """Handle Set Shot button click.

        Args:
            row: Table row index
        """
        # Deactivate previous active shot
        if self._active_shot_index is not None:
            prev_shot_data = self._shots[self._active_shot_index]
            prev_shot_data['is_active'] = False

            # Update CTX node
            if 'ctx_node' in prev_shot_data and prev_shot_data['ctx_node']:
                try:
                    prev_shot_data['ctx_node'].set_active(False)
                except Exception as e:
                    logger.error("Failed to deactivate CTX node: %s", e)

            # Update button
            prev_btn = self.shot_table.cellWidget(self._active_shot_index, 2)
            if prev_btn:
                prev_btn.setText("Set")
                prev_btn.setStyleSheet("")

        # Activate new shot
        self._active_shot_index = row
        shot_data = self._shots[row]
        shot_data['is_active'] = True

        # Update CTX node
        if 'ctx_node' in shot_data and shot_data['ctx_node']:
            try:
                shot_data['ctx_node'].set_active(True)
                self._context_manager.set_active_shot(shot_data['ctx_node'])
                logger.info("Set active shot in CTX: %s", shot_data['ctx_node'].node_name)
            except Exception as e:
                logger.error("Failed to activate CTX node: %s", e)

        # Update button
        set_btn = self.shot_table.cellWidget(row, 2)
        if set_btn:
            set_btn.setText("Active")
            set_btn.setStyleSheet("background-color: #4A90E2; color: white; font-weight: bold;")

        # Update current shot display
        self._update_current_shot_display()

        shot_path = "{}_{}_{}_{}".format(
            shot_data['project'], shot_data['ep'], shot_data['seq'], shot_data['shot']
        )
        logger.info("Active shot set to: %s", shot_path)
        self.statusBar().showMessage("Active shot: {}".format(shot_path))

    def _update_current_shot_display(self):
        """Update the current shot label."""
        if self._active_shot_index is not None:
            shot_data = self._shots[self._active_shot_index]
            shot_path = "{}_{}_{}_{}".format(
                shot_data['project'], shot_data['ep'], shot_data['seq'], shot_data['shot']
            )
            self.current_shot_label.setText("Current Shot: {}".format(shot_path))
        else:
            self.current_shot_label.setText("Current Shot: None")

    def _update_set_button(self, row):
        """Update the Set button for a specific row.

        Args:
            row: Table row index
        """
        shot_data = self._shots[row]
        set_btn = self.shot_table.cellWidget(row, 2)
        if set_btn:
            if shot_data.get('is_active', False):
                set_btn.setText("Active")
                set_btn.setStyleSheet("background-color: #4A90E2; color: white; font-weight: bold;")
            else:
                set_btn.setText("Set")
                set_btn.setStyleSheet("")

    def _on_context_changed(self, event_type, data):
        """Callback for context change events.

        Triggered by ContextManager when shot is switched, version updated, etc.
        Handles token-based path resolution when active shot changes.

        Args:
            event_type (str): Type of event ('shot_switched', 'shot_created', etc.)
            data (dict): Event data
        """
        if event_type == 'shot_switched':
            shot_node = data.get('shot')
            if shot_node:
                logger.info("Context changed: shot_switched -> %s",
                            shot_node.node_name)
                self._resolve_shot_paths(shot_node)

    def _resolve_shot_paths(self, shot_node):
        """Resolve template paths for all assets in a shot and update Maya nodes.

        This is the core token-based path resolution workflow:
        Template (on CTX_Asset) -> Token expansion -> Apply to Maya node.

        Args:
            shot_node: CTXShotNode instance
        """
        if not self._config:
            logger.warning("No config loaded, cannot resolve paths")
            return

        try:
            platform_config = PlatformConfig(self._config)
            node_manager = NodeManager()

            count = node_manager.update_shot_paths(
                shot_node, self._config, platform_config)

            if count > 0:
                self.statusBar().showMessage(
                    "Updated {} asset path(s)".format(count))
                logger.info("Resolved %d asset paths for shot %s",
                            count, shot_node.node_name)
            else:
                logger.info("No asset paths to update for shot %s",
                            shot_node.node_name)

        except Exception as e:
            logger.error("Failed to resolve shot paths: %s", e)
            self.statusBar().showMessage("Path resolution failed: {}".format(e))

    def _on_version_click(self, row):
        """Handle Version button click.

        Args:
            row: Table row index
        """
        from ui.asset_manager_dialog import AssetManagerDialog

        shot_data = self._shots[row]
        shot_id = "{}_{}_{}_{}".format(
            shot_data['project'],
            shot_data['ep'],
            shot_data['seq'],
            shot_data['shot']
        )
        logger.info("Opening Asset Manager for shot: %s", shot_id)

        # Check if dialog already exists for this shot
        if shot_id in self._asset_manager_dialogs:
            # Bring existing dialog to front
            existing_dialog = self._asset_manager_dialogs[shot_id]
            existing_dialog.raise_()
            existing_dialog.activateWindow()
            logger.info("Bringing existing Asset Manager to front")
            return

        # Use show() instead of exec_() to make it non-modal (non-blocking)
        dialog = AssetManagerDialog(shot_data, self._config, self)

        # Store reference to prevent garbage collection
        self._asset_manager_dialogs[shot_id] = dialog

        # Remove from dict when dialog is closed
        def on_dialog_closed():
            if shot_id in self._asset_manager_dialogs:
                del self._asset_manager_dialogs[shot_id]
                logger.info("Asset Manager closed for shot: %s", shot_id)

        dialog.finished.connect(on_dialog_closed)
        dialog.show()

        # Note: We don't wait for dialog to close anymore since it's non-modal
        # The dialog will update CTX nodes directly when user clicks Apply

    def _update_version_button(self, row):
        """Update version button status for a shot.

        Args:
            row: Table row index
        """
        shot_data = self._shots[row]
        version_status = self._check_shot_version_status(shot_data)

        # Update button
        version_btn = self.shot_table.cellWidget(row, 3)
        if version_btn:
            version_btn.setText(version_status['text'])
            if version_status['status'] == 'latest':
                version_btn.setStyleSheet("background-color: #2E7D32; color: white;")  # Green
            elif version_status['status'] == 'outdated':
                version_btn.setStyleSheet("background-color: #F57C00; color: white;")  # Orange
            else:
                version_btn.setStyleSheet("")  # Default

        # Update stored data
        shot_data['version_status'] = version_status

    def _on_remove_shot(self, row):
        """Handle Remove button click.

        Args:
            row: Table row index
        """
        shot_data = self._shots[row]
        shot_path = "{}_{}_{}_{}".format(
            shot_data['project'], shot_data['ep'], shot_data['seq'], shot_data['shot']
        )

        reply = QtWidgets.QMessageBox.question(
            self,
            "Remove Shot",
            "Remove shot {} from scene?\n\nThis will delete the CTX_Shot node and all associated CTX_Asset nodes.".format(shot_path),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            # Delete CTX node
            if 'ctx_node' in shot_data and shot_data['ctx_node']:
                try:
                    self._context_manager.delete_shot(shot_data['ctx_node'])
                    logger.info("Deleted CTX_Shot node: %s", shot_data['ctx_node'].node_name)
                except Exception as e:
                    logger.error("Failed to delete CTX node: %s", e)
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Error",
                        "Failed to delete CTX node: {}".format(e)
                    )

            # Remove from table
            self.shot_table.removeRow(row)

            # Remove from shots list
            del self._shots[row]

            # Update active shot index
            if self._active_shot_index == row:
                self._active_shot_index = None
                self.current_shot_label.setText("Current Shot: None")

                # Set first shot as active if available
                if self._shots:
                    self._on_set_shot(0)
            elif self._active_shot_index is not None and self._active_shot_index > row:
                self._active_shot_index -= 1

            # Update row numbers
            for i in range(self.shot_table.rowCount()):
                self.shot_table.item(i, 0).setText(str(i + 1))

            logger.info("Removed shot: %s", shot_path)
            self.statusBar().showMessage("Removed shot: {}".format(shot_path))

    def _on_save_shot(self, row):
        """Handle Save button click.

        Args:
            row: Table row index
        """
        # TODO: Implement save to shot directory
        shot_data = self._shots[row]
        shot_path = "{}_{}_{}_{}".format(
            shot_data['project'], shot_data['ep'], shot_data['seq'], shot_data['shot']
        )
        logger.info("Save clicked for shot: %s", shot_path)
        QtWidgets.QMessageBox.information(
            self,
            "Save Shot",
            "Save functionality will be implemented in Phase 4C.\n\nWill save scene to: {}".format(shot_path)
        )

    def _on_update_versions(self):
        """Handle Update All Versions button click."""
        logger.info("Update All Versions clicked")
        QtWidgets.QMessageBox.information(
            self,
            "Update Versions",
            "Update All Versions will be implemented in Phase 4C."
        )

    def _on_validate_all(self):
        """Handle Validate All button click."""
        logger.info("Validate All clicked")
        QtWidgets.QMessageBox.information(
            self,
            "Validate All",
            "Validate All will be implemented in Phase 4C."
        )

    def _on_save_all(self):
        """Handle Save All button click."""
        logger.info("Save All clicked")
        QtWidgets.QMessageBox.information(
            self,
            "Save All",
            "Save All will be implemented in Phase 4C.\n\nWill save scene to all shot directories."
        )
