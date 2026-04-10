# -*- coding: utf-8 -*-
"""Gaffer Manager Dialog - Manage light gaffers and overrides.

Two-panel layout (Katana-style):
  Left  — gaffer selector + search box + lights table + action buttons
  Right — embedded LightEditorPanel (updates when a light row is selected)
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

from core.gaffer.manager import GafferManager
from core.gaffer.resolver import AttributeResolver
from core.gaffer.light_ops import LightOperations
from core.gaffer.chain_ops import ChainOperations
from core.gaffer.edit_mode import EditMode
from core.nodes.wrappers.gaffer import CTXLightGafferNode

logger = logging.getLogger(__name__)


class GafferManagerDialog(QtWidgets.QDialog):
    """Dialog for managing light gaffers."""

    _instance = None  # Singleton reference

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
        """Return the singleton instance, creating it if necessary.

        Args:
            parent: Parent widget (fallback when Maya main window is unavailable)

        Returns:
            GafferManagerDialog: The singleton instance
        """
        if cls._instance is not None:
            try:
                cls._instance.show()
                cls._instance.raise_()
                cls._instance.activateWindow()
                return cls._instance
            except Exception:
                cls._instance = None

        # Prefer the explicit parent (e.g. MainWindow) so the dialog sits in the
        # correct Z-order chain: Gaffer -> Multishot Manager -> Maya main window.
        # Fall back to Maya's main window when no parent is supplied.
        maya_win = cls._maya_main_window()
        instance = cls(parent=parent or maya_win)
        instance.show()
        instance.raise_()
        instance.activateWindow()
        return instance

    def __init__(self, parent=None):
        """Initialize gaffer manager dialog."""
        if GafferManagerDialog._instance is not None:
            try:
                GafferManagerDialog._instance.close()
            except Exception:
                pass
            GafferManagerDialog._instance = None

        super(GafferManagerDialog, self).__init__(parent)
        GafferManagerDialog._instance = self

        self.setWindowModality(QtCore.Qt.NonModal)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        # Qt::Tool + parented to Maya's main window:
        #   - stays in front of Maya's viewport (owner window)
        #   - yields to other apps (browser, etc.) when they get focus
        # This matches the behaviour of Maya's own floating panels.
        self.setWindowFlags(
            QtCore.Qt.Tool |
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowMinimizeButtonHint |
            QtCore.Qt.WindowMaximizeButtonHint
        )

        self.setWindowTitle("Light Gaffer Manager")
        self.setMinimumSize(1100, 680)
        self.resize(1280, 760)

        self._current_gaffer = None
        self._lights_data = []
        self._edit_mode = None
        self._detail_panel = None  # Currently shown LightEditorPanel

        self._setup_ui()
        self._connect_signals()
        self._refresh_gaffer_list()

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        # Lock banner -- shown when the current gaffer is locked (hidden by default)
        self._lock_banner = QtWidgets.QLabel('')
        self._lock_banner.setStyleSheet(
            'background-color: #7B3F00; color: #FFD54F; '
            'padding: 4px 8px; font-weight: bold;'
        )
        self._lock_banner.setVisible(False)
        self._lock_banner.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(self._lock_banner)

        # ── Compact header bar (gaffer + edit mode on 2 tight rows) ───
        header_widget = QtWidgets.QWidget()
        header_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        header_layout = QtWidgets.QVBoxLayout(header_widget)
        header_layout.setContentsMargins(4, 4, 4, 4)
        header_layout.setSpacing(3)

        # Row 1: gaffer combo + all gaffer buttons in one line
        gaffer_row = QtWidgets.QHBoxLayout()
        gaffer_row.setSpacing(4)

        lbl = QtWidgets.QLabel("Gaffer:")
        lbl.setFixedWidth(48)
        gaffer_row.addWidget(lbl)

        self._gaffer_combo = QtWidgets.QComboBox()
        self._gaffer_combo.setMinimumWidth(180)
        self._gaffer_combo.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        gaffer_row.addWidget(self._gaffer_combo)

        self._refresh_button = QtWidgets.QPushButton("Refresh")
        self._refresh_button.setFixedWidth(70)
        gaffer_row.addWidget(self._refresh_button)

        sep1 = QtWidgets.QFrame()
        sep1.setFrameShape(QtWidgets.QFrame.VLine)
        sep1.setFrameShadow(QtWidgets.QFrame.Sunken)
        gaffer_row.addWidget(sep1)

        self._create_gaffer_button = QtWidgets.QPushButton("+ Create")
        self._create_gaffer_button.setFixedWidth(75)
        self._create_gaffer_button.setToolTip("Create a new gaffer for a sequence or shot")
        gaffer_row.addWidget(self._create_gaffer_button)

        self._set_parent_button = QtWidgets.QPushButton("Set Parent")
        self._set_parent_button.setFixedWidth(80)
        self._set_parent_button.setToolTip("Set a parent gaffer to inherit its lights")
        gaffer_row.addWidget(self._set_parent_button)

        self._clear_parent_button = QtWidgets.QPushButton("Clear Parent")
        self._clear_parent_button.setFixedWidth(85)
        self._clear_parent_button.setToolTip("Remove parent gaffer connection")
        gaffer_row.addWidget(self._clear_parent_button)

        header_layout.addLayout(gaffer_row)

        # Row 2: chain info (single line)
        info_row = QtWidgets.QHBoxLayout()
        info_row.setSpacing(12)
        self._chain_label = QtWidgets.QLabel("Chain: -")
        self._chain_label.setStyleSheet("color: #888; font-style: italic; font-size: 11px;")
        info_row.addWidget(self._chain_label)
        self._gaffer_info_label = QtWidgets.QLabel("")
        self._gaffer_info_label.setStyleSheet("color: #aaa; font-size: 11px;")
        info_row.addWidget(self._gaffer_info_label)
        info_row.addStretch()
        header_layout.addLayout(info_row)

        # Row 3: edit mode bar
        edit_row = QtWidgets.QHBoxLayout()
        edit_row.setSpacing(4)
        self._edit_mode_label = QtWidgets.QLabel("Edit Mode: OFF")
        self._edit_mode_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        edit_row.addWidget(self._edit_mode_label)
        edit_row.addStretch()

        self._enter_edit_button = QtWidgets.QPushButton("Enter Edit Mode")
        self._enter_edit_button.setFixedWidth(130)
        self._enter_edit_button.setStyleSheet("background-color: #37474F; color: white;")
        edit_row.addWidget(self._enter_edit_button)

        self._commit_button = QtWidgets.QPushButton("Commit Changes")
        self._commit_button.setFixedWidth(130)
        self._commit_button.setStyleSheet("background-color: #2E7D32; color: white;")
        self._commit_button.setVisible(False)
        edit_row.addWidget(self._commit_button)

        self._discard_button = QtWidgets.QPushButton("Discard Changes")
        self._discard_button.setFixedWidth(130)
        self._discard_button.setStyleSheet("background-color: #B71C1C; color: white;")
        self._discard_button.setVisible(False)
        edit_row.addWidget(self._discard_button)

        self._lock_btn = QtWidgets.QPushButton("Lock Gaffer")
        self._lock_btn.setFixedWidth(110)
        self._lock_btn.setToolTip("Lock this gaffer so its values cannot be edited")
        self._lock_btn.setVisible(False)
        self._lock_btn.clicked.connect(self._on_toggle_gaffer_lock)
        edit_row.addWidget(self._lock_btn)

        header_layout.addLayout(edit_row)

        # Thin separator under header
        sep_h = QtWidgets.QFrame()
        sep_h.setFrameShape(QtWidgets.QFrame.HLine)
        sep_h.setFrameShadow(QtWidgets.QFrame.Sunken)
        header_layout.addWidget(sep_h)

        main_layout.addWidget(header_widget)

        # ── Main splitter (fills all remaining space) ──────────────────
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(4)

        # Left panel
        left_widget = QtWidgets.QWidget()
        left_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 2, 0)
        left_layout.setSpacing(3)

        # Search
        self._search_box = QtWidgets.QLineEdit()
        self._search_box.setPlaceholderText("Search lights...")
        self._search_box.setClearButtonEnabled(True)
        self._search_box.setFixedHeight(24)
        left_layout.addWidget(self._search_box)

        # Lights table
        self._lights_table = QtWidgets.QTableWidget()
        self._lights_table.setColumnCount(5)
        self._lights_table.setHorizontalHeaderLabels([
            "Light", "Mute", "Intensity", "Exposure", "Color"
        ])
        self._lights_table.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )

        header = self._lights_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        for col in range(1, 5):
            header.setSectionResizeMode(col, QtWidgets.QHeaderView.Fixed)

        self._lights_table.setColumnWidth(1, 46)   # Mute
        self._lights_table.setColumnWidth(2, 80)   # Intensity
        self._lights_table.setColumnWidth(3, 80)   # Exposure
        self._lights_table.setColumnWidth(4, 90)   # Color swatch

        self._lights_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._lights_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._lights_table.verticalHeader().setDefaultSectionSize(22)
        self._lights_table.setAlternatingRowColors(True)
        self._lights_table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        left_layout.addWidget(self._lights_table, 1)  # stretch=1

        # Action buttons
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(4)
        self._add_light_button = QtWidgets.QPushButton("+ Add Light")
        self._add_light_button.setFixedHeight(24)
        btn_row.addWidget(self._add_light_button)

        self._remove_light_button = QtWidgets.QPushButton("- Remove Light")
        self._remove_light_button.setFixedHeight(24)
        btn_row.addWidget(self._remove_light_button)

        self._clear_override_button = QtWidgets.QPushButton("Clear Override")
        self._clear_override_button.setFixedHeight(24)
        self._clear_override_button.setToolTip(
            "Remove this gaffer's override for the selected light so it falls back "
            "to the inherited value from the parent gaffer."
        )
        btn_row.addWidget(self._clear_override_button)

        btn_row.addStretch()

        self._apply_button = QtWidgets.QPushButton("Apply Gaffer to Lights")
        self._apply_button.setFixedHeight(24)
        self._apply_button.setToolTip(
            "Push all enabled gaffer overrides to the Maya lights in the viewport."
        )
        btn_row.addWidget(self._apply_button)
        left_layout.addLayout(btn_row)

        # Right panel — detail panel container (fills height)
        right_widget = QtWidgets.QWidget()
        right_widget.setMinimumWidth(350)
        right_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self._right_layout = QtWidgets.QVBoxLayout(right_widget)
        self._right_layout.setContentsMargins(4, 0, 0, 0)
        self._right_layout.setSpacing(0)

        self._detail_placeholder = QtWidgets.QLabel("Select a light to view details")
        self._detail_placeholder.setAlignment(QtCore.Qt.AlignCenter)
        self._detail_placeholder.setStyleSheet("color: #666; font-style: italic;")
        self._detail_placeholder.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self._right_layout.addWidget(self._detail_placeholder)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([620, 500])

        main_layout.addWidget(splitter, 1)  # stretch=1 so splitter fills all height

    def _connect_signals(self):
        self._gaffer_combo.currentIndexChanged.connect(self._on_gaffer_changed)
        self._refresh_button.clicked.connect(self._on_refresh_clicked)
        self._create_gaffer_button.clicked.connect(self._on_create_gaffer)
        self._set_parent_button.clicked.connect(self._on_set_parent_gaffer)
        self._clear_parent_button.clicked.connect(self._on_clear_parent_gaffer)
        self._enter_edit_button.clicked.connect(self._on_enter_edit_mode)
        self._commit_button.clicked.connect(self._on_commit_edit_mode)
        self._discard_button.clicked.connect(self._on_discard_edit_mode)
        self._add_light_button.clicked.connect(self._on_add_light_clicked)
        self._remove_light_button.clicked.connect(self._on_remove_light_clicked)
        self._clear_override_button.clicked.connect(self._on_clear_override_clicked)
        self._apply_button.clicked.connect(self._on_apply_clicked)
        self._search_box.textChanged.connect(self._on_search_changed)
        self._lights_table.itemSelectionChanged.connect(self._on_selection_changed)
        self._lights_table.itemChanged.connect(self._on_table_item_changed)
        self._lights_table.customContextMenuRequested.connect(self._on_table_context_menu)

    # ------------------------------------------------------------------
    # Gaffer list helpers
    # ------------------------------------------------------------------

    def _refresh_gaffer_list(self):
        if not cmds:
            return
        try:
            all_gaffers = ChainOperations.list_all_gaffers()
            self._gaffer_combo.clear()

            if not all_gaffers:
                self._gaffer_combo.addItem("No gaffers found", None)
                self._current_gaffer = None
                self._update_chain_label()
                self._populate_lights_table()
                return

            master_gaffers = []
            inherit_gaffers = []
            for gi in all_gaffers:
                wrapper = gi.get('wrapper')
                if wrapper and wrapper.get_parent_gaffer() is None:
                    master_gaffers.append(gi)
                else:
                    inherit_gaffers.append(gi)

            for gi in master_gaffers:
                self._gaffer_combo.addItem("[Master] {}".format(gi['name']), gi['wrapper'])
            for gi in inherit_gaffers:
                self._gaffer_combo.addItem("[Inherit] {}".format(gi['name']), gi['wrapper'])

            if self._gaffer_combo.count() > 0:
                self._gaffer_combo.setCurrentIndex(0)

        except Exception as e:
            logger.error("Failed to refresh gaffer list: {}".format(e))
            self._gaffer_combo.clear()
            self._gaffer_combo.addItem("Error loading gaffers", None)

    def _update_chain_label(self):
        if not self._current_gaffer:
            self._chain_label.setText("Chain: -")
            self._gaffer_info_label.setText("")
            return
        try:
            chain = self._current_gaffer.build_chain()
            chain_text = " -> ".join(reversed([g.get_gaffer_name() for g in chain]))
            self._chain_label.setText("Chain: {}".format(chain_text))

            has_parent = self._current_gaffer.get_parent_gaffer() is not None
            type_label = "Inherit" if has_parent else "Master"
            owner_text = self._get_gaffer_owner_text(self._current_gaffer)
            self._gaffer_info_label.setText("Type: {}  |  {}".format(type_label, owner_text))
        except Exception as e:
            logger.error("Failed to build chain: {}".format(e))
            self._chain_label.setText("Chain: Error")
            self._gaffer_info_label.setText("")

    def _get_gaffer_owner_text(self, gaffer):
        if not cmds:
            return "Owner: unknown"
        try:
            connections = cmds.listConnections(
                "{}.message".format(gaffer.node_name),
                source=False, destination=True, type='network'
            ) or []
            for node in connections:
                if not cmds.attributeQuery('ctx_type', node=node, exists=True):
                    continue
                node_type = cmds.getAttr('{}.ctx_type'.format(node))
                if node_type == 'CTX_Sequence':
                    code = cmds.getAttr('{}.sequenceCode'.format(node)) if \
                        cmds.attributeQuery('sequenceCode', node=node, exists=True) else node
                    return "Owner: Sequence {}".format(code)
                elif node_type == 'CTX_Shot':
                    code = cmds.getAttr('{}.shot_code'.format(node)) if \
                        cmds.attributeQuery('shot_code', node=node, exists=True) else node
                    return "Owner: Shot {}".format(code)
            return "Owner: None (standalone)"
        except Exception:
            return "Owner: unknown"

    # ------------------------------------------------------------------
    # Lights table
    # ------------------------------------------------------------------

    def _populate_lights_table(self):
        self._lights_table.setRowCount(0)
        self._lights_data = []
        self._clear_detail_panel()

        if not self._current_gaffer or not cmds:
            return

        try:
            lights = GafferManager.get_lights_in_gaffer(
                self._current_gaffer, include_inherited=True
            )
            # Block itemChanged during population to prevent spurious Maya writes
            self._lights_table.blockSignals(True)
            for light_info in lights:
                self._add_light_row(light_info)
            self._lights_table.blockSignals(False)

            # Re-apply current search filter
            self._on_search_changed(self._search_box.text())

        except Exception as e:
            self._lights_table.blockSignals(False)
            logger.error("Failed to populate lights table: {}".format(e))

    def _add_light_row(self, light_info):
        """Add one light row to the table."""
        try:
            light_context = light_info['context']
            light_name = light_info['name']
            target_shape = light_info.get('target', '')
            is_direct = light_info.get('is_direct', True)

            resolved = AttributeResolver.resolve_all_attributes(
                self._current_gaffer, light_name
            )

            def _val(attr, default):
                entry = resolved.get(attr)
                return entry.get('value', default) if entry else default

            row = self._lights_table.rowCount()
            self._lights_table.insertRow(row)

            # Col 0: Light name — show "parent|lightname" with full-path tooltip
            display_name, full_path = self._resolve_display_name(
                light_name, target_shape, is_direct
            )
            name_item = QtWidgets.QTableWidgetItem(display_name)
            name_item.setToolTip(full_path)
            if not is_direct:
                name_item.setForeground(QtGui.QColor("#888"))
            self._lights_table.setItem(row, 0, name_item)

            # Col 1: Mute — interactive checkbox
            muted = bool(_val('muted', False))
            mute_cb = QtWidgets.QCheckBox()
            mute_cb.setChecked(muted)
            mute_container = QtWidgets.QWidget()
            mute_layout = QtWidgets.QHBoxLayout(mute_container)
            mute_layout.addWidget(mute_cb)
            mute_layout.setAlignment(QtCore.Qt.AlignCenter)
            mute_layout.setContentsMargins(0, 0, 0, 0)
            mute_cb.setEnabled(False)  # enabled only in edit mode
            mute_cb.toggled.connect(
                lambda checked, r=row: self._on_mute_toggled(r, checked)
            )
            self._lights_table.setCellWidget(row, 1, mute_container)

            # Col 2: Intensity — read-only until edit mode
            intensity = _val('intensity', 1.0)
            item = QtWidgets.QTableWidgetItem("{:.2f}".format(intensity))
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self._lights_table.setItem(row, 2, item)

            # Col 3: Exposure — read-only until edit mode
            exposure = _val('exposure', 0.0)
            item = QtWidgets.QTableWidgetItem("{:.2f}".format(exposure))
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self._lights_table.setItem(row, 3, item)

            # Col 4: Color swatch button — disabled until edit mode
            color_val = _val('color', (1.0, 1.0, 1.0))
            if isinstance(color_val, (list, tuple)) and len(color_val) == 3:
                cr, cg, cb_val = color_val
            else:
                cr, cg, cb_val = 1.0, 1.0, 1.0
            color_btn = QtWidgets.QPushButton()
            color_btn.setFixedHeight(22)
            color_btn.setEnabled(False)  # enabled only in edit mode
            ri, gi, bi = int(cr * 255), int(cg * 255), int(cb_val * 255)
            color_btn.setStyleSheet(
                "background-color: rgb({},{},{}); border: 1px solid #555;".format(ri, gi, bi)
            )
            color_btn.setToolTip(
                "R:{:.3f}  G:{:.3f}  B:{:.3f}\nClick to change color".format(cr, cg, cb_val)
            )
            color_btn.clicked.connect(
                lambda checked=False, r=row: self._on_color_swatch_clicked(r)
            )
            self._lights_table.setCellWidget(row, 4, color_btn)

            # Store data for later use
            self._lights_data.append({
                'light_context': light_context,
                'light_name': light_name,
                'target_shape': target_shape,
                'is_direct': is_direct,
                'resolved': resolved,
            })

        except Exception as e:
            logger.error("Failed to add row for {}: {}".format(
                light_info.get('name', '?'), e))

    def _resolve_display_name(self, light_name, target_shape, is_direct):
        """Return (display_name, full_path_tooltip) for the light name column.

        Shows the shape node's full DAG path so duplicates are distinguishable.
        Falls back to the stored light_name when Maya is unavailable.
        """
        full_path = light_name
        display = light_name

        if cmds and target_shape and cmds.objExists(target_shape):
            try:
                # Get the full path of the shape node itself
                long_names = cmds.ls(target_shape, long=True) or []
                if long_names:
                    full_path = long_names[0]
                    # Display: last 2 path components  "parent|shape"
                    parts = full_path.strip('|').split('|')
                    if len(parts) >= 2:
                        display = "{}|{}".format(parts[-2], parts[-1])
                    else:
                        display = parts[-1]
            except Exception:
                pass

        if not is_direct:
            display = "  (inh) {}".format(display)

        return display, full_path

    # ------------------------------------------------------------------
    # Edit mode UI toggle
    # ------------------------------------------------------------------

    def _set_editing_enabled(self, enabled):
        """Enable or disable all interactive table controls and the detail panel.

        Called when edit mode starts (enabled=True) or ends (enabled=False).
        """
        for row in range(self._lights_table.rowCount()):
            # Intensity (col 2) and Exposure (col 3): toggle editable flag
            for col in (2, 3):
                item = self._lights_table.item(row, col)
                if item:
                    if enabled:
                        item.setFlags(
                            QtCore.Qt.ItemIsSelectable |
                            QtCore.Qt.ItemIsEnabled |
                            QtCore.Qt.ItemIsEditable
                        )
                    else:
                        item.setFlags(
                            QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
                        )

            # Mute checkbox (col 1)
            mute_container = self._lights_table.cellWidget(row, 1)
            if mute_container:
                cb = mute_container.findChild(QtWidgets.QCheckBox)
                if cb:
                    cb.setEnabled(enabled)

            # Color swatch button (col 4)
            color_btn = self._lights_table.cellWidget(row, 4)
            if color_btn:
                color_btn.setEnabled(enabled)

        # Detail panel
        if self._detail_panel is not None:
            self._detail_panel.set_editing_enabled(enabled)

    # ------------------------------------------------------------------
    # Table item changed (edit mode only — applies to Maya, no CTX write)
    # ------------------------------------------------------------------

    def _on_table_item_changed(self, item):
        """Apply intensity/exposure cell edits to Maya live.

        Only active during edit mode. No CTX node writes — the snapshot/diff
        commit captures all Maya-side changes.
        """
        if self._edit_mode is None:
            return

        row = item.row()
        col = item.column()
        if col not in (2, 3):
            return
        if row >= len(self._lights_data):
            return
        if not cmds:
            return

        data = self._lights_data[row]
        target_shape = data['target_shape']
        attr = 'intensity' if col == 2 else 'exposure'

        try:
            value = float(item.text())
        except (ValueError, TypeError):
            return

        try:
            if target_shape and cmds.objExists(target_shape):
                shape = target_shape
                if cmds.nodeType(target_shape) == 'transform':
                    shapes = cmds.listRelatives(target_shape, shapes=True) or []
                    shape = shapes[0] if shapes else target_shape
                if cmds.attributeQuery(attr, node=shape, exists=True):
                    cmds.setAttr('{}.{}'.format(shape, attr), value)
        except Exception as e:
            logger.error("Failed to apply {} for row {}: {}".format(attr, row, e))

    # ------------------------------------------------------------------
    # Mute & color interactive handlers
    # ------------------------------------------------------------------

    def _on_mute_toggled(self, row, checked):
        """Toggle mute on a Maya light directly (live preview — does NOT write to CTX nodes).

        The change is temporary: switching shot will restore the gaffer-stored value.
        To persist a mute override, use Edit Mode and Commit.
        """
        if row >= len(self._lights_data):
            return
        if not cmds:
            return

        data = self._lights_data[row]
        target_shape = data['target_shape']

        try:
            if target_shape and cmds.objExists(target_shape):
                from core.renderers import get_maya_attr

                shape = target_shape
                if cmds.nodeType(target_shape) == 'transform':
                    shapes = cmds.listRelatives(target_shape, shapes=True) or []
                    shape = shapes[0] if shapes else target_shape

                muted_attr = get_maya_attr(shape, 'muted')
                if muted_attr and cmds.attributeQuery(muted_attr, node=shape, exists=True):
                    cmds.setAttr('{}.{}'.format(shape, muted_attr), 0 if checked else 1)

                transforms = cmds.listRelatives(shape, parent=True, fullPath=True) or []
                if transforms:
                    transform = transforms[0]
                    if cmds.attributeQuery('visibility', node=transform, exists=True):
                        cmds.setAttr('{}.visibility'.format(transform), not checked)

        except Exception as e:
            logger.error("Failed to toggle mute for row {}: {}".format(row, e))

    def _on_color_swatch_clicked(self, row):
        """Open color picker for a light row and store the override."""
        if row >= len(self._lights_data):
            return

        data = self._lights_data[row]
        light_context = data['light_context']
        resolved = data['resolved']

        # Current color from resolved values
        color_val = resolved.get('color', {}).get('value', (1.0, 1.0, 1.0))
        if isinstance(color_val, (list, tuple)) and len(color_val) == 3:
            cr, cg, cb_val = color_val
        else:
            cr, cg, cb_val = 1.0, 1.0, 1.0

        initial = QtGui.QColor(int(cr * 255), int(cg * 255), int(cb_val * 255))
        color = QtWidgets.QColorDialog.getColor(initial, self, "Pick Light Color")
        if not color.isValid():
            return

        nr, ng, nb = color.redF(), color.greenF(), color.blueF()

        try:
            # Update the swatch button in the table (UI only — does NOT write to CTX nodes)
            swatch = self._lights_table.cellWidget(row, 4)
            if swatch:
                swatch.setStyleSheet(
                    "background-color: rgb({},{},{}); border: 1px solid #555;".format(
                        int(nr * 255), int(ng * 255), int(nb * 255)
                    )
                )
                swatch.setToolTip(
                    "R:{:.3f}  G:{:.3f}  B:{:.3f}\nClick to change color".format(nr, ng, nb)
                )

            # Apply to Maya live (temporary — switching shot restores gaffer value)
            target_shape = data['target_shape']
            if cmds and target_shape and cmds.objExists(target_shape):
                shape = target_shape
                if cmds.nodeType(target_shape) == 'transform':
                    shapes = cmds.listRelatives(target_shape, shapes=True) or []
                    shape = shapes[0] if shapes else target_shape
                if cmds.attributeQuery('color', node=shape, exists=True):
                    cmds.setAttr('{}.color'.format(shape), nr, ng, nb, type='double3')

        except Exception as e:
            logger.error("Failed to set color for row {}: {}".format(row, e))

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _on_search_changed(self, text):
        """Filter the lights table to rows matching the search text."""
        text = text.lower().strip()
        for row in range(self._lights_table.rowCount()):
            item = self._lights_table.item(row, 0)
            if item is None:
                self._lights_table.setRowHidden(row, False)
                continue
            match = text == '' or text in item.text().lower() or text in (
                item.toolTip() or ''
            ).lower()
            self._lights_table.setRowHidden(row, not match)

    # ------------------------------------------------------------------
    # Detail panel (right pane)
    # ------------------------------------------------------------------

    def _on_selection_changed(self):
        """Update the detail panel and select the light in Maya when a row is clicked."""
        rows = self._lights_table.selectionModel().selectedRows()
        if not rows:
            self._clear_detail_panel()
            return

        row = rows[0].row()
        if row >= len(self._lights_data):
            self._clear_detail_panel()
            return

        if self._lights_table.isRowHidden(row):
            self._clear_detail_panel()
            return

        data = self._lights_data[row]

        # Select the light transform in Maya viewport
        self._on_select_light_clicked(data['target_shape'])

        # Update detail panel (always shows first selected row)
        self._update_detail_panel(data['light_context'])

    def _on_table_context_menu(self, pos):
        """Show right-click context menu on the lights table."""
        menu = QtWidgets.QMenu(self)

        rows = self._lights_table.selectionModel().selectedRows()
        has_selection = len(rows) > 0
        in_edit_mode = self._edit_mode is not None

        add_action = menu.addAction("+ Add Light")
        add_action.setEnabled(not in_edit_mode and self._current_gaffer is not None)

        menu.addSeparator()

        remove_action = menu.addAction("- Remove Light")
        remove_action.setEnabled(has_selection and not in_edit_mode)

        clear_action = menu.addAction("Clear Override")
        clear_action.setEnabled(has_selection and not in_edit_mode)
        clear_action.setToolTip(
            "Remove this gaffer's overrides for selected lights; "
            "they fall back to inherited values from the parent gaffer."
        )

        action = menu.exec_(self._lights_table.viewport().mapToGlobal(pos))

        if action == add_action:
            self._on_add_light_clicked()
        elif action == remove_action:
            self._on_remove_light_clicked()
        elif action == clear_action:
            self._on_clear_override_clicked()

    def _update_detail_panel(self, light_context):
        """Show the detail panel for the given light context."""
        from ui.light_editor_panel import LightEditorPanel

        self._detail_placeholder.setVisible(False)

        if self._detail_panel is not None:
            try:
                self._detail_panel.refresh(self._current_gaffer, light_context)
                return
            except Exception:
                # Panel might be stale; recreate it
                self._right_layout.removeWidget(self._detail_panel)
                self._detail_panel.deleteLater()
                self._detail_panel = None

        self._detail_panel = LightEditorPanel(
            gaffer=self._current_gaffer,
            light_context=light_context,
            parent=self
        )
        self._detail_panel.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        # Match current edit mode state so panel is live if already in edit mode
        if self._edit_mode is not None:
            self._detail_panel.set_editing_enabled(True)
        self._right_layout.addWidget(self._detail_panel, 1)  # stretch=1

    def _clear_detail_panel(self):
        """Remove the detail panel and show the placeholder."""
        if self._detail_panel is not None:
            self._right_layout.removeWidget(self._detail_panel)
            self._detail_panel.deleteLater()
            self._detail_panel = None
        self._detail_placeholder.setVisible(True)

    # ------------------------------------------------------------------
    # Edit Mode
    # ------------------------------------------------------------------

    # HUD block ID for viewport edit-mode indicator
    _EDIT_HUD_BLOCK = 'GafferEditModeHUD'

    def _show_viewport_hud(self):
        """Show a persistent 'GAFFER EDIT MODE' HUD in the Maya 3D viewport."""
        if not cmds:
            return
        try:
            if cmds.headsUpDisplay(self._EDIT_HUD_BLOCK, exists=True):
                cmds.headsUpDisplay(self._EDIT_HUD_BLOCK, remove=True)
            gaffer_name = self._current_gaffer.get_gaffer_name() if self._current_gaffer else '?'
            cmds.headsUpDisplay(
                self._EDIT_HUD_BLOCK,
                section=2, block=0,
                blockSize='large',
                label='GAFFER EDIT MODE  [{}]'.format(gaffer_name),
                labelFontSize='large',
                command=lambda: '',
                event='idle',
            )
        except Exception as e:
            logger.debug("HUD show failed (non-fatal): %s", e)

    def _hide_viewport_hud(self):
        """Remove the viewport edit-mode HUD."""
        if not cmds:
            return
        try:
            if cmds.headsUpDisplay(self._EDIT_HUD_BLOCK, exists=True):
                cmds.headsUpDisplay(self._EDIT_HUD_BLOCK, remove=True)
        except Exception as e:
            logger.debug("HUD hide failed (non-fatal): %s", e)

    def _on_enter_edit_mode(self):
        if not self._current_gaffer:
            QtWidgets.QMessageBox.warning(self, "No Gaffer Selected",
                                          "Please select a gaffer first.")
            return
        from core.lock_manager import LockManager
        if LockManager.is_locked(self._current_gaffer.node_name):
            QtWidgets.QMessageBox.information(
                self, 'Locked',
                'This gaffer is locked and cannot be edited.\n'
                'Use "Unlock Gaffer" to enable editing.'
            )
            return
        if not cmds:
            QtWidgets.QMessageBox.warning(self, "Maya Not Available",
                                          "Maya is not available.")
            return
        try:
            self._edit_mode = EditMode(self._current_gaffer)
            self._edit_mode.enter()

            self._edit_mode_label.setText(
                "Edit Mode: ON  (edit lights in Maya viewport, then Commit or Discard)"
            )
            self._edit_mode_label.setStyleSheet("font-weight: bold; color: #FFA000;")
            self._enter_edit_button.setVisible(False)
            self._commit_button.setVisible(True)
            self._discard_button.setVisible(True)

            self._gaffer_combo.setEnabled(False)
            self._refresh_button.setEnabled(False)
            self._add_light_button.setEnabled(False)
            self._remove_light_button.setEnabled(False)
            self._clear_override_button.setEnabled(False)

            # Unlock all interactive table controls and detail panel
            self._set_editing_enabled(True)

            # Show viewport HUD so the artist knows edit mode is active
            self._show_viewport_hud()

            logger.info("Edit mode entered for: {}".format(
                self._current_gaffer.get_gaffer_name()))

        except Exception as e:
            logger.error("Failed to enter edit mode: {}".format(e))
            QtWidgets.QMessageBox.critical(self, "Error",
                                           "Failed to enter edit mode:\n{}".format(e))
            self._edit_mode = None

    def _on_commit_edit_mode(self):
        if self._edit_mode is None:
            return
        try:
            changed = self._edit_mode.commit()

            total_attrs = sum(len(v) for v in changed.values())
            msg = "Stored {} override(s) across {} light(s).".format(
                total_attrs, len(changed))
            if changed:
                details = [
                    "{}: {}".format(ln, ", ".join(attrs.keys()))
                    for ln, attrs in changed.items()
                ]
                msg += "\n\n" + "\n".join(details)

            QtWidgets.QMessageBox.information(self, "Commit Complete", msg)
            logger.info("Edit mode committed: {} lights changed".format(len(changed)))

            if self._current_gaffer:
                try:
                    LightOperations.apply_gaffer_to_all_lights(self._current_gaffer)
                except Exception as apply_err:
                    logger.warning("Failed to apply gaffer after commit: {}".format(apply_err))

        except Exception as e:
            logger.error("Failed to commit edit mode: {}".format(e))
            QtWidgets.QMessageBox.critical(self, "Error",
                                           "Failed to commit changes:\n{}".format(e))
            return

        self._edit_mode = None
        self._exit_edit_mode_ui()
        self._populate_lights_table()
        self._refresh_lock_state()

    def _on_discard_edit_mode(self):
        if self._edit_mode is None:
            return
        reply = QtWidgets.QMessageBox.question(
            self, "Discard Changes",
            "Discard all edits and restore original values?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return
        try:
            restored = self._edit_mode.cancel()
            logger.info("Edit mode discarded: {} lights restored".format(restored))
        except Exception as e:
            logger.error("Failed to discard edit mode: {}".format(e))
            QtWidgets.QMessageBox.critical(self, "Error",
                                           "Failed to restore values:\n{}".format(e))
            return
        self._edit_mode = None
        self._exit_edit_mode_ui()

    def _exit_edit_mode_ui(self):
        self._edit_mode_label.setText("Edit Mode: OFF")
        self._edit_mode_label.setStyleSheet("font-weight: bold;")
        self._enter_edit_button.setVisible(True)
        self._commit_button.setVisible(False)
        self._discard_button.setVisible(False)
        self._gaffer_combo.setEnabled(True)
        self._refresh_button.setEnabled(True)
        self._add_light_button.setEnabled(True)
        self._remove_light_button.setEnabled(True)
        self._clear_override_button.setEnabled(True)

        # Lock all interactive controls back to read-only
        self._set_editing_enabled(False)

        # Remove viewport HUD
        self._hide_viewport_hud()

    # ------------------------------------------------------------------
    # Gaffer creation (unified Sequence + Shot)
    # ------------------------------------------------------------------

    def _on_create_gaffer(self):
        """Unified gaffer creation — asks Sequence or Shot."""
        if not cmds:
            QtWidgets.QMessageBox.warning(self, "Maya Not Available",
                                          "Maya is not available.")
            return

        choices = ["Sequence Gaffer", "Shot Gaffer"]
        choice, ok = QtWidgets.QInputDialog.getItem(
            self, "Create Gaffer", "Attach to:", choices, 0, False
        )
        if not ok:
            return

        if choice == "Sequence Gaffer":
            self._create_sequence_gaffer()
        else:
            self._create_shot_gaffer()

    def _create_sequence_gaffer(self):
        """Create a gaffer and attach it to a sequence."""
        try:
            from core.nodes.wrappers.sequence import CTXSequenceNode

            all_seqs = CTXSequenceNode.list_all()
            if not all_seqs:
                QtWidgets.QMessageBox.warning(
                    self, "No Sequences",
                    "No CTX_Sequence nodes found. Create shots first."
                )
                return

            seq_labels = []
            for s in all_seqs:
                existing = s.get_gaffer()
                label = s.get_attribute('sequenceCode') or s.node_name
                if existing:
                    label += "  [has gaffer: {}]".format(existing)
                seq_labels.append(label)

            seq_label, ok = QtWidgets.QInputDialog.getItem(
                self, "Select Sequence", "Attach to:", seq_labels, 0, False
            )
            if not ok:
                return

            seq = all_seqs[seq_labels.index(seq_label)]
            seq_code = seq.get_attribute('sequenceCode') or seq.node_name

            name, ok = QtWidgets.QInputDialog.getText(
                self, "Gaffer Name", "Name:", text="seq_{}".format(seq_code)
            )
            if not ok or not name.strip():
                return

            parent_gaffer = self._ask_parent_gaffer()
            if parent_gaffer is False:
                return  # User cancelled

            gaffer = CTXLightGafferNode.create(
                gafferName=name.strip(), gafferType='sequence'
            )
            seq.set_gaffer(gaffer)

            if parent_gaffer is not None:
                gaffer.set_parent_gaffer(parent_gaffer)
                logger.info("Parent gaffer set: {}".format(parent_gaffer.node_name))

            logger.info("Created sequence gaffer '{}' for seq '{}'".format(
                gaffer.node_name, seq_code))
            self._refresh_gaffer_list()
            self.select_gaffer(gaffer)

        except Exception as e:
            logger.error("Failed to create sequence gaffer: {}".format(e))
            QtWidgets.QMessageBox.critical(self, "Error",
                                           "Failed to create sequence gaffer:\n{}".format(e))

    def _create_shot_gaffer(self):
        """Create a gaffer and attach it to a shot."""
        try:
            from core.nodes.wrappers.shot import CTXShotNode

            all_shots = CTXShotNode.list_all()
            if not all_shots:
                QtWidgets.QMessageBox.warning(
                    self, "No Shots",
                    "No CTX_Shot nodes found. Create shots first."
                )
                return

            shot_labels = []
            for s in all_shots:
                existing = s.get_gaffer()
                label = "{}_{}".format(
                    s.get_seq_code() or '?', s.get_shot_code() or s.node_name
                )
                if existing:
                    label += "  [has gaffer: {}]".format(existing)
                shot_labels.append(label)

            shot_label, ok = QtWidgets.QInputDialog.getItem(
                self, "Select Shot", "Attach to:", shot_labels, 0, False
            )
            if not ok:
                return

            shot = all_shots[shot_labels.index(shot_label)]
            shot_id = "{}_{}".format(
                shot.get_seq_code() or '?', shot.get_shot_code() or shot.node_name
            )

            name, ok = QtWidgets.QInputDialog.getText(
                self, "Gaffer Name", "Name:", text=shot_id
            )
            if not ok or not name.strip():
                return

            parent_gaffer = self._ask_parent_gaffer()
            if parent_gaffer is False:
                return

            gaffer = CTXLightGafferNode.create(
                gafferName=name.strip(), gafferType='shot'
            )
            shot.set_gaffer(gaffer)

            if parent_gaffer is not None:
                gaffer.set_parent_gaffer(parent_gaffer)
                logger.info("Parent gaffer set: {}".format(parent_gaffer.node_name))

            logger.info("Created shot gaffer '{}' for shot '{}'".format(
                gaffer.node_name, shot_id))
            self._refresh_gaffer_list()
            self.select_gaffer(gaffer)

        except Exception as e:
            logger.error("Failed to create shot gaffer: {}".format(e))
            QtWidgets.QMessageBox.critical(self, "Error",
                                           "Failed to create shot gaffer:\n{}".format(e))

    def _ask_parent_gaffer(self):
        """Ask user to optionally choose a parent gaffer.

        Returns:
            CTXLightGafferNode: chosen parent, or None if standalone chosen,
            or False if user cancelled the dialog.
        """
        all_gaffers = ChainOperations.list_all_gaffers()
        if not all_gaffers:
            return None

        choices = ["(none — standalone)"] + [g['name'] for g in all_gaffers]
        chosen, ok = QtWidgets.QInputDialog.getItem(
            self, "Parent Gaffer",
            "Inherit from (optional):", choices, 0, False
        )
        if not ok:
            return False

        if chosen == "(none — standalone)":
            return None

        for g in all_gaffers:
            if g['name'] == chosen:
                return g['wrapper']
        return None

    # ------------------------------------------------------------------
    # Inherit controls
    # ------------------------------------------------------------------

    def _on_set_parent_gaffer(self):
        if not cmds:
            QtWidgets.QMessageBox.warning(self, "Maya Not Available", "Maya is not available.")
            return
        if not self._current_gaffer:
            QtWidgets.QMessageBox.warning(self, "No Gaffer Selected", "Select a gaffer first.")
            return
        try:
            all_gaffers = ChainOperations.list_all_gaffers()
            current_node = self._current_gaffer.node_name
            current_chain = {g.node_name for g in self._current_gaffer.build_chain()}

            candidates = [
                g for g in all_gaffers
                if g['node'] != current_node and g['node'] not in current_chain
            ]
            if not candidates:
                QtWidgets.QMessageBox.warning(self, "No Candidates",
                                              "No other gaffers available as parent.")
                return

            labels = ["{} [{}]".format(g['name'], g['type']) for g in candidates]
            chosen, ok = QtWidgets.QInputDialog.getItem(
                self, "Set Parent Gaffer", "Inherit from:", labels, 0, False
            )
            if not ok:
                return

            parent_info = candidates[labels.index(chosen)]
            self._current_gaffer.set_parent_gaffer(parent_info['wrapper'])
            logger.info("Set parent '{}' on '{}'".format(
                parent_info['name'], self._current_gaffer.get_gaffer_name()))

            self._refresh_gaffer_list()
            self.select_gaffer(self._current_gaffer)

        except Exception as e:
            logger.error("Failed to set parent: {}".format(e))
            QtWidgets.QMessageBox.critical(self, "Error",
                                           "Failed to set parent:\n{}".format(e))

    def _on_clear_parent_gaffer(self):
        if not cmds:
            QtWidgets.QMessageBox.warning(self, "Maya Not Available", "Maya is not available.")
            return
        if not self._current_gaffer:
            QtWidgets.QMessageBox.warning(self, "No Gaffer Selected", "Select a gaffer first.")
            return
        try:
            existing_parent = self._current_gaffer.get_parent_gaffer()
            if existing_parent is None:
                QtWidgets.QMessageBox.information(
                    self, "No Parent",
                    "Gaffer '{}' has no parent.".format(
                        self._current_gaffer.get_gaffer_name())
                )
                return

            parent_name = existing_parent.get_gaffer_name()
            reply = QtWidgets.QMessageBox.question(
                self, "Clear Parent",
                "Remove inheritance from '{}'?\n\nGaffer will become standalone.".format(
                    parent_name),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

            src = "{}.message".format(existing_parent.node_name)
            dst = "{}.parentGaffer".format(self._current_gaffer.node_name)
            if cmds.isConnected(src, dst):
                cmds.disconnectAttr(src, dst)

            logger.info("Cleared parent '{}' from '{}'".format(
                parent_name, self._current_gaffer.get_gaffer_name()))

            self._refresh_gaffer_list()
            self.select_gaffer(self._current_gaffer)

        except Exception as e:
            logger.error("Failed to clear parent: {}".format(e))
            QtWidgets.QMessageBox.critical(self, "Error",
                                           "Failed to clear parent:\n{}".format(e))

    # ------------------------------------------------------------------
    # Light list actions
    # ------------------------------------------------------------------

    def _on_add_light_clicked(self):
        if not self._current_gaffer:
            QtWidgets.QMessageBox.warning(self, "No Gaffer Selected",
                                          "Please select a gaffer first.")
            return
        try:
            from ui.add_light_dialog import AddLightDialog
            dialog = AddLightDialog(self._current_gaffer, parent=self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                self._populate_lights_table()
        except Exception as e:
            logger.error("Failed to open add light dialog: {}".format(e))
            QtWidgets.QMessageBox.critical(self, "Error",
                                           "Failed to open add light dialog:\n{}".format(e))

    def _on_remove_light_clicked(self):
        if not self._current_gaffer:
            QtWidgets.QMessageBox.warning(self, "No Gaffer Selected",
                                          "Please select a gaffer first.")
            return

        rows = self._lights_table.selectionModel().selectedRows()
        if not rows:
            QtWidgets.QMessageBox.warning(self, "No Light Selected",
                                          "Please select a light to remove.")
            return

        row = rows[0].row()
        if row >= len(self._lights_data):
            return

        data = self._lights_data[row]
        if not data.get('is_direct', True):
            QtWidgets.QMessageBox.warning(
                self, "Cannot Remove Inherited Light",
                "Light '{}' is inherited from a parent gaffer.\n"
                "Remove it there.".format(data['light_name'])
            )
            return

        reply = QtWidgets.QMessageBox.question(
            self, "Remove Light",
            "Remove '{}' from gaffer '{}'?\n\n"
            "This deletes the CTX_LightContext node but not the Maya light.".format(
                data['light_name'], self._current_gaffer.get_gaffer_name()),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            try:
                data['light_context'].delete()
                self._populate_lights_table()
                logger.info("Removed light '{}'".format(data['light_name']))
            except Exception as e:
                logger.error("Failed to remove light: {}".format(e))
                QtWidgets.QMessageBox.critical(self, "Error",
                                               "Failed to remove light:\n{}".format(e))

    def _on_clear_override_clicked(self):
        """Remove this gaffer's local CTX overrides for all selected lights.

        Per light:
          - Direct + has parent value  → deletes local CTX; light becomes (inh)
          - Direct + no parent value   → warns and removes from gaffer entirely
          - Inherited (no local CTX)   → skipped (already fully inherited)
        """
        if not self._current_gaffer:
            QtWidgets.QMessageBox.warning(self, "No Gaffer Selected",
                                          "Please select a gaffer first.")
            return

        sel_rows = self._lights_table.selectionModel().selectedRows()
        if not sel_rows:
            QtWidgets.QMessageBox.warning(self, "No Light Selected",
                                          "Please select one or more lights first.")
            return

        from core.gaffer.manager import GafferManager

        parent_gaffer = self._current_gaffer.get_parent_gaffer()

        # Classify each selected row
        to_clear = []       # (data, has_parent_value)
        already_inherited = []

        for idx in sel_rows:
            row = idx.row()
            if row >= len(self._lights_data):
                continue
            data = self._lights_data[row]

            if not data.get('is_direct', True):
                already_inherited.append(data['light_name'])
                continue

            has_parent_value = False
            if parent_gaffer is not None:
                try:
                    target = GafferManager._find_light_in_chain(
                        parent_gaffer, data['light_name']
                    )
                    has_parent_value = target is not None
                except Exception:
                    pass
            to_clear.append((data, has_parent_value))

        if not to_clear:
            names = ', '.join(already_inherited) or 'selected lights'
            QtWidgets.QMessageBox.information(
                self, "Already Inherited",
                "{} already inherit all values from the parent gaffer — "
                "nothing to clear.".format(names)
            )
            return

        # Build confirmation message
        fall_back = [d['light_name'] for d, hp in to_clear if hp]
        remove_entirely = [d['light_name'] for d, hp in to_clear if not hp]

        msg_parts = []
        if fall_back:
            msg_parts.append(
                "Fall back to parent value:\n  " + "\n  ".join(fall_back)
            )
        if remove_entirely:
            msg_parts.append(
                "Remove from gaffer entirely (no parent value):\n  " +
                "\n  ".join(remove_entirely)
            )
        if already_inherited:
            msg_parts.append(
                "Skipped (already inherited):\n  " + "\n  ".join(already_inherited)
            )

        reply = QtWidgets.QMessageBox.question(
            self, "Clear Override",
            "Gaffer: {}\n\n{}".format(
                self._current_gaffer.get_gaffer_name(), "\n\n".join(msg_parts)
            ),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        errors = []
        cleared = 0
        for data, _ in to_clear:
            try:
                data['light_context'].delete()
                cleared += 1
                logger.info("Cleared override for '{}' in '{}'".format(
                    data['light_name'], self._current_gaffer.get_gaffer_name()))
            except Exception as e:
                errors.append("{}: {}".format(data['light_name'], e))
                logger.error("Failed to clear override for '{}': {}".format(
                    data['light_name'], e))

        self._populate_lights_table()

        if errors:
            QtWidgets.QMessageBox.warning(
                self, "Partial Failure",
                "Cleared {} override(s). Errors:\n{}".format(cleared, "\n".join(errors))
            )

    def _on_apply_clicked(self):
        if not self._current_gaffer:
            QtWidgets.QMessageBox.warning(self, "No Gaffer Selected",
                                          "Please select a gaffer first.")
            return
        try:
            results = LightOperations.apply_gaffer_to_all_lights(self._current_gaffer)
            ok_count = len([r for r in results.values() if r])
            QtWidgets.QMessageBox.information(
                self, "Apply Complete",
                "Applied gaffer '{}' to {} of {} lights.".format(
                    self._current_gaffer.get_gaffer_name(), ok_count, len(results))
            )
            logger.info("Applied gaffer to {} lights".format(ok_count))
        except Exception as e:
            logger.error("Failed to apply gaffer: {}".format(e))
            QtWidgets.QMessageBox.critical(self, "Error",
                                           "Failed to apply gaffer:\n{}".format(e))

    def _on_select_light_clicked(self, target_shape):
        if not cmds or not target_shape:
            return
        try:
            if not cmds.objExists(target_shape):
                return

            node_type = cmds.nodeType(target_shape)
            if node_type == 'transform':
                # target_shape IS the light transform (or a group).
                # If it has direct shape children it's the light transform — select it.
                # If not (group), find the first light shape descendant and select its parent.
                child_shapes = cmds.listRelatives(
                    target_shape, shapes=True, fullPath=True) or []
                if child_shapes:
                    select_node = target_shape
                else:
                    all_shapes = cmds.listRelatives(
                        target_shape, shapes=True, fullPath=True,
                        allDescendants=True) or []
                    if all_shapes:
                        parents = cmds.listRelatives(
                            all_shapes[0], parent=True, fullPath=True) or []
                        select_node = parents[0] if parents else target_shape
                    else:
                        select_node = target_shape
            else:
                # target_shape is a shape node — select its parent transform
                parents = cmds.listRelatives(
                    target_shape, parent=True, fullPath=True) or []
                select_node = parents[0] if parents else target_shape

            if cmds.objExists(select_node):
                cmds.select(select_node, replace=True)
        except Exception as e:
            logger.error("Failed to select light: {}".format(e))

    # ------------------------------------------------------------------
    # Lock state helpers
    # ------------------------------------------------------------------

    def _refresh_lock_state(self):
        """Update banner visibility, Edit button state, and lock button label."""
        if self._current_gaffer is None:
            self._lock_banner.setVisible(False)
            self._lock_btn.setVisible(False)
            return

        from core.lock_manager import LockManager
        info = LockManager.get_lock_info(self._current_gaffer.node_name)
        locked = info['is_locked']

        self._lock_banner.setVisible(locked)
        if locked:
            by = info.get('locked_by', '')
            self._lock_banner.setText(
                'Read only -- locked by {}. Edit mode disabled.'.format(by) if by
                else 'Read only -- locked. Edit mode disabled.'
            )

        # Edit button disabled when locked
        self._enter_edit_button.setEnabled(not locked)

        # Lock button label toggles
        self._lock_btn.setText('Unlock Gaffer' if locked else 'Lock Gaffer')
        self._lock_btn.setVisible(True)

    def _on_toggle_gaffer_lock(self):
        """Toggle lock state of the currently selected gaffer."""
        if self._current_gaffer is None:
            return

        from core.lock_manager import LockManager
        if LockManager.is_locked(self._current_gaffer.node_name):
            LockManager.unlock_node(self._current_gaffer.node_name)
        else:
            LockManager.lock_node(self._current_gaffer.node_name)

        self._refresh_lock_state()

    # ------------------------------------------------------------------
    # Gaffer combo handlers
    # ------------------------------------------------------------------

    def _on_gaffer_changed(self, index):
        if index < 0:
            return
        if self._edit_mode is not None and self._edit_mode.is_active:
            return

        gaffer_wrapper = self._gaffer_combo.itemData(index)
        self._current_gaffer = gaffer_wrapper
        self._update_chain_label()
        self._populate_lights_table()
        self._refresh_lock_state()

    def _on_refresh_clicked(self):
        self._refresh_gaffer_list()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def select_gaffer(self, gaffer):
        """Select a specific gaffer in the dropdown by wrapper or node name."""
        self._refresh_gaffer_list()

        target_node = gaffer.node_name if hasattr(gaffer, 'node_name') else str(gaffer)
        for i in range(self._gaffer_combo.count()):
            item_gaffer = self._gaffer_combo.itemData(i)
            if item_gaffer is not None and hasattr(item_gaffer, 'node_name'):
                if item_gaffer.node_name == target_node:
                    self._gaffer_combo.setCurrentIndex(i)
                    return

    def refresh(self):
        """Refresh list and table (called on shot switch when no specific gaffer)."""
        if self._edit_mode is not None and self._edit_mode.is_active:
            return
        self._refresh_gaffer_list()

    def showEvent(self, event):
        """Refresh lock state when dialog becomes visible."""
        QtWidgets.QDialog.showEvent(self, event)
        self._refresh_lock_state()

    def closeEvent(self, event):
        """Clear singleton reference and viewport HUD on close."""
        self._hide_viewport_hud()
        GafferManagerDialog._instance = None
        QtWidgets.QDialog.closeEvent(self, event)
