# =============================================================================
# Pipeline Tools - Shot Build - Place3D Linker - BlendShape (Anim->Groom) - Assign Shader
# ALL TABS USE THE SHARED HEADER:
#   - Geometry NS (for Place3D, Assign Shader, and BlendShape)
#   - Shader NS   (for Place3D and Assign Shader)
# BlendShape: Groom-first scan, BLENDSHAPE LIVES ON GROOM, ANIM is TARGET,
#             new/added weights set to 1.0 for immediate effect
# =============================================================================

from __future__ import print_function
import json, ast, os, re
import maya.cmds as cmds

# Qt imports (Maya 2020+ ships PySide2)
try:
    from PySide2 import QtWidgets, QtCore
    from shiboken2 import wrapInstance
except Exception:
    from PySide6 import QtWidgets, QtCore
    from shiboken6 import wrapInstance

import maya.OpenMayaUI as omui

WIN_TITLE  = "Pipeline Tools - Shot Build - Place3D - BlendShape - Assign Shader"
WIN_OBJECT = "EE_PipelineTools_ShotBuild_AllInOne"

# -----------------------------------------------------------------------------
# Common helpers
# -----------------------------------------------------------------------------

def _maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget)

def _short(node):
    return node.split(":")[-1] if node else node

def _list_namespaces():
    ns = (cmds.namespaceInfo(listOnlyNamespaces=True) or [])
    bad = {"UI", "shared"}
    out = []
    for n in ns:
        if n in bad:
            continue
        if cmds.ls(n + ":*", long=True):
            out.append(n)
    return sorted(out, key=lambda x: (x.count(":"), x))

def _unlock_trs(node):
    for ch in ("translateX","translateY","translateZ",
               "rotateX","rotateY","rotateZ",
               "scaleX","scaleY","scaleZ"):
        a = "{}.{}".format(node, ch)
        if cmds.objExists(a):
            try:
                if cmds.getAttr(a, lock=True):
                    cmds.setAttr(a, lock=False)
                cmds.setAttr(a, keyable=True)
            except Exception:
                pass

def _first_mesh_shape(xform):
    """Return first non-intermediate mesh shape under transform."""
    shapes = cmds.listRelatives(xform, shapes=True, ni=True, fullPath=True) or []
    for s in shapes:
        if cmds.nodeType(s) == "mesh" and not cmds.getAttr(s + ".intermediateObject"):
            return s
    return None

# =============================================================================
# Shot Build Helper Functions
# =============================================================================

# Category mappings
CATEGORY_MAPPINGS = {
    "Character": "CHAR",
    "Props": "PROP",
    "Setdress": "SDRS",
    "Sets": "SETS",
    "Dressing": "DRSG"  # New shot-based dressing category
}

def _validate_directory(path):
    """Check if directory exists and is accessible."""
    try:
        return os.path.exists(path) and os.path.isdir(path)
    except Exception:
        return False

def _list_directories(parent_path):
    """List subdirectories in parent_path, return sorted list."""
    if not _validate_directory(parent_path):
        return []
    try:
        dirs = []
        for item in os.listdir(parent_path):
            full_path = os.path.join(parent_path, item)
            if os.path.isdir(full_path):
                dirs.append(item)
        return sorted(dirs)
    except Exception:
        return []

def _list_versions(version_path):
    """List version directories, return sorted with latest first."""
    if not _validate_directory(version_path):
        return []
    try:
        versions = []
        for item in os.listdir(version_path):
            full_path = os.path.join(version_path, item)
            if os.path.isdir(full_path):
                versions.append(item)
        # Sort versions with latest first (assuming v001, v002, etc format)
        versions.sort(reverse=True)
        return versions
    except Exception:
        return []

def _parse_cache_filename(filename):
    """Parse cache filename: Ep01_sq0010_SH0020__PROP_ChickenAlarmClock_001.abc
    Also handles camera files: SWA_Ep01_SH0020_camera.abc
    Returns dict with ep, seq, shot, category, name, identifier"""
    if not filename.endswith('.abc'):
        return None

    base = filename[:-4]  # remove .abc
    try:
        # Check for camera files first (different pattern)
        if 'camera' in base.lower():
            # Handle camera files: SWA_Ep01_SH0020_camera
            parts = base.split('_')
            if len(parts) >= 4 and 'camera' in parts[-1].lower():
                # Extract episode and shot info
                ep = None
                shot = None
                for part in parts:
                    if part.startswith('Ep'):
                        ep = part
                    elif part.startswith('SH'):
                        shot = part

                return {
                    'ep': ep or 'Ep01',
                    'seq': 'sq0000',  # Default sequence for cameras
                    'shot': shot or 'SH0000',
                    'category': 'CAM',
                    'name': 'camera',
                    'identifier': '001',
                    'namespace': 'CAM_camera_001'
                }

        # Standard format: Split by double underscore first
        if '__' not in base:
            return None

        shot_part, asset_part = base.split('__', 1)

        # Parse shot part: Ep01_sq0010_SH0020
        shot_parts = shot_part.split('_')
        if len(shot_parts) < 3:
            return None

        ep = shot_parts[0]
        seq = shot_parts[1]
        shot = shot_parts[2]

        # Parse asset part: PROP_ChickenAlarmClock_001 or DRSG_SH0240
        asset_parts = asset_part.split('_')

        # Special handling for DRSG (Dressing) - format: DRSG_{shot}
        if asset_parts[0] == 'DRSG' and len(asset_parts) == 2:
            category = asset_parts[0]
            name = asset_parts[1]  # Shot name (e.g., SH0240)
            identifier = '001'  # Default identifier for DRSG
            namespace = '{}_{}'.format(category, name)  # DRSG_SH0240
        else:
            # Standard format: CATEGORY_name_identifier
            if len(asset_parts) < 3:
                return None

            category = asset_parts[0]
            name = '_'.join(asset_parts[1:-1])  # Handle multi-part names
            identifier = asset_parts[-1]
            namespace = '{}_{}_{}'.format(category, name, identifier)

        return {
            'ep': ep,
            'seq': seq,
            'shot': shot,
            'category': category,
            'name': name,
            'identifier': identifier,
            'namespace': namespace
        }
    except Exception:
        return None

def _get_asset_namespace(category, name, identifier):
    """Generate namespace for asset: CATEGORY_name_identifier"""
    return "{}_{}_{}".format(category, name, identifier)

def _find_shader_paths(category, name, project_root="V:/SWA"):
    """Find shader paths for asset based on category and name."""
    shader_paths = []

    # Define search paths based on category
    if category == "CHAR":
        search_paths = [
            os.path.join(project_root, "all", "asset", "Character", "Main", name, "hero"),
            os.path.join(project_root, "all", "asset", "Character", "object", name, "hero")
        ]
    elif category == "SETS":
        search_paths = [
            os.path.join(project_root, "all", "asset", "Sets", "Exterior", name, "hero"),
            os.path.join(project_root, "all", "asset", "Sets", "Interior", name, "hero")
        ]
    else:  # PROP, SDRS
        cat_name = "Props" if category == "PROP" else "Setdress"
        search_paths = [
            os.path.join(project_root, "all", "asset", cat_name, "Main", name, "hero"),
            os.path.join(project_root, "all", "asset", cat_name, "object", name, "hero")
        ]

    # Check for shader and groom files
    for path in search_paths:
        if _validate_directory(path):
            shader_file = os.path.join(path, "{}_rsshade.ma".format(name))
            groom_file = os.path.join(path, "{}_groom.ma".format(name))

            if os.path.exists(shader_file):
                shader_paths.append(("shader", shader_file))
            if os.path.exists(groom_file):
                shader_paths.append(("groom", groom_file))

    return shader_paths

# =============================================================================
# TAB 1: Shot Build System
# =============================================================================

class ShotBuildTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ShotBuildTab, self).__init__(parent)
        self.assets_data = []  # Store parsed asset information
        self.current_shot_path = ""
        self._build()
        self._wire()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Directory Root Configuration
        root_layout = QtWidgets.QHBoxLayout()
        root_layout.addWidget(QtWidgets.QLabel("Project Root:"))
        self.root_path_edit = QtWidgets.QLineEdit("V:/")
        self.root_path_edit.setMinimumWidth(200)
        root_layout.addWidget(self.root_path_edit)
        root_layout.addStretch()
        layout.addLayout(root_layout)

        # Navigation Dropdowns
        nav_layout = QtWidgets.QGridLayout()

        # Project dropdown
        nav_layout.addWidget(QtWidgets.QLabel("Project:"), 0, 0)
        self.project_combo = QtWidgets.QComboBox()
        self.project_combo.setMinimumWidth(120)
        nav_layout.addWidget(self.project_combo, 0, 1)

        # Episode dropdown
        nav_layout.addWidget(QtWidgets.QLabel("Episode:"), 0, 2)
        self.episode_combo = QtWidgets.QComboBox()
        self.episode_combo.setMinimumWidth(100)
        nav_layout.addWidget(self.episode_combo, 0, 3)

        # Sequence dropdown
        nav_layout.addWidget(QtWidgets.QLabel("Sequence:"), 1, 0)
        self.sequence_combo = QtWidgets.QComboBox()
        self.sequence_combo.setMinimumWidth(120)
        nav_layout.addWidget(self.sequence_combo, 1, 1)

        # Shot dropdown
        nav_layout.addWidget(QtWidgets.QLabel("Shot:"), 1, 2)
        self.shot_combo = QtWidgets.QComboBox()
        self.shot_combo.setMinimumWidth(120)
        nav_layout.addWidget(self.shot_combo, 1, 3)

        # Version dropdown
        nav_layout.addWidget(QtWidgets.QLabel("Version:"), 2, 0)
        self.version_combo = QtWidgets.QComboBox()
        self.version_combo.setMinimumWidth(100)
        nav_layout.addWidget(self.version_combo, 2, 1)

        # Refresh and Load buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        self.load_cache_btn = QtWidgets.QPushButton("Load Cache List")
        self.load_cache_btn.setStyleSheet("font-weight: bold;")

        # Auto-detect button
        self.auto_detect_btn = QtWidgets.QPushButton("Auto-Detect Scene")
        self.auto_detect_btn.setToolTip("Auto-detect shot context from current Maya scene file name")
        self.auto_detect_btn.setStyleSheet("background-color: #4CAF50; color: white;")

        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.auto_detect_btn)
        btn_layout.addWidget(self.load_cache_btn)
        btn_layout.addStretch()
        nav_layout.addLayout(btn_layout, 2, 2, 1, 2)

        layout.addLayout(nav_layout)

        # Assets Table
        self.assets_table = QtWidgets.QTableWidget(0, 8)
        self.assets_table.setHorizontalHeaderLabels([
            "Cache File", "Category", "Name", "Identifier", "Namespace", "Status", "Build", "Update"
        ])
        self.assets_table.horizontalHeader().setStretchLastSection(False)
        self.assets_table.horizontalHeader().setSectionResizeMode(6, QtWidgets.QHeaderView.Fixed)  # Build column fixed width
        self.assets_table.horizontalHeader().setSectionResizeMode(7, QtWidgets.QHeaderView.Fixed)  # Update column fixed width
        self.assets_table.setColumnWidth(6, 80)  # Build button column width
        self.assets_table.setColumnWidth(7, 80)  # Update button width
        layout.addWidget(self.assets_table, 1)

        # Scene Setup Section
        setup_group = QtWidgets.QGroupBox("Scene Setup")
        setup_layout = QtWidgets.QVBoxLayout(setup_group)

        # Scene options
        scene_opts_layout = QtWidgets.QHBoxLayout()
        self.scene_new_radio = QtWidgets.QRadioButton("New Scene")
        self.scene_replace_radio = QtWidgets.QRadioButton("Replace References")
        self.scene_remove_radio = QtWidgets.QRadioButton("Remove All & Import")
        self.scene_new_radio.setChecked(True)
        scene_opts_layout.addWidget(self.scene_new_radio)
        scene_opts_layout.addWidget(self.scene_replace_radio)
        scene_opts_layout.addWidget(self.scene_remove_radio)
        scene_opts_layout.addStretch()
        setup_layout.addLayout(scene_opts_layout)

        # Logging options
        logging_opts_layout = QtWidgets.QHBoxLayout()
        self.verbose_logging_checkbox = QtWidgets.QCheckBox("Verbose Logging")
        self.verbose_logging_checkbox.setToolTip("Enable detailed logging for component referencing and build processes")
        self.verbose_logging_checkbox.setStyleSheet("font-weight: bold; color: #4CAF50;")
        logging_opts_layout.addWidget(self.verbose_logging_checkbox)
        logging_opts_layout.addStretch()
        setup_layout.addLayout(logging_opts_layout)

        # Place3D method selection
        place3d_method_layout = QtWidgets.QHBoxLayout()
        self.use_matrix_method_checkbox = QtWidgets.QCheckBox("Use Matrix Method for Place3D (instead of Constraints)")
        self.use_matrix_method_checkbox.setToolTip(
            "Use decomposeMatrix nodes instead of parent/scale constraints for Place3D linking.\n"
            "Matrix method: Cleaner scene, better performance, 1 node per link.\n"
            "Constraint method (default): Traditional approach, 2 nodes per link."
        )
        self.use_matrix_method_checkbox.setStyleSheet("font-weight: bold; color: #2196F3;")
        self.use_matrix_method_checkbox.setChecked(False)  # Default to constraint method
        place3d_method_layout.addWidget(self.use_matrix_method_checkbox)
        place3d_method_layout.addStretch()
        setup_layout.addLayout(place3d_method_layout)

        # SETS Instance optimization option
        sets_instance_layout = QtWidgets.QHBoxLayout()
        self.use_sets_instances_checkbox = QtWidgets.QCheckBox("Use Instances for Duplicate SETS Components (Optimization)")
        self.use_sets_instances_checkbox.setToolTip(
            "Optimize SETS build by using Maya instances for duplicate components.\n"
            "Instead of referencing the same geo file multiple times, creates:\n"
            "  - 1 reference for the MASTER component\n"
            "  - Instances for all duplicates (sharing geometry & shaders)\n"
            "Result: Faster load times, less memory usage, cleaner scene."
        )
        self.use_sets_instances_checkbox.setStyleSheet("font-weight: bold; color: #FF9800;")
        self.use_sets_instances_checkbox.setChecked(False)  # Default to traditional references
        sets_instance_layout.addWidget(self.use_sets_instances_checkbox)
        sets_instance_layout.addStretch()
        setup_layout.addLayout(sets_instance_layout)

        # Build buttons
        build_layout = QtWidgets.QVBoxLayout()

        # Main build button (all steps)
        main_build_layout = QtWidgets.QHBoxLayout()
        self.build_all_btn = QtWidgets.QPushButton("[START] BUILD ALL STEPS (1-5): Setup + Sets + Assets + Assign + Place3D + BlendShape")
        self.build_all_btn.setStyleSheet("font-weight: bold; background-color: #2196F3; color: white; padding: 10px; font-size: 14px;")
        self.build_all_btn.setMinimumHeight(50)
        main_build_layout.addWidget(self.build_all_btn)
        build_layout.addLayout(main_build_layout)

        # Subprocess build section
        subprocess_layout = QtWidgets.QHBoxLayout()

        # Department selection
        subprocess_layout.addWidget(QtWidgets.QLabel("Target Dept:"))
        self.dept_combo = QtWidgets.QComboBox()
        self.dept_combo.addItems(["anim", "lighting", "comp", "fx", "layout"])
        self.dept_combo.setCurrentText("lighting")  # Default to lighting
        subprocess_layout.addWidget(self.dept_combo)

        # Subprocess build button
        self.build_subprocess_btn = QtWidgets.QPushButton("[UPDATE] BUILD IN SUBPROCESS & SAVE")
        self.build_subprocess_btn.setStyleSheet("font-weight: bold; background-color: #9C27B0; color: white; padding: 8px;")
        subprocess_layout.addWidget(self.build_subprocess_btn)

        # Batch build button
        self.batch_build_btn = QtWidgets.QPushButton("[BATCH] BATCH BUILD SHOTS")
        self.batch_build_btn.setStyleSheet("font-weight: bold; background-color: #FF5722; color: white; padding: 8px;")
        subprocess_layout.addWidget(self.batch_build_btn)

        # Update assets button
        self.update_assets_btn = QtWidgets.QPushButton("[UPDATE] UPDATE ASSETS")
        self.update_assets_btn.setStyleSheet("font-weight: bold; background-color: #FF9800; color: white; padding: 8px;")
        self.update_assets_btn.setToolTip("Update assets from new shot version (only geometry from */publish/{version} paths)")
        subprocess_layout.addWidget(self.update_assets_btn)

        subprocess_layout.addStretch()
        build_layout.addLayout(subprocess_layout)

        # Individual step buttons (for debugging/manual use)
        individual_layout = QtWidgets.QHBoxLayout()
        self.setup_scene_btn = QtWidgets.QPushButton("Setup Scene")
        self.build_sets_btn = QtWidgets.QPushButton("Build Sets (Step 1)")
        self.build_assets_btn = QtWidgets.QPushButton("Build Assets + Assign + Place3D + BlendShape (Steps 2+3+4)")
        self.build_assets_btn.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
        self.assign_shaders_btn = QtWidgets.QPushButton("Assign Shaders Only (Step 3)")
        self.create_blendshapes_btn = QtWidgets.QPushButton("Create BlendShapes Only (Step 4)")

        individual_layout.addWidget(self.setup_scene_btn)
        individual_layout.addWidget(self.build_sets_btn)
        individual_layout.addWidget(self.build_assets_btn)
        individual_layout.addWidget(self.assign_shaders_btn)
        individual_layout.addWidget(self.create_blendshapes_btn)
        build_layout.addLayout(individual_layout)

        setup_layout.addLayout(build_layout)

        layout.addWidget(setup_group)

        # Log
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(150)
        layout.addWidget(self.log)

    def _wire(self):
        # Connect dropdown change events
        self.root_path_edit.textChanged.connect(self._on_root_changed)
        self.project_combo.currentTextChanged.connect(self._on_project_changed)
        self.episode_combo.currentTextChanged.connect(self._on_episode_changed)
        self.sequence_combo.currentTextChanged.connect(self._on_sequence_changed)
        self.shot_combo.currentTextChanged.connect(self._on_shot_changed)

        # Connect buttons
        self.refresh_btn.clicked.connect(self._refresh_projects)
        self.auto_detect_btn.clicked.connect(self._auto_detect_shot_context)
        self.load_cache_btn.clicked.connect(self._load_cache_list)
        self.build_all_btn.clicked.connect(self._build_all_steps)
        self.build_subprocess_btn.clicked.connect(self._build_in_subprocess)
        self.batch_build_btn.clicked.connect(self._batch_build_shots)
        self.update_assets_btn.clicked.connect(self._update_assets)
        self.setup_scene_btn.clicked.connect(self._setup_scene)
        self.build_sets_btn.clicked.connect(self._build_sets)
        self.build_assets_btn.clicked.connect(self._build_assets)
        self.assign_shaders_btn.clicked.connect(self._assign_shaders)
        self.create_blendshapes_btn.clicked.connect(self._create_blendshapes)

        # Initial load
        self._refresh_projects()

        # Auto-detect shot context from current scene on startup
        self._auto_detect_shot_context()

    def _log(self, msg):
        """Add message to log."""
        self.log.appendPlainText(msg)

    def _log_verbose(self, msg):
        """Add message to log only if verbose logging is enabled."""
        if hasattr(self, 'verbose_logging_checkbox') and self.verbose_logging_checkbox.isChecked():
            self._log(msg)

    def _on_root_changed(self):
        """Handle root path change."""
        self._refresh_projects()

    def _refresh_projects(self):
        """Refresh project list - reverted to synchronous for reliability."""
        root = self.root_path_edit.text().strip()
        if not root:
            return

        self.project_combo.clear()
        projects = _list_directories(root)
        if projects:
            self.project_combo.addItems(projects)
            self._log("Found {} projects in {}".format(len(projects), root))
        else:
            self._log("No projects found in {}".format(root))

    def _on_project_changed(self):
        """Handle project selection change."""
        self.episode_combo.clear()
        self.sequence_combo.clear()
        self.shot_combo.clear()
        self.version_combo.clear()

        project = self.project_combo.currentText()
        if not project:
            return

        root = self.root_path_edit.text().strip()
        scene_path = os.path.join(root, project, "all", "scene")

        episodes = _list_directories(scene_path)
        if episodes:
            self.episode_combo.addItems(episodes)
            self._log("Found {} episodes in {}".format(len(episodes), project))
        else:
            self._log("No episodes found in {}".format(project))

    def _on_episode_changed(self):
        """Handle episode selection change."""
        self.sequence_combo.clear()
        self.shot_combo.clear()
        self.version_combo.clear()

        project = self.project_combo.currentText()
        episode = self.episode_combo.currentText()
        if not project or not episode:
            return

        root = self.root_path_edit.text().strip()
        ep_path = os.path.join(root, project, "all", "scene", episode)

        sequences = _list_directories(ep_path)
        if sequences:
            self.sequence_combo.addItems(sequences)
        else:
            self._log("No sequences found in {}/{}".format(project, episode))

    def _on_sequence_changed(self):
        """Handle sequence selection change."""
        self.shot_combo.clear()
        self.version_combo.clear()

        project = self.project_combo.currentText()
        episode = self.episode_combo.currentText()
        sequence = self.sequence_combo.currentText()
        if not all([project, episode, sequence]):
            return

        root = self.root_path_edit.text().strip()
        seq_path = os.path.join(root, project, "all", "scene", episode, sequence)

        shots = _list_directories(seq_path)
        if shots:
            self.shot_combo.addItems(shots)
        else:
            self._log("No shots found in {}/{}/{}".format(project, episode, sequence))

    def _on_shot_changed(self):
        """Handle shot selection change."""
        self.version_combo.clear()

        project = self.project_combo.currentText()
        episode = self.episode_combo.currentText()
        sequence = self.sequence_combo.currentText()
        shot = self.shot_combo.currentText()
        if not all([project, episode, sequence, shot]):
            return

        root = self.root_path_edit.text().strip()
        version_path = os.path.join(root, project, "all", "scene", episode, sequence, shot, "anim", "publish")

        versions = _list_versions(version_path)
        if versions:
            self.version_combo.addItems(versions)
        else:
            self._log("No versions found for {}/{}/{}/{}".format(project, episode, sequence, shot))

    def _load_cache_list(self):
        """Load and parse cache files from selected shot/version."""
        project = self.project_combo.currentText()
        episode = self.episode_combo.currentText()
        sequence = self.sequence_combo.currentText()
        shot = self.shot_combo.currentText()
        version = self.version_combo.currentText()

        if not all([project, episode, sequence, shot, version]):
            self._log("[ERROR] Please select project, episode, sequence, shot, and version")
            return

        root = self.root_path_edit.text().strip()
        cache_path = os.path.join(root, project, "all", "scene", episode, sequence, shot, "anim", "publish", version)

        if not _validate_directory(cache_path):
            self._log("[ERROR] Cache directory does not exist: {}".format(cache_path))
            return

        self.current_shot_path = cache_path
        self.assets_data = []

        # List all .abc files
        try:
            files = [f for f in os.listdir(cache_path) if f.endswith('.abc')]
            self._log("Found {} cache files in {}".format(len(files), cache_path))

            # Parse each file
            for filename in files:
                parsed = _parse_cache_filename(filename)
                if parsed:
                    parsed['filename'] = filename
                    parsed['full_path'] = os.path.join(cache_path, filename)
                    self.assets_data.append(parsed)
                else:
                    self._log("[WARNING] Could not parse filename: {}".format(filename))

            self._populate_assets_table()
            self._log("Parsed {} valid assets from cache files".format(len(self.assets_data)))

        except Exception as e:
            self._log("[ERROR] Failed to load cache list: {}".format(str(e)))

    def _populate_assets_table(self):
        """Populate the assets table with parsed data."""
        self.assets_table.setRowCount(0)

        for i, asset in enumerate(self.assets_data):
            row = self.assets_table.rowCount()
            self.assets_table.insertRow(row)

            self.assets_table.setItem(row, 0, QtWidgets.QTableWidgetItem(asset['filename']))
            self.assets_table.setItem(row, 1, QtWidgets.QTableWidgetItem(asset['category']))
            self.assets_table.setItem(row, 2, QtWidgets.QTableWidgetItem(asset['name']))
            self.assets_table.setItem(row, 3, QtWidgets.QTableWidgetItem(asset['identifier']))
            self.assets_table.setItem(row, 4, QtWidgets.QTableWidgetItem(asset['namespace']))
            self.assets_table.setItem(row, 5, QtWidgets.QTableWidgetItem("Ready"))

            # Add build button
            build_btn = QtWidgets.QPushButton("Build")
            build_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
            build_btn.clicked.connect(lambda checked=False, idx=i: self._build_single_asset(idx))
            self.assets_table.setCellWidget(row, 6, build_btn)

            # Add update button
            update_btn = QtWidgets.QPushButton("Update")
            update_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
            update_btn.setToolTip("Update this asset from new version (only geometry from */publish/{version} paths)")
            update_btn.clicked.connect(lambda checked=False, idx=i: self._update_single_asset(idx))
            self.assets_table.setCellWidget(row, 7, update_btn)

        self.assets_table.resizeColumnsToContents()

    def _setup_scene(self):
        """Setup scene with enhanced user choice for current vs new scene."""
        # Check current scene state
        scene_state = self._check_scene_state()

        # Ask user for scene choice
        choice = self._ask_scene_choice(scene_state["has_content"], context="setup")

        if choice == "cancel":
            self._log("[SETUP] Setup cancelled by user")
            return
        elif choice == "new":
            self._setup_new_scene_enhanced()
        elif choice == "current":
            self._setup_current_scene_enhanced(scene_state)

    def _setup_new_scene_enhanced(self):
        """Create new scene with predefined groups."""
        result = cmds.confirmDialog(
            title="New Scene Confirmation",
            message="This will create a new scene and lose any unsaved changes.\n\nContinue?",
            button=["Yes", "No"],
            defaultButton="Yes",
            cancelButton="No",
            dismissString="No"
        )

        if result == "Yes":
            cmds.file(new=True, force=True)
            self._create_scene_groups()
            self._log("[SETUP] Created new scene with all asset groups")
        else:
            self._log("[SETUP] New scene creation cancelled")

    def _setup_current_scene_enhanced(self, scene_state):
        """Setup groups in current scene, creating only missing ones."""
        existing_groups = scene_state["existing_groups"]
        missing_groups = scene_state["missing_groups"]
        matching_refs = scene_state["matching_references"]

        if existing_groups:
            self._log("[SETUP] Found existing groups: {}".format(", ".join(existing_groups)))

        if matching_refs:
            self._log("[SETUP] Found {} matching references for current shot".format(len(matching_refs)))

        if missing_groups:
            self._log("[SETUP] Creating missing groups: {}".format(", ".join(missing_groups)))
            for grp_name in missing_groups:
                grp = cmds.group(empty=True, name=grp_name)
                self._log("Created group: {}".format(grp))
        else:
            self._log("[SETUP] All standard groups already exist")

        self._log("[SETUP] Scene setup complete in current scene")

    def _setup_new_scene(self):
        """Create new scene with predefined groups."""
        result = cmds.confirmDialog(
            title="New Scene",
            message="This will create a new scene. Continue?",
            button=["Yes", "No"],
            defaultButton="Yes",
            cancelButton="No",
            dismissString="No"
        )

        if result == "Yes":
            cmds.file(new=True, force=True)
            self._create_scene_groups()
            self._log("[SETUP] Created new scene with asset groups")

    def _setup_replace_references(self):
        """Replace references with same name but new shot."""
        self._log("[SETUP] Replace references mode - not implemented yet")
        # TODO: Implement reference replacement logic

    def _setup_remove_all(self):
        """Remove all references and import all from selected shot."""
        result = cmds.confirmDialog(
            title="Remove All References",
            message="This will remove all references from the current scene. Continue?",
            button=["Yes", "No"],
            defaultButton="No",
            cancelButton="No",
            dismissString="No"
        )

        if result == "Yes":
            # Remove all references
            refs = cmds.ls(type="reference") or []
            for ref in refs:
                if ref != "sharedReferenceNode":
                    try:
                        cmds.file(removeReference=True, referenceNode=ref)
                        self._log("Removed reference: {}".format(ref))
                    except Exception as e:
                        self._log("[ERROR] Failed to remove reference {}: {}".format(ref, str(e)))

            self._create_scene_groups()
            self._log("[SETUP] Removed all references and created asset groups")

    def _create_scene_groups(self):
        """Create predefined asset groups."""
        groups = ["Camera_Grp", "Character_Grp", "Setdress_Grp", "Props_Grp", "Sets_Grp", "Dressing_Grp"]

        for grp_name in groups:
            if not cmds.objExists(grp_name):
                grp = cmds.group(empty=True, name=grp_name)
                self._log("Created group: {}".format(grp))

    def _check_scene_state(self):
        """Check current scene state for groups and references matching current shot."""
        # Check standard groups
        standard_groups = ["Camera_Grp", "Character_Grp", "Setdress_Grp", "Props_Grp", "Sets_Grp", "Dressing_Grp"]
        existing_groups = []
        missing_groups = []

        for grp in standard_groups:
            if cmds.objExists(grp):
                existing_groups.append(grp)
            else:
                missing_groups.append(grp)

        # Check references matching current shot assets
        matching_references = self._get_current_shot_references()

        has_content = len(existing_groups) > 0 or len(matching_references) > 0

        return {
            "has_content": has_content,
            "existing_groups": existing_groups,
            "missing_groups": missing_groups,
            "matching_references": matching_references
        }

    def _get_current_shot_references(self):
        """Get references that match current shot assets."""
        if not self.assets_data:
            return []

        matching_refs = []
        all_refs = cmds.ls(type="reference") or []

        # Get expected namespaces from current shot assets
        expected_namespaces = set()
        for asset in self.assets_data:
            expected_namespaces.add(asset['namespace'])
            # Also add shader and groom namespaces
            expected_namespaces.add(asset['namespace'] + "_shade")
            if asset['category'] == 'CHAR':
                expected_namespaces.add(asset['namespace'] + "_groom")

        for ref in all_refs:
            if ref == "sharedReferenceNode":
                continue
            try:
                # Get namespace associated with this reference
                ref_namespace = cmds.referenceQuery(ref, namespace=True)
                if ref_namespace and ref_namespace.lstrip(':') in expected_namespaces:
                    matching_refs.append(ref)
            except Exception:
                continue

        return matching_refs

    def _ask_scene_choice(self, has_content=False, context="setup"):
        """Ask user whether to work in current scene or new scene."""
        if has_content:
            if context == "setup":
                message = "Scene has existing groups/references.\n\nCreate/update groups in current scene or new scene?"
            else:  # build context
                message = "Scene has existing groups/references.\n\nBuild shot in current scene or new scene?\n\nNote: If building in current scene with existing references,\nconsider using 'Replace References' mode."
        else:
            if context == "setup":
                message = "Scene appears empty.\n\nCreate groups in current scene or new scene?"
            else:  # build context
                message = "Build shot in current scene or new scene?"

        try:
            from PySide2 import QtWidgets
        except ImportError:
            from PySide6 import QtWidgets

        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle("Scene Choice")
        msg.setText(message)

        current_btn = msg.addButton("Current Scene", QtWidgets.QMessageBox.AcceptRole)
        new_btn = msg.addButton("New Scene", QtWidgets.QMessageBox.AcceptRole)
        cancel_btn = msg.addButton("Cancel", QtWidgets.QMessageBox.RejectRole)

        msg.setDefaultButton(current_btn)
        msg.exec_()

        clicked = msg.clickedButton()
        if clicked == current_btn:
            return "current"
        elif clicked == new_btn:
            return "new"
        else:
            return "cancel"

    def _auto_detect_shot_context(self):
        """Auto-detect shot context from current Maya scene file name and set dropdowns."""
        try:
            # Get current scene file path
            current_scene = cmds.file(query=True, sceneName=True)
            if not current_scene:
                self._log("[AUTO-DETECT] No current scene file to analyze")
                return

            self._log("[AUTO-DETECT] Analyzing scene: {}".format(os.path.basename(current_scene)))

            # Parse scene context using existing functions
            context = self._parse_scene_context(current_scene)
            if not context:
                self._log("[AUTO-DETECT] Could not parse shot context from scene name")
                return

            # Set dropdowns based on detected context
            self._set_dropdowns_from_context(context)

        except Exception as e:
            self._log("[AUTO-DETECT] Failed to auto-detect context: {}".format(str(e)))

    def _parse_scene_context(self, scene_path):
        """Parse shot context from scene file path using multiple methods."""
        if not scene_path:
            return None

        # Method 1: Parse from file path structure (V:/SWA/all/scene/Ep01/sq0010/SH0020/...)
        path_context = self._parse_context_from_path(scene_path)
        if path_context:
            return path_context

        # Method 2: Parse from filename (Ep01_sq0010_SH0020_lighting_v001.ma)
        filename_context = self._parse_context_from_filename(scene_path)
        if filename_context:
            return filename_context

        return None

    def _parse_context_from_path(self, scene_path):
        """Parse context from file path structure."""
        try:
            # Normalize path separators
            normalized_path = scene_path.replace('\\', '/')
            parts = normalized_path.split('/')

            # Look for scene directory structure: .../scene/Ep01/sq0010/SH0020/...
            scene_index = -1
            for i, part in enumerate(parts):
                if part.lower() == 'scene':
                    scene_index = i
                    break

            if scene_index >= 0 and len(parts) > scene_index + 3:
                # Extract project (directory before 'all')
                project = None
                for i in range(scene_index - 1, -1, -1):
                    if parts[i] == 'all' and i > 0:
                        project = parts[i - 1]
                        break

                episode = parts[scene_index + 1]  # Ep01
                sequence = parts[scene_index + 2]  # sq0010
                shot = parts[scene_index + 3]      # SH0020

                # Validate format
                if (episode.startswith('Ep') and
                    sequence.startswith('sq') and
                    shot.startswith('SH')):
                    return {
                        'project': project,
                        'episode': episode,
                        'sequence': sequence,
                        'shot': shot,
                        'source': 'path'
                    }
        except Exception:
            pass
        return None

    def _parse_context_from_filename(self, scene_path):
        """Parse context from filename using regex patterns."""
        try:
            import re
            filename = os.path.basename(scene_path)

            # Pattern: Ep01_sq0010_SH0020_lighting_v001.ma
            pattern = r'(?:^|_)(Ep\d+).*?[_-](sq\d+).*?[_-](SH\d+)'
            match = re.search(pattern, filename, re.IGNORECASE)

            if match:
                episode = match.group(1)
                sequence = match.group(2)
                shot = match.group(3)

                # Try to extract project from path
                project = None
                path_parts = scene_path.replace('\\', '/').split('/')
                for i, part in enumerate(path_parts):
                    if part.lower() == 'all' and i > 0:
                        project = path_parts[i - 1]
                        break

                return {
                    'project': project,
                    'episode': episode,
                    'sequence': sequence,
                    'shot': shot,
                    'source': 'filename'
                }
        except Exception:
            pass
        return None

    def _set_dropdowns_from_context(self, context):
        """Set dropdown selections based on detected context."""
        try:
            project = context.get('project')
            episode = context.get('episode')
            sequence = context.get('sequence')
            shot = context.get('shot')
            source = context.get('source', 'unknown')

            self._log("[AUTO-DETECT] Detected context from {}: Project={}, Episode={}, Sequence={}, Shot={}".format(
                source, project or 'None', episode or 'None', sequence or 'None', shot or 'None'))

            # Set project if detected and exists in dropdown
            if project:
                project_index = self.project_combo.findText(project)
                if project_index >= 0:
                    self.project_combo.setCurrentIndex(project_index)
                    self._log("[AUTO-DETECT] Set project: {}".format(project))

                    # Trigger project change to populate episodes
                    self._on_project_changed()
                else:
                    self._log("[AUTO-DETECT] Project '{}' not found in dropdown".format(project))

            # Set episode if detected and exists in dropdown
            if episode:
                episode_index = self.episode_combo.findText(episode)
                if episode_index >= 0:
                    self.episode_combo.setCurrentIndex(episode_index)
                    self._log("[AUTO-DETECT] Set episode: {}".format(episode))

                    # Trigger episode change to populate sequences
                    self._on_episode_changed()
                else:
                    self._log("[AUTO-DETECT] Episode '{}' not found in dropdown".format(episode))

            # Set sequence if detected and exists in dropdown
            if sequence:
                sequence_index = self.sequence_combo.findText(sequence)
                if sequence_index >= 0:
                    self.sequence_combo.setCurrentIndex(sequence_index)
                    self._log("[AUTO-DETECT] Set sequence: {}".format(sequence))

                    # Trigger sequence change to populate shots
                    self._on_sequence_changed()
                else:
                    self._log("[AUTO-DETECT] Sequence '{}' not found in dropdown".format(sequence))

            # Set shot if detected and exists in dropdown
            if shot:
                shot_index = self.shot_combo.findText(shot)
                if shot_index >= 0:
                    self.shot_combo.setCurrentIndex(shot_index)
                    self._log("[AUTO-DETECT] Set shot: {}".format(shot))

                    # Trigger shot change to populate versions
                    self._on_shot_changed()
                else:
                    self._log("[AUTO-DETECT] Shot '{}' not found in dropdown".format(shot))

            if project or episode or sequence or shot:
                self._log("[AUTO-DETECT] Context detection complete - dropdowns updated")
            else:
                self._log("[AUTO-DETECT] No valid context detected from scene")

        except Exception as e:
            self._log("[AUTO-DETECT] Failed to set dropdowns: {}".format(str(e)))

    def _build_sets(self):
        """Build Sets assets first - Step 1."""
        if not self.assets_data:
            self._log("[ERROR] No assets loaded. Please load cache list first.")
            return

        sets_assets = [asset for asset in self.assets_data if asset['category'] == 'SETS']
        if not sets_assets:
            self._log("[INFO] No SETS assets found in cache list.")
            return

        # Check if instance optimization is enabled
        use_instances = self.use_sets_instances_checkbox.isChecked()

        if use_instances:
            self._log("[BUILD SETS] Starting Sets build with INSTANCE OPTIMIZATION...")
            self._build_sets_with_instances(sets_assets)
        else:
            self._log("[BUILD SETS] Starting Sets build (traditional references)...")
            self._build_sets_traditional(sets_assets)

        self._log("[BUILD SETS] Completed Sets build process")

    def _build_sets_with_instances(self, sets_assets):
        """Build Sets using instance optimization (1 reference + instances for duplicates)."""
        try:
            # Import the instance builder module
            from . import sets_instance_builder
        except ImportError:
            try:
                import sets_instance_builder
            except ImportError:
                self._log("[ERROR] Could not import sets_instance_builder module")
                self._log("[FALLBACK] Using traditional reference method...")
                self._build_sets_traditional(sets_assets)
                return

        root = self.root_path_edit.text().strip()
        project = self.project_combo.currentText()

        builder = sets_instance_builder.SetsInstanceBuilder(
            root, project, log_callback=self._log
        )

        for asset in sets_assets:
            try:
                cache_file = asset['full_path']
                self._log("\n[INSTANCE BUILD] Processing: {}".format(asset['filename']))

                stats = builder.build_sets_with_instances(cache_file)

                if stats.get("errors"):
                    for error in stats["errors"]:
                        self._log("[ERROR] {}".format(error))
                else:
                    self._log("[OK] Built {} with {} masters + {} instances (saved {} references)".format(
                        asset['filename'],
                        stats.get("masters_created", 0),
                        stats.get("instances_created", 0),
                        stats.get("instances_created", 0)
                    ))

            except Exception as e:
                self._log("[ERROR] Failed to build SETS asset with instances {}: {}".format(
                    asset['filename'], str(e)))

    def _build_sets_traditional(self, sets_assets):
        """Build Sets using traditional method (reference per locator)."""
        for asset in sets_assets:
            try:
                # Import alembic cache
                namespace = asset['namespace']
                cache_file = asset['full_path']

                self._log("Importing SETS cache: {}".format(asset['filename']))

                # Create namespace for the set BEFORE import
                if not cmds.namespace(exists=namespace):
                    cmds.namespace(add=namespace)
                    self._log("Created namespace: {}".format(namespace))

                # Store current namespace
                current_ns = cmds.namespaceInfo(currentNamespace=True)

                try:
                    # Set current namespace so import goes into it automatically
                    cmds.namespace(setNamespace=namespace)
                    self._log("Set current namespace to: {}".format(namespace))

                    # Import the alembic file (will go into current namespace)
                    cmds.AbcImport(cache_file, mode="import", fitTimeRange=False)
                    self._log("Imported alembic into namespace: {}".format(namespace))

                finally:
                    # Always restore original namespace
                    cmds.namespace(setNamespace=current_ns)
                    self._log("Restored namespace to: {}".format(current_ns))

                # Find locators in the namespace (should all be there now)
                all_locators = cmds.ls("{}:*_Loc".format(namespace), type="transform") or []
                self._log("Found {} locators in namespace: {}".format(len(all_locators), all_locators))

                # If no locators found in namespace, try fallback search
                if not all_locators:
                    self._log("[WARNING] No locators found in namespace, trying fallback search...")
                    all_locator_shapes = cmds.ls(type="locator") or []
                    fallback_locators = []

                    for loc_shape in all_locator_shapes:
                        loc_transforms = cmds.listRelatives(loc_shape, parent=True, fullPath=True) or []
                        for loc_transform in loc_transforms:
                            if loc_transform.endswith("_Loc"):
                                fallback_locators.append(loc_transform)

                    all_locators = fallback_locators
                    self._log("Found {} locators in fallback search: {}".format(len(all_locators), all_locators))

                # Process each locator
                for loc in all_locators:
                    self._process_sets_locator(loc, namespace)

                # Move to Sets group
                sets_group = self._get_group_for_category("SETS")
                if sets_group and cmds.objExists(sets_group):
                    # Find main group in namespace
                    main_grps = cmds.ls("{}:*Main_Grp".format(namespace), type="transform") or []
                    if main_grps:
                        try:
                            cmds.parent(main_grps[0], sets_group)
                            self._log("Moved {} to {}".format(main_grps[0], sets_group))
                        except Exception as e:
                            self._log("[WARNING] Could not parent to Sets group: {}".format(str(e)))

            except Exception as e:
                self._log("[ERROR] Failed to build SETS asset {}: {}".format(asset['filename'], str(e)))

    def _process_sets_locator(self, locator, set_namespace):
        """Process individual Sets locator for asset placement."""
        try:
            # Extract component name from locator
            # Format: SETS_KitBedRoomInt_001:KBDIntCelling_001_Loc
            loc_short = _short(locator)  # KBDIntCelling_001_Loc
            if not loc_short.endswith("_Loc"):
                self._log("[WARNING] Locator doesn't end with _Loc: {}".format(locator))
                return

            # Extract component name: KBDIntCelling_001_Loc -> KBDIntCelling
            component_parts = loc_short.replace("_Loc", "").split("_")
            if len(component_parts) < 2:
                self._log("[WARNING] Invalid locator name format: {}".format(locator))
                return

            component_name = "_".join(component_parts[:-1])  # KBDIntCelling (remove _001)
            component_id = component_parts[-1]  # 001

            self._log("Processing locator: {} -> component: {}, id: {}".format(locator, component_name, component_id))
            self._log_verbose("  Locator full path: {}".format(locator))
            self._log_verbose("  Component name extracted: {}".format(component_name))
            self._log_verbose("  Component ID extracted: {}".format(component_id))

            # Build paths for geometry and shader - comprehensive search approach
            root = self.root_path_edit.text().strip()
            project = self.project_combo.currentText()

            # Search locations in priority order:
            # 1. Setdress/interior, 2. Setdress/exterior, 3. Props/object
            search_locations = [
                ("Setdress", "interior"),
                ("Setdress", "exterior"),
                ("Props", "object")
            ]

            self._log_verbose("  Searching for component '{}' in asset directories...".format(component_name))

            geo_file = None
            shader_file = None
            asset_category = None
            asset_subdir = None

            # Search all possible locations
            for category, subdir in search_locations:
                base_path = os.path.join(root, project, "all", "asset", category, subdir, component_name, "hero")
                test_geo_file = os.path.join(base_path, "{}_geo.abc".format(component_name))
                test_shader_file = os.path.join(base_path, "{}_rsshade.ma".format(component_name))

                self._log_verbose("    Checking {}/{}: {}".format(category, subdir, base_path))
                self._log_verbose("      Geometry: {}".format(test_geo_file))
                self._log_verbose("      Shader: {}".format(test_shader_file))

                if os.path.exists(test_geo_file):
                    geo_file = test_geo_file
                    shader_file = test_shader_file
                    asset_category = category
                    asset_subdir = subdir
                    self._log("Found asset in {}/{} directory: {}".format(category, subdir, component_name))
                    self._log_verbose("      [OK] Found geometry file: {}".format(test_geo_file))
                    self._log_verbose("      [OK] Shader file exists: {}".format(os.path.exists(test_shader_file)))
                    break
                else:
                    self._log_verbose("      [FAIL] Geometry file not found")

            # Check if asset was found
            if not geo_file:
                self._log("[ERROR] Asset not found in any directory: {}".format(component_name))
                for category, subdir in search_locations:
                    test_path = os.path.join(root, project, "all", "asset", category, subdir, component_name, "hero", "{}_geo.abc".format(component_name))
                    self._log("Checked {}/{}: {}".format(category, subdir, test_path))
                return

            self._log("Using {}/{} asset: {}".format(asset_category, asset_subdir, component_name))
            self._log_verbose("  Geometry file: {}".format(geo_file))
            self._log_verbose("  Shader file: {}".format(shader_file))

            # Create nested namespace for this component
            component_namespace = "{}_{}".format(component_name, component_id)  # KBDIntCelling_001
            full_component_ns = "{}:{}".format(set_namespace, component_namespace)  # SETS_KitBedRoomInt_001:KBDIntCelling_001

            self._log_verbose("  Creating component namespace: {}".format(component_namespace))
            self._log_verbose("  Full component namespace: {}".format(full_component_ns))

            # Reference geometry if exists
            if os.path.exists(geo_file):
                try:
                    self._log_verbose("  Referencing geometry file...")
                    cmds.file(geo_file, reference=True, namespace=full_component_ns)
                    self._log("Referenced geometry: {} -> {}".format(geo_file, full_component_ns))

                    # Find top-level transform in the referenced geometry
                    ref_nodes = cmds.ls("{}:*".format(full_component_ns), type="transform") or []
                    top_level_nodes = []

                    for node in ref_nodes:
                        # Check if this node has no parent (except world)
                        parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
                        if not parents or parents[0] == "|":
                            top_level_nodes.append(node)

                    # Parent top-level nodes to locator (move object, not preserve position)
                    for top_node in top_level_nodes:
                        try:
                            self._log_verbose("    Parenting {} to locator {}".format(top_node, locator))
                            cmds.parent(top_node, locator)
                            self._log("Parented {} to locator {}".format(top_node, locator))

                            # Reset top-level transform to origin (TR=0, Scale=1)
                            cmds.xform(top_node, translation=[0, 0, 0], rotation=[0, 0, 0])
                            cmds.xform(top_node, scale=[1, 1, 1])
                            self._log("Reset {} transform to origin".format(top_node))

                        except Exception as e:
                            self._log("[WARNING] Could not parent/reset {}: {}".format(top_node, str(e)))

                except Exception as e:
                    self._log("[ERROR] Failed to reference geometry {}: {}".format(geo_file, str(e)))
            else:
                self._log("[WARNING] Geometry file not found: {}".format(geo_file))

            # Reference shader if exists
            if os.path.exists(shader_file):
                try:
                    shader_ns = "{}_shade".format(full_component_ns)  # SETS_KitBedRoomInt_001:KBDIntCelling_001_shade
                    self._log_verbose("  Referencing shader file...")
                    self._log_verbose("  Shader namespace: {}".format(shader_ns))
                    cmds.file(shader_file, reference=True, namespace=shader_ns)
                    self._log("Referenced shader: {} -> {}".format(shader_file, shader_ns))

                    # Assign shaders to geometry
                    self._assign_component_shaders(full_component_ns, shader_ns)

                except Exception as e:
                    self._log("[ERROR] Failed to reference shader {}: {}".format(shader_file, str(e)))
            else:
                self._log("[WARNING] Shader file not found: {}".format(shader_file))

        except Exception as e:
            self._log("[ERROR] Failed to process locator {}: {}".format(locator, str(e)))

    def _process_sets_locator_with_conflict_check(self, locator, set_namespace):
        """Process Sets locator with conflict checking and user choice for existing references."""
        try:
            # Extract component name from locator
            loc_short = _short(locator)  # KBDIntCelling_001_Loc
            if not loc_short.endswith("_Loc"):
                self._log("[WARNING] Locator doesn't end with _Loc: {}".format(locator))
                return

            # Extract component name: KBDIntCelling_001_Loc -> KBDIntCelling
            component_parts = loc_short.replace("_Loc", "").split("_")
            if len(component_parts) < 2:
                self._log("[WARNING] Invalid locator name format: {}".format(locator))
                return

            component_name = "_".join(component_parts[:-1])  # KBDIntCelling (remove _001)
            component_id = component_parts[-1]  # 001

            self._log("Processing locator with conflict check: {} -> component: {}, id: {}".format(locator, component_name, component_id))

            # Build paths for geometry and shader - comprehensive search approach
            root = self.root_path_edit.text().strip()
            project = self.project_combo.currentText()

            # Search locations in priority order:
            # 1. Setdress/interior, 2. Setdress/exterior, 3. Props/object
            search_locations = [
                ("Setdress", "interior"),
                ("Setdress", "exterior"),
                ("Props", "object")
            ]

            geo_file = None
            shader_file = None
            asset_category = None
            asset_subdir = None

            # Search all possible locations
            for category, subdir in search_locations:
                base_path = os.path.join(root, project, "all", "asset", category, subdir, component_name, "hero")
                test_geo_file = os.path.join(base_path, "{}_geo.abc".format(component_name))
                test_shader_file = os.path.join(base_path, "{}_rsshade.ma".format(component_name))

                if os.path.exists(test_geo_file):
                    geo_file = test_geo_file
                    shader_file = test_shader_file
                    asset_category = category
                    asset_subdir = subdir
                    self._log("Found asset in {}/{} directory: {}".format(category, subdir, component_name))
                    break

            # Check if asset was found
            if not geo_file:
                self._log("[ERROR] Asset not found in any directory: {}".format(component_name))
                return

            self._log("Using {}/{} asset: {}".format(asset_category, asset_subdir, component_name))

            # Create nested namespace for this component
            component_namespace = "{}_{}".format(component_name, component_id)  # KBDIntCelling_001
            full_component_ns = "{}:{}".format(set_namespace, component_namespace)  # SETS_KitBedRoomInt_001:KBDIntCelling_001

            # Check if this component namespace already exists (conflict check)
            if cmds.namespace(exists=full_component_ns):
                self._log("[CONFLICT] Component namespace already exists: {}".format(full_component_ns))

                # Ask user what to do
                choice = self._ask_reference_conflict_choice(component_name, component_id)

                if choice == "skip":
                    self._log("[SKIP] User chose to skip existing reference: {}".format(full_component_ns))
                    return
                elif choice == "next":
                    # Find next available identifier
                    next_id = self._find_next_available_identifier(set_namespace, component_name, component_id)
                    if next_id:
                        component_id = next_id
                        component_namespace = "{}_{}".format(component_name, component_id)
                        full_component_ns = "{}:{}".format(set_namespace, component_namespace)
                        self._log("[NEXT] Using next available identifier: {}".format(full_component_ns))
                    else:
                        self._log("[ERROR] Could not find next available identifier for {}".format(component_name))
                        return
                else:
                    self._log("[CANCEL] User cancelled reference creation")
                    return

            # Import geometry and shader (same as original function)
            self._import_component_geometry_and_shader(locator, full_component_ns, geo_file, shader_file)

        except Exception as e:
            self._log("[ERROR] Failed to process locator with conflict check {}: {}".format(locator, str(e)))

    def _ask_reference_conflict_choice(self, component_name, component_id):
        """Ask user what to do when reference already exists."""
        try:
            from PySide2 import QtWidgets
        except ImportError:
            from PySide6 import QtWidgets

        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle("Reference Conflict")
        msg.setText("Reference already exists for component: {}_{}".format(component_name, component_id))
        msg.setInformativeText("What would you like to do?")

        skip_btn = msg.addButton("Skip (Keep Existing)", QtWidgets.QMessageBox.ActionRole)
        next_btn = msg.addButton("Use Next ID", QtWidgets.QMessageBox.ActionRole)
        cancel_btn = msg.addButton("Cancel", QtWidgets.QMessageBox.RejectRole)

        msg.setDefaultButton(skip_btn)
        msg.exec_()

        if msg.clickedButton() == skip_btn:
            return "skip"
        elif msg.clickedButton() == next_btn:
            return "next"
        else:
            return "cancel"

    def _find_next_available_identifier(self, set_namespace, component_name, current_id):
        """Find next available identifier for component."""
        try:
            # Convert current ID to integer and start from next
            current_num = int(current_id)
            next_num = current_num + 1

            # Check up to 999 for available identifier
            for i in range(next_num, 1000):
                test_id = str(i).zfill(3)  # 002, 003, etc.
                test_namespace = "{}:{}_{}".format(set_namespace, component_name, test_id)

                if not cmds.namespace(exists=test_namespace):
                    return test_id

            return None  # No available identifier found

        except Exception as e:
            self._log("[ERROR] Failed to find next identifier: {}".format(str(e)))
            return None

    def _import_component_geometry_and_shader(self, locator, full_component_ns, geo_file, shader_file):
        """Reference geometry and shader for component (using standard workflow)."""
        try:
            # Reference geometry if exists
            if os.path.exists(geo_file):
                try:
                    cmds.file(geo_file, reference=True, namespace=full_component_ns)
                    self._log("Referenced geometry: {} -> {}".format(geo_file, full_component_ns))

                    # Find top-level transform in the referenced geometry
                    ref_nodes = cmds.ls("{}:*".format(full_component_ns), type="transform") or []
                    top_level_nodes = []

                    for node in ref_nodes:
                        # Check if this node has no parent (except world)
                        parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
                        if not parents or parents[0] == "|":
                            top_level_nodes.append(node)

                    # Parent top-level nodes to locator (move object, not preserve position)
                    for top_node in top_level_nodes:
                        try:
                            cmds.parent(top_node, locator)
                            self._log("Parented {} to locator {}".format(top_node, locator))

                            # Reset top-level transform to origin (TR=0, Scale=1)
                            cmds.xform(top_node, translation=[0, 0, 0], rotation=[0, 0, 0])
                            cmds.xform(top_node, scale=[1, 1, 1])
                            self._log("Reset {} transform to origin".format(top_node))

                        except Exception as e:
                            self._log("[WARNING] Could not parent/reset {}: {}".format(top_node, str(e)))

                except Exception as e:
                    self._log("[ERROR] Failed to reference geometry {}: {}".format(geo_file, str(e)))
            else:
                self._log("[WARNING] Geometry file not found: {}".format(geo_file))

            # Reference shader if exists
            if os.path.exists(shader_file):
                try:
                    shader_ns = "{}_shade".format(full_component_ns)  # SETS_KitBedRoomInt_001:KBDIntCelling_001_shade
                    cmds.file(shader_file, reference=True, namespace=shader_ns)
                    self._log("Referenced shader: {} -> {}".format(shader_file, shader_ns))

                    # Assign shaders to geometry
                    self._assign_component_shaders(full_component_ns, shader_ns)

                except Exception as e:
                    self._log("[ERROR] Failed to reference shader {}: {}".format(shader_file, str(e)))
            else:
                self._log("[WARNING] Shader file not found: {}".format(shader_file))

        except Exception as e:
            self._log("[ERROR] Failed to reference component geometry and shader: {}".format(str(e)))

    def _assign_component_shaders(self, geo_ns, shader_ns):
        """Assign shaders to geometry for a Sets component and bind to rsMeshParameters."""
        try:
            self._log("Assigning shaders from {} to geometry in {}".format(shader_ns, geo_ns))

            # Find shading groups in shader namespace
            shader_sgs = cmds.ls("{}:*".format(shader_ns), type="shadingEngine") or []

            if not shader_sgs:
                self._log("[WARNING] No shading groups found in shader namespace: {}".format(shader_ns))
                return

            # Find geometry shapes and transforms in geo namespace
            geo_shapes = []
            geo_transforms = cmds.ls("{}:*".format(geo_ns), type="transform") or []
            top_level_transforms = []

            for xform in geo_transforms:
                # Check if this is a top-level transform (no parent except world or locator)
                parents = cmds.listRelatives(xform, parent=True, fullPath=True) or []
                if not parents or parents[0] == "|" or "Loc" in parents[0]:
                    top_level_transforms.append(xform)

                # Collect mesh shapes
                shapes = cmds.listRelatives(xform, shapes=True, fullPath=True) or []
                for shape in shapes:
                    if cmds.nodeType(shape) == "mesh":
                        geo_shapes.append(shape)

            if not geo_shapes:
                self._log("[WARNING] No mesh shapes found in geometry namespace: {}".format(geo_ns))
                return

            # Use proper shader assignment with stored mapping data (like Assign Shader by Namespace tab)
            total_assigned = 0

            # Scan for shading groups with stored mapping data
            shader_assignments = self._scan_shader_assignments(shader_ns)
            if not shader_assignments:
                self._log("[WARNING] No shading groups with 'snow__assign_shade' mapping found in {}".format(shader_ns))
                return

            # Plan assignments using stored mapping data
            assignment_plan = self._plan_shader_assignments(geo_ns, shader_assignments)

            # Execute assignments based on the plan
            for entry in assignment_plan:
                sg = entry["sg"]
                targets = entry.get("resolved", [])

                if not targets:
                    self._log("[SKIP] {} - no resolved targets".format(sg))
                    continue

                try:
                    assigned, failed = _assign_shapes_to_sg(targets, sg)
                    if assigned > 0:
                        total_assigned += assigned
                        self._log("Assigned {} specific shapes to {}".format(assigned, sg))
                    if failed:
                        self._log("[WARNING] Failed to assign {} shapes to {}".format(len(failed), sg))
                        for shp, reason in failed[:3]:  # Show first 3 failures
                            self._log("   ! {} ({})".format(shp, reason))
                except Exception as e:
                    self._log("[ERROR] Failed to assign {}: {}".format(sg, str(e)))

            self._log("Component shader assignment complete: {} shapes assigned".format(total_assigned))

            # IMPORTANT: Bind top-level transforms to rsMeshParameters sets
            if top_level_transforms:
                self._bind_to_rs_mesh_parameters(geo_ns, shader_ns, top_level_transforms)

        except Exception as e:
            self._log("[ERROR] Component shader assignment failed: {}".format(str(e)))

    def _build_assets(self):
        """Build other assets (Character, Props, Setdress, Camera) - Step 2."""
        if not self.assets_data:
            self._log("[ERROR] No assets loaded. Please load cache list first.")
            return

        other_assets = [asset for asset in self.assets_data if asset['category'] != 'SETS']
        if not other_assets:
            self._log("[INFO] No non-SETS assets found in cache list.")
            return

        self._log("[BUILD ASSETS] Starting other assets build process...")

        # Group assets by category
        categories = {}
        for asset in other_assets:
            cat = asset['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(asset)

        # Process each category
        for category, assets in categories.items():
            self._log("Processing {} {} assets...".format(len(assets), category))

            for asset in assets:
                try:
                    # Reference alembic cache with namespace
                    namespace = asset['namespace']
                    cache_file = asset['full_path']
                    name = asset['name']
                    identifier = asset['identifier']

                    self._log("Referencing {} cache: {} with namespace: {}".format(category, asset['filename'], namespace))

                    # Reference the alembic file with namespace
                    cmds.file(cache_file, reference=True, namespace=namespace)

                    # Move the reference node to appropriate group
                    group_name = self._get_group_for_category(category)
                    if cmds.objExists(group_name):
                        # Find the reference node for this namespace
                        ref_nodes = cmds.ls(type="reference") or []
                        target_ref = None

                        for ref_node in ref_nodes:
                            if ref_node == "sharedReferenceNode":
                                continue
                            try:
                                # Get the namespace of this reference
                                ref_namespace = cmds.referenceQuery(ref_node, namespace=True)
                                if ref_namespace == ":{}".format(namespace):
                                    target_ref = ref_node
                                    break
                            except Exception:
                                continue

                        if target_ref:
                            # Get the top-level nodes from this reference
                            try:
                                ref_nodes_list = cmds.referenceQuery(target_ref, nodes=True, dagPath=True) or []
                                # Find top-level transforms (no parent outside the reference)
                                top_level_nodes = []
                                for node in ref_nodes_list:
                                    if cmds.nodeType(node) == "transform":
                                        parent = cmds.listRelatives(node, parent=True, fullPath=True)
                                        if not parent or not any(p in ref_nodes_list for p in parent):
                                            top_level_nodes.append(node)

                                # Parent top-level nodes to the group
                                for top_node in top_level_nodes:
                                    try:
                                        cmds.parent(top_node, group_name)
                                        self._log("Moved {} to {}".format(top_node, group_name))
                                    except Exception as e:
                                        self._log("[WARNING] Failed to move {} to {}: {}".format(top_node, group_name, str(e)))

                            except Exception as e:
                                self._log("[WARNING] Failed to query reference nodes for {}: {}".format(namespace, str(e)))
                        else:
                            self._log("[WARNING] Could not find reference node for namespace: {}".format(namespace))

                    # Reference shader and groom files for this asset
                    self._reference_shader_and_groom(category, name, identifier)

                    # Update status in table
                    self._update_asset_status(asset['filename'], "Referenced")

                except Exception as e:
                    self._log("[ERROR] Failed to build {} asset {}: {}".format(category, asset['filename'], str(e)))
                    self._update_asset_status(asset['filename'], "Failed")

        self._log("[BUILD ASSETS] Completed other assets build process")

        # Automatically run Steps 3 and 4 after building assets
        self._log("[AUTO] Starting automatic Shader Assignment, Place3D Linker, and BlendShape creation...")
        self._assign_shaders()  # This already includes Place3D and BlendShape
        self._log("[AUTO] Completed all asset processing steps (Steps 2+3+4)")

    def _update_assets(self):
        """Update assets from new shot version - only update geometry from */publish/{version} paths."""
        self._log("[UPDATE] UPDATE ASSETS button clicked!")

        # Check if Maya is available
        try:
            import maya.cmds as cmds
            self._log("[DEBUG] Maya cmds available for update")
        except ImportError:
            self._log("[ERROR] Maya cmds not available - cannot update assets")
            self._log("[INFO] This function requires Maya to be running")
            return

        if not self.assets_data:
            self._log("[ERROR] No assets loaded. Please load cache list first.")
            return

        self._log("[UPDATE ASSETS] Starting asset update process...")
        self._log("[DEBUG] Found {} total assets to process".format(len(self.assets_data)))

        # Separate Sets and other assets
        sets_assets = [asset for asset in self.assets_data if asset['category'] == 'SETS']
        other_assets = [asset for asset in self.assets_data if asset['category'] != 'SETS']

        self._log("[DEBUG] Sets assets: {}, Other assets: {}".format(len(sets_assets), len(other_assets)))

        # Update Sets assets first (complex merge process)
        if sets_assets:
            self._log("[UPDATE SETS] Updating {} Sets assets...".format(len(sets_assets)))
            for i, asset in enumerate(sets_assets, 1):
                self._log("[UPDATE SETS] Processing asset {}/{}: {}".format(i, len(sets_assets), asset['filename']))
                try:
                    self._update_single_sets_asset(asset)
                    self._update_asset_status(asset['filename'], "Updated")
                except Exception as e:
                    self._log("[ERROR] Failed to update Sets asset {}: {}".format(asset['filename'], str(e)))
                    self._update_asset_status(asset['filename'], "Update Failed")

        # Update other assets (simple reference replacement)
        if other_assets:
            self._log("[UPDATE OTHER] Updating {} other assets...".format(len(other_assets)))
            for i, asset in enumerate(other_assets, 1):
                self._log("[UPDATE OTHER] Processing asset {}/{}: {}".format(i, len(other_assets), asset['filename']))
                try:
                    self._update_single_other_asset(asset)
                    self._update_asset_status(asset['filename'], "Updated")
                except Exception as e:
                    self._log("[ERROR] Failed to update other asset {}: {}".format(asset['filename'], str(e)))
                    self._update_asset_status(asset['filename'], "Update Failed")

        self._log("[UPDATE ASSETS] Completed asset update process")

    def _update_single_sets_asset(self, asset):
        """Update a single Sets asset - UPDATE existing SETS, don't create new ones."""
        try:
            # Check if Maya is available
            try:
                import maya.cmds as cmds
                self._log("[DEBUG] Maya cmds imported successfully")
            except ImportError:
                self._log("[ERROR] Maya cmds not available - cannot update Sets asset")
                return

            namespace = asset['namespace']
            cache_file = asset['full_path']

            self._log("[UPDATE SETS] Updating individual SETS asset: {}".format(asset['filename']))

            # Step 1: Check if SETS namespace exists in scene
            if not cmds.namespace(exists=namespace):
                self._log("[ERROR] SETS namespace {} not found in scene - cannot update non-existing asset".format(namespace))
                self._log("[INFO] Use BUILD button to create new SETS asset")
                return

            # Step 2: Check if SETS asset exists under Sets_Grp
            sets_grp = "Sets_Grp"
            sets_main_grp = None

            if cmds.objExists(sets_grp):
                children = cmds.listRelatives(sets_grp, children=True, fullPath=True) or []
                for child in children:
                    if child.endswith(":Main_Grp") and namespace in child:
                        sets_main_grp = child
                        break

            if not sets_main_grp:
                self._log("[ERROR] SETS Main_Grp not found under Sets_Grp - cannot update non-existing asset")
                self._log("[INFO] Use BUILD button to create new SETS asset")
                return

            self._log("[UPDATE] Found existing SETS Main_Grp: {}".format(sets_main_grp))

            # Step 3: Select the top-level SETS Main_Grp for proper merge
            try:
                cmds.select(sets_main_grp, replace=True)
                self._log("Selected SETS Main_Grp for merge: {}".format(sets_main_grp.split(":")[-1]))
            except Exception as e:
                self._log("[WARNING] Could not select Main_Grp: {}".format(str(e)))
                cmds.select(clear=True)

            # Step 4: Update existing SETS using MERGE MODE (correct Maya alembic workflow)
            self._log("Updating SETS using alembic MERGE mode...")

            # Store current namespace and set to target namespace
            current_ns = cmds.namespaceInfo(currentNamespace=True)

            try:
                # Set current namespace for merge
                cmds.namespace(setNamespace=namespace)

                # Use MERGE MODE with CONNECT parameter to update existing alembic geometry
                # Connect to the existing Main_Grp to merge properly
                main_grp_short = "{}:Main_Grp".format(namespace)

                # Use MERGE MODE with connect parameter - this is the correct Maya workflow
                cmds.AbcImport(cache_file, mode="merge", connect=main_grp_short, fitTimeRange=False)
                self._log("[OK] Updated SETS locators using MERGE mode connected to: {}".format(main_grp_short))

            except Exception as e:
                self._log("[ERROR] Failed to merge alembic: {}".format(str(e)))
                self._log("[ERROR] MERGE mode failed - UPDATE cannot proceed without creating duplicates")
                self._log("[INFO] This may happen if:")
                self._log("[INFO] 1. SETS was not properly built with alembic import")
                self._log("[INFO] 2. Alembic file structure doesn't match existing geometry")
                self._log("[INFO] 3. Namespace or geometry structure is corrupted")
                self._log("[INFO] Try using BUILD button to rebuild the SETS asset")
                return

            finally:
                # Always restore original namespace
                cmds.namespace(setNamespace=current_ns)

            # Step 6: Check for NEW locators that need component references
            all_locators = cmds.ls("{}:*_Loc".format(namespace), type="transform") or []
            new_locators = []
            existing_locators = []

            self._log("Checking {} locators after SETS update...".format(len(all_locators)))

            for loc in all_locators:
                children = cmds.listRelatives(loc, children=True, fullPath=True) or []
                # Filter out non-geometry children (like constraints, etc.)
                geometry_children = []
                for child in children:
                    if cmds.nodeType(child) == "transform":
                        geometry_children.append(child)

                if not geometry_children:
                    new_locators.append(loc)
                    self._log("Found NEW locator (no component references): {}".format(loc.split(":")[-1]))
                else:
                    existing_locators.append(loc)
                    self._log("Existing locator {} has {} component references - keeping".format(loc.split(":")[-1], len(geometry_children)))

            self._log("Found {} NEW locators and {} existing locators with references".format(len(new_locators), len(existing_locators)))

            # Step 7: Only create references for NEW locators
            if new_locators:
                self._log("Creating component references for {} new locators...".format(len(new_locators)))
                for loc in new_locators:
                    self._log("Processing new locator: {}".format(loc.split(":")[-1]))
                    self._process_sets_locator_with_conflict_check(loc, namespace)
            else:
                self._log("No new locators found - all locators already have component references")

            # Step 8: Existing locators keep their references (positions updated by alembic merge)
            if existing_locators:
                self._log("Existing locators updated positions from SETS alembic merge - references preserved")

            self._log("[OK] Successfully updated SETS asset: {}".format(asset['filename']))

        except Exception as e:
            self._log("[ERROR] ERROR updating Sets asset {}: {}".format(asset['filename'], str(e)))

    def _update_single_drsg_asset(self, asset):
        """Update a single Dressing asset - SAME PROCESS as SETS UPDATE."""
        try:
            # Check if Maya is available
            try:
                import maya.cmds as cmds
                self._log("[DEBUG] Maya cmds imported successfully")
            except ImportError:
                self._log("[ERROR] Maya cmds not available - cannot update Dressing asset")
                return

            namespace = asset['namespace']
            cache_file = asset['full_path']

            self._log("[UPDATE DRSG] Updating individual DRSG asset: {}".format(asset['filename']))

            # Step 1: Check if DRSG namespace exists in scene
            if not cmds.namespace(exists=namespace):
                self._log("[ERROR] DRSG namespace {} not found in scene - cannot update non-existing asset".format(namespace))
                self._log("[INFO] Use BUILD button to create new DRSG asset")
                return

            # Step 2: Check if DRSG asset exists under Dressing_Grp
            drsg_grp = "Dressing_Grp"
            drsg_main_grp = None

            if cmds.objExists(drsg_grp):
                children = cmds.listRelatives(drsg_grp, children=True, fullPath=True) or []
                for child in children:
                    if child.endswith(":Main_Grp") and namespace in child:
                        drsg_main_grp = child
                        break

            if not drsg_main_grp:
                self._log("[ERROR] DRSG Main_Grp not found under Dressing_Grp - cannot update non-existing asset")
                self._log("[INFO] Use BUILD button to create new DRSG asset")
                return

            self._log("[UPDATE] Found existing DRSG Main_Grp: {}".format(drsg_main_grp))

            # Step 3: Select the top-level DRSG Main_Grp for proper merge
            try:
                cmds.select(drsg_main_grp, replace=True)
                self._log("Selected DRSG Main_Grp for merge: {}".format(drsg_main_grp.split(":")[-1]))
            except Exception as e:
                self._log("[WARNING] Could not select Main_Grp: {}".format(str(e)))
                cmds.select(clear=True)

            # Step 4: Update existing DRSG using MERGE MODE (same as SETS)
            self._log("Updating DRSG using alembic MERGE mode...")

            # Store current namespace and set to target namespace
            current_ns = cmds.namespaceInfo(currentNamespace=True)

            try:
                # Set current namespace for merge
                cmds.namespace(setNamespace=namespace)

                # Use MERGE MODE with CONNECT parameter - same as SETS
                main_grp_short = "{}:Main_Grp".format(namespace)

                # Use MERGE MODE with connect parameter
                cmds.AbcImport(cache_file, mode="merge", connect=main_grp_short, fitTimeRange=False)
                self._log("[OK] Updated DRSG locators using MERGE mode connected to: {}".format(main_grp_short))

            except Exception as e:
                self._log("[ERROR] Failed to merge alembic: {}".format(str(e)))
                self._log("[ERROR] MERGE mode failed - UPDATE cannot proceed without creating duplicates")
                self._log("[INFO] This may happen if:")
                self._log("[INFO] 1. DRSG was not properly built with alembic import")
                self._log("[INFO] 2. Alembic file structure doesn't match existing geometry")
                self._log("[INFO] 3. Namespace or geometry structure is corrupted")
                self._log("[INFO] Try using BUILD button to rebuild the DRSG asset")
                return

            finally:
                # Always restore original namespace
                cmds.namespace(setNamespace=current_ns)

            # Step 5: Check for NEW locators that need component references (same as SETS)
            all_locators = cmds.ls("{}:*_Loc".format(namespace), type="transform") or []
            new_locators = []
            existing_locators = []

            self._log("Checking {} locators after DRSG update...".format(len(all_locators)))

            for loc in all_locators:
                children = cmds.listRelatives(loc, children=True, fullPath=True) or []
                # Filter out non-geometry children (like constraints, etc.)
                geometry_children = []
                for child in children:
                    if cmds.nodeType(child) == "transform":
                        geometry_children.append(child)

                if not geometry_children:
                    new_locators.append(loc)
                    self._log("Found NEW locator (no component references): {}".format(loc.split(":")[-1]))
                else:
                    existing_locators.append(loc)
                    self._log("Existing locator {} has {} component references - keeping".format(loc.split(":")[-1], len(geometry_children)))

            self._log("Found {} NEW locators and {} existing locators with references".format(len(new_locators), len(existing_locators)))

            # Step 6: Only create references for NEW locators (reuse SETS method)
            if new_locators:
                self._log("Creating component references for {} new locators...".format(len(new_locators)))
                for loc in new_locators:
                    self._log("Processing new locator: {}".format(loc.split(":")[-1]))
                    self._process_sets_locator_with_conflict_check(loc, namespace)
            else:
                self._log("No new locators found - all locators already have component references")

            # Step 7: Existing locators keep their references (positions updated by alembic merge)
            if existing_locators:
                self._log("Existing locators updated positions from DRSG alembic merge - references preserved")

            self._log("[OK] Successfully updated DRSG asset: {}".format(asset['filename']))

        except Exception as e:
            self._log("[ERROR] ERROR updating Dressing asset {}: {}".format(asset['filename'], str(e)))

    def _check_and_update_locator_references(self, locator, set_namespace):
        """Check if existing locator needs reference updates."""
        try:
            # Extract component info from locator
            loc_short = locator.split(":")[-1]  # Get short name
            if not loc_short.endswith("_Loc"):
                return

            component_parts = loc_short.replace("_Loc", "").split("_")
            if len(component_parts) < 2:
                return

            component_name = "_".join(component_parts[:-1])
            component_id = component_parts[-1]

            # Check if locator has children (referenced geometry)
            children = cmds.listRelatives(locator, children=True, fullPath=True) or []
            if not children:
                # No references, try to reference if files exist
                self._log("Locator {} has no references, attempting to reference...".format(loc_short))
                self._process_sets_locator(locator, set_namespace)
            else:
                self._log("Locator {} already has references, keeping existing".format(loc_short))

        except Exception as e:
            self._log("[ERROR] Failed to check locator references for {}: {}".format(locator, str(e)))

    def _remove_locator_references(self, removed_locator_name, set_namespace):
        """Remove references associated with a deleted locator."""
        try:
            # Extract component info from removed locator name
            loc_short = removed_locator_name.split(":")[-1]
            if not loc_short.endswith("_Loc"):
                return

            component_parts = loc_short.replace("_Loc", "").split("_")
            if len(component_parts) < 2:
                return

            component_name = "_".join(component_parts[:-1])
            component_id = component_parts[-1]

            # Build expected component namespace
            full_component_ns = "{}:{}_{:03d}".format(set_namespace, component_name, int(component_id))

            # Find and remove geometry reference
            geo_refs = cmds.ls(type="reference") or []
            for ref in geo_refs:
                if ref == "sharedReferenceNode":
                    continue
                try:
                    ref_namespace = cmds.referenceQuery(ref, namespace=True)
                    if ref_namespace == ":{}".format(full_component_ns):
                        cmds.file(removeReference=True, referenceNode=ref)
                        self._log("Removed geometry reference: {}".format(ref))
                        break
                except Exception:
                    continue

            # Find and remove shader reference
            shader_ns = "{}_shade".format(full_component_ns)
            for ref in geo_refs:
                if ref == "sharedReferenceNode":
                    continue
                try:
                    ref_namespace = cmds.referenceQuery(ref, namespace=True)
                    if ref_namespace == ":{}".format(shader_ns):
                        cmds.file(removeReference=True, referenceNode=ref)
                        self._log("Removed shader reference: {}".format(ref))
                        break
                except Exception:
                    continue

        except Exception as e:
            self._log("[ERROR] Failed to remove references for {}: {}".format(removed_locator_name, str(e)))

    def _check_and_reference_locator_if_needed(self, locator, set_namespace):
        """Check if locator has children, and only reference if it doesn't have any."""
        try:
            loc_short = locator.split(":")[-1]  # Get short name
            self._log("[DEBUG] Checking locator: {}".format(loc_short))

            # Check if locator has children (referenced geometry)
            children = cmds.listRelatives(locator, children=True, fullPath=True) or []

            if children:
                # Locator already has children (references), skip
                self._log("[SKIP] Locator {} already has {} children, skipping reference".format(
                    loc_short, len(children)))
                return

            # Locator has no children, need to reference
            self._log("[REFERENCE] Locator {} has no children, creating reference...".format(loc_short))
            self._process_sets_locator(locator, set_namespace)

        except Exception as e:
            self._log("[ERROR] Failed to check/reference locator {}: {}".format(locator, str(e)))

    def _update_single_other_asset(self, asset):
        """Update a single non-Sets asset by replacing geometry reference."""
        try:
            # Check if Maya is available
            try:
                import maya.cmds as cmds
                self._log("[DEBUG] Maya cmds imported successfully for other asset")
            except ImportError:
                self._log("[ERROR] Maya cmds not available - cannot update other asset")
                return

            category = asset['category']
            namespace = asset['namespace']
            cache_file = asset['full_path']

            # Check if this is from shot publish directory (pull pipeline)
            # Shot cache format: {ep}_{seq}_{shot}__{category}_{name}_{identifier}.abc
            # Handle both forward and backward slashes for cross-platform compatibility
            normalized_path = cache_file.replace('\\', '/')
            if "/publish/" not in normalized_path:
                self._log("[SKIP] Not from publish directory: {}".format(asset['filename']))
                self._log("[DEBUG] Path checked: {}".format(normalized_path))
                return

            # For shot caches, we accept the format: {ep}_{seq}_{shot}__{category}_{name}_{identifier}.abc
            is_shot_cache = "__" in asset['filename'] and asset['filename'].endswith(".abc")

            if not is_shot_cache:
                self._log("[SKIP] Not a valid shot cache format: {}".format(asset['filename']))
                return

            self._log("[DEBUG] Valid shot cache detected: {}".format(asset['filename']))

            # Note: Cameras DO need updates when switching between shots
            # Only skip cameras if they don't have references in the scene

            self._log("[UPDATE OTHER] Updating {} reference...".format(asset['filename']))

            # Check if namespace exists in scene
            if not cmds.namespace(exists=namespace):
                self._log("[INFO] Namespace {} not found in scene - creating new {} asset".format(namespace, category))
                # Create new asset using existing build function
                self._build_single_other_asset(asset)
                return

            # Find existing reference for this namespace
            existing_ref = None
            refs = cmds.ls(type="reference") or []

            self._log("[DEBUG] Searching for references in namespace: {}".format(namespace))
            self._log("[DEBUG] Found {} total references in scene".format(len(refs)))

            for ref in refs:
                if ref == "sharedReferenceNode":
                    continue
                try:
                    ref_namespace = cmds.referenceQuery(ref, namespace=True)
                    ref_filename = cmds.referenceQuery(ref, filename=True)

                    self._log("[DEBUG] Checking ref: {} | namespace: {} | file: {}".format(
                        ref, ref_namespace, os.path.basename(ref_filename)))

                    # Check if namespace matches (handle both :namespace and namespace formats)
                    namespace_match = (ref_namespace == ":{}".format(namespace) or
                                     ref_namespace == namespace)

                    if namespace_match and ref_filename.endswith(".abc"):
                        existing_ref = ref
                        self._log("[DEBUG] Found matching geometry reference: {}".format(ref))
                        break

                except Exception as e:
                    self._log("[DEBUG] Error checking reference {}: {}".format(ref, str(e)))
                    continue

            if not existing_ref:
                self._log("[WARNING] No existing geometry reference found for namespace: {}".format(namespace))
                self._log("[INFO] Creating new asset instead...")
                # Create new asset using existing build function
                self._build_single_other_asset(asset)
                return

            # Replace the reference file path
            try:
                # Get current reference file
                old_file = cmds.referenceQuery(existing_ref, filename=True)
                self._log("Replacing reference: {} -> {}".format(os.path.basename(old_file), os.path.basename(cache_file)))

                # Check if files are the same (avoid unnecessary updates)
                if os.path.normpath(old_file) == os.path.normpath(cache_file):
                    self._log("[INFO] Reference already points to target file, no update needed")
                    return

                # Replace reference with new file using loadReference
                cmds.file(cache_file, loadReference=existing_ref)
                self._log("[OK] Updated reference for {} from {} to {}".format(
                    namespace, os.path.basename(old_file), os.path.basename(cache_file)))

                # Verify the update worked
                new_file = cmds.referenceQuery(existing_ref, filename=True)
                if os.path.normpath(new_file) == os.path.normpath(cache_file):
                    self._log("[OK] Reference update verified successfully")
                else:
                    self._log("[WARNING] Reference update may not have worked as expected")
                    self._log("[DEBUG] Expected: {}, Got: {}".format(cache_file, new_file))

            except Exception as e:
                self._log("[ERROR] Failed to replace reference for {}: {}".format(namespace, str(e)))
                # Try alternative method
                try:
                    self._log("[DEBUG] Trying alternative reference replacement method...")
                    cmds.file(cache_file, loadReference=existing_ref, options="v=0")
                    self._log("[OK] Updated reference using alternative method")
                except Exception as e2:
                    self._log("[ERROR] Alternative method also failed: {}".format(str(e2)))

        except Exception as e:
            self._log("[ERROR] ERROR updating other asset {}: {}".format(asset['filename'], str(e)))

    def _get_group_for_category(self, category):
        """Get the appropriate group name for asset category."""
        group_map = {
            "CHAR": "Character_Grp",
            "PROP": "Props_Grp",
            "SDRS": "Setdress_Grp",
            "SETS": "Sets_Grp",
            "DRSG": "Dressing_Grp",  # New dressing group for shot-based dressing
            "CAM": "Camera_Grp",
            "CAMERA": "Camera_Grp"
        }
        return group_map.get(category, "Props_Grp")  # Default to Props_Grp

    def _update_asset_status(self, filename, status):
        """Update asset status in the table."""
        try:
            for row in range(self.assets_table.rowCount()):
                item = self.assets_table.item(row, 0)  # Cache File column
                if item and item.text() == filename:
                    status_item = self.assets_table.item(row, 5)  # Status column
                    if status_item:
                        status_item.setText(status)
                    break
        except Exception as e:
            self._log("[WARNING] Could not update status for {}: {}".format(filename, str(e)))

    def _reference_shader_and_groom(self, category, name, identifier):
        """Reference shader and groom files for an asset."""
        try:
            # Skip shader/groom referencing for cameras
            if category in ["CAM", "CAMERA"]:
                self._log("[INFO] Skipping shader/groom for camera asset: {}".format(category))
                return

            # Get project root
            root = self.root_path_edit.text().strip()
            project = self.project_combo.currentText()

            # Build category directory name
            category_dirs = {
                "CHAR": "Character",
                "PROP": "Props",
                "SDRS": "Setdress",
                "SETS": "Sets"
            }

            category_dir = category_dirs.get(category)
            if not category_dir:
                self._log("[WARNING] Unknown category: {}".format(category))
                return

            # Build search paths based on category
            search_paths = []

            if category == "SETS":
                # Sets: Exterior and Interior
                search_paths = [
                    os.path.join(root, project, "all", "asset", category_dir, "Exterior", name, "hero"),
                    os.path.join(root, project, "all", "asset", category_dir, "Interior", name, "hero")
                ]
            elif category == "SDRS":
                # Setdress: Check name for Int/Ext, then try all paths
                if "Int" in name:
                    search_paths = [
                        os.path.join(root, project, "all", "asset", category_dir, "interior", name, "hero"),
                        os.path.join(root, project, "all", "asset", category_dir, "Interior", name, "hero")
                    ]
                elif "Ext" in name:
                    search_paths = [
                        os.path.join(root, project, "all", "asset", category_dir, "exterior", name, "hero"),
                        os.path.join(root, project, "all", "asset", category_dir, "Exterior", name, "hero")
                    ]
                else:
                    # Try all possible paths for setdress
                    search_paths = [
                        os.path.join(root, project, "all", "asset", category_dir, "interior", name, "hero"),
                        os.path.join(root, project, "all", "asset", category_dir, "Interior", name, "hero"),
                        os.path.join(root, project, "all", "asset", category_dir, "exterior", name, "hero"),
                        os.path.join(root, project, "all", "asset", category_dir, "Exterior", name, "hero"),
                        os.path.join(root, project, "all", "asset", category_dir, "Main", name, "hero"),
                        os.path.join(root, project, "all", "asset", category_dir, "object", name, "hero")
                    ]
            else:
                # Character, Props: Main and object
                search_paths = [
                    os.path.join(root, project, "all", "asset", category_dir, "Main", name, "hero"),
                    os.path.join(root, project, "all", "asset", category_dir, "object", name, "hero")
                ]

            # Look for shader and groom files
            shader_found = False
            groom_found = False

            for search_path in search_paths:
                if not _validate_directory(search_path):
                    continue

                # Look for shader file: {name}_rsshade.ma (only if not already found)
                if not shader_found:
                    shader_file = os.path.join(search_path, "{}_rsshade.ma".format(name))
                    if os.path.exists(shader_file):
                        shader_ns = "{}_{}_{}_shade".format(category, name, identifier)
                        try:
                            cmds.file(shader_file, reference=True, namespace=shader_ns)
                            self._log("Referenced shader: {} -> {}".format(shader_file, shader_ns))
                            shader_found = True
                        except Exception as e:
                            self._log("[ERROR] Failed to reference shader {}: {}".format(shader_file, str(e)))

                # Look for groom file: {name}_groom.ma (only if not already found)
                if not groom_found:
                    groom_file = os.path.join(search_path, "{}_groom.ma".format(name))
                    if os.path.exists(groom_file):
                        groom_ns = "{}_{}_{}_groom".format(category, name, identifier)
                        try:
                            cmds.file(groom_file, reference=True, namespace=groom_ns)
                            self._log("Referenced groom: {} -> {}".format(groom_file, groom_ns))
                            groom_found = True
                        except Exception as e:
                            self._log("[ERROR] Failed to reference groom {}: {}".format(groom_file, str(e)))

                # Break early if both shader and groom are found
                if shader_found and groom_found:
                    break

        except Exception as e:
            self._log("[ERROR] Failed to reference shader/groom for {}_{}: {}".format(category, name, str(e)))

    def _assign_shaders(self):
        """Assign shaders to assets - Step 3."""
        if not self.assets_data:
            self._log("[ERROR] No assets loaded. Please load cache list first.")
            return

        self._log("[ASSIGN SHADERS] Starting shader assignment process...")

        for asset in self.assets_data:
            try:
                category = asset['category']
                name = asset['name']
                identifier = asset['identifier']
                namespace = asset['namespace']

                # Shader and groom namespaces (already referenced in Step 2)
                shader_ns = "{}_{}_{}_shade".format(category, name, identifier)
                groom_ns = "{}_{}_{}_groom".format(category, name, identifier)

                # Check if shader namespace exists (was referenced)
                if cmds.namespace(exists=shader_ns):
                    self._log("Assigning shaders from {} to {}".format(shader_ns, namespace))
                    self._assign_shader_to_namespace(shader_ns, namespace)
                else:
                    self._log("[INFO] No shader namespace found: {}".format(shader_ns))

                # Check if groom namespace exists (was referenced)
                if cmds.namespace(exists=groom_ns):
                    self._log("Processing groom {} for {}".format(groom_ns, namespace))
                    self._assign_groom_to_namespace(groom_ns, namespace)
                else:
                    self._log("[INFO] No groom namespace found: {}".format(groom_ns))

            except Exception as e:
                self._log("[ERROR] Failed to assign shaders for {}: {}".format(asset['filename'], str(e)))

        self._log("[ASSIGN SHADERS] Completed shader assignment process")

        # Automatically run Place3D Linker and BlendShape creation after shader assignment
        self._log("[AUTO] Starting automatic Place3D Linker and BlendShape creation...")
        self._auto_place3d_linker()
        self._auto_create_blendshapes()
        self._log("[AUTO] Completed automatic Place3D Linker and BlendShape creation")

    def _assign_shader_to_namespace(self, shader_ns, geo_ns):
        """Assign shaders from shader namespace to geometry namespace and bind to rsMeshParameters."""
        try:
            self._log("Assigning shaders from {} to geometry in {}".format(shader_ns, geo_ns))

            # Find shading groups in shader namespace
            shader_sgs = cmds.ls("{}:*".format(shader_ns), type="shadingEngine") or []

            if not shader_sgs:
                self._log("[WARNING] No shading groups found in shader namespace: {}".format(shader_ns))
                return

            # Find geometry shapes and transforms in geo namespace
            geo_shapes = []
            geo_transforms = cmds.ls("{}:*".format(geo_ns), type="transform") or []
            top_level_transforms = []

            for xform in geo_transforms:
                # Check if this is a top-level transform (more flexible detection)
                parents = cmds.listRelatives(xform, parent=True, fullPath=True) or []
                is_top_level = False

                if not parents:
                    # No parents = definitely top level
                    is_top_level = True
                elif len(parents) == 1:
                    parent = parents[0]
                    # Check if parent is world, or a group node
                    if (parent == "|" or
                        parent.endswith("_Grp") or
                        parent.endswith("Grp") or
                        "Grp" in parent):
                        is_top_level = True

                if is_top_level:
                    top_level_transforms.append(xform)
                    self._log("[DEBUG] DEBUG: Identified top-level transform: {}".format(xform.split(":")[-1]))

                # Collect mesh shapes
                shapes = cmds.listRelatives(xform, shapes=True, fullPath=True) or []
                for shape in shapes:
                    if cmds.nodeType(shape) == "mesh":
                        geo_shapes.append(shape)

            if not geo_shapes:
                self._log("[WARNING] No mesh shapes found in geometry namespace: {}".format(geo_ns))
                return

            # Use proper shader assignment with stored mapping data (like Assign Shader by Namespace tab)
            total_assigned = 0

            # Scan for shading groups with stored mapping data
            shader_assignments = self._scan_shader_assignments(shader_ns)
            if not shader_assignments:
                self._log("[WARNING] No shading groups with 'snow__assign_shade' mapping found in {}".format(shader_ns))
                return

            # Plan assignments using stored mapping data
            assignment_plan = self._plan_shader_assignments(geo_ns, shader_assignments)

            # Execute assignments based on the plan
            for entry in assignment_plan:
                sg = entry["sg"]
                targets = entry.get("resolved", [])

                if not targets:
                    self._log("[SKIP] {} - no resolved targets".format(sg))
                    continue

                try:
                    assigned, failed = _assign_shapes_to_sg(targets, sg)
                    if assigned > 0:
                        total_assigned += assigned
                        self._log("Assigned {} specific shapes to {}".format(assigned, sg))
                    if failed:
                        self._log("[WARNING] Failed to assign {} shapes to {}".format(len(failed), sg))
                        for shp, reason in failed[:3]:  # Show first 3 failures
                            self._log("   ! {} ({})".format(shp, reason))
                except Exception as e:
                    self._log("[ERROR] Failed to assign {}: {}".format(sg, str(e)))

            self._log("Total shapes assigned using mapping data: {}".format(total_assigned))

            # IMPORTANT: Bind top-level transforms to rsMeshParameters sets
            if top_level_transforms:
                self._bind_to_rs_mesh_parameters(geo_ns, shader_ns, top_level_transforms)

        except Exception as e:
            self._log("[ERROR] Shader assignment failed: {}".format(str(e)))

    def _assign_groom_to_namespace(self, groom_ns, geo_ns):
        """Handle groom assignment to geometry namespace."""
        try:
            self._log("Processing groom {} for geometry {}".format(groom_ns, geo_ns))
            # For now, just log the groom processing
            # This can be expanded based on specific groom workflow requirements
            self._log("Groom namespace {} ready for blendshape creation with {}".format(groom_ns, geo_ns))
        except Exception as e:
            self._log("[ERROR] Groom processing failed: {}".format(str(e)))

    def _auto_place3d_linker(self):
        """Automatically run Place3D Linker for all assets with shaders."""
        self._log("[PLACE3D] Starting automatic Place3D Linker...")

        for asset in self.assets_data:
            try:
                category = asset['category']
                name = asset['name']
                identifier = asset['identifier']

                # Skip cameras (no shaders)
                if category in ["CAM", "CAMERA"]:
                    continue

                # Namespace patterns
                geo_ns = asset['namespace']  # CHAR_MainCharacter_001

                # Check if geo namespace exists
                if not cmds.namespace(exists=geo_ns):
                    self._log("[WARNING] Geo namespace does not exist: {}".format(geo_ns))
                    continue

                # Find shader namespace(s) - may be auto-renamed by Maya
                # Expected: CHAR_MainCharacter_001_shade
                # Actual may be: CHAR_MainCharacter_001_shade1, CHAR_MainCharacter_001_shade2, etc.
                expected_shader_ns = "{}_{}_{}_shade".format(category, name, identifier)

                # Get all namespaces and find matches
                all_namespaces = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []
                shader_namespaces = []

                # First check if expected namespace exists
                if cmds.namespace(exists=expected_shader_ns):
                    shader_namespaces.append(expected_shader_ns)

                # Also check for auto-renamed versions (shade1, shade2, etc.)
                import re
                shader_pattern = re.compile(r'^{}_shade\d*$'.format(re.escape(geo_ns)))
                for ns in all_namespaces:
                    if shader_pattern.match(ns) and ns not in shader_namespaces:
                        shader_namespaces.append(ns)

                if not shader_namespaces:
                    self._log("[INFO] No shader namespace found for: {} (expected: {})".format(geo_ns, expected_shader_ns))
                    continue

                # Process each shader namespace (usually just one, but handle multiple)
                for shader_ns in shader_namespaces:
                    if shader_ns != expected_shader_ns:
                        self._log("[PLACE3D] Processing: {} (geo) ↔ {} (shader - AUTO-RENAMED)".format(geo_ns, shader_ns))
                    else:
                        self._log("[PLACE3D] Processing: {} (geo) ↔ {} (shader)".format(geo_ns, shader_ns))

                    # Use same logic as working Place3D tab
                    geo_suffix = "_Grp"
                    place_suffix = "_Place3dTexture"

                    # Find Place3D pairs using existing function
                    pairs = _find_place3d_pairs_by_place(shader_ns, geo_ns, place_suffix, geo_suffix, allow_fuzzy=True)

                    if not pairs:
                        self._log("[INFO] No Place3D pairs found in shader namespace: {}".format(shader_ns))
                        continue

                    # Determine which method to use based on checkbox
                    use_matrix = self.use_matrix_method_checkbox.isChecked()
                    method_name = "Matrix" if use_matrix else "Constraint"

                    # Process each pair (same as working Place3D tab)
                    for pair in pairs:
                        place = pair["place"]
                        xform = pair["xform"]

                        if not xform:
                            self._log("[SKIP] No transform for place3D: {}".format(place))
                            continue

                        # Snap TRS (same for both methods)
                        snap_result = _snap_trs_world(xform, place, dry_run=False)

                        # Apply connection method based on user choice
                        if use_matrix:
                            # Use matrix method
                            connect_result = _matrix_transfer_transform(xform, place, force=False, dry_run=False)
                        else:
                            # Use constraint method (default)
                            connect_result = _parent_and_scale_constrain(xform, place, force=False, dry_run=False)

                        self._log("[PLACE3D] {}  <--  {}  ::  {} | {} ({})".format(
                            place, xform, snap_result, connect_result, method_name
                        ))

            except Exception as e:
                self._log("[ERROR] Place3D failed for {}: {}".format(asset['filename'], str(e)))

        self._log("[PLACE3D] Completed automatic Place3D Linker")

    def _auto_create_blendshapes(self):
        """Automatically create blendshapes for character assets."""
        self._log("[BLENDSHAPE] Starting automatic BlendShape creation...")

        char_assets = [asset for asset in self.assets_data if asset['category'] == 'CHAR']
        if not char_assets:
            self._log("[INFO] No character assets found for blendshape creation.")
            return

        for asset in char_assets:
            try:
                category = asset['category']
                name = asset['name']
                identifier = asset['identifier']

                # Namespace patterns
                anim_ns = asset['namespace']  # CHAR_MainCharacter_001
                groom_ns = "{}_{}_{}_groom".format(category, name, identifier)  # CHAR_MainCharacter_001_groom

                # Check if both namespaces exist
                if not cmds.namespace(exists=anim_ns):
                    self._log("[WARNING] Anim namespace does not exist: {}".format(anim_ns))
                    continue

                if not cmds.namespace(exists=groom_ns):
                    self._log("[INFO] No groom namespace for BlendShape: {}".format(groom_ns))
                    continue

                self._log("[BLENDSHAPE] Processing: {} (anim) ↔ {} (groom)".format(anim_ns, groom_ns))

                # Use EXACT same logic as working groom.py
                anim_suffix = "_Geo"
                groom_suffix = "_GroomGeo"

                # Find pairs using existing function
                pairs = _pairs_groom_first(anim_ns, groom_ns, anim_suffix, groom_suffix, allow_fuzzy=True)

                if not pairs:
                    self._log("[INFO] No BlendShape pairs found for {}".format(asset['name']))
                    continue

                # Process each pair (same as working BlendShape tab)
                for pair in pairs:
                    groom = pair["groomXform"]  # base (blendShape lives here)
                    anim = pair["animXform"]    # target

                    if not anim:
                        self._log("[SKIP] No anim match for groom: {}".format(groom))
                        continue

                    # Use EXACT same function call as working groom.py
                    result = _blendshape_anim_to_groom(
                        anim_xform=anim,
                        groom_xform=groom,
                        add_to_existing=True,
                        create_if_missing=True,
                        force_delete_existing=False,
                        dry_run=False
                    )
                    self._log("[BLENDSHAPE] {}  (base=groom)  <-  {}  (target=anim)  ::  {}".format(groom, anim, result))

            except Exception as e:
                self._log("[ERROR] BlendShape failed for {}: {}".format(asset['filename'], str(e)))

        self._log("[BLENDSHAPE] Completed automatic BlendShape creation")

    def _create_blendshapes(self):
        """Create blendshapes for characters - Step 4. Uses EXACT same logic as working groom.py"""
        if not self.assets_data:
            self._log("[ERROR] No assets loaded. Please load cache list first.")
            return

        char_assets = [asset for asset in self.assets_data if asset['category'] == 'CHAR']
        if not char_assets:
            self._log("[INFO] No character assets found for blendshape creation.")
            return

        self._log("[CREATE BLENDSHAPES] Starting blendshape creation process...")

        for asset in char_assets:
            try:
                category = asset['category']
                name = asset['name']
                identifier = asset['identifier']

                # We know the exact namespaces (instead of UI dropdowns)
                anim_ns = asset['namespace']  # CHAR_CharacterName_001
                groom_ns = "{}_{}_{}_groom".format(category, name, identifier)  # CHAR_CharacterName_001_groom

                self._log("Processing blendshapes: anim_ns={}, groom_ns={}".format(anim_ns, groom_ns))

                # Check if namespaces exist
                if not cmds.namespace(exists=anim_ns):
                    self._log("[WARNING] Anim namespace does not exist: {}".format(anim_ns))
                    continue

                if not cmds.namespace(exists=groom_ns):
                    self._log("[WARNING] Groom namespace does not exist: {}".format(groom_ns))
                    continue

                # Use EXACT same _pairs_groom_first logic from working groom.py
                anim_suffix = "_Geo"
                groom_suffix = "_GroomGeo"
                allow_fuzzy = True

                # EXACT same logic as _pairs_groom_first() function
                pairs = []
                groom_xforms = cmds.ls(groom_ns + ":*" + groom_suffix, type="transform") or []
                anim_xforms = cmds.ls(anim_ns + ":*" + anim_suffix, type="transform") or []
                anim_map = {_short(a): a for a in anim_xforms}

                self._log("Found {} groom transforms, {} anim transforms".format(len(groom_xforms), len(anim_xforms)))

                for groom in groom_xforms:
                    sg = _short(groom)
                    base = sg[:-len(groom_suffix)] if groom_suffix and sg.endswith(groom_suffix) else sg
                    wanted = base + (anim_suffix or "")
                    anim = anim_map.get(wanted)

                    if not anim and allow_fuzzy:
                        for s, full in anim_map.items():
                            if (not anim_suffix and s.startswith(base)) or (anim_suffix and s.startswith(base) and s.endswith(anim_suffix)):
                                anim = full
                                break

                    pairs.append({"groomXform": groom, "animXform": anim, "base": base, "status": "ok" if anim else "missing"})
                    if anim:
                        self._log("Found pair: {} (groom) <- {} (anim)".format(groom, anim))

                # Process pairs exactly like working groom.py BlendShapeTab._do_apply()
                for pair in pairs:
                    groom = pair["groomXform"]  # base (blendShape lives here)
                    anim = pair["animXform"]    # target
                    if anim == "-" or not anim:
                        self._log("No anim match for groom: {}".format(groom))
                        continue

                    # EXACT same function call as working groom.py
                    result = _blendshape_anim_to_groom(
                        anim_xform=anim,
                        groom_xform=groom,
                        add_to_existing=True,
                        create_if_missing=True,
                        force_delete_existing=False,
                        dry_run=False
                    )
                    self._log("{}  (base=groom)  <-  {}  (target=anim)  ::  {}".format(groom, anim, result))

            except Exception as e:
                self._log("[ERROR] Failed to create blendshapes for {}: {}".format(asset['filename'], str(e)))

        self._log("[CREATE BLENDSHAPES] Completed blendshape creation process")

    def _build_all_steps(self):
        """Execute all build steps in sequence with enhanced scene choice (Steps 1-5)."""
        try:
            # Check current scene state first
            scene_state = self._check_scene_state()

            # Ask user for scene choice
            choice = self._ask_scene_choice(scene_state["has_content"], context="build")

            if choice == "cancel":
                self._log("[BUILD] Build process cancelled by user")
                return
            elif choice == "new":
                # Create new scene first
                result = cmds.confirmDialog(
                    title="New Scene for Build",
                    message="This will create a new scene for building and lose any unsaved changes.\n\nContinue?",
                    button=["Yes", "No"],
                    defaultButton="Yes",
                    cancelButton="No",
                    dismissString="No"
                )
                if result != "Yes":
                    self._log("[BUILD] Build process cancelled by user")
                    return

                cmds.file(new=True, force=True)
                self._log("[BUILD] Created new scene for build process")
            elif choice == "current":
                # Building in current scene
                if scene_state["has_content"]:
                    self._log("[BUILD] Building in current scene with existing content")
                    if scene_state["matching_references"]:
                        self._log("[NOTICE] Scene has {} existing references matching current shot".format(len(scene_state["matching_references"])))
                        self._log("[NOTICE] Consider using 'Replace References' mode if needed")
                else:
                    self._log("[BUILD] Building in current empty scene")

            # Now proceed with the actual build process
            self._log("=" * 80)
            self._log("[START] STARTING COMPLETE SHOT BUILD PROCESS (STEPS 1-5)")
            self._log("=" * 80)

            # Step 0: Setup Scene (create groups if needed)
            self._log("[STEP] STEP 0: Setup Scene...")
            if choice == "new":
                self._create_scene_groups()
                self._log("[SETUP] Created asset groups in new scene")
            else:
                # For current scene, create missing groups only
                missing_groups = scene_state["missing_groups"]
                if missing_groups:
                    for grp_name in missing_groups:
                        if not cmds.objExists(grp_name):
                            grp = cmds.group(empty=True, name=grp_name)
                            self._log("Created missing group: {}".format(grp))
                else:
                    self._log("[SETUP] All required groups already exist")

            # Step 1: Build Sets
            self._log("[BUILD] STEP 1: Build Sets...")
            self._build_sets()

            # Steps 2+3+4: Build Assets + Assign + Place3D + BlendShape
            self._log("[TARGET] STEPS 2+3+4: Build Assets + Assign + Place3D + BlendShape...")
            self._build_assets()  # This already includes steps 3+4

            self._log("=" * 80)
            self._log("[OK] COMPLETE SHOT BUILD PROCESS FINISHED!")
            self._log("[SUCCESS] All steps completed successfully:")
            self._log("   [OK] Step 0: Scene setup")
            self._log("   [OK] Step 1: Sets built and components referenced")
            self._log("   [OK] Step 2: Other assets built and organized")
            self._log("   [OK] Step 3: Shaders assigned")
            self._log("   [OK] Step 4: Place3D linked and BlendShapes created")
            self._log("=" * 80)

        except Exception as e:
            self._log("=" * 80)
            self._log("[ERROR] ERROR IN COMPLETE BUILD PROCESS: {}".format(str(e)))
            self._log("=" * 80)
            raise

    def _build_single_asset(self, asset_index):
        """Build a single asset by index."""
        try:
            if asset_index >= len(self.assets_data):
                self._log("[ERROR] Invalid asset index: {}".format(asset_index))
                return

            asset = self.assets_data[asset_index]
            category = asset['category']

            self._log("[COMPLETE] BUILDING SINGLE ASSET: {} ({})".format(asset['filename'], category))

            # Update status to "Building"
            self._update_asset_status(asset['filename'], "Building...")

            if category == 'SETS':
                # Build Sets asset
                self._build_single_sets_asset(asset)
            elif category == 'DRSG':
                # Build Dressing asset (same process as SETS)
                self._build_single_drsg_asset(asset)
            else:
                # Build other asset (CHAR, PROP, SDRS, CAM)
                self._build_single_other_asset(asset)

            self._log("[OK] COMPLETED SINGLE ASSET BUILD: {}".format(asset['filename']))

        except Exception as e:
            self._log("[ERROR] ERROR BUILDING SINGLE ASSET: {}".format(str(e)))

    def _update_single_asset(self, asset_index):
        """Update a single asset by index."""
        self._log("[UPDATE] Individual Update button clicked for asset index: {}".format(asset_index))

        try:
            if asset_index >= len(self.assets_data):
                self._log("[ERROR] Invalid asset index: {}".format(asset_index))
                return

            asset = self.assets_data[asset_index]
            category = asset['category']

            self._log("[UPDATE] UPDATING SINGLE ASSET: {} ({})".format(asset['filename'], category))
            self._log("[DEBUG] Asset details: {}".format(asset))

            # Update status to "Updating"
            self._update_asset_status(asset['filename'], "Updating...")

            if category == 'SETS':
                # Update Sets asset with merge mode
                self._log("[DEBUG] Calling _update_single_sets_asset...")
                self._update_single_sets_asset(asset)
            elif category == 'DRSG':
                # Update Dressing asset with merge mode (same process as SETS)
                self._log("[DEBUG] Calling _update_single_drsg_asset...")
                self._update_single_drsg_asset(asset)
            else:
                # Update other asset (CHAR, PROP, SDRS, CAM) with reference replacement
                self._log("[DEBUG] Calling _update_single_other_asset...")
                self._update_single_other_asset(asset)

            # Update status to "Updated"
            self._update_asset_status(asset['filename'], "Updated")
            self._log("[OK] COMPLETED SINGLE ASSET UPDATE: {}".format(asset['filename']))

        except Exception as e:
            self._log("[ERROR] ERROR in single asset update: {}".format(str(e)))
            self._update_asset_status(asset['filename'], "Update Failed")
            if asset_index < len(self.assets_data):
                self._update_asset_status(self.assets_data[asset_index]['filename'], "Failed")

    def _build_single_sets_asset(self, asset):
        """Build a single Sets asset - EXACT SAME as Build Sets (Step 1) but for single asset with user scene choice."""
        try:
            namespace = asset['namespace']
            cache_file = asset['full_path']

            self._log("[BUILD] Building individual SETS asset: {}".format(asset['filename']))
            self._log_verbose("Importing SETS cache: {}".format(asset['filename']))

            # Check current scene state and ask user for scene choice (same as Build Sets Step 1)
            scene_state = self._check_scene_state()
            choice = self._ask_scene_choice(scene_state["has_content"], context="build")

            if choice == "cancel":
                self._log("[BUILD] Build cancelled by user for asset: {}".format(asset['filename']))
                self._update_asset_status(asset['filename'], "Cancelled")
                return
            elif choice == "new":
                self._log("[BUILD] User chose new scene for asset: {}".format(asset['filename']))
                # Create new scene
                result = cmds.confirmDialog(
                    title="New Scene Confirmation",
                    message="This will create a new scene and lose any unsaved changes.\n\nContinue?",
                    button=["Yes", "No"],
                    defaultButton="Yes",
                    cancelButton="No",
                    dismissString="No"
                )
                if result != "Yes":
                    self._log("[BUILD] User cancelled new scene creation")
                    self._update_asset_status(asset['filename'], "Cancelled")
                    return

                cmds.file(new=True, force=True)
                self._log("[BUILD] Created new scene for SETS build")

                # Create standard groups in new scene
                self._create_scene_groups()
            elif choice == "current":
                self._log("[BUILD] User chose current scene for asset: {}".format(asset['filename']))

            # === EXACT SAME LOGIC AS _build_sets() ===

            # Import alembic cache
            self._log("Importing SETS cache: {}".format(asset['filename']))

            # Create namespace for the set BEFORE import
            if not cmds.namespace(exists=namespace):
                cmds.namespace(add=namespace)
                self._log("Created namespace: {}".format(namespace))

            # Store current namespace
            current_ns = cmds.namespaceInfo(currentNamespace=True)

            try:
                # Set current namespace so import goes into it automatically
                cmds.namespace(setNamespace=namespace)
                self._log("Set current namespace to: {}".format(namespace))

                # Import the alembic file (will go into current namespace)
                cmds.AbcImport(cache_file, mode="import", fitTimeRange=False)
                self._log("Imported alembic into namespace: {}".format(namespace))

            finally:
                # Always restore original namespace
                cmds.namespace(setNamespace=current_ns)
                self._log("Restored namespace to: {}".format(current_ns))

            # Find locators in the namespace (should all be there now)
            all_locators = cmds.ls("{}:*_Loc".format(namespace), type="transform") or []
            self._log("Found {} locators in namespace: {}".format(len(all_locators), all_locators))

            # If no locators found in namespace, try fallback search
            if not all_locators:
                self._log("[WARNING] No locators found in namespace, trying fallback search...")
                all_locator_shapes = cmds.ls(type="locator") or []
                fallback_locators = []

                for loc_shape in all_locator_shapes:
                    loc_transforms = cmds.listRelatives(loc_shape, parent=True, fullPath=True) or []
                    for loc_transform in loc_transforms:
                        if loc_transform.endswith("_Loc"):
                            fallback_locators.append(loc_transform)

                all_locators = fallback_locators
                self._log("Found {} locators in fallback search: {}".format(len(all_locators), all_locators))

            # Process each locator - SAME AS Build Sets (Step 1)
            for loc in all_locators:
                self._process_sets_locator(loc, namespace)

            # Move to Sets group
            sets_group = self._get_group_for_category("SETS")
            if sets_group and cmds.objExists(sets_group):
                # Find main group in namespace
                main_grps = cmds.ls("{}:*Main_Grp".format(namespace), type="transform") or []
                if main_grps:
                    try:
                        cmds.parent(main_grps[0], sets_group)
                        self._log("Moved {} to {}".format(main_grps[0], sets_group))
                    except Exception as e:
                        self._log("[WARNING] Could not parent to Sets group: {}".format(str(e)))

            self._update_asset_status(asset['filename'], "Built")
            self._log("[OK] Successfully built individual SETS asset: {}".format(asset['filename']))

        except Exception as e:
            self._log("[ERROR] Failed to build Sets asset {}: {}".format(asset['filename'], str(e)))
            self._update_asset_status(asset['filename'], "Failed")

    def _build_single_drsg_asset(self, asset):
        """Build a single Dressing asset - SAME PROCESS as SETS but for shot-based dressing."""
        try:
            namespace = asset['namespace']
            cache_file = asset['full_path']

            self._log("[BUILD] Building individual DRSG asset: {}".format(asset['filename']))
            self._log_verbose("Importing DRSG cache: {}".format(asset['filename']))

            # Check current scene state and ask user for scene choice (same as SETS)
            scene_state = self._check_scene_state()
            choice = self._ask_scene_choice(scene_state["has_content"], context="build")

            if choice == "cancel":
                self._log("[BUILD] Build cancelled by user for asset: {}".format(asset['filename']))
                self._update_asset_status(asset['filename'], "Cancelled")
                return
            elif choice == "new":
                self._log("[BUILD] User chose new scene for asset: {}".format(asset['filename']))
                # Create new scene
                result = cmds.confirmDialog(
                    title="New Scene Confirmation",
                    message="This will create a new scene and lose any unsaved changes.\n\nContinue?",
                    button=["Yes", "No"],
                    defaultButton="Yes",
                    cancelButton="No",
                    dismissString="No"
                )
                if result != "Yes":
                    self._log("[BUILD] User cancelled new scene creation")
                    self._update_asset_status(asset['filename'], "Cancelled")
                    return

                cmds.file(new=True, force=True)
                self._log("[BUILD] Created new scene for DRSG build")

                # Create standard groups in new scene
                self._create_scene_groups()
            elif choice == "current":
                self._log("[BUILD] User chose current scene for asset: {}".format(asset['filename']))

            # === SAME LOGIC AS SETS BUILD ===

            # Import alembic cache
            self._log("Importing DRSG cache: {}".format(asset['filename']))

            # Create namespace for the dressing BEFORE import
            if not cmds.namespace(exists=namespace):
                cmds.namespace(add=namespace)
                self._log("Created namespace: {}".format(namespace))

            # Store current namespace
            current_ns = cmds.namespaceInfo(currentNamespace=True)

            try:
                # Set current namespace so import goes into it automatically
                self._log_verbose("Created namespace: {}".format(namespace))
                cmds.namespace(setNamespace=namespace)
                self._log("Set current namespace to: {}".format(namespace))

                # Import the alembic file (will go into current namespace)
                self._log_verbose("Importing alembic cache: {}".format(cache_file))
                cmds.AbcImport(cache_file, mode="import", fitTimeRange=False)
                self._log("Imported alembic into namespace: {}".format(namespace))

            finally:
                # Always restore original namespace
                cmds.namespace(setNamespace=current_ns)
                self._log("Restored namespace to: {}".format(current_ns))

            # Find locators in the namespace (should all be there now)
            all_locators = cmds.ls("{}:*_Loc".format(namespace), type="transform") or []
            self._log("Found {} locators in namespace: {}".format(len(all_locators), all_locators))

            if all_locators:
                self._log_verbose("Locator list:")
                for i, loc in enumerate(all_locators, 1):
                    self._log_verbose("  {}: {}".format(i, loc))

            # If no locators found in namespace, try fallback search
            if not all_locators:
                self._log("[WARNING] No locators found in namespace, trying fallback search...")
                all_locator_shapes = cmds.ls(type="locator") or []
                fallback_locators = []

                for loc_shape in all_locator_shapes:
                    loc_transforms = cmds.listRelatives(loc_shape, parent=True, fullPath=True) or []
                    for loc_transform in loc_transforms:
                        if loc_transform.endswith("_Loc"):
                            fallback_locators.append(loc_transform)

                all_locators = fallback_locators
                self._log("Found {} locators in fallback search: {}".format(len(all_locators), all_locators))

            # Process each locator - SAME AS SETS (reuse existing method)
            self._log_verbose("Processing {} locators for component referencing...".format(len(all_locators)))
            for i, loc in enumerate(all_locators, 1):
                self._log_verbose("Processing locator {}/{}: {}".format(i, len(all_locators), loc.split(":")[-1]))
                self._process_sets_locator(loc, namespace)

            # Move to Dressing group
            drsg_group = self._get_group_for_category("DRSG")
            self._log_verbose("Target group for DRSG: {}".format(drsg_group))
            if drsg_group and cmds.objExists(drsg_group):
                # Find main group in namespace
                main_grps = cmds.ls("{}:*Main_Grp".format(namespace), type="transform") or []
                self._log_verbose("Found main groups: {}".format(main_grps))
                if main_grps:
                    try:
                        self._log_verbose("Moving {} to {}".format(main_grps[0], drsg_group))
                        cmds.parent(main_grps[0], drsg_group)
                        self._log("Moved {} to {}".format(main_grps[0], drsg_group))
                    except Exception as e:
                        self._log("[WARNING] Could not parent to Dressing group: {}".format(str(e)))

            self._update_asset_status(asset['filename'], "Built")
            self._log("[OK] Successfully built individual DRSG asset: {}".format(asset['filename']))

        except Exception as e:
            self._log("[ERROR] Failed to build Dressing asset {}: {}".format(asset['filename'], str(e)))
            self._update_asset_status(asset['filename'], "Failed")

    def _build_single_other_asset(self, asset):
        """Build a single non-Sets asset (CHAR, PROP, SDRS, CAM) - COMPLETE BUILD."""
        try:
            category = asset['category']
            name = asset['name']
            identifier = asset['identifier']
            cache_file = asset['full_path']
            namespace = asset['namespace']

            self._log("[COMPLETE] COMPLETE BUILD {} asset: {} -> {}".format(category, asset['filename'], namespace))

            # Step 1: Reference the alembic file with namespace
            cmds.file(cache_file, reference=True, namespace=namespace)
            self._log("[OK] Referenced {} cache with namespace: {}".format(category, namespace))

            # Step 2: Move to appropriate group
            group = self._get_group_for_category(category)
            if group:
                self._move_to_group(namespace, group)
                self._log("[OK] Moved {} to group: {}".format(namespace, group))

            # Skip shader/groom/place3d/blendshape for cameras
            if category in ["CAM", "CAMERA"]:
                self._log("[OK] Camera asset build complete (no shaders needed)")
                self._update_asset_status(asset['filename'], "Built")
                return

            # Step 3: Reference shader and groom files
            self._log("[SHADER] Referencing shader and groom files...")
            self._reference_shader_and_groom(category, name, identifier)

            # Set expected namespaces
            shader_ns = "{}_shade".format(namespace)
            groom_ns = "{}_groom".format(namespace) if category == 'CHAR' else None

            # Step 4: Assign shaders
            if cmds.namespace(exists=shader_ns):
                self._log("[SHADER] Assigning shaders...")
                self._assign_single_asset_shaders(namespace, shader_ns)
                self._log("[OK] Shaders assigned")

            # Step 5: Place3D Linker + Shading Attribute Connections
            if shader_ns and cmds.namespace(exists=shader_ns):
                self._log("[LINK] Running Place3D Linker...")
                self._auto_place3d_single_asset(asset)

                # Connect shading attributes (snow__ -> shader namespace)
                self._log("[ATTR] Connecting shading attributes...")
                attr_results = _connect_shading_attributes(namespace, shader_ns.split(':')[-1])  # Remove any namespace prefix
                if attr_results:
                    for result in attr_results:
                        self._log_verbose("  {}".format(result))
                    connected_count = sum(1 for r in attr_results if r.startswith("// Result: Connected"))
                    if connected_count > 0:
                        self._log("[OK] Connected {} shading attributes".format(connected_count))
                    else:
                        self._log("[INFO] No new shading attribute connections needed")

                self._log("[OK] Place3D Linker complete")

            # Step 6: BlendShape (only for characters with groom)
            if category == 'CHAR' and groom_ns and cmds.namespace(exists=groom_ns):
                self._log("[BLEND] Creating BlendShapes...")
                self._auto_blendshape_single_asset(asset)
                self._log("[OK] BlendShapes created")

            self._log("[SUCCESS] COMPLETE BUILD FINISHED: {}".format(asset['filename']))
            self._update_asset_status(asset['filename'], "Built")

        except Exception as e:
            self._log("[ERROR] ERROR in complete build for {} asset {}: {}".format(category, asset['filename'], str(e)))
            self._update_asset_status(asset['filename'], "Failed")

    def _auto_place3d_single_asset(self, asset):
        """Run Place3D Linker for a single asset."""
        try:
            geo_ns = asset['namespace']
            shader_ns = "{}_shade".format(geo_ns)

            if cmds.namespace(exists=shader_ns):
                pairs = _find_place3d_pairs_by_place(shader_ns, geo_ns, "_Place3dTexture", "_Grp", allow_fuzzy=True)
                if pairs:
                    # Determine which method to use based on checkbox
                    use_matrix = self.use_matrix_method_checkbox.isChecked()
                    method_name = "Matrix" if use_matrix else "Constraint"

                    for pair in pairs:
                        if pair["xform"] and pair["place"]:  # Only process if both exist
                            # Snap TRS (same for both methods)
                            _snap_trs_world(pair["xform"], pair["place"])

                            # Apply connection method based on user choice
                            if use_matrix:
                                _matrix_transfer_transform(pair["xform"], pair["place"])
                            else:
                                _parent_and_scale_constrain(pair["xform"], pair["place"])

                    self._log("Place3D Linker ({}): {} pairs processed for {}".format(
                        method_name, len(pairs), asset['filename']
                    ))
                else:
                    self._log("Place3D Linker: No pairs found for {}".format(asset['filename']))
            else:
                self._log("Place3D Linker: No shader namespace found for {}".format(asset['filename']))

        except Exception as e:
            self._log("[WARNING] Place3D Linker failed for {}: {}".format(asset['filename'], str(e)))

    def _auto_blendshape_single_asset(self, asset):
        """Run BlendShape creation for a single asset."""
        try:
            anim_ns = asset['namespace']
            groom_ns = "{}_groom".format(anim_ns)

            self._log_verbose("=== BLENDSHAPE AUTO DIAGNOSTICS ===")
            self._log_verbose("Anim NS: '{}', Groom NS: '{}'".format(anim_ns, groom_ns))

            # Check if namespaces exist
            all_ns = cmds.namespaceInfo(listOnlyNamespaces=True) or []
            self._log_verbose("Namespace exists - Anim: {}, Groom: {}".format(anim_ns in all_ns, groom_ns in all_ns))

            if cmds.namespace(exists=groom_ns):
                # Auto-detect correct suffixes by checking what exists in scene
                anim_suffix, groom_suffix = _detect_blendshape_suffixes(anim_ns, groom_ns)

                self._log_verbose("Auto-detected suffixes - Anim: '{}', Groom: '{}'".format(anim_suffix, groom_suffix))

                # Check objects in groom namespace
                groom_all = cmds.ls(groom_ns + ":*", type="transform") or []
                groom_with_suffix = cmds.ls(groom_ns + ":*" + groom_suffix, type="transform") or []
                anim_all = cmds.ls(anim_ns + ":*", type="transform") or []
                anim_with_suffix = cmds.ls(anim_ns + ":*" + anim_suffix, type="transform") or []

                self._log_verbose("Objects found - Groom all: {}, with suffix: {}".format(len(groom_all), len(groom_with_suffix)))
                self._log_verbose("Objects found - Anim all: {}, with suffix: {}".format(len(anim_all), len(anim_with_suffix)))

                if groom_with_suffix:
                    self._log_verbose("Groom objects: {}".format([_short(x) for x in groom_with_suffix[:3]]))
                if anim_with_suffix:
                    self._log_verbose("Anim objects: {}".format([_short(x) for x in anim_with_suffix[:3]]))

                # Use enhanced function with auto-detection disabled (already detected above)
                pairs = _pairs_groom_first(anim_ns, groom_ns, anim_suffix, groom_suffix, allow_fuzzy=True, auto_detect_suffixes=False)
                self._log_verbose("Found {} pairs for BlendShape processing".format(len(pairs)))

                if pairs:
                    success_count = 0
                    for i, pair in enumerate(pairs):
                        self._log_verbose("Pair {}: Groom='{}', Anim='{}', Status='{}'".format(
                            i+1, pair.get("groomXform", "None"), pair.get("animXform", "None"), pair.get("status", "unknown")))

                        if pair["status"] == "ok" and pair["animXform"] and pair["groomXform"]:
                            result = _blendshape_anim_to_groom(pair["animXform"], pair["groomXform"])
                            self._log_verbose("  BlendShape result: {}".format(result))
                            if "error" not in result.lower():
                                success_count += 1
                        else:
                            self._log_verbose("  Skipped - missing anim or groom object")

                    self._log("BlendShape: {} pairs processed, {} successful for {}".format(len(pairs), success_count, asset['filename']))
                else:
                    self._log("BlendShape: No pairs found for {}".format(asset['filename']))
            else:
                self._log("BlendShape: No groom namespace found for {}".format(asset['filename']))

            self._log_verbose("=== END BLENDSHAPE DIAGNOSTICS ===")

        except Exception as e:
            self._log("[WARNING] BlendShape creation failed for {}: {}".format(asset['filename'], str(e)))

    def _find_asset_shader_file(self, category, name):
        """Find shader file for an asset."""
        try:
            root = self.root_path_edit.text().strip()
            project = self.project_combo.currentText()

            # Build shader file path based on category
            if category == 'CHAR':
                # Character shader path
                shader_path = os.path.join(root, project, "all", "asset", "Character", "Main", name, "hero", "{}_rsshade.ma".format(name))
            elif category == 'PROP':
                # Props shader path
                shader_path = os.path.join(root, project, "all", "asset", "Props", "object", name, "hero", "{}_rsshade.ma".format(name))
            elif category == 'SDRS':
                # Setdress shader path - determine interior/exterior
                if "Int" in name:
                    subdir = "interior"
                elif "Ext" in name:
                    subdir = "exterior"
                else:
                    subdir = "interior"  # Default
                shader_path = os.path.join(root, project, "all", "asset", "Setdress", subdir, name, "hero", "{}_rsshade.ma".format(name))
            else:
                return None

            if os.path.exists(shader_path):
                return shader_path
            else:
                self._log("[WARNING] Shader file not found: {}".format(shader_path))
                return None

        except Exception as e:
            self._log("[ERROR] Failed to find shader file for {}: {}".format(name, str(e)))
            return None

    def _find_asset_groom_file(self, category, name):
        """Find groom file for an asset."""
        try:
            root = self.root_path_edit.text().strip()
            project = self.project_combo.currentText()

            # Only characters have grooms
            if category == 'CHAR':
                groom_path = os.path.join(root, project, "all", "asset", "Character", "Main", name, "hero", "{}_groom.ma".format(name))
                if os.path.exists(groom_path):
                    return groom_path
                else:
                    self._log("[WARNING] Groom file not found: {}".format(groom_path))
                    return None
            else:
                return None

        except Exception as e:
            self._log("[ERROR] Failed to find groom file for {}: {}".format(name, str(e)))
            return None

    def _assign_shader_to_single_asset(self, shader_ns, geo_ns):
        """Assign shaders to geometry for a single asset."""
        try:
            self._log("Assigning shaders from {} to geometry in {}".format(shader_ns, geo_ns))

            # Find shading groups in shader namespace
            shader_sgs = cmds.ls("{}:*".format(shader_ns), type="shadingEngine") or []

            if not shader_sgs:
                self._log("[WARNING] No shading groups found in shader namespace: {}".format(shader_ns))
                return

            # Find geometry shapes in geo namespace
            geo_shapes = []
            geo_transforms = cmds.ls("{}:*".format(geo_ns), type="transform") or []

            for xform in geo_transforms:
                shapes = cmds.listRelatives(xform, shapes=True, fullPath=True) or []
                for shape in shapes:
                    if cmds.nodeType(shape) == "mesh":
                        geo_shapes.append(shape)

            if not geo_shapes:
                self._log("[WARNING] No mesh shapes found in geometry namespace: {}".format(geo_ns))
                return

            # Use proper shader assignment with stored mapping data (like Assign Shader by Namespace tab)
            total_assigned = 0

            # Scan for shading groups with stored mapping data
            shader_assignments = self._scan_shader_assignments(shader_ns)
            if not shader_assignments:
                self._log("[WARNING] No shading groups with 'snow__assign_shade' mapping found in {}".format(shader_ns))
                return

            # Plan assignments using stored mapping data
            assignment_plan = self._plan_shader_assignments(geo_ns, shader_assignments)

            # Execute assignments based on the plan
            for entry in assignment_plan:
                sg = entry["sg"]
                targets = entry.get("resolved", [])

                if not targets:
                    self._log("[SKIP] {} - no resolved targets".format(sg))
                    continue

                try:
                    assigned, failed = _assign_shapes_to_sg(targets, sg)
                    if assigned > 0:
                        total_assigned += assigned
                        self._log("Assigned {} specific shapes to {}".format(assigned, sg))
                    if failed:
                        self._log("[WARNING] Failed to assign {} shapes to {}".format(len(failed), sg))
                        for shp, reason in failed[:3]:  # Show first 3 failures
                            self._log("   ! {} ({})".format(shp, reason))
                except Exception as e:
                    self._log("[ERROR] Failed to assign {}: {}".format(sg, str(e)))

            self._log("Total shapes assigned using mapping data: {}".format(total_assigned))

        except Exception as e:
            self._log("[ERROR] Single asset shader assignment failed: {}".format(str(e)))

    def _move_to_group(self, namespace, group_name):
        """Move referenced asset to appropriate group."""
        try:
            if not cmds.objExists(group_name):
                self._log("[WARNING] Group does not exist: {}".format(group_name))
                return

            # Find the reference node for this namespace
            ref_nodes = cmds.ls(type="reference") or []
            target_ref = None

            for ref_node in ref_nodes:
                if ref_node == "sharedReferenceNode":
                    continue
                try:
                    # Get the namespace of this reference
                    ref_namespace = cmds.referenceQuery(ref_node, namespace=True)
                    if ref_namespace == ":{}".format(namespace):
                        target_ref = ref_node
                        break
                except Exception:
                    continue

            if target_ref:
                # Get the top-level nodes from this reference
                try:
                    ref_nodes_list = cmds.referenceQuery(target_ref, nodes=True, dagPath=True) or []
                    # Find top-level transforms (no parent outside the reference)
                    top_level_nodes = []
                    for node in ref_nodes_list:
                        if cmds.nodeType(node) == "transform":
                            parent = cmds.listRelatives(node, parent=True, fullPath=True)
                            if not parent or not any(p in ref_nodes_list for p in parent):
                                top_level_nodes.append(node)

                    # Parent top-level nodes to the group
                    for top_node in top_level_nodes:
                        try:
                            cmds.parent(top_node, group_name)
                            self._log("Moved {} to {}".format(top_node, group_name))
                        except Exception as e:
                            self._log("[WARNING] Failed to move {} to {}: {}".format(top_node, group_name, str(e)))

                except Exception as e:
                    self._log("[WARNING] Failed to query reference nodes for {}: {}".format(namespace, str(e)))
            else:
                self._log("[WARNING] Could not find reference node for namespace: {}".format(namespace))

        except Exception as e:
            self._log("[ERROR] Failed to move {} to group {}: {}".format(namespace, group_name, str(e)))

    def _assign_single_asset_shaders(self, geo_namespace, shader_namespace):
        """Assign shaders to a single asset and bind to rsMeshParameters sets."""
        try:
            # Find shading groups in shader namespace
            shader_sgs = cmds.ls("{}:*".format(shader_namespace), type="shadingEngine") or []

            if not shader_sgs:
                self._log("[WARNING] No shading groups found in shader namespace: {}".format(shader_namespace))
                return

            # Find geometry shapes and transforms in geo namespace
            geo_shapes = []
            geo_transforms = cmds.ls("{}:*".format(geo_namespace), type="transform") or []
            top_level_transforms = []

            for xform in geo_transforms:
                # Check if this is a top-level transform (more flexible detection)
                parents = cmds.listRelatives(xform, parent=True, fullPath=True) or []
                is_top_level = False

                if not parents:
                    # No parents = definitely top level
                    is_top_level = True
                elif len(parents) == 1:
                    parent = parents[0]
                    # Check if parent is world, or a group node
                    if (parent == "|" or
                        parent.endswith("_Grp") or
                        parent.endswith("Grp") or
                        "Grp" in parent):
                        is_top_level = True

                if is_top_level:
                    top_level_transforms.append(xform)
                    self._log("[DEBUG] DEBUG: Identified top-level transform: {}".format(xform.split(":")[-1]))

                # Collect mesh shapes
                shapes = cmds.listRelatives(xform, shapes=True, fullPath=True) or []
                for shape in shapes:
                    if cmds.nodeType(shape) == "mesh":
                        geo_shapes.append(shape)

            if not geo_shapes:
                self._log("[WARNING] No mesh shapes found in geometry namespace: {}".format(geo_namespace))
                return

            self._log("Found {} mesh shapes and {} top-level transforms in {}".format(
                len(geo_shapes), len(top_level_transforms), geo_namespace))

            # Use proper shader assignment with stored mapping data (like Assign Shader by Namespace tab)
            total_assigned = 0

            # Scan for shading groups with stored mapping data
            shader_assignments = self._scan_shader_assignments(shader_namespace)
            if not shader_assignments:
                self._log("[WARNING] No shading groups with 'snow__assign_shade' mapping found in {}".format(shader_namespace))
                return

            # Plan assignments using stored mapping data
            assignment_plan = self._plan_shader_assignments(geo_namespace, shader_assignments)

            # Execute assignments based on the plan
            for entry in assignment_plan:
                sg = entry["sg"]
                targets = entry.get("resolved", [])

                if not targets:
                    self._log("[SKIP] {} - no resolved targets".format(sg))
                    continue

                try:
                    assigned, failed = _assign_shapes_to_sg(targets, sg)
                    if assigned > 0:
                        total_assigned += assigned
                        self._log("Assigned {} specific shapes to {}".format(assigned, sg))
                    if failed:
                        self._log("[WARNING] Failed to assign {} shapes to {}".format(len(failed), sg))
                        for shp, reason in failed[:5]:  # Show first 5 failures
                            self._log("   ! {} ({})".format(shp, reason))
                except Exception as e:
                    self._log("[ERROR] Failed to assign {}: {}".format(sg, str(e)))

            # IMPORTANT: Bind top-level transforms to rsMeshParameters sets
            self._bind_to_rs_mesh_parameters(geo_namespace, shader_namespace, top_level_transforms)

            self._log("Total shapes assigned: {}".format(total_assigned))

        except Exception as e:
            self._log("[ERROR] Failed to assign shaders for {}: {}".format(geo_namespace, str(e)))

    def _scan_shader_assignments(self, shader_namespace):
        """Scan for shading groups with stored mapping data (same as AssignShaderTab._scan_shading_groups)."""
        all_sg = cmds.ls(type="shadingEngine") or []
        hit = []
        for sg in all_sg:
            if not sg.startswith(shader_namespace + ":"):
                continue
            if cmds.objExists("{}.snow__assign_shade".format(sg)):
                mapping = _read_mapping_from_sg(sg)
                mat = _sg_has_material_connection(sg)
                hit.append((sg, mat, mapping))
        return hit

    def _plan_shader_assignments(self, geo_namespace, sg_entries):
        """Plan shader assignments using stored mapping data (same as AssignShaderTab._plan_assignments)."""
        plan = []
        for sg, mat, stored_paths in sg_entries:
            resolved, unresolved = [], []
            for p in stored_paths:
                shp = _resolve_shape_in_scene(p, geo_namespace)
                if shp and cmds.objExists(shp):
                    resolved.append(shp)
                else:
                    unresolved.append(p)
            plan.append({
                "sg": sg,
                "material": mat,
                "targets": list(stored_paths),
                "resolved": sorted(list(set(resolved))),
                "unresolved": list(unresolved)
            })
        return plan

    def _bind_to_rs_mesh_parameters(self, geo_namespace, shader_namespace, top_level_transforms):
        """Bind top-level geometry transforms to rsMeshParameters sets in shader namespace."""
        try:
            self._log("[DEBUG] DEBUG: Searching for rsMeshParameters sets in {}".format(shader_namespace))

            # Find all rsMeshParameters sets in shader namespace
            rs_mesh_sets = []
            all_shader_nodes = cmds.ls("{}:*".format(shader_namespace)) or []
            shader_sets = cmds.ls("{}:*".format(shader_namespace), type="objectSet") or []

            self._log("[DEBUG] DEBUG: Found {} total nodes in shader namespace".format(len(all_shader_nodes)))
            self._log("[DEBUG] DEBUG: Found {} objectSet nodes in shader namespace".format(len(shader_sets)))

            # List all sets for debugging
            for set_node in shader_sets:
                set_short = set_node.split(":")[-1]
                self._log("[DEBUG] DEBUG: Found objectSet: {}".format(set_short))

                # Check if this is an rsMeshParameters set (more flexible matching)
                if ("rsMeshParameters" in set_short or
                    "rsMP" in set_short or
                    "rsMesh" in set_short or
                    "MeshParameters" in set_short):
                    rs_mesh_sets.append(set_node)
                    self._log("[OK] DEBUG: Identified as rsMeshParameters set: {}".format(set_short))

            if not rs_mesh_sets:
                self._log("[WARNING] No rsMeshParameters sets found in {}".format(shader_namespace))
                self._log("[DEBUG] DEBUG: Available objectSets: {}".format([s.split(":")[-1] for s in shader_sets]))
                return

            if not top_level_transforms:
                self._log("[WARNING] No top-level transforms found in {}".format(geo_namespace))
                return

            self._log("[LINK] Binding {} transforms to {} rsMeshParameters sets".format(
                len(top_level_transforms), len(rs_mesh_sets)))

            # Debug: List transforms and sets
            for transform in top_level_transforms:
                self._log("[DEBUG] DEBUG: Transform to bind: {}".format(transform.split(":")[-1]))
            for rs_set in rs_mesh_sets:
                self._log("[DEBUG] DEBUG: rsMeshParameters set: {}".format(rs_set.split(":")[-1]))

            # Strategy 1: Try to match by name pattern
            bound_count = 0
            for transform in top_level_transforms:
                transform_short = transform.split(":")[-1]  # Get short name without namespace
                self._log("[DEBUG] DEBUG: Trying to match transform: {}".format(transform_short))

                # Try to find matching rsMeshParameters set
                matching_set = None
                for rs_set in rs_mesh_sets:
                    rs_set_short = rs_set.split(":")[-1]  # Get short name without namespace
                    self._log("[DEBUG] DEBUG: Checking against set: {}".format(rs_set_short))

                    # Check various naming patterns
                    if (transform_short in rs_set_short or
                        rs_set_short in transform_short or
                        self._names_match_pattern(transform_short, rs_set_short)):
                        matching_set = rs_set
                        self._log("[OK] DEBUG: Found match: {} -> {}".format(transform_short, rs_set_short))
                        break

                # If found matching set, add transform to it
                if matching_set:
                    try:
                        # Check if already in set
                        current_members = cmds.sets(matching_set, query=True) or []
                        if transform not in current_members:
                            cmds.sets(transform, addElement=matching_set)
                            bound_count += 1
                            self._log("[OK] Bound {} to {}".format(transform_short, matching_set.split(":")[-1]))
                        else:
                            self._log("[INFO] {} already in {}".format(transform_short, matching_set.split(":")[-1]))
                    except Exception as e:
                        self._log("[ERROR] Failed to bind {} to {}: {}".format(transform_short, matching_set, str(e)))
                        # Try alternative binding method
                        try:
                            cmds.sets(transform, edit=True, addElement=matching_set)
                            bound_count += 1
                            self._log("[OK] Bound {} to {} (alternative method)".format(transform_short, matching_set.split(":")[-1]))
                        except Exception as e2:
                            self._log("[ERROR] Alternative binding also failed: {}".format(str(e2)))
                else:
                    self._log("[WARNING] No matching rsMeshParameters set found for {}".format(transform_short))

            # Strategy 2: If no matches found, add all transforms to all rsMeshParameters sets
            if bound_count == 0 and rs_mesh_sets:
                self._log("[UPDATE] No name matches found, adding all transforms to all rsMeshParameters sets")
                for rs_set in rs_mesh_sets:
                    rs_set_short = rs_set.split(":")[-1]
                    for transform in top_level_transforms:
                        transform_short = transform.split(":")[-1]
                        try:
                            current_members = cmds.sets(rs_set, query=True) or []
                            if transform not in current_members:
                                # Try primary method
                                cmds.sets(transform, addElement=rs_set)
                                bound_count += 1
                                self._log("[OK] Added {} to {}".format(transform_short, rs_set_short))
                            else:
                                self._log("[INFO] {} already in {}".format(transform_short, rs_set_short))
                        except Exception as e:
                            self._log("[WARNING] Primary method failed for {} -> {}: {}".format(transform_short, rs_set_short, str(e)))
                            # Try alternative method
                            try:
                                cmds.sets(transform, edit=True, addElement=rs_set)
                                bound_count += 1
                                self._log("[OK] Added {} to {} (alternative method)".format(transform_short, rs_set_short))
                            except Exception as e2:
                                self._log("[ERROR] Both methods failed for {} -> {}: {}".format(transform_short, rs_set_short, str(e2)))

            # Strategy 3: If still no bindings, try more aggressive approach
            if bound_count == 0 and rs_mesh_sets and top_level_transforms:
                self._log("🚨 AGGRESSIVE: Trying to bind any transform to any rsMeshParameters set")
                # Just try to add the first transform to the first set as a test
                first_transform = top_level_transforms[0]
                first_set = rs_mesh_sets[0]
                try:
                    # Force add without checking membership
                    cmds.sets(first_transform, forceElement=first_set)
                    bound_count += 1
                    self._log("[OK] AGGRESSIVE: Forced {} into {}".format(
                        first_transform.split(":")[-1], first_set.split(":")[-1]))
                except Exception as e:
                    self._log("[ERROR] AGGRESSIVE method also failed: {}".format(str(e)))
                    # Last resort: check if nodes actually exist
                    if cmds.objExists(first_transform):
                        self._log("[OK] Transform exists: {}".format(first_transform))
                    else:
                        self._log("[ERROR] Transform does not exist: {}".format(first_transform))

                    if cmds.objExists(first_set):
                        self._log("[OK] Set exists: {}".format(first_set))
                    else:
                        self._log("[ERROR] Set does not exist: {}".format(first_set))

            if bound_count > 0:
                self._log("[TARGET] rsMeshParameters binding complete: {} bindings created".format(bound_count))
            else:
                self._log("[ERROR] rsMeshParameters binding failed: No bindings created")
                self._log("[DEBUG] DEBUG: This may indicate a problem with transform detection or set identification")

        except Exception as e:
            self._log("[ERROR] Failed to bind rsMeshParameters: {}".format(str(e)))

    def _names_match_pattern(self, transform_name, set_name):
        """Check if transform name and set name match common patterns."""
        try:
            # Remove common suffixes/prefixes
            transform_clean = transform_name.replace("_Grp", "").replace("_grp", "").replace("Grp", "")
            set_clean = set_name.replace("rsMeshParameters", "").replace("rsMP", "").replace("_", "")

            # Check if cleaned names match
            if transform_clean.lower() == set_clean.lower():
                return True

            # Check if one contains the other
            if transform_clean.lower() in set_clean.lower() or set_clean.lower() in transform_clean.lower():
                return True

            # Check for common asset naming patterns
            # Example: CHAR_MainCharacter_001 matches MainCharacter or Character
            transform_parts = transform_clean.split("_")
            set_parts = set_clean.split("_")

            for t_part in transform_parts:
                for s_part in set_parts:
                    if len(t_part) > 3 and len(s_part) > 3:  # Avoid matching short words
                        if t_part.lower() in s_part.lower() or s_part.lower() in t_part.lower():
                            return True

            return False

        except Exception:
            return False

        except Exception as e:
            self._log("[ERROR] Single asset shader assignment failed: {}".format(str(e)))

    def _build_in_subprocess(self):
        """Build shot in subprocess and save to target department."""
        try:
            # Get current shot info
            project = self.project_combo.currentText()
            episode = self.episode_combo.currentText()
            sequence = self.sequence_combo.currentText()
            shot = self.shot_combo.currentText()
            department = self.dept_combo.currentText()

            if not all([project, episode, sequence, shot]):
                self._log("[ERROR] Please select project, episode, sequence, and shot first")
                return

            self._log("[UPDATE] STARTING SUBPROCESS BUILD")
            self._log("Project: {}, Episode: {}, Sequence: {}, Shot: {}".format(project, episode, sequence, shot))
            self._log("Target Department: {}".format(department))

            # Build output path
            root = self.root_path_edit.text().strip()
            output_path = os.path.join(root, project, "all", "scene", episode, sequence, shot, department, "work")

            if not os.path.exists(output_path):
                os.makedirs(output_path)
                self._log("Created output directory: {}".format(output_path))

            # Generate standardized filename: {ep}_{seq}_{shot}_{department}_{version}.ma
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            # Get version from current shot (if available)
            version = "v001"  # Default version for single shot build
            if hasattr(self, 'current_shot_version') and self.current_shot_version:
                version = self.current_shot_version

            scene_filename = "{}_{}_{}_{}_{}_{}.ma".format(episode, sequence, shot, department, version, timestamp)
            scene_filepath = os.path.join(output_path, scene_filename)

            # Create subprocess build script
            self._create_subprocess_build_script(project, episode, sequence, shot, department, scene_filepath)

        except Exception as e:
            self._log("[ERROR] Subprocess build failed: {}".format(str(e)))

    def _create_subprocess_build_script(self, project, episode, sequence, shot, department, output_file):
        """Create and execute subprocess build script."""
        try:
            import tempfile
            import subprocess

            # Create temporary Python script for subprocess
            script_content = '''
import sys
import os
import maya.standalone
maya.standalone.initialize()

import maya.cmds as cmds

def build_shot():
    """Build shot in subprocess."""
    try:
        print("=== SUBPROCESS SHOT BUILD START ===")
        print("Project: {project}")
        print("Shot: {episode}_{sequence}_{shot}")
        print("Department: {department}")
        print("Output: {output_file}")

        # Create new scene
        cmds.file(new=True, force=True)

        # Set project (if needed)
        # cmds.workspace("{root_path}/{project}", openWorkspace=True)

        # TODO: Add your shot build logic here
        # This would include the same logic as _build_all_steps()
        # but adapted for subprocess execution

        # Create basic scene structure for now
        groups = ["Camera_Grp", "Character_Grp", "Setdress_Grp", "Props_Grp", "Sets_Grp"]
        for grp_name in groups:
            if not cmds.objExists(grp_name):
                cmds.group(empty=True, name=grp_name)
                print("Created group: {{}}".format(grp_name))

        # Save scene
        cmds.file(rename="{output_file}")
        cmds.file(save=True, type="mayaAscii")
        print("Saved scene: {output_file}")

        print("=== SUBPROCESS SHOT BUILD COMPLETE ===")
        return True

    except Exception as e:
        print("ERROR in subprocess build: {{}}".format(str(e)))
        return False

if __name__ == "__main__":
    success = build_shot()
    sys.exit(0 if success else 1)
'''.format(
                project=project,
                episode=episode,
                sequence=sequence,
                shot=shot,
                department=department,
                output_file=output_file,
                root_path=self.root_path_edit.text().strip()
            )

            # Write script to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_content)
                script_path = f.name

            self._log("Created subprocess script: {}".format(script_path))

            # Execute subprocess
            self._execute_subprocess_build(script_path, output_file)

        except Exception as e:
            self._log("[ERROR] Failed to create subprocess script: {}".format(str(e)))

    def _execute_subprocess_build(self, script_path, output_file):
        """Execute the subprocess build script."""
        try:
            import subprocess
            import threading

            # Get Maya executable path
            maya_exe = self._get_maya_executable()
            if not maya_exe:
                self._log("[ERROR] Could not find Maya executable")
                return

            # Build command
            cmd = [maya_exe, "-batch", "-script", script_path]

            self._log("Executing subprocess: {}".format(" ".join(cmd)))

            # Execute in thread to avoid blocking UI
            def run_subprocess():
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5 minute timeout

                    if result.returncode == 0:
                        self._log("[OK] SUBPROCESS BUILD SUCCESSFUL")
                        self._log("Output file: {}".format(output_file))
                        if result.stdout:
                            self._log("Subprocess output: {}".format(result.stdout))
                    else:
                        self._log("[ERROR] SUBPROCESS BUILD FAILED")
                        if result.stderr:
                            self._log("Subprocess error: {}".format(result.stderr))
                        if result.stdout:
                            self._log("Subprocess output: {}".format(result.stdout))

                    # Clean up script file
                    try:
                        os.unlink(script_path)
                    except:
                        pass

                except subprocess.TimeoutExpired:
                    self._log("[ERROR] SUBPROCESS BUILD TIMED OUT")
                except Exception as e:
                    self._log("[ERROR] SUBPROCESS EXECUTION ERROR: {}".format(str(e)))

            # Start subprocess in background thread
            thread = threading.Thread(target=run_subprocess)
            thread.daemon = True
            thread.start()

            self._log("[UPDATE] Subprocess started in background...")

        except Exception as e:
            self._log("[ERROR] Failed to execute subprocess: {}".format(str(e)))

    def _get_maya_executable(self):
        """Get Maya executable path."""
        try:
            import maya.cmds as cmds
            import sys
            import os

            # Try to get Maya executable from current process
            if sys.platform == "win32":
                # Windows
                maya_location = os.environ.get("MAYA_LOCATION")
                if maya_location:
                    maya_exe = os.path.join(maya_location, "bin", "maya.exe")
                    if os.path.exists(maya_exe):
                        return maya_exe

                # Fallback: try common locations
                common_paths = [
                    "C:/Program Files/Autodesk/Maya2024/bin/maya.exe",
                    "C:/Program Files/Autodesk/Maya2023/bin/maya.exe",
                    "C:/Program Files/Autodesk/Maya2022/bin/maya.exe",
                ]
                for path in common_paths:
                    if os.path.exists(path):
                        return path
            else:
                # Linux/Mac
                maya_location = os.environ.get("MAYA_LOCATION")
                if maya_location:
                    maya_exe = os.path.join(maya_location, "bin", "maya")
                    if os.path.exists(maya_exe):
                        return maya_exe

            return None

        except Exception as e:
            self._log("[WARNING] Could not determine Maya executable: {}".format(str(e)))
            return None

    def _batch_build_shots(self):
        """Build multiple shots in batch using latest versions."""
        try:
            # Scan for available shots with latest versions
            available_shots = self._scan_available_shots_with_versions()

            if not available_shots:
                self._log("[ERROR] No shots found with cache files")
                return

            # Create batch build dialog with real shot data
            dialog = BatchBuildDialog(self, available_shots)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                shots_to_build = dialog.get_selected_shots()
                department = dialog.get_target_department()
                use_latest = dialog.get_use_latest_version()

                if shots_to_build:
                    self._log("[BATCH] STARTING BATCH BUILD WITH LATEST VERSIONS")
                    self._log("Shots to build: {}".format(len(shots_to_build)))
                    self._log("Target department: {}".format(department))
                    self._log("Use latest versions: {}".format(use_latest))

                    # Ask user for build method to avoid crashes
                    build_method = self._ask_batch_build_method()

                    if build_method == "mel":
                        # RECOMMENDED: Create MEL scripts for Maya batch execution
                        self._create_mel_batch_scripts(shots_to_build, department)
                        self._log("[OK] MEL BATCH SCRIPTS CREATED")
                        self._log("[TOOL] MEL scripts saved - use Maya batch mode to execute")
                        self._log("[INFO] Command: maya -batch -file script.mel")

                    elif build_method == "scripts":
                        # Create Python scripts only
                        for shot_info in shots_to_build:
                            self._batch_build_single_shot(shot_info, department, use_latest)
                        self._log("[OK] PYTHON BATCH SCRIPTS CREATED")
                        self._log("[SCRIPT] Build scripts saved to build_scripts folders")
                        self._log("[INFO] Execute scripts manually in Maya to avoid crashes")

                    elif build_method == "current":
                        # Build in current Maya session (may be slower but safer)
                        self._batch_build_in_current_session(shots_to_build, department)
                        self._log("[OK] BATCH BUILD COMPLETED IN CURRENT SESSION")

                    elif build_method == "cmdline":
                        # Create command line batch file
                        self._create_cmdline_batch(shots_to_build, department)
                        self._log("[OK] COMMAND LINE BATCH FILE CREATED")
                        self._log("[WARNING]  Execute batch file outside of Maya")

                    else:
                        self._log("[INFO] Batch build cancelled by user")
                else:
                    self._log("[INFO] No shots selected for batch build")

        except Exception as e:
            self._log("[ERROR] Batch build failed: {}".format(str(e)))

    def _scan_available_shots_with_versions(self):
        """Scan for available shots and their latest versions."""
        try:
            root = self.root_path_edit.text().strip()
            project = self.project_combo.currentText()

            if not root or not project:
                self._log("[ERROR] Please set root path and select project first")
                return []

            shots_data = []
            scene_path = os.path.join(root, project, "all", "scene")

            if not os.path.exists(scene_path):
                self._log("[WARNING] Scene path does not exist: {}".format(scene_path))
                return []

            # Scan episodes
            for episode in os.listdir(scene_path):
                episode_path = os.path.join(scene_path, episode)
                if not os.path.isdir(episode_path):
                    continue

                # Scan sequences
                for sequence in os.listdir(episode_path):
                    sequence_path = os.path.join(episode_path, sequence)
                    if not os.path.isdir(sequence_path):
                        continue

                    # Scan shots
                    for shot in os.listdir(sequence_path):
                        shot_path = os.path.join(sequence_path, shot)
                        if not os.path.isdir(shot_path):
                            continue

                        # Find latest version for this shot
                        latest_version = self._find_latest_shot_version(shot_path)
                        if latest_version:
                            cache_count = len(latest_version['cache_files'])
                            shots_data.append({
                                'episode': episode,
                                'sequence': sequence,
                                'shot': shot,
                                'version': latest_version['version'],
                                'cache_path': latest_version['cache_path'],
                                'cache_files': latest_version['cache_files'],
                                'cache_count': cache_count
                            })

            self._log("Found {} shots with cache files".format(len(shots_data)))
            return shots_data

        except Exception as e:
            self._log("[ERROR] Failed to scan available shots: {}".format(str(e)))
            return []

    def _find_latest_shot_version(self, shot_path):
        """Find the latest version for a shot."""
        try:
            anim_path = os.path.join(shot_path, "anim", "publish")
            if not os.path.exists(anim_path):
                return None

            # Find all version directories
            versions = []
            for item in os.listdir(anim_path):
                version_path = os.path.join(anim_path, item)
                if os.path.isdir(version_path) and item.startswith('v'):
                    try:
                        version_num = int(item[1:])  # Remove 'v' prefix
                        versions.append((version_num, item, version_path))
                    except ValueError:
                        continue

            if not versions:
                return None

            # Get latest version
            versions.sort(reverse=True)  # Sort by version number, highest first
            latest_version_num, latest_version_dir, latest_version_path = versions[0]

            # Find cache files in latest version
            cache_files = []
            if os.path.exists(latest_version_path):
                for filename in os.listdir(latest_version_path):
                    if filename.endswith('.abc'):
                        cache_files.append(filename)

            if cache_files:
                return {
                    'version': latest_version_dir,
                    'version_num': latest_version_num,
                    'cache_path': latest_version_path,
                    'cache_files': cache_files
                }

            return None

        except Exception as e:
            self._log("[WARNING] Failed to find latest version for shot: {}".format(str(e)))
            return None

    def _batch_build_single_shot(self, shot_info, department, use_latest):
        """Build a single shot in batch mode."""
        try:
            episode = shot_info['episode']
            sequence = shot_info['sequence']
            shot = shot_info['shot']
            version = shot_info['version']
            cache_path = shot_info['cache_path']

            self._log("[COMPLETE] BATCH BUILDING: {}_{}_{} ({}), {} cache files".format(
                episode, sequence, shot, version, shot_info['cache_count']))

            # Create subprocess build for this shot
            root = self.root_path_edit.text().strip()
            project = self.project_combo.currentText()

            # Build output path
            output_path = os.path.join(root, project, "all", "scene", episode, sequence, shot, department, "work")
            if not os.path.exists(output_path):
                os.makedirs(output_path)

            # Generate standardized filename with metadata
            scene_filename = self._get_standardized_filename(episode, sequence, shot, department, version, add_timestamp=True)
            scene_filepath = os.path.join(output_path, scene_filename)

            # Create and execute subprocess build
            self._create_batch_subprocess_build(shot_info, department, scene_filepath)

        except Exception as e:
            self._log("[ERROR] Failed to batch build shot {}_{}_{}: {}".format(
                shot_info.get('episode', '?'), shot_info.get('sequence', '?'),
                shot_info.get('shot', '?'), str(e)))

    def _create_batch_subprocess_build(self, shot_info, department, output_file):
        """Create batch build script (safer approach without subprocess)."""
        try:
            # Instead of subprocess, create a batch script that can be run later
            # This avoids Maya crashes from threading/subprocess issues

            episode = shot_info['episode']
            sequence = shot_info['sequence']
            shot = shot_info['shot']
            version = shot_info['version']

            # Create batch script content
            script_content = '''# Batch Build Script for {episode}_{sequence}_{shot} ({version})
# Target Department: {department}
# Output: {output_file}
# Cache Path: {cache_path}
# Cache Files: {cache_files}

import maya.cmds as cmds
import os

def build_shot():
    """Build shot with cache files."""
    try:
        print("=== BUILDING {episode}_{sequence}_{shot} ({version}) ===")

        # Create new scene
        cmds.file(new=True, force=True)

        # Create scene groups
        groups = ["Camera_Grp", "Character_Grp", "Setdress_Grp", "Props_Grp", "Sets_Grp"]
        for grp_name in groups:
            if not cmds.objExists(grp_name):
                cmds.group(empty=True, name=grp_name)
                print("Created group: {{}}".format(grp_name))

        # Process cache files
        cache_path = r"{cache_path}"
        cache_files = {cache_files}

        for cache_file in cache_files:
            try:
                full_path = os.path.join(cache_path, cache_file)
                if os.path.exists(full_path):
                    print("Processing cache: {{}}".format(cache_file))
                    # TODO: Add actual cache processing logic here
                    # This would include the same logic as the main build process
                else:
                    print("WARNING: Cache file not found: {{}}".format(full_path))
            except Exception as e:
                print("ERROR processing {{}}: {{}}".format(cache_file, str(e)))

        # Save scene
        output_dir = os.path.dirname(r"{output_file}")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        cmds.file(rename=r"{output_file}")
        cmds.file(save=True, type="mayaAscii")
        print("Saved scene: {output_file}")

        print("=== BUILD COMPLETE ===")
        return True

    except Exception as e:
        print("ERROR in build: {{}}".format(str(e)))
        return False

# Execute the build
if __name__ == "__main__":
    build_shot()
'''.format(
                episode=episode,
                sequence=sequence,
                shot=shot,
                version=version,
                department=department,
                cache_files=shot_info['cache_files'],
                cache_path=shot_info['cache_path'].replace('\\', '\\\\'),  # Escape backslashes
                output_file=output_file.replace('\\', '\\\\')  # Escape backslashes
            )

            # Save script to a file for manual execution or later processing
            script_dir = os.path.join(os.path.dirname(output_file), "build_scripts")
            if not os.path.exists(script_dir):
                os.makedirs(script_dir)

            script_filename = "build_{}_{}_{}_{}_{}.py".format(
                episode, sequence, shot, version, department)
            script_path = os.path.join(script_dir, script_filename)

            with open(script_path, 'w') as f:
                f.write(script_content)

            self._log("[OK] Created build script: {}".format(script_path))
            self._log("   Shot: {}_{}_{} ({})".format(episode, sequence, shot, version))
            self._log("   Output: {}".format(output_file))

            # For now, just create the script - user can execute manually
            # This avoids Maya crashes from subprocess execution

        except Exception as e:
            self._log("[ERROR] Failed to create batch build script: {}".format(str(e)))

    def _ask_batch_build_method(self):
        """Ask user which batch build method to use."""
        try:
            from PySide2 import QtWidgets

            msg = QtWidgets.QMessageBox()
            msg.setWindowTitle("Batch Build Method")
            msg.setText("Choose batch build method:")
            msg.setInformativeText(
                "[TOOL] MEL Scripts: Create MEL scripts for Maya batch execution (RECOMMENDED)\n"
                "[SCRIPT] Python Scripts: Create Python scripts for manual execution\n"
                "[UPDATE] Current Session: Build all shots in current Maya session (slower)\n"
                "[WARNING]  Command Line: Generate command line batch file (external)"
            )

            mel_btn = msg.addButton("MEL Scripts (Recommended)", QtWidgets.QMessageBox.AcceptRole)
            scripts_btn = msg.addButton("Python Scripts", QtWidgets.QMessageBox.AcceptRole)
            current_btn = msg.addButton("Current Session", QtWidgets.QMessageBox.AcceptRole)
            cmdline_btn = msg.addButton("Command Line Batch", QtWidgets.QMessageBox.AcceptRole)
            cancel_btn = msg.addButton("Cancel", QtWidgets.QMessageBox.RejectRole)

            msg.setDefaultButton(mel_btn)
            msg.exec_()

            if msg.clickedButton() == mel_btn:
                return "mel"
            elif msg.clickedButton() == scripts_btn:
                return "scripts"
            elif msg.clickedButton() == current_btn:
                return "current"
            elif msg.clickedButton() == cmdline_btn:
                return "cmdline"
            else:
                return "cancel"

        except Exception as e:
            self._log("[WARNING] Could not show dialog: {}".format(str(e)))
            return "mel"  # Default to safest option

    def _batch_build_in_current_session(self, shots_to_build, department):
        """Build multiple shots in current Maya session (safer but slower)."""
        try:
            self._log("[UPDATE] Building {} shots in current Maya session...".format(len(shots_to_build)))

            for i, shot_info in enumerate(shots_to_build, 1):
                try:
                    episode = shot_info['episode']
                    sequence = shot_info['sequence']
                    shot = shot_info['shot']
                    version = shot_info['version']

                    self._log("[COMPLETE] [{}/{}] Building: {}_{}_{} ({})".format(
                        i, len(shots_to_build), episode, sequence, shot, version))

                    # Create new scene for this shot
                    cmds.file(new=True, force=True)

                    # Create scene groups
                    groups = ["Camera_Grp", "Character_Grp", "Setdress_Grp", "Props_Grp", "Sets_Grp"]
                    for grp_name in groups:
                        if not cmds.objExists(grp_name):
                            cmds.group(empty=True, name=grp_name)

                    # Build output path
                    root = self.root_path_edit.text().strip()
                    project = self.project_combo.currentText()
                    output_path = os.path.join(root, project, "all", "scene", episode, sequence, shot, department, "work")

                    if not os.path.exists(output_path):
                        os.makedirs(output_path)

                    # Generate standardized filename
                    scene_filename = self._get_standardized_filename(episode, sequence, shot, department, version, add_timestamp=True)
                    scene_filepath = os.path.join(output_path, scene_filename)

                    # TODO: Add actual shot build logic here
                    # For now, just save empty scene with groups

                    # Save scene with metadata
                    cache_files = shot_info.get('cache_files', [])
                    self._save_scene_with_metadata(scene_filepath, episode, sequence, shot, department, version, cache_files)

                    self._log("[OK] [{}/{}] Saved: {}".format(i, len(shots_to_build), scene_filename))

                except Exception as e:
                    self._log("[ERROR] [{}/{}] Failed to build {}_{}_{}: {}".format(
                        i, len(shots_to_build),
                        shot_info.get('episode', '?'), shot_info.get('sequence', '?'),
                        shot_info.get('shot', '?'), str(e)))

            self._log("[SUCCESS] Batch build in current session completed")

        except Exception as e:
            self._log("[ERROR] Batch build in current session failed: {}".format(str(e)))

    def _add_maya_metadata(self, episode, sequence, shot, department, version, cache_files=None):
        """Add metadata to Maya scene for batch build tracking."""
        try:
            import datetime

            # Create metadata as Maya file info
            metadata = {
                "LRC_Episode": episode,
                "LRC_Sequence": sequence,
                "LRC_Shot": shot,
                "LRC_Department": department,
                "LRC_Version": version,
                "LRC_BuildDate": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "LRC_BuildTool": "LRC Toolbox v2.0",
                "LRC_BuildType": "Batch Build",
                "LRC_CacheCount": str(len(cache_files)) if cache_files else "0",
                "LRC_Project": self.project_combo.currentText() if hasattr(self, 'project_combo') else "Unknown"
            }

            # Add cache file list if provided
            if cache_files:
                metadata["LRC_CacheFiles"] = "|".join(cache_files)

            # Set Maya file info
            for key, value in metadata.items():
                cmds.fileInfo(key, value)
                self._log("Added metadata: {} = {}".format(key, value))

            # Also create a metadata node for easy querying
            if not cmds.objExists("LRC_BuildMetadata"):
                metadata_node = cmds.createNode("network", name="LRC_BuildMetadata")

                # Add custom attributes
                for key, value in metadata.items():
                    attr_name = key.replace("LRC_", "").lower()
                    if not cmds.attributeQuery(attr_name, node=metadata_node, exists=True):
                        cmds.addAttr(metadata_node, longName=attr_name, dataType="string")
                        cmds.setAttr("{}.{}".format(metadata_node, attr_name), value, type="string")

                self._log("Created metadata node: LRC_BuildMetadata")

            return True

        except Exception as e:
            self._log("[WARNING] Failed to add Maya metadata: {}".format(str(e)))
            return False

    def _get_standardized_filename(self, episode, sequence, shot, department, version, add_timestamp=True):
        """Generate standardized filename: {ep}_{seq}_{shot}_{department}_{version}[_{timestamp}].ma"""
        try:
            # Base filename: {ep}_{seq}_{shot}_{department}_{version}
            base_filename = "{}_{}_{}_{}_{}".format(episode, sequence, shot, department, version)

            # Add timestamp if requested
            if add_timestamp:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = "{}_{}.ma".format(base_filename, timestamp)
            else:
                filename = "{}.ma".format(base_filename)

            return filename

        except Exception as e:
            self._log("[ERROR] Failed to generate filename: {}".format(str(e)))
            return "unknown_shot.ma"

    def _save_scene_with_metadata(self, filepath, episode, sequence, shot, department, version, cache_files=None):
        """Save Maya scene with metadata."""
        try:
            # Add metadata before saving
            self._add_maya_metadata(episode, sequence, shot, department, version, cache_files)

            # Ensure output directory exists
            output_dir = os.path.dirname(filepath)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Save scene
            cmds.file(rename=filepath)
            cmds.file(save=True, type="mayaAscii")

            self._log("[OK] Saved scene with metadata: {}".format(os.path.basename(filepath)))
            return True

        except Exception as e:
            self._log("[ERROR] Failed to save scene with metadata: {}".format(str(e)))
            return False

    def _create_mel_batch_scripts(self, shots_to_build, department):
        """Create MEL scripts for Maya batch execution (RECOMMENDED for batch processing)."""
        try:
            import datetime
            self._log("[TOOL] Creating MEL batch scripts for {} shots...".format(len(shots_to_build)))

            root = self.root_path_edit.text().strip()
            project = self.project_combo.currentText()

            # Create master batch directory
            batch_dir = os.path.join(root, project, "batch_builds", department)
            if not os.path.exists(batch_dir):
                os.makedirs(batch_dir)

            master_mel_script = []
            master_mel_script.append("// LRC Toolbox v2.0 - Batch Build MEL Script")
            master_mel_script.append("// Department: {}".format(department))
            master_mel_script.append("// Generated: {}".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            master_mel_script.append("// Shots: {}".format(len(shots_to_build)))
            master_mel_script.append("")

            for i, shot_info in enumerate(shots_to_build, 1):
                episode = shot_info['episode']
                sequence = shot_info['sequence']
                shot = shot_info['shot']
                version = shot_info['version']
                cache_files = shot_info.get('cache_files', [])

                # Generate output path
                output_path = os.path.join(root, project, "all", "scene", episode, sequence, shot, department, "work")
                scene_filename = self._get_standardized_filename(episode, sequence, shot, department, version, add_timestamp=True)
                scene_filepath = os.path.join(output_path, scene_filename)

                # Add MEL commands for this shot
                master_mel_script.append("// === SHOT {}/{}: {}_{}_{} ({}) ===".format(i, len(shots_to_build), episode, sequence, shot, version))
                master_mel_script.append("print \"Building shot {}/{}: {}_{}_{} ({})\\n\";".format(i, len(shots_to_build), episode, sequence, shot, version))

                # Create new scene
                master_mel_script.append("file -new -force;")

                # Create groups
                groups = ["Camera_Grp", "Character_Grp", "Setdress_Grp", "Props_Grp", "Sets_Grp"]
                for grp in groups:
                    master_mel_script.append("if (!`objExists \"{}\"`) group -empty -name \"{}\";".format(grp, grp))

                # Add metadata as file info
                master_mel_script.append("fileInfo \"LRC_Episode\" \"{}\";".format(episode))
                master_mel_script.append("fileInfo \"LRC_Sequence\" \"{}\";".format(sequence))
                master_mel_script.append("fileInfo \"LRC_Shot\" \"{}\";".format(shot))
                master_mel_script.append("fileInfo \"LRC_Department\" \"{}\";".format(department))
                master_mel_script.append("fileInfo \"LRC_Version\" \"{}\";".format(version))
                master_mel_script.append("fileInfo \"LRC_BuildTool\" \"LRC Toolbox v2.0\";")
                master_mel_script.append("fileInfo \"LRC_BuildType\" \"MEL Batch Build\";")
                master_mel_script.append("fileInfo \"LRC_CacheCount\" \"{}\";".format(len(cache_files)))

                # TODO: Add cache processing commands here
                # master_mel_script.append("// Process cache files:")
                # for cache_file in cache_files:
                #     cache_path = os.path.join(shot_info['cache_path'], cache_file)
                #     master_mel_script.append("// AbcImport -mode import \"{}\";".format(cache_path.replace('\\', '/')))

                # Create output directory and save
                master_mel_script.append("sysFile -makeDir \"{}\";".format(output_path.replace('\\', '/')))
                master_mel_script.append("file -rename \"{}\";".format(scene_filepath.replace('\\', '/')))
                master_mel_script.append("file -save -type \"mayaAscii\";")
                master_mel_script.append("print \"Saved: {}\\n\";".format(scene_filename))
                master_mel_script.append("")

            # Add completion message
            master_mel_script.append("print \"=== BATCH BUILD COMPLETE ===\\n\";")
            master_mel_script.append("print \"Built {} shots for {} department\\n\";".format(len(shots_to_build), department))

            # Save master MEL script
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            mel_filename = "batch_build_{}_{}.mel".format(department, timestamp)
            mel_filepath = os.path.join(batch_dir, mel_filename)

            with open(mel_filepath, 'w') as f:
                f.write('\n'.join(master_mel_script))

            self._log("[OK] Created MEL batch script: {}".format(mel_filepath))
            self._log("[TOOL] Execute with: maya -batch -file \"{}\"".format(mel_filepath))

            # Also create a Windows batch file for easy execution
            bat_content = [
                "@echo off",
                "echo Starting Maya batch build...",
                "echo Department: {}".format(department),
                "echo Shots: {}".format(len(shots_to_build)),
                "echo.",
                "maya -batch -file \"{}\"".format(mel_filepath),
                "echo.",
                "echo Batch build completed!",
                "pause"
            ]

            bat_filename = "run_batch_build_{}_{}.bat".format(department, timestamp)
            bat_filepath = os.path.join(batch_dir, bat_filename)

            with open(bat_filepath, 'w') as f:
                f.write('\n'.join(bat_content))

            self._log("[OK] Created batch runner: {}".format(bat_filepath))
            self._log("[INFO] Double-click the .bat file to run batch build")

        except Exception as e:
            self._log("[ERROR] Failed to create MEL batch scripts: {}".format(str(e)))

    def _create_cmdline_batch(self, shots_to_build, department):
        """Create command line batch file for external execution."""
        try:
            import datetime
            self._log("[WARNING]  Creating command line batch for {} shots...".format(len(shots_to_build)))

            root = self.root_path_edit.text().strip()
            project = self.project_combo.currentText()

            # Create batch directory
            batch_dir = os.path.join(root, project, "batch_builds", department)
            if not os.path.exists(batch_dir):
                os.makedirs(batch_dir)

            # Create individual MEL scripts for each shot
            mel_scripts = []

            for i, shot_info in enumerate(shots_to_build, 1):
                episode = shot_info['episode']
                sequence = shot_info['sequence']
                shot = shot_info['shot']
                version = shot_info['version']

                # Create individual MEL script for this shot
                shot_mel_filename = "build_{}_{}_{}_{}_{}.mel".format(episode, sequence, shot, department, version)
                shot_mel_filepath = os.path.join(batch_dir, shot_mel_filename)

                # Generate output path
                output_path = os.path.join(root, project, "all", "scene", episode, sequence, shot, department, "work")
                scene_filename = self._get_standardized_filename(episode, sequence, shot, department, version, add_timestamp=True)
                scene_filepath = os.path.join(output_path, scene_filename)

                # MEL script content for this shot
                mel_content = [
                    "// LRC Toolbox v2.0 - Individual Shot Build",
                    "// Shot: {}_{}_{} ({})".format(episode, sequence, shot, version),
                    "// Department: {}".format(department),
                    "",
                    "print \"Building shot: {}_{}_{} ({})\\n\";".format(episode, sequence, shot, version),
                    "",
                    "// Create new scene",
                    "file -new -force;",
                    "",
                    "// Create groups",
                    "if (!`objExists \"Camera_Grp\"`) group -empty -name \"Camera_Grp\";",
                    "if (!`objExists \"Character_Grp\"`) group -empty -name \"Character_Grp\";",
                    "if (!`objExists \"Setdress_Grp\"`) group -empty -name \"Setdress_Grp\";",
                    "if (!`objExists \"Props_Grp\"`) group -empty -name \"Props_Grp\";",
                    "if (!`objExists \"Sets_Grp\"`) group -empty -name \"Sets_Grp\";",
                    "",
                    "// Add metadata",
                    "fileInfo \"LRC_Episode\" \"{}\";".format(episode),
                    "fileInfo \"LRC_Sequence\" \"{}\";".format(sequence),
                    "fileInfo \"LRC_Shot\" \"{}\";".format(shot),
                    "fileInfo \"LRC_Department\" \"{}\";".format(department),
                    "fileInfo \"LRC_Version\" \"{}\";".format(version),
                    "fileInfo \"LRC_BuildTool\" \"LRC Toolbox v2.0\";",
                    "fileInfo \"LRC_BuildType\" \"Command Line Batch\";",
                    "",
                    "// TODO: Add cache processing here",
                    "",
                    "// Save scene",
                    "sysFile -makeDir \"{}\";".format(output_path.replace('\\', '/')),
                    "file -rename \"{}\";".format(scene_filepath.replace('\\', '/')),
                    "file -save -type \"mayaAscii\";",
                    "print \"Saved: {}\\n\";".format(scene_filename),
                    "",
                    "print \"Shot build complete\\n\";"
                ]

                # Write individual MEL script
                with open(shot_mel_filepath, 'w') as f:
                    f.write('\n'.join(mel_content))

                mel_scripts.append((shot_mel_filepath, "{}_{}_{} ({})".format(episode, sequence, shot, version)))

            # Create master batch file
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            bat_filename = "cmdline_batch_{}_{}.bat".format(department, timestamp)
            bat_filepath = os.path.join(batch_dir, bat_filename)

            bat_content = [
                "@echo off",
                "echo ========================================",
                "echo LRC Toolbox v2.0 - Command Line Batch Build",
                "echo Department: {}".format(department),
                "echo Shots: {}".format(len(shots_to_build)),
                "echo ========================================",
                "echo.",
                ""
            ]

            # Add commands for each shot
            for i, (mel_script, shot_name) in enumerate(mel_scripts, 1):
                bat_content.extend([
                    "echo [{}/{}] Building: {}".format(i, len(mel_scripts), shot_name),
                    "maya -batch -file \"{}\"".format(mel_script),
                    "if errorlevel 1 (",
                    "    echo ERROR: Failed to build {}".format(shot_name),
                    ") else (",
                    "    echo SUCCESS: Built {}".format(shot_name),
                    ")",
                    "echo."
                ])

            bat_content.extend([
                "",
                "echo ========================================",
                "echo Batch build completed!",
                "echo Check output directories for results.",
                "echo ========================================",
                "pause"
            ])

            # Write batch file
            with open(bat_filepath, 'w') as f:
                f.write('\n'.join(bat_content))

            self._log("[OK] Created command line batch: {}".format(bat_filepath))
            self._log("[OK] Created {} individual MEL scripts".format(len(mel_scripts)))
            self._log("[WARNING]  Execute batch file OUTSIDE of Maya")
            self._log("[INFO] Close Maya before running the batch file")

        except Exception as e:
            self._log("[ERROR] Failed to create command line batch: {}".format(str(e)))


class BatchBuildDialog(QtWidgets.QDialog):
    """Dialog for selecting shots to build in batch with latest versions."""

    def __init__(self, parent=None, available_shots=None):
        super(BatchBuildDialog, self).__init__(parent)
        self.setWindowTitle("Batch Build Shots - Latest Versions")
        self.setModal(True)
        self.resize(800, 500)
        self.available_shots = available_shots or []

        layout = QtWidgets.QVBoxLayout(self)

        # Instructions
        instructions = QtWidgets.QLabel("Select shots to build in batch (using latest versions):")
        instructions.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(instructions)

        # Options layout
        options_layout = QtWidgets.QHBoxLayout()

        # Department selection
        options_layout.addWidget(QtWidgets.QLabel("Target Department:"))
        self.dept_combo = QtWidgets.QComboBox()
        self.dept_combo.addItems(["anim", "lighting", "comp", "fx", "layout"])
        self.dept_combo.setCurrentText("lighting")
        options_layout.addWidget(self.dept_combo)

        options_layout.addWidget(QtWidgets.QLabel("  "))

        # Latest version checkbox
        self.use_latest_checkbox = QtWidgets.QCheckBox("Use Latest Versions")
        self.use_latest_checkbox.setChecked(True)
        self.use_latest_checkbox.setStyleSheet("font-weight: bold; color: #2196F3;")
        options_layout.addWidget(self.use_latest_checkbox)

        options_layout.addStretch()
        layout.addLayout(options_layout)

        # Shots table with version info
        self.shots_table = QtWidgets.QTableWidget(0, 6)
        self.shots_table.setHorizontalHeaderLabels(["Select", "Episode", "Sequence", "Shot", "Version", "Cache Files"])
        self.shots_table.horizontalHeader().setStretchLastSection(True)
        self.shots_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self.shots_table.setColumnWidth(0, 60)  # Select column
        layout.addWidget(self.shots_table)

        # Populate with real shot data
        self._populate_shots_table()

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()

        select_all_btn = QtWidgets.QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all)
        button_layout.addWidget(select_all_btn)

        select_none_btn = QtWidgets.QPushButton("Select None")
        select_none_btn.clicked.connect(self._select_none)
        button_layout.addWidget(select_none_btn)

        button_layout.addStretch()

        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        build_btn = QtWidgets.QPushButton("Build Selected")
        build_btn.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
        build_btn.clicked.connect(self.accept)
        button_layout.addWidget(build_btn)

        layout.addLayout(button_layout)

    def _populate_shots_table(self):
        """Populate shots table with available shots and their latest versions."""
        if not self.available_shots:
            # Show message if no shots found
            row = self.shots_table.rowCount()
            self.shots_table.insertRow(row)

            # Empty checkbox
            checkbox = QtWidgets.QCheckBox()
            checkbox.setEnabled(False)
            self.shots_table.setCellWidget(row, 0, checkbox)

            # Message
            self.shots_table.setItem(row, 1, QtWidgets.QTableWidgetItem("No shots found"))
            self.shots_table.setItem(row, 2, QtWidgets.QTableWidgetItem(""))
            self.shots_table.setItem(row, 3, QtWidgets.QTableWidgetItem(""))
            self.shots_table.setItem(row, 4, QtWidgets.QTableWidgetItem(""))
            self.shots_table.setItem(row, 5, QtWidgets.QTableWidgetItem("Check root path and project"))
            return

        # Populate with real shot data
        for shot_data in self.available_shots:
            row = self.shots_table.rowCount()
            self.shots_table.insertRow(row)

            # Checkbox
            checkbox = QtWidgets.QCheckBox()
            self.shots_table.setCellWidget(row, 0, checkbox)

            # Shot info with version data
            self.shots_table.setItem(row, 1, QtWidgets.QTableWidgetItem(shot_data['episode']))
            self.shots_table.setItem(row, 2, QtWidgets.QTableWidgetItem(shot_data['sequence']))
            self.shots_table.setItem(row, 3, QtWidgets.QTableWidgetItem(shot_data['shot']))
            self.shots_table.setItem(row, 4, QtWidgets.QTableWidgetItem(shot_data['version']))
            self.shots_table.setItem(row, 5, QtWidgets.QTableWidgetItem("{} files".format(shot_data['cache_count'])))

        self.shots_table.resizeColumnsToContents()

    def _select_all(self):
        """Select all shots."""
        for row in range(self.shots_table.rowCount()):
            checkbox = self.shots_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)

    def _select_none(self):
        """Deselect all shots."""
        for row in range(self.shots_table.rowCount()):
            checkbox = self.shots_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)

    def get_selected_shots(self):
        """Get list of selected shots with their version data."""
        selected_shots = []
        for row in range(self.shots_table.rowCount()):
            checkbox = self.shots_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                # Find the corresponding shot data from available_shots
                episode = self.shots_table.item(row, 1).text()
                sequence = self.shots_table.item(row, 2).text()
                shot = self.shots_table.item(row, 3).text()

                # Find matching shot data
                for shot_data in self.available_shots:
                    if (shot_data['episode'] == episode and
                        shot_data['sequence'] == sequence and
                        shot_data['shot'] == shot):
                        selected_shots.append(shot_data)
                        break
        return selected_shots

    def get_target_department(self):
        """Get selected target department."""
        return self.dept_combo.currentText()

    def get_use_latest_version(self):
        """Get whether to use latest versions."""
        return self.use_latest_checkbox.isChecked()

    def _find_geometry_in_namespace(self, namespace, suffix):
        """Find geometry transforms in namespace with given suffix."""
        try:
            geos = cmds.ls("{}:*{}".format(namespace, suffix), type="transform") or []
            return geos[0] if geos else None
        except Exception:
            return None

# =============================================================================
# TAB 2: Place3D Linker (copy TRS + parent/scale constrain)
# =============================================================================

def _delete_existing_constraints_on(node):
    cons = []
    for ctype in ("parentConstraint", "scaleConstraint"):
        cons += cmds.listRelatives(node, type=ctype, parent=False) or []
        cons += cmds.listConnections(node, s=True, d=False, type=ctype) or []
    for c in set(cons):
        try:
            cmds.delete(c)
        except Exception:
            pass

def _snap_trs_world(src_xform, dst_node, dry_run=False):
    """Copy TRS from src transform -> dst place3dTexture (world T/R, local S)."""
    _unlock_trs(dst_node)
    t = cmds.xform(src_xform, q=True, ws=True, t=True)
    r = cmds.xform(src_xform, q=True, ws=True, ro=True)
    s = cmds.getAttr(src_xform + ".scale")[0]
    if dry_run:
        return "would-set T{} R{} S{}".format(
            [round(v,3) for v in t], [round(v,3) for v in r], [round(v,3) for v in s])
    try:
        cmds.xform(dst_node, ws=True, t=t)
        cmds.xform(dst_node, ws=True, ro=r)
        cmds.setAttr(dst_node + ".scale", *s, type="double3")
        return "snapped TRS"
    except Exception as e:
        return "error: {}".format(e)

def _parent_and_scale_constrain(src_xform, dst_node, force=False, dry_run=False):
    if dry_run:
        return "would parentConstraint (no offset) + scaleConstraint -mo"
    try:
        if force:
            _delete_existing_constraints_on(dst_node)
        if not cmds.listRelatives(dst_node, type="parentConstraint"):
            cmds.parentConstraint(src_xform, dst_node, mo=False,
                                  name="EE_{}_pcon".format(_short(dst_node)))
        if not cmds.listRelatives(dst_node, type="scaleConstraint"):
            cmds.scaleConstraint(src_xform, dst_node, mo=True,
                                 name="EE_{}_scon".format(_short(dst_node)))
        return "constrained"
    except Exception as e:
        return "error: {}".format(e)

def _matrix_transfer_transform(src_xform, dst_node, force=False, dry_run=False):
    """
    Transfer transform from src to dst using matrix decomposition.

    This is an alternative to constraint-based linking that uses Maya's
    decomposeMatrix node for cleaner, more performant connections.

    Method:
    1. Create decomposeMatrix node
    2. Connect src_xform.worldMatrix[0] → decomposeMatrix.inputMatrix
    3. Connect decomposeMatrix outputs → dst_node (translate, rotate, scale, shear)

    Args:
        src_xform (str): Source transform node (e.g., "CHAR_Kit_001:Body_Grp")
        dst_node (str): Destination place3dTexture node (e.g., "CHAR_Kit_001_shade:Body_Place3dTexture")
        force (bool): If True, remove existing matrix connections before creating new ones
        dry_run (bool): If True, only report what would be done without making changes

    Returns:
        str: Status message ("matrix-linked", "error: ...", etc.)

    Example:
        result = _matrix_transfer_transform("CHAR_Kit_001:Body_Grp",
                                           "CHAR_Kit_001_shade:Body_Place3dTexture")
        # Result: "matrix-linked"
    """
    if dry_run:
        return "would create decomposeMatrix connection"

    try:
        # Cleanup existing connections if force is enabled
        if force:
            _delete_existing_matrix_connections(dst_node)

        # Unlock transform attributes on destination node
        _unlock_trs(dst_node)

        # Check if destination node already has a decomposeMatrix connection
        existing_decomp = None
        for attr in ["translate", "rotate", "scale"]:
            connections = cmds.listConnections(
                "{}.{}".format(dst_node, attr),
                source=True, destination=False, type="decomposeMatrix"
            ) or []
            if connections:
                existing_decomp = connections[0]
                break

        if existing_decomp and not force:
            # Check if it's connected to the correct source
            input_connections = cmds.listConnections(
                "{}.inputMatrix".format(existing_decomp),
                source=True, destination=False, plugs=True
            ) or []

            expected_connection = "{}.worldMatrix[0]".format(src_xform)
            if expected_connection in input_connections:
                return "matrix connection already exists (correct)"
            else:
                return "matrix connection already exists but wrong source (use force=True to replace)"

        # If force=True, delete existing decomposeMatrix connection
        if existing_decomp and force:
            cmds.delete(existing_decomp)

        # Create decomposeMatrix node with UNIQUE name per asset namespace
        # Include full namespace path to ensure each asset has its own decomposeMatrix node
        # Replace colons with underscores to create valid Maya node names
        # Example: CHAR_Kit_001_shade:Body_Place3dTexture -> EE_CHAR_Kit_001_shade_Body_Place3dTexture_decomp
        decomp_name = "EE_{}_decomp".format(dst_node.replace(":", "_"))

        # Verify the name doesn't already exist (shouldn't happen if naming is correct)
        if cmds.objExists(decomp_name):
            # This shouldn't happen with unique namespace-based naming
            # But if it does, it means there's a leftover node from previous build
            if force:
                cmds.delete(decomp_name)
            else:
                return "error: decomposeMatrix node '{}' already exists but not connected to destination (use force=True)".format(decomp_name)

        # Create the decomposeMatrix node with unique name
        decomp = cmds.createNode("decomposeMatrix", name=decomp_name)

        # Verify Maya didn't rename the node (it shouldn't with unique names)
        if decomp != decomp_name:
            return "error: Maya renamed decomposeMatrix node from '{}' to '{}' (name collision)".format(decomp_name, decomp)

        # Connect worldMatrix[0] from source to inputMatrix of decomposeMatrix
        cmds.connectAttr(
            "{}.worldMatrix[0]".format(src_xform),
            "{}.inputMatrix".format(decomp),
            force=True
        )

        # Connect decomposeMatrix outputs to destination transform attributes
        cmds.connectAttr(
            "{}.outputTranslate".format(decomp),
            "{}.translate".format(dst_node),
            force=True
        )
        cmds.connectAttr(
            "{}.outputRotate".format(decomp),
            "{}.rotate".format(dst_node),
            force=True
        )
        cmds.connectAttr(
            "{}.outputScale".format(decomp),
            "{}.scale".format(dst_node),
            force=True
        )
        cmds.connectAttr(
            "{}.outputShear".format(decomp),
            "{}.shear".format(dst_node),
            force=True
        )

        return "matrix-linked"

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return "error: {} | Details: {}".format(str(e), error_details.split('\n')[-2])

def _delete_existing_matrix_connections(node):
    """
    Remove existing decomposeMatrix connections from a node.

    Searches for decomposeMatrix nodes connected to the node's transform
    attributes (translate, rotate, scale, shear) and deletes them.

    Args:
        node (str): Node to clean up (e.g., "CHAR_Kit_001_shade:Body_Place3dTexture")

    Example:
        _delete_existing_matrix_connections("CHAR_Kit_001_shade:Body_Place3dTexture")
    """
    try:
        # Find all connections to transform attributes
        attrs_to_check = ["translate", "rotate", "scale", "shear"]
        decomp_nodes = set()

        for attr in attrs_to_check:
            full_attr = "{}.{}".format(node, attr)
            if cmds.objExists(full_attr):
                # Get incoming connections
                connections = cmds.listConnections(full_attr, source=True, destination=False, plugs=False) or []
                for conn in connections:
                    # Check if it's a decomposeMatrix node
                    if cmds.nodeType(conn) == "decomposeMatrix":
                        decomp_nodes.add(conn)

        # Delete all found decomposeMatrix nodes
        for decomp in decomp_nodes:
            if cmds.objExists(decomp):
                cmds.delete(decomp)

    except Exception as e:
        # Silently fail - this is a cleanup function
        pass

def _connect_shading_attributes(geo_ns, shader_ns, dry_run=False):
    """Connect animation cache attributes from ShadingAttr_Grp to shader namespace.

    Connects: geo_ns:ShadingAttr_Grp.snow__{attrName} -> shader_ns:{attrName}.default
    Example: CHAR_Kit_001:ShadingAttr_Grp.snow__Eyelid_R_buffer -> CHAR_Kit_001_shade:Eyelid_R_buffer.default
    """
    results = []

    # Find ShadingAttr_Grp in geometry namespace
    shading_grp = "{}:ShadingAttr_Grp".format(geo_ns)
    if not cmds.objExists(shading_grp):
        return ["No ShadingAttr_Grp found in {}".format(geo_ns)]

    # Get all attributes starting with "snow__" on ShadingAttr_Grp
    try:
        all_attrs = cmds.listAttr(shading_grp, userDefined=True) or []
        snow_attrs = [attr for attr in all_attrs if attr.startswith("snow__")]

        if not snow_attrs:
            return ["No snow__ attributes found on {}".format(shading_grp)]

        for snow_attr in snow_attrs:
            # Extract target attribute name (remove "snow__" prefix)
            target_attr = snow_attr[6:]  # Remove "snow__" (6 characters)

            # Build source and target attribute paths
            source_attr = "{}.{}".format(shading_grp, snow_attr)
            target_attr_path = "{}:{}.default".format(shader_ns, target_attr)

            if dry_run:
                results.append("would-connect {} -> {}".format(source_attr, target_attr_path))
                continue

            # Check if target attribute exists
            if not cmds.objExists(target_attr_path):
                results.append("target missing: {}".format(target_attr_path))
                continue

            # Check if connection already exists
            existing_connections = cmds.listConnections(source_attr, destination=True, plugs=True) or []
            if target_attr_path in existing_connections:
                results.append("already connected: {} -> {}".format(source_attr, target_attr_path))
                continue

            # Create the connection
            try:
                cmds.connectAttr(source_attr, target_attr_path, force=True)
                results.append("// Result: Connected {} to {}. //".format(source_attr, target_attr_path))
            except Exception as e:
                results.append("error connecting {} -> {}: {}".format(source_attr, target_attr_path, str(e)))

        return results

    except Exception as e:
        return ["error listing attributes on {}: {}".format(shading_grp, str(e))]

def _find_place3d_pairs_by_place(shader_ns, geo_ns, place_suffix, geo_suffix, allow_fuzzy=True):
    """Key from place3dTexture (shader NS); match geo transform (geo NS)."""
    pairs = []
    places = cmds.ls(shader_ns + ":*", type="place3dTexture") or []
    geos   = cmds.ls(geo_ns   + ":*", type="transform") or []
    geo_map = { _short(g): g for g in geos }

    for p in places:
        sp = _short(p)
        base = sp[:-len(place_suffix)] if place_suffix and sp.endswith(place_suffix) else sp
        wanted = base + (geo_suffix or "")
        xform = geo_map.get(wanted)

        if not xform and allow_fuzzy:
            for s, full in geo_map.items():
                if (not geo_suffix and s.startswith(base)) or (geo_suffix and s.startswith(base) and s.endswith(geo_suffix)):
                    xform = full
                    break

        pairs.append({"place": p, "xform": xform, "base": base, "status": "ok" if xform else "missing"})
    return pairs

class Place3DTab(QtWidgets.QWidget):
    def __init__(self, shared_geo_combo, shared_shader_combo, parent=None):
        super(Place3DTab, self).__init__(parent)
        self.shared_geo_ns = shared_geo_combo
        self.shared_shd_ns = shared_shader_combo
        self._build(); self._wire()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Suffixes (tab-specific)
        row_suf = QtWidgets.QHBoxLayout()
        self.edit_geo_suffix   = QtWidgets.QLineEdit("_Grp")
        self.edit_place_suffix = QtWidgets.QLineEdit("_Place3dTexture")
        row_suf.addWidget(QtWidgets.QLabel("Geo Suffix"))
        row_suf.addWidget(self.edit_geo_suffix)
        row_suf.addSpacing(10)
        row_suf.addWidget(QtWidgets.QLabel("Place3D Suffix"))
        row_suf.addWidget(self.edit_place_suffix)
        layout.addLayout(row_suf)

        # Options
        row_opts = QtWidgets.QHBoxLayout()
        self.chk_dry = QtWidgets.QCheckBox("Dry Run"); self.chk_dry.setChecked(True)
        self.chk_force = QtWidgets.QCheckBox("Force delete old constraints")
        self.chk_fuzzy = QtWidgets.QCheckBox("Fuzzy match"); self.chk_fuzzy.setChecked(True)
        row_opts.addWidget(self.chk_dry); row_opts.addWidget(self.chk_force); row_opts.addWidget(self.chk_fuzzy); row_opts.addStretch(1)
        layout.addLayout(row_opts)

        # Actions
        row_btns = QtWidgets.QHBoxLayout()
        self.btn_scan = QtWidgets.QPushButton("Scan (Place3D -> Geo)")
        self.btn_apply = QtWidgets.QPushButton("Copy TRS + Constrain"); self.btn_apply.setStyleSheet("font-weight: bold;")
        row_btns.addStretch(1); row_btns.addWidget(self.btn_scan); row_btns.addWidget(self.btn_apply)
        layout.addLayout(row_btns)

        # Table + Log
        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["place3dTexture (Shader)", "Transform (Geo)", "Match", "Result"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        self.log = QtWidgets.QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(140)
        layout.addWidget(self.log)

    def _wire(self):
        self.btn_scan.clicked.connect(self._do_scan)
        self.btn_apply.clicked.connect(self._do_apply)

    def _log(self, msg): self.log.appendPlainText(msg)

    def _do_scan(self):
        geo_ns    = self.shared_geo_ns.currentText().strip()
        shd_ns    = self.shared_shd_ns.currentText().strip()
        geo_suf   = self.edit_geo_suffix.text()
        place_suf = self.edit_place_suffix.text()
        fuzzy     = self.chk_fuzzy.isChecked()

        if not geo_ns or not shd_ns:
            self._log("Select Geometry/Shader namespaces from the top bar."); return

        self.pairs = _find_place3d_pairs_by_place(shd_ns, geo_ns, place_suf, geo_suf, allow_fuzzy=fuzzy)
        self._populate(self.pairs)
        missing = sum(1 for p in self.pairs if not p["xform"])
        self._log("Scan: {} place3dTexture, {} missing transforms".format(len(self.pairs), missing))

    def _populate(self, pairs):
        self.table.setRowCount(0)
        for p in pairs:
            r = self.table.rowCount(); self.table.insertRow(r)
            self.table.setItem(r,0,QtWidgets.QTableWidgetItem(p["place"]))
            self.table.setItem(r,1,QtWidgets.QTableWidgetItem(p["xform"] or "-"))
            match_item = QtWidgets.QTableWidgetItem("OK" if p["xform"] else "Missing")
            match_item.setForeground(QtCore.Qt.darkGreen if p["xform"] else QtCore.Qt.red)
            self.table.setItem(r,2,match_item)
            self.table.setItem(r,3,QtWidgets.QTableWidgetItem("-"))
        self.table.resizeColumnsToContents()

    def _do_apply(self):
        dry   = self.chk_dry.isChecked()
        force = self.chk_force.isChecked()
        geo_ns = self.shared_geo_ns.currentText().strip()
        shd_ns = self.shared_shd_ns.currentText().strip()

        # Apply Place3D constraints
        for r in range(self.table.rowCount()):
            place = self.table.item(r,0).text()
            xform = self.table.item(r,1).text()
            if xform == "-":
                self.table.item(r,3).setText("No transform"); continue
            s = _snap_trs_world(xform, place, dry)
            c = _parent_and_scale_constrain(xform, place, force, dry)
            res = "{} | {}".format(s, c)
            self.table.item(r,3).setText(res)
            self._log("{}  <--  {}  ::  {}".format(place, xform, res))

        # Connect shading attributes if both namespaces are available
        if geo_ns and shd_ns and not dry:
            self._log("=== Connecting Shading Attributes ===")
            attr_results = _connect_shading_attributes(geo_ns, shd_ns, dry_run=dry)
            if attr_results:
                for result in attr_results:
                    self._log("  {}".format(result))
                connected_count = sum(1 for r in attr_results if r.startswith("// Result: Connected"))
                if connected_count > 0:
                    self._log("Connected {} shading attributes".format(connected_count))
                else:
                    self._log("No new shading attribute connections needed")
            else:
                self._log("No shading attributes to connect")

        self._log("=== Place3D Apply done (DryRun={}, Force={}) ===".format(dry, force))

# =============================================================================
# Matrix-Based Place3D Tab - Alternative to constraint-based method
# =============================================================================

class MatrixPlace3DTab(QtWidgets.QWidget):
    """
    Matrix-based Place3D linker tab.

    This tab provides an alternative to the constraint-based Place3D linking method.
    Instead of using parentConstraint + scaleConstraint, it uses Maya's decomposeMatrix
    node for cleaner, more performant transform connections.

    Features:
    - Same scanning logic as Place3DTab
    - Uses _matrix_transfer_transform() instead of constraints
    - Shares namespace dropdowns from main window
    - Independent testing environment
    """

    def __init__(self, shared_geo_combo, shared_shader_combo, parent=None):
        super(MatrixPlace3DTab, self).__init__(parent)
        self.shared_geo_ns = shared_geo_combo
        self.shared_shd_ns = shared_shader_combo
        self._build()
        self._wire()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Title label
        title = QtWidgets.QLabel("Matrix-Based Place3D Linker")
        title.setStyleSheet("font-weight: bold; font-size: 12pt; color: #2196F3;")
        layout.addWidget(title)

        info = QtWidgets.QLabel("Uses decomposeMatrix nodes instead of constraints for cleaner connections")
        info.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info)

        layout.addSpacing(10)

        # Suffixes (tab-specific)
        row_suf = QtWidgets.QHBoxLayout()
        self.edit_geo_suffix = QtWidgets.QLineEdit("_Grp")
        self.edit_place_suffix = QtWidgets.QLineEdit("_Place3dTexture")
        row_suf.addWidget(QtWidgets.QLabel("Geo Suffix"))
        row_suf.addWidget(self.edit_geo_suffix)
        row_suf.addSpacing(10)
        row_suf.addWidget(QtWidgets.QLabel("Place3D Suffix"))
        row_suf.addWidget(self.edit_place_suffix)
        layout.addLayout(row_suf)

        # Options
        row_opts = QtWidgets.QHBoxLayout()
        self.chk_dry = QtWidgets.QCheckBox("Dry Run")
        self.chk_dry.setChecked(True)
        self.chk_force = QtWidgets.QCheckBox("Force replace existing matrix connections")
        self.chk_fuzzy = QtWidgets.QCheckBox("Fuzzy match")
        self.chk_fuzzy.setChecked(True)
        row_opts.addWidget(self.chk_dry)
        row_opts.addWidget(self.chk_force)
        row_opts.addWidget(self.chk_fuzzy)
        row_opts.addStretch(1)
        layout.addLayout(row_opts)

        # Actions
        row_btns = QtWidgets.QHBoxLayout()
        self.btn_scan = QtWidgets.QPushButton("Scan (Place3D → Geo)")
        self.btn_apply = QtWidgets.QPushButton("Apply Matrix Transfer")
        self.btn_apply.setStyleSheet("font-weight: bold; background-color: #2196F3; color: white;")
        row_btns.addStretch(1)
        row_btns.addWidget(self.btn_scan)
        row_btns.addWidget(self.btn_apply)
        layout.addLayout(row_btns)

        # Table + Log
        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([
            "place3dTexture (Shader)",
            "Transform (Geo)",
            "Match",
            "Result"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(140)
        layout.addWidget(self.log)

    def _wire(self):
        self.btn_scan.clicked.connect(self._do_scan)
        self.btn_apply.clicked.connect(self._do_apply)

    def _log(self, msg):
        self.log.appendPlainText(msg)

    def _do_scan(self):
        geo_ns = self.shared_geo_ns.currentText().strip()
        shd_ns = self.shared_shd_ns.currentText().strip()
        geo_suf = self.edit_geo_suffix.text()
        place_suf = self.edit_place_suffix.text()
        fuzzy = self.chk_fuzzy.isChecked()

        if not geo_ns or not shd_ns:
            self._log("Select Geometry/Shader namespaces from the top bar.")
            return

        self.pairs = _find_place3d_pairs_by_place(shd_ns, geo_ns, place_suf, geo_suf, allow_fuzzy=fuzzy)
        self._populate(self.pairs)
        missing = sum(1 for p in self.pairs if not p["xform"])
        self._log("Scan: {} place3dTexture, {} missing transforms".format(len(self.pairs), missing))

    def _populate(self, pairs):
        self.table.setRowCount(0)
        for p in pairs:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QtWidgets.QTableWidgetItem(p["place"]))
            self.table.setItem(r, 1, QtWidgets.QTableWidgetItem(p["xform"] or "-"))
            match_item = QtWidgets.QTableWidgetItem("OK" if p["xform"] else "Missing")
            match_item.setForeground(QtCore.Qt.darkGreen if p["xform"] else QtCore.Qt.red)
            self.table.setItem(r, 2, match_item)
            self.table.setItem(r, 3, QtWidgets.QTableWidgetItem("-"))
        self.table.resizeColumnsToContents()

    def _do_apply(self):
        dry = self.chk_dry.isChecked()
        force = self.chk_force.isChecked()
        geo_ns = self.shared_geo_ns.currentText().strip()
        shd_ns = self.shared_shd_ns.currentText().strip()

        self._log("=== Applying Matrix-Based Place3D Transfer ===")

        # Apply matrix transfer for each pair
        for r in range(self.table.rowCount()):
            place = self.table.item(r, 0).text()
            xform = self.table.item(r, 1).text()

            if xform == "-":
                self.table.item(r, 3).setText("No transform")
                continue

            # Snap TRS first (same as constraint method)
            s = _snap_trs_world(xform, place, dry)

            # Apply matrix transfer instead of constraints
            m = _matrix_transfer_transform(xform, place, force, dry)

            res = "{} | {}".format(s, m)
            self.table.item(r, 3).setText(res)
            self._log("{}  <--  {}  ::  {} (Matrix)".format(place, xform, res))

        # Connect shading attributes if both namespaces are available
        if geo_ns and shd_ns and not dry:
            self._log("=== Connecting Shading Attributes ===")
            attr_results = _connect_shading_attributes(geo_ns, shd_ns, dry_run=dry)
            if attr_results:
                for result in attr_results:
                    self._log("  {}".format(result))
                connected_count = sum(1 for r in attr_results if r.startswith("// Result: Connected"))
                if connected_count > 0:
                    self._log("Connected {} shading attributes".format(connected_count))
                else:
                    self._log("No new shading attribute connections needed")
            else:
                self._log("No shading attributes to connect")

        self._log("=== Matrix Place3D Apply done (DryRun={}, Force={}) ===".format(dry, force))

# =============================================================================
# TAB 2: BlendShape Builder (Anim -> Groom) - Groom-first scan
#   Base (blendShape): Groom   |   Target: Anim   |   Weight=1.0
#   Uses ONLY the shared Geometry NS from the header (no per-tab NS dropdowns)
# =============================================================================

def _existing_blendShape_on(shape):
    hist = cmds.listHistory(shape, pruneDagObjects=True) or []
    bs = [h for h in hist if cmds.nodeType(h) == "blendShape"]
    return bs[0] if bs else None

def _blendshape_anim_to_groom(anim_xform, groom_xform,
                              add_to_existing=True, create_if_missing=True,
                              force_delete_existing=False, dry_run=False):
    anim_shape  = _first_mesh_shape(anim_xform)   # target
    groom_shape = _first_mesh_shape(groom_xform)  # base
    if not anim_shape or not groom_shape:
        return "no mesh (anim:{}, groom:{})".format(bool(anim_shape), bool(groom_shape))
    if dry_run:
        return "would BS: target={} -> base={}".format(_short(anim_shape), _short(groom_shape))

    bs = _existing_blendShape_on(groom_shape)  # lives on Groom
    try:
        if bs and force_delete_existing:
            cmds.delete(bs); bs = None
    except Exception:
        pass

    try:
        if not bs:
            if not create_if_missing: return "no BS on base (skipped)"
            bs_name = "BS_{}".format(_short(groom_xform))
            bs = cmds.blendShape(anim_shape, groom_shape, foc=True, name=bs_name, origin="world")[0]
            cmds.blendShape(bs, e=True, w=[(0, 1.0)])   # ensure visible result
            return "created {} (w0=1.0)".format(bs)

        if not add_to_existing: return "existing {} (skipped add)".format(bs)

        idx = cmds.blendShape(bs, q=True, wc=True)
        cmds.blendShape(bs, e=True, t=(groom_shape, idx, anim_shape, 1.0))
        cmds.setAttr("{}.weight[{}]".format(bs, idx), 1.0)
        return "added target to {} (w{}=1.0)".format(bs, idx)

    except Exception as e:
        return "error: {}".format(e)

def _detect_blendshape_suffixes(anim_ns, groom_ns):
    """Auto-detect the correct suffixes for BlendShape matching by checking what exists in scene.

    Returns: (anim_suffix, groom_suffix) tuple
    """
    # Common suffix patterns to check
    anim_suffixes = ["_Geo", "_geo", "_Mesh", "_mesh", "Geo", "geo"]
    groom_suffixes = ["_GroomGeo", "_groomGeo", "_GroomMesh", "_groomMesh", "_Groom_Geo", "_groom_geo", "GroomGeo", "groomGeo", "_Geo", "_geo", "_Mesh", "_mesh"]

    # Get all transforms in both namespaces
    anim_transforms = cmds.ls(anim_ns + ":*", type="transform", long=True) or []
    groom_transforms = cmds.ls(groom_ns + ":*", type="transform", long=True) or []

    # Count objects with each suffix pattern
    best_anim_suffix = ""
    best_groom_suffix = ""
    max_anim_count = 0
    max_groom_count = 0

    # Check anim suffixes
    for suffix in anim_suffixes:
        count = len([t for t in anim_transforms if _short(t).endswith(suffix)])
        if count > max_anim_count:
            max_anim_count = count
            best_anim_suffix = suffix

    # Check groom suffixes
    for suffix in groom_suffixes:
        count = len([t for t in groom_transforms if _short(t).endswith(suffix)])
        if count > max_groom_count:
            max_groom_count = count
            best_groom_suffix = suffix

    # Fallback to defaults if nothing found
    if not best_anim_suffix:
        best_anim_suffix = "_Geo"
    if not best_groom_suffix:
        best_groom_suffix = "_GroomGeo"

    return best_anim_suffix, best_groom_suffix

def _enhanced_groom_match(anim_name, groom_candidates, anim_suffix, groom_suffix):
    """Enhanced matching for complex groom naming patterns.

    Handles patterns like:
    - Ear_Geo -> EarGroom_Geo or Ear_GroomGeo
    - Body_Geo -> BodyGroom_Geo or Body_GroomGeo
    - Face_Geo -> FaceGroom_Geo or Face_GroomGeo
    """
    # Extract base name from anim (remove suffix)
    base = anim_name[:-len(anim_suffix)] if anim_suffix and anim_name.endswith(anim_suffix) else anim_name

    # Try multiple groom naming patterns
    patterns = [
        # Pattern 1: {base}Groom{suffix} (e.g., EarGroom_Geo)
        "{}Groom{}".format(base, groom_suffix or ""),
        # Pattern 2: {base}_{groom_suffix} (e.g., Ear_GroomGeo)
        "{}_{}".format(base, groom_suffix.lstrip('_') if groom_suffix else "GroomGeo"),
        # Pattern 3: Exact match with groom suffix
        "{}{}".format(base, groom_suffix or ""),
        # Pattern 4: Case variations
        "{}groom{}".format(base, groom_suffix or ""),
        "{}GROOM{}".format(base, groom_suffix or ""),
    ]

    # Try exact matches first
    for pattern in patterns:
        if pattern in groom_candidates:
            return groom_candidates[pattern]

    # Try fuzzy matching (contains base name)
    for groom_name, groom_full in groom_candidates.items():
        # Check if groom name contains the base name
        if base.lower() in groom_name.lower():
            # Additional validation: should contain "groom" or end with groom_suffix
            if ("groom" in groom_name.lower() or
                (groom_suffix and groom_name.endswith(groom_suffix))):
                return groom_full

    return None

def _pairs_groom_first(anim_ns, groom_ns, anim_suffix, groom_suffix, allow_fuzzy=True, auto_detect_suffixes=True):
    """
    Enhanced BlendShape matching with support for complex naming patterns and hierarchy.

    Handles patterns like:
    - CHAR_Kit_001:Ear_Geo -> CHAR_Kit_001_groom:EarGroom_Geo
    - CHAR_Kit_001:Ear_Geo -> CHAR_Kit_001_groom:Ear_GroomGeo
    - Supports hierarchy: CHAR_Kit_001_groom:GroomGeo_Grp|CHAR_Kit_001_groom:BodyGroomGeo_Grp|CHAR_Kit_001_groom:EarGroom_Geo
    - Auto-detects correct suffixes if enabled
    """
    pairs = []

    # Auto-detect suffixes if enabled and no objects found with provided suffixes
    if auto_detect_suffixes:
        # Check if provided suffixes work
        test_groom = cmds.ls(groom_ns + ":*" + groom_suffix, type="transform") or []
        test_anim = cmds.ls(anim_ns + ":*" + anim_suffix, type="transform") or []

        if not test_groom or not test_anim:
            detected_anim_suffix, detected_groom_suffix = _detect_blendshape_suffixes(anim_ns, groom_ns)
            if not test_anim:
                anim_suffix = detected_anim_suffix
            if not test_groom:
                groom_suffix = detected_groom_suffix

    # Get all transforms in both namespaces (including hierarchy)
    groom_xforms = cmds.ls(groom_ns + ":*" + groom_suffix, type="transform", long=True) or []
    anim_xforms  = cmds.ls(anim_ns  + ":*" + anim_suffix,  type="transform", long=True) or []

    # Create maps for both short names and hierarchy-aware names
    anim_map = {}
    for anim in anim_xforms:
        short_name = _short(anim)
        anim_map[short_name] = anim

    groom_map = {}
    for groom in groom_xforms:
        short_name = _short(groom)
        groom_map[short_name] = groom

    for groom in groom_xforms:
        sg = _short(groom)
        base = sg[:-len(groom_suffix)] if groom_suffix and sg.endswith(groom_suffix) else sg

        # Try standard matching first
        wanted = base + (anim_suffix or "")
        anim = anim_map.get(wanted)

        # If no match and fuzzy is enabled, try enhanced matching
        if not anim and allow_fuzzy:
            # Extract potential base names from groom name
            potential_bases = []

            # Pattern 1: Remove "Groom" from name (EarGroom -> Ear)
            if "Groom" in sg:
                potential_bases.append(sg.replace("Groom", ""))
            if "groom" in sg:
                potential_bases.append(sg.replace("groom", ""))

            # Pattern 2: Remove groom suffix and extract base
            if groom_suffix and sg.endswith(groom_suffix):
                base_part = sg[:-len(groom_suffix)]
                if "Groom" in base_part:
                    potential_bases.append(base_part.replace("Groom", ""))
                if "groom" in base_part:
                    potential_bases.append(base_part.replace("groom", ""))
                potential_bases.append(base_part)

            # Try to find anim match for each potential base
            for potential_base in potential_bases:
                wanted_anim = potential_base + (anim_suffix or "")
                if wanted_anim in anim_map:
                    anim = anim_map[wanted_anim]
                    break

            # If still no match, try partial matching
            if not anim:
                for anim_name, anim_full in anim_map.items():
                    anim_base = anim_name[:-len(anim_suffix)] if anim_suffix and anim_name.endswith(anim_suffix) else anim_name

                    # Check if groom name contains anim base
                    if (anim_base.lower() in sg.lower() and
                        len(anim_base) > 2):  # Avoid matching very short names
                        anim = anim_full
                        break

        pairs.append({
            "groomXform": groom,
            "animXform": anim,
            "base": base,
            "status": "ok" if anim else "missing",
            "detected_anim_suffix": anim_suffix,
            "detected_groom_suffix": groom_suffix
        })

    return pairs

def _pairs_groom_first_single_ns(ns, anim_suffix, groom_suffix, allow_fuzzy=True):
    """Enhanced single namespace scan with complex naming pattern support."""
    pairs = []

    # Get all transforms with hierarchy support
    groom_xforms = cmds.ls(ns + ":*" + groom_suffix, type="transform", long=True) or []
    anim_xforms  = cmds.ls(ns + ":*" + anim_suffix,  type="transform", long=True) or []

    anim_map = { _short(a): a for a in anim_xforms }

    for groom in groom_xforms:
        sg = _short(groom)
        base = sg[:-len(groom_suffix)] if groom_suffix and sg.endswith(groom_suffix) else sg
        anim = anim_map.get(base + (anim_suffix or ""))

        if not anim and allow_fuzzy:
            # Use enhanced matching logic
            potential_bases = []

            # Extract potential base names from groom
            if "Groom" in sg:
                potential_bases.append(sg.replace("Groom", ""))
            if "groom" in sg:
                potential_bases.append(sg.replace("groom", ""))

            if groom_suffix and sg.endswith(groom_suffix):
                base_part = sg[:-len(groom_suffix)]
                if "Groom" in base_part:
                    potential_bases.append(base_part.replace("Groom", ""))
                if "groom" in base_part:
                    potential_bases.append(base_part.replace("groom", ""))
                potential_bases.append(base_part)

            # Try to find anim match
            for potential_base in potential_bases:
                wanted_anim = potential_base + (anim_suffix or "")
                if wanted_anim in anim_map:
                    anim = anim_map[wanted_anim]
                    break

            # Fallback to partial matching
            if not anim:
                for anim_name, anim_full in anim_map.items():
                    anim_base = anim_name[:-len(anim_suffix)] if anim_suffix and anim_name.endswith(anim_suffix) else anim_name
                    if (anim_base.lower() in sg.lower() and len(anim_base) > 2):
                        anim = anim_full
                        break

        pairs.append({"groomXform": groom, "animXform": anim, "base": base, "status": "ok" if anim else "missing"})

    return pairs

class BlendShapeTab(QtWidgets.QWidget):
    def __init__(self, shared_geo_combo, parent=None):
        super(BlendShapeTab, self).__init__(parent)
        self.shared_geo_ns = shared_geo_combo
        self._build(); self._wire(); self._refresh_namespaces()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Separate Anim and Groom namespaces (like working groom.py)
        row_ns = QtWidgets.QHBoxLayout()
        self.anim_ns  = QtWidgets.QComboBox(); self.anim_ns.setEditable(True)
        self.groom_ns = QtWidgets.QComboBox(); self.groom_ns.setEditable(True)
        self.btn_refresh = QtWidgets.QPushButton("Refresh")
        row_ns.addWidget(QtWidgets.QLabel("Anim NS (Targets)"))
        row_ns.addWidget(self.anim_ns, 2)
        row_ns.addSpacing(10)
        row_ns.addWidget(QtWidgets.QLabel("Groom NS (Bases)"))
        row_ns.addWidget(self.groom_ns, 2)
        row_ns.addWidget(self.btn_refresh, 0)
        layout.addLayout(row_ns)

        # Suffixes
        row_suf = QtWidgets.QHBoxLayout()
        self.anim_suffix  = QtWidgets.QLineEdit("_Geo")
        self.groom_suffix = QtWidgets.QLineEdit("_GroomGeo")
        row_suf.addWidget(QtWidgets.QLabel("Anim Suffix"));  row_suf.addWidget(self.anim_suffix)
        row_suf.addSpacing(10)
        row_suf.addWidget(QtWidgets.QLabel("Groom Suffix")); row_suf.addWidget(self.groom_suffix)
        layout.addLayout(row_suf)

        row_opts = QtWidgets.QHBoxLayout()
        self.chk_dry    = QtWidgets.QCheckBox("Dry Run"); self.chk_dry.setChecked(True)
        self.chk_add    = QtWidgets.QCheckBox("Add to existing BS"); self.chk_add.setChecked(True)
        self.chk_create = QtWidgets.QCheckBox("Create if missing"); self.chk_create.setChecked(True)
        self.chk_force  = QtWidgets.QCheckBox("Force delete existing BS on base")
        self.chk_fuzzy  = QtWidgets.QCheckBox("Fuzzy match"); self.chk_fuzzy.setChecked(True)
        row_opts.addWidget(self.chk_dry); row_opts.addWidget(self.chk_add); row_opts.addWidget(self.chk_create)
        row_opts.addWidget(self.chk_force); row_opts.addWidget(self.chk_fuzzy); row_opts.addStretch(1)
        layout.addLayout(row_opts)

        row_btns = QtWidgets.QHBoxLayout()
        self.btn_scan = QtWidgets.QPushButton("Scan (Groom-first: Anim -> Groom)")
        self.btn_apply = QtWidgets.QPushButton("Create/Add BlendShapes"); self.btn_apply.setStyleSheet("font-weight: bold;")
        row_btns.addStretch(1); row_btns.addWidget(self.btn_scan); row_btns.addWidget(self.btn_apply)
        layout.addLayout(row_btns)

        # Table + Log
        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Groom Transform (Base)", "Anim Transform (Target)", "Match", "Action", "Result"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        self.log = QtWidgets.QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(140)
        layout.addWidget(self.log)

    def _wire(self):
        self.btn_refresh.clicked.connect(self._refresh_namespaces)
        self.btn_scan.clicked.connect(self._do_scan)
        self.btn_apply.clicked.connect(self._do_apply)

    def _refresh_namespaces(self):
        ns = _list_namespaces()
        self.anim_ns.clear(); self.groom_ns.clear()
        self.anim_ns.addItems(ns); self.groom_ns.addItems(ns)
        for i in range(self.groom_ns.count()):
            if "groom" in self.groom_ns.itemText(i).lower():
                self.groom_ns.setCurrentIndex(i)

    def _log(self, msg): self.log.appendPlainText(msg)

    def _do_scan(self):
        anim_ns  = self.anim_ns.currentText().strip()
        groom_ns = self.groom_ns.currentText().strip()
        asuf = self.anim_suffix.text()
        gsuf = self.groom_suffix.text()
        fuzzy = self.chk_fuzzy.isChecked()

        if not anim_ns or not groom_ns:
            self._log("Select Anim and Groom namespaces first."); return

        # DIAGNOSTIC: Debug namespace and object detection
        self._log("=== BLENDSHAPE SCAN DIAGNOSTICS ===")
        self._log("Anim NS: '{}', Groom NS: '{}'".format(anim_ns, groom_ns))
        self._log("Anim Suffix: '{}', Groom Suffix: '{}'".format(asuf, gsuf))

        # Check if namespaces exist
        all_ns = cmds.namespaceInfo(listOnlyNamespaces=True) or []
        self._log("Namespace exists - Anim: {}, Groom: {}".format(anim_ns in all_ns, groom_ns in all_ns))

        # Check objects in namespaces
        anim_all = cmds.ls(anim_ns + ":*", type="transform") or []
        groom_all = cmds.ls(groom_ns + ":*", type="transform") or []
        self._log("All transforms - Anim: {}, Groom: {}".format(len(anim_all), len(groom_all)))

        # Check objects with provided suffixes
        anim_with_suffix = cmds.ls(anim_ns + ":*" + asuf, type="transform") or []
        groom_with_suffix = cmds.ls(groom_ns + ":*" + gsuf, type="transform") or []
        self._log("With provided suffixes - Anim: {}, Groom: {}".format(len(anim_with_suffix), len(groom_with_suffix)))

        # Auto-detect suffixes if no objects found with provided suffixes
        if not anim_with_suffix or not groom_with_suffix:
            self._log("Auto-detecting suffixes...")
            detected_asuf, detected_gsuf = _detect_blendshape_suffixes(anim_ns, groom_ns)

            if not anim_with_suffix:
                self._log("No anim objects with '{}', trying detected: '{}'".format(asuf, detected_asuf))
                asuf = detected_asuf
                anim_with_suffix = cmds.ls(anim_ns + ":*" + asuf, type="transform") or []
                # Update the UI field with detected suffix
                self.anim_suffix.setText(asuf)

            if not groom_with_suffix:
                self._log("No groom objects with '{}', trying detected: '{}'".format(gsuf, detected_gsuf))
                gsuf = detected_gsuf
                groom_with_suffix = cmds.ls(groom_ns + ":*" + gsuf, type="transform") or []
                # Update the UI field with detected suffix
                self.groom_suffix.setText(gsuf)

            self._log("After auto-detection - Anim: {}, Groom: {}".format(len(anim_with_suffix), len(groom_with_suffix)))

        if anim_with_suffix:
            self._log("Anim objects: {}".format([_short(x) for x in anim_with_suffix[:5]]))  # Show first 5
        if groom_with_suffix:
            self._log("Groom objects: {}".format([_short(x) for x in groom_with_suffix[:5]]))  # Show first 5

        self._log("=== END DIAGNOSTICS ===")

        # Use enhanced function with auto-detection disabled (already done above)
        self.pairs = _pairs_groom_first(anim_ns, groom_ns, asuf, gsuf, fuzzy, auto_detect_suffixes=False)
        self._populate(self.pairs)
        missing = sum(1 for p in self.pairs if not p["animXform"])
        self._log("Scan: {} groom candidates, {} missing anim matches".format(len(self.pairs), missing))

    def _populate(self, pairs):
        self.table.setRowCount(0)
        for p in pairs:
            r = self.table.rowCount(); self.table.insertRow(r)
            self.table.setItem(r,0,QtWidgets.QTableWidgetItem(p["groomXform"]))
            self.table.setItem(r,1,QtWidgets.QTableWidgetItem(p["animXform"] or "-"))
            match_item = QtWidgets.QTableWidgetItem("OK" if p["animXform"] else "Missing")
            match_item.setForeground(QtCore.Qt.darkGreen if p["animXform"] else QtCore.Qt.red)
            self.table.setItem(r,2,match_item)

            act = "Add to existing" if self.chk_add.isChecked() else "Create new"
            if not self.chk_create.isChecked(): act = "Add only (no create)"
            if self.chk_force.isChecked(): act += " | Force delete existing"
            self.table.setItem(r,3,QtWidgets.QTableWidgetItem(act))

            self.table.setItem(r,4,QtWidgets.QTableWidgetItem("-"))
        self.table.resizeColumnsToContents()

    def _do_apply(self):
        dry    = self.chk_dry.isChecked()
        add    = self.chk_add.isChecked()
        create = self.chk_create.isChecked()
        force  = self.chk_force.isChecked()
        for r in range(self.table.rowCount()):
            groom = self.table.item(r,0).text()  # base
            anim  = self.table.item(r,1).text()  # target
            if anim == "-":
                self.table.item(r,4).setText("No anim match"); continue
            res = _blendshape_anim_to_groom(anim_xform=anim, groom_xform=groom,
                                            add_to_existing=add, create_if_missing=create,
                                            force_delete_existing=force, dry_run=dry)
            self.table.item(r,4).setText(res)
            self._log("{}  (base=groom)  <-  {}  (target=anim)  ::  {}".format(groom, anim, res))
        self._log("=== BlendShape Apply done (DryRun={}, Add={}, Create={}, Force={}) ==="
                  .format(dry, add, create, force))

# =============================================================================
# TAB 3: Assign Shader by Namespace - Qt Table UI (uses shared dropdowns)
# =============================================================================

def _strip_namespace(node_name):
    return node_name.split(':')[-1] if node_name else node_name

def _apply_namespace_to_path(src_dag_path, namespace):
    if not src_dag_path or not src_dag_path.startswith("|"):
        return None
    parts = [p for p in src_dag_path.split("|") if p]
    new_parts = ["{}:{}".format(namespace, _strip_namespace(seg)) for seg in parts]
    return "|" + "|".join(new_parts)

def _resolve_shape_in_scene(stored_path, geo_namespace):
    # Try full DAG reconstruction
    candidate = _apply_namespace_to_path(stored_path, geo_namespace)
    if candidate and cmds.objExists(candidate):
        if cmds.nodeType(candidate) in ("mesh", "nurbsSurface", "nurbsCurve", "subdiv", "aiStandIn"):
            return candidate
        if cmds.objectType(candidate, isAType="transform"):
            shapes = cmds.listRelatives(candidate, shapes=True, fullPath=True) or []
            if shapes:
                return shapes[0]
    # Fallback by leaf shape name within geo namespace
    leaf = _strip_namespace(stored_path.split("|")[-1]) if "|" in stored_path else _strip_namespace(stored_path)
    candidates = []
    for shp in cmds.ls(type=["mesh", "nurbsSurface", "nurbsCurve", "aiStandIn"], long=True) or []:
        if _strip_namespace(shp).lower() == leaf.lower():
            # ensure it's under geo namespace
            last_seg = shp.split("|")[-1]
            if ":" in last_seg and last_seg.split(":")[0] == geo_namespace:
                candidates.append(shp)
    if len(candidates) == 1:
        return candidates[0]
    elif len(candidates) > 1:
        target_segments = [s for s in stored_path.split("|") if s]
        target_wo_ns = [_strip_namespace(s) for s in target_segments]
        for shp in candidates:
            segs = [s for s in shp.split("|") if s]
            segs_wo_ns = [_strip_namespace(s) for s in segs]
            if segs_wo_ns[-len(target_wo_ns):] == target_wo_ns:
                return shp
        return candidates[0]
    return None

def _read_mapping_from_sg(sg):
    attr = "{}.snow__assign_shade".format(sg)
    if not cmds.objExists(attr):
        return []
    atype = cmds.getAttr(attr, type=True)
    try:
        if atype == "stringArray":
            arr = cmds.getAttr(attr)
            if isinstance(arr, (list, tuple)):
                if len(arr) == 2 and isinstance(arr[1], (list, tuple)):
                    return list(arr[1])
                return list(arr)
            return []
        elif atype == "string":
            raw = cmds.getAttr(attr)
            if not raw:
                return []
            try:
                val = json.loads(raw)
                if isinstance(val, list):
                    return [str(x) for x in val]
            except Exception:
                try:
                    val = ast.literal_eval(raw)
                    if isinstance(val, list):
                        return [str(x) for x in val]
                except Exception:
                    return [raw]
    except Exception:
        pass
    return []

def _sg_has_material_connection(sg):
    for plug in ("rsSurfaceShader", "surfaceShader"):
        plg = "{}.{}".format(sg, plug)
        if cmds.objExists(plg):
            conns = cmds.listConnections(plg, source=True, destination=False) or []
            if conns:
                return conns[0]
    return None

def _assign_shapes_to_sg(shapes, sg):
    assigned, failed = 0, []
    for shp in shapes:
        try:
            if not cmds.objExists(shp):
                failed.append((shp, "missing")); continue
            cmds.sets(shp, e=True, forceElement=sg)
            assigned += 1
        except Exception as e:
            failed.append((shp, str(e)))
    return assigned, failed

class AssignShaderTab(QtWidgets.QWidget):
    def __init__(self, shared_geo_combo, shared_shader_combo, parent=None):
        super(AssignShaderTab, self).__init__(parent)
        self.shared_geo_ns = shared_geo_combo
        self.shared_shd_ns = shared_shader_combo
        self.plan = []
        self._build(); self._wire()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Top hint row (uses shared combos above)
        hint = QtWidgets.QLabel("Uses shared Geometry/Shader namespaces from the top bar.")
        hint.setStyleSheet("color: #aaa;")
        layout.addWidget(hint)

        # Buttons
        row = QtWidgets.QHBoxLayout()
        self.btn_scan = QtWidgets.QPushButton("Scan")
        self.btn_assign_all = QtWidgets.QPushButton("Assign All"); self.btn_assign_all.setStyleSheet("font-weight: bold;")
        row.addStretch(1); row.addWidget(self.btn_scan); row.addWidget(self.btn_assign_all)
        layout.addLayout(row)

        # Table
        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ShadingEngine (Material)", "Resolved Shapes", "Action", "Result"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        # Log
        self.log = QtWidgets.QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(140)
        layout.addWidget(self.log)

    def _wire(self):
        self.btn_scan.clicked.connect(self._on_scan)
        self.btn_assign_all.clicked.connect(self._on_assign_all)
        self.table.cellClicked.connect(self._on_cell_clicked)

    def _log(self, msg):
        self.log.appendPlainText(msg)

    # ---- Data ops ----
    def _scan_shading_groups(self, shader_namespace):
        all_sg = cmds.ls(type="shadingEngine") or []
        hit = []
        for sg in all_sg:
            if not sg.startswith(shader_namespace + ":"):
                continue
            if cmds.objExists("{}.snow__assign_shade".format(sg)):
                mapping = _read_mapping_from_sg(sg)
                mat = _sg_has_material_connection(sg)
                hit.append((sg, mat, mapping))
        return hit

    def _plan_assignments(self, geo_namespace, sg_entries):
        plan = []
        for sg, mat, stored_paths in sg_entries:
            resolved, unresolved = [], []
            for p in stored_paths:
                shp = _resolve_shape_in_scene(p, geo_namespace)
                if shp and cmds.objExists(shp): resolved.append(shp)
                else: unresolved.append(p)
            plan.append({
                "sg": sg,
                "material": mat,
                "targets": list(stored_paths),
                "resolved": sorted(list(set(resolved))),
                "unresolved": list(unresolved)
            })
        return plan

    # ---- UI ops ----
    def _on_scan(self):
        geo_ns = self.shared_geo_ns.currentText().strip()
        shd_ns = self.shared_shd_ns.currentText().strip()
        if not geo_ns or not shd_ns:
            self._log("[ERR] Pick Geometry/Shader namespaces in the top bar."); return

        self._log("[SCAN] SGs under '{}' ...".format(shd_ns))
        hits = self._scan_shading_groups(shd_ns)
        if not hits:
            self._log("[INFO] No SGs with 'snow__assign_shade' in '{}'.".format(shd_ns))
            self.plan = []; self._populate_table([]); return

        self.plan = self._plan_assignments(geo_ns, hits)
        self._log("[SCAN] Planned {} SG(s).".format(len(self.plan)))
        self._populate_table(self.plan)

    def _populate_table(self, plan):
        self.table.setRowCount(0)
        for entry in plan:
            r = self.table.rowCount(); self.table.insertRow(r)

            # Column 0: SG (Material)
            sg = entry["sg"]; mat = entry["material"]
            label = sg if not mat else "{}  [mat:{}]".format(sg, mat)
            self.table.setItem(r, 0, QtWidgets.QTableWidgetItem(label))

            # Column 1: Resolved list
            lw = QtWidgets.QListWidget()
            rs = entry["resolved"]
            if rs:
                lw.addItems(rs)
                lw.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
            else:
                lw.addItem("-- no resolved targets --")
                lw.setEnabled(False)
            self.table.setCellWidget(r, 1, lw)

            # Column 2: Assign Selected
            btn = QtWidgets.QPushButton("Assign Selected")
            btn.clicked.connect(lambda _=None, row=r: self._assign_selected_row(row))
            self.table.setCellWidget(r, 2, btn)

            # Column 3: Result
            self.table.setItem(r, 3, QtWidgets.QTableWidgetItem("-"))

            # tint if unresolved only
            if not rs and entry["unresolved"]:
                self._color_row(r, QtCore.Qt.yellow)

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

    def _color_row(self, row, color_qt):
        for c in range(self.table.columnCount()):
            item = self.table.item(row, c)
            if not item:
                item = QtWidgets.QTableWidgetItem(self.table.item(row, 0).text() if c==0 else "")
                self.table.setItem(row, c, item)
            item.setBackground(color_qt)

    def _row_widgets(self, row):
        sg_label = self.table.item(row, 0).text()
        sg = sg_label.split("  [mat:")[0]
        lw = self.table.cellWidget(row, 1)
        res_item = self.table.item(row, 3)
        return sg, lw, res_item

    def _assign_selected_row(self, row):
        if row < 0: return
        sg, lw, res_item = self._row_widgets(row)
        selected = [i.text() for i in lw.selectedItems()] if lw else []
        selected = [s for s in selected if not s.startswith("-- no resolved")]
        if not selected:
            self._log("[WARN] {}: nothing selected.".format(sg))
            if res_item: res_item.setText("nothing selected")
            return
        self._log("[EXEC] Assign {} item(s) to {} ...".format(len(selected), sg))
        ok, fail = _assign_shapes_to_sg(selected, sg)
        if fail:
            self._color_row(row, QtCore.Qt.red)
            self._log("[FAIL] {}: {} failed".format(sg, len(fail)))
            for shp, reason in fail[:10]:
                self._log("   ! {}  ({})".format(shp, reason))
            if res_item: res_item.setText("fail: {} / {}".format(len(fail), len(selected)))
        else:
            self._color_row(row, QtCore.Qt.green)
            self._log("[OK] {}: assigned {}".format(sg, ok))
            if res_item: res_item.setText("ok: {}".format(ok))

    def _on_assign_all(self):
        if not self.plan:
            self._log("[ERR] Nothing to assign. Scan first."); return
        self._log("[EXEC] Assign All - sequential by rows ...")
        total_ok, total_fail = 0, 0
        for r in range(self.table.rowCount()):
            sg, lw, res_item = self._row_widgets(r)
            self._color_row(r, QtCore.Qt.white)
            entry = self.plan[r]
            targets = entry.get("resolved", [])
            if not targets:
                self._log("[SKIP] {} - no resolved targets.".format(sg))
                if res_item: res_item.setText("skip (no targets)")
                continue
            self._log("[EXEC] {} -> {} target(s)".format(sg, len(targets)))
            ok, fail = _assign_shapes_to_sg(targets, sg)
            total_ok += ok; total_fail += len(fail)
            if fail:
                self._color_row(r, QtCore.Qt.red)
                self._log("[FAIL] {}: {} failed".format(sg, len(fail)))
                for shp, reason in fail[:10]:
                    self._log("   ! {}  ({})".format(shp, reason))
                if res_item: res_item.setText("fail: {} / {}".format(len(fail), len(targets)))
            else:
                self._color_row(r, QtCore.Qt.green)
                self._log("[OK] {}: assigned {}".format(sg, ok))
                if res_item: res_item.setText("ok: {}".format(ok))
        self._log("[DONE] Assign All - success: {}, failed: {}".format(total_ok, total_fail))

    def _on_cell_clicked(self, row, col):
        if col == 0:
            lw = self.table.cellWidget(row, 1)
            if lw and lw.isEnabled():
                lw.selectAll()

# =============================================================================
# Main window with shared namespace bar
# =============================================================================

class MainTools(QtWidgets.QDialog):
    def __init__(self, parent=_maya_main_window()):
        # ensure single instance
        for w in QtWidgets.QApplication.topLevelWidgets():
            if w.objectName() == WIN_OBJECT:
                w.close(); w.deleteLater()
        super(MainTools, self).__init__(parent)
        self.setObjectName(WIN_OBJECT)
        self.setWindowTitle(WIN_TITLE)
        self.setMinimumWidth(1150)
        self.setMinimumHeight(760)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        outer = QtWidgets.QVBoxLayout(self)

        # Shared Namespace Bar
        ns_bar = QtWidgets.QHBoxLayout()
        self.geo_ns_global = QtWidgets.QComboBox(); self.geo_ns_global.setEditable(True)
        self.shd_ns_global = QtWidgets.QComboBox(); self.shd_ns_global.setEditable(True)
        self.btn_refresh_ns = QtWidgets.QPushButton("Refresh")
        ns_bar.addWidget(QtWidgets.QLabel("Geometry NS")); ns_bar.addWidget(self.geo_ns_global, 2)
        ns_bar.addSpacing(14)
        ns_bar.addWidget(QtWidgets.QLabel("Shader NS"));   ns_bar.addWidget(self.shd_ns_global, 2)
        ns_bar.addWidget(self.btn_refresh_ns)
        outer.addLayout(ns_bar)

        # Populate shared combos
        self._refresh_ns_list()

        # Tabs (Shot Build first, then existing tabs)
        tabs = QtWidgets.QTabWidget()
        tabs.addTab(ShotBuildTab(), "Shot Build")
        tabs.addTab(Place3DTab(self.geo_ns_global, self.shd_ns_global), "Place3D Linker")
        tabs.addTab(MatrixPlace3DTab(self.geo_ns_global, self.shd_ns_global), "Matrix Place3D Linker")
        tabs.addTab(BlendShapeTab(self.geo_ns_global), "BlendShape (Anim -> Groom)")
        tabs.addTab(AssignShaderTab(self.geo_ns_global, self.shd_ns_global), "Assign Shader (by Namespace)")
        outer.addWidget(tabs)

        # Wire refresh
        self.btn_refresh_ns.clicked.connect(self._refresh_ns_list)

    def _refresh_ns_list(self):
        ns = _list_namespaces()
        def refill(combo, prefer_contains=None, prefer_suffix=None):
            t = combo.currentText()
            combo.blockSignals(True)
            combo.clear(); combo.addItems(ns)
            # heuristic defaulting
            idx = -1
            if prefer_suffix:
                for i in range(combo.count()):
                    if combo.itemText(i).endswith(prefer_suffix):
                        idx = i; break
            if idx == -1 and prefer_contains:
                for i in range(combo.count()):
                    if prefer_contains in combo.itemText(i):
                        idx = i; break
            if idx >= 0: combo.setCurrentIndex(idx)
            elif t in ns: combo.setCurrentText(t)
            combo.blockSignals(False)

        refill(self.geo_ns_global, prefer_contains="_geo".lower(), prefer_suffix="_geo")
        refill(self.shd_ns_global, prefer_contains="Shade")

def show():
    dlg = MainTools()
    dlg.show()
    return dlg

# Launch
show()
