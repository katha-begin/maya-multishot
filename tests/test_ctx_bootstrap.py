"""Tests for ctx_bootstrap -- locating, clearing and re-running this install.

Plain unittest (no unittest.mock) so the same file also runs under Maya's
Python 2.7 interpreter:  mayapy2 -m unittest tests.test_ctx_bootstrap
"""

from __future__ import absolute_import, division, print_function

import os
import shutil
import sys
import tempfile
import types
import unittest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import ctx_bootstrap


def _norm(path):
    return os.path.normcase(os.path.abspath(path))


def _touch(path, text=''):
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    with open(path, 'w') as handle:
        handle.write(text)


def _make_checkout(root):
    """Create the files that identify a CTX Tools checkout (old or new)."""
    _touch(os.path.join(root, 'tools', 'maya_menu.py'))
    _touch(os.path.join(root, 'core', 'gaffer', '__init__.py'))


def _fake_module(name, path, package_dir=None):
    module = types.ModuleType(name)
    module.__file__ = path
    if package_dir:
        module.__path__ = [package_dir]
    return module


class _TempDirTestCase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._added_modules = []

    def tearDown(self):
        for name in self._added_modules:
            sys.modules.pop(name, None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def add_module(self, name, module):
        sys.modules[name] = module
        self._added_modules.append(name)


class TestRepoRoot(_TempDirTestCase):

    def test_repo_root_is_this_checkout(self):
        self.assertEqual(_norm(ctx_bootstrap.REPO_ROOT), _norm(_PROJECT_ROOT))

    def test_is_repo_root_recognises_a_checkout(self):
        root = os.path.join(self.tmp, 'maya-multishot')
        _make_checkout(root)
        self.assertTrue(ctx_bootstrap.is_repo_root(root))

    def test_is_repo_root_rejects_other_folders(self):
        other = os.path.join(self.tmp, 'other_tool')
        _touch(os.path.join(other, 'core', '__init__.py'))
        self.assertFalse(ctx_bootstrap.is_repo_root(other))


class TestPurgeModules(_TempDirTestCase):

    def test_removes_only_modules_inside_the_root(self):
        root = os.path.join(self.tmp, 'install')
        sibling = os.path.join(self.tmp, 'install2')  # shares the prefix
        self.add_module('ctxtest_inside',
                        _fake_module('ctxtest_inside',
                                     os.path.join(root, 'core', 'x.py')))
        self.add_module('ctxtest_sibling',
                        _fake_module('ctxtest_sibling',
                                     os.path.join(sibling, 'core', 'y.py')))
        self.add_module('ctxtest_placeholder', None)  # Python 2 leaves these

        purged = ctx_bootstrap.purge_modules(roots=[root])

        self.assertIn('ctxtest_inside', purged)
        self.assertNotIn('ctxtest_inside', sys.modules)
        self.assertIn('ctxtest_sibling', sys.modules)
        self.assertIn('ctxtest_placeholder', sys.modules)
        self.assertIn('os', sys.modules)

    def test_same_package_name_from_another_tool_is_kept(self):
        # A studio tool with its own "core" package must survive a purge.
        root = os.path.join(self.tmp, 'install')
        other = os.path.join(self.tmp, 'studio_tool')
        self.add_module('ctxtest_core.gaffer',
                        _fake_module('ctxtest_core.gaffer',
                                     os.path.join(other, 'core', 'gaffer.py')))

        ctx_bootstrap.purge_modules(roots=[root])

        self.assertIn('ctxtest_core.gaffer', sys.modules)

    def test_never_removes_main(self):
        root = os.path.join(self.tmp, 'install')
        real_main = sys.modules['__main__']
        fake_main = _fake_module('__main__', os.path.join(root, 'launch.py'))
        sys.modules['__main__'] = fake_main
        try:
            ctx_bootstrap.purge_modules(roots=[root])
            self.assertIs(sys.modules['__main__'], fake_main)
        finally:
            sys.modules['__main__'] = real_main


class TestCandidateRoots(_TempDirTestCase):

    def test_includes_checkout_of_already_loaded_package(self):
        # An older copy loaded earlier in the session (e.g. from another
        # drive) must be purged too, or its modules shadow the new install.
        old_root = os.path.join(self.tmp, 'old_install')
        _make_checkout(old_root)
        old_core = os.path.join(old_root, 'core')
        real_core = sys.modules.get('core')
        sys.modules['core'] = _fake_module(
            'core', os.path.join(old_core, '__init__.py'), package_dir=old_core)
        try:
            roots = ctx_bootstrap.candidate_roots()
        finally:
            if real_core is None:
                sys.modules.pop('core', None)
            else:
                sys.modules['core'] = real_core

        self.assertIn(_norm(old_root), roots)
        self.assertIn(_norm(ctx_bootstrap.REPO_ROOT), roots)

    def test_ignores_package_of_another_tool(self):
        other_core = os.path.join(self.tmp, 'studio_tool', 'core')
        _touch(os.path.join(other_core, '__init__.py'))
        real_core = sys.modules.get('core')
        sys.modules['core'] = _fake_module(
            'core', os.path.join(other_core, '__init__.py'),
            package_dir=other_core)
        try:
            roots = ctx_bootstrap.candidate_roots()
        finally:
            if real_core is None:
                sys.modules.pop('core', None)
            else:
                sys.modules['core'] = real_core

        self.assertNotIn(_norm(os.path.dirname(other_core)), roots)


class TestClearBytecode(_TempDirTestCase):

    def test_removes_pycache_and_orphaned_pyc_only(self):
        pkg = os.path.join(self.tmp, 'pkg')
        _touch(os.path.join(pkg, '__pycache__', 'mod.cpython-37.pyc'))
        _touch(os.path.join(pkg, 'kept.py'))
        _touch(os.path.join(pkg, 'kept.pyc'))       # has its source
        _touch(os.path.join(pkg, 'orphan.pyc'))     # source was deleted
        _touch(os.path.join(self.tmp, '.git', 'hooks', 'x.pyc'))

        ctx_bootstrap.clear_bytecode(self.tmp)

        self.assertFalse(os.path.exists(os.path.join(pkg, '__pycache__')))
        self.assertTrue(os.path.exists(os.path.join(pkg, 'kept.pyc')))
        self.assertFalse(os.path.exists(os.path.join(pkg, 'orphan.pyc')))
        self.assertTrue(os.path.exists(
            os.path.join(self.tmp, '.git', 'hooks', 'x.pyc')))


class TestRunScript(_TempDirTestCase):

    def test_script_gets_its_own_file_and_globals(self):
        script = os.path.join(self.tmp, 'launcher.py')
        _touch(script, (
            "SEEN_FILE = __file__\n"
            "SEEN_NAME = __name__\n"
            "def helper():\n"
            "    return SEEN_FILE\n"
            "RESULT = helper()\n"
        ))

        namespace = ctx_bootstrap.run_script(script)

        self.assertEqual(_norm(namespace['SEEN_FILE']), _norm(script))
        # Functions defined by the script must see the script's globals.
        self.assertEqual(_norm(namespace['RESULT']), _norm(script))
        self.assertEqual(namespace['SEEN_NAME'], '__main__')


if __name__ == '__main__':
    unittest.main()
