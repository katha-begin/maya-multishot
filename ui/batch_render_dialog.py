"""Batch Render dialog -- Monitor and Configure tabs.

Non-modal dialog for configuring and monitoring multi-shot batch renders.
Launched from the Context Manager menu or from the Multishot Manager
right-click Quick Render action.
"""

import threading

from core.logging_config import get_logger

logger = get_logger(__name__)

try:
    from PySide6 import QtCore, QtWidgets, QtGui
    Signal = QtCore.Signal
except ImportError:
    from PySide2 import QtCore, QtWidgets, QtGui
    Signal = QtCore.Signal

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False

from ui.base_dialog import BaseDialog


# ---------------------------------------------------------------------------
# Add Shot popup dialog
# ---------------------------------------------------------------------------

class AddShotDialog(QtWidgets.QDialog):
    """Popup dialog listing CTX shots for selection.

    Shows all shots from CTXShotNode.list_all() that are not already
    in the caller's shot list. Greyed out entries cannot be re-added.
    """

    def __init__(self, existing_shot_ids=None, parent=None):
        super(AddShotDialog, self).__init__(parent)
        self.setWindowTitle('Add Shots')
        self.setModal(True)
        self.resize(480, 380)
        self._existing = set(existing_shot_ids or [])
        self._selected = []
        self._setup_ui()
        self._populate()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Filter
        filter_row = QtWidgets.QHBoxLayout()
        filter_row.addWidget(QtWidgets.QLabel('Filter:'))
        self._filter_edit = QtWidgets.QLineEdit()
        self._filter_edit.setPlaceholderText('Filter shots...')
        self._filter_edit.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self._filter_edit)
        layout.addLayout(filter_row)

        # List
        self._list = QtWidgets.QTableWidget(0, 2)
        self._list.setHorizontalHeaderLabels(['Shot', 'Frame Range'])
        self._list.horizontalHeader().setStretchLastSection(False)
        self._list.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self._list.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        self._list.setColumnWidth(1, 80)
        self._list.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        layout.addWidget(self._list)

        # Select all / clear row
        sel_row = QtWidgets.QHBoxLayout()
        select_all_btn = QtWidgets.QPushButton('Select All')
        select_all_btn.clicked.connect(self._select_all)
        clear_btn = QtWidgets.QPushButton('Clear')
        clear_btn.clicked.connect(self._clear_all)
        sel_row.addWidget(select_all_btn)
        sel_row.addWidget(clear_btn)
        sel_row.addStretch()
        layout.addLayout(sel_row)

        # OK / Cancel
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        add_btn = QtWidgets.QPushButton('Add Selected')
        add_btn.setDefault(True)
        add_btn.clicked.connect(self._on_add)
        cancel_btn = QtWidgets.QPushButton('Cancel')
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _populate(self):
        """Load shots from CTXShotNode.list_all()."""
        self._all_rows = []  # list of (shot_id, frame_range_text, ep, seq, shot)
        if not MAYA_AVAILABLE:
            return
        try:
            from core.nodes.wrappers import CTXShotNode
            for sn in CTXShotNode.list_all():
                ep = sn.get_ep_code()
                seq = sn.get_seq_code()
                shot = sn.get_shot_code()
                shot_id = '%s_%s_%s' % (ep, seq, shot)
                try:
                    start, end = sn.get_frame_range()
                    fr = '%d-%d' % (start, end)
                except Exception:
                    fr = '----'
                self._all_rows.append((shot_id, fr, ep, seq, shot))
        except Exception as exc:
            logger.warning("AddShotDialog: failed to list shots: %s", exc)
        self._render_rows(self._all_rows)

    def _render_rows(self, rows):
        self._list.setRowCount(0)
        for shot_id, fr, ep, seq, shot in rows:
            row = self._list.rowCount()
            self._list.insertRow(row)

            already_in = shot_id in self._existing
            chk = QtWidgets.QTableWidgetItem(shot_id)
            chk.setFlags(chk.flags() | QtCore.Qt.ItemIsUserCheckable)
            chk.setCheckState(QtCore.Qt.Unchecked)
            if already_in:
                chk.setForeground(QtGui.QColor(120, 120, 120))
                chk.setFlags(chk.flags() & ~QtCore.Qt.ItemIsEnabled)
            self._list.setItem(row, 0, chk)

            fr_item = QtWidgets.QTableWidgetItem(fr)
            fr_item.setTextAlignment(QtCore.Qt.AlignCenter)
            if already_in:
                fr_item.setForeground(QtGui.QColor(120, 120, 120))
            self._list.setItem(row, 1, fr_item)
            # Store ep/seq/shot for later
            self._list.item(row, 0).setData(QtCore.Qt.UserRole, (ep, seq, shot, fr))

    def _apply_filter(self, text):
        text = text.lower()
        filtered = [r for r in self._all_rows if text in r[0].lower()] if text else self._all_rows
        self._render_rows(filtered)

    def _select_all(self):
        for row in range(self._list.rowCount()):
            item = self._list.item(row, 0)
            if item and (item.flags() & QtCore.Qt.ItemIsEnabled):
                item.setCheckState(QtCore.Qt.Checked)

    def _clear_all(self):
        for row in range(self._list.rowCount()):
            item = self._list.item(row, 0)
            if item:
                item.setCheckState(QtCore.Qt.Unchecked)

    def _on_add(self):
        self._selected = []
        for row in range(self._list.rowCount()):
            item = self._list.item(row, 0)
            if item and item.checkState() == QtCore.Qt.Checked:
                data = item.data(QtCore.Qt.UserRole)
                if data:
                    ep, seq, shot, fr = data
                    self._selected.append({
                        'ep': ep, 'seq': seq, 'shot': shot,
                        'frame_range': fr,
                    })
        self.accept()

    def get_selected(self):
        """Return list of selected shot dicts."""
        return self._selected


# ---------------------------------------------------------------------------
# Settings dialog (gear button)
# ---------------------------------------------------------------------------

class RenderSettingsDialog(QtWidgets.QDialog):
    """Small settings dialog for batch render options."""

    def __init__(self, settings, parent=None):
        super(RenderSettingsDialog, self).__init__(parent)
        self.setWindowTitle('Render Settings')
        self.setModal(True)
        self.resize(360, 220)
        self._settings = dict(settings)
        self._setup_ui()

    def _setup_ui(self):
        layout = QtWidgets.QFormLayout(self)
        layout.setSpacing(8)

        # Frame range
        frame_row = QtWidgets.QHBoxLayout()
        self._auto_check = QtWidgets.QCheckBox('Auto from shot')
        self._auto_check.setChecked(self._settings.get('auto_frame', True))
        self._start_spin = QtWidgets.QSpinBox()
        self._start_spin.setRange(0, 99999)
        self._start_spin.setValue(self._settings.get('start_frame', 1001))
        self._end_spin = QtWidgets.QSpinBox()
        self._end_spin.setRange(0, 99999)
        self._end_spin.setValue(self._settings.get('end_frame', 1100))
        self._auto_check.toggled.connect(lambda c: self._start_spin.setEnabled(not c))
        self._auto_check.toggled.connect(lambda c: self._end_spin.setEnabled(not c))
        self._start_spin.setEnabled(not self._settings.get('auto_frame', True))
        self._end_spin.setEnabled(not self._settings.get('auto_frame', True))
        frame_row.addWidget(self._auto_check)
        frame_row.addWidget(QtWidgets.QLabel('Start'))
        frame_row.addWidget(self._start_spin)
        frame_row.addWidget(QtWidgets.QLabel('End'))
        frame_row.addWidget(self._end_spin)
        layout.addRow('Frame Range:', frame_row)

        # Temp scenes
        temp_row = QtWidgets.QHBoxLayout()
        self._temp_max_spin = QtWidgets.QSpinBox()
        self._temp_max_spin.setRange(0, 100)
        self._temp_max_spin.setValue(self._settings.get('temp_max', 5))
        self._temp_max_spin.setFixedWidth(60)
        self._temp_dir_edit = QtWidgets.QLineEdit()
        self._temp_dir_edit.setPlaceholderText('(auto)')
        self._temp_dir_edit.setText(self._settings.get('temp_dir', ''))
        browse_btn = QtWidgets.QPushButton('Browse')
        browse_btn.clicked.connect(self._browse_temp_dir)
        temp_row.addWidget(QtWidgets.QLabel('Max'))
        temp_row.addWidget(self._temp_max_spin)
        temp_row.addWidget(self._temp_dir_edit)
        temp_row.addWidget(browse_btn)
        layout.addRow('Temp Scenes:', temp_row)

        # Reserve GPUs
        self._reserve_spin = QtWidgets.QSpinBox()
        self._reserve_spin.setRange(0, 8)
        self._reserve_spin.setValue(self._settings.get('reserve_gpus', 1))
        self._reserve_spin.setFixedWidth(60)
        layout.addRow('Reserve GPUs:', self._reserve_spin)

        # OK / Cancel
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QtWidgets.QPushButton('OK')
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QtWidgets.QPushButton('Cancel')
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addRow(btn_row)

    def _browse_temp_dir(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Select Temp Scene Directory', self._temp_dir_edit.text())
        if path:
            self._temp_dir_edit.setText(path)

    def get_settings(self):
        """Return updated settings dict."""
        return {
            'auto_frame': self._auto_check.isChecked(),
            'start_frame': self._start_spin.value(),
            'end_frame': self._end_spin.value(),
            'temp_max': self._temp_max_spin.value(),
            'temp_dir': self._temp_dir_edit.text().strip(),
            'reserve_gpus': self._reserve_spin.value(),
        }


# ---------------------------------------------------------------------------
# Main dialog
# ---------------------------------------------------------------------------

class BatchRenderDialog(BaseDialog):
    """Non-modal Batch Render Monitor and Configure dialog.

    Monitor tab  -- persistent task list showing all render jobs this session.
    Configure tab -- shot list + layer list + Start / Dry Run buttons.
    """

    _instance = None

    # Thread-safe signal for progress updates from render thread
    progress_updated = Signal(object, str, str, str)  # job, layer, status, msg

    def __init__(self, parent=None):
        self._render_thread = None
        self._cancelled = False
        self._gpu_timer = None
        self._settings = {
            'auto_frame': True,
            'start_frame': 1001,
            'end_frame': 1100,
            'temp_max': 5,
            'temp_dir': '',
            'reserve_gpus': 1,
        }

        super(BatchRenderDialog, self).__init__(parent=parent)

        self.setWindowTitle('Batch Render')
        self.setModal(False)
        self.resize(780, 640)

        self._populate_layer_list()
        self._refresh_gpu_panel()
        self._gpu_timer.start()

    # ------------------------------------------------------------------
    # Singleton helpers
    # ------------------------------------------------------------------

    @classmethod
    def get_or_create(cls, parent=None):
        """Return existing instance or create a new one."""
        if cls._instance is None or not cls._instance.isVisible():
            cls._instance = cls(parent=parent)
        return cls._instance

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        self._gpu_timer = QtCore.QTimer(self)
        self._gpu_timer.setInterval(5000)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Top toolbar: tabs + gear
        toolbar = QtWidgets.QHBoxLayout()
        self._tab_widget = QtWidgets.QTabWidget()
        toolbar.addWidget(self._tab_widget)

        gear_btn = QtWidgets.QPushButton('\u2699 Settings')
        gear_btn.setFixedWidth(90)
        gear_btn.setToolTip('Configure render settings')
        gear_btn.clicked.connect(self._open_settings)
        toolbar.addWidget(gear_btn, 0, QtCore.Qt.AlignTop)
        main_layout.addLayout(toolbar)

        # ---- Monitor tab ----
        monitor_widget = QtWidgets.QWidget()
        monitor_layout = QtWidgets.QVBoxLayout(monitor_widget)
        monitor_layout.setContentsMargins(4, 4, 4, 4)

        # GPU status
        gpu_group = QtWidgets.QGroupBox('GPU Status')
        gpu_inner = QtWidgets.QVBoxLayout(gpu_group)
        self._gpu_table = QtWidgets.QTableWidget(0, 5)
        self._gpu_table.setHorizontalHeaderLabels(['GPU', 'Name', 'VRAM', 'Util', 'Status'])
        self._gpu_table.horizontalHeader().setStretchLastSection(True)
        self._gpu_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self._gpu_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._gpu_table.setFixedHeight(100)
        gpu_inner.addWidget(self._gpu_table)
        monitor_layout.addWidget(gpu_group)

        # Task list
        task_header = QtWidgets.QHBoxLayout()
        task_header.addWidget(QtWidgets.QLabel('Render Tasks'))
        task_header.addStretch()
        clear_btn = QtWidgets.QPushButton('Clear Completed')
        clear_btn.clicked.connect(self._clear_completed_tasks)
        task_header.addWidget(clear_btn)
        monitor_layout.addLayout(task_header)

        self._task_table = QtWidgets.QTableWidget(0, 5)
        self._task_table.setHorizontalHeaderLabels(
            ['Shot', 'Layer', 'Frames', 'GPU', 'Status'])
        self._task_table.horizontalHeader().setStretchLastSection(True)
        self._task_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._task_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._task_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        monitor_layout.addWidget(self._task_table)

        task_btns = QtWidgets.QHBoxLayout()
        self._cancel_selected_btn = QtWidgets.QPushButton('Cancel Selected')
        self._cancel_all_btn = QtWidgets.QPushButton('Cancel All')
        self._cancel_selected_btn.setEnabled(False)
        self._cancel_all_btn.setEnabled(False)
        task_btns.addWidget(self._cancel_selected_btn)
        task_btns.addWidget(self._cancel_all_btn)
        task_btns.addStretch()
        monitor_layout.addLayout(task_btns)

        self._tab_widget.addTab(monitor_widget, 'Monitor')

        # ---- Configure tab ----
        config_widget = QtWidgets.QWidget()
        config_layout = QtWidgets.QVBoxLayout(config_widget)
        config_layout.setContentsMargins(4, 4, 4, 4)

        middle = QtWidgets.QHBoxLayout()

        # Shot list
        shot_group = QtWidgets.QGroupBox('Shot List')
        shot_inner = QtWidgets.QVBoxLayout(shot_group)
        self._shot_table = QtWidgets.QTableWidget(0, 2)
        self._shot_table.setHorizontalHeaderLabels(['Shot', 'Frame Range'])
        self._shot_table.horizontalHeader().setStretchLastSection(False)
        self._shot_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self._shot_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        self._shot_table.setColumnWidth(1, 80)
        self._shot_table.setMinimumWidth(300)
        shot_inner.addWidget(self._shot_table)

        shot_btn_row = QtWidgets.QHBoxLayout()
        self._add_shot_btn = QtWidgets.QPushButton('Add')
        self._remove_shot_btn = QtWidgets.QPushButton('Remove')
        self._select_all_btn = QtWidgets.QPushButton('Select All')
        shot_btn_row.addWidget(self._add_shot_btn)
        shot_btn_row.addWidget(self._remove_shot_btn)
        shot_btn_row.addWidget(self._select_all_btn)
        shot_inner.addLayout(shot_btn_row)
        middle.addWidget(shot_group)

        # Render layers
        layer_group = QtWidgets.QGroupBox('Render Layers')
        layer_inner = QtWidgets.QVBoxLayout(layer_group)
        self._layer_list = QtWidgets.QListWidget()
        self._layer_list.setMinimumWidth(160)
        layer_inner.addWidget(self._layer_list)
        middle.addWidget(layer_group)

        config_layout.addLayout(middle)

        # Start buttons
        start_row = QtWidgets.QHBoxLayout()
        self._dry_run_btn = QtWidgets.QPushButton('Dry Run')
        self._start_btn = QtWidgets.QPushButton('Start Render')
        start_row.addStretch()
        start_row.addWidget(self._dry_run_btn)
        start_row.addWidget(self._start_btn)
        config_layout.addLayout(start_row)

        self._tab_widget.addTab(config_widget, 'Configure')

    def _connect_signals(self):
        self._gpu_timer.timeout.connect(self._refresh_gpu_panel)
        self._add_shot_btn.clicked.connect(self._on_add_shot)
        self._remove_shot_btn.clicked.connect(self._on_remove_shot)
        self._select_all_btn.clicked.connect(self._shot_table.selectAll)
        self._start_btn.clicked.connect(self._on_start_render)
        self._dry_run_btn.clicked.connect(self._on_dry_run)
        self._cancel_selected_btn.clicked.connect(self._on_cancel_selected)
        self._cancel_all_btn.clicked.connect(self._on_cancel_all)
        self.progress_updated.connect(self._on_progress_updated)

    # ------------------------------------------------------------------
    # GPU panel
    # ------------------------------------------------------------------

    def _refresh_gpu_panel(self):
        try:
            from core.batch.gpu_inventory import detect_gpus
            gpus = detect_gpus()
        except Exception as exc:
            logger.warning("GPU refresh failed: %s", exc)
            gpus = []

        reserved = self._settings.get('reserve_gpus', 1)
        self._gpu_table.setRowCount(len(gpus))

        for row, gpu in enumerate(gpus):
            is_reserved = row < reserved
            items = [
                str(gpu.index),
                gpu.name,
                '%d MB' % gpu.vram_total_mb,
                '%d%%' % gpu.util_pct,
                'Reserved' if is_reserved else 'Available',
            ]
            for col, text in enumerate(items):
                item = QtWidgets.QTableWidgetItem(text)
                if is_reserved:
                    item.setForeground(QtGui.QColor(150, 150, 150))
                self._gpu_table.setItem(row, col, item)

    # ------------------------------------------------------------------
    # Configure tab -- shot list
    # ------------------------------------------------------------------

    def _add_shot_row(self, ep, seq, shot, frame_range=None):
        """Add one row to the Configure shot list."""
        shot_id = '%s_%s_%s' % (ep, seq, shot)
        row = self._shot_table.rowCount()
        self._shot_table.insertRow(row)

        chk = QtWidgets.QTableWidgetItem(shot_id)
        chk.setFlags(chk.flags() | QtCore.Qt.ItemIsUserCheckable)
        chk.setCheckState(QtCore.Qt.Checked)
        chk.setData(QtCore.Qt.UserRole, (ep, seq, shot))
        self._shot_table.setItem(row, 0, chk)

        if frame_range is None and MAYA_AVAILABLE:
            try:
                from core.nodes.wrappers import CTXShotNode
                sn = CTXShotNode.find_by_code(ep, seq, shot)
                if sn:
                    start, end = sn.get_frame_range()
                    frame_range = '%d-%d' % (start, end)
            except Exception:
                pass
        fr_item = QtWidgets.QTableWidgetItem(frame_range or '----')
        fr_item.setTextAlignment(QtCore.Qt.AlignCenter)
        self._shot_table.setItem(row, 1, fr_item)

    def _get_shot_ids_in_list(self):
        """Return set of shot_id strings currently in the Configure shot list."""
        ids = set()
        for row in range(self._shot_table.rowCount()):
            item = self._shot_table.item(row, 0)
            if item:
                ids.add(item.text())
        return ids

    def _on_add_shot(self):
        existing = self._get_shot_ids_in_list()
        dlg = AddShotDialog(existing_shot_ids=existing, parent=self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            for shot_dict in dlg.get_selected():
                self._add_shot_row(
                    shot_dict['ep'], shot_dict['seq'], shot_dict['shot'],
                    frame_range=shot_dict.get('frame_range'))

    def _on_remove_shot(self):
        rows = sorted(
            set(idx.row() for idx in self._shot_table.selectedIndexes()),
            reverse=True)
        for row in rows:
            self._shot_table.removeRow(row)

    # ------------------------------------------------------------------
    # Configure tab -- layer list
    # ------------------------------------------------------------------

    def _populate_layer_list(self):
        self._layer_list.clear()
        try:
            from core.batch.render_setup_manager import RenderSetupManager
            mgr = RenderSetupManager()
            layers = mgr.get_all_layers()
            if not layers:
                item = QtWidgets.QListWidgetItem('defaultRenderLayer')
                item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
                item.setCheckState(QtCore.Qt.Checked)
                self._layer_list.addItem(item)
                return
            for layer in layers:
                item = QtWidgets.QListWidgetItem(layer.name)
                item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
                item.setCheckState(
                    QtCore.Qt.Checked if layer.renderable else QtCore.Qt.Unchecked)
                if not layer.renderable:
                    item.setForeground(QtGui.QColor(150, 150, 150))
                self._layer_list.addItem(item)
        except Exception as exc:
            logger.warning("Failed to populate layer list: %s", exc)

    def _get_checked_layers(self):
        layers = []
        for i in range(self._layer_list.count()):
            item = self._layer_list.item(i)
            if item and item.checkState() == QtCore.Qt.Checked:
                layers.append(item.text())
        return layers

    # ------------------------------------------------------------------
    # Configure tab -- start / dry run
    # ------------------------------------------------------------------

    def _on_start_render(self):
        shots = self._get_checked_shots()
        if not shots:
            QtWidgets.QMessageBox.warning(self, 'Batch Render', 'No shots selected.')
            return
        self._launch_render(shots, dry_run=False)

    def _on_dry_run(self):
        shots = self._get_checked_shots()
        if not shots:
            QtWidgets.QMessageBox.warning(self, 'Batch Render', 'No shots selected.')
            return
        self._launch_render(shots, dry_run=True)

    def _get_checked_shots(self):
        shots = []
        for row in range(self._shot_table.rowCount()):
            item = self._shot_table.item(row, 0)
            if item and item.checkState() == QtCore.Qt.Checked:
                data = item.data(QtCore.Qt.UserRole)
                if data:
                    ep, seq, shot = data
                    shots.append({'ep': ep, 'seq': seq, 'shot': shot})
        return shots

    def _launch_render(self, shots, dry_run=False):
        """Build jobs for shots and start render thread."""
        render_layers = self._get_checked_layers() or None
        auto_frame = self._settings.get('auto_frame', True)
        start_frame = None if auto_frame else self._settings.get('start_frame')
        end_frame   = None if auto_frame else self._settings.get('end_frame')
        reserved    = self._settings.get('reserve_gpus', 1)

        self._append_tasks_to_monitor(shots, render_layers)
        self._tab_widget.setCurrentIndex(0)  # switch to Monitor
        self._cancel_selected_btn.setEnabled(True)
        self._cancel_all_btn.setEnabled(True)
        self._cancelled = False

        def run():
            try:
                from tools.pipeline_api import PipelineAPI
                api = PipelineAPI()
                api.batch_render(
                    shots=shots,
                    render_layers=render_layers,
                    start_frame=start_frame,
                    end_frame=end_frame,
                    on_progress=self._on_progress,
                    dry_run=dry_run,
                    reserved_gpus=reserved,
                )
            except Exception as exc:
                logger.exception("Batch render thread failed: %s", exc)
            finally:
                QtCore.QMetaObject.invokeMethod(
                    self, '_on_render_finished', QtCore.Qt.QueuedConnection)

        self._render_thread = threading.Thread(target=run, daemon=True)
        self._render_thread.start()

    # ------------------------------------------------------------------
    # Quick Render entry point (called from Multishot Manager)
    # ------------------------------------------------------------------

    def queue_quick_render_jobs(self, jobs_config):
        """Add pre-built single-frame jobs and start render immediately.

        Called by MainWindow._on_quick_render(). Each item in jobs_config
        is a dict with keys: ep, seq, shot, start_frame, end_frame,
        render_layers, label.

        Args:
            jobs_config (list[dict]): Job specifications.
        """
        if not jobs_config:
            return

        self._tab_widget.setCurrentIndex(0)  # Monitor tab
        self._cancel_selected_btn.setEnabled(True)
        self._cancel_all_btn.setEnabled(True)
        self._cancelled = False

        # Append rows to task table
        for jc in jobs_config:
            shot_id = '%s_%s_%s' % (jc['ep'], jc['seq'], jc['shot'])
            layers = jc.get('render_layers') or ['defaultRenderLayer']
            for layer in layers:
                row = self._task_table.rowCount()
                self._task_table.insertRow(row)
                frame_str = str(jc.get('start_frame', '-'))
                self._task_table.setItem(row, 0, QtWidgets.QTableWidgetItem(shot_id))
                self._task_table.setItem(row, 1, QtWidgets.QTableWidgetItem(layer))
                self._task_table.setItem(row, 2, QtWidgets.QTableWidgetItem(frame_str))
                self._task_table.setItem(row, 3, QtWidgets.QTableWidgetItem('-'))
                status_item = QtWidgets.QTableWidgetItem('Queued')
                status_item.setForeground(QtGui.QColor('#F57C00'))
                self._task_table.setItem(row, 4, status_item)

        reserved = self._settings.get('reserve_gpus', 1)

        def run():
            try:
                from tools.pipeline_api import PipelineAPI
                api = PipelineAPI()
                for jc in jobs_config:
                    if self._cancelled:
                        break
                    api.batch_render(
                        shots=[{'ep': jc['ep'], 'seq': jc['seq'], 'shot': jc['shot']}],
                        render_layers=jc.get('render_layers'),
                        start_frame=jc.get('start_frame'),
                        end_frame=jc.get('end_frame'),
                        on_progress=self._on_progress,
                        dry_run=False,
                        reserved_gpus=reserved,
                    )
            except Exception as exc:
                logger.exception("Quick render thread failed: %s", exc)
            finally:
                QtCore.QMetaObject.invokeMethod(
                    self, '_on_render_finished', QtCore.Qt.QueuedConnection)

        self._render_thread = threading.Thread(target=run, daemon=True)
        self._render_thread.start()

    # ------------------------------------------------------------------
    # Monitor tab -- task management
    # ------------------------------------------------------------------

    def _append_tasks_to_monitor(self, shots, render_layers):
        """Append queued rows to the task table."""
        layers = render_layers or ['(all renderable)']
        for shot in shots:
            shot_id = '%s_%s_%s' % (shot['ep'], shot['seq'], shot['shot'])
            for layer in layers:
                row = self._task_table.rowCount()
                self._task_table.insertRow(row)
                self._task_table.setItem(row, 0, QtWidgets.QTableWidgetItem(shot_id))
                self._task_table.setItem(row, 1, QtWidgets.QTableWidgetItem(layer))
                self._task_table.setItem(row, 2, QtWidgets.QTableWidgetItem('-'))
                self._task_table.setItem(row, 3, QtWidgets.QTableWidgetItem('-'))
                status_item = QtWidgets.QTableWidgetItem('Queued')
                status_item.setForeground(QtGui.QColor('#F57C00'))
                self._task_table.setItem(row, 4, status_item)

    def _clear_completed_tasks(self):
        """Remove Done and Failed rows from the task table."""
        done_statuses = {'done', 'failed', 'cancelled', 'complete'}
        rows_to_remove = []
        for row in range(self._task_table.rowCount()):
            status_item = self._task_table.item(row, 4)
            if status_item:
                text = status_item.text().lower()
                if any(s in text for s in done_statuses):
                    rows_to_remove.append(row)
        for row in reversed(rows_to_remove):
            self._task_table.removeRow(row)

    def _on_cancel_selected(self):
        self._cancelled = True
        rows = set(idx.row() for idx in self._task_table.selectedIndexes())
        for row in rows:
            status_item = self._task_table.item(row, 4)
            if status_item and 'queued' in status_item.text().lower():
                status_item.setText('Cancelled')
                status_item.setForeground(QtGui.QColor(150, 150, 150))

    def _on_cancel_all(self):
        self._cancelled = True
        for row in range(self._task_table.rowCount()):
            status_item = self._task_table.item(row, 4)
            if status_item and status_item.text().lower() in ('queued',):
                status_item.setText('Cancelled')
                status_item.setForeground(QtGui.QColor(150, 150, 150))

    def _on_render_finished(self):
        """Called in main thread when render thread completes."""
        self._cancel_selected_btn.setEnabled(False)
        self._cancel_all_btn.setEnabled(False)
        logger.info("Render finished")

    # ------------------------------------------------------------------
    # Progress -- thread-safe via Signal
    # ------------------------------------------------------------------

    def _on_progress(self, job, layer, status, message):
        """Called from render thread. Emits signal for main-thread update."""
        self.progress_updated.emit(job, str(layer or ''), str(status), str(message))

    def _on_progress_updated(self, job, layer, status, message):
        """Called in Qt main thread. Finds matching task row and updates status."""
        shot_id = job.shot_id if hasattr(job, 'shot_id') else str(job)
        status_lower = status.lower()

        if status_lower in ('rendering', 'queued'):
            color = QtGui.QColor('#F57C00')
        elif status_lower == 'done' or 'complete' in status_lower:
            color = QtGui.QColor('#2E7D32')
        elif status_lower == 'failed':
            color = QtGui.QColor('#D32F2F')
        else:
            color = None

        for row in range(self._task_table.rowCount()):
            row_shot = self._task_table.item(row, 0)
            row_layer = self._task_table.item(row, 1)
            if not row_shot or row_shot.text() != shot_id:
                continue
            if layer and row_layer and row_layer.text() not in (layer, '(all renderable)', '-'):
                continue

            # GPU
            if hasattr(job, 'gpu_index') and job.gpu_index is not None:
                gpu_item = self._task_table.item(row, 3)
                if gpu_item:
                    gpu_item.setText(str(job.gpu_index))

            # Status
            status_item = self._task_table.item(row, 4)
            if status_item:
                display = status
                if message and message not in ('Started', 'Complete', status):
                    display = '%s: %s' % (status, message)
                status_item.setText(display)
                if color:
                    status_item.setForeground(color)
            break

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _open_settings(self):
        dlg = RenderSettingsDialog(self._settings, parent=self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self._settings = dlg.get_settings()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        self._gpu_timer.stop()
        super(BatchRenderDialog, self).closeEvent(event)
