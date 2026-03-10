# -*- coding: utf-8 -*-
"""Slate Manager Dialog -- manage render layer renderable overrides per shot.

Mirrors GafferManagerDialog structure exactly.
Two-panel layout:
  Left  -- slate selector list + action buttons
  Right -- layer table (Layer Name / Renderable / Override / Source)
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui

try:
    from maya import cmds
except ImportError:
    cmds = None

from core.slate.manager import SlateManager
from core.slate.resolver import SlateResolver
from core.nodes.wrappers.slate import CTXSlateNode

logger = logging.getLogger(__name__)


class SlateManagerDialog(QtWidgets.QMainWindow):
    """Dockable Slate Manager -- per-shot render layer renderable control.

    Mirrors GafferManagerDialog structure exactly.
    """

    _instance = None

    @staticmethod
    def _maya_main_window():
        """Return Maya's main window as a Qt widget, or None outside Maya."""
        try:
            from maya import OpenMayaUI
            try:
                import shiboken6 as shiboken
            except ImportError:
                import shiboken2 as shiboken
            ptr = OpenMayaUI.MQtUtil.mainWindow()
            if ptr:
                return shiboken.wrapInstance(int(ptr), QtWidgets.QWidget)
        except Exception:
            pass
        return None

    @classmethod
    def open_or_raise(cls, parent=None):
        """Return existing instance (raised to front) or create new one.

        Args:
            parent (QWidget|None): Parent widget.

        Returns:
            SlateManagerDialog: The singleton instance.
        """
        if cls._instance is not None:
            try:
                cls._instance.raise_()
                cls._instance.activateWindow()
                return cls._instance
            except RuntimeError:
                cls._instance = None

        if parent is None:
            parent = cls._maya_main_window()

        instance = cls(parent=parent)
        instance.show()
        cls._instance = instance
        return instance

    def __init__(self, parent=None):
        super(SlateManagerDialog, self).__init__(parent)
        self.setObjectName('SlateManagerDialog')
        self.setWindowTitle('Slate Manager')
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self.resize(460, 600)

        self._current_slate = None   # CTXSlateNode currently selected
        self._edit_mode = False
        self._snapshot = {}          # {layer_name: {renderable, renderableEnabled}}

        self._setup_ui()
        self._connect_signals()
        self._refresh_slate_list()

    def closeEvent(self, event):
        """Clear instance reference on close."""
        SlateManagerDialog._instance = None
        super(SlateManagerDialog, self).closeEvent(event)

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        """Build the full window layout."""
        self._setup_menu()

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        # Lock banner (hidden by default)
        self._lock_banner = QtWidgets.QLabel('')
        self._lock_banner.setAlignment(QtCore.Qt.AlignCenter)
        self._lock_banner.setStyleSheet(
            'background-color: #B8860B; color: white; font-weight: bold; padding: 4px;'
        )
        self._lock_banner.setVisible(False)
        main_layout.addWidget(self._lock_banner)

        # Splitter: left panel | right panel
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        main_layout.addWidget(splitter, stretch=1)

        # Left panel
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        left_widget.setMinimumWidth(160)
        left_widget.setMaximumWidth(220)

        self._slate_list = QtWidgets.QListWidget()
        self._slate_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        left_layout.addWidget(self._slate_list)

        left_btn_layout = QtWidgets.QHBoxLayout()
        self._new_slate_btn = QtWidgets.QPushButton('+ New Slate')
        self._set_parent_btn = QtWidgets.QPushButton('Set Parent...')
        self._remove_slate_btn = QtWidgets.QPushButton('Remove')
        left_btn_layout.addWidget(self._new_slate_btn)
        left_btn_layout.addWidget(self._set_parent_btn)
        left_btn_layout.addWidget(self._remove_slate_btn)
        left_layout.addLayout(left_btn_layout)

        splitter.addWidget(left_widget)

        # Right panel
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        self._layer_table = QtWidgets.QTableWidget()
        self._layer_table.setColumnCount(4)
        self._layer_table.setHorizontalHeaderLabels(
            ['Layer Name', 'Renderable', 'Override', 'Source']
        )

        header = self._layer_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self._layer_table.setColumnWidth(1, 70)
        self._layer_table.setColumnWidth(2, 60)
        self._layer_table.setColumnWidth(3, 70)

        self._layer_table.setAlternatingRowColors(True)
        self._layer_table.verticalHeader().setDefaultSectionSize(22)
        self._layer_table.verticalHeader().setVisible(False)
        self._layer_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._layer_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        right_layout.addWidget(self._layer_table)

        layer_btn_layout = QtWidgets.QHBoxLayout()
        self._add_layer_btn = QtWidgets.QPushButton('Add Layer')
        self._remove_layer_btn = QtWidgets.QPushButton('Remove Layer')
        layer_btn_layout.addWidget(self._add_layer_btn)
        layer_btn_layout.addWidget(self._remove_layer_btn)
        layer_btn_layout.addStretch()
        right_layout.addLayout(layer_btn_layout)

        splitter.addWidget(right_widget)
        splitter.setSizes([180, 280])

        # Bottom bar
        bottom_layout = QtWidgets.QHBoxLayout()
        bottom_layout.addStretch()

        self._edit_btn = QtWidgets.QPushButton('Edit')
        self._commit_btn = QtWidgets.QPushButton('Commit')
        self._cancel_btn = QtWidgets.QPushButton('Cancel')

        self._commit_btn.setEnabled(False)
        self._cancel_btn.setEnabled(False)

        bottom_layout.addWidget(self._edit_btn)
        bottom_layout.addWidget(self._commit_btn)
        bottom_layout.addWidget(self._cancel_btn)

        main_layout.addLayout(bottom_layout)

    def _setup_menu(self):
        """Create menuBar with Tools > Settings."""
        menubar = self.menuBar()
        tools_menu = menubar.addMenu('Tools')
        settings_action = QtWidgets.QAction('Settings', self)
        settings_action.triggered.connect(self._open_settings)
        tools_menu.addAction(settings_action)

    def _connect_signals(self):
        """Wire all button and list signals."""
        self._slate_list.currentItemChanged.connect(self._on_slate_selected)
        self._new_slate_btn.clicked.connect(self._on_new_slate)
        self._set_parent_btn.clicked.connect(self._on_set_parent)
        self._remove_slate_btn.clicked.connect(self._on_remove_slate)
        self._add_layer_btn.clicked.connect(self._on_add_layer)
        self._remove_layer_btn.clicked.connect(self._on_remove_layer)
        self._edit_btn.clicked.connect(self._enter_edit_mode)
        self._commit_btn.clicked.connect(self._commit_edit)
        self._cancel_btn.clicked.connect(self._cancel_edit)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def select_slate(self, slate):
        """Pre-select a slate in the left panel.

        Args:
            slate (CTXSlateNode|str): Slate node or node name to select.
        """
        if slate is None:
            return

        target_name = slate if isinstance(slate, str) else slate.node_name

        for i in range(self._slate_list.count()):
            item = self._slate_list.item(i)
            node = item.data(QtCore.Qt.UserRole)
            if node is not None and node.node_name == target_name:
                self._slate_list.setCurrentItem(item)
                return

        # Not found -- refresh list and try again
        self._refresh_slate_list()
        for i in range(self._slate_list.count()):
            item = self._slate_list.item(i)
            node = item.data(QtCore.Qt.UserRole)
            if node is not None and node.node_name == target_name:
                self._slate_list.setCurrentItem(item)
                return

    def refresh(self):
        """Refresh both panels from the current scene state."""
        self._refresh_slate_list()
        self._refresh_layer_table()

    def show_lock_banner(self, message):
        """Show the lock banner with a message.

        Args:
            message (str): Banner message text.
        """
        self._lock_banner.setText(message)
        self._lock_banner.setVisible(True)

    def hide_lock_banner(self):
        """Hide the lock banner."""
        self._lock_banner.setVisible(False)

    # ------------------------------------------------------------------
    # Left panel helpers
    # ------------------------------------------------------------------

    def _refresh_slate_list(self):
        """Repopulate the left panel from CTXSlateNode.list_all()."""
        current_node_name = None
        current_item = self._slate_list.currentItem()
        if current_item is not None:
            node = current_item.data(QtCore.Qt.UserRole)
            if node is not None:
                current_node_name = node.node_name

        self._slate_list.blockSignals(True)
        self._slate_list.clear()

        try:
            slates = CTXSlateNode.list_all()
        except Exception as exc:
            logger.warning('Failed to list slates: %s', exc)
            slates = []

        for sn in slates:
            try:
                slate_name = sn.get_attribute('slateName') or sn.node_name
                slate_type = sn.get_attribute('slateType') or '?'
                label = '{} [{}]'.format(slate_name, slate_type)
            except Exception:
                label = sn.node_name

            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.UserRole, sn)
            self._slate_list.addItem(item)

        self._slate_list.blockSignals(False)

        # Restore selection
        if current_node_name:
            for i in range(self._slate_list.count()):
                item = self._slate_list.item(i)
                node = item.data(QtCore.Qt.UserRole)
                if node is not None and node.node_name == current_node_name:
                    self._slate_list.setCurrentItem(item)
                    return

        # If nothing selected and list not empty, select first item
        if self._slate_list.count() > 0 and self._slate_list.currentItem() is None:
            self._slate_list.setCurrentRow(0)

    def _on_slate_selected(self, current, previous):
        """Handle slate selection change."""
        if current is None:
            self._current_slate = None
            self._refresh_layer_table()
            return

        node = current.data(QtCore.Qt.UserRole)
        self._current_slate = node
        self._refresh_layer_table()

    # ------------------------------------------------------------------
    # Right panel helpers
    # ------------------------------------------------------------------

    def _refresh_layer_table(self):
        """Redraw the layer table for the currently selected slate."""
        self._layer_table.setRowCount(0)
        if self._current_slate is None:
            return

        # Resolve chain for source indicators
        try:
            resolved = SlateResolver.resolve_layer_state(self._current_slate)
        except Exception as exc:
            logger.warning('SlateResolver failed: %s', exc)
            resolved = {}

        try:
            layers = self._current_slate.get_layers()
        except Exception as exc:
            logger.warning('get_layers failed: %s', exc)
            layers = []

        self._layer_table.setRowCount(len(layers))

        for row, layer_entry in enumerate(layers):
            try:
                name = layer_entry.get_layer_name()
                renderable = layer_entry.get_renderable()
                override_enabled = layer_entry.is_override_enabled()
            except Exception:
                name = '?'
                renderable = True
                override_enabled = False

            # Col 0: Layer Name (read-only)
            name_item = QtWidgets.QTableWidgetItem(name)
            name_item.setFlags(QtCore.Qt.ItemIsEnabled)
            self._layer_table.setItem(row, 0, name_item)

            # Col 1: Renderable checkbox
            renderable_cb = QtWidgets.QCheckBox()
            renderable_cb.setChecked(renderable)
            renderable_cb.setEnabled(self._edit_mode and override_enabled)
            self._layer_table.setCellWidget(row, 1, self._center_widget(renderable_cb))

            # Col 2: Override checkbox (renderableEnabled)
            override_cb = QtWidgets.QCheckBox()
            override_cb.setChecked(override_enabled)
            override_cb.setEnabled(self._edit_mode)
            # When override toggled, enable/disable renderable checkbox
            override_cb.stateChanged.connect(
                lambda state, rcb=renderable_cb: rcb.setEnabled(
                    self._edit_mode and bool(state)
                )
            )
            self._layer_table.setCellWidget(row, 2, self._center_widget(override_cb))

            # Col 3: Source indicator
            layer_state = resolved.get(name, {})
            if not layer_state.get('overridden'):
                source_text = '(-)'
            elif layer_state.get('source') == self._current_slate.node_name:
                source_text = '(own)'
            else:
                source_node = layer_state.get('source', '')
                source_text = '(inh)'
                if source_node and cmds is not None:
                    try:
                        slate_type = cmds.getAttr('{}.slateType'.format(source_node))
                        # Show first 3 chars of type: 'seq', 'mas', 'sho' etc.
                        source_text = '({})'.format(str(slate_type)[:3])
                    except Exception:
                        pass

            source_item = QtWidgets.QTableWidgetItem(source_text)
            source_item.setFlags(QtCore.Qt.ItemIsEnabled)
            source_item.setForeground(
                QtGui.QColor('#CCCCCC') if source_text == '(own)' else QtGui.QColor('#888888')
            )
            self._layer_table.setItem(row, 3, source_item)

    def _center_widget(self, widget):
        """Wrap a widget in a centered container for table cells.

        Args:
            widget (QWidget): Widget to center.

        Returns:
            QWidget: Container widget.
        """
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.addWidget(widget)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        return container

    # ------------------------------------------------------------------
    # Edit mode
    # ------------------------------------------------------------------

    def _enter_edit_mode(self):
        """Snapshot current state; enable checkboxes."""
        if self._current_slate is None:
            return
        self._snapshot = self._capture_snapshot()
        self._edit_mode = True
        self._edit_btn.setEnabled(False)
        self._commit_btn.setEnabled(True)
        self._cancel_btn.setEnabled(True)
        self._refresh_layer_table()

    def _commit_edit(self):
        """Write table state to CTX nodes (snapshot-diff pattern)."""
        if self._current_slate is None:
            self._exit_edit_mode()
            return

        current_state = self._read_table_state()
        for layer_name, state in current_state.items():
            snap = self._snapshot.get(layer_name, {})
            try:
                layer_entry = self._current_slate.get_layer_by_name(layer_name)
            except Exception:
                layer_entry = None
            if layer_entry is None:
                continue
            try:
                if state['renderableEnabled'] != snap.get('renderableEnabled'):
                    layer_entry.set_override_enabled(state['renderableEnabled'])
                if state['renderable'] != snap.get('renderable'):
                    layer_entry.set_renderable(state['renderable'])
            except Exception as exc:
                logger.error('Failed to write layer %s: %s', layer_name, exc)

        self._exit_edit_mode()

    def _cancel_edit(self):
        """Restore snapshot to CTX nodes."""
        if self._current_slate is None:
            self._exit_edit_mode()
            return

        for layer_name, state in self._snapshot.items():
            try:
                layer_entry = self._current_slate.get_layer_by_name(layer_name)
            except Exception:
                layer_entry = None
            if layer_entry is None:
                continue
            try:
                layer_entry.set_renderable(state['renderable'])
                layer_entry.set_override_enabled(state['renderableEnabled'])
            except Exception as exc:
                logger.error('Failed to restore layer %s: %s', layer_name, exc)

        self._exit_edit_mode()

    def _exit_edit_mode(self):
        """Exit edit mode and refresh the table."""
        self._edit_mode = False
        self._snapshot = {}
        self._edit_btn.setEnabled(True)
        self._commit_btn.setEnabled(False)
        self._cancel_btn.setEnabled(False)
        self._refresh_layer_table()

    # ------------------------------------------------------------------
    # Snapshot helpers
    # ------------------------------------------------------------------

    def _capture_snapshot(self):
        """Capture current layer state from CTX nodes.

        Returns:
            dict: {layer_name: {renderable: bool, renderableEnabled: bool}}
        """
        snap = {}
        if self._current_slate is None:
            return snap
        try:
            for layer_entry in self._current_slate.get_layers():
                name = layer_entry.get_layer_name()
                if name:
                    snap[name] = {
                        'renderable': layer_entry.get_renderable(),
                        'renderableEnabled': layer_entry.is_override_enabled(),
                    }
        except Exception as exc:
            logger.warning('Snapshot capture failed: %s', exc)
        return snap

    def _read_table_state(self):
        """Read current widget state from the layer table.

        Returns:
            dict: {layer_name: {renderable: bool, renderableEnabled: bool}}
        """
        state = {}
        for row in range(self._layer_table.rowCount()):
            name_item = self._layer_table.item(row, 0)
            if name_item is None:
                continue
            name = name_item.text()

            renderable = False
            rnd_container = self._layer_table.cellWidget(row, 1)
            if rnd_container is not None:
                cb = rnd_container.findChild(QtWidgets.QCheckBox)
                if cb is not None:
                    renderable = cb.isChecked()

            override_enabled = False
            ov_container = self._layer_table.cellWidget(row, 2)
            if ov_container is not None:
                cb = ov_container.findChild(QtWidgets.QCheckBox)
                if cb is not None:
                    override_enabled = cb.isChecked()

            state[name] = {
                'renderable': renderable,
                'renderableEnabled': override_enabled,
            }
        return state

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_new_slate(self):
        """Create a new CTXSlateNode after prompting for name and type."""
        slate_name, ok = QtWidgets.QInputDialog.getText(
            self, 'New Slate', 'Slate name:'
        )
        if not ok or not slate_name.strip():
            return

        slate_type_options = ['master', 'sequence', 'shot']
        slate_type, ok2 = QtWidgets.QInputDialog.getItem(
            self, 'New Slate', 'Slate type:', slate_type_options, 0, False
        )
        if not ok2:
            return

        try:
            new_slate = CTXSlateNode.create(
                slateName=slate_name.strip(),
                slateType=slate_type,
                scopeCode=slate_name.strip(),
            )
            logger.info('Created new slate: %s (%s)', new_slate.node_name, slate_type)
        except Exception as exc:
            logger.error('Failed to create slate: %s', exc)
            QtWidgets.QMessageBox.critical(
                self, 'Error', 'Failed to create slate:\n{}'.format(exc)
            )
            return

        self._refresh_slate_list()
        self.select_slate(new_slate)

    def _on_set_parent(self):
        """Open a dialog to pick a parent slate for the currently selected slate."""
        if self._current_slate is None:
            QtWidgets.QMessageBox.information(
                self, 'No Slate Selected', 'Select a slate first.'
            )
            return

        try:
            all_slates = CTXSlateNode.list_all()
        except Exception:
            all_slates = []

        # Exclude current slate from candidates
        candidates = [
            sn for sn in all_slates
            if sn.node_name != self._current_slate.node_name
        ]

        if not candidates:
            QtWidgets.QMessageBox.information(
                self, 'No Candidates', 'No other slates available to use as parent.'
            )
            return

        labels = []
        for sn in candidates:
            try:
                slate_name = sn.get_attribute('slateName') or sn.node_name
                slate_type = sn.get_attribute('slateType') or '?'
                labels.append('{} [{}]'.format(slate_name, slate_type))
            except Exception:
                labels.append(sn.node_name)

        choice, ok = QtWidgets.QInputDialog.getItem(
            self, 'Set Parent Slate', 'Select parent slate:', labels, 0, False
        )
        if not ok:
            return

        idx = labels.index(choice)
        parent_slate = candidates[idx]

        try:
            self._current_slate.set_parent_slate(parent_slate)
            logger.info(
                'Set parent of %s to %s',
                self._current_slate.node_name, parent_slate.node_name
            )
        except Exception as exc:
            logger.error('Failed to set parent slate: %s', exc)
            QtWidgets.QMessageBox.critical(
                self, 'Error', 'Failed to set parent:\n{}'.format(exc)
            )

    def _on_remove_slate(self):
        """Remove the currently selected slate node from the scene."""
        if self._current_slate is None:
            return

        try:
            slate_name = self._current_slate.get_attribute('slateName') or self._current_slate.node_name
        except Exception:
            slate_name = self._current_slate.node_name

        reply = QtWidgets.QMessageBox.question(
            self,
            'Remove Slate',
            'Remove slate "{}"?'.format(slate_name),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        try:
            if cmds is not None:
                cmds.delete(self._current_slate.node_name)
            self._current_slate = None
        except Exception as exc:
            logger.error('Failed to delete slate: %s', exc)
            QtWidgets.QMessageBox.critical(
                self, 'Error', 'Failed to remove slate:\n{}'.format(exc)
            )

        self._refresh_slate_list()
        self._refresh_layer_table()

    def _on_add_layer(self):
        """Open popup to select render layers from the current scene."""
        if self._current_slate is None:
            return

        try:
            from core.batch.render_setup_manager import RenderSetupManager
            all_layers = RenderSetupManager().get_all_layers()
        except Exception:
            all_layers = []

        if not all_layers:
            QtWidgets.QMessageBox.information(
                self, 'No Layers',
                'No render layers found in the current scene.'
            )
            return

        # Exclude layers already in the slate
        try:
            existing_names = {l.get_layer_name() for l in self._current_slate.get_layers()}
        except Exception:
            existing_names = set()

        available = [l for l in all_layers if l.name not in existing_names]

        if not available:
            QtWidgets.QMessageBox.information(
                self, 'All Layers Added',
                'All scene render layers are already in this slate.'
            )
            return

        dlg = _AddLayerDialog(available, parent=self)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        selected_names = dlg.get_selected_layer_names()
        for name in selected_names:
            try:
                self._current_slate.add_layer(name, renderable=True, enabled=False)
                logger.info('Added layer %r to slate %s', name, self._current_slate.node_name)
            except Exception as exc:
                logger.error('Failed to add layer %r: %s', name, exc)

        self._refresh_layer_table()

    def _on_remove_layer(self):
        """Remove the selected layer row from the current slate."""
        if self._current_slate is None:
            return

        selected_rows = self._layer_table.selectionModel().selectedRows()
        if not selected_rows:
            return

        for index in selected_rows:
            row = index.row()
            name_item = self._layer_table.item(row, 0)
            if name_item is None:
                continue
            layer_name = name_item.text()
            try:
                self._current_slate.remove_layer(layer_name)
                logger.info('Removed layer %r from slate %s', layer_name, self._current_slate.node_name)
            except Exception as exc:
                logger.error('Failed to remove layer %r: %s', layer_name, exc)

        self._refresh_layer_table()

    def _open_settings(self):
        """Open a basic settings dialog (placeholder)."""
        QtWidgets.QMessageBox.information(
            self, 'Settings', 'Slate Manager settings are not yet implemented.'
        )


class _AddLayerDialog(QtWidgets.QDialog):
    """Popup to pick render layers to add to a slate.

    Mirrors AddShotDialog pattern from batch_render_dialog.
    """

    def __init__(self, layers, parent=None):
        """
        Args:
            layers (list[RenderLayerInfo]): Available layers.
            parent (QWidget|None): Parent widget.
        """
        super(_AddLayerDialog, self).__init__(parent)
        self.setWindowTitle('Add Layers to Slate')
        self.resize(300, 400)
        self._layers = layers

        layout = QtWidgets.QVBoxLayout(self)

        # Filter box
        self._filter = QtWidgets.QLineEdit()
        self._filter.setPlaceholderText('Filter...')
        self._filter.textChanged.connect(self._apply_filter)
        layout.addWidget(self._filter)

        # List with checkboxes
        self._list = QtWidgets.QListWidget()
        self._list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        for layer in layers:
            item = QtWidgets.QListWidgetItem(layer.name)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Unchecked)
            self._list.addItem(item)
        layout.addWidget(self._list)

        # OK / Cancel buttons
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _apply_filter(self, text):
        """Show/hide list items based on filter text.

        Args:
            text (str): Filter string.
        """
        for i in range(self._list.count()):
            item = self._list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def get_selected_layer_names(self):
        """Return list of checked layer names.

        Returns:
            list[str]: Names of checked layers.
        """
        result = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.checkState() == QtCore.Qt.Checked:
                result.append(item.text())
        return result
