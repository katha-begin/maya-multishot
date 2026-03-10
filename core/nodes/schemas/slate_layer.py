"""CTXSlateLayerSchema -- schema for the CTX_SlateLayer node.

Analog of CTXLightContextSchema. One CTXSlateLayerNode per render layer
entry within a slate. Stores the renderable override value and its enabled flag.

Phase 6 scope: renderable control only.
Future phases may add collection membership, AOV overrides, etc.
"""

from ..base import NodeSchema


class CTXSlateLayerSchema(NodeSchema):
    """Schema for CTX_SlateLayer nodes.

    Attributes
    ----------
    ctx_type : string
        Always 'CTX_SlateLayer'.
    layerName : string
        Name of the render layer as it exists in Maya Render Setup.
        Must match exactly (case-sensitive).
    renderable : bool
        The renderable state this slate entry records.
        True = layer should be renderable when this shot is active.
        False = layer should NOT be renderable.
    renderableEnabled : bool
        Whether this slate OVERRIDES the renderable state.
        False (default) = inherit from parent slate -- do not apply.
        True = this entry owns the value and applies it.

        This mirrors the {attr}Enabled pattern in CTXLightContextSchema
        (e.g. intensityEnabled, colorEnabled).
    """

    NODE_TYPE = 'network'
    NODE_PREFIX = 'CTX_SlateLayer'
    CATEGORY = 'Slate'
    DESCRIPTION = 'Render layer renderable override for a slate entry'

    ATTRIBUTES = {
        'ctx_type': {
            'type': 'string',
            'default': 'CTX_SlateLayer',
            'description': 'CTX node type identifier',
        },
        'layerName': {
            'type': 'string',
            'default': '',
            'description': 'Render layer name (must match Maya Render Setup exactly)',
        },
        'renderable': {
            'type': 'bool',
            'default': True,
            'description': 'Renderable state this entry records',
        },
        'renderableEnabled': {
            'type': 'bool',
            'default': False,
            'description': 'Whether renderable is overridden by this slate entry',
        },
    }

    CONNECTIONS = {}
