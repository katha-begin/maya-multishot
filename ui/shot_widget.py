# -*- coding: utf-8 -*-
"""Shot widget for Context Variables Pipeline.

This widget displays a list of shots with radio buttons for selection.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

try:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtCore import Signal
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtCore import Signal

import logging

logger = logging.getLogger(__name__)


class ShotWidget(QtWidgets.QWidget):
    """Widget for displaying and selecting shots."""
    
    # Signal emitted when shot selection changes
    shot_selected = Signal(str)  # shot_code
    
    def __init__(self, parent=None):
        """Initialize shot widget.
        
        Args:
            parent (QWidget, optional): Parent widget
        """
        super(ShotWidget, self).__init__(parent)
        
        self._shots_data = []
        self._button_group = QtWidgets.QButtonGroup(self)
        self._button_group.setExclusive(True)
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the user interface."""
        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        
        # Header with title and add button
        header_layout = QtWidgets.QHBoxLayout()
        
        title_label = QtWidgets.QLabel("SHOTS IN SCENE")
        title_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.add_shot_btn = QtWidgets.QPushButton("+ Add Shot")
        self.add_shot_btn.setMaximumWidth(100)
        header_layout.addWidget(self.add_shot_btn)
        
        main_layout.addLayout(header_layout)
        
        # Shot list
        self.shot_list = QtWidgets.QListWidget()
        self.shot_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.shot_list.setMinimumHeight(150)
        main_layout.addWidget(self.shot_list)
    
    def _connect_signals(self):
        """Connect widget signals."""
        self._button_group.buttonClicked.connect(self._on_shot_radio_clicked)
        self.add_shot_btn.clicked.connect(self._on_add_shot_clicked)
    
    def load_shots(self, shots_data):
        """Load shots from data.
        
        Args:
            shots_data (list): List of shot dicts with keys: shot_code, ep, seq, path, asset_count
        """
        self._shots_data = shots_data
        self.shot_list.clear()
        
        # Remove all buttons from button group
        for button in self._button_group.buttons():
            self._button_group.removeButton(button)
        
        # Add shots to list
        for shot_data in shots_data:
            self._add_shot_item(shot_data)
        
        # Select first shot by default
        if shots_data:
            first_button = self._button_group.buttons()[0]
            first_button.setChecked(True)
            self.shot_selected.emit(shots_data[0]['shot_code'])
    
    def _add_shot_item(self, shot_data):
        """Add a shot item to the list.
        
        Args:
            shot_data (dict): Shot data dict
        """
        # Create list item
        item = QtWidgets.QListWidgetItem(self.shot_list)
        item.setSizeHint(QtCore.QSize(0, 40))
        
        # Create custom widget for item
        item_widget = QtWidgets.QWidget()
        item_layout = QtWidgets.QHBoxLayout(item_widget)
        item_layout.setContentsMargins(5, 2, 5, 2)
        item_layout.setSpacing(10)
        
        # Radio button
        radio_btn = QtWidgets.QRadioButton()
        radio_btn.setProperty('shot_code', shot_data['shot_code'])
        self._button_group.addButton(radio_btn)
        item_layout.addWidget(radio_btn)
        
        # Shot code label
        shot_label = QtWidgets.QLabel(shot_data['shot_code'])
        shot_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        shot_label.setMinimumWidth(80)
        item_layout.addWidget(shot_label)
        
        # Asset count label
        asset_count_label = QtWidgets.QLabel("{} assets".format(shot_data['asset_count']))
        asset_count_label.setStyleSheet("color: #888;")
        asset_count_label.setMinimumWidth(80)
        item_layout.addWidget(asset_count_label)
        
        # Frame range label (placeholder)
        frame_range_label = QtWidgets.QLabel("[1001-1050]")
        frame_range_label.setStyleSheet("color: #888;")
        item_layout.addWidget(frame_range_label)
        
        item_layout.addStretch()
        
        # Set widget for item
        self.shot_list.setItemWidget(item, item_widget)
    
    def _on_shot_radio_clicked(self, button):
        """Handle shot radio button click.
        
        Args:
            button (QRadioButton): Clicked button
        """
        shot_code = button.property('shot_code')
        logger.info("Shot selected: {}".format(shot_code))
        self.shot_selected.emit(shot_code)
    
    def _on_add_shot_clicked(self):
        """Handle add shot button click."""
        QtWidgets.QMessageBox.information(
            self,
            "Not Implemented",
            "Add Shot functionality will be implemented in Phase 4B (CTX Integration)."
        )
    
    def get_selected_shot(self):
        """Get currently selected shot code.
        
        Returns:
            str: Selected shot code or None
        """
        checked_button = self._button_group.checkedButton()
        if checked_button:
            return checked_button.property('shot_code')
        return None

