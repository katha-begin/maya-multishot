# -*- coding: utf-8 -*-
"""Find, refresh and launch this CTX Tools install -- wherever it lives.

The tool can be cloned anywhere (a dev drive, a studio share). Everything that
needs to know where that is, or needs a clean re-import after the files on
disk change, goes through here:

- REPO_ROOT         this checkout's folder, derived from this file
- purge_modules()   drop the tool's modules from sys.modules so the next
                    import reads the files on disk
- clear_bytecode()  delete __pycache__ folders (Python 3) and orphaned .pyc
                    files (Python 2 keeps importing a .pyc whose .py is gone)
- run_script(path)  run a launch_*.py script with its own __file__

Modules are purged by where their files live, never by package name: "core",
"ui", "tools" and "config" are common names, and other studio tools using
them must keep working.

Works on Python 2.7 and 3.x. Imports nothing from the repo, so launch scripts
can load it before any of the tool's own packages.
"""

from __future__ import absolute_import, division, print_function

import os
import shutil
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

# Top-level packages that make up the tool.
PACKAGES = ('core', 'ui', 'tools', 'config')


def _norm(path):
    return os.path.normcase(os.path.abspath(path))


def is_repo_root(path):
    """Return True if ``path`` is a CTX Tools checkout, of any version."""
    return (os.path.isfile(os.path.join(path, 'tools', 'maya_menu.py')) and
            os.path.isdir(os.path.join(path, 'core', 'gaffer')))


def candidate_roots(root=None):
    """Return the normalised checkout folders whose modules belong to the tool.

    That is ``root`` (default: this checkout) plus the checkout of any CTX
    package already loaded -- e.g. an older copy imported earlier in the
    session from another folder, which would otherwise shadow this one.
    """
    roots = set([_norm(root or REPO_ROOT)])
    for name in PACKAGES:
        module = sys.modules.get(name)
        for package_dir in getattr(module, '__path__', None) or []:
            parent = os.path.dirname(os.path.abspath(package_dir))
            if is_repo_root(parent):
                roots.add(_norm(parent))
    return roots


def purge_modules(roots=None):
    """Remove the tool's modules from sys.modules.

    The next import of any of them reads the files on disk again. Objects
    that already hold the old modules (open windows, menu callbacks) keep
    running the old code until they are recreated.

    Args:
        roots (iterable): Checkout folders to purge. Default: candidate_roots().

    Returns:
        list: Sorted names of the purged modules.
    """
    if roots is None:
        roots = candidate_roots()
    prefixes = [_norm(root).rstrip(os.sep) + os.sep for root in roots]

    purged = []
    for name, module in list(sys.modules.items()):
        if name == '__main__':
            continue
        try:
            path = getattr(module, '__file__', None)
        except Exception:
            continue  # lazy/proxy modules from other tools
        if not path:
            continue
        path = _norm(path)
        if any(path.startswith(prefix) for prefix in prefixes):
            del sys.modules[name]
            purged.append(name)
    return sorted(purged)


def clear_bytecode(root=None):
    """Delete compiled bytecode that could shadow the .py files.

    Removes every __pycache__ folder (Python 3) and every .pyc/.pyo whose .py
    no longer exists (Python 2 imports such an orphan as if the module still
    existed). A .pyc next to its .py is left alone -- Python 2 recompiles it
    when the source changes.

    Returns:
        int: Number of folders and files removed.
    """
    root = root or REPO_ROOT
    removed = 0
    for dirpath, dirnames, filenames in os.walk(root):
        if '.git' in dirnames:
            dirnames.remove('.git')
        if '__pycache__' in dirnames:
            dirnames.remove('__pycache__')
            shutil.rmtree(os.path.join(dirpath, '__pycache__'), ignore_errors=True)
            removed += 1
        for filename in filenames:
            if not filename.endswith(('.pyc', '.pyo')):
                continue
            if os.path.exists(os.path.join(dirpath, filename[:-1])):
                continue
            try:
                os.remove(os.path.join(dirpath, filename))
                removed += 1
            except OSError:
                pass  # held open by another Maya session; harmless
    return removed


def prepare(root=None):
    """Clear stale bytecode and the tool's loaded modules before re-importing.

    Returns:
        list: Names of the purged modules.
    """
    clear_bytecode(root)
    return purge_modules(candidate_roots(root))


def run_script(path):
    """Run a launch script as if it had been started as a file.

    The script gets its own globals with ``__file__`` set to its path, so it
    can find the repo, and functions it defines see its own top-level names.
    A bare exec() inside a function would instead hand it the caller's
    globals -- including the caller's ``__file__``.

    Returns:
        dict: The script's globals after it ran.
    """
    path = os.path.abspath(path)
    with open(path, 'rb') as handle:
        # dont_inherit: the script's own __future__ imports apply, not ours
        code = compile(handle.read(), path, 'exec', 0, True)
    namespace = {'__file__': path, '__name__': '__main__'}
    exec(code, namespace)
    return namespace
