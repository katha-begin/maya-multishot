"""Lock mixin for CTX node schemas.

Adds is_locked, locked_by, and locked_at attributes to any schema
that inherits this mixin. Mixed in before NodeSchema in MRO.
"""

from __future__ import absolute_import, division, print_function


class LockSchemaMixin(object):
    """Mixin that adds lock state attributes to a CTX node schema.

    Usage:
        class CTXShotSchema(LockSchemaMixin, NodeSchema):
            ...

    The mixin adds three string/bool attributes. They are merged into the
    schema's ATTRIBUTES dict by the NodeSchema metaclass via _collect_attributes().
    """

    LOCK_ATTRIBUTES = {
        'is_locked': {
            'type': 'bool',
            'default': False,
        },
        'locked_by': {
            'type': 'string',
            'default': '',
        },
        'locked_at': {
            'type': 'string',
            'default': '',
        },
    }
