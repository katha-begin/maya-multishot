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
from core.nodes.wrappers import CTXManagerNode, CTXShotNode
from core.asset_scanner import AssetScanner
from core.nodes import NodeManager
from core.display_layers import DisplayLayerManager
from core.shot_switching import ShotSwitcher

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
        self._platform_config = None
        self._context_manager = ContextManager()
        self._shots = []  # List of dicts with shot data + CTX node reference
        self._active_shot_index = None
        self._asset_manager_dialogs = {}  # Store references to prevent garbage collection
        self._gaffer_manager_dialog = None  # Single Gaffer Manager instance
        self._slate_manager_dialog = None  # Single Slate Manager instance
        # Light originals are persisted in CTX_LightOriginals node (no in-memory snapshot needed)

        # Initialize display layer management
        self._layer_manager = DisplayLayerManager()
        self._shot_switcher = ShotSwitcher(
            self._layer_manager,
            self._context_manager
        )

        self._setup_ui()
        self._connect_signals()
        self._load_config()
        self._load_existing_shots()

        # Light originals are captured at add-time by GafferManager and
        # persisted in CTX_LightOriginals node -- no in-memory snapshot needed.

        # Register context change callback for path resolution
        self._context_manager.register_callback(self._on_context_changed)

        self._register_scene_callbacks()

        from core.batch import render_state as rs
        rs.add_listener(self._on_render_state_changed)

    def closeEvent(self, event):
        """Handle window close event."""
        # Unregister context callback
        self._context_manager.unregister_callback(self._on_context_changed)
        self._deregister_scene_callbacks()
        try:
            from core.batch import render_state as rs
            rs.remove_listener(self._on_render_state_changed)
        except Exception:
            pass
        # Close Slate Manager if open
        try:
            from ui.slate_manager_dialog import SlateManagerDialog
            if SlateManagerDialog._instance is not None:
                try:
                    SlateManagerDialog._instance.close()
                except Exception:
                    pass
                SlateManagerDialog._instance = None
        except Exception:
            pass
        # Clear instance reference when window is closed
        MainWindow._instance = None
        super(MainWindow, self).closeEvent(event)
    
    def _setup_ui(self):
        self.setWindowTitle("Multishot Manager")
        self.setObjectName("MultishotManagerWindow")

        # Qt::Tool + parented to Maya main window keeps the window above Maya
        # without forcing it above other applications (browser, etc.)
        self.setWindowFlags(
            QtCore.Qt.Tool |
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowMinimizeButtonHint |
            QtCore.Qt.WindowMaximizeButtonHint
        )

        # Set initial size based on content (will resize after table is populated)
        # Use static method since table doesn't exist yet
        initial_width = MainWindow.get_recommended_width()
        self.resize(initial_width, 400)
        
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        self.current_shot_label = QtWidgets.QLabel("Current Shot: None")
        self.current_shot_label.setStyleSheet("font-weight: bold; font-size: 12pt; padding: 5px;")
        main_layout.addWidget(self.current_shot_label)

        # Header with label and search box
        header_layout = QtWidgets.QHBoxLayout()

        controller_label = QtWidgets.QLabel("SHOT CONTEXT CONTROLLER")
        controller_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        header_layout.addWidget(controller_label)

        header_layout.addStretch()

        # Search box
        search_label = QtWidgets.QLabel("Search:")
        header_layout.addWidget(search_label)

        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Filter shots...")
        self.search_box.setMinimumWidth(200)
        self.search_box.setClearButtonEnabled(True)
        header_layout.addWidget(self.search_box)

        main_layout.addLayout(header_layout)
        
        self.shot_table = QtWidgets.QTableWidget()
        self.shot_table.setColumnCount(9)
        self.shot_table.setHorizontalHeaderLabels(
            ["#", "Lck", "Shot", "Frame Range", "Set", "Ver", "Gaf", "Slt", "Rnd"]
        )

        # Set column widths -- Shot column stretches like Light column in Gaffer Manager
        header = self.shot_table.horizontalHeader()
        header.setStretchLastSection(False)

        # Column 0: # - minimal width for row numbers
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self.shot_table.setColumnWidth(0, 20)

        # Column 1: Lck - fixed 20px, no resize
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        self.shot_table.setColumnWidth(1, 20)

        # Column 2: Shot - stretches to fill available space (matches Gaffer's Light column)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)

        # Column 3: Frame Range - compact, fits "1001-1100"
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)
        self.shot_table.setColumnWidth(3, 75)

        # Column 4: Set button (3-char label)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.Fixed)
        self.shot_table.setColumnWidth(4, 38)

        # Column 5: Version button (3-char label)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.Fixed)
        self.shot_table.setColumnWidth(5, 38)

        # Column 6: Gaffer button (3-char label)
        header.setSectionResizeMode(6, QtWidgets.QHeaderView.Fixed)
        self.shot_table.setColumnWidth(6, 38)

        # Column 7: Slate button (3-char label)
        header.setSectionResizeMode(7, QtWidgets.QHeaderView.Fixed)
        self.shot_table.setColumnWidth(7, 38)

        # Column 8: Render status dot
        header.setSectionResizeMode(8, QtWidgets.QHeaderView.Fixed)
        self.shot_table.setColumnWidth(8, 28)

        # Enable multi-selection and row selection
        self.shot_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.shot_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.shot_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.shot_table.setAlternatingRowColors(True)

        # Compact row height to match Gaffer Manager (22px)
        self.shot_table.verticalHeader().setDefaultSectionSize(22)
        # Hide vertical header -- the # column already shows row numbers
        self.shot_table.verticalHeader().setVisible(False)

        # Enable context menu
        self.shot_table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.shot_table.customContextMenuRequested.connect(self._show_context_menu)

        # Set size policy to expand with window
        self.shot_table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        main_layout.addWidget(self.shot_table)
        
        button_layout = QtWidgets.QHBoxLayout()

        self.add_shots_btn = QtWidgets.QPushButton("Add Shots")
        self.add_shots_btn.setFixedHeight(24)
        button_layout.addWidget(self.add_shots_btn)

        self.update_versions_btn = QtWidgets.QPushButton("Update All Versions")
        self.update_versions_btn.setFixedHeight(24)
        button_layout.addWidget(self.update_versions_btn)

        self.validate_all_btn = QtWidgets.QPushButton("Validate All")
        self.validate_all_btn.setFixedHeight(24)
        button_layout.addWidget(self.validate_all_btn)

        self.save_all_btn = QtWidgets.QPushButton("Save All")
        self.save_all_btn.setFixedHeight(24)
        button_layout.addWidget(self.save_all_btn)

        button_layout.addStretch()

        self.delete_all_btn = QtWidgets.QPushButton("Delete All")
        self.delete_all_btn.setFixedHeight(24)
        self.delete_all_btn.setStyleSheet("background-color: #D32F2F; color: white; font-weight: bold;")
        button_layout.addWidget(self.delete_all_btn)

        main_layout.addLayout(button_layout)

        # Create menu bar
        self._create_menu_bar()

        self.statusBar().showMessage("Ready")

    def _calculate_table_width(self):
        """Calculate the optimal width for the window based on table column widths.

        Returns:
            int: Calculated width in pixels
        """
        # Sum up all column widths
        total_column_width = 0
        for col in range(self.shot_table.columnCount()):
            total_column_width += self.shot_table.columnWidth(col)

        # Add extra space for margins, scrollbar, and padding
        scrollbar_width = 20  # Vertical scrollbar
        margins = 40  # Left and right margins (20 + 20)
        padding = 10  # Extra padding for borders

        calculated_width = total_column_width + scrollbar_width + margins + padding

        return calculated_width

    @staticmethod
    def get_recommended_width():
        """Get recommended window width based on column configuration.

        This is a static method that can be called without creating an instance.
        Useful for setting initial dock control width.

        Returns:
            int: Recommended width in pixels
        """
        # Column 2 (Shot) stretches; use 180px as its minimum contribution
        column_widths = [20, 20, 180, 75, 38, 38, 38, 38, 28]
        total_column_width = sum(column_widths)

        # Add extra space for margins, scrollbar, and padding
        scrollbar_width = 20
        margins = 40
        padding = 10

        return total_column_width + scrollbar_width + margins + padding

    def _create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()

        # Tools menu
        tools_menu = menubar.addMenu("Tools")

        # Gaffer Manager action
        gaffer_action = QtWidgets.QAction("Gaffer Manager", self)
        gaffer_action.setStatusTip("Open Light Gaffer Manager")
        gaffer_action.triggered.connect(self._open_gaffer_manager)
        tools_menu.addAction(gaffer_action)

        # Slate Manager action
        slate_action = QtWidgets.QAction("Slate Manager", self)
        slate_action.setStatusTip("Open Render Layer Slate Manager")
        slate_action.triggered.connect(self._open_slate_manager)
        tools_menu.addAction(slate_action)

        # Settings action (existing functionality)
        settings_action = QtWidgets.QAction("Settings", self)
        settings_action.setStatusTip("Open Settings")
        settings_action.triggered.connect(self._open_settings)
        tools_menu.addAction(settings_action)

        tools_menu.addSeparator()

        # Reload action -- closes and reopens both windows with fresh modules
        reload_action = QtWidgets.QAction("Reload All Tools", self)
        reload_action.setStatusTip("Reload all modules and reopen Multishot Manager")
        reload_action.setShortcut("Ctrl+Shift+R")
        reload_action.triggered.connect(self._reload_all_tools)
        tools_menu.addAction(reload_action)

    def _reload_all_tools(self):
        """Reload all project modules and reopen this window with fresh code.

        Closes the Gaffer Manager (if open), reloads all modules, then
        relaunches the Multishot Manager so new flags/parenting take effect.
        """
        try:
            import sys
            import importlib

            # Close Gaffer Manager first so it is recreated with correct parent
            from ui.gaffer_manager_dialog import GafferManagerDialog
            if GafferManagerDialog._instance is not None:
                try:
                    GafferManagerDialog._instance.close()
                except Exception:
                    pass

            # Close Slate Manager so it is recreated with correct parent
            try:
                from ui.slate_manager_dialog import SlateManagerDialog
                if SlateManagerDialog._instance is not None:
                    try:
                        SlateManagerDialog._instance.close()
                    except Exception:
                        pass
                    SlateManagerDialog._instance = None
            except Exception:
                pass

            # Reload all project modules
            prefixes = ('core.', 'ui.', 'tools.', 'utils.',
                        'core', 'ui', 'tools', 'utils')
            to_reload = [
                name for name, mod in list(sys.modules.items())
                if mod is not None and name.startswith(prefixes)
            ]
            for name in reversed(to_reload):
                try:
                    importlib.reload(sys.modules[name])
                except Exception:
                    pass

            # Close this window -- the launch below will create a fresh one
            self.close()

            # Relaunch via the same entry point used by the launch script
            from tools.maya_menu import open_context_manager
            open_context_manager()

        except Exception as e:
            logger.error("Reload failed: {}".format(e))
            import traceback
            traceback.print_exc()

    def _open_gaffer_manager(self):
        """Open the Gaffer Manager dialog."""
        try:
            from ui.gaffer_manager_dialog import GafferManagerDialog
            self._gaffer_manager_dialog = GafferManagerDialog.open_or_raise(parent=self)
            logger.info("Opened Gaffer Manager")
            self.statusBar().showMessage("Gaffer Manager opened")
        except Exception as e:
            logger.error("Failed to open Gaffer Manager: {}".format(e))
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                "Failed to open Gaffer Manager:\n{}".format(e)
            )

    def _on_gaffer_click(self, row):
        """Handle Gaffer button click on a shot row.

        Creates a shot-level gaffer if one does not exist, auto-wires it to
        the sequence gaffer (if present), then opens the Gaffer Manager.

        Args:
            row (int): Shot table row index
        """
        if row >= len(self._shots):
            return

        shot_data = self._shots[row]
        ctx_node = shot_data.get('ctx_node')
        if not ctx_node:
            return

        try:
            import maya.cmds as cmds
        except ImportError:
            QtWidgets.QMessageBox.warning(
                self, "Maya Not Available", "Maya is not available."
            )
            return

        try:
            from core.nodes.wrappers import CTXLightGafferNode
            from ui.gaffer_manager_dialog import GafferManagerDialog

            # Check if shot already has a gaffer
            existing_gaffer_name = ctx_node.get_gaffer()
            if existing_gaffer_name:
                gaffer = CTXLightGafferNode(existing_gaffer_name)
            else:
                # Create shot-level gaffer named after the shot
                shot_id = "{}_{}".format(ctx_node.get_seq_code(), ctx_node.get_shot_code())
                gaffer = CTXLightGafferNode.create(
                    gafferName=shot_id,
                    gafferType='shot'
                )
                ctx_node.set_gaffer(gaffer)

                # Auto-wire parentGaffer chain: seq gaffer first, then master
                try:
                    wired = False
                    from core.nodes.wrappers import CTXSequenceNode
                    seq_name = ctx_node.get_parent_sequence()
                    if seq_name:
                        seq = CTXSequenceNode(seq_name)
                        seq_gaffer_name = seq.get_gaffer()
                        if seq_gaffer_name:
                            seq_gaffer = CTXLightGafferNode(seq_gaffer_name)
                            gaffer.set_parent_gaffer(seq_gaffer)
                            logger.info("Auto-wired shot gaffer to sequence gaffer: {}".format(seq_gaffer_name))
                            wired = True

                    if not wired:
                        # No sequence gaffer -- wire directly to master gaffer
                        from core.gaffer.chain_ops import ChainOperations
                        all_gaffers = ChainOperations.list_all_gaffers()
                        master_gaffers = [g['wrapper'] for g in all_gaffers
                                          if g.get('type') == 'master']
                        if master_gaffers:
                            gaffer.set_parent_gaffer(master_gaffers[0])
                            logger.info("Auto-wired shot gaffer to master gaffer: {}".format(
                                master_gaffers[0].node_name))
                except Exception as e:
                    logger.warning("Could not auto-wire gaffer chain: {}".format(e))

                # Update button appearance
                gaffer_btn = self.shot_table.cellWidget(row, 6)
                if gaffer_btn:
                    gaffer_btn.setText("GAF")
                    gaffer_btn.setStyleSheet("background-color: #1565C0; color: white;")

                logger.info("Created shot gaffer: {}".format(gaffer.node_name))

            # Open / refresh Gaffer Manager and pre-select this gaffer
            self._open_gaffer_manager_for(gaffer)

        except Exception as e:
            logger.error("Gaffer button error: {}".format(e))
            QtWidgets.QMessageBox.critical(
                self, "Error", "Failed to open gaffer:\n{}".format(e)
            )

    def _open_gaffer_manager_for(self, gaffer):
        """Open (or bring to front) the Gaffer Manager and select a specific gaffer.

        Args:
            gaffer (CTXLightGafferNode): Gaffer to pre-select
        """
        try:
            from ui.gaffer_manager_dialog import GafferManagerDialog
            self._gaffer_manager_dialog = GafferManagerDialog.open_or_raise(parent=self)
            self._gaffer_manager_dialog.select_gaffer(gaffer)
        except Exception as e:
            logger.error("Failed to open Gaffer Manager for gaffer: {}".format(e))

    def _open_slate_manager(self):
        """Open the Slate Manager dialog."""
        try:
            from ui.slate_manager_dialog import SlateManagerDialog
            self._slate_manager_dialog = SlateManagerDialog.open_or_raise(parent=self)
            logger.info("Opened Slate Manager")
            self.statusBar().showMessage("Slate Manager opened")
        except Exception as e:
            logger.error("Failed to open Slate Manager: %s", e)
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                "Failed to open Slate Manager:\n{}".format(e)
            )

    def _open_slate_manager_for(self, slate):
        """Open (or bring to front) the Slate Manager and select a specific slate.

        Args:
            slate (CTXSlateNode): Slate to pre-select.
        """
        try:
            from ui.slate_manager_dialog import SlateManagerDialog
            self._slate_manager_dialog = SlateManagerDialog.open_or_raise(parent=self)
            self._slate_manager_dialog.select_slate(slate)
        except Exception as e:
            logger.error("Failed to open Slate Manager for slate: %s", e)

    def _on_slate_click(self, row):
        """Handle Slate button click on a shot row.

        Creates a shot-level slate if one does not exist, auto-wires it to
        the sequence slate (if present), then opens the Slate Manager.

        Args:
            row (int): Table row index.
        """
        if row < 0 or row >= len(self._shots):
            return

        shot_data = self._shots[row]
        ctx_node = shot_data.get('ctx_node')
        if ctx_node is None:
            return

        try:
            from core.slate.manager import SlateManager
            from ui.slate_manager_dialog import SlateManagerDialog

            slate = SlateManager.get_or_create_shot_slate(ctx_node)

            # Update button appearance
            slate_btn = self.shot_table.cellWidget(row, 7)
            if slate_btn:
                slate_btn.setText("SLT")
                slate_btn.setStyleSheet("background-color: #1565C0; color: white;")

            logger.info("Opened slate: %s", slate.node_name)

            # Open / refresh Slate Manager and pre-select this slate
            self._open_slate_manager_for(slate)

        except Exception as exc:
            logger.error("Slate button error: %s", exc)
            QtWidgets.QMessageBox.critical(
                self, "Error", "Failed to open slate:\n{}".format(exc)
            )

    def _open_settings(self):
        """Open the Settings dialog."""
        try:
            from ui.settings_dialog import SettingsDialog

            dialog = SettingsDialog(parent=self)
            dialog.exec_()

            logger.info("Opened Settings")

        except Exception as e:
            logger.error("Failed to open Settings: {}".format(e))
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                "Failed to open Settings:\n{}".format(e)
            )

    def _connect_signals(self):
        self.search_box.textChanged.connect(self._on_search_changed)
        self.add_shots_btn.clicked.connect(self._on_add_shots)
        self.delete_all_btn.clicked.connect(self._on_delete_all)
    
    def _load_config(self):
        """Load project configuration."""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'project_configs', 'ctx_config.json')
            config_path = os.path.abspath(config_path)

            if not os.path.exists(config_path):
                self.statusBar().showMessage("Config file not found")
                return

            self._config = ProjectConfig(config_path)

            try:
                self._platform_config = PlatformConfig(self._config)
            except Exception as exc:
                logger.warning("Failed to create platform config: %s", exc)
                self._platform_config = None

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

            # Initialize metadata loader if enabled
            metadata_loader = None
            print("=" * 80)
            print("DEBUG: Checking if metadata is enabled...")
            print("DEBUG: self._config = {}".format(self._config))

            if self._config:
                is_enabled = self._config.is_shot_metadata_enabled()
                print("DEBUG: is_shot_metadata_enabled() = {}".format(is_enabled))

                if is_enabled:
                    from core.shot_metadata_loader import ShotMetadataLoader
                    metadata_loader = ShotMetadataLoader(self._config)
                    print("Shot metadata import ENABLED")
                    logger.info("Shot metadata import enabled")
                else:
                    print("WARNING: Shot metadata import is DISABLED in config")
                    logger.warning("Shot metadata import is DISABLED in config")
            else:
                print("WARNING: Config is None, cannot load metadata")
                logger.warning("Config is None, cannot load metadata")

            # Clear current table
            self.shot_table.setRowCount(0)
            self._shots = []

            # Add each shot to table
            failed_shots = []
            for shot_node in existing_shots:
                node_label = shot_node.node_name if hasattr(shot_node, 'node_name') else str(shot_node)
                try:
                    # Load metadata from JSON if available
                    if metadata_loader:
                        shot_id = shot_node.get_shot_id()
                        shot_root = self._build_shot_root_path(shot_node)
                        metadata = metadata_loader.load_all_metadata(shot_id, shot_root)

                        # Update CTX_Shot node with metadata
                        if 'frame_range' in metadata:
                            start, end = metadata['frame_range']
                            try:
                                shot_node.set_frame_range(start, end)
                            except Exception as fr_err:
                                logger.warning("Could not update frame range for %s: %s", node_label, fr_err)

                        if 'fps' in metadata:
                            try:
                                shot_node.set_fps(metadata['fps'])
                            except Exception as fps_err:
                                logger.warning("Could not update FPS for %s: %s", node_label, fps_err)

                    shot_data = {
                        'project': self._config.get_project_code() if self._config else 'SWA',
                        'ep': shot_node.get_ep_code(),
                        'seq': shot_node.get_seq_code(),
                        'shot': shot_node.get_shot_code(),
                        'ctx_node': shot_node,
                        'version': 'v001',
                        'is_active': shot_node.is_active()
                    }

                    self._add_shot_to_table(shot_data)

                except Exception as shot_err:
                    logger.error("Failed to load shot %s: %s", node_label, shot_err)
                    import traceback
                    traceback.print_exc()
                    failed_shots.append(node_label)

            if failed_shots:
                logger.warning("Skipped %d shot(s) due to errors: %s", len(failed_shots), failed_shots)

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

    def _build_shot_root_path(self, shot_node):
        """Build shot root directory path using template system.

        Args:
            shot_node (CTXShotNode): Shot node

        Returns:
            str: Shot root path (e.g., "v:/SWA/all/scene/Ep04/sq0070/SH0180")
        """
        if not self._config:
            print("WARNING: _build_shot_root_path - config is None")
            return None

        try:
            # Use PathResolver to resolve shotRoot template
            from core.resolver import PathResolver
            from config.platform_config import PlatformConfig

            platform_config = PlatformConfig(self._config)
            resolver = PathResolver(self._config, platform_config)

            # Build context dict for token resolution
            context = {
                'ep': shot_node.get_ep_code(),
                'seq': shot_node.get_seq_code(),
                'shot': shot_node.get_shot_code()
            }

            print("DEBUG: Resolving shotRoot with context: {}".format(context))

            # Resolve shotRoot template
            shot_path = resolver.resolve_path('shotRoot', context)

            print("DEBUG: Resolved shot_path: {}".format(shot_path))

            return shot_path

        except Exception as e:
            print("ERROR: Failed to resolve shot root path: {}".format(e))
            logger.error("Failed to resolve shot root path: %s", e)
            import traceback
            traceback.print_exc()
            return None

    def _parse_scene_filename(self):
        """Parse current Maya scene filename to extract dept and version.

        Supports two patterns:
        1. {ep}_{seq}_{shot}_{dept}_{ver}.ma
           Example: Ep04_sq0070_SH0180_lighting_v002.ma

        2. {ep}_{seq}_{shot}_{dept}_{variant}_{ver}.ma
           Example: Ep04_sq0070_SH0180_lighting_master_v002.ma

        Returns:
            dict: {'dept': str, 'version': str, 'variant': str or None}
                  Returns None if parsing fails
        """
        try:
            import maya.cmds as cmds
            import re

            scene_file = cmds.file(query=True, sceneName=True)
            if not scene_file:
                logger.debug("No scene file open")
                return None

            # Get just the filename without path and extension
            filename = os.path.basename(scene_file)
            name_without_ext = os.path.splitext(filename)[0]

            logger.debug("Parsing scene filename: {}".format(filename))

            # Split by underscore
            parts = name_without_ext.split('_')

            # Need at least: ep, seq, shot, dept, ver = 5 parts
            if len(parts) < 5:
                logger.debug("Filename has too few parts: {}".format(len(parts)))
                return None

            # Extract version (always last part, format: v###)
            version_part = parts[-1]
            version_match = re.match(r'v\d{3}', version_part)
            if not version_match:
                logger.debug("Last part is not a valid version: {}".format(version_part))
                return None

            version = version_part

            # Check if we have variant (6+ parts) or not (5 parts)
            if len(parts) == 5:
                # Pattern 1: {ep}_{seq}_{shot}_{dept}_{ver}
                dept = parts[3]
                variant = None
            elif len(parts) >= 6:
                # Pattern 2: {ep}_{seq}_{shot}_{dept}_{variant}_{ver}
                # or more complex: {ep}_{seq}_{shot}_{dept}_{variant1}_{variant2}_{ver}
                dept = parts[3]
                # Everything between dept and version is variant
                variant = '_'.join(parts[4:-1])
            else:
                logger.debug("Unexpected number of parts: {}".format(len(parts)))
                return None

            result = {
                'dept': dept,
                'version': version,
                'variant': variant
            }

            logger.info("Parsed scene filename: dept={}, version={}, variant={}".format(
                dept, version, variant))

            return result

        except Exception as e:
            logger.warning("Failed to parse scene filename: {}".format(e))
            return None

    def _get_current_dept(self):
        """Get current department from scene file or config fallback.

        Returns:
            str: Department code (e.g., 'lighting')
        """
        # Try to get from render settings config
        if self._config and self._config.is_render_settings_enabled():
            output_config = self._config.get_render_output_config()
            if output_config:
                dept_source = output_config.get('deptSource', 'config')

                if dept_source == 'sceneFile':
                    # Parse from scene filename
                    parsed = self._parse_scene_filename()
                    if parsed and parsed.get('dept'):
                        return parsed['dept']

                # Fallback to config default
                return output_config.get('deptFallback', 'lighting')

        # Ultimate fallback
        return 'lighting'

    def _get_current_version(self):
        """Get current version from scene file or config fallback.

        Returns:
            str: Version string (e.g., 'v002')
        """
        # Try to get from render settings config
        if self._config and self._config.is_render_settings_enabled():
            output_config = self._config.get_render_output_config()
            if output_config:
                version_source = output_config.get('versionSource', 'config')

                if version_source == 'sceneFile':
                    # Parse from scene filename
                    parsed = self._parse_scene_filename()
                    if parsed and parsed.get('version'):
                        return parsed['version']

                # Fallback to config default
                return output_config.get('versionFallback', 'v001')

        # Ultimate fallback
        return 'v001'

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
            return {'status': 'unknown', 'text': 'UNK'}

        try:
            # Get base publish path for this shot
            proj_root = self._config.get_root('projRoot')
            project_code = self._config.get_project_code()
            scene_base = self._config.get_static_path('sceneBase')

            if not all([proj_root, project_code, scene_base]):
                return {'status': 'unknown', 'text': 'UNK'}

            shot_base = os.path.join(
                proj_root,
                project_code,
                scene_base,
                shot_data['ep'],
                shot_data['seq'],
                shot_data['shot']
            )

            if not os.path.exists(shot_base):
                return {'status': 'unknown', 'text': 'UNK'}

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
                return {'status': 'unknown', 'text': 'N/A'}

            if has_outdated:
                return {'status': 'outdated', 'text': 'OTD'}
            else:
                return {'status': 'latest', 'text': 'OK'}

        except Exception as e:
            logger.error("Failed to check version status: %s", e)
            return {'status': 'unknown', 'text': 'UNK'}

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
                    print("\n" + "="*80)
                    print("CREATING NEW CTX_SHOT NODE FOR: {}".format(shot_id))
                    print("="*80)

                    ctx_shot = self._context_manager.create_shot(
                        shot_data['ep'],
                        shot_data['seq'],
                        shot_data['shot']
                    )
                    logger.info("Created new CTX_Shot node: %s", ctx_shot.node_name)
                    print("Created CTX_Shot node: {}".format(ctx_shot.node_name))

                    # Ensure global display layers exist (CTX_Active and CTX_Inactive)
                    try:
                        self._layer_manager.ensure_global_layers()
                        logger.info("Ensured global display layers exist (CTX_Active, CTX_Inactive)")
                    except Exception as e:
                        logger.error("Failed to ensure global display layers: %s", e)

                    # Load metadata from JSON if available
                    if self._config and self._config.is_shot_metadata_enabled():
                        print("\n" + "="*60)
                        print("DEBUG: Loading metadata for NEW shot: {}".format(shot_id))
                        try:
                            from core.shot_metadata_loader import ShotMetadataLoader
                            metadata_loader = ShotMetadataLoader(self._config)
                            shot_root = self._build_shot_root_path(ctx_shot)
                            print("DEBUG: Shot root path: {}".format(shot_root))

                            metadata = metadata_loader.load_all_metadata(shot_id, shot_root)
                            print("DEBUG: Loaded metadata: {}".format(metadata))

                            if 'frame_range' in metadata:
                                start, end = metadata['frame_range']
                                ctx_shot.set_frame_range(start, end)
                                print("DEBUG: Set frame range: {}-{}".format(start, end))
                                logger.info("Loaded frame range from JSON: {}-{}".format(start, end))

                            if 'fps' in metadata:
                                ctx_shot.set_fps(metadata['fps'])
                                print("DEBUG: Set FPS: {}".format(metadata['fps']))
                                logger.info("Loaded FPS from JSON: {}".format(metadata['fps']))
                        except Exception as e:
                            print("ERROR: Failed to load metadata: {}".format(e))
                            logger.error("Failed to load metadata for shot {}: {}".format(shot_id, e))
                        print("="*60 + "\n")

                    # Scan filesystem and create CTX_Asset nodes for new shots only
                    if self._config:
                        scanner = AssetScanner(self._config, self._layer_manager)
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

        # Column 1: Lock indicator
        try:
            self._update_lock_cell(row, shot_data)
        except Exception as lock_err:
            logger.warning("Lock cell update failed for row %d: %s", row, lock_err)

        # Column 2: Shot path (PROJECT_EPISODE_SEQUENCE_SHOT)
        shot_path = "{}_{}_{}_{}".format(
            shot_data['project'], shot_data['ep'], shot_data['seq'], shot_data['shot']
        )
        self.shot_table.setItem(row, 2, QtWidgets.QTableWidgetItem(shot_path))

        # Column 3: Frame Range
        frame_range_text = "1001-1100"  # Default
        if 'ctx_node' in shot_data and shot_data['ctx_node']:
            try:
                start, end = shot_data['ctx_node'].get_frame_range()
                frame_range_text = "{}-{}".format(start, end)
            except Exception as e:
                logger.warning("Failed to get frame range: %s", e)
        frame_range_item = QtWidgets.QTableWidgetItem(frame_range_text)
        frame_range_item.setTextAlignment(QtCore.Qt.AlignCenter)
        self.shot_table.setItem(row, 3, frame_range_item)

        # Column 4: Set Shot button
        set_btn = QtWidgets.QPushButton("Set")
        set_btn.setToolTip("Set as active shot")
        set_btn.clicked.connect(lambda checked=False, r=row: self._on_set_shot(r))
        self.shot_table.setCellWidget(row, 4, set_btn)

        # Column 5: Version button - check asset status
        version_status = self._check_shot_version_status(shot_data)
        version_btn = QtWidgets.QPushButton(version_status['text'])
        if version_status['status'] == 'latest':
            version_btn.setStyleSheet("background-color: #2E7D32; color: white;")  # Green
        elif version_status['status'] == 'outdated':
            version_btn.setStyleSheet("background-color: #F57C00; color: white;")  # Orange
        else:
            version_btn.setStyleSheet("")  # Default
        version_btn.clicked.connect(lambda checked=False, r=row: self._on_version_click(r))
        self.shot_table.setCellWidget(row, 5, version_btn)

        # Column 6: Gaffer button
        ctx_node = shot_data.get('ctx_node')
        has_gaffer = False
        if ctx_node:
            try:
                has_gaffer = ctx_node.get_gaffer() is not None
            except Exception:
                pass
        gaffer_btn = QtWidgets.QPushButton("GAF" if has_gaffer else "+GAF")
        gaffer_btn.setToolTip("Open Gaffer Manager for this shot")
        if has_gaffer:
            gaffer_btn.setStyleSheet("background-color: #1565C0; color: white;")
        gaffer_btn.clicked.connect(lambda checked=False, r=row: self._on_gaffer_click(r))
        self.shot_table.setCellWidget(row, 6, gaffer_btn)

        # Column 7: Slate button (mirrors Col 6 Gaffer button exactly)
        has_slate = False
        if ctx_node is not None:
            try:
                has_slate = ctx_node.get_slate() is not None
            except Exception:
                pass
        slate_btn = QtWidgets.QPushButton("SLT" if has_slate else "+SLT")
        slate_btn.setToolTip("Open Slate Manager for this shot")
        if has_slate:
            slate_btn.setStyleSheet("background-color: #1565C0; color: white;")
        slate_btn.clicked.connect(lambda checked=False, r=row: self._on_slate_click(r))
        self.shot_table.setCellWidget(row, 7, slate_btn)

        # Column 8: Render status
        ep = shot_data.get('ep', '')
        seq = shot_data.get('seq', '')
        shot = shot_data.get('shot', '')
        self.shot_table.setItem(row, 8, self._make_rnd_badge(ep, seq, shot))

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
            # Set minimum size when no shots
            self.resize(800, 300)
            return

        # Get row height (including header)
        row_height = self.shot_table.rowHeight(0) if row_count > 0 else 30
        header_height = self.shot_table.horizontalHeader().height()

        # Calculate table height needed (limit to 15 rows visible)
        visible_rows = min(row_count, 15)
        table_height = header_height + (row_height * visible_rows) + 4  # +4 for borders

        # Add heights of other widgets
        current_shot_height = self.current_shot_label.sizeHint().height()
        search_header_height = 40  # Search box and label
        button_layout_height = 50  # Bottom buttons
        status_bar_height = self.statusBar().height() if self.statusBar() else 20

        # Calculate total height with margins
        total_height = (current_shot_height + search_header_height +
                       table_height + button_layout_height +
                       status_bar_height + 80)  # +80 for margins and spacing

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

        # Set minimum and maximum bounds
        min_height = 400
        new_height = max(min_height, min(total_height, max_height))

        # Calculate width based on actual column widths
        calculated_width = self._calculate_table_width()

        # Set width bounds (fit to content, but allow some flexibility)
        min_width = calculated_width
        max_width = calculated_width + 100  # Allow slight expansion
        new_width = max(min_width, min(calculated_width, max_width))

        self.resize(new_width, new_height)

    def _on_search_changed(self, text):
        """Handle search box text change - filter table rows.

        Args:
            text: Search text
        """
        search_text = text.lower().strip()

        # If search is empty, show all rows
        if not search_text:
            for row in range(self.shot_table.rowCount()):
                self.shot_table.setRowHidden(row, False)
            return

        # Filter rows based on search text
        for row in range(self.shot_table.rowCount()):
            if row >= len(self._shots):
                continue

            shot_data = self._shots[row]

            # Search in shot path
            shot_path = "{}_{}_{}_{}".format(
                shot_data.get('project', ''),
                shot_data.get('ep', ''),
                shot_data.get('seq', ''),
                shot_data.get('shot', '')
            ).lower()

            # Show row if search text is found
            if search_text in shot_path:
                self.shot_table.setRowHidden(row, False)
            else:
                self.shot_table.setRowHidden(row, True)

    def _show_context_menu(self, position):
        """Show context menu for selected shots.

        Args:
            position: QPoint position where menu was requested
        """
        # Get selected rows
        selected_rows = set()
        for item in self.shot_table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            return

        # Create context menu
        menu = QtWidgets.QMenu(self)

        edit_action = menu.addAction("Edit Frame Range")
        save_action = menu.addAction("Save to Shot Directory")
        menu.addSeparator()
        quick_render_action = menu.addAction("Quick Render (First & Last Frame)")
        refresh_rnd_action = menu.addAction("Refresh Render Status")
        menu.addSeparator()
        remove_action = menu.addAction("Remove")

        # Lock / Unlock actions -- based on first selected row
        first_row = min(selected_rows)
        node_name = None
        if first_row < len(self._shots):
            ctx_node = self._shots[first_row].get('ctx_node')
            if ctx_node is not None:
                node_name = (
                    ctx_node.node_name if hasattr(ctx_node, 'node_name') else str(ctx_node)
                )

        if node_name is not None:
            from core.lock_manager import LockManager
            menu.addSeparator()
            lock_info = LockManager.get_lock_info(node_name)
            if lock_info['is_locked']:
                unlock_shot_action = menu.addAction('Unlock Shot')
                unlock_shot_action.triggered.connect(
                    lambda checked=False, n=node_name: self._on_unlock_shot(n)
                )
            else:
                lock_shot_action = menu.addAction('Lock Shot')
                lock_shot_action.triggered.connect(
                    lambda checked=False, n=node_name: self._on_lock_shot(n)
                )

            seq_node = LockManager._get_parent_sequence(node_name)
            if seq_node:
                seq_info = LockManager.get_lock_info(seq_node)
                if seq_info['is_locked']:
                    unlock_seq_action = menu.addAction('Unlock Sequence')
                    unlock_seq_action.triggered.connect(
                        lambda checked=False, sn=seq_node: self._on_unlock_sequence(sn)
                    )
                else:
                    lock_seq_action = menu.addAction('Lock Sequence')
                    lock_seq_action.triggered.connect(
                        lambda checked=False, sn=seq_node: self._on_lock_sequence(sn)
                    )

        # Execute menu and get selected action
        action = menu.exec_(self.shot_table.viewport().mapToGlobal(position))

        if action == edit_action:
            # Edit selected shot(s) - pass all selected rows
            self._on_edit_shot(sorted(selected_rows))
        elif action == save_action:
            # Save all selected shots
            for row in sorted(selected_rows):
                self._on_save_shot(row)
        elif action == quick_render_action:
            self._on_quick_render(sorted(selected_rows))
        elif action == refresh_rnd_action:
            self._refresh_rnd_column()
        elif action == remove_action:
            # Remove all selected shots
            for row in sorted(selected_rows, reverse=True):
                self._on_remove_shot(row)
        # Lock/Unlock actions are handled via triggered signals above

    def _on_set_shot(self, row):
        """Handle Set Shot button click.

        Args:
            row: Table row index
        """
        shot_data = self._shots[row]

        if 'ctx_node' not in shot_data or not shot_data['ctx_node']:
            logger.warning("No CTX node for shot at row {}".format(row))
            return

        shot_node = shot_data['ctx_node']
        manager_node = self._context_manager.get_or_create_manager()

        if not manager_node:
            logger.error("No CTX_Manager node found")
            return

        # Update previous button state
        if self._active_shot_index is not None:
            prev_btn = self.shot_table.cellWidget(self._active_shot_index, 4)
            if prev_btn:
                prev_btn.setText("Set")
                prev_btn.setStyleSheet("")

        # Use ShotSwitcher to handle layer visibility and CTX node updates
        try:
            success = self._shot_switcher.switch_to_shot(
                shot_node.node_name,
                manager_node.node_name,
                hide_others=True  # Hide other shots' layers
            )

            if success:
                # Update internal state
                if self._active_shot_index is not None:
                    self._shots[self._active_shot_index]['is_active'] = False

                self._active_shot_index = row
                shot_data['is_active'] = True

                # Update button
                set_btn = self.shot_table.cellWidget(row, 4)
                if set_btn:
                    set_btn.setText("ACT")
                    set_btn.setStyleSheet("background-color: #4A90E2; color: white; font-weight: bold;")

                # Update current shot display
                self._update_current_shot_display()

                # Reconcile assets BEFORE path resolution so that newly
                # created CTX_Asset nodes also get their paths resolved.
                try:
                    from core.asset_reconciler import reconcile_assets_for_shot
                    recon = reconcile_assets_for_shot(shot_node)
                    if recon['created'] or recon['linked']:
                        logger.info("Asset reconcile: created=%d, linked=%d, skipped=%d",
                                    recon['created'], recon['linked'], recon['skipped'])
                except Exception as exc:
                    logger.warning("Asset reconciliation failed (non-fatal): %s", exc)

                # Trigger context change callback to resolve paths for ALL
                # assets (including ones just created by reconciliation).
                logger.info("Triggering context change callback for path resolution")
                self._context_manager.set_active_shot(shot_node)

                # Switch display layers: move active shot assets to CTX_Active, others to CTX_Inactive
                if self._layer_manager:
                    logger.info("Switching display layers...")
                    # Get all shot nodes from self._shots (key is 'ctx_node', not 'shot_node')
                    all_shot_nodes = [s['ctx_node'] for s in self._shots if s.get('ctx_node')]
                    all_shot_nodes = [n for n in all_shot_nodes if n is not None]

                    logger.info("Found {} shot nodes for layer switching".format(len(all_shot_nodes)))

                    stats = self._layer_manager.switch_shot_layers(shot_node, all_shot_nodes)
                    logger.info("Display layer switch complete: {} active, {} inactive".format(
                        stats['active_moved'], stats['inactive_moved']))

                # Set Maya timeline and render settings to match shot frame range
                try:
                    import maya.cmds as cmds
                    start, end = shot_node.get_frame_range()

                    # Set playback timeline
                    cmds.playbackOptions(
                        minTime=start,
                        maxTime=end,
                        animationStartTime=start,
                        animationEndTime=end
                    )
                    logger.info("Set timeline to frame range: {}-{}".format(start, end))

                    # Set render frame range
                    cmds.setAttr("defaultRenderGlobals.startFrame", start)
                    cmds.setAttr("defaultRenderGlobals.endFrame", end)
                    logger.info("Set render frame range: {}-{}".format(start, end))

                except Exception as e:
                    logger.warning("Failed to set timeline/render range: %s", e)

                # Set render output path
                if self._config and self._config.is_render_settings_enabled():
                    try:
                        import maya.cmds as cmds
                        from core.resolver import PathResolver
                        from config.platform_config import PlatformConfig

                        output_config = self._config.get_render_output_config()
                        if output_config and output_config.get('template'):
                            platform_config = PlatformConfig(self._config)
                            resolver = PathResolver(self._config, platform_config)

                            # Get dept and version from scene file
                            dept = self._get_current_dept()
                            version = self._get_current_version()

                            context = {
                                'ep': shot_data['ep'],
                                'seq': shot_data['seq'],
                                'shot': shot_data['shot'],
                                'dept': dept,
                                'ver': version
                            }

                            template_name = output_config.get('template', 'imgPath')
                            img_path = resolver.resolve_path(template_name, context)

                            # Set Maya render output path
                            cmds.setAttr("defaultRenderGlobals.imageFilePrefix", img_path, type="string")
                            logger.info("Set render output path: {}".format(img_path))
                            logger.info("  (dept={}, version={})".format(dept, version))

                    except Exception as e:
                        logger.warning("Failed to set render output path: {}".format(e))
                        import traceback
                        traceback.print_exc()

                # Update camera namespace to match active shot
                try:
                    import maya.cmds as cmds

                    # Use the existing node_manager instance
                    node_manager = self._node_manager if hasattr(self, '_node_manager') else NodeManager()

                    # Get camera assets for this shot
                    camera_assets = node_manager.get_assets_by_type(shot_node, 'CAM')

                    if camera_assets:
                        camera_asset = camera_assets[0]  # Use first camera

                        # Get the target namespace from CTX_Asset node
                        target_ns = camera_asset.get_namespace()

                        # Find current camera namespace in Maya
                        # Get all namespaces that contain '_camera'
                        all_namespaces = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []
                        current_camera_ns = None

                        for ns in all_namespaces:
                            if '_camera' in ns.lower() and ns != target_ns:
                                current_camera_ns = ns
                                break

                        if current_camera_ns:
                            # Rename namespace
                            if not cmds.namespace(exists=target_ns):
                                cmds.namespace(rename=(current_camera_ns, target_ns))
                                logger.info("Renamed camera namespace: {} -> {}".format(current_camera_ns, target_ns))
                            else:
                                logger.warning("Target namespace already exists: {}".format(target_ns))
                        else:
                            logger.debug("Camera namespace already correct or not found")

                except Exception as e:
                    logger.warning("Failed to update camera namespace: {}".format(e))
                    import traceback
                    traceback.print_exc()

                # Guard: if Gaffer Manager has active edit mode, force commit or discard
                # before applying the new shot's gaffer (otherwise edits are silently lost).
                try:
                    from ui.gaffer_manager_dialog import GafferManagerDialog
                    _gm_dlg = GafferManagerDialog._instance
                    if _gm_dlg is not None and getattr(_gm_dlg, '_edit_mode', None) is not None:
                        reply = QtWidgets.QMessageBox.question(
                            self, 'Gaffer Edit Mode Active',
                            'You have unsaved gaffer edits.\n\n'
                            'Commit changes before switching shot?',
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                        )
                        if reply == QtWidgets.QMessageBox.Yes:
                            _gm_dlg._on_commit_edit_mode()
                        else:
                            _gm_dlg._on_discard_edit_mode()
                except Exception:
                    pass

                # Apply gaffer overrides to Maya lights when switching shot.
                # apply_gaffer_to_all_lights always restores originals first,
                # then applies the full chain root-first (master -> seq -> shot).
                # If no gaffer exists, restore originals directly.
                try:
                    from core.nodes.wrappers.gaffer import CTXLightGafferNode
                    from core.nodes.wrappers.sequence import CTXSequenceNode
                    from core.gaffer.light_ops import LightOperations

                    apply_gaffer = None

                    # Try shot gaffer first, then sequence gaffer
                    shot_gaffer_name = shot_node.get_gaffer()
                    if shot_gaffer_name:
                        apply_gaffer = CTXLightGafferNode(shot_gaffer_name)
                        logger.info("Shot switch: using shot gaffer: {}".format(shot_gaffer_name))
                    else:
                        seq_name = shot_node.get_parent_sequence()
                        if seq_name:
                            seq = CTXSequenceNode(seq_name)
                            seq_gaffer_name = seq.get_gaffer()
                            if seq_gaffer_name:
                                apply_gaffer = CTXLightGafferNode(seq_gaffer_name)
                                logger.info("Shot switch: using sequence gaffer: {}".format(seq_gaffer_name))

                    if apply_gaffer:
                        # Restores originals + applies full chain in one call
                        LightOperations.apply_gaffer_to_all_lights(apply_gaffer)
                        logger.info("Shot switch: applied gaffer chain from {}".format(
                            apply_gaffer.node_name))
                    else:
                        # No gaffer -- restore persisted originals
                        restored = LightOperations.restore_originals()
                        logger.info("Shot switch: no gaffer -- restored {} original light values".format(
                            restored))

                except Exception as e:
                    logger.warning("Failed to apply gaffer on shot switch: {}".format(e))
                    import traceback
                    traceback.print_exc()

                # Apply slate (render layer renderable state) -- non-fatal
                try:
                    from core.slate.resolver import SlateResolver as _SR
                    if shot_node is not None:
                        slate_for_shot = _SR._get_slate_for_node(shot_node)
                        if slate_for_shot is not None:
                            _SR.apply_to_scene(shot_node)
                        else:
                            if hasattr(_SR, 'restore_originals'):
                                _SR.restore_originals()
                    else:
                        if hasattr(_SR, 'restore_originals'):
                            _SR.restore_originals()
                except Exception as exc:
                    logger.warning('Slate apply failed (non-fatal): %s', exc)

                shot_path = "{}_{}_{}_{}".format(
                    shot_data['project'], shot_data['ep'], shot_data['seq'], shot_data['shot']
                )
                logger.info("Active shot set to: %s (display layer visibility updated)", shot_path)
                self.statusBar().showMessage("Active shot: {}".format(shot_path))

                # Refresh Gaffer Manager if open; auto-select the active gaffer
                try:
                    from ui.gaffer_manager_dialog import GafferManagerDialog
                    dlg = GafferManagerDialog._instance
                    if dlg is not None:
                        if apply_gaffer is not None:
                            dlg.select_gaffer(apply_gaffer)
                        else:
                            dlg.refresh()
                except Exception:
                    pass

                # Refresh Slate Manager if open; auto-select the active slate.
                # Falls back to sequence slate when shot has no slate (mirrors gaffer).
                try:
                    from ui.slate_manager_dialog import SlateManagerDialog
                    slate_dlg = SlateManagerDialog._instance
                    if slate_dlg is not None:
                        active_slate = None
                        try:
                            active_slate = shot_node.get_slate()
                            if active_slate is None:
                                # No shot slate -- try sequence slate
                                from core.nodes.wrappers.sequence import CTXSequenceNode
                                seq_name = shot_node.get_parent_sequence()
                                if seq_name:
                                    seq = CTXSequenceNode(seq_name)
                                    active_slate = seq.get_slate()
                        except Exception:
                            pass
                        if active_slate is not None:
                            slate_dlg.select_slate(active_slate)
                        else:
                            slate_dlg.refresh()
                except Exception:
                    pass
            else:
                logger.error("Failed to switch to shot")
                QtWidgets.QMessageBox.warning(
                    self,
                    "Error",
                    "Failed to switch to shot"
                )
        except Exception as e:
            logger.error("Failed to switch shot: %s", e)
            QtWidgets.QMessageBox.warning(
                self,
                "Error",
                "Failed to switch shot: {}".format(e)
            )

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
        set_btn = self.shot_table.cellWidget(row, 4)  # Column 4 is Set Shot button
        if set_btn:
            if shot_data.get('is_active', False):
                set_btn.setText("ACT")
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
        dialog = AssetManagerDialog(shot_data, self._config, self, self._layer_manager)

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
        version_btn = self.shot_table.cellWidget(row, 5)  # Column 5 is Version button
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

    def _on_edit_shot(self, rows):
        """Handle Edit button click - open Shot Context Manager dialog.

        Args:
            rows: Table row index (int) or list of row indices (list)
        """
        # Convert single row to list
        if isinstance(rows, int):
            rows = [rows]

        if not rows:
            return

        # If single shot, use existing dialog
        if len(rows) == 1:
            from ui.shot_context_dialog import ShotContextDialog

            row = rows[0]
            shot_data = self._shots[row]
            if 'ctx_node' not in shot_data or not shot_data['ctx_node']:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Error",
                    "No CTX node found for this shot"
                )
                return

            # Open dialog
            dialog = ShotContextDialog(shot_data['ctx_node'], parent=self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                # Update frame range display in table
                try:
                    start, end = shot_data['ctx_node'].get_frame_range()
                    frame_range_text = "{}-{}".format(start, end)
                    frame_range_item = self.shot_table.item(row, 3)
                    if frame_range_item:
                        frame_range_item.setText(frame_range_text)
                    logger.info("Updated frame range display for row {}: {}".format(row, frame_range_text))
                except Exception as e:
                    logger.error("Failed to update frame range display: %s", e)

        # If multiple shots, use table-based dialog
        else:
            self._on_edit_multiple_shots(rows)

    def _on_edit_multiple_shots(self, rows):
        """Handle editing multiple shots at once with table-based dialog.

        Args:
            rows: List of table row indices
        """
        # Create dialog
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Edit Frame Ranges - {} Shots".format(len(rows)))
        dialog.setMinimumSize(600, 400)

        layout = QtWidgets.QVBoxLayout(dialog)

        # Info label
        info_label = QtWidgets.QLabel("Edit frame ranges for selected shots:")
        info_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(info_label)

        # Create table
        table = QtWidgets.QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Shot", "Start Frame", "End Frame", "FPS"])
        table.setRowCount(len(rows))

        # Set column widths
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)
        table.setColumnWidth(1, 100)
        table.setColumnWidth(2, 100)
        table.setColumnWidth(3, 80)

        # Populate table
        shot_nodes = []
        for i, row in enumerate(rows):
            shot_data = self._shots[row]
            shot_node = shot_data.get('ctx_node')

            if not shot_node:
                continue

            shot_nodes.append((row, shot_node))

            # Shot name (read-only)
            shot_name = "{}_{}_{}".format(
                shot_data.get('ep', ''),
                shot_data.get('seq', ''),
                shot_data.get('shot', '')
            )
            shot_item = QtWidgets.QTableWidgetItem(shot_name)
            shot_item.setFlags(shot_item.flags() & ~QtCore.Qt.ItemIsEditable)
            table.setItem(i, 0, shot_item)

            # Start frame (editable)
            start, end = shot_node.get_frame_range()
            start_item = QtWidgets.QTableWidgetItem(str(start))
            table.setItem(i, 1, start_item)

            # End frame (editable)
            end_item = QtWidgets.QTableWidgetItem(str(end))
            table.setItem(i, 2, end_item)

            # FPS (editable)
            fps = shot_node.get_fps()
            fps_item = QtWidgets.QTableWidgetItem(str(fps))
            table.setItem(i, 3, fps_item)

        layout.addWidget(table)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)

        apply_btn = QtWidgets.QPushButton("Apply")
        apply_btn.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold;")
        apply_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(apply_btn)

        layout.addLayout(button_layout)

        # Execute dialog
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            # Apply changes to all shots
            for i, (row, shot_node) in enumerate(shot_nodes):
                try:
                    # Get values from table
                    start_text = table.item(i, 1).text()
                    end_text = table.item(i, 2).text()
                    fps_text = table.item(i, 3).text()

                    start = int(start_text)
                    end = int(end_text)
                    fps = float(fps_text)

                    # Update shot node
                    shot_node.set_frame_range(start, end)
                    shot_node.set_fps(fps)

                    # Update table display
                    frame_range_text = "{}-{}".format(start, end)
                    frame_range_item = self.shot_table.item(row, 3)
                    if frame_range_item:
                        frame_range_item.setText(frame_range_text)

                    logger.info("Updated shot at row {}: {}-{} @ {}fps".format(row, start, end, fps))

                except Exception as e:
                    logger.error("Failed to update shot at row {}: {}".format(row, e))
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Update Error",
                        "Failed to update shot at row {}:\n\n{}".format(row, str(e))
                    )

            self.statusBar().showMessage("Updated {} shot(s)".format(len(shot_nodes)))

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
            # NOTE: We no longer delete per-shot display layers because we use
            # global CTX_Active and CTX_Inactive layers. When the shot is deleted,
            # its assets will be automatically removed from the layers.

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

                # Refresh display layers to remove deleted shot's assets
                if self._active_shot_index is not None and self._shots:
                    active_shot_data = self._shots[self._active_shot_index]
                    if 'ctx_node' in active_shot_data and active_shot_data['ctx_node']:
                        all_shot_nodes = [s['ctx_node'] for s in self._shots if s.get('ctx_node')]
                        self._layer_manager.switch_shot_layers(
                            active_shot_data['ctx_node'],
                            all_shot_nodes
                        )
                        logger.info("Refreshed display layers after shot deletion")

            # Update row numbers
            for i in range(self.shot_table.rowCount()):
                self.shot_table.item(i, 0).setText(str(i + 1))

            logger.info("Removed shot: %s", shot_path)
            self.statusBar().showMessage("Removed shot: {}".format(shot_path))

    def _on_save_shot(self, row):
        """Handle Save button click - Save current scene, copy to target shot, rename with pattern.

        Args:
            row: Table row index
        """
        import maya.cmds as cmds
        import shutil
        from core.resolver import PathResolver
        from config.platform_config import PlatformConfig

        shot_data = self._shots[row]
        shot_id = "{}_{}_{}_{}".format(
            shot_data['project'], shot_data['ep'], shot_data['seq'], shot_data['shot']
        )

        logger.info("=" * 80)
        logger.info("SAVE SHOT: {}".format(shot_id))

        try:
            # Step 1: Save current scene
            current_scene = cmds.file(query=True, sceneName=True)
            if not current_scene:
                QtWidgets.QMessageBox.warning(
                    self,
                    "No Scene",
                    "Please save the scene first before using Save to Shot."
                )
                return

            logger.info("Current scene: {}".format(current_scene))
            cmds.file(save=True, force=True)
            logger.info("Saved current scene")

            # Step 2: Get scene file pattern from config
            if not self._config:
                raise Exception("No config loaded")

            render_settings = self._config.get_render_settings_config()
            if not render_settings:
                raise Exception("renderSettings not found in config")

            scene_pattern = render_settings.get('outputPath', {}).get('sceneFilePattern')
            if not scene_pattern:
                raise Exception("sceneFilePattern not found in config")

            logger.info("Scene pattern: {}".format(scene_pattern))

            # Step 3: Parse current scene to get dept and version
            parsed = self._parse_scene_filename()
            if parsed:
                dept = parsed.get('dept', 'lighting')
                version = parsed.get('version', 'v001')
            else:
                dept = "lighting"  # Fallback
                version = "v001"  # Fallback

            logger.info("Parsed - dept: {}, version: {}".format(dept, version))

            # Step 4: Build target filename using pattern with variant='CTX'
            target_filename = scene_pattern.format(
                ep=shot_data['ep'],
                seq=shot_data['seq'],
                shot=shot_data['shot'],
                dept=dept,
                variant='CTX',
                ver=version
            )

            logger.info("Target filename: {}".format(target_filename))

            # Step 5: Resolve target directory using shotWork template
            platform_config = PlatformConfig(self._config)
            resolver = PathResolver(self._config, platform_config)

            # Build context with dept for shotWork template
            context = {
                'project': shot_data['project'],
                'ep': shot_data['ep'],
                'seq': shot_data['seq'],
                'shot': shot_data['shot'],
                'dept': dept  # Required for shotWork template
            }

            # Use shotWork template: $projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/version
            shot_work_dir = resolver.resolve_path('shotWork', context)
            logger.info("Shot work directory: {}".format(shot_work_dir))

            # Step 6: Create target directory if it doesn't exist
            if not os.path.exists(shot_work_dir):
                os.makedirs(shot_work_dir)
                logger.info("Created directory: {}".format(shot_work_dir))

            # Step 7: Copy file to target directory with new name
            target_path = os.path.join(shot_work_dir, target_filename)
            shutil.copy2(current_scene, target_path)
            logger.info("Copied to: {}".format(target_path))

            # Success message
            QtWidgets.QMessageBox.information(
                self,
                "Save Complete",
                "Scene saved to shot directory:\n\n{}".format(target_path)
            )

            self.statusBar().showMessage("Saved to: {}".format(target_path))

        except Exception as e:
            logger.error("Failed to save shot: {}".format(e))
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(
                self,
                "Save Error",
                "Failed to save scene to shot directory:\n\n{}".format(str(e))
            )

    def _make_rnd_badge(self, ep, seq, shot):
        """Create the render status badge item for the Rnd column.

        Checks render_state registry first (session state), then filesystem.

        Args:
            ep (str): Episode code.
            seq (str): Sequence code.
            shot (str): Shot code.

        Returns:
            QTableWidgetItem: Colored dot item with tooltip.
        """
        from core.batch import render_state as rs

        shot_id = '%s_%s_%s' % (ep, seq, shot)
        session_status = rs.get_status(shot_id)

        color = None
        tooltip = None

        if session_status in (rs.QUEUED, rs.RENDERING):
            color = QtGui.QColor('#F57C00')   # orange
            tooltip = 'Queued for render' if session_status == rs.QUEUED else 'Rendering'
        elif session_status == rs.FAILED:
            color = QtGui.QColor('#D32F2F')   # red
            tooltip = 'Last render failed'
        elif session_status == rs.DONE:
            # Fall through to filesystem check
            session_status = None

        if session_status is None:
            # Filesystem check
            try:
                from core.batch.output_checker import check_shot_output, HAS_OUTPUT
                result = check_shot_output(
                    self._config,
                    self._platform_config if hasattr(self, '_platform_config') else None,
                    ep, seq, shot
                )
                if result == HAS_OUTPUT:
                    color = QtGui.QColor('#2E7D32')   # green
                    tooltip = 'Has output'
                else:
                    color = QtGui.QColor('#757575')   # gray
                    tooltip = 'No output'
            except Exception:
                color = QtGui.QColor('#757575')
                tooltip = 'No output'

        item = QtWidgets.QTableWidgetItem('\u25cf')  # filled circle
        item.setForeground(color)
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        item.setToolTip(tooltip)
        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
        return item

    def _refresh_rnd_column(self):
        """Refresh the Rnd column for all rows. Called after render state changes."""
        for row, shot_data in enumerate(self._shots):
            ep = shot_data.get('ep', '')
            seq = shot_data.get('seq', '')
            shot = shot_data.get('shot', '')
            self.shot_table.setItem(row, 8, self._make_rnd_badge(ep, seq, shot))

    def _update_lock_cell(self, row, shot_data):
        """Set the lock indicator cell for a shot row.

        Shows a lock icon label. Color indicates lock state:
          - no lock:                   blank (no widget)
          - locked directly:           amber text label  "L"
          - locked via seq (cascade):  amber, slightly dimmer, tooltip shows source

        Args:
            row (int): Table row index.
            shot_data (dict): Shot data dict from self._shots.
        """
        from core.lock_manager import LockManager

        ctx_node = shot_data.get('ctx_node')
        if ctx_node is None:
            self.shot_table.setCellWidget(row, 1, None)
            return

        node_name = ctx_node.node_name if hasattr(ctx_node, 'node_name') else str(ctx_node)
        direct_locked = LockManager.is_locked(node_name)
        info = LockManager.get_lock_info(node_name) if direct_locked else {}

        # Check sequence cascade
        seq_locked = False
        seq_info = {}
        if not direct_locked:
            seq_node = LockManager._get_parent_sequence(node_name)
            if seq_node and LockManager.is_locked(seq_node):
                seq_locked = True
                seq_info = LockManager.get_lock_info(seq_node)

        if not direct_locked and not seq_locked:
            self.shot_table.setCellWidget(row, 1, None)
            item = QtWidgets.QTableWidgetItem('')
            item.setFlags(QtCore.Qt.NoItemFlags)
            self.shot_table.setItem(row, 1, item)
            return

        label = QtWidgets.QLabel('L')
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setFixedWidth(20)

        if direct_locked:
            label.setStyleSheet('color: #FFA000; font-weight: bold; font-size: 10px;')
            by = info.get('locked_by', '')
            at = info.get('locked_at', '')
            label.setToolTip('Locked by {} at {}'.format(by, at) if by else 'Locked')
        else:
            # Cascade from sequence -- slightly dimmer
            label.setStyleSheet('color: #CC8800; font-size: 10px;')
            by = seq_info.get('locked_by', '')
            at = seq_info.get('locked_at', '')
            label.setToolTip(
                'Locked via sequence (by {} at {})'.format(by, at) if by
                else 'Locked via sequence'
            )

        self.shot_table.setCellWidget(row, 1, label)

    def _refresh_lock_column(self):
        """Refresh the Lck column for all rows."""
        for row, shot_data in enumerate(self._shots):
            self._update_lock_cell(row, shot_data)

    def _on_lock_shot(self, node_name):
        """Lock a single shot node."""
        from core.lock_manager import LockManager
        try:
            LockManager.lock_node(node_name)
            self._refresh_lock_column()
            self.statusBar().showMessage('Shot locked: {}'.format(node_name))
        except Exception as exc:
            logger.error('Failed to lock shot %s: %s', node_name, exc)

    def _on_unlock_shot(self, node_name):
        """Unlock a single shot node."""
        from core.lock_manager import LockManager
        try:
            LockManager.unlock_node(node_name)
            self._refresh_lock_column()
            self.statusBar().showMessage('Shot unlocked: {}'.format(node_name))
        except Exception as exc:
            logger.error('Failed to unlock shot %s: %s', node_name, exc)

    def _on_lock_sequence(self, seq_node):
        """Lock a sequence and all shots under it (cascade)."""
        from core.lock_manager import LockManager
        try:
            LockManager.lock_sequence(seq_node, cascade=True)
            self._refresh_lock_column()
            self.statusBar().showMessage('Sequence locked: {}'.format(seq_node))
        except Exception as exc:
            logger.error('Failed to lock sequence %s: %s', seq_node, exc)

    def _on_unlock_sequence(self, seq_node):
        """Unlock a sequence and all shots under it (cascade)."""
        from core.lock_manager import LockManager
        try:
            LockManager.unlock_sequence(seq_node, cascade=True)
            self._refresh_lock_column()
            self.statusBar().showMessage('Sequence unlocked: {}'.format(seq_node))
        except Exception as exc:
            logger.error('Failed to unlock sequence %s: %s', seq_node, exc)

    def _register_scene_callbacks(self):
        """Register Maya scene open/new callbacks to refresh the shot table."""
        try:
            import maya.OpenMaya as om
            self._scene_open_cb = om.MSceneMessage.addCallback(
                om.MSceneMessage.kAfterOpen, self._on_scene_changed)
            self._scene_new_cb = om.MSceneMessage.addCallback(
                om.MSceneMessage.kAfterNew, self._on_scene_changed)
            logger.info("Scene change callbacks registered")
        except Exception as exc:
            logger.warning("Could not register scene callbacks: %s", exc)

    def _deregister_scene_callbacks(self):
        """Remove Maya scene callbacks."""
        try:
            import maya.OpenMaya as om
            for attr in ('_scene_open_cb', '_scene_new_cb'):
                cb = getattr(self, attr, None)
                if cb is not None:
                    om.MMessage.removeCallback(cb)
                    setattr(self, attr, None)
        except Exception as exc:
            logger.warning("Could not deregister scene callbacks: %s", exc)

    def _on_scene_changed(self, *args):
        """Called by Maya after scene open or new. Clears and repopulates shot table."""
        from core.batch import render_state as rs
        rs.clear()
        # Use QTimer.singleShot to defer back to the Qt main thread
        QtCore.QTimer.singleShot(100, self._reload_shots_from_scene)

    def _reload_shots_from_scene(self):
        """Clear shot table and repopulate from the newly opened scene."""
        self.shot_table.setRowCount(0)
        self._shots = []
        self._active_shot_index = None
        self.current_shot_label.setText("Current Shot: None")
        # Re-use the existing load method
        self._load_existing_shots()
        logger.info("Shot table refreshed after scene change")

    def _on_render_state_changed(self, shot_id, status):
        """Called when render state changes. Refreshes Rnd column via Qt main thread."""
        QtCore.QTimer.singleShot(0, self._refresh_rnd_column)

    def _on_quick_render(self, rows):
        """Queue first and last frame render for selected shots.

        Creates two single-frame RenderJob per shot (start frame + end frame).
        Layers are resolved by ScenePreparer (slate -> renderable -> defaultRenderLayer).
        Opens BatchRenderDialog.

        Args:
            rows (list[int]): Selected row indices.
        """
        from core.batch import render_state as rs

        jobs_config = []  # list of dicts to pass to dialog

        for row in rows:
            if row >= len(self._shots):
                continue
            shot_data = self._shots[row]
            ctx_node = shot_data.get('ctx_node')
            ep = shot_data.get('ep', '')
            seq = shot_data.get('seq', '')
            shot = shot_data.get('shot', '')

            start, end = 1001, 1100  # fallback
            if ctx_node:
                try:
                    start, end = ctx_node.get_frame_range()
                except Exception:
                    pass

            shot_id = '%s_%s_%s' % (ep, seq, shot)
            rs.set_status(shot_id, rs.QUEUED)

            # Two single-frame jobs: first frame and last frame
            # No explicit render_layers -- ScenePreparer resolves via slate then
            # renderable layers (clapper icon), falling back to defaultRenderLayer
            jobs_config.append({
                'ep': ep, 'seq': seq, 'shot': shot,
                'start_frame': start, 'end_frame': start,
                'label': '%s_%s_%s frame %d' % (ep, seq, shot, start),
            })
            jobs_config.append({
                'ep': ep, 'seq': seq, 'shot': shot,
                'start_frame': end, 'end_frame': end,
                'label': '%s_%s_%s frame %d' % (ep, seq, shot, end),
            })

        if not jobs_config:
            return

        self._refresh_rnd_column()

        # Open / focus BatchRenderDialog on Monitor tab, start these jobs
        try:
            from ui.batch_render_dialog import BatchRenderDialog
            dlg = BatchRenderDialog.get_or_create(parent=self)
            dlg.show()
            dlg.raise_()
            dlg.queue_quick_render_jobs(jobs_config)
        except Exception as exc:
            logger.error("Failed to open Batch Render dialog: %s", exc)
            from PySide2 import QtWidgets as _qw
            _qw.QMessageBox.critical(self, 'Quick Render', 'Failed to open Batch Render dialog:\n%s' % exc)

    def _on_update_versions(self):
        """Handle Update All Versions button click."""
        logger.info("Update All Versions clicked")
        QtWidgets.QMessageBox.information(
            self,
            "Update Versions",
            "Update All Versions will be implemented in Phase 4C."
        )
        self._refresh_rnd_column()

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

    def _on_delete_all(self):
        """Handle Delete All button click - Remove all shots from scene."""
        if not self._shots:
            QtWidgets.QMessageBox.information(
                self,
                "No Shots",
                "There are no shots to delete."
            )
            return

        # Confirm deletion
        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete All Shots",
            "Are you sure you want to delete ALL {} shot(s) from the scene?\n\nThis will remove all CTX_Shot nodes and their assets.".format(len(self._shots)),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        logger.info("Deleting all {} shots".format(len(self._shots)))

        # Delete all shots in reverse order
        for row in range(len(self._shots) - 1, -1, -1):
            try:
                shot_data = self._shots[row]

                # Delete CTX_Shot node
                if 'ctx_node' in shot_data and shot_data['ctx_node']:
                    shot_node = shot_data['ctx_node']
                    shot_node.delete()
                    logger.info("Deleted CTX_Shot node: {}".format(shot_node.get_node_name()))

                # Remove from list
                self._shots.pop(row)

                # Remove from table
                self.shot_table.removeRow(row)

            except Exception as e:
                logger.error("Failed to delete shot at row {}: {}".format(row, e))

        # Clear active shot
        self._active_shot_index = None
        self.current_shot_label.setText("Current Shot: None")

        # Clear display layers
        try:
            self._layer_manager.cleanup_all_layers()
        except Exception as e:
            logger.warning("Failed to cleanup display layers: {}".format(e))

        logger.info("All shots deleted")
        self.statusBar().showMessage("All shots deleted")

        QtWidgets.QMessageBox.information(
            self,
            "Delete Complete",
            "All shots have been deleted from the scene."
        )
