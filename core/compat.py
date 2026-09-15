# -*- coding: utf-8 -*-
"""Python 2.7 / 3.x compatibility helpers.

Maya 2019-2021, and Maya 2022 started in Python 2 mode, run Python 2.7. There,
maya.cmds, PySide2 and json all return ``unicode`` rather than ``str``, so a
plain ``isinstance(name, str)`` check rejects every node name. Use
``string_types`` for such checks instead.
"""

from __future__ import absolute_import, division, print_function

import errno
import os
import threading

try:
    string_types = (basestring,)  # noqa: F821 -- Python 2 only
except NameError:
    string_types = (str,)


def makedirs(path):
    """Create ``path`` and any missing parents; an existing folder is fine.

    Same as ``os.makedirs(path, exist_ok=True)``, which Python 2 lacks.

    Raises:
        OSError: If the folder cannot be created, or ``path`` is a file.
    """
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno != errno.EEXIST or not os.path.isdir(path):
            raise


def is_main_thread():
    """Return True when called on the interpreter's main thread.

    ``threading.main_thread()`` only exists on Python 3.4+.
    """
    main_thread = getattr(threading, 'main_thread', None)
    if main_thread is not None:
        return threading.current_thread() is main_thread()
    return isinstance(threading.current_thread(), threading._MainThread)
