# -*- coding: utf-8 -*-
"""Real-time log console dialog for batch render output.

Tails the active render job's log file and displays it in a scrollable
read-only text area. Polling is driven by a 500ms QTimer.
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


class LogConsoleDialog(QtWidgets.QDialog):
    """Floating log console that tails a render log file in real time."""

    _instance = None

    @classmethod
    def get_or_create(cls, parent=None):
        """Return existing instance or create a new one."""
        if cls._instance is not None:
            try:
                _ = cls._instance.isVisible()  # raises if Qt object deleted
            except RuntimeError:
                cls._instance = None
        if cls._instance is None:
            cls._instance = cls(parent=parent)
        return cls._instance

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle('Render Log Console')
        self.setWindowFlags(
            QtCore.Qt.Tool | QtCore.Qt.WindowCloseButtonHint
        )
        self.resize(750, 420)

        self._log_path = None
        self._log_file_pos = 0

        self._setup_ui()

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._poll_log_file)
        self._timer.start()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Toolbar row
        toolbar = QtWidgets.QHBoxLayout()
        self._watching_label = QtWidgets.QLabel('Not watching any file.')
        self._watching_label.setStyleSheet('color: #888888; font-size: 10px;')
        toolbar.addWidget(self._watching_label)
        toolbar.addStretch()
        self._auto_scroll_cb = QtWidgets.QCheckBox('Auto-scroll')
        self._auto_scroll_cb.setChecked(True)
        toolbar.addWidget(self._auto_scroll_cb)
        self._clear_btn = QtWidgets.QPushButton('Clear')
        self._clear_btn.setFixedWidth(55)
        self._clear_btn.clicked.connect(self._on_clear)
        toolbar.addWidget(self._clear_btn)
        layout.addLayout(toolbar)

        # Text area
        self._text_edit = QtWidgets.QPlainTextEdit()
        self._text_edit.setReadOnly(True)
        font = QtGui.QFont('Courier New', 9)
        font.setStyleHint(QtGui.QFont.Monospace)
        self._text_edit.setFont(font)
        self._text_edit.setStyleSheet(
            'background-color: #1A1A1A; color: #CCCCCC;'
        )
        layout.addWidget(self._text_edit)

    def watch_file(self, path):
        """Start tailing a new log file. Resets position to 0."""
        if path == self._log_path:
            return
        self._log_path = path
        self._log_file_pos = 0
        self._watching_label.setText(os.path.basename(path) if path else '')
        self._text_edit.appendPlainText('--- %s ---' % (path or ''))
        self._scroll_to_bottom()

    def append_text(self, text):
        """Directly append text (for non-file messages)."""
        self._text_edit.appendPlainText(text)
        self._scroll_to_bottom()

    def _poll_log_file(self):
        """Read new bytes from the log file since last poll."""
        if not self._log_path:
            return
        try:
            if not os.path.exists(self._log_path):
                return
            with open(self._log_path, 'rb') as f:
                f.seek(self._log_file_pos)
                raw = f.read()
                self._log_file_pos = f.tell()
            if raw:
                text = raw.decode('utf-8', errors='replace').rstrip('\n')
                self._text_edit.appendPlainText(text)
                self._scroll_to_bottom()
        except Exception:
            pass

    def _scroll_to_bottom(self):
        if self._auto_scroll_cb.isChecked():
            sb = self._text_edit.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _on_clear(self):
        self._text_edit.clear()
        self._log_file_pos = 0

    def closeEvent(self, event):
        self._timer.stop()
        QtWidgets.QDialog.closeEvent(self, event)
