"""CTXSlateSchema -- schema for the CTX_Slate node.

Analog of CTXLightGafferSchema. One CTXSlateNode per scope level
(master, sequence, or shot). Connected to CTXSequenceNode or CTXShotNode.
Inherits from parent slate via parentSlate connection.
"""

from ..base import NodeSchema


class CTXSlateSchema(NodeSchema):
    """Schema for CTX_Slate nodes.

    Attributes
    ----------
    ctx_type : string
        Always 'CTX_Slate'. Used for node type identification.
    slateName : string
        Human-readable label for this slate (e.g. 'Master', 'sq0070', 'SH0170').
    slateType : string
        Scope level: 'master', 'sequence', or 'shot'.
    scopeCode : string
        Sequence or shot code this slate applies to (empty for master).
    enabled : bool
        Whether this slate participates in resolution. If False, it is skipped
        in the chain walk (same as CTXLightGaffer.enabled).
    notes : string
        Free-text notes for leads.

    Connections
    -----------
    parentSlate : INPUT
        Receives message from the parent CTXSlateNode.
        Enables inheritance: master -> sequence -> shot.
    layers : INPUT (multi)
        Receives messages from CTXSlateLayerNodes owned by this slate.
    """

    NODE_TYPE = 'network'
    NODE_PREFIX = 'CTX_Slate'
    CATEGORY = 'Slate'
    DESCRIPTION = 'Slate node with hierarchical render layer inheritance'

    ATTRIBUTES = {
        'ctx_type': {
            'type': 'string',
            'default': 'CTX_Slate',
            'description': 'CTX node type identifier',
        },
        'slateName': {
            'type': 'string',
            'default': '',
            'description': 'Human-readable slate name (e.g., "Master", "sq0070", "SH0170")',
        },
        'slateType': {
            'type': 'string',
            'default': 'master',
            'description': 'Scope level: master, sequence, or shot',
        },
        'scopeCode': {
            'type': 'string',
            'default': '',
            'description': 'Scope identifier (empty for master, seq code, or shot code)',
        },
        'enabled': {
            'type': 'bool',
            'default': True,
            'description': 'Whether this slate participates in chain resolution',
        },
        'notes': {
            'type': 'string',
            'default': '',
            'description': 'Free-text notes for leads',
        },
    }

    CONNECTIONS = {
        'parentSlate': {
            'type': 'message',
            'multi': False,
            'direction': 'input',
            'accepts': ['CTX_Slate'],
            'description': 'Parent slate in inheritance chain (master -> sequence -> shot)',
        },
        'layers': {
            'type': 'message',
            'multi': True,
            'direction': 'input',
            'description': 'CTXSlateLayerNodes managed by this slate',
        },
    }
