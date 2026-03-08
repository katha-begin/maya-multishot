# -*- coding: utf-8 -*-
"""Light Editor Panel - Embedded per-light attribute inspector.

Shows resolved attribute values for the selected light within a gaffer.
Designed to be embedded inside GafferManagerDialog's right splitter pane.

Edit mode behaviour:
  - set_editing_enabled(True)  : all widgets become interactive; any change is
                                 applied to the Maya light live (no CTX write).
  - set_editing_enabled(False) : all widgets are disabled (view/inspect only).

CTX nodes are NEVER written from this panel.  The host dialog's Edit Mode
commit captures all Maya-live edits via snapshot diff.

Widget types:
  float scalars  -> SliderField (slider + spinbox)
  color          -> clickable swatch (edit mode) / disabled swatch (view mode)
  bool (muted)   -> QCheckBox
  contribution   -> SliderField 0-1
  transform      -> SliderField per axis
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

from core.gaffer.resolver import AttributeResolver
from ui.widgets.slider_field import SliderField, SLIDER_CONFIGS

logger = logging.getLogger(__name__)


class LightEditorPanel(QtWidgets.QWidget):
    """Inspector / live-edit panel for a single light within a gaffer.

    Embeds directly into the GafferManagerDialog splitter.
    In view mode: read-only display of resolved gaffer values.
    In edit mode: all widgets are live — changes apply to Maya immediately
                  but do NOT write to CTX nodes (the host's commit does that).
    """

    def __init__(self, gaffer=None, light_context=None, parent=None):
        super(LightEditorPanel, self).__init__(parent)

        self._gaffer = gaffer
        self._light_context = light_context
        self._light_name = light_context.get_light_name() if light_context else ''
        self._target_shape = light_context.get_target_light() if light_context else None

        self._widgets = {}          # {attr_name: widget}
        self._color = (1.0, 1.0, 1.0)
        self._editing = False       # True only while Edit Mode is active
        self._loading = False       # True while _load_values runs (suppress live apply)

        self._setup_ui()
        self._connect_live_signals()

        if light_context is not None:
            self._load_values()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_editing_enabled(self, enabled):
        """Enable or disable all interactive widgets.

        Call with True when Edit Mode starts, False when it ends.

        Args:
            enabled (bool): True = edit mode, False = view mode
        """
        self._editing = enabled
        for w in self._widgets.values():
            w.setEnabled(enabled)
        self._color_btn.setEnabled(enabled)

    def refresh(self, gaffer, light_context):
        """Reload the panel for a different light context.

        Args:
            gaffer: CTXLightGafferNode instance
            light_context: CTXLightContextNode instance
        """
        self._gaffer = gaffer
        self._light_context = light_context
        self._light_name = light_context.get_light_name() if light_context else ''
        self._target_shape = light_context.get_target_light() if light_context else None

        self._lbl_light.setText(self._light_name or '-')
        self._lbl_shape.setText(self._target_shape or 'Not connected')

        if cmds and self._target_shape:
            try:
                ltype = cmds.nodeType(self._target_shape)
            except Exception:
                ltype = 'unknown'
        else:
            ltype = 'unknown'
        self._lbl_type.setText(ltype)
        self._lbl_gaffer.setText(gaffer.get_gaffer_name() if gaffer else '-')

        self._load_values()

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # Info header
        info_form = QtWidgets.QFormLayout()
        info_form.setLabelAlignment(QtCore.Qt.AlignRight)
        info_form.setSpacing(2)

        self._lbl_light = QtWidgets.QLabel(self._light_name or '-')
        self._lbl_shape = QtWidgets.QLabel(self._target_shape or 'Not connected')
        self._lbl_gaffer = QtWidgets.QLabel(
            self._gaffer.get_gaffer_name() if self._gaffer else '-'
        )

        if cmds and self._target_shape:
            try:
                ltype = cmds.nodeType(self._target_shape)
            except Exception:
                ltype = 'unknown'
        else:
            ltype = 'unknown'
        self._lbl_type = QtWidgets.QLabel(ltype)

        info_form.addRow("Light:", self._lbl_light)
        info_form.addRow("Shape:", self._lbl_shape)
        info_form.addRow("Type:", self._lbl_type)
        info_form.addRow("Gaffer:", self._lbl_gaffer)
        main_layout.addLayout(info_form)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Sunken)
        main_layout.addWidget(sep)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(4, 4, 4, 4)
        content_layout.setSpacing(8)

        self._build_color_intensity_group(content_layout)
        self._build_shape_group(content_layout)
        self._build_contribution_group(content_layout)
        self._build_transform_group(content_layout)
        content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll, 1)

    def _build_color_intensity_group(self, parent_layout):
        group = QtWidgets.QGroupBox("Color && Intensity")
        form = QtWidgets.QFormLayout(group)
        form.setLabelAlignment(QtCore.Qt.AlignRight)

        # Color swatch — disabled until edit mode
        self._color_btn = QtWidgets.QPushButton()
        self._color_btn.setFixedHeight(22)
        self._color_btn.setEnabled(False)
        self._update_color_swatch()
        form.addRow("Color:", self._color_btn)

        for attr, label in [
            ('intensity',   'Intensity'),
            ('exposure',    'Exposure'),
            ('temperature', 'Temperature (K)'),
        ]:
            w = self._make_slider_field(attr)
            w.setEnabled(False)
            self._widgets[attr] = w
            form.addRow(label + ":", w)

        parent_layout.addWidget(group)

    def _build_shape_group(self, parent_layout):
        group = QtWidgets.QGroupBox("Light Shape")
        form = QtWidgets.QFormLayout(group)
        form.setLabelAlignment(QtCore.Qt.AlignRight)

        w = self._make_slider_field('spread')
        w.setEnabled(False)
        self._widgets['spread'] = w
        form.addRow("Spread:", w)

        cb = QtWidgets.QCheckBox()
        cb.setEnabled(False)
        self._widgets['muted'] = cb
        form.addRow("Muted:", cb)

        parent_layout.addWidget(group)

    def _build_contribution_group(self, parent_layout):
        group = QtWidgets.QGroupBox("Contribution (0 = off, 1 = full)")
        form = QtWidgets.QFormLayout(group)
        form.setLabelAlignment(QtCore.Qt.AlignRight)

        for attr, label in [
            ('affectDiffuse',  'Affect Diffuse'),
            ('affectSpecular', 'Affect Specular'),
            ('affectGI',       'Affect GI'),
            ('shadowEnable',   'Cast Shadows'),
        ]:
            w = self._make_slider_field(attr)
            w.setEnabled(False)
            self._widgets[attr] = w
            form.addRow(label + ":", w)

        parent_layout.addWidget(group)

    def _build_transform_group(self, parent_layout):
        group = QtWidgets.QGroupBox("Transform")
        grid = QtWidgets.QGridLayout(group)
        grid.setSpacing(4)

        grid.addWidget(QtWidgets.QLabel(""), 0, 0)
        for col, axis in enumerate(['X', 'Y', 'Z'], start=1):
            lbl = QtWidgets.QLabel(axis)
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            grid.addWidget(lbl, 0, col)

        rows = [
            ('translate', ['translateX', 'translateY', 'translateZ']),
            ('rotate',    ['rotateX', 'rotateY', 'rotateZ']),
            ('scale',     ['scaleX', 'scaleY', 'scaleZ']),
        ]

        for r_idx, (row_label, attrs) in enumerate(rows, start=1):
            grid.addWidget(QtWidgets.QLabel(row_label.capitalize() + ":"), r_idx, 0)
            for c_idx, attr in enumerate(attrs, start=1):
                w = self._make_slider_field(attr)
                w.setEnabled(False)
                if row_label == 'scale':
                    w.setValue(1.0)
                self._widgets[attr] = w
                grid.addWidget(w, r_idx, c_idx)

        parent_layout.addWidget(group)

    # ------------------------------------------------------------------
    # Widget helpers
    # ------------------------------------------------------------------

    def _make_slider_field(self, attr_name):
        cfg = SLIDER_CONFIGS.get(attr_name)
        if cfg:
            return SliderField(**cfg)
        w = QtWidgets.QDoubleSpinBox()
        w.setRange(-999999, 999999)
        w.setDecimals(3)
        w.setSingleStep(0.01)
        w.setMinimumWidth(80)
        return w

    def _update_color_swatch(self):
        r, g, b = self._color
        ri, gi, bi = int(r * 255), int(g * 255), int(b * 255)
        self._color_btn.setStyleSheet(
            "background-color: rgb({},{},{}); border: 1px solid #555;".format(ri, gi, bi)
        )
        self._color_btn.setText("{:.2f}  {:.2f}  {:.2f}".format(r, g, b))

    # ------------------------------------------------------------------
    # Signal wiring — connected once, guarded inside handlers
    # ------------------------------------------------------------------

    def _connect_live_signals(self):
        """Connect all widget signals to the live-apply handler.

        Handlers are no-ops when not in edit mode (_editing == False).
        SliderField.setValue() already blocks signals so _load_values is safe.
        """
        for attr, w in self._widgets.items():
            if isinstance(w, SliderField):
                w.valueChanged.connect(self._on_live_apply)
            elif isinstance(w, QtWidgets.QDoubleSpinBox):
                w.valueChanged.connect(self._on_live_apply)
            elif isinstance(w, QtWidgets.QCheckBox):
                w.toggled.connect(self._on_live_apply)

        self._color_btn.clicked.connect(self._on_color_pick)

    # ------------------------------------------------------------------
    # Live-edit handlers (edit mode only, no CTX writes)
    # ------------------------------------------------------------------

    def _on_color_pick(self, *_):
        """Open color picker and apply to Maya live. No CTX write."""
        if not self._editing:
            return
        r, g, b = self._color
        initial = QtGui.QColor(int(r * 255), int(g * 255), int(b * 255))
        color = QtWidgets.QColorDialog.getColor(initial, self, "Pick Light Color")
        if color.isValid():
            self._color = (color.redF(), color.greenF(), color.blueF())
            self._update_color_swatch()
            self._on_live_apply()

    def _on_live_apply(self, *_):
        """Apply all current widget values to the Maya light shape.

        Called on any widget change. Does nothing outside edit mode or during
        _load_values. Never writes to CTX nodes — the snapshot/diff commit
        handles persistence.
        """
        if not self._editing or self._loading:
            return
        if not self._target_shape or not cmds:
            return
        if not cmds.objExists(self._target_shape):
            return

        try:
            from core.renderers import get_maya_attr

            shape = self._target_shape
            transforms = cmds.listRelatives(shape, parent=True, fullPath=True) or []
            transform = transforms[0] if transforms else None

            # Color
            r, g, b = self._color
            if cmds.attributeQuery('color', node=shape, exists=True):
                cmds.setAttr('{}.color'.format(shape), r, g, b, type='double3')

            # Scalar attrs
            for attr in ('intensity', 'exposure', 'temperature'):
                if attr not in self._widgets:
                    continue
                value = self._widgets[attr].value()
                maya_attr = get_maya_attr(shape, attr) or attr
                if cmds.attributeQuery(maya_attr, node=shape, exists=True):
                    cmds.setAttr('{}.{}'.format(shape, maya_attr), value)

            # Spread
            if 'spread' in self._widgets:
                value = self._widgets['spread'].value()
                spread_attr = get_maya_attr(shape, 'spread')
                if spread_attr and cmds.attributeQuery(spread_attr, node=shape, exists=True):
                    cmds.setAttr('{}.{}'.format(shape, spread_attr), value)

            # Muted (shape on/off + transform visibility)
            if 'muted' in self._widgets:
                muted = self._widgets['muted'].isChecked()
                muted_attr = get_maya_attr(shape, 'muted')
                if muted_attr and cmds.attributeQuery(muted_attr, node=shape, exists=True):
                    cmds.setAttr('{}.{}'.format(shape, muted_attr), 0 if muted else 1)
                if transform and cmds.attributeQuery('visibility', node=transform, exists=True):
                    cmds.setAttr('{}.visibility'.format(transform), not muted)

            # Contribution attrs
            for attr in ('affectDiffuse', 'affectSpecular', 'affectGI', 'shadowEnable'):
                if attr not in self._widgets:
                    continue
                value = self._widgets[attr].value()
                maya_attr = get_maya_attr(shape, attr)
                if maya_attr and cmds.attributeQuery(maya_attr, node=shape, exists=True):
                    attr_type = cmds.getAttr('{}.{}'.format(shape, maya_attr), type=True)
                    write_val = (value > 0.5) if attr_type in ('bool',) else value
                    cmds.setAttr('{}.{}'.format(shape, maya_attr), write_val)

            # Transform
            if transform:
                for attr in ('translateX', 'translateY', 'translateZ',
                             'rotateX', 'rotateY', 'rotateZ',
                             'scaleX', 'scaleY', 'scaleZ'):
                    if attr in self._widgets:
                        if cmds.attributeQuery(attr, node=transform, exists=True):
                            cmds.setAttr('{}.{}'.format(transform, attr),
                                         self._widgets[attr].value())

        except Exception as e:
            logger.warning("Live apply to '{}' failed: {}".format(self._target_shape, e))

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_values(self):
        """Read resolved gaffer values and populate all widgets.

        Suppresses _on_live_apply via _loading flag.
        SliderField.setValue() already blocks its own signals.
        """
        if not self._gaffer or not self._light_context:
            return

        self._loading = True
        try:
            resolved = AttributeResolver.resolve_all_attributes(
                self._gaffer, self._light_name
            )
        except Exception as e:
            logger.warning("resolve_all_attributes failed for '{}': {}".format(
                self._light_name, e))
            self._loading = False
            return

        def _val(attr, default):
            entry = resolved.get(attr)
            return entry.get('value', default) if entry else default

        # Color
        color_val = _val('color', (1.0, 1.0, 1.0))
        if isinstance(color_val, (list, tuple)) and len(color_val) == 3:
            self._color = tuple(color_val)
        else:
            self._color = (1.0, 1.0, 1.0)
        self._update_color_swatch()

        # Scalars
        for attr, default in [
            ('intensity', 1.0), ('exposure', 0.0), ('temperature', 6500.0), ('spread', 1.0),
        ]:
            if attr in self._widgets:
                self._widgets[attr].setValue(float(_val(attr, default)))

        # Muted (blockSignals on QCheckBox to avoid spurious live-apply)
        if 'muted' in self._widgets:
            cb = self._widgets['muted']
            cb.blockSignals(True)
            cb.setChecked(bool(_val('muted', False)))
            cb.blockSignals(False)

        # Contribution flags
        for attr in ('affectDiffuse', 'affectSpecular', 'affectGI', 'shadowEnable'):
            if attr in self._widgets:
                raw = _val(attr, True)
                self._widgets[attr].setValue(1.0 if raw else 0.0)

        # Transform
        defaults = {'translateX': 0.0, 'translateY': 0.0, 'translateZ': 0.0,
                    'rotateX': 0.0, 'rotateY': 0.0, 'rotateZ': 0.0,
                    'scaleX': 1.0, 'scaleY': 1.0, 'scaleZ': 1.0}
        for attr, default in defaults.items():
            if attr in self._widgets:
                self._widgets[attr].setValue(float(_val(attr, default)))

        self._loading = False
