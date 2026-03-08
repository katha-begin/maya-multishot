# -*- coding: utf-8 -*-
"""SliderField - Maya-style slider + number input composite widget.

Matches Maya Attribute Editor layout: horizontal slider fills available width,
compact number input on the right. The slider uses a practical "visual range"
while the spinbox allows the full numeric range.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

try:
    from PySide6 import QtWidgets, QtCore
    from PySide6.QtCore import Signal
except ImportError:
    from PySide2 import QtWidgets, QtCore
    from PySide2.QtCore import Signal


# Slider integer resolution — higher = smoother drag
_SLIDER_STEPS = 10000

# Per-attribute configuration:
#   slider_min/max: "visual" range the slider covers
#   spinbox_min/max: full numeric range the spinbox allows
#   decimals: decimal places
#   step: spinbox single-step increment
SLIDER_CONFIGS = {
    'intensity':      dict(slider_min=0,     slider_max=200,   spinbox_min=0,       spinbox_max=999999, decimals=3, step=0.1),
    'exposure':       dict(slider_min=-10,   slider_max=10,    spinbox_min=-20,     spinbox_max=20,     decimals=2, step=0.1),
    'temperature':    dict(slider_min=1000,  slider_max=20000, spinbox_min=1000,    spinbox_max=20000,  decimals=0, step=100),
    'spread':         dict(slider_min=0,     slider_max=1,     spinbox_min=0,       spinbox_max=1,      decimals=3, step=0.01),
    'affectDiffuse':  dict(slider_min=0,     slider_max=1,     spinbox_min=0,       spinbox_max=1,      decimals=2, step=0.01),
    'affectSpecular': dict(slider_min=0,     slider_max=1,     spinbox_min=0,       spinbox_max=1,      decimals=2, step=0.01),
    'affectGI':       dict(slider_min=0,     slider_max=1,     spinbox_min=0,       spinbox_max=1,      decimals=2, step=0.01),
    'shadowEnable':   dict(slider_min=0,     slider_max=1,     spinbox_min=0,       spinbox_max=1,      decimals=2, step=0.01),
    'translateX':     dict(slider_min=-100,  slider_max=100,   spinbox_min=-999999, spinbox_max=999999, decimals=4, step=0.001),
    'translateY':     dict(slider_min=-100,  slider_max=100,   spinbox_min=-999999, spinbox_max=999999, decimals=4, step=0.001),
    'translateZ':     dict(slider_min=-100,  slider_max=100,   spinbox_min=-999999, spinbox_max=999999, decimals=4, step=0.001),
    'rotateX':        dict(slider_min=-360,  slider_max=360,   spinbox_min=-360,    spinbox_max=360,    decimals=2, step=0.1),
    'rotateY':        dict(slider_min=-360,  slider_max=360,   spinbox_min=-360,    spinbox_max=360,    decimals=2, step=0.1),
    'rotateZ':        dict(slider_min=-360,  slider_max=360,   spinbox_min=-360,    spinbox_max=360,    decimals=2, step=0.1),
    'scaleX':         dict(slider_min=0,     slider_max=4,     spinbox_min=0.001,   spinbox_max=999999, decimals=4, step=0.001),
    'scaleY':         dict(slider_min=0,     slider_max=4,     spinbox_min=0.001,   spinbox_max=999999, decimals=4, step=0.001),
    'scaleZ':         dict(slider_min=0,     slider_max=4,     spinbox_min=0.001,   spinbox_max=999999, decimals=4, step=0.001),
}


class SliderField(QtWidgets.QWidget):
    """Maya-style composite: QSlider (fills width) + QDoubleSpinBox (right, fixed).

    Signals:
        valueChanged(float): emitted whenever the value changes from either widget
    """

    valueChanged = Signal(float)

    def __init__(self, slider_min, slider_max, spinbox_min, spinbox_max,
                 decimals=3, step=0.01, parent=None):
        super(SliderField, self).__init__(parent)

        self._slider_min = float(slider_min)
        self._slider_max = float(slider_max)
        self._decimals = decimals

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._slider.setRange(0, _SLIDER_STEPS)
        self._slider.setMinimumWidth(80)
        layout.addWidget(self._slider, stretch=1)

        self._spinbox = QtWidgets.QDoubleSpinBox()
        self._spinbox.setRange(spinbox_min, spinbox_max)
        self._spinbox.setDecimals(decimals)
        self._spinbox.setSingleStep(step)
        self._spinbox.setMinimumWidth(90)
        self._spinbox.setMaximumWidth(100)
        layout.addWidget(self._spinbox, stretch=0)

        self._slider.valueChanged.connect(self._on_slider_moved)
        self._spinbox.valueChanged.connect(self._on_spinbox_changed)

    # ------------------------------------------------------------------
    # Float <-> int mapping for slider
    # ------------------------------------------------------------------

    def _float_to_int(self, v):
        """Map a float value to slider integer position (clamped to slider range)."""
        v = max(self._slider_min, min(self._slider_max, float(v)))
        span = self._slider_max - self._slider_min
        if span == 0:
            return 0
        return int((v - self._slider_min) / span * _SLIDER_STEPS)

    def _int_to_float(self, i):
        """Map slider integer position to float value."""
        span = self._slider_max - self._slider_min
        return self._slider_min + (i / _SLIDER_STEPS) * span

    # ------------------------------------------------------------------
    # Sync handlers (blockSignals prevents recursion)
    # ------------------------------------------------------------------

    def _on_slider_moved(self, int_val):
        float_val = self._int_to_float(int_val)
        self._spinbox.blockSignals(True)
        self._spinbox.setValue(float_val)
        self._spinbox.blockSignals(False)
        self.valueChanged.emit(float_val)

    def _on_spinbox_changed(self, float_val):
        self._slider.blockSignals(True)
        self._slider.setValue(self._float_to_int(float_val))
        self._slider.blockSignals(False)
        self.valueChanged.emit(float_val)

    # ------------------------------------------------------------------
    # Public API (matches QDoubleSpinBox interface used by light editor)
    # ------------------------------------------------------------------

    def value(self):
        """Return current float value."""
        return self._spinbox.value()

    def setValue(self, v):
        """Set value (updates both slider and spinbox without emitting signal)."""
        self._slider.blockSignals(True)
        self._spinbox.blockSignals(True)
        self._spinbox.setValue(float(v))
        self._slider.setValue(self._float_to_int(float(v)))
        self._slider.blockSignals(False)
        self._spinbox.blockSignals(False)
