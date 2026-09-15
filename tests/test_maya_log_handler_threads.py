# -*- coding: utf-8 -*-
"""Maya log handler must not call MGlobal from worker threads.

Plain unittest with no mock, so it also runs under Maya's Python 2.7:
    mayapy2 -m unittest tests.test_maya_log_handler_threads
"""

from __future__ import absolute_import, division, print_function

import logging
import os
import sys
import threading
import unittest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core import logging_config


class _FakeMGlobal(object):
    def __init__(self):
        self.calls = []

    def _record(self, kind, msg):
        self.calls.append((kind, msg, threading.current_thread().name))

    def displayInfo(self, msg):
        self._record('info', msg)

    def displayWarning(self, msg):
        self._record('warning', msg)

    def displayError(self, msg):
        self._record('error', msg)


def _handler():
    handler = logging_config._MayaOutputHandler()
    handler._available = True
    handler._mglobal = _FakeMGlobal()
    handler.deferred = []
    handler._defer = lambda fn, *args: handler.deferred.append((fn, args))
    handler.setFormatter(logging.Formatter('%(message)s'))
    return handler


def _record(level, msg):
    return logging.LogRecord('ctx_tools.test', level, __file__, 1, msg, None, None)


class TestMayaOutputHandlerThreads(unittest.TestCase):

    def test_main_thread_displays_immediately(self):
        handler = _handler()
        handler.emit(_record(logging.INFO, 'hello'))
        handler.emit(_record(logging.WARNING, 'careful'))
        handler.emit(_record(logging.ERROR, 'broken'))

        self.assertEqual([c[:2] for c in handler._mglobal.calls],
                         [('info', 'hello'), ('warning', 'careful'), ('error', 'broken')])
        self.assertEqual(handler.deferred, [])

    def test_worker_thread_is_deferred_not_displayed(self):
        handler = _handler()
        worker = threading.Thread(
            target=handler.emit, args=(_record(logging.INFO, 'from render thread'),))
        worker.start()
        worker.join()

        self.assertEqual(handler._mglobal.calls, [],
                         'MGlobal was called from a worker thread')
        self.assertEqual(len(handler.deferred), 1)

        # Running the deferred call (Maya does this on its main thread) displays it.
        fn, args = handler.deferred[0]
        fn(*args)
        self.assertEqual([c[:2] for c in handler._mglobal.calls],
                         [('info', 'from render thread')])


if __name__ == '__main__':
    unittest.main()
