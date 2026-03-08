# -*- coding: utf-8 -*-
"""Add Shot Dialog - Tree view for selecting shots from filesystem."""

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


class AddShotDialog(QtWidgets.QDialog):
    def __init__(self, config, parent=None):
        super(AddShotDialog, self).__init__(parent)

        self._config = config
        self._selected_shots = []
        self._existing_shots = set()  # Store existing shots for persistent checkboxes

        self._setup_ui()
        self._connect_signals()
        self._load_existing_shots()
        self._discover_shots()
    
    def _setup_ui(self):
        self.setWindowTitle("Add Shots")
        self.setModal(True)
        self.setMinimumSize(600, 500)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        instructions = QtWidgets.QLabel("Select shots to add to the scene. Use checkboxes to select multiple shots.")
        instructions.setWordWrap(True)
        main_layout.addWidget(instructions)

        # Add filter text box
        filter_layout = QtWidgets.QHBoxLayout()
        filter_label = QtWidgets.QLabel("Filter:")
        filter_layout.addWidget(filter_label)
        self.filter_edit = QtWidgets.QLineEdit()
        self.filter_edit.setPlaceholderText("Type to filter shots...")
        filter_layout.addWidget(self.filter_edit)
        main_layout.addLayout(filter_layout)

        self.tree_widget = QtWidgets.QTreeWidget()
        self.tree_widget.setHeaderLabels(["Project / Episode / Sequence / Shot"])
        self.tree_widget.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.tree_widget.setAlternatingRowColors(True)
        main_layout.addWidget(self.tree_widget)
        
        selection_layout = QtWidgets.QHBoxLayout()
        self.select_all_btn = QtWidgets.QPushButton("Select All")
        selection_layout.addWidget(self.select_all_btn)
        self.deselect_all_btn = QtWidgets.QPushButton("Deselect All")
        selection_layout.addWidget(self.deselect_all_btn)
        selection_layout.addStretch()
        main_layout.addLayout(selection_layout)
        
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        self.add_btn = QtWidgets.QPushButton("Add Selected")
        self.add_btn.setDefault(True)
        self.add_btn.setMinimumWidth(120)
        button_layout.addWidget(self.add_btn)
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setMinimumWidth(120)
        button_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(button_layout)
    
    def _connect_signals(self):
        self.select_all_btn.clicked.connect(self._on_select_all)
        self.deselect_all_btn.clicked.connect(self._on_deselect_all)
        self.add_btn.clicked.connect(self._on_add_selected)
        self.cancel_btn.clicked.connect(self.reject)
        self.tree_widget.itemChanged.connect(self._on_item_changed)
        self.filter_edit.textChanged.connect(self._on_filter_changed)
    
    def _discover_shots(self):
        if not self._config:
            return
        
        try:
            proj_root = self._config.get_root('projRoot')
            project_code = self._config.get_project_code()
            scene_base = self._config.get_static_path('sceneBase')
            
            if not all([proj_root, project_code, scene_base]):
                return
            
            base_path = os.path.join(proj_root, project_code, scene_base)
            
            if not os.path.exists(base_path):
                logger.warning("Base path does not exist: %s", base_path)
                return
            
            project_item = QtWidgets.QTreeWidgetItem([project_code])
            project_item.setFlags(project_item.flags() | QtCore.Qt.ItemIsUserCheckable)
            project_item.setCheckState(0, QtCore.Qt.Unchecked)
            self.tree_widget.addTopLevelItem(project_item)
            
            self._discover_episodes(base_path, project_item, project_code)
            # Don't expand all - keep tree collapsed by default
            # self.tree_widget.expandAll()  # REMOVED - tree should start collapsed

            # Mark existing shots after discovery
            self._mark_existing_shots()

        except Exception as e:
            logger.error("Failed to discover shots: %s", e)
    
    def _discover_episodes(self, base_path, project_item, project_code):
        for ep_name in sorted(os.listdir(base_path)):
            ep_path = os.path.join(base_path, ep_name)
            if not os.path.isdir(ep_path):
                continue
            if not ep_name.startswith('Ep') and not ep_name.startswith('ep'):
                continue
            
            ep_item = QtWidgets.QTreeWidgetItem([ep_name])
            ep_item.setFlags(ep_item.flags() | QtCore.Qt.ItemIsUserCheckable)
            ep_item.setCheckState(0, QtCore.Qt.Unchecked)
            project_item.addChild(ep_item)
            
            self._discover_sequences(ep_path, ep_item, project_code, ep_name)
    
    def _discover_sequences(self, ep_path, ep_item, project_code, ep_name):
        for seq_name in sorted(os.listdir(ep_path)):
            seq_path = os.path.join(ep_path, seq_name)
            if not os.path.isdir(seq_path):
                continue
            if not seq_name.startswith('sq'):
                continue
            
            seq_item = QtWidgets.QTreeWidgetItem([seq_name])
            seq_item.setFlags(seq_item.flags() | QtCore.Qt.ItemIsUserCheckable)
            seq_item.setCheckState(0, QtCore.Qt.Unchecked)
            ep_item.addChild(seq_item)
            
            self._discover_shot_dirs(seq_path, seq_item, project_code, ep_name, seq_name)
    
    def _discover_shot_dirs(self, seq_path, seq_item, project_code, ep_name, seq_name):
        for shot_name in sorted(os.listdir(seq_path)):
            shot_path = os.path.join(seq_path, shot_name)
            if not os.path.isdir(shot_path):
                continue
            if not shot_name.startswith('SH'):
                continue
            
            shot_item = QtWidgets.QTreeWidgetItem([shot_name])
            shot_item.setFlags(shot_item.flags() | QtCore.Qt.ItemIsUserCheckable)
            shot_item.setCheckState(0, QtCore.Qt.Unchecked)
            shot_item.setData(0, QtCore.Qt.UserRole, {
                'project': project_code,
                'ep': ep_name,
                'seq': seq_name,
                'shot': shot_name
            })
            seq_item.addChild(shot_item)
    
    def _on_item_changed(self, item, column):
        # Set orange color when checked
        if item.checkState(column) == QtCore.Qt.Checked:
            item.setBackground(column, QtGui.QBrush(QtGui.QColor(255, 165, 0)))
            item.setForeground(column, QtGui.QBrush(QtGui.QColor(0, 0, 0)))  # Black text
        else:
            # Only clear color if shot is not in existing shots
            shot_data = item.data(0, QtCore.Qt.UserRole)
            if shot_data:
                key = (shot_data['ep'], shot_data['seq'], shot_data['shot'])
                if key not in self._existing_shots:
                    item.setBackground(column, QtGui.QBrush(QtCore.Qt.Transparent))
                    item.setForeground(column, QtGui.QBrush(QtGui.QColor()))  # Default text color
            else:
                item.setBackground(column, QtGui.QBrush(QtCore.Qt.Transparent))
                item.setForeground(column, QtGui.QBrush(QtGui.QColor()))  # Default text color

        # Propagate to children
        if item.childCount() > 0:
            state = item.checkState(column)
            for i in range(item.childCount()):
                child = item.child(i)
                child.setCheckState(column, state)
    
    def _on_select_all(self):
        self._set_all_check_states(QtCore.Qt.Checked)
    
    def _on_deselect_all(self):
        self._set_all_check_states(QtCore.Qt.Unchecked)
    
    def _set_all_check_states(self, state):
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            item.setCheckState(0, state)
    
    def _on_add_selected(self):
        self._selected_shots = []
        self._collect_selected_shots(self.tree_widget.invisibleRootItem())
        
        if not self._selected_shots:
            QtWidgets.QMessageBox.warning(self, "No Selection", "Please select at least one shot.")
            return
        
        self.accept()
    
    def _collect_selected_shots(self, parent_item):
        for i in range(parent_item.childCount()):
            item = parent_item.child(i)
            
            if item.childCount() == 0:
                if item.checkState(0) == QtCore.Qt.Checked:
                    shot_data = item.data(0, QtCore.Qt.UserRole)
                    if shot_data:
                        self._selected_shots.append(shot_data)
            else:
                self._collect_selected_shots(item)
    
    def get_selected_shots(self):
        return self._selected_shots

    def _load_existing_shots(self):
        """Load existing shots from the scene to mark them as already added."""
        try:
            from core.context import ContextManager
            ctx = ContextManager()
            existing_shots = ctx.get_all_shots()

            print("=== DEBUG: Loading existing shots ===")
            print("Found {} shots in scene".format(len(existing_shots)))

            # Build set of existing shot identifiers (ep, seq, shot)
            for shot in existing_shots:
                ep = shot.get_ep_code()
                seq = shot.get_seq_code()
                shot_code = shot.get_shot_code()
                self._existing_shots.add((ep, seq, shot_code))
                print("  Existing shot: ep='{}', seq='{}', shot='{}'".format(ep, seq, shot_code))
                logger.debug("Loaded existing shot: {} / {} / {}".format(ep, seq, shot_code))

            print("Total existing shots loaded: {}".format(len(self._existing_shots)))
            print("Existing shots set: {}".format(self._existing_shots))
            logger.info("Loaded {} existing shots from scene: {}".format(
                len(self._existing_shots), self._existing_shots))
        except Exception as e:
            print("ERROR loading existing shots: {}".format(e))
            import traceback
            traceback.print_exc()
            logger.warning("Failed to load existing shots: {}".format(e))

    def _mark_existing_shots(self):
        """Mark tree items for shots that already exist in the scene."""
        logger.info("Starting to mark {} existing shots in tree".format(len(self._existing_shots)))
        self._mark_tree_items(self.tree_widget.invisibleRootItem())
        logger.info("Finished marking existing shots")

    def _mark_tree_items(self, parent_item):
        """Recursively mark tree items that match existing shots.

        Args:
            parent_item: Parent tree widget item to process
        """
        for i in range(parent_item.childCount()):
            item = parent_item.child(i)
            shot_data = item.data(0, QtCore.Qt.UserRole)

            if shot_data:
                # This is a shot item
                key = (shot_data['ep'], shot_data['seq'], shot_data['shot'])
                print("  Checking tree item: ep='{}', seq='{}', shot='{}'".format(
                    shot_data['ep'], shot_data['seq'], shot_data['shot']))
                print("    Key: {}".format(key))
                print("    In existing_shots? {}".format(key in self._existing_shots))

                logger.debug("Checking shot item: {} / {} / {}".format(
                    shot_data['ep'], shot_data['seq'], shot_data['shot']))

                if key in self._existing_shots:
                    print("    >>> MARKING AS CHECKED AND ORANGE <<<")
                    logger.info("Marking existing shot as checked: {} / {} / {}".format(
                        shot_data['ep'], shot_data['seq'], shot_data['shot']))
                    # Block signals to avoid triggering itemChanged
                    self.tree_widget.blockSignals(True)
                    item.setCheckState(0, QtCore.Qt.Checked)
                    # Set orange background with black text
                    item.setBackground(0, QtGui.QBrush(QtGui.QColor(255, 165, 0)))
                    item.setForeground(0, QtGui.QBrush(QtGui.QColor(0, 0, 0)))  # Black text
                    self.tree_widget.blockSignals(False)

            # Recurse to children
            if item.childCount() > 0:
                self._mark_tree_items(item)

    def _on_filter_changed(self, text):
        """Handle filter text change.

        Args:
            text (str): Filter text
        """
        filter_text = text.lower()
        self._filter_tree_items(self.tree_widget.invisibleRootItem(), filter_text)

    def _filter_tree_items(self, parent_item, filter_text):
        """Recursively filter tree items based on text.

        Args:
            parent_item: Parent tree widget item to process
            filter_text (str): Lowercase filter text

        Returns:
            bool: True if this item or any child should be visible
        """
        has_visible_child = False

        for i in range(parent_item.childCount()):
            item = parent_item.child(i)
            item_text = item.text(0).lower()

            # Check if this item matches
            matches = filter_text in item_text if filter_text else True

            # Check children recursively
            child_visible = False
            if item.childCount() > 0:
                child_visible = self._filter_tree_items(item, filter_text)

            # Item is visible if it matches OR has visible children
            is_visible = matches or child_visible
            item.setHidden(not is_visible)

            if is_visible:
                has_visible_child = True
                # Expand item if filter is active and it has visible children
                if filter_text and child_visible:
                    item.setExpanded(True)
            else:
                # Collapse hidden items
                item.setExpanded(False)

        return has_visible_child
