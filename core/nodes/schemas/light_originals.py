"""
Schema definition for CTX_LightOriginals node.

Singleton node that stores original Maya light values as a JSON string,
captured before any gaffer is applied. This is the ground-truth baseline
used when restoring lights on shot switch.
"""

from ..base import NodeSchema


class CTXLightOriginalsSchema(NodeSchema):
    """Schema for CTX_LightOriginals node.

    Singleton -- at most one per scene. Stores original light values as
    JSON so they survive scene save/reload without re-capture.
    """

    NODE_TYPE = "network"
    NODE_PREFIX = "CTX_LightOriginals"
    CATEGORY = "Lighting"
    DESCRIPTION = "Persistent original light value store (pre-gaffer baseline)"

    ATTRIBUTES = {
        'ctx_type': {
            'type': 'string',
            'default': 'CTX_LightOriginals',
            'description': 'CTX node type identifier',
        },
        'originalsJson': {
            'type': 'string',
            'default': '{}',
            'description': 'JSON dict of original light values: {shape: {attr: value}}',
        },
    }

    CONNECTIONS = {}
