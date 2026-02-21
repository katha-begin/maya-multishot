# -*- coding: utf-8 -*-
"""Light Editor Panel - Detailed per-attribute editing with override controls.

Provides UI for:
- Per-attribute override fields
- Enable/disable checkboxes for each attribute
- Inherited value display
- Source gaffer display
- Apply/Revert/Capture buttons
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
from core.nodes.wrappers.light_context import CTXLightContextNode

logger = logging.getLogger(__name__)


class LightEditorPanel(QtWidgets.QDialog):
    """Panel for detailed light attribute editing."""
    
    def __init__(self, gaffer, light_context, parent=None):
        """Initialize light editor panel.
        
        Args:
            gaffer: CTXLightGafferNode instance
            light_context: CTXLightContextNode instance
            parent: Parent widget (optional)
        """
        super(LightEditorPanel, self).__init__(parent)
        
        # Make dialog non-modal
        self.setWindowModality(QtCore.Qt.NonModal)
        
        # Set window flags
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowMinimizeButtonHint |
            QtCore.Qt.WindowMaximizeButtonHint
        )
        
        self._gaffer = gaffer
        self._light_context = light_context
        self._light_name = light_context.get_light_name()
        
        self.setWindowTitle("Light Editor: {}".format(self._light_name))
        self.setMinimumSize(700, 600)
        
        # Attribute widgets storage
        self._attribute_widgets = {}  # {attr_name: {'override': widget, 'enable': widget, ...}}
        
        self._setup_ui()
        self._load_values()
    
    def _setup_ui(self):
        """Set up the user interface."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Title
        title_label = QtWidgets.QLabel("LIGHT EDITOR: {}".format(self._light_name))
        title_font = QtGui.QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)
        
        # Light info section
        info_layout = QtWidgets.QFormLayout()
        
        # Target light
        target_light = self._light_context.get_target_light()
        self._target_label = QtWidgets.QLabel(target_light if target_light else "Unknown")
        info_layout.addRow("Target Light:", self._target_label)
        
        # Light type
        if cmds and target_light and cmds.objExists(target_light):
            light_type = cmds.nodeType(target_light)
        else:
            light_type = "Unknown"
        self._type_label = QtWidgets.QLabel(light_type)
        info_layout.addRow("Light Type:", self._type_label)
        
        # Current gaffer
        gaffer_name = self._gaffer.get_gaffer_name()
        self._gaffer_label = QtWidgets.QLabel(gaffer_name)
        info_layout.addRow("Current Gaffer:", self._gaffer_label)
        
        # Inheritance chain
        chain = self._gaffer.build_chain()
        chain_names = [g.get_gaffer_name() for g in chain]
        chain_text = " → ".join(reversed(chain_names))
        self._chain_label = QtWidgets.QLabel(chain_text)
        self._chain_label.setStyleSheet("color: #888; font-style: italic;")
        info_layout.addRow("Inheritance Chain:", self._chain_label)
        
        main_layout.addLayout(info_layout)
        
        # Separator
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        main_layout.addLine(line)
        
        # Scrollable area for attributes
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        
        scroll_widget = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(10)
        
        # Light attributes group
        self._create_light_attributes_group(scroll_layout)
        
        # Transform attributes group
        self._create_transform_attributes_group(scroll_layout)
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        # Action buttons
        button_layout = QtWidgets.QHBoxLayout()

        self._apply_button = QtWidgets.QPushButton("Apply Changes")
        self._apply_button.setMinimumWidth(120)
        button_layout.addWidget(self._apply_button)

        self._revert_button = QtWidgets.QPushButton("Revert")
        self._revert_button.setMinimumWidth(100)
        button_layout.addWidget(self._revert_button)

        self._capture_button = QtWidgets.QPushButton("Capture Current")
        self._capture_button.setMinimumWidth(120)
        button_layout.addWidget(self._capture_button)

        button_layout.addStretch()

        self._select_button = QtWidgets.QPushButton("Select Light in Maya")
        self._select_button.setMinimumWidth(150)
        button_layout.addWidget(self._select_button)

        main_layout.addLayout(button_layout)

        # Connect signals
        self._apply_button.clicked.connect(self._on_apply_clicked)
        self._revert_button.clicked.connect(self._on_revert_clicked)
        self._capture_button.clicked.connect(self._on_capture_clicked)
        self._select_button.clicked.connect(self._on_select_clicked)

    def _create_light_attributes_group(self, parent_layout):
        """Create light attributes section.

        Args:
            parent_layout: Parent layout to add to
        """
        group = QtWidgets.QGroupBox("Light Attributes")
        layout = QtWidgets.QGridLayout(group)
        layout.setSpacing(5)

        # Headers
        layout.addWidget(QtWidgets.QLabel("Attribute"), 0, 0)
        layout.addWidget(QtWidgets.QLabel("Override"), 0, 1)
        layout.addWidget(QtWidgets.QLabel("Enable"), 0, 2)
        layout.addWidget(QtWidgets.QLabel("Inherited"), 0, 3)
        layout.addWidget(QtWidgets.QLabel("Source"), 0, 4)

        # Light attributes
        attributes = [
            ('intensity', 'Intensity', 1.0),
            ('exposure', 'Exposure', 0.0),
            ('colorR', 'Color R', 1.0),
            ('colorG', 'Color G', 1.0),
            ('colorB', 'Color B', 1.0),
            ('temperature', 'Temperature', 5500.0),
            ('muted', 'Muted', False),
        ]

        row = 1
        for attr_name, display_name, default_value in attributes:
            self._add_attribute_row(layout, row, attr_name, display_name, default_value)
            row += 1

        parent_layout.addWidget(group)

    def _create_transform_attributes_group(self, parent_layout):
        """Create transform attributes section.

        Args:
            parent_layout: Parent layout to add to
        """
        group = QtWidgets.QGroupBox("Transform")
        layout = QtWidgets.QGridLayout(group)
        layout.setSpacing(5)

        # Headers
        layout.addWidget(QtWidgets.QLabel("Attribute"), 0, 0)
        layout.addWidget(QtWidgets.QLabel("Override"), 0, 1)
        layout.addWidget(QtWidgets.QLabel("Enable"), 0, 2)
        layout.addWidget(QtWidgets.QLabel("Inherited"), 0, 3)
        layout.addWidget(QtWidgets.QLabel("Source"), 0, 4)

        # Transform attributes
        attributes = [
            ('translateX', 'Translate X', 0.0),
            ('translateY', 'Translate Y', 0.0),
            ('translateZ', 'Translate Z', 0.0),
            ('rotateX', 'Rotate X', 0.0),
            ('rotateY', 'Rotate Y', 0.0),
            ('rotateZ', 'Rotate Z', 0.0),
        ]

        row = 1
        for attr_name, display_name, default_value in attributes:
            self._add_attribute_row(layout, row, attr_name, display_name, default_value)
            row += 1

        parent_layout.addWidget(group)

    def _add_attribute_row(self, layout, row, attr_name, display_name, default_value):
        """Add an attribute row to the layout.

        Args:
            layout: Grid layout to add to
            row: Row number
            attr_name: Attribute name (e.g., 'intensity')
            display_name: Display name (e.g., 'Intensity')
            default_value: Default value for the attribute
        """
        # Attribute name label
        name_label = QtWidgets.QLabel(display_name)
        layout.addWidget(name_label, row, 0)

        # Override field
        if isinstance(default_value, bool):
            override_widget = QtWidgets.QCheckBox()
        else:
            override_widget = QtWidgets.QLineEdit()
            override_widget.setMaximumWidth(100)
            # Connect text changed to auto-enable checkbox
            override_widget.textChanged.connect(
                lambda text, attr=attr_name: self._on_override_changed(attr, text)
            )
        layout.addWidget(override_widget, row, 1)

        # Enable checkbox
        enable_checkbox = QtWidgets.QCheckBox()
        enable_checkbox.stateChanged.connect(
            lambda state, attr=attr_name: self._on_enable_changed(attr, state)
        )
        layout.addWidget(enable_checkbox, row, 2)

        # Inherited value label (read-only)
        inherited_label = QtWidgets.QLabel("-")
        inherited_label.setStyleSheet("color: #888;")
        layout.addWidget(inherited_label, row, 3)

        # Source label (read-only)
        source_label = QtWidgets.QLabel("-")
        source_label.setStyleSheet("color: #888;")
        layout.addWidget(source_label, row, 4)

        # Store widgets
        self._attribute_widgets[attr_name] = {
            'override': override_widget,
            'enable': enable_checkbox,
            'inherited': inherited_label,
            'source': source_label,
            'default': default_value
        }

    def _load_values(self):
        """Load current values into the UI."""
        if not cmds:
            logger.warning("Maya not available, cannot load values")
            return

        try:
            # Get enabled attributes from current gaffer's light context
            enabled_attrs = self._light_context.get_enabled_attributes()

            # Resolve all attributes from chain
            resolved = AttributeResolver.resolve_all_attributes(self._gaffer, self._light_name)

            # Get attribute sources
            sources = AttributeResolver.get_all_attribute_sources(self._gaffer, self._light_name)

            # Update each attribute widget
            for attr_name, widgets in self._attribute_widgets.items():
                # Get enabled attribute name (e.g., 'intensityEnabled')
                enabled_attr = "{}Enabled".format(attr_name)
                is_enabled = enabled_attrs.get(enabled_attr, False)

                # Set enable checkbox
                widgets['enable'].setChecked(is_enabled)

                # Set override value if enabled
                if is_enabled:
                    override_value = getattr(self._light_context, "get_{}".format(attr_name))()
                    if isinstance(widgets['override'], QtWidgets.QCheckBox):
                        widgets['override'].setChecked(override_value)
                    else:
                        widgets['override'].setText(str(override_value))
                else:
                    # Clear override field
                    if isinstance(widgets['override'], QtWidgets.QCheckBox):
                        widgets['override'].setChecked(False)
                    else:
                        widgets['override'].clear()

                # Set inherited value
                inherited_value = resolved.get(attr_name, widgets['default'])
                if isinstance(inherited_value, bool):
                    widgets['inherited'].setText("true" if inherited_value else "false")
                elif isinstance(inherited_value, float):
                    widgets['inherited'].setText("{:.2f}".format(inherited_value))
                else:
                    widgets['inherited'].setText(str(inherited_value))

                # Set source gaffer
                source_gaffer = sources.get(attr_name)
                if source_gaffer:
                    widgets['source'].setText(source_gaffer.get_gaffer_name())
                else:
                    widgets['source'].setText("-")

        except Exception as e:
            logger.error("Failed to load values: {}".format(e))

    def _on_override_changed(self, attr_name, text):
        """Handle override field text change.

        Args:
            attr_name: Attribute name
            text: New text value
        """
        # Auto-enable checkbox when user types
        if text:
            widgets = self._attribute_widgets.get(attr_name)
            if widgets:
                widgets['enable'].setChecked(True)

    def _on_enable_changed(self, attr_name, state):
        """Handle enable checkbox state change.

        Args:
            attr_name: Attribute name
            state: Checkbox state
        """
        # Could add visual feedback here
        pass

    def _on_apply_clicked(self):
        """Handle apply changes button click."""
        if not cmds:
            QtWidgets.QMessageBox.warning(
                self,
                "Maya Not Available",
                "Maya is not available."
            )
            return

        try:
            # Collect all enabled overrides
            overrides = {}

            for attr_name, widgets in self._attribute_widgets.items():
                if widgets['enable'].isChecked():
                    # Get override value
                    if isinstance(widgets['override'], QtWidgets.QCheckBox):
                        value = widgets['override'].isChecked()
                    else:
                        text = widgets['override'].text()
                        if text:
                            # Try to convert to float
                            try:
                                value = float(text)
                            except ValueError:
                                logger.warning("Invalid value for {}: {}".format(attr_name, text))
                                continue
                        else:
                            continue

                    overrides[attr_name] = value

            # Apply overrides to gaffer
            for attr_name, value in overrides.items():
                GafferManager.add_override_to_gaffer(
                    self._gaffer,
                    self._light_name,
                    attr_name,
                    value
                )

            # Apply to Maya light
            LightOperations.apply_gaffer_to_light(self._gaffer, self._light_name)

            QtWidgets.QMessageBox.information(
                self,
                "Apply Complete",
                "Applied {} overrides to light '{}'.".format(len(overrides), self._light_name)
            )

            logger.info("Applied {} overrides to light".format(len(overrides)))

        except Exception as e:
            logger.error("Failed to apply changes: {}".format(e))
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                "Failed to apply changes:\n{}".format(e)
            )

    def _on_revert_clicked(self):
        """Handle revert button click."""
        reply = QtWidgets.QMessageBox.question(
            self,
            "Revert Changes",
            "Revert all changes and reload values?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            self._load_values()

    def _on_capture_clicked(self):
        """Handle capture current button click."""
        if not cmds:
            QtWidgets.QMessageBox.warning(
                self,
                "Maya Not Available",
                "Maya is not available."
            )
            return

        try:
            # Sync light from Maya
            synced = LightOperations.sync_light_from_maya(self._gaffer, self._light_name)

            QtWidgets.QMessageBox.information(
                self,
                "Capture Complete",
                "Captured {} attributes from Maya light '{}'.".format(len(synced), self._light_name)
            )

            # Reload values
            self._load_values()

            logger.info("Captured {} attributes from Maya".format(len(synced)))

        except Exception as e:
            logger.error("Failed to capture from Maya: {}".format(e))
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                "Failed to capture from Maya:\n{}".format(e)
            )

    def _on_select_clicked(self):
        """Handle select light in Maya button click."""
        if not cmds:
            QtWidgets.QMessageBox.warning(
                self,
                "Maya Not Available",
                "Maya is not available."
            )
            return

        try:
            target_light = self._light_context.get_target_light()
            if target_light and cmds.objExists(target_light):
                cmds.select(target_light, replace=True)
                logger.info("Selected light: {}".format(target_light))
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Light Not Found",
                    "Target light '{}' not found in scene.".format(target_light)
                )

        except Exception as e:
            logger.error("Failed to select light: {}".format(e))
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                "Failed to select light:\n{}".format(e)
            )

