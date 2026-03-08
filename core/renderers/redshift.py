"""
Redshift light attribute map.

Maps gaffer attribute names to Redshift Maya attribute names.
Key:   gaffer attribute name (as stored in CTXLightContextSchema)
Value: Maya attribute name on the light shape node
"""

# Redshift light node types
LIGHT_TYPES = [
    'RedshiftPhysicalLight',
    'RedshiftDomeLight',
    'RedshiftIESLight',
]

# Gaffer attribute -> Maya attribute name on Redshift light shape
ATTR_MAP = {
    # Brightness
    'intensity':              'intensity',
    'exposure':               'exposure',

    # Color
    'color':                  'color',

    # Mute — RS uses .on (1=enabled, 0=disabled)
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
