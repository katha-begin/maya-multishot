"""LockManager -- application-level and Maya-attribute-level node locking.

Two enforcement layers:
  1. Application layer: sets is_locked=True on the CTX node.
     UI code checks this flag before allowing edits.
  2. Maya attribute layer: calls cmds.setAttr(lock=True) on key
     attributes of the CTX node to prevent direct Attribute Editor edits.

Lock cascade:
  lock_sequence() locks the sequence node and, with cascade=True (default),
  locks all CTX_Shot nodes connected to that sequence. Artists see the lock
  on both the sequence row and every shot row under it.
"""

from __future__ import absolute_import, division, print_function

import os

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False

from core.logging_config import get_logger

logger = get_logger(__name__)


# Key attributes to lock/unlock at the Maya attribute level, per node ctx_type.
# These are the fields most likely to be accidentally edited via Attribute Editor.
_MAYA_LOCK_ATTRS = {
    'CTX_Shot': ['ep_code', 'seq_code', 'shot_code', 'start_frame', 'end_frame'],
    'CTX_Sequence': ['sequenceCode', 'frameStart', 'frameEnd'],
    'CTX_LightGaffer': ['gafferName', 'gafferType', 'scopeCode'],
    'CTX_Asset': ['file_path', 'version', 'asset_name', 'asset_type'],
}


class LockManager(object):

    @staticmethod
    def lock_node(node, user=None):
        """Lock a CTX node.

        Sets is_locked=True, records locked_by and locked_at.
        Applies Maya attribute-level locks on key fields.

        Args:
            node (str): Maya node name (CTX node).
            user (str|None): Username. Defaults to os.getenv('USERNAME') or 'unknown'.
        """
        if not MAYA_AVAILABLE:
            logger.warning("Maya not available -- skipping Maya attr lock for %s", node)
            return

        if not cmds.objExists(node):
            logger.warning("lock_node: node does not exist: %s", node)
            return

        import datetime
        user = user or os.getenv('USERNAME') or os.getenv('USER') or 'unknown'
        timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

        try:
            cmds.setAttr('{}.is_locked'.format(node), True)
            cmds.setAttr('{}.locked_by'.format(node), user, type='string')
            cmds.setAttr('{}.locked_at'.format(node), timestamp, type='string')
        except RuntimeError as exc:
            logger.error("Failed to set lock attributes on %s: %s", node, exc)
            return

        LockManager._apply_maya_attr_locks(node, lock=True)
        logger.info("Locked node %s (by %s at %s)", node, user, timestamp)

    @staticmethod
    def unlock_node(node):
        """Unlock a CTX node.

        Clears is_locked, locked_by, locked_at.
        Removes Maya attribute-level locks on key fields.

        Args:
            node (str): Maya node name (CTX node).
        """
        if not MAYA_AVAILABLE:
            return

        if not cmds.objExists(node):
            logger.warning("unlock_node: node does not exist: %s", node)
            return

        LockManager._apply_maya_attr_locks(node, lock=False)

        try:
            cmds.setAttr('{}.is_locked'.format(node), False)
            cmds.setAttr('{}.locked_by'.format(node), '', type='string')
            cmds.setAttr('{}.locked_at'.format(node), '', type='string')
        except RuntimeError as exc:
            logger.error("Failed to clear lock attributes on %s: %s", node, exc)
            return

        logger.info("Unlocked node %s", node)

    @staticmethod
    def is_locked(node):
        """Return True if the CTX node has is_locked=True.

        Args:
            node (str): Maya node name.

        Returns:
            bool: True if locked.
        """
        if not MAYA_AVAILABLE:
            return False
        if not cmds.objExists(node):
            return False
        try:
            return bool(cmds.getAttr('{}.is_locked'.format(node)))
        except Exception:
            return False

    @staticmethod
    def get_lock_info(node):
        """Return lock state and metadata for a CTX node.

        Args:
            node (str): Maya node name.

        Returns:
            dict: {
                'is_locked': bool,
                'locked_by': str,
                'locked_at': str,
            }
        """
        result = {'is_locked': False, 'locked_by': '', 'locked_at': ''}
        if not MAYA_AVAILABLE or not cmds.objExists(node):
            return result
        try:
            result['is_locked'] = bool(cmds.getAttr('{}.is_locked'.format(node)))
            result['locked_by'] = cmds.getAttr('{}.locked_by'.format(node)) or ''
            result['locked_at'] = cmds.getAttr('{}.locked_at'.format(node)) or ''
        except Exception:
            pass
        return result

    @staticmethod
    def lock_sequence(seq_node, user=None, cascade=True):
        """Lock a CTX_Sequence node and optionally all shots under it.

        Args:
            seq_node (str): CTX_Sequence Maya node name.
            user (str|None): Username. Defaults to environment variable.
            cascade (bool): If True, also lock all CTX_Shot nodes connected
                            to this sequence. Default True.
        """
        LockManager.lock_node(seq_node, user=user)

        if cascade:
            shot_nodes = LockManager._get_shots_under_sequence(seq_node)
            for shot in shot_nodes:
                LockManager.lock_node(shot, user=user)
            logger.info(
                "Cascaded lock to %d shot(s) under sequence %s",
                len(shot_nodes), seq_node
            )

    @staticmethod
    def unlock_sequence(seq_node, cascade=True):
        """Unlock a CTX_Sequence node and optionally all shots under it.

        Args:
            seq_node (str): CTX_Sequence Maya node name.
            cascade (bool): If True, also unlock all CTX_Shot nodes connected
                            to this sequence. Default True.
        """
        LockManager.unlock_node(seq_node)

        if cascade:
            shot_nodes = LockManager._get_shots_under_sequence(seq_node)
            for shot in shot_nodes:
                LockManager.unlock_node(shot)
            logger.info(
                "Cascaded unlock to %d shot(s) under sequence %s",
                len(shot_nodes), seq_node
            )

    @staticmethod
    def is_effectively_locked(shot_node):
        """Return True if a shot is locked directly OR via its parent sequence.

        This is the method UI code should call for shot rows.

        Args:
            shot_node (str): CTX_Shot Maya node name.

        Returns:
            bool: True if locked by any means.
        """
        if LockManager.is_locked(shot_node):
            return True

        # Walk up to parent sequence
        seq_node = LockManager._get_parent_sequence(shot_node)
        if seq_node and LockManager.is_locked(seq_node):
            return True

        return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_maya_attr_locks(node, lock):
        """Apply or remove Maya attribute-level locks on key fields.

        Reads the node's ctx_type to select which attributes to lock.
        Silently skips attributes that do not exist on the node.

        Args:
            node (str): Maya node name.
            lock (bool): True = lock, False = unlock.
        """
        if not MAYA_AVAILABLE:
            return

        try:
            ctx_type = cmds.getAttr('{}.ctx_type'.format(node))
        except Exception:
            return

        attrs = _MAYA_LOCK_ATTRS.get(ctx_type, [])
        for attr in attrs:
            full = '{}.{}'.format(node, attr)
            try:
                if cmds.attributeQuery(attr, node=node, exists=True):
                    cmds.setAttr(full, lock=lock)
            except Exception as exc:
                logger.debug(
                    "Could not %s attr %s: %s",
                    'lock' if lock else 'unlock',
                    full,
                    exc
                )

    @staticmethod
    def _get_shots_under_sequence(seq_node):
        """Return list of CTX_Shot node names connected to a sequence.

        Args:
            seq_node (str): CTX_Sequence Maya node name.

        Returns:
            list[str]: Shot node names.
        """
        if not MAYA_AVAILABLE:
            return []
        try:
            connected = cmds.listConnections(
                '{}.shots'.format(seq_node),
                source=True,
                destination=False,
            ) or []
            return list(set(connected))
        except Exception:
            return []

    @staticmethod
    def _get_parent_sequence(shot_node):
        """Return the CTX_Sequence node that owns this shot, or None.

        Args:
            shot_node (str): CTX_Shot Maya node name.

        Returns:
            str|None: Sequence node name or None.
        """
        if not MAYA_AVAILABLE:
            return None
        try:
            connected = cmds.listConnections(
                '{}.message'.format(shot_node),
                source=False,
                destination=True,
                plugs=True,
            ) or []
            for plug in connected:
                node_name = plug.split('.')[0]
                try:
                    ctx_type = cmds.getAttr('{}.ctx_type'.format(node_name))
                    if ctx_type == 'CTX_Sequence':
                        return node_name
                except Exception:
                    continue
        except Exception:
            pass
        return None
