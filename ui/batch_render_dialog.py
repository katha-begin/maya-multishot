# -*- coding: utf-8 -*-
"""Batch Render dialog.

Non-modal dialog for configuring and monitoring multi-shot batch renders.
Launched from the Context Manager menu.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

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


class BatchRenderDialog(BaseDialog):
    """Non-modal dialog for batch render configuration and monitoring.

    Shows GPU status, shot queue, render layer selection, frame range controls,
    and a live progress table.
    """

    _instance = None

    # Signals (thread-safe progress updates)
    progress_updated = Signal(object, str, str, str)  # job, layer, status, msg

    def __init__(self, parent=None):
        # Initialise member variables before super().__init__() because
        # BaseDialog.__init__() calls _setup_ui() and _connect_signals()
        # which reference these attributes.
        self._render_thread = None
        self._cancelled = False
        self._gpu_timer = None  # Created in _setup_ui after super()

        super(BatchRenderDialog, self).__init__(parent=parent)

        self.setWindowTitle('Batch Render')
        self.setModal(False)
        self.resize(820, 700)

        # Post-setup initialisation (requires widgets to exist)
        self._populate_shot_table()
        self._populate_layer_list()
        self._refresh_gpu_panel()

        # Start GPU refresh timer (every 5 seconds)
        self._gpu_timer.start(5000)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        """Build all widgets."""
        # QTimer must be created after QApplication exists; safe here.
        self._gpu_timer = QtCore.QTimer(self)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # GPU Status group
        gpu_group = QtWidgets.QGroupBox('GPU Status')
        gpu_layout = QtWidgets.QVBoxLayout(gpu_group)

        self._gpu_table = QtWidgets.QTableWidget(0, 5)
        self._gpu_table.setHorizontalHeaderLabels(
            ['GPU', 'Name', 'VRAM', 'Utilization', 'Status'])
        self._gpu_table.horizontalHeader().setStretchLastSection(True)
        self._gpu_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self._gpu_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._gpu_table.setFixedHeight(120)
        gpu_layout.addWidget(self._gpu_table)

        reserve_row = QtWidgets.QHBoxLayout()
        reserve_row.addStretch()
        reserve_row.addWidget(QtWidgets.QLabel('Reserve for interactive:'))
        self._reserve_spin = QtWidgets.QSpinBox()
        self._reserve_spin.setRange(0, 8)
        self._reserve_spin.setValue(1)
        self._reserve_spin.setFixedWidth(60)
        reserve_row.addWidget(self._reserve_spin)
        gpu_layout.addLayout(reserve_row)
        main_layout.addWidget(gpu_group)

        # Middle row: shot queue + render layers
        middle_layout = QtWidgets.QHBoxLayout()

        # Shot Queue
        shot_group = QtWidgets.QGroupBox('Shot Queue')
        shot_layout = QtWidgets.QVBoxLayout(shot_group)
        self._shot_table = QtWidgets.QTableWidget(0, 2)
        self._shot_table.setHorizontalHeaderLabels(['Shot', 'Frame Range'])
        self._shot_table.horizontalHeader().setStretchLastSection(True)
        self._shot_table.setMinimumWidth(320)
        shot_layout.addWidget(self._shot_table)

        shot_btn_row = QtWidgets.QHBoxLayout()
        self._add_shot_btn = QtWidgets.QPushButton('Add Shot')
        self._remove_shot_btn = QtWidgets.QPushButton('Remove')
        self._select_all_btn = QtWidgets.QPushButton('Select All')
        shot_btn_row.addWidget(self._add_shot_btn)
        shot_btn_row.addWidget(self._remove_shot_btn)
        shot_btn_row.addWidget(self._select_all_btn)
        shot_layout.addLayout(shot_btn_row)
        middle_layout.addWidget(shot_group)

        # Render Layers
        layer_group = QtWidgets.QGroupBox('Render Layers')
        layer_layout = QtWidgets.QVBoxLayout(layer_group)
        self._layer_list = QtWidgets.QListWidget()
        self._layer_list.setMinimumWidth(180)
        layer_layout.addWidget(self._layer_list)
        middle_layout.addWidget(layer_group)

        main_layout.addLayout(middle_layout)

        # Frame range + temp scene settings
        settings_group = QtWidgets.QGroupBox('Settings')
        settings_layout = QtWidgets.QFormLayout(settings_group)

        frame_row = QtWidgets.QHBoxLayout()
        self._auto_frame_check = QtWidgets.QCheckBox('Auto from shot')
        self._auto_frame_check.setChecked(True)
        self._start_frame_spin = QtWidgets.QSpinBox()
        self._start_frame_spin.setRange(0, 99999)
        self._start_frame_spin.setValue(1001)
        self._start_frame_spin.setEnabled(False)
        self._end_frame_spin = QtWidgets.QSpinBox()
        self._end_frame_spin.setRange(0, 99999)
        self._end_frame_spin.setValue(1100)
        self._end_frame_spin.setEnabled(False)
        frame_row.addWidget(self._auto_frame_check)
        frame_row.addWidget(QtWidgets.QLabel('Start'))
        frame_row.addWidget(self._start_frame_spin)
        frame_row.addWidget(QtWidgets.QLabel('End'))
        frame_row.addWidget(self._end_frame_spin)
        frame_row.addStretch()
        settings_layout.addRow('Frame Range:', frame_row)

        temp_row = QtWidgets.QHBoxLayout()
        self._temp_max_spin = QtWidgets.QSpinBox()
        self._temp_max_spin.setRange(0, 100)
        self._temp_max_spin.setValue(5)
        self._temp_max_spin.setFixedWidth(60)
        self._temp_dir_edit = QtWidgets.QLineEdit()
        self._temp_dir_edit.setPlaceholderText('(auto)')
        self._temp_dir_browse_btn = QtWidgets.QPushButton('Browse')
        temp_row.addWidget(QtWidgets.QLabel('Max count'))
        temp_row.addWidget(self._temp_max_spin)
        temp_row.addWidget(self._temp_dir_edit)
        temp_row.addWidget(self._temp_dir_browse_btn)
        settings_layout.addRow('Temp Scenes:', temp_row)

        main_layout.addWidget(settings_group)

        # Progress table
        progress_group = QtWidgets.QGroupBox('Progress')
        progress_layout = QtWidgets.QVBoxLayout(progress_group)
        self._progress_table = QtWidgets.QTableWidget(0, 5)
        self._progress_table.setHorizontalHeaderLabels(
            ['Shot', 'Layer', 'GPU', 'Frames', 'Status'])
        self._progress_table.horizontalHeader().setStretchLastSection(True)
        self._progress_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._progress_table.setFixedHeight(150)
        progress_layout.addWidget(self._progress_table)
        main_layout.addWidget(progress_group)

        # Action buttons
        btn_row = QtWidgets.QHBoxLayout()
        self._dry_run_btn = QtWidgets.QPushButton('Dry Run')
        self._start_btn = QtWidgets.QPushButton('Start Render')
        self._pause_btn = QtWidgets.QPushButton('Pause')
        self._cancel_btn = QtWidgets.QPushButton('Cancel')
        self._pause_btn.setEnabled(False)
        self._cancel_btn.setEnabled(False)
        btn_row.addWidget(self._dry_run_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._start_btn)
        btn_row.addWidget(self._pause_btn)
        btn_row.addWidget(self._cancel_btn)
        main_layout.addLayout(btn_row)

    def _connect_signals(self):
        """Connect all signals/slots."""
        self._gpu_timer.timeout.connect(self._refresh_gpu_panel)
        self._auto_frame_check.toggled.connect(self._on_auto_frame_toggled)
        self._start_btn.clicked.connect(self._on_start_render)
        self._dry_run_btn.clicked.connect(self._on_dry_run)
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._add_shot_btn.clicked.connect(self._on_add_shot)
        self._remove_shot_btn.clicked.connect(self._on_remove_shot)
        self._select_all_btn.clicked.connect(self._shot_table.selectAll)
        self._temp_dir_browse_btn.clicked.connect(self._on_browse_temp_dir)
        self.progress_updated.connect(self._on_progress_updated)

    # ------------------------------------------------------------------
    # GPU panel
    # ------------------------------------------------------------------

    def _refresh_gpu_panel(self):
        """Refresh GPU status table. Called by QTimer every 5s."""
        try:
            from core.batch.gpu_inventory import detect_gpus
            gpus = detect_gpus()
        except Exception as exc:
            logger.warning("GPU refresh failed: %s", exc)
            gpus = []

        reserved = self._reserve_spin.value()
        self._gpu_table.setRowCount(len(gpus))

        for row, gpu in enumerate(gpus):
            is_reserved = row < reserved
            status_text = 'Reserved' if is_reserved else 'Available'

            items = [
                str(gpu.index),
                gpu.name,
                '%d MB' % gpu.vram_total_mb,
                '%d%%' % gpu.util_pct,
                status_text,
            ]
            for col, text in enumerate(items):
                item = QtWidgets.QTableWidgetItem(text)
                if is_reserved:
                    item.setForeground(QtGui.QColor(150, 150, 150))
                self._gpu_table.setItem(row, col, item)

    # ------------------------------------------------------------------
    # Shot table
    # ------------------------------------------------------------------

    def _populate_shot_table(self):
        """Populate shot table from CTXShotNode.list_all()."""
        if not MAYA_AVAILABLE:
            return
        try:
            from core.nodes.wrappers import CTXShotNode
            shots = CTXShotNode.list_all()
            self._shot_table.setRowCount(len(shots))
            for row, shot_node in enumerate(shots):
                shot_id = '%s_%s_%s' % (shot_node.ep, shot_node.seq, shot_node.shot)

                # Checkbox column
                chk_item = QtWidgets.QTableWidgetItem(shot_id)
                chk_item.setFlags(chk_item.flags() | QtCore.Qt.ItemIsUserCheckable)
                chk_item.setCheckState(QtCore.Qt.Checked)
                self._shot_table.setItem(row, 0, chk_item)

                # Frame range
                try:
                    start, end = shot_node.get_frame_range()
                    range_text = '%d-%d' % (start, end)
                except Exception:
                    range_text = '----'
                self._shot_table.setItem(row, 1, QtWidgets.QTableWidgetItem(range_text))
        except Exception as exc:
            logger.warning("Failed to populate shot table: %s", exc)

    # ------------------------------------------------------------------
    # Layer list
    # ------------------------------------------------------------------

    def _populate_layer_list(self):
        """Populate render layer list from RenderSetupManager."""
        self._layer_list.clear()
        try:
            from core.batch.render_setup_manager import RenderSetupManager
            mgr = RenderSetupManager()
            layers = mgr.get_all_layers()
            if not layers:
                # Add default layer as fallback
                item = QtWidgets.QListWidgetItem('defaultRenderLayer')
                item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
                item.setCheckState(QtCore.Qt.Checked)
                self._layer_list.addItem(item)
                return

            for layer in layers:
                item = QtWidgets.QListWidgetItem(layer.name)
                item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
                # Check renderable layers by default
                item.setCheckState(
                    QtCore.Qt.Checked if layer.renderable else QtCore.Qt.Unchecked)
                if not layer.renderable:
                    item.setForeground(QtGui.QColor(150, 150, 150))
                self._layer_list.addItem(item)
        except Exception as exc:
            logger.warning("Failed to populate layer list: %s", exc)

    # ------------------------------------------------------------------
    # Frame range toggle
    # ------------------------------------------------------------------

    def _on_auto_frame_toggled(self, checked):
        """Enable/disable manual frame range inputs."""
        self._start_frame_spin.setEnabled(not checked)
        self._end_frame_spin.setEnabled(not checked)

    # ------------------------------------------------------------------
    # Render actions
    # ------------------------------------------------------------------

    def _on_start_render(self):
        """Build job list and call PipelineAPI.batch_render() in background thread."""
        shots = self._get_checked_shots()
        if not shots:
            QtWidgets.QMessageBox.warning(self, 'Batch Render', 'No shots selected.')
            return
        self._start_render_internal(shots, dry_run=False)

    def _on_dry_run(self):
        """Dry run -- prepare scenes only, no render."""
        shots = self._get_checked_shots()
        if not shots:
            QtWidgets.QMessageBox.warning(self, 'Batch Render', 'No shots selected.')
            return
        self._start_render_internal(shots, dry_run=True)

    def _start_render_internal(self, shots, dry_run=False):
        """Start render in background thread."""
        render_layers = self._get_checked_layers()
        start_frame = None if self._auto_frame_check.isChecked() else self._start_frame_spin.value()
        end_frame   = None if self._auto_frame_check.isChecked() else self._end_frame_spin.value()
        reserved    = self._reserve_spin.value()

        # Populate progress table
        self._progress_table.setRowCount(0)
        for shot in shots:
            shot_id = '%s_%s_%s' % (shot['ep'], shot['seq'], shot['shot'])
            for layer in (render_layers or ['(all renderable)']):
                row = self._progress_table.rowCount()
                self._progress_table.insertRow(row)
                self._progress_table.setItem(row, 0, QtWidgets.QTableWidgetItem(shot_id))
                self._progress_table.setItem(row, 1, QtWidgets.QTableWidgetItem(layer))
                self._progress_table.setItem(row, 2, QtWidgets.QTableWidgetItem('-'))
                self._progress_table.setItem(row, 3, QtWidgets.QTableWidgetItem('-'))
                self._progress_table.setItem(row, 4, QtWidgets.QTableWidgetItem('Queued'))

        self._start_btn.setEnabled(False)
        self._dry_run_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._cancelled = False

        def run():
            try:
                from tools.pipeline_api import PipelineAPI
                api = PipelineAPI()
                api.batch_render(
                    shots=shots,
                    render_layers=render_layers or None,
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

    def _on_cancel(self):
        """Set cancel flag. JobDispatcher does not support mid-job cancel yet."""
        self._cancelled = True
        self._cancel_btn.setEnabled(False)
        logger.info("Cancel requested")

    def _on_render_finished(self):
        """Called in main thread when render thread completes."""
        self._start_btn.setEnabled(True)
        self._dry_run_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._pause_btn.setEnabled(False)
        logger.info("Render finished")

    # ------------------------------------------------------------------
    # Progress (thread-safe via signal)
    # ------------------------------------------------------------------

    def _on_progress(self, job, layer, status, message):
        """Called from render thread. Emits signal for main-thread update."""
        layer_str = layer or ''
        status_str = str(status)
        message_str = str(message)
        self.progress_updated.emit(job, layer_str, status_str, message_str)

    def _on_progress_updated(self, job, layer, status, message):
        """Called in Qt main thread. Updates progress table row."""
        shot_id = job.shot_id if hasattr(job, 'shot_id') else str(job)
        for row in range(self._progress_table.rowCount()):
            row_shot = self._progress_table.item(row, 0)
            row_layer = self._progress_table.item(row, 1)
            if row_shot and row_shot.text() == shot_id:
                if layer and row_layer and row_layer.text() not in (layer, '(all renderable)'):
                    continue
                # Update GPU
                if hasattr(job, 'gpu_index') and job.gpu_index is not None:
                    gpu_item = self._progress_table.item(row, 2)
                    if gpu_item:
                        gpu_item.setText(str(job.gpu_index))
                # Update status
                status_item = self._progress_table.item(row, 4)
                if status_item:
                    status_item.setText('%s: %s' % (status, message) if message else status)
                break

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_checked_shots(self):
        """Return list of dicts for checked shots in the shot table."""
        shots = []
        for row in range(self._shot_table.rowCount()):
            item = self._shot_table.item(row, 0)
            if item and item.checkState() == QtCore.Qt.Checked:
                parts = item.text().split('_', 2)
                if len(parts) == 3:
                    shots.append({'ep': parts[0], 'seq': parts[1], 'shot': parts[2]})
        return shots

    def _get_checked_layers(self):
        """Return list of checked render layer names."""
        layers = []
        for i in range(self._layer_list.count()):
            item = self._layer_list.item(i)
            if item and item.checkState() == QtCore.Qt.Checked:
                layers.append(item.text())
        return layers

    def _on_add_shot(self):
        """Open simple input dialog to add a shot by ID."""
        text, ok = QtWidgets.QInputDialog.getText(
            self, 'Add Shot', 'Enter shot ID (ep_seq_shot):')
        if not ok or not text:
            return
        parts = text.strip().split('_', 2)
        if len(parts) != 3:
            QtWidgets.QMessageBox.warning(
                self, 'Add Shot', 'Invalid format. Expected: ep_seq_shot')
            return
        row = self._shot_table.rowCount()
        self._shot_table.insertRow(row)
        chk_item = QtWidgets.QTableWidgetItem(text.strip())
        chk_item.setFlags(chk_item.flags() | QtCore.Qt.ItemIsUserCheckable)
        chk_item.setCheckState(QtCore.Qt.Checked)
        self._shot_table.setItem(row, 0, chk_item)
        self._shot_table.setItem(row, 1, QtWidgets.QTableWidgetItem('----'))

    def _on_remove_shot(self):
        """Remove selected rows from shot table."""
        rows = sorted(set(idx.row() for idx in self._shot_table.selectedIndexes()),
                      reverse=True)
        for row in rows:
            self._shot_table.removeRow(row)

    def _on_browse_temp_dir(self):
        """Open directory browser for temp scene directory."""
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Select Temp Scene Directory', self._temp_dir_edit.text())
        if path:
            self._temp_dir_edit.setText(path)

    def closeEvent(self, event):
        """Stop GPU timer on close."""
        self._gpu_timer.stop()
        super(BatchRenderDialog, self).closeEvent(event)
