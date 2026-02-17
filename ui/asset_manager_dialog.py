# -*- coding: utf-8 -*-
"""Asset Manager Dialog - Manage assets and versions for a specific shot.

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

logger = logging.getLogger(__name__)


class AssetManagerDialog(QtWidgets.QDialog):
    """Dialog for managing assets and versions for a shot."""

    def __init__(self, shot_data, config, parent=None, layer_manager=None):
        """Initialize asset manager dialog.

        Args:
            shot_data: Dict with keys: project, ep, seq, shot, version
            config: ProjectConfig instance
            parent: Parent widget (optional)
            layer_manager (DisplayLayerManager, optional): Display layer manager for assigning assets to layers
        """
        super(AssetManagerDialog, self).__init__(parent)

        # Make dialog non-modal and allow interaction with Maya
        self.setWindowModality(QtCore.Qt.NonModal)

        # Remove "always on top" flag
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowMinimizeButtonHint |
            QtCore.Qt.WindowMaximizeButtonHint
        )

        self._shot_data = shot_data
        self._config = config
        self._layer_manager = layer_manager
        self._assets = []  # List of asset dicts

        self._setup_ui()
        self._connect_signals()
        self._load_assets()
    
    def _setup_ui(self):
        """Set up the user interface."""
        shot_path = "{}_{}_{}_{}".format(
            self._shot_data['project'],
            self._shot_data['ep'],
            self._shot_data['seq'],
            self._shot_data['shot']
        )
        
        self.setWindowTitle("Asset Manager - {} ({})".format(shot_path, self._shot_data.get('version', 'v001')))
        # DO NOT set modal - we want non-blocking dialog
        # self.setModal(True)  # REMOVED - this was blocking Maya
        self.setMinimumSize(1000, 600)
        self.resize(1200, 700)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Assets section label and search box
        header_layout = QtWidgets.QHBoxLayout()

        assets_label = QtWidgets.QLabel("ASSETS IN SHOT")
        assets_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        header_layout.addWidget(assets_label)

        header_layout.addStretch()

        # Search box
        search_label = QtWidgets.QLabel("Search:")
        header_layout.addWidget(search_label)

        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Filter assets by name, type, dept...")
        self.search_box.setMinimumWidth(250)
        self.search_box.setClearButtonEnabled(True)
        header_layout.addWidget(self.search_box)

        main_layout.addLayout(header_layout)
        
        # Asset table
        self.asset_table = QtWidgets.QTableWidget()
        self.asset_table.setColumnCount(8)
        self.asset_table.setHorizontalHeaderLabels([
            "Type", "Name", "Var", "Dept", "Current", "Latest", "Status", "Action"
        ])

        # Set column widths for better readability
        header = self.asset_table.horizontalHeader()
        header.setStretchLastSection(False)

        # Column 0: Type - Fixed width (60px)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self.asset_table.setColumnWidth(0, 60)

        # Column 1: Name - Stretch to fill available space
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

        # Column 2: Var - Fixed width (50px)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        self.asset_table.setColumnWidth(2, 50)

        # Column 3: Dept - Fixed width (70px)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)
        self.asset_table.setColumnWidth(3, 70)

        # Column 4: Current - Fixed width (120px) for dropdown
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.Fixed)
        self.asset_table.setColumnWidth(4, 120)

        # Column 5: Latest - Fixed width (80px)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.Fixed)
        self.asset_table.setColumnWidth(5, 80)

        # Column 6: Status - Fixed width (100px)
        header.setSectionResizeMode(6, QtWidgets.QHeaderView.Fixed)
        self.asset_table.setColumnWidth(6, 100)

        # Column 7: Action - Fixed width (80px)
        header.setSectionResizeMode(7, QtWidgets.QHeaderView.Fixed)
        self.asset_table.setColumnWidth(7, 80)

        # Enable multi-selection
        self.asset_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.asset_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.asset_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.asset_table.setAlternatingRowColors(True)
        main_layout.addWidget(self.asset_table)
        
        # Action buttons
        action_layout = QtWidgets.QHBoxLayout()
        
        self.import_asset_btn = QtWidgets.QPushButton("Import Asset")
        self.import_asset_btn.setMinimumHeight(30)
        action_layout.addWidget(self.import_asset_btn)
        
        self.update_all_btn = QtWidgets.QPushButton("Update All to Latest")
        self.update_all_btn.setMinimumHeight(30)
        action_layout.addWidget(self.update_all_btn)
        
        self.validate_all_btn = QtWidgets.QPushButton("Validate All")
        self.validate_all_btn.setMinimumHeight(30)
        action_layout.addWidget(self.validate_all_btn)
        
        action_layout.addStretch()
        main_layout.addLayout(action_layout)
        
        # Dialog buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        
        self.apply_btn = QtWidgets.QPushButton("Apply")
        self.apply_btn.setDefault(True)
        self.apply_btn.setMinimumWidth(100)
        button_layout.addWidget(self.apply_btn)
        
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setMinimumWidth(100)
        button_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """Connect UI signals to slots."""
        self.search_box.textChanged.connect(self._on_search_changed)
        self.import_asset_btn.clicked.connect(self._on_import_asset)
        self.update_all_btn.clicked.connect(self._on_update_all)
        self.validate_all_btn.clicked.connect(self._on_validate_all)
        self.apply_btn.clicked.connect(self._on_apply)
        self.cancel_btn.clicked.connect(self.reject)
    
    def _load_assets(self):
        """Load assets for the shot from filesystem."""
        self._assets = []

        if not self._config:
            logger.warning("No config loaded, cannot discover assets")
            self._populate_asset_table()
            return

        # Detect CTX-ready assets in scene
        from core.ctx_converter import CTXConverter
        converter = CTXConverter()
        self._scene_assets = converter.detect_scene_assets()
        self._converter = converter

        try:
            # Get base publish path for this shot
            # Path: projRoot/project/sceneBase/ep/seq/shot/dept/publish
            proj_root = self._config.get_root('projRoot')
            project_code = self._config.get_project_code()
            scene_base = self._config.get_static_path('sceneBase')

            if not all([proj_root, project_code, scene_base]):
                logger.warning("Missing config values for asset discovery")
                self._populate_asset_table()
                return

            # Build shot base path
            shot_base = os.path.join(
                proj_root,
                project_code,
                scene_base,
                self._shot_data['ep'],
                self._shot_data['seq'],
                self._shot_data['shot']
            )

            logger.info("Scanning for assets in: %s", shot_base)

            if not os.path.exists(shot_base):
                logger.warning("Shot path does not exist: %s", shot_base)
                self._populate_asset_table()
                return

            # Scan departments
            departments = ['anim', 'layout', 'fx', 'lighting']
            for dept in departments:
                dept_path = os.path.join(shot_base, dept, 'publish')
                if not os.path.exists(dept_path):
                    continue

                logger.info("Scanning department: %s", dept)
                self._scan_department_assets(dept_path, dept)

            logger.info("Found %d assets", len(self._assets))

            # Match assets with scene assets to determine CTX ready status
            self._match_ctx_ready_status()

        except Exception as e:
            logger.error("Failed to load assets: %s", e)

        self._populate_asset_table()

    def _scan_department_assets(self, dept_path, dept):
        """Scan department publish directory for assets.

        Args:
            dept_path: Path to department publish directory
            dept: Department name (anim, layout, etc.)
        """
        import re
        from core.asset_scanner import AssetScanner

        # Create scanner instance to use its parser
        scanner = AssetScanner(self._config)

        # Track all versions for each asset
        asset_versions = {}  # Key: (type, name, var, dept), Value: list of (version, file_path, filename)

        # Scan for version directories (v001, v002, etc.)
        for version_dir in sorted(os.listdir(dept_path)):
            version_path = os.path.join(dept_path, version_dir)
            if not os.path.isdir(version_path):
                continue
            if not re.match(r'v\d{3}', version_dir):
                continue

            # Scan for asset files in version directory
            for filename in os.listdir(version_path):
                file_path = os.path.join(version_path, filename)
                if not os.path.isfile(file_path):
                    continue

                # Use asset_scanner's parser (handles both standard assets and cameras)
                parsed = scanner._parse_filename(filename)
                if not parsed:
                    continue

                asset_type = parsed['type']
                asset_name = parsed['name']
                variant = parsed['variant']

                # Create asset key
                asset_key = (asset_type, asset_name, variant, dept)

                # Track this version
                if asset_key not in asset_versions:
                    asset_versions[asset_key] = []
                asset_versions[asset_key].append((version_dir, file_path, filename))

        # Now process all assets and set current to latest version
        for asset_key, versions in asset_versions.items():
            asset_type, asset_name, variant, dept = asset_key

            # Sort versions to get latest
            versions.sort(key=lambda x: x[0], reverse=True)  # Sort descending
            latest_version, latest_file_path, latest_filename = versions[0]

            # Add asset with latest version as current
            self._assets.append({
                'type': asset_type,
                'name': asset_name,
                'var': variant,
                'dept': dept,
                'current': latest_version,  # Set to latest version
                'latest': latest_version,
                'status': 'valid',
                'file_path': latest_file_path,
                'filename': latest_filename,
                'ctx_ready': False,
                'ctx_node': None,
                'maya_node': None
            })

    def _match_ctx_ready_status(self):
        """Match filesystem assets with scene assets using namespace matching.

        For each filesystem asset, builds the namespace (e.g., 'CHAR_CatStompie_001')
        and matches it against:
        1. Scene assets detected by detect_scene_assets() (which already has namespace)
        2. CTX_Asset nodes that belong to the current shot

        When a match is found, the CTX_Asset node is auto-linked to the Maya reference
        via message attribute if not already linked.
        """
        from maya import cmds

        logger.info("=" * 80)
        logger.info("MATCHING CTX READY STATUS (namespace-based)")
        logger.info("  Total filesystem assets: {}".format(len(self._assets)))
        logger.info("  Total scene assets: {}".format(len(self._scene_assets)))

        # Get shot code for this dialog's shot
        shot_code = self._shot_data.get('shot', '')

        for asset_data in self._assets:
            matched = False

            # Build namespace from asset identity (same format as CTX_Asset namespace attr)
            # Special handling for cameras: namespace is just the asset name
            if asset_data['type'] == 'CAM':
                asset_namespace = asset_data['name']  # e.g., 'SWA_Ep04_SH0140_camera'
            else:
                # Standard assets: TYPE_Name_Variant
                asset_namespace = "{}_{}_{}".format(
                    asset_data['type'],
                    asset_data['name'],
                    asset_data['var']
                )

            logger.info("  Matching asset: {} (namespace: {})".format(
                asset_data['name'], asset_namespace))

            # --- Method 1: Match via scene assets (namespace from detect_scene_assets) ---
            for scene_asset in self._scene_assets:
                scene_ns = scene_asset.get('namespace', '')
                if scene_ns == asset_namespace:
                    # Namespace match found
                    asset_data['maya_node'] = scene_asset['maya_node']

                    # Check if scene asset already has a CTX node linked
                    if scene_asset.get('ctx_ready') and scene_asset.get('ctx_node'):
                        ctx_node = scene_asset['ctx_node']
                        # Verify this CTX node belongs to current shot
                        if shot_code and shot_code in ctx_node:
                            asset_data['ctx_ready'] = True
                            asset_data['ctx_node'] = ctx_node
                            self._read_version_from_ctx(asset_data, ctx_node)
                            matched = True
                            logger.info("    MATCHED via scene namespace: {} -> {} (CTX: {})".format(
                                asset_namespace, scene_asset['maya_node'], ctx_node))
                            break

                    # Scene asset found but no CTX node for this shot yet
                    # Search for a CTX_Asset node for this shot + namespace
                    if not matched:
                        ctx_node = self._find_ctx_for_shot_namespace(
                            shot_code, asset_namespace)
                        if ctx_node:
                            asset_data['ctx_ready'] = True
                            asset_data['ctx_node'] = ctx_node
                            self._read_version_from_ctx(asset_data, ctx_node)

                            # Auto-link the CTX node to the Maya reference
                            self._auto_link_if_needed(ctx_node, scene_asset['maya_node'])

                            matched = True
                            logger.info("    MATCHED via CTX node search: {} -> {} (CTX: {})".format(
                                asset_namespace, scene_asset['maya_node'], ctx_node))
                            break
                        else:
                            # Maya node exists but no CTX node for this shot
                            asset_data['ctx_ready'] = False
                            matched = True
                            logger.info("    Maya ref found but no CTX node: {} -> {}".format(
                                asset_namespace, scene_asset['maya_node']))
                            break

            # --- Method 2: No scene asset match, but CTX node may exist ---
            if not matched:
                ctx_node = self._find_ctx_for_shot_namespace(shot_code, asset_namespace)
                if ctx_node:
                    asset_data['ctx_ready'] = True
                    asset_data['ctx_node'] = ctx_node
                    self._read_version_from_ctx(asset_data, ctx_node)
                    matched = True
                    logger.info("    MATCHED via CTX node only (no scene ref): {} (CTX: {})".format(
                        asset_namespace, ctx_node))

            if not matched:
                logger.info("    NO MATCH for {}".format(asset_namespace))

        logger.info("=" * 80)

    def _find_ctx_for_shot_namespace(self, shot_code, namespace):
        """Find CTX_Asset node matching a shot code and namespace.

        Args:
            shot_code (str): Shot code (e.g., 'SH0140')
            namespace (str): Asset namespace (e.g., 'CHAR_CatStompie_001')

        Returns:
            str or None: CTX_Asset node name, or None
        """
        from maya import cmds

        all_network = cmds.ls(type='network') or []
        ctx_asset_nodes = [n for n in all_network if n.startswith('CTX_Asset_')]

        for ctx_node in ctx_asset_nodes:
            # Check shot code in node name
            if shot_code and shot_code not in ctx_node:
                continue

            if not cmds.attributeQuery('namespace', node=ctx_node, exists=True):
                continue

            node_ns = cmds.getAttr('{}.namespace'.format(ctx_node))
            if node_ns == namespace:
                return ctx_node

        return None

    def _read_version_from_ctx(self, asset_data, ctx_node):
        """Read version from CTX node and update asset_data.

        Args:
            asset_data (dict): Asset data dict to update
            ctx_node (str): CTX_Asset node name
        """
        from maya import cmds

        version_attr = '{}.version'.format(ctx_node)
        if cmds.objExists(version_attr):
            current_version = cmds.getAttr(version_attr)
            if current_version:
                asset_data['current'] = current_version
                # Update status based on version comparison
                if current_version < asset_data['latest']:
                    asset_data['status'] = 'update'
                else:
                    asset_data['status'] = 'valid'
                logger.info("      Version from CTX: {} (latest: {})".format(
                    current_version, asset_data['latest']))

    def _auto_link_if_needed(self, ctx_node, maya_node):
        """Auto-link CTX_Asset to Maya node if not already linked.

        Args:
            ctx_node (str): CTX_Asset node name
            maya_node (str): Maya reference node name
        """
        from core.ctx_linker import link_to_maya_node, get_linked_maya_node

        existing = get_linked_maya_node(ctx_node)
        if existing == maya_node:
            return  # Already linked

        linked = link_to_maya_node(ctx_node, maya_node)
        if linked:
            logger.info("      Auto-linked {} -> {}".format(ctx_node, maya_node))

    def _populate_asset_table(self):
        """Populate asset table with asset data."""
        self.asset_table.setRowCount(0)

        for asset_data in self._assets:
            row = self.asset_table.rowCount()
            self.asset_table.insertRow(row)

            # Column 0: Type
            self.asset_table.setItem(row, 0, QtWidgets.QTableWidgetItem(asset_data['type']))

            # Column 1: Name
            self.asset_table.setItem(row, 1, QtWidgets.QTableWidgetItem(asset_data['name']))

            # Column 2: Var
            self.asset_table.setItem(row, 2, QtWidgets.QTableWidgetItem(asset_data['var']))

            # Column 3: Dept
            self.asset_table.setItem(row, 3, QtWidgets.QTableWidgetItem(asset_data['dept']))

            # Column 4: Current - Version dropdown
            version_combo = QtWidgets.QComboBox()
            versions = self._get_available_versions(asset_data)

            if versions:
                version_combo.addItems(versions)
                current_version = asset_data['current']

                # Set current version as selected
                if current_version in versions:
                    version_combo.setCurrentText(current_version)

                # Color code based on version status
                if current_version == asset_data['latest']:
                    # Latest version - green
                    version_combo.setStyleSheet("QComboBox { background-color: #4CAF50; color: white; font-weight: bold; }")
                elif current_version < asset_data['latest']:
                    # Outdated version - red
                    version_combo.setStyleSheet("QComboBox { background-color: #F44336; color: white; font-weight: bold; }")
                else:
                    # Normal
                    version_combo.setStyleSheet("")

                # Store row index for callback
                version_combo.currentTextChanged.connect(
                    lambda text, r=row: self._on_version_changed(r, text)
                )
            else:
                version_combo.addItem(asset_data['current'])
                version_combo.setEnabled(False)

            self.asset_table.setCellWidget(row, 4, version_combo)

            # Column 5: Latest
            self.asset_table.setItem(row, 5, QtWidgets.QTableWidgetItem(asset_data['latest']))

            # Column 6: Status
            status = asset_data['status']
            if status == 'valid':
                status_widget = QtWidgets.QLabel("Updated")
                status_widget.setStyleSheet("color: green; font-weight: bold;")
            elif status == 'update':
                status_widget = QtWidgets.QLabel("Outdated")
                status_widget.setStyleSheet("color: orange; font-weight: bold;")
            else:
                status_widget = QtWidgets.QLabel("Missing")
                status_widget.setStyleSheet("color: red; font-weight: bold;")

            status_widget.setAlignment(QtCore.Qt.AlignCenter)
            self.asset_table.setCellWidget(row, 6, status_widget)

            # Column 7: Action button - Apply version change
            set_btn = QtWidgets.QPushButton("Apply")
            set_btn.clicked.connect(lambda checked=False, r=row: self._on_apply_version(r))
            self.asset_table.setCellWidget(row, 7, set_btn)

    def _on_search_changed(self, text):
        """Handle search box text change - filter table rows.

        Args:
            text: Search text
        """
        search_text = text.lower().strip()

        # If search is empty, show all rows
        if not search_text:
            for row in range(self.asset_table.rowCount()):
                self.asset_table.setRowHidden(row, False)
            return

        # Filter rows based on search text
        for row in range(self.asset_table.rowCount()):
            asset_data = self._assets[row]

            # Search in multiple fields
            searchable_text = " ".join([
                asset_data.get('type', ''),
                asset_data.get('name', ''),
                asset_data.get('var', ''),
                asset_data.get('dept', ''),
                asset_data.get('current', ''),
                asset_data.get('latest', ''),
                asset_data.get('status', '')
            ]).lower()

            # Show row if search text is found in any field
            if search_text in searchable_text:
                self.asset_table.setRowHidden(row, False)
            else:
                self.asset_table.setRowHidden(row, True)

    def _on_version_changed(self, row, version):
        """Handle version dropdown change.

        Args:
            row: Table row index
            version: Selected version string
        """
        if not version:
            return

        asset_data = self._assets[row]
        logger.debug("Version changed for row {}: {} -> {}".format(
            row, asset_data.get('current'), version))

        # Update asset data (but don't apply to Maya yet)
        asset_data['pending_version'] = version

        # Update status color based on selection
        version_combo = self.asset_table.cellWidget(row, 4)
        if version_combo:
            if version == asset_data['latest']:
                # Latest version - green
                version_combo.setStyleSheet("QComboBox { background-color: #4CAF50; color: white; font-weight: bold; }")
            elif version < asset_data['latest']:
                # Outdated version - red
                version_combo.setStyleSheet("QComboBox { background-color: #F44336; color: white; font-weight: bold; }")
            else:
                # Normal
                version_combo.setStyleSheet("")

    def _on_apply_version(self, row):
        """Handle Apply button click to apply version change.

        Args:
            row: Table row index
        """
        logger.info("=" * 80)
        logger.info("APPLY VERSION BUTTON CLICKED - Row: {}".format(row))

        asset_data = self._assets[row]

        # Get selected version from dropdown
        version_combo = self.asset_table.cellWidget(row, 4)
        if not version_combo:
            logger.warning("No version dropdown found for row {}".format(row))
            return

        version = version_combo.currentText()

        logger.info("Asset: {} {} (current: {} -> new: {})".format(
            asset_data['type'], asset_data['name'], asset_data.get('current', 'N/A'), version))

        if version == asset_data.get('current'):
            logger.info("Version unchanged, skipping")
            return

        if version:
            from maya import cmds
            from core.custom_nodes import CTXAssetNode, CTXManagerNode
            from core.nodes import NodeManager
            from config.platform_config import PlatformConfig

            logger.info("Updating asset data to version: {}".format(version))
            # Update asset data
            asset_data['current'] = version

            # Update CTX_Asset node if it exists
            ctx_node_name = asset_data.get('ctx_node')
            logger.info("CTX node from asset_data: {}".format(ctx_node_name))

            # Fallback: find CTX node by namespace + shot if not already set
            if not ctx_node_name:
                shot_code = self._shot_data.get('shot', '')
                # Special handling for cameras
                if asset_data['type'] == 'CAM':
                    asset_namespace = asset_data['name']  # Camera namespace is just the name
                else:
                    asset_namespace = "{}_{}_{}".format(
                        asset_data['type'], asset_data['name'], asset_data['var'])

                logger.info("Searching for CTX node: shot={}, namespace={}".format(
                    shot_code, asset_namespace))
                ctx_node_name = self._find_ctx_for_shot_namespace(shot_code, asset_namespace)
                logger.info("Found CTX node: {}".format(ctx_node_name))

                if ctx_node_name:
                    asset_data['ctx_node'] = ctx_node_name
                    asset_data['ctx_ready'] = True

            if ctx_node_name and cmds.objExists(ctx_node_name):
                logger.info("CTX node exists, proceeding with update...")
                try:
                    logger.info("Creating CTXAssetNode wrapper for: {}".format(ctx_node_name))
                    ctx_node = CTXAssetNode(ctx_node_name)

                    logger.info("Setting version to: {}".format(version))
                    ctx_node.set_version(version)

                    # Verify version was set
                    verify_version = ctx_node.get_version()
                    logger.info("Version set successfully. Verified: {}".format(verify_version))

                    # Check if this shot is the active shot
                    manager_node = CTXManagerNode.get_manager()
                    is_active_shot = False
                    if manager_node:
                        active_shot_id = manager_node.get_active_shot_id()
                        shot_node_name = "CTX_Shot_{}_{}_{}" .format(
                            self._shot_data.get('ep', ''),
                            self._shot_data.get('seq', ''),
                            self._shot_data.get('shot', '')
                        )
                        # Active shot ID is stored without CTX_Shot_ prefix
                        # e.g., "Ep04_sq0070_SH0140" vs "CTX_Shot_Ep04_sq0070_SH0140"
                        is_active_shot = (active_shot_id == shot_node_name or
                                         "CTX_Shot_" + active_shot_id == shot_node_name)
                        logger.info("Active shot check: active={}, current={}, match={}".format(
                            active_shot_id, shot_node_name, is_active_shot))

                    # If active shot, resolve and apply path to Maya node with new version
                    if is_active_shot:
                        logger.info("ACTIVE SHOT - Resolving path with version {} for {}".format(
                            version, ctx_node_name))
                        try:
                            logger.info("Creating PlatformConfig...")
                            platform_config = PlatformConfig(self._config)

                            logger.info("Creating NodeManager...")
                            node_manager = NodeManager()

                            # Get shot node
                            from core.custom_nodes import CTXShotNode
                            logger.info("Getting shot node: {}".format(shot_node_name))
                            shot_node = CTXShotNode(shot_node_name)

                            # Update asset path (this will resolve template with new version and apply to Maya node)
                            logger.info("Calling update_asset_path...")
                            success = node_manager.update_asset_path(
                                ctx_node, shot_node, self._config, platform_config)

                            logger.info("update_asset_path returned: {}".format(success))

                            if success:
                                logger.info("SUCCESS - Asset path updated to version {}".format(version))
                                # Refresh the table to show the update
                                logger.info("Refreshing asset table...")
                                self._populate_asset_table()
                                QtWidgets.QMessageBox.information(
                                    self,
                                    "Version Updated",
                                    "Asset {} updated to version {}\nPath resolved and applied to Maya node.".format(
                                        asset_data['name'], version)
                                )
                            else:
                                logger.warning("FAILED - update_asset_path returned False")
                                QtWidgets.QMessageBox.warning(
                                    self,
                                    "Path Update Failed",
                                    "Version updated but failed to apply path to Maya node."
                                )
                        except Exception as e:
                            logger.error("EXCEPTION during path resolution: {}".format(e))
                            import traceback
                            logger.error(traceback.format_exc())
                            QtWidgets.QMessageBox.warning(
                                self,
                                "Path Update Failed",
                                "Version updated but failed to resolve path:\n\n{}".format(str(e))
                            )
                    else:
                        logger.info("INACTIVE SHOT - Version updated but path not resolved")
                        QtWidgets.QMessageBox.information(
                            self,
                            "Version Updated",
                            "Asset {} updated to version {}\n(Path will be resolved when this shot becomes active)".format(
                                asset_data['name'], version)
                        )

                except Exception as e:
                    logger.error("EXCEPTION updating CTX_Asset node version: {}".format(e))
                    import traceback
                    logger.error(traceback.format_exc())
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Update Failed",
                        "Failed to update CTX_Asset node:\n\n{}".format(str(e))
                    )
                    return
            else:
                logger.warning("CTX node not found or doesn't exist: {}".format(ctx_node_name))
                logger.warning("Version only updated in UI, not stored in CTX node")

            # Update table
            logger.info("Updating table cell at row {} col 4 to: {}".format(row, version))
            self.asset_table.item(row, 4).setText(version)
            logger.info("Version setting complete!")
            logger.info("=" * 80)

            # Update status
            if version == asset_data['latest']:
                status_widget = QtWidgets.QLabel("Updated")
                status_widget.setStyleSheet("color: green; font-weight: bold;")
            elif version < asset_data['latest']:
                status_widget = QtWidgets.QLabel("Outdated")
                status_widget.setStyleSheet("color: orange; font-weight: bold;")
            else:
                status_widget = QtWidgets.QLabel("Updated")
                status_widget.setStyleSheet("color: green; font-weight: bold;")

            status_widget.setAlignment(QtCore.Qt.AlignCenter)
            self.asset_table.setCellWidget(row, 6, status_widget)

            logger.info("Set version for %s %s to %s", asset_data['type'], asset_data['name'], version)

    def _get_available_versions(self, asset_data):
        """Get list of available versions for an asset from filesystem.

        Args:
            asset_data: Asset dict with type, name, var, dept

        Returns:
            list: Sorted list of version strings (e.g., ['v001', 'v002', 'v003'])
        """
        import re

        versions = []

        try:
            # Build department publish path
            proj_root = self._config.get_root('projRoot')
            project_code = self._config.get_project_code()
            scene_base = self._config.get_static_path('sceneBase')

            dept_path = os.path.join(
                proj_root,
                project_code,
                scene_base,
                self._shot_data['ep'],
                self._shot_data['seq'],
                self._shot_data['shot'],
                asset_data['dept'],
                'publish'
            )

            if not os.path.exists(dept_path):
                logger.warning("Department path does not exist: %s", dept_path)
                return versions

            # Expected filename pattern
            # Special handling for cameras: no type prefix, no variant
            if asset_data['type'] == 'CAM':
                # Camera pattern: Ep04_sq0070_SH0140__SWA_Ep04_SH0140_camera.abc
                filename_pattern = r'{}_{}_{}__{}\.(.*)'.format(
                    self._shot_data['ep'],
                    self._shot_data['seq'],
                    self._shot_data['shot'],
                    asset_data['name']  # Full camera name
                )
            else:
                # Standard pattern: Ep04_sq0070_SH0140__CHAR_CatStompie_001.abc
                filename_pattern = r'{}_{}_{}__{}_{}_{}\.(.*)'.format(
                    self._shot_data['ep'],
                    self._shot_data['seq'],
                    self._shot_data['shot'],
                    asset_data['type'],
                    asset_data['name'],
                    asset_data['var']
                )

            logger.debug("Searching for versions with pattern: %s", filename_pattern)

            # Scan version directories
            for version_dir in os.listdir(dept_path):
                version_path = os.path.join(dept_path, version_dir)
                if not os.path.isdir(version_path):
                    continue
                if not re.match(r'v\d{3}', version_dir):
                    continue

                # Check if this version has the asset file
                for filename in os.listdir(version_path):
                    if re.match(filename_pattern, filename):
                        versions.append(version_dir)
                        logger.debug("Found version %s with file: %s", version_dir, filename)
                        break

            # Sort versions
            versions.sort()

            logger.info("Found %d versions for %s %s: %s",
                       len(versions), asset_data['type'], asset_data['name'], versions)

        except Exception as e:
            logger.error("Failed to get available versions: %s", e)

        return versions

    def _on_convert_to_ctx(self, row):
        """Link asset to CTX node and Maya reference by namespace.

        This button links or re-links assets. If a CTX_Asset node already exists
        for this shot+namespace, it updates it. Otherwise creates one.

        Args:
            row: Table row index
        """
        from maya import cmds
        from core.custom_nodes import CTXAssetNode

        asset_data = self._assets[row]
        # Special handling for cameras: namespace is just the asset name
        if asset_data['type'] == 'CAM':
            asset_namespace = asset_data['name']  # e.g., 'SWA_Ep04_SH0140_camera'
        else:
            asset_namespace = "{}_{}_{}".format(
                asset_data['type'], asset_data['name'], asset_data['var'])
        shot_code = self._shot_data.get('shot', '')

        try:
            # Step 1: Find or create CTX_Asset node
            ctx_node_name = asset_data.get('ctx_node')
            if not ctx_node_name:
                ctx_node_name = self._find_ctx_for_shot_namespace(
                    shot_code, asset_namespace)

            # Step 2: Find Maya reference node by namespace
            maya_node = asset_data.get('maya_node')
            if not maya_node:
                maya_node = self._converter.find_maya_node_by_namespace(asset_namespace)
                if maya_node:
                    asset_data['maya_node'] = maya_node

            if ctx_node_name and cmds.objExists(ctx_node_name):
                # CTX node exists - update version and ensure link
                ctx_node = CTXAssetNode(ctx_node_name)
                ctx_node.set_version(asset_data['current'])

                if maya_node:
                    self._auto_link_if_needed(ctx_node_name, maya_node)

                asset_data['ctx_ready'] = True
                asset_data['ctx_node'] = ctx_node_name

                self._populate_asset_table()
                logger.info("Updated existing CTX node {} (version: {})".format(
                    ctx_node_name, asset_data['current']))
                QtWidgets.QMessageBox.information(
                    self,
                    "Link Updated",
                    "Asset {} linked and updated to {}.".format(
                        asset_data['name'], asset_data['current']))
                return

            # Step 3: Need to create new CTX_Asset node
            shot_node = self._shot_data.get('ctx_node')
            if not shot_node:
                QtWidgets.QMessageBox.warning(
                    self, "No Shot Node",
                    "Cannot convert asset: Shot node not found.")
                return

            if not maya_node:
                QtWidgets.QMessageBox.warning(
                    self, "No Maya Node",
                    "No Maya reference found for namespace: {}\n\n"
                    "Please ensure the asset is loaded in the scene.".format(
                        asset_namespace))
                return

            # Create via converter (handles duplicate check internally)
            ctx_node = self._converter.convert_to_ctx(
                maya_node=maya_node,
                shot_node=shot_node,
                asset_type=asset_data['type'],
                asset_name=asset_data['name'],
                variant=asset_data['var'],
                version=asset_data['current'],
                dept=asset_data['dept']
            )

            asset_data['ctx_ready'] = True
            asset_data['ctx_node'] = ctx_node

            # Assign Maya node to display layer if layer_manager available
            if self._layer_manager and maya_node and shot_node:
                try:
                    layer_name = shot_node.get_display_layer_name()
                    if layer_name and cmds.objExists(layer_name):
                        self._layer_manager.assign_to_layer(maya_node, layer_name)
                        logger.info("Assigned {} to display layer {}".format(maya_node, layer_name))
                    else:
                        logger.warning("Display layer {} not found".format(layer_name))
                except Exception as e:
                    logger.error("Failed to assign to display layer: %s", e)

            self._populate_asset_table()

            logger.info("Created and linked CTX node: {}".format(ctx_node))
            QtWidgets.QMessageBox.information(
                self, "Conversion Successful",
                "Successfully linked {} to CTX.".format(asset_data['name']))

        except Exception as e:
            import traceback
            logger.error("Failed to convert asset: %s\n%s", e, traceback.format_exc())
            QtWidgets.QMessageBox.critical(
                self, "Conversion Failed",
                "Failed:\n\n{}\n\nSee Script Editor for details.".format(str(e)))

    def _on_import_asset(self):
        """Handle Import Asset button click."""
        logger.info("Import Asset clicked")
        QtWidgets.QMessageBox.information(
            self,
            "Import Asset",
            "Import Asset functionality will be implemented in Phase 4C."
        )

    def _on_update_all(self):
        """Handle Update All to Latest button click."""
        logger.info("Update All to Latest clicked")

        from maya import cmds
        from core.custom_nodes import CTXAssetNode, CTXManagerNode, CTXShotNode
        from core.nodes import NodeManager
        from config.platform_config import PlatformConfig

        # Check if there are any non-CTX assets
        non_ctx_assets = [a for a in self._assets if not a.get('ctx_ready', False)]
        if non_ctx_assets:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Non-CTX Assets Found",
                "{} asset(s) are not CTX-ready.\n\nDo you want to convert them first?".format(len(non_ctx_assets)),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )

            if reply == QtWidgets.QMessageBox.Yes:
                # Convert all non-CTX assets
                for asset_data in non_ctx_assets:
                    # Find row index
                    row = self._assets.index(asset_data)
                    try:
                        self._on_convert_to_ctx(row)
                    except Exception as e:
                        logger.error("Failed to convert asset {}: {}".format(asset_data['name'], e))
                        continue

        # Check if this shot is the active shot
        manager_node = CTXManagerNode.get_manager()
        is_active_shot = False
        shot_node_name = None
        if manager_node:
            active_shot_id = manager_node.get_active_shot_id()
            shot_node_name = "CTX_Shot_{}_{}_{}" .format(
                self._shot_data.get('ep', ''),
                self._shot_data.get('seq', ''),
                self._shot_data.get('shot', '')
            )
            is_active_shot = (active_shot_id == shot_node_name)

        # Update all outdated assets to latest version
        updated_count = 0
        failed_count = 0
        path_resolved_count = 0

        for asset_data in self._assets:
            if asset_data['status'] == 'update':
                # Update UI data
                old_version = asset_data['current']
                new_version = asset_data['latest']
                asset_data['current'] = new_version
                asset_data['status'] = 'valid'

                # Find CTX_Asset node (with namespace fallback)
                ctx_node_name = asset_data.get('ctx_node')
                if not ctx_node_name:
                    shot_code = self._shot_data.get('shot', '')
                    # Special handling for cameras
                    if asset_data['type'] == 'CAM':
                        ns = asset_data['name']
                    else:
                        ns = "{}_{}_{}".format(
                            asset_data['type'], asset_data['name'], asset_data['var'])
                    ctx_node_name = self._find_ctx_for_shot_namespace(shot_code, ns)

                if ctx_node_name and cmds.objExists(ctx_node_name):
                    try:
                        ctx_node = CTXAssetNode(ctx_node_name)
                        ctx_node.set_version(new_version)
                        logger.info("Updated {} from {} to {}".format(
                            ctx_node_name, old_version, new_version))
                        updated_count += 1

                        # If active shot, resolve and apply path
                        if is_active_shot and shot_node_name:
                            try:
                                platform_config = PlatformConfig(self._config)
                                node_manager = NodeManager()
                                shot_node = CTXShotNode(shot_node_name)

                                # Update asset path (resolves template with new version and applies to Maya node)
                                success = node_manager.update_asset_path(
                                    ctx_node, shot_node, self._config, platform_config)

                                if success:
                                    path_resolved_count += 1
                                    logger.info("Resolved path for {} to version {}".format(
                                        ctx_node_name, new_version))
                            except Exception as e:
                                logger.error("Failed to resolve path for {}: {}".format(
                                    ctx_node_name, e))

                    except Exception as e:
                        logger.error("Failed to update CTX_Asset node {}: {}".format(
                            ctx_node_name, e))
                        failed_count += 1
                else:
                    logger.warning("No CTX node for {} (UI only update)".format(
                        asset_data['name']))
                    updated_count += 1

        if updated_count > 0 or failed_count > 0:
            self._populate_asset_table()

            if failed_count > 0:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Update Complete with Errors",
                    "Updated {} asset(s) to latest version.\nFailed to update {} asset(s).\n\nSee Script Editor for details.".format(
                        updated_count, failed_count)
                )
            else:
                if is_active_shot:
                    QtWidgets.QMessageBox.information(
                        self,
                        "Update Complete",
                        "Updated {} asset(s) to latest version.\n{} asset path(s) resolved and applied to Maya nodes.".format(
                            updated_count, path_resolved_count)
                    )
                else:
                    QtWidgets.QMessageBox.information(
                        self,
                        "Update Complete",
                        "Updated {} asset(s) to latest version.\n(Paths will be resolved when this shot becomes active)".format(
                            updated_count)
                    )
        else:
            QtWidgets.QMessageBox.information(
                self,
                "No Updates",
                "All assets are already up to date."
            )

    def _on_validate_all(self):
        """Handle Validate All button click."""
        logger.info("Validate All clicked")
        QtWidgets.QMessageBox.information(
            self,
            "Validate All",
            "Validate All functionality will be implemented in Phase 4C.\n\nWill check file existence for all assets."
        )

    def _on_apply(self):
        """Handle Apply button click - Apply version changes to selected assets."""
        logger.info("Apply clicked - applying version changes to selected assets")

        try:
            from maya import cmds
        except ImportError:
            from tests.mock_maya import cmds

        from core.resolver import PathResolver
        from config.platform_config import PlatformConfig

        # Get selected rows
        selected_rows = set()
        for item in self.asset_table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QtWidgets.QMessageBox.information(
                self,
                "No Selection",
                "Please select one or more assets to apply version changes."
            )
            return

        logger.info("Applying version changes to {} selected asset(s)".format(len(selected_rows)))

        # Apply version changes to selected assets
        platform_config = PlatformConfig(self._config)
        resolver = PathResolver(self._config, platform_config)

        updated_count = 0
        errors = []

        for row in sorted(selected_rows):
            asset_data = self._assets[row]

            # Get selected version from dropdown
            version_combo = self.asset_table.cellWidget(row, 4)
            if not version_combo:
                continue

            new_version = version_combo.currentText()

            try:
                # Skip if not CTX-ready
                if not asset_data.get('ctx_ready', False):
                    errors.append("{}: Not CTX-ready".format(asset_data['name']))
                    continue

                ctx_node = asset_data.get('ctx_node')
                if not ctx_node or not cmds.objExists(ctx_node):
                    errors.append("{}: CTX node not found".format(asset_data['name']))
                    continue

                # Get current version from CTX node
                old_version = cmds.getAttr('{}.version'.format(ctx_node))

                if new_version == old_version:
                    continue  # No change

                # Build context for path resolution
                context = {
                    'project': self._shot_data.get('project', self._config.get_project_code()),
                    'ep': self._shot_data['ep'],
                    'seq': self._shot_data['seq'],
                    'shot': self._shot_data['shot'],
                    'dept': asset_data['dept'],
                    'asset_type': asset_data['type'],
                    'asset_name': asset_data['name'],
                    'variant': asset_data['var']
                }

                # Resolve new path using tokens
                template_name = 'assetPath'
                new_path = resolver.resolve_path(
                    template_name,
                    context,
                    version=new_version,
                    validate_exists=True
                )

                # Update CTX node
                cmds.setAttr('{}.version'.format(ctx_node), new_version, type='string')
                cmds.setAttr('{}.file_path'.format(ctx_node), new_path, type='string')

                # Update Maya node
                maya_node = asset_data.get('maya_node')
                if maya_node and cmds.objExists(maya_node):
                    node_type = cmds.nodeType(maya_node)
                    if node_type == 'aiStandIn':
                        cmds.setAttr('{}.dso'.format(maya_node), new_path, type='string')
                    elif node_type == 'RedshiftProxyMesh':
                        cmds.setAttr('{}.fileName'.format(maya_node), new_path, type='string')
                    elif node_type == 'reference':
                        # For references, use file command to change the reference path
                        cmds.file(new_path, loadReference=maya_node)

                # Update asset_data
                asset_data['current'] = new_version
                if new_version == asset_data['latest']:
                    asset_data['status'] = 'valid'
                elif new_version < asset_data['latest']:
                    asset_data['status'] = 'update'

                updated_count += 1
                logger.info("Updated {} to version {} -> {}".format(
                    asset_data['name'], old_version, new_version
                ))

            except Exception as e:
                error_msg = "Failed to update {}: {}".format(
                    asset_data.get('name', 'unknown'), str(e)
                )
                errors.append(error_msg)
                logger.error(error_msg)

        # Refresh table to show updated versions
        if updated_count > 0:
            self._populate_asset_table()

        # Show results
        if errors:
            QtWidgets.QMessageBox.warning(
                self,
                "Update Errors",
                "Updated {} asset(s) with {} error(s):\n\n{}".format(
                    updated_count, len(errors), '\n'.join(errors[:5])
                )
            )
        elif updated_count > 0:
            QtWidgets.QMessageBox.information(
                self,
                "Update Complete",
                "Successfully updated {} asset(s) to new versions.".format(updated_count)
            )
        else:
            QtWidgets.QMessageBox.information(
                self,
                "No Changes",
                "No asset version changes to apply."
            )

    def get_assets(self):
        """Get the current asset list.

        Returns:
            list: List of asset dicts
        """
        return self._assets

