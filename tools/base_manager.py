# -*- coding: utf-8 -*-
"""Base manager module for Context Variables Pipeline tools.

Provides shared infrastructure used by all tool managers:
- MAYA_AVAILABLE flag
- MockCmds for testing without Maya
- BaseManager base class with dependency-injected cmds
"""

from __future__ import absolute_import
from __future__ import print_function

try:
    import maya.cmds as _maya_cmds
    MAYA_AVAILABLE = True
except ImportError:
    _maya_cmds = None
    MAYA_AVAILABLE = False


class MockCmds(object):
    """Mock Maya commands for testing without Maya installed."""

    def objExists(self, name):
        return False

    def createNode(self, node_type, name=None, **kwargs):
        return name or node_type

    def delete(self, *args, **kwargs):
        pass

    def getAttr(self, attr, **kwargs):
        return None

    def setAttr(self, attr, *args, **kwargs):
        pass

    def addAttr(self, node, **kwargs):
        pass

    def connectAttr(self, src, dst, **kwargs):
        pass

    def listConnections(self, attr, **kwargs):
        return []

    def ls(self, *args, **kwargs):
        return []

    def attributeQuery(self, attr, **kwargs):
        return False


if MAYA_AVAILABLE:
    cmds = _maya_cmds
else:
    cmds = MockCmds()


class BaseManager(object):
    """Base class for all tool managers.

    Provides dependency-injected cmds so subclasses work in tests without Maya.

    Usage:
        class ShotManager(BaseManager):
            def __init__(self, ...):
                super(ShotManager, self).__init__()
                ...
    """

    def __init__(self, cmds_override=None):
        """Initialize base manager.

        Args:
            cmds_override: Optional Maya cmds replacement (used in tests).
        """
        if cmds_override is not None:
            self._cmds = cmds_override
        else:
            self._cmds = cmds

