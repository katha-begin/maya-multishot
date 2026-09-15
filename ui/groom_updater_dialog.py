# -*- coding: utf-8 -*-
"""EGA Groom Updater -- list CFX groom standins and point them at the active shot.

Temporary tool for project EGA.  Set Shot already repoints grooms when the
project config enables ``cfx.repathOnShotSwitch``; this dialog shows where
each groom points, checks the frames the shot needs, and lets another publish
version be picked.  Logic lives in core/groom_updater.py.
"""

from __future__ import absolute_import, division, print_function

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui

from core import groom_updater
from core.logging_config import get_logger

logger = get_logger(__name__)

COL_CHECK, COL_GROOM, COL_STANDIN, COL_CURRENT, COL_VERSION, COL_FRAMES, COL_ACTION = range(7)
HEADERS = ['', 'Groom', 'Standin', 'Current', 'Version', 'Frames', 'Action']
WARN_COLOR = QtGui.QColor(230, 150, 60)


def _load_config():
    """The Multishot Manager's config when it is open, else the scene's."""
    try:
        from ui.main_window import MainWindow
        window = MainWindow._instance
        if window is not None and window._config is not None:
            return window._config
    except Exception:
        pass
    from config.config_resolver import resolve_config_path
    from config.project_config import ProjectConfig
    return ProjectConfig(resolve_config_path())


def _active_shot():
    from core.context import ContextManager
    return ContextManager().get_active_shot()


def _short(node):
    return (node or '').split('|')[-1]


class GroomUpdaterDialog(QtWidgets.QDialog):
    """Table of CFX groom standins with version pick and frame check."""

    _instance = None

    @classmethod
    def open_or_raise(cls, parent=None):
        """Show the dialog (refreshed), creating it on first use."""
        if cls._instance is not None:
            try:
                cls._instance.refresh()
                cls._instance.show()
                cls._instance.raise_()
                cls._instance.activateWindow()
                return cls._instance
            except RuntimeError:
                cls._instance = None  # Qt object already deleted
        dialog = cls(parent=parent)
        cls._instance = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        return dialog

    def __init__(self, parent=None, config_loader=None, shot_loader=None):
        super(GroomUpdaterDialog, self).__init__(parent)
        self._config_loader = config_loader or _load_config
        self._shot_loader = shot_loader or _active_shot
        self._config = None
        self._shot = None
        self._items = []

        self.setWindowTitle('EGA Groom Updater')
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self.resize(980, 320)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        self.shot_label = QtWidgets.QLabel()
        layout.addWidget(self.shot_label)

        self.table = QtWidgets.QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(22)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        header = self.table.horizontalHeader()
        for col in range(len(HEADERS)):
            header.setSectionResizeMode(col, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_FRAMES, QtWidgets.QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.summary_label = QtWidgets.QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(self.summary_label)

        buttons = QtWidgets.QHBoxLayout()
        self.refresh_btn = QtWidgets.QPushButton('Refresh')
        self.refresh_btn.clicked.connect(self.refresh)
        buttons.addWidget(self.refresh_btn)
        buttons.addStretch()
        self.apply_btn = QtWidgets.QPushButton('Apply to Checked')
        self.apply_btn.setToolTip(
            'Point checked grooms at the active shot using the chosen version; '
            'hide grooms the shot has no publish of.')
        self.apply_btn.clicked.connect(self._on_apply)
        buttons.addWidget(self.apply_btn)
        close_btn = QtWidgets.QPushButton('Close')
        close_btn.clicked.connect(self.close)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

    # ------------------------------------------------------------------
    # table
    # ------------------------------------------------------------------

    def refresh(self):
        """Re-read the active shot, the standins and the publish folders."""
        self.table.setRowCount(0)
        self._items = []
        self.apply_btn.setEnabled(False)
        self.summary_label.setText('')

        try:
            self._config = self._config_loader()
            self._shot = self._shot_loader()
        except Exception as exc:
            logger.exception('Groom Updater could not load the config or shot')
            self.shot_label.setText('Cannot load the project config: {}'.format(exc))
            return

        if self._shot is None:
            self.shot_label.setText(
                'No active shot. Click Set on a shot in Multishot Manager first.')
            return

        start, end = self._shot.get_frame_range()
        self.shot_label.setText('Active shot: <b>{}</b> &nbsp; frames {}-{}'.format(
            self._shot.get_shot_id(), int(start), int(end)))

        try:
            self._items = groom_updater.plan_grooms(self._config, self._shot)
        except Exception as exc:
            logger.exception('Groom scan failed')
            self.summary_label.setText('Groom scan failed: {}'.format(exc))
            return

        self.table.setRowCount(len(self._items))
        for row, item in enumerate(self._items):
            self._fill_row(row, item)

        if not self._items:
            self.summary_label.setText('No CFX groom standins in this scene.')
            return
        self.apply_btn.setEnabled(True)
        if not groom_updater.is_enabled(self._config):
            self.summary_label.setText(
                'This project does not repoint grooms on Set Shot; use Apply here.')

    def _fill_row(self, row, item):
        check = QtWidgets.QTableWidgetItem()
        check.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        check.setCheckState(QtCore.Qt.Checked)
        self.table.setItem(row, COL_CHECK, check)

        self._set_text(row, COL_GROOM, item['groom'])
        self._set_text(row, COL_STANDIN, _short(item['transform'] or item['shape']),
                       tooltip=item['shape'])
        self._set_text(row, COL_CURRENT, '{} {}'.format(
            item['current_shot'], item['current_version']), tooltip=item['current_path'])

        combo = QtWidgets.QComboBox()
        if item['versions']:
            for index, version in enumerate(item['versions']):
                combo.addItem(version + ('  (latest)' if index == 0 else ''), version)
            combo.setCurrentIndex(item['versions'].index(groom_updater.default_version(item)))
        else:
            combo.addItem('--', None)
            combo.setEnabled(False)
        combo.currentIndexChanged.connect(lambda _index, r=row: self._update_row(r))
        self.table.setCellWidget(row, COL_VERSION, combo)

        self._update_row(row)

    def _selected_version(self, row):
        combo = self.table.cellWidget(row, COL_VERSION)
        return combo.itemData(combo.currentIndex()) if combo is not None else None

    def _update_row(self, row):
        """Refresh the Frames and Action cells for the row's chosen version."""
        item = self._items[row]
        version = self._selected_version(row)
        action = groom_updater.get_action(item, version)

        if action == groom_updater.ACTION_UPDATE:
            action_text = 'update'
        elif action == groom_updater.ACTION_CURRENT:
            action_text = 'up to date'
        elif action == groom_updater.ACTION_NO_PUBLISH:
            action_text = 'hide: no publish in {}'.format(item['shot'])
        else:
            action_text = 'hide: duplicate of {}'.format(_short(item['duplicate_of']))

        frames_text, frames_tip, warn = '', '', False
        if action in (groom_updater.ACTION_UPDATE, groom_updater.ACTION_CURRENT):
            check = groom_updater.check_item_frames(item, version)
            problem = groom_updater.describe_frames(check)
            if problem:
                frames_text, warn = problem, True
                frames_tip = groom_updater.describe_frames(check, limit=None)
            else:
                frames_text = '{} frames OK'.format(check['count'])

        self._set_text(row, COL_FRAMES, frames_text, tooltip=frames_tip, warn=warn)
        self._set_text(row, COL_ACTION, action_text,
                       tooltip=groom_updater.target_path(item, version) or '')

    def _set_text(self, row, col, text, tooltip='', warn=False):
        cell = QtWidgets.QTableWidgetItem(text)
        cell.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
        if tooltip:
            cell.setToolTip(tooltip)
        if warn:
            cell.setForeground(WARN_COLOR)
        self.table.setItem(row, col, cell)

    # ------------------------------------------------------------------
    # apply
    # ------------------------------------------------------------------

    def _on_apply(self):
        counts = {}
        problems = []
        for row, item in enumerate(self._items):
            if self.table.item(row, COL_CHECK).checkState() != QtCore.Qt.Checked:
                continue
            version = self._selected_version(row)
            try:
                action = groom_updater.apply_item(item, version)
            except Exception as exc:
                logger.exception('Groom update failed for %s', item['shape'])
                problems.append('{}: update failed: {}'.format(item['groom'], exc))
                continue
            counts[action] = counts.get(action, 0) + 1
            if action in (groom_updater.ACTION_UPDATE, groom_updater.ACTION_CURRENT):
                problem = groom_updater.describe_frames(
                    groom_updater.check_item_frames(item, version))
                if problem:
                    problems.append('{}: {}'.format(item['groom'], problem))

        self.refresh()

        hidden = (counts.get(groom_updater.ACTION_NO_PUBLISH, 0) +
                  counts.get(groom_updater.ACTION_DUPLICATE, 0))
        text = '{} updated, {} already set, {} hidden.'.format(
            counts.get(groom_updater.ACTION_UPDATE, 0),
            counts.get(groom_updater.ACTION_CURRENT, 0), hidden)
        if problems:
            text += '\nCheck before rendering:\n' + '\n'.join(problems)
        logger.info('Groom Updater: %s', text.replace('\n', ' '))
        self.summary_label.setText(text)
