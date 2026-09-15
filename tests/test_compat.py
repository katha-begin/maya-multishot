"""Tests for core.compat -- Python 2.7 / 3.x helpers.

Plain unittest (no unittest.mock) so the same file also runs under Maya's
Python 2.7 interpreter:  mayapy2 -m unittest tests.test_compat
"""

from __future__ import absolute_import, division, print_function

import os
import shutil
import sys
import tempfile
import threading
import unittest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core.compat import string_types, makedirs, is_main_thread


class TestStringTypes(unittest.TestCase):

    def test_native_str_is_a_string(self):
        self.assertTrue(isinstance('node1', string_types))

    def test_unicode_is_a_string(self):
        # maya.cmds, PySide2 and json all return unicode on Python 2
        self.assertTrue(isinstance(u'node1', string_types))

    def test_wrapper_object_is_not_a_string(self):
        self.assertFalse(isinstance(object(), string_types))


class TestMakedirs(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_creates_nested_dirs(self):
        path = os.path.join(self.root, 'a', 'b', 'c')
        makedirs(path)
        self.assertTrue(os.path.isdir(path))

    def test_existing_dir_is_not_an_error(self):
        path = os.path.join(self.root, 'a')
        makedirs(path)
        makedirs(path)
        self.assertTrue(os.path.isdir(path))

    def test_existing_file_still_raises(self):
        path = os.path.join(self.root, 'file.txt')
        with open(path, 'w') as handle:
            handle.write('x')
        with self.assertRaises(OSError):
            makedirs(path)


class TestIsMainThread(unittest.TestCase):

    def test_true_on_main_thread(self):
        self.assertTrue(is_main_thread())

    def test_false_on_worker_thread(self):
        seen = []
        worker = threading.Thread(target=lambda: seen.append(is_main_thread()))
        worker.start()
        worker.join()
        self.assertEqual(seen, [False])


if __name__ == '__main__':
    unittest.main()
