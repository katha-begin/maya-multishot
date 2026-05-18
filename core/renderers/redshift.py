"""
Redshift light attribute map.

Maps gaffer attribute names to Redshift Maya attribute names.
Key:   gaffer attribute name (as stored in CTXLightContextSchema)
Value: Maya attribute name on the light shape node
"""

from __future__ import absolute_import, division, print_function

# Redshift light node types
LIGHT_TYPES = [
    'RedshiftPhysicalLight',
    'RedshiftDomeLight',
    'RedshiftIESLight',
]

# Per-light-type attribute overrides for light types with non-standard attribute names.
# Values here take precedence over ATTR_MAP for the specified light type.
LIGHT_TYPE_ATTR_OVERRIDES = {
    'RedshiftDomeLight': {
        # Dome lights use 'multiplier' for the overall brightness, not 'intensity'
        'intensity': 'multiplier',
    },
}

# Gaffer attribute -> Maya attribute name on Redshift light shape
ATTR_MAP = {
    # Brightness
    'intensity':              'intensity',
    'exposure':               'exposure',

    # Color
    'color':                  'color',

    # Mute -- RS uses .on (1=enabled, 0=disabled)
    'muted':                  'on',

    # Spread / cone
    'spread':                 'spread',
    'areaSpread':             'areaSpread',

    # Legacy contribution flags (bool)
    'affectDiffuse':          'affectDiffuse',
    'affectSpecular':         'affectSpecular',
    'affectGI':               'affectGI',
    'shadowEnable':           'shadowEnable',

    # Per-ray-type contribution scales (float 0-1)
    'diffuseContrib':         'diffuseRayContributionScale',
    'reflectionContrib':      'reflectionRayContributionScale',
    'transmissionContrib':    'transmissionRayContributionScale',
    'singleScatterContrib':   'singleScatteringRayContributionScale',
    'multiScatterContrib':    'multipleScatteringRayContributionScale',
    'volumeContrib':          'volumeRayContributionScale',
    'indirectContrib':        'indirectRayContributionScale',
    'toonDiffuseContrib':     'toonDiffuseRayContributionScale',
    'toonReflectionContrib':  'toonReflectionRayContributionScale',
}
