"""
Arnold light attribute map.

Maps gaffer attribute names to Arnold Maya attribute names.
Key:   gaffer attribute name (as stored in CTXLightContextSchema)
Value: Maya attribute name on the light shape node

Notes:
- Arnold contribution flags (aiDiffuse, aiSpecular, aiIndirect) are float
  multipliers (0.0 = off, 1.0 = full contribution). The gaffer stores them
  as bool and the application layer coerces: True -> 1.0, False -> 0.0.
"""

from __future__ import absolute_import, division, print_function

# Arnold light node types
LIGHT_TYPES = [
    'aiAreaLight',
    'aiSkyDomeLight',
    'aiPhotometricLight',
    'aiLightPortal',
]

# Gaffer attribute -> Maya attribute name on Arnold light shape
ATTR_MAP = {
    # Brightness
    'intensity':      'intensity',
    'exposure':       'exposure',

    # Color
    'color':          'color',          # compound (colorR, colorG, colorB)

    # Spread / softness
    'spread':         'aiSpread',

    # Contribution flags (Arnold uses float multipliers)
    'affectDiffuse':  'aiDiffuse',
    'affectSpecular': 'aiSpecular',
    'affectGI':       'aiIndirect',
    'shadowEnable':   'aiCastShadows',
}
