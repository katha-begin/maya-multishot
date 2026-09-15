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
        self._projects = []

        self._setup_ui()
        self._connect_signals()
        self._load_existing_shots()
        self._load_projects()

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

        # Project picker: only the chosen project is listed
        project_layout = QtWidgets.QHBoxLayout()
        project_layout.addWidget(QtWidgets.QLabel("Project:"))
        self.project_combo = QtWidgets.QComboBox()
        self.project_combo.setMinimumWidth(200)
        project_layout.addWidget(self.project_combo)
        project_layout.addStretch()
        main_layout.addLayout(project_layout)

        # Add filter text box
        filter_layout = QtWidgets.QHBoxLayout()
        filter_label = QtWidgets.QLabel("Filter:")
        filter_layout.addWidget(filter_label)
        self.filter_edit = QtWidgets.QLineEdit()
        self.filter_edit.setPlaceholderText("Type to filter shots...")
        filter_layout.addWidget(self.filter_edit)
        main_layout.addLayout(filter_layout)

        self.tree_widget = QtWidgets.QTreeWidget()
        self.tree_widget.setHeaderLabels(["Episode / Sequence / Shot"])
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
    
    def _current_project_code(self):
        """Project code of the config the Multishot Manager has loaded."""
        try:
            return self._config.get_project_code() if self._config else None
        except Exception:
            return None

    def _load_projects(self):
        """Fill the project picker, the scene's project selected, and list it.

        Only the selected project is scanned and listed; picking another one
        in the combo box lists that project instead.
        """
        from core import shot_discovery

        try:
            self._projects = shot_discovery.list_projects()
        except Exception as e:
            logger.exception("Failed to list project configs: %s", e)
            self._projects = []
            self._add_info_item("Could not list project configs: {}".format(e))
            return

        if not self._projects:
            self._add_info_item("No project configs found in project_configs")
            return

        current = self._current_project_code()
        self.project_combo.blockSignals(True)
        selected = 0
        for index, project in enumerate(self._projects):
            label = project['code']
            if project['code'] == current:
                label = "{}  (current scene)".format(label)
                selected = index
            self.project_combo.addItem(label)
        self.project_combo.setCurrentIndex(selected)
        self.project_combo.blockSignals(False)

        self.project_combo.currentIndexChanged.connect(self._show_project)
        self._show_project(selected)

    def _show_project(self, index):
        """List the shots of the project at ``index`` in the picker."""
        from core import shot_discovery

        self.tree_widget.clear()
        if not 0 <= index < len(self._projects):
            return

        project = self._projects[index]
        if project['error']:
            self._add_info_item("Config error: {}".format(project['error']))
            return

        try:
            base_path = shot_discovery.get_scene_base(project['config'])
            if not base_path or not os.path.isdir(base_path):
                logger.warning("Scene folder for %s not found: %s", project['code'], base_path)
                self._add_info_item("Scene folder not found: {}".format(
                    (base_path or '').replace('\\', '/')))
                return
            episodes = shot_discovery.discover_shots(base_path)
        except Exception as e:
            logger.exception("Failed to discover shots for %s: %s", project['code'], e)
            self._add_info_item("Could not list shots: {}".format(e))
            return

        if not episodes:
            self._add_info_item("No shots found in {}".format(base_path.replace('\\', '/')))
            return

        # Building hundreds of items would otherwise fire itemChanged per item.
        self.tree_widget.blockSignals(True)
        try:
            self._populate_project(project, episodes)
        finally:
            self.tree_widget.blockSignals(False)

        if project['code'] == self._current_project_code():
            # Scene shots belong to the scene's project; another project may
            # reuse the same shot codes.
            self._mark_tree_items(self.tree_widget.invisibleRootItem())

        if self.filter_edit.text():
            self._on_filter_changed(self.filter_edit.text())

    def _populate_project(self, project, episodes):
        for ep_name, sequences in episodes:
            ep_item = self._add_checkable_item(self.tree_widget, ep_name)
            for seq_name, shots in sequences:
                seq_item = self._add_checkable_item(ep_item, seq_name)
                for shot_name in shots:
                    shot_item = self._add_checkable_item(seq_item, shot_name)
                    shot_item.setData(0, QtCore.Qt.UserRole, {
                        'project': project['code'],
                        'config_path': project['config_path'],
                        'ep': ep_name,
                        'seq': seq_name,
                        'shot': shot_name
                    })

    def _add_checkable_item(self, parent, text):
        item = QtWidgets.QTreeWidgetItem([text])
        item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
        item.setCheckState(0, QtCore.Qt.Unchecked)
        if isinstance(parent, QtWidgets.QTreeWidget):
            parent.addTopLevelItem(item)
        else:
            parent.addChild(item)
        return item

    def _add_info_item(self, text):
        """Add a grey, non-selectable line explaining a missing project."""
        item = QtWidgets.QTreeWidgetItem([text])
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        item.setForeground(0, QtGui.QBrush(QtGui.QColor(150, 150, 150)))
        self.tree_widget.addTopLevelItem(item)
        return item
    
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
                    self._clear_item_colors(item, column)
            else:
                self._clear_item_colors(item, column)

        # Propagate to children
        if item.childCount() > 0:
            state = item.checkState(column)
            for i in range(item.childCount()):
                child = item.child(i)
                child.setCheckState(column, state)
    
    @staticmethod
    def _clear_item_colors(item, column):
        """Return an item to the view's default colours.

        Clearing the roles works on PySide2 and PySide6 alike.  The previous
        QBrush(QtCore.Qt.Transparent) raised AttributeError on every unchecked
        item: the colour is spelled Qt.transparent.
        """
        item.setData(column, QtCore.Qt.BackgroundRole, None)
        item.setData(column, QtCore.Qt.ForegroundRole, None)

    def _on_select_all(self):
        self._set_all_check_states(QtCore.Qt.Checked)
    
    def _on_deselect_all(self):
        self._set_all_check_states(QtCore.Qt.Unchecked)
    
    def _set_all_check_states(self, state):
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            if item.flags() & QtCore.Qt.ItemIsUserCheckable:
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

            # Build set of existing shot identifiers (ep, seq, shot)
            for shot in existing_shots:
                self._existing_shots.add(
                    (shot.get_ep_code(), shot.get_seq_code(), shot.get_shot_code()))

            logger.debug("Loaded %d existing shots from scene", len(self._existing_shots))
        except Exception as e:
            logger.exception("Failed to load existing shots: %s", e)

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
                if key in self._existing_shots:
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
