# -*- coding: utf-8 -*-
"""Shot switching must not reload unchanged references or unload on a missing file.

Plain unittest with a fake cmds, so it also runs under Maya's Python 2.7:
    mayapy2 -m unittest tests.test_reference_swap
"""

from __future__ import absolute_import, division, print_function

import os
import shutil
import sys
import tempfile
import unittest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# core/nodes/ (a package) shadows core/nodes.py; the package loads the file as
# nodes_legacy, whose globals are what NodeManager actually reads.
from core.nodes import nodes_legacy as nodes


class _FakeCmds(object):
    """A scene with one loaded reference 'thornbyRN'."""

    def __init__(self, current_file, loaded=True):
        self.current_file = current_file
        self.loaded = loaded
        self.file_calls = []

    def objExists(self, name):
        return True

    def nodeType(self, node):
        return 'reference' if node == 'thornbyRN' else 'mesh'

    def referenceQuery(self, node, **kwargs):
        if kwargs.get('filename'):
            return self.current_file
        if kwargs.get('isLoaded'):
            return self.loaded
        if kwargs.get('isNodeReferenced'):
            return True
        if kwargs.get('referenceNode'):
            return 'thornbyRN'
        raise AssertionError('unexpected referenceQuery {}'.format(kwargs))

    def file(self, path, **kwargs):
        self.file_calls.append((path, kwargs))
        self.current_file = path
        self.loaded = True


class TestReferenceSwap(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.v1 = os.path.join(self.tmp, 'v001', 'asset.abc').replace('\\', '/')
        self.v2 = os.path.join(self.tmp, 'v002', 'asset.abc').replace('\\', '/')
        for path in (self.v1, self.v2):
            os.makedirs(os.path.dirname(path))
            open(path, 'w').close()
        self._saved = (nodes.cmds, nodes.MAYA_AVAILABLE)
        nodes.MAYA_AVAILABLE = True

    def tearDown(self):
        nodes.cmds, nodes.MAYA_AVAILABLE = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _apply(self, fake, node, path):
        nodes.cmds = fake
        return nodes.NodeManager()._apply_path_to_maya_node(node, path)

    def test_unchanged_path_does_not_reload(self):
        fake = _FakeCmds(self.v1)
        self.assertTrue(self._apply(fake, 'thornbyRN', self.v1))
        self.assertTrue(self._apply(fake, 'thornbyRN', self.v1.replace('/', '\\')))
        self.assertEqual(fake.file_calls, [])

    def test_changed_path_swaps_once(self):
        fake = _FakeCmds(self.v1)
        self.assertTrue(self._apply(fake, 'thornbyRN', self.v2))
        self.assertEqual([c[0] for c in fake.file_calls], [self.v2])
        self.assertEqual(fake.file_calls[0][1], {'loadReference': 'thornbyRN'})

    def test_missing_file_leaves_reference_alone(self):
        fake = _FakeCmds(self.v1)
        missing = self.v2.replace('v002', 'v099')
        self.assertFalse(self._apply(fake, 'thornbyRN', missing))
        self.assertEqual(fake.file_calls, [])
        self.assertEqual(fake.current_file, self.v1)

    def test_unloaded_reference_on_same_path_is_loaded(self):
        fake = _FakeCmds(self.v1, loaded=False)
        self.assertTrue(self._apply(fake, 'thornbyRN', self.v1))
        self.assertEqual(len(fake.file_calls), 1)

    def test_node_inside_reference_uses_its_reference_node(self):
        fake = _FakeCmds(self.v1)
        self.assertTrue(self._apply(fake, 'thornby:bodyShape', self.v1))
        self.assertEqual(fake.file_calls, [])


if __name__ == '__main__':
    unittest.main()
