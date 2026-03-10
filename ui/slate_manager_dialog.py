# -*- coding: utf-8 -*-
"""Slate Manager Dialog -- manage render layer renderable overrides per shot.

Layout mirrors GafferManagerDialog exactly:
  Row 1: Slate combo + Refresh | + Create  Set Parent  Clear Parent  Remove
  Row 2: Chain: -
  Row 3: Edit Mode: OFF            [Enter Edit Mode] [Commit] [Discard]
  Sep:   horizontal line
  Body:  Search layers... + full-width layer table
  Btns:  + Add Layer   - Remove Layer        Apply Slate
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

    Layout identical to GafferManagerDialog.
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
        """Return existing instance (raised to front) or create new one."""
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
        self.resize(545, 600)

        self._current_slate = None
        self._edit_mode = False
        self._snapshot = {}

        self._setup_ui()
        self._connect_signals()
        self._refresh_slate_combo()

    def closeEvent(self, event):
        """Clear instance reference on close."""
        SlateManagerDialog._instance = None
        QtWidgets.QMainWindow.closeEvent(self, event)

    def showEvent(self, event):
        """Refresh combo on reopen so scene state is always current."""
        QtWidgets.QMainWindow.showEvent(self, event)
        self._refresh_slate_combo()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        """Build the full window layout -- mirrors GafferManagerDialog."""
        self._setup_menu()

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        # Lock banner (hidden by default)
        self._lock_banner = QtWidgets.QLabel('')
        self._lock_banner.setStyleSheet(
            'background-color: #7B3F00; color: #FFD54F; '
            'padding: 4px 8px; font-weight: bold;'
        )
        self._lock_banner.setVisible(False)
        self._lock_banner.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(self._lock_banner)

        # ── Compact header (mirrors gaffer header exactly) ──────────────
        header_widget = QtWidgets.QWidget()
        header_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        header_layout = QtWidgets.QVBoxLayout(header_widget)
        header_layout.setContentsMargins(4, 4, 4, 4)
        header_layout.setSpacing(3)

        # Row 1: slate combo + all action buttons
        slate_row = QtWidgets.QHBoxLayout()
        slate_row.setSpacing(4)

        lbl = QtWidgets.QLabel('Slate:')
        lbl.setFixedWidth(40)
        slate_row.addWidget(lbl)

        self._slate_combo = QtWidgets.QComboBox()
        self._slate_combo.setMinimumWidth(180)
        self._slate_combo.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        slate_row.addWidget(self._slate_combo)

        self._refresh_button = QtWidgets.QPushButton('Refresh')
        self._refresh_button.setFixedWidth(70)
        slate_row.addWidget(self._refresh_button)

        sep1 = QtWidgets.QFrame()
        sep1.setFrameShape(QtWidgets.QFrame.VLine)
        sep1.setFrameShadow(QtWidgets.QFrame.Sunken)
        slate_row.addWidget(sep1)

        self._create_slate_button = QtWidgets.QPushButton('+ Create')
        self._create_slate_button.setFixedWidth(75)
        self._create_slate_button.setToolTip('Create a new slate for a sequence or shot')
        slate_row.addWidget(self._create_slate_button)

        self._set_parent_button = QtWidgets.QPushButton('Set Parent')
        self._set_parent_button.setFixedWidth(80)
        self._set_parent_button.setToolTip('Set a parent slate to inherit its layer overrides')
        slate_row.addWidget(self._set_parent_button)

        self._clear_parent_button = QtWidgets.QPushButton('Clear Parent')
        self._clear_parent_button.setFixedWidth(85)
        self._clear_parent_button.setToolTip('Remove parent slate connection')
        slate_row.addWidget(self._clear_parent_button)

        self._remove_slate_button = QtWidgets.QPushButton('Remove')
        self._remove_slate_button.setFixedWidth(65)
        self._remove_slate_button.setToolTip('Delete the selected slate node')
        slate_row.addWidget(self._remove_slate_button)

        header_layout.addLayout(slate_row)

        # Row 2: chain info
        info_row = QtWidgets.QHBoxLayout()
        info_row.setSpacing(12)
        self._chain_label = QtWidgets.QLabel('Chain: -')
        self._chain_label.setStyleSheet('color: #888; font-style: italic; font-size: 11px;')
        info_row.addWidget(self._chain_label)
        info_row.addStretch()
        header_layout.addLayout(info_row)

        # Row 3: edit mode bar
        edit_row = QtWidgets.QHBoxLayout()
        edit_row.setSpacing(4)

        self._edit_mode_label = QtWidgets.QLabel('Edit Mode: OFF')
        self._edit_mode_label.setStyleSheet('font-weight: bold; font-size: 11px;')
        edit_row.addWidget(self._edit_mode_label)
        edit_row.addStretch()

        self._enter_edit_button = QtWidgets.QPushButton('Enter Edit Mode')
        self._enter_edit_button.setFixedWidth(130)
        self._enter_edit_button.setStyleSheet('background-color: #37474F; color: white;')
        edit_row.addWidget(self._enter_edit_button)

        self._commit_button = QtWidgets.QPushButton('Commit Changes')
        self._commit_button.setFixedWidth(130)
        self._commit_button.setStyleSheet('background-color: #2E7D32; color: white;')
        self._commit_button.setVisible(False)
        edit_row.addWidget(self._commit_button)

        self._discard_button = QtWidgets.QPushButton('Discard Changes')
        self._discard_button.setFixedWidth(130)
        self._discard_button.setStyleSheet('background-color: #B71C1C; color: white;')
        self._discard_button.setVisible(False)
        edit_row.addWidget(self._discard_button)

        header_layout.addLayout(edit_row)

        # Thin horizontal separator under header
        sep_h = QtWidgets.QFrame()
        sep_h.setFrameShape(QtWidgets.QFrame.HLine)
        sep_h.setFrameShadow(QtWidgets.QFrame.Sunken)
        header_layout.addWidget(sep_h)

        main_layout.addWidget(header_widget)

        # ── Body: search box + layer table ─────────────────────────────
        body_widget = QtWidgets.QWidget()
        body_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        body_layout = QtWidgets.QVBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(3)

        # Search box
        self._search_box = QtWidgets.QLineEdit()
        self._search_box.setPlaceholderText('Search layers...')
        self._search_box.setClearButtonEnabled(True)
        self._search_box.setFixedHeight(24)
        body_layout.addWidget(self._search_box)

        # Layer table (full width -- no splitter)
        self._layer_table = QtWidgets.QTableWidget()
        self._layer_table.setColumnCount(2)
        self._layer_table.setHorizontalHeaderLabels(
            ['Layer', 'Renderable']
        )

        tbl_header = self._layer_table.horizontalHeader()
        tbl_header.setStretchLastSection(False)
        tbl_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        tbl_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        self._layer_table.setColumnWidth(1, 80)   # Renderable

        self._layer_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._layer_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._layer_table.verticalHeader().setDefaultSectionSize(22)
        self._layer_table.verticalHeader().setVisible(False)
        self._layer_table.setAlternatingRowColors(True)
        self._layer_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._layer_table.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )

        body_layout.addWidget(self._layer_table, 1)

        # Action button row (mirrors gaffer "Add Light / Remove Light / Apply" row)
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(4)

        self._add_layer_button = QtWidgets.QPushButton('+ Add Layer')
        self._add_layer_button.setFixedHeight(24)
        btn_row.addWidget(self._add_layer_button)

        self._remove_layer_button = QtWidgets.QPushButton('- Remove Layer')
        self._remove_layer_button.setFixedHeight(24)
        btn_row.addWidget(self._remove_layer_button)

        btn_row.addStretch()

        self._apply_button = QtWidgets.QPushButton('Apply Slate')
        self._apply_button.setFixedHeight(24)
        self._apply_button.setToolTip(
            'Apply all enabled slate overrides to the scene render layers.'
        )
        btn_row.addWidget(self._apply_button)

        body_layout.addLayout(btn_row)
        main_layout.addWidget(body_widget, 1)

    def _setup_menu(self):
        """Create menuBar with Tools > Settings."""
        menubar = self.menuBar()
        tools_menu = menubar.addMenu('Tools')
        settings_action = QtWidgets.QAction('Settings', self)
        settings_action.triggered.connect(self._open_settings)
        tools_menu.addAction(settings_action)

    def _connect_signals(self):
        """Wire all widget signals."""
        self._slate_combo.currentIndexChanged.connect(self._on_slate_changed)
        self._refresh_button.clicked.connect(self._refresh_slate_combo)
        self._create_slate_button.clicked.connect(self._on_new_slate)
        self._set_parent_button.clicked.connect(self._on_set_parent)
        self._clear_parent_button.clicked.connect(self._on_clear_parent)
        self._remove_slate_button.clicked.connect(self._on_remove_slate)
        self._search_box.textChanged.connect(self._on_search_changed)
        self._add_layer_button.clicked.connect(self._on_add_layer)
        self._remove_layer_button.clicked.connect(self._on_remove_layer)
        self._enter_edit_button.clicked.connect(self._enter_edit_mode)
        self._commit_button.clicked.connect(self._commit_edit)
        self._discard_button.clicked.connect(self._cancel_edit)
        self._apply_button.clicked.connect(self._on_apply_slate)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def select_slate(self, slate):
        """Pre-select a slate in the combo.

        Args:
            slate (CTXSlateNode|str): Slate node or node name to select.
        """
        if slate is None:
            return
        target_name = slate if isinstance(slate, str) else slate.node_name
        for i in range(self._slate_combo.count()):
            wrapper = self._slate_combo.itemData(i)
            if wrapper is not None and wrapper.node_name == target_name:
                self._slate_combo.setCurrentIndex(i)
                return
        # Not in combo yet -- refresh and retry
        self._refresh_slate_combo()
        for i in range(self._slate_combo.count()):
            wrapper = self._slate_combo.itemData(i)
            if wrapper is not None and wrapper.node_name == target_name:
                self._slate_combo.setCurrentIndex(i)
                return

    def refresh(self):
        """Refresh combo and layer table from current scene state."""
        self._refresh_slate_combo()

    def show_lock_banner(self, message):
        """Show the lock banner."""
        self._lock_banner.setText(message)
        self._lock_banner.setVisible(True)

    def hide_lock_banner(self):
        """Hide the lock banner."""
        self._lock_banner.setVisible(False)

    # ------------------------------------------------------------------
    # Combo helpers
    # ------------------------------------------------------------------

    def _refresh_slate_combo(self):
        """Repopulate the slate combo from CTXSlateNode.list_all()."""
        current_name = None
        current_data = self._slate_combo.currentData()
        if current_data is not None:
            current_name = current_data.node_name

        self._slate_combo.blockSignals(True)
        self._slate_combo.clear()

        try:
            slates = CTXSlateNode.list_all()
        except Exception as exc:
            logger.warning('Failed to list slates: %s', exc)
            slates = []

        if not slates:
            self._slate_combo.addItem('No slates found', None)
            self._slate_combo.blockSignals(False)
            self._current_slate = None
            self._update_chain_label()
            self._refresh_layer_table()
            return

        restore_idx = 0
        for i, sn in enumerate(slates):
            try:
                try:
                    slate_name = cmds.getAttr('{}.slateName'.format(sn.node_name))
                except Exception:
                    slate_name = None
                if not slate_name:
                    slate_name = sn.node_name

                slate_type = 'master'
                try:
                    slate_type = cmds.getAttr('{}.slateType'.format(sn.node_name))
                except Exception:
                    pass

                if slate_type == 'master':
                    label = '[Master] {}'.format(slate_name)
                elif slate_type == 'sequence':
                    label = '[seq] {}'.format(slate_name)
                else:
                    label = '[shot] {}'.format(slate_name)
            except Exception:
                label = sn.node_name

            self._slate_combo.addItem(label, sn)
            if current_name and sn.node_name == current_name:
                restore_idx = i

        self._slate_combo.blockSignals(False)
        self._slate_combo.setCurrentIndex(restore_idx)
        # Manually trigger since we blocked signals during repopulation
        self._on_slate_changed(restore_idx)

    def _on_slate_changed(self, index):
        """Handle combo selection change."""
        wrapper = self._slate_combo.itemData(index)
        self._current_slate = wrapper  # None if "No slates found" placeholder
        self._update_chain_label()
        self._refresh_layer_table()

    def _slate_display_name(self, slate_node):
        """Return the slateName attribute value for display, falling back to node name."""
        try:
            return cmds.getAttr('{}.slateName'.format(slate_node.node_name))
        except Exception:
            return slate_node.node_name

    def _update_chain_label(self):
        """Update the chain info label to show the inheritance path."""
        if self._current_slate is None:
            self._chain_label.setText('Chain: -')
            return
        try:
            chain = SlateResolver.build_chain(self._current_slate)
            names = [self._slate_display_name(sn) for sn in reversed(chain)]
            self._chain_label.setText('Chain: {}'.format(' > '.join(names)))
        except Exception:
            self._chain_label.setText('Chain: -')

    # ------------------------------------------------------------------
    # Layer table helpers
    # ------------------------------------------------------------------

    def _refresh_layer_table(self):
        """Redraw the layer table for the currently selected slate.

        Shows local layers (defined on this slate) normally and inherited
        layers (from parent slates only) in gray with '(inh)' suffix.
        Mirrors the gaffer attribute table pattern.
        """
        self._layer_table.setRowCount(0)
        if self._current_slate is None:
            return

        # Build parent chain (index 0 = current slate)
        try:
            chain = SlateResolver.build_chain(self._current_slate)
        except Exception as exc:
            logger.warning('SlateResolver.build_chain failed: %s', exc)
            chain = [self._current_slate]

        # Own layers on the current slate
        try:
            own_layers = {
                l.get_layer_name(): l
                for l in self._current_slate.get_layers()
                if l.get_layer_name()
            }
        except Exception:
            own_layers = {}

        # Inherited layers: in parent slates, not already owned locally.
        # Show all parent layers regardless of override_enabled so users can
        # see and take ownership of any inherited layer.
        inherited = {}  # layer_name -> (layer_entry, source_slate)
        for slate_node in chain[1:]:
            try:
                for layer_entry in slate_node.get_layers():
                    name = layer_entry.get_layer_name()
                    if name and name not in own_layers and name not in inherited:
                        inherited[name] = (layer_entry, slate_node)
            except Exception:
                continue

        # Build ordered row list: own first, then inherited
        rows = []
        for name, layer_entry in sorted(own_layers.items()):
            rows.append(('local', name, layer_entry))
        for name, (layer_entry, _src) in sorted(inherited.items()):
            rows.append(('inh', name, layer_entry))

        self._layer_table.setRowCount(len(rows))
        gray = QtGui.QColor('#888888')

        for row, (kind, name, layer_entry) in enumerate(rows):
            is_local = kind == 'local'

            # Col 0: Layer name -- real name stored in UserRole
            display_name = name if is_local else '{} (inh)'.format(name)
            name_item = QtWidgets.QTableWidgetItem(display_name)
            name_item.setData(QtCore.Qt.UserRole, name)
            name_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            if not is_local:
                name_item.setForeground(gray)
            self._layer_table.setItem(row, 0, name_item)

            # Col 1: Renderable checkbox
            renderable_cb = QtWidgets.QCheckBox()
            try:
                renderable_cb.setChecked(layer_entry.get_renderable())
            except Exception:
                renderable_cb.setChecked(True)
            # All rows editable in edit mode; inherited rows show as grayed text only
            renderable_cb.setEnabled(self._edit_mode)
            self._layer_table.setCellWidget(row, 1, self._center_widget(renderable_cb))

        # Re-apply search filter
        self._on_search_changed(self._search_box.text())

    def _on_search_changed(self, text):
        """Filter the layer table to rows matching the search text."""
        text = text.lower()
        for row in range(self._layer_table.rowCount()):
            name_item = self._layer_table.item(row, 0)
            if name_item is None:
                self._layer_table.setRowHidden(row, bool(text))
                continue
            self._layer_table.setRowHidden(row, bool(text) and text not in name_item.text().lower())

    def _center_widget(self, widget):
        """Wrap a widget in a centered container for table cells."""
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
        """Snapshot current state and switch to edit mode."""
        if self._current_slate is None:
            return
        self._snapshot = self._capture_snapshot()
        self._edit_mode = True
        self._edit_mode_label.setText('Edit Mode: ON')
        self._edit_mode_label.setStyleSheet('font-weight: bold; color: #FFA000; font-size: 11px;')
        self._enter_edit_button.setVisible(False)
        self._commit_button.setVisible(True)
        self._discard_button.setVisible(True)
        self._slate_combo.setEnabled(False)
        self._refresh_layer_table()

    def _commit_edit(self):
        """Write table state to CTX nodes (snapshot-diff pattern).

        For local rows: update existing layer entry if value changed.
        For inherited rows that changed: create a local layer entry on this
        slate (taking ownership), then set the new value.
        """
        if self._current_slate is None:
            self._exit_edit_mode()
            return
        current_state = self._read_table_state()
        for layer_name, state in current_state.items():
            snap = self._snapshot.get(layer_name, {})
            if state['renderable'] == snap.get('renderable'):
                continue  # Unchanged -- skip
            try:
                layer_entry = self._current_slate.get_layer_by_name(layer_name)
                if layer_entry is None:
                    # Inherited layer changed -- take ownership by creating local entry
                    layer_entry = self._current_slate.add_layer(
                        layer_name,
                        renderable=state['renderable'],
                        enabled=True,
                    )
                else:
                    layer_entry.set_renderable(state['renderable'])
                    layer_entry.set_override_enabled(True)
            except Exception as exc:
                logger.error('Failed to write layer %s: %s', layer_name, exc)
        self._exit_edit_mode()

    def _cancel_edit(self):
        """Restore snapshot to CTX nodes and exit edit mode."""
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
        """Return to read-only state."""
        self._edit_mode = False
        self._snapshot = {}
        self._edit_mode_label.setText('Edit Mode: OFF')
        self._edit_mode_label.setStyleSheet('font-weight: bold; font-size: 11px;')
        self._enter_edit_button.setVisible(True)
        self._commit_button.setVisible(False)
        self._discard_button.setVisible(False)
        self._slate_combo.setEnabled(True)
        self._refresh_layer_table()

    # ------------------------------------------------------------------
    # Snapshot helpers
    # ------------------------------------------------------------------

    def _capture_snapshot(self):
        """Return {layer_name: {renderable, renderableEnabled}} from CTX nodes.

        Captures own layers and the resolved value of inherited layers so that
        _commit_edit can detect which inherited rows the user changed.
        """
        snap = {}
        if self._current_slate is None:
            return snap
        # Own layers
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
        # Inherited layers (resolved value from parent chain)
        try:
            chain = SlateResolver.build_chain(self._current_slate)
            for slate_node in chain[1:]:
                for layer_entry in slate_node.get_layers():
                    name = layer_entry.get_layer_name()
                    if name and name not in snap:
                        snap[name] = {
                            'renderable': layer_entry.get_renderable(),
                            'renderableEnabled': layer_entry.is_override_enabled(),
                        }
        except Exception:
            pass
        return snap

    def _read_table_state(self):
        """Read current widget state from all rows (local and inherited)."""
        state = {}
        for row in range(self._layer_table.rowCount()):
            name_item = self._layer_table.item(row, 0)
            if name_item is None:
                continue
            is_inherited = name_item.text().endswith(' (inh)')
            real_name = name_item.data(QtCore.Qt.UserRole) or name_item.text()

            renderable = False
            rnd_container = self._layer_table.cellWidget(row, 1)
            if rnd_container is not None:
                cb = rnd_container.findChild(QtWidgets.QCheckBox)
                if cb is not None:
                    renderable = cb.isChecked()

            state[real_name] = {'renderable': renderable, 'is_inherited': is_inherited}
        return state

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_new_slate(self):
        """Unified slate creation -- asks Sequence Slate or Shot Slate.

        Mirrors GafferManagerDialog._on_create_gaffer() exactly.
        """
        if not cmds:
            QtWidgets.QMessageBox.warning(self, 'Maya Not Available',
                                          'Maya is not available.')
            return

        choices = ['Sequence Slate', 'Shot Slate']
        choice, ok = QtWidgets.QInputDialog.getItem(
            self, 'Create Slate', 'Attach to:', choices, 0, False
        )
        if not ok:
            return

        if choice == 'Sequence Slate':
            self._create_sequence_slate()
        else:
            self._create_shot_slate()

    def _create_sequence_slate(self):
        """Create a slate and attach it to a sequence.

        Mirrors GafferManagerDialog._create_sequence_gaffer().
        """
        try:
            from core.nodes.wrappers.sequence import CTXSequenceNode

            all_seqs = CTXSequenceNode.list_all()
            if not all_seqs:
                QtWidgets.QMessageBox.warning(
                    self, 'No Sequences',
                    'No CTX_Sequence nodes found. Create shots first.'
                )
                return

            seq_labels = []
            for s in all_seqs:
                existing = s.get_slate()
                label = s.get_attribute('sequenceCode') or s.node_name
                if existing:
                    try:
                        existing_name = existing.get_attribute('slateName') or existing.node_name
                    except Exception:
                        existing_name = existing.node_name
                    label += '  [has slate: {}]'.format(existing_name)
                seq_labels.append(label)

            seq_label, ok = QtWidgets.QInputDialog.getItem(
                self, 'Select Sequence', 'Attach to:', seq_labels, 0, False
            )
            if not ok:
                return

            seq = all_seqs[seq_labels.index(seq_label)]
            seq_code = seq.get_attribute('sequenceCode') or seq.node_name

            name, ok = QtWidgets.QInputDialog.getText(
                self, 'Slate Name', 'Name:', text='seq_{}'.format(seq_code)
            )
            if not ok or not name.strip():
                return

            parent_slate = self._ask_parent_slate()
            if parent_slate is False:
                return  # User cancelled

            new_slate = SlateManager.create_sequence_slate(
                seq, name=name.strip(), parent_slate=parent_slate
            )

            logger.info("Created sequence slate '%s' for seq '%s'",
                        new_slate.node_name, seq_code)
            self._refresh_slate_combo()
            self.select_slate(new_slate)

        except Exception as exc:
            logger.error('Failed to create sequence slate: %s', exc)
            QtWidgets.QMessageBox.critical(
                self, 'Error', 'Failed to create sequence slate:\n{}'.format(exc)
            )

    def _create_shot_slate(self):
        """Create a slate and attach it to a shot.

        Mirrors GafferManagerDialog._create_shot_gaffer().
        """
        try:
            from core.nodes.wrappers.shot import CTXShotNode

            all_shots = CTXShotNode.list_all()
            if not all_shots:
                QtWidgets.QMessageBox.warning(
                    self, 'No Shots',
                    'No CTX_Shot nodes found. Create shots first.'
                )
                return

            shot_labels = []
            for s in all_shots:
                existing = s.get_slate()
                label = '{}_{}'.format(
                    s.get_seq_code() or '?', s.get_shot_code() or s.node_name
                )
                if existing:
                    try:
                        existing_name = existing.get_attribute('slateName') or existing.node_name
                    except Exception:
                        existing_name = existing.node_name
                    label += '  [has slate: {}]'.format(existing_name)
                shot_labels.append(label)

            shot_label, ok = QtWidgets.QInputDialog.getItem(
                self, 'Select Shot', 'Attach to:', shot_labels, 0, False
            )
            if not ok:
                return

            shot = all_shots[shot_labels.index(shot_label)]
            shot_id = '{}_{}'.format(
                shot.get_seq_code() or '?', shot.get_shot_code() or shot.node_name
            )

            name, ok = QtWidgets.QInputDialog.getText(
                self, 'Slate Name', 'Name:', text=shot_id
            )
            if not ok or not name.strip():
                return

            parent_slate = self._ask_parent_slate()
            if parent_slate is False:
                return

            new_slate = SlateManager.create_shot_slate(
                shot, name=name.strip(), parent_slate=parent_slate
            )

            logger.info("Created shot slate '%s' for shot '%s'",
                        new_slate.node_name, shot_id)
            self._refresh_slate_combo()
            self.select_slate(new_slate)

        except Exception as exc:
            logger.error('Failed to create shot slate: %s', exc)
            QtWidgets.QMessageBox.critical(
                self, 'Error', 'Failed to create shot slate:\n{}'.format(exc)
            )

    def _ask_parent_slate(self):
        """Ask user to optionally choose a parent slate.

        Mirrors GafferManagerDialog._ask_parent_gaffer().

        Returns:
            CTXSlateNode: chosen parent slate.
            None: user chose standalone (no parent).
            False: user cancelled the dialog.
        """
        try:
            all_slates = CTXSlateNode.list_all()
        except Exception:
            all_slates = []

        if not all_slates:
            return None

        choices = ['(none -- standalone)']
        for sn in all_slates:
            try:
                n = sn.get_attribute('slateName') or sn.node_name
                t = sn.get_attribute('slateType') or '?'
                choices.append('{} [{}]'.format(n, t))
            except Exception:
                choices.append(sn.node_name)

        chosen, ok = QtWidgets.QInputDialog.getItem(
            self, 'Parent Slate',
            'Inherit from (optional):', choices, 0, False
        )
        if not ok:
            return False

        if chosen == '(none -- standalone)':
            return None

        for i, sn in enumerate(all_slates):
            if choices[i + 1] == chosen:
                return sn
        return None

    def _on_set_parent(self):
        """Set parent slate -- excludes current chain to prevent cycles.

        Mirrors GafferManagerDialog._on_set_parent_gaffer().
        """
        if not cmds:
            QtWidgets.QMessageBox.warning(self, 'Maya Not Available',
                                          'Maya is not available.')
            return
        if self._current_slate is None:
            QtWidgets.QMessageBox.warning(self, 'No Slate Selected',
                                          'Select a slate first.')
            return

        try:
            all_slates = CTXSlateNode.list_all()
            current_node = self._current_slate.node_name

            # Build existing chain to prevent cycles
            try:
                current_chain = {
                    sn.node_name
                    for sn in SlateResolver.build_chain(self._current_slate)
                }
            except Exception:
                current_chain = {current_node}

            candidates = [
                sn for sn in all_slates
                if sn.node_name != current_node and sn.node_name not in current_chain
            ]

            if not candidates:
                QtWidgets.QMessageBox.warning(
                    self, 'No Candidates',
                    'No other slates available as parent.'
                )
                return

            labels = []
            for sn in candidates:
                try:
                    n = sn.get_attribute('slateName') or sn.node_name
                    t = sn.get_attribute('slateType') or '?'
                    labels.append('{} [{}]'.format(n, t))
                except Exception:
                    labels.append(sn.node_name)

            chosen, ok = QtWidgets.QInputDialog.getItem(
                self, 'Set Parent Slate', 'Inherit from:', labels, 0, False
            )
            if not ok:
                return

            parent_slate = candidates[labels.index(chosen)]
            self._current_slate.set_parent_slate(parent_slate)
            logger.info("Set parent '%s' on '%s'",
                        parent_slate.node_name, self._current_slate.node_name)

            self._refresh_slate_combo()
            self.select_slate(self._current_slate)

        except Exception as exc:
            logger.error('Failed to set parent: %s', exc)
            QtWidgets.QMessageBox.critical(
                self, 'Error', 'Failed to set parent:\n{}'.format(exc)
            )

    def _on_clear_parent(self):
        """Clear parent slate with confirmation dialog.

        Mirrors GafferManagerDialog._on_clear_parent_gaffer().
        """
        if not cmds:
            QtWidgets.QMessageBox.warning(self, 'Maya Not Available',
                                          'Maya is not available.')
            return
        if self._current_slate is None:
            QtWidgets.QMessageBox.warning(self, 'No Slate Selected',
                                          'Select a slate first.')
            return

        try:
            existing_parent = self._current_slate.get_parent_slate()
            if existing_parent is None:
                try:
                    slate_name = self._current_slate.get_attribute('slateName') or self._current_slate.node_name
                except Exception:
                    slate_name = self._current_slate.node_name
                QtWidgets.QMessageBox.information(
                    self, 'No Parent',
                    "Slate '{}' has no parent.".format(slate_name)
                )
                return

            try:
                parent_name = existing_parent.get_attribute('slateName') or existing_parent.node_name
            except Exception:
                parent_name = existing_parent.node_name

            reply = QtWidgets.QMessageBox.question(
                self, 'Clear Parent',
                "Remove inheritance from '{}'?\n\nSlate will become standalone.".format(
                    parent_name),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

            src = '{}.message'.format(existing_parent.node_name)
            dst = '{}.parentSlate'.format(self._current_slate.node_name)
            if cmds.isConnected(src, dst):
                cmds.disconnectAttr(src, dst)

            logger.info("Cleared parent '%s' from '%s'",
                        parent_name, self._current_slate.node_name)

            self._refresh_slate_combo()
            self.select_slate(self._current_slate)

        except Exception as exc:
            logger.error('Failed to clear parent: %s', exc)
            QtWidgets.QMessageBox.critical(
                self, 'Error', 'Failed to clear parent:\n{}'.format(exc)
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

        self._refresh_slate_combo()

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
                self, 'No Layers', 'No render layers found in the current scene.'
            )
            return

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

        for name in dlg.get_selected_layer_names():
            try:
                self._current_slate.add_layer(name, renderable=True, enabled=True)
                logger.info('Added layer %r to slate %s', name, self._current_slate.node_name)
            except Exception as exc:
                logger.error('Failed to add layer %r: %s', name, exc)

        self._refresh_layer_table()

    def _on_remove_layer(self):
        """Remove selected layer rows from the current slate."""
        if self._current_slate is None:
            return

        selected_rows = self._layer_table.selectionModel().selectedRows()
        if not selected_rows:
            return

        for index in sorted(selected_rows, reverse=True):
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

    def _on_apply_slate(self):
        """Apply enabled overrides to Maya scene render layers."""
        if self._current_slate is None:
            return
        try:
            SlateResolver.apply_to_scene(self._current_slate)
            logger.info('Applied slate %s to scene', self._current_slate.node_name)
        except Exception as exc:
            logger.error('Failed to apply slate: %s', exc)
            QtWidgets.QMessageBox.critical(
                self, 'Error', 'Failed to apply slate:\n{}'.format(exc)
            )

    def _open_settings(self):
        """Open settings dialog (placeholder)."""
        QtWidgets.QMessageBox.information(
            self, 'Settings', 'Slate Manager settings are not yet implemented.'
        )


class _AddLayerDialog(QtWidgets.QDialog):
    """Popup to pick render layers to add to a slate."""

    def __init__(self, layers, parent=None):
        super(_AddLayerDialog, self).__init__(parent)
        self.setWindowTitle('Add Layers to Slate')
        self.resize(300, 400)
        self._layers = layers

        layout = QtWidgets.QVBoxLayout(self)

        self._filter = QtWidgets.QLineEdit()
        self._filter.setPlaceholderText('Filter...')
        self._filter.textChanged.connect(self._apply_filter)
        layout.addWidget(self._filter)

        self._list = QtWidgets.QListWidget()
        self._list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        for layer in layers:
            item = QtWidgets.QListWidgetItem(layer.name)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Unchecked)
            self._list.addItem(item)
        layout.addWidget(self._list)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _apply_filter(self, text):
        for i in range(self._list.count()):
            item = self._list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def get_selected_layer_names(self):
        result = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.checkState() == QtCore.Qt.Checked:
                result.append(item.text())
        return result
