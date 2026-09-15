# -*- coding: utf-8 -*-
"""The Edit Frame Range dialogs must be able to read and write a CTX_Shot.

ShotContextDialog and the multi-shot dialog call get_fps / get_handles /
set_handles / get_frame_offset / set_frame_offset; the schema-based
CTXShotNode lacked them, so saving failed with "'CTXShotNode' object has no
attribute 'set_handles'" before the frame range JSON was written.

Plain unittest with a fake cmds, so it also runs under Maya's Python 2.7:
    mayapy2 -m unittest tests.test_shot_frame_edit
"""

from __future__ import absolute_import, division, print_function

import os
import sys
import unittest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core.nodes import base
from core.nodes.wrappers.shot import CTXShotNode


class _FakeCmds(object):
    """Holds attribute values per node; enough for get/set_attribute."""

    def __init__(self, attrs):
        self.attrs = attrs

    def attributeQuery(self, attr, node=None, exists=False):
        return attr in self.attrs.get(node, {})

    def getAttr(self, plug):
        node, attr = plug.split('.', 1)
        return self.attrs[node][attr]

    def setAttr(self, plug, value, **kwargs):
        node, attr = plug.split('.', 1)
        if attr not in self.attrs[node]:
            raise RuntimeError('No attribute {}'.format(plug))
        self.attrs[node][attr] = value

    def addAttr(self, node, longName=None, **kwargs):
        self.attrs[node][longName] = None


class TestShotFrameEditApi(unittest.TestCase):

    def setUp(self):
        self._orig_cmds = base.cmds
        self.cmds = _FakeCmds({
            'CTX_Shot_new': {'start_frame': 1001, 'end_frame': 1100, 'fps': 25.0,
                             'handles': 8, 'frame_offset': 3},
            # Created before handles / frame_offset joined the schema.
            'CTX_Shot_old': {'start_frame': 1001, 'end_frame': 1100, 'fps': 24.0},
        })
        base.cmds = self.cmds

    def tearDown(self):
        base.cmds = self._orig_cmds

    def test_reads_values(self):
        shot = CTXShotNode('CTX_Shot_new')
        self.assertEqual(shot.get_fps(), 25.0)
        self.assertEqual(shot.get_handles(), 8)
        self.assertEqual(shot.get_frame_offset(), 3)

    def test_writes_values(self):
        shot = CTXShotNode('CTX_Shot_new')
        shot.set_handles(12)
        shot.set_frame_offset(-5)
        attrs = self.cmds.attrs['CTX_Shot_new']
        self.assertEqual(attrs['handles'], 12)
        self.assertEqual(attrs['frame_offset'], -5)

    def test_old_node_reads_schema_defaults(self):
        shot = CTXShotNode('CTX_Shot_old')
        self.assertEqual(shot.get_handles(), 10)
        self.assertEqual(shot.get_frame_offset(), 0)

    def test_old_node_gains_attributes_on_write(self):
        shot = CTXShotNode('CTX_Shot_old')
        shot.set_handles(4)
        shot.set_frame_offset(2)
        attrs = self.cmds.attrs['CTX_Shot_old']
        self.assertEqual(attrs['handles'], 4)
        self.assertEqual(attrs['frame_offset'], 2)

    def test_dialog_methods_exist(self):
        for name in ('get_frame_range', 'set_frame_range', 'get_fps', 'set_fps',
                     'get_handles', 'set_handles', 'get_frame_offset',
                     'set_frame_offset', 'get_shot_id'):
            self.assertTrue(callable(getattr(CTXShotNode, name, None)), name)


if __name__ == '__main__':
    unittest.main()
