"""Schema for CTX_SlateOriginals node.

Singleton node per scene. Stores the renderable state of all render layers
before any slate override is applied.
"""

from __future__ import absolute_import, division, print_function

from ..base import NodeSchema


class CTXSlateOriginalsSchema(NodeSchema):
    """Schema for CTX_SlateOriginals node.

    Singleton -- at most one per scene. Stores original render layer renderable
    states as JSON so they survive scene save/reload without re-capture.
    """

    NODE_TYPE = "network"
    NODE_PREFIX = "CTX_SlateOriginals"
    CATEGORY = "Context"
    DESCRIPTION = "Singleton: stores original render layer renderable states"

    ATTRIBUTES = {
        'ctx_type': {
            'type': 'string',
            'default': 'CTX_SlateOriginals',
            'description': 'CTX node type identifier',
        },
        'originalsJson': {
            'type': 'string',
            'default': '{}',
            'description': 'JSON dict: {layer_name: renderable_bool}',
        },
    }

    CONNECTIONS = {}
