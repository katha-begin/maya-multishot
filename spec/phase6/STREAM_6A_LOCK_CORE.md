# Stream 6-A — Lock Core: Mixin, LockManager, Schema Changes

**Status:** Not Started
**Round:** 1 (parallel with 6-C)
**Branch:** `feature/phase6-lock-slate`
**Dependencies:** None

---

## Goal

Build the data layer for the Lock / Read-Only system. No UI in this stream.
Three deliverables: `LockSchemaMixin` (reusable schema mixin), `LockManager`
(lock/unlock operations with Maya attribute enforcement), and schema changes to
inject lock attributes into Shot, Sequence, Gaffer, and Asset nodes.

---

## Background — Maya Lock Mechanics

Two distinct Maya lock mechanisms exist:

**Full node lock (`cmds.lockNode`):**
- Locks the entire Maya node — no attributes changeable, no connections addable, node cannot be deleted.
- Dangerous: locked reference nodes may be unrecoverable. **Do not use for CTX nodes.**

**Attribute-level lock (`cmds.setAttr("node.attr", lock=True)`):**
- Locks one specific attribute. All other attributes on the node remain editable.
- Safe and reversible: `cmds.setAttr("node.attr", lock=False)` to unlock.
- This is the correct primitive for CTX lock enforcement.

The system uses two enforcement layers:
1. **Application layer (primary):** `is_locked=True` → UI disables all editing widgets.
2. **Maya attribute layer (secondary):** `cmds.setAttr(lock=True)` on key attributes prevents
   direct Attribute Editor edits from bypassing the UI.

---

## 1. `core/nodes/schemas/lock_mixin.py` — NEW FILE

```python
"""Lock mixin for CTX node schemas.

Adds is_locked, locked_by, and locked_at attributes to any schema
that inherits this mixin. Mixed in before NodeSchema in MRO.
"""


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
```

**Integration note:** The schema base class (`NodeSchema`) must be updated to merge
`LOCK_ATTRIBUTES` from any mixin into the full attribute set during `ensure_node_attributes()`.
Read `core/nodes/schemas/base.py` before editing to understand the existing merge pattern.

---

## 2. `core/lock_manager.py` — NEW FILE

```python
"""LockManager — application-level and Maya-attribute-level node locking.

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
            logger.warning("Maya not available — skipping Maya attr lock for %s", node)
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
                if cmds.objExists(full) or cmds.attributeQuery(attr, node=node, exists=True):
                    cmds.setAttr(full, lock=lock)
            except Exception as exc:
                logger.debug("Could not %s attr %s: %s", 'lock' if lock else 'unlock', full, exc)

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
```

---

## 3. Schema Changes — Existing Files

### `core/nodes/schemas/shot.py`

Read the file first. Add `LockSchemaMixin` to the inheritance chain:

```python
# Before
class CTXShotSchema(NodeSchema):

# After
from core.nodes.schemas.lock_mixin import LockSchemaMixin

class CTXShotSchema(LockSchemaMixin, NodeSchema):
```

Then merge `LOCK_ATTRIBUTES` into `ATTRIBUTES` in `ensure_node_attributes()` (or wherever the
schema applies its attribute dict — read the base class pattern first).

### `core/nodes/schemas/sequence.py`

Same change:
```python
from core.nodes.schemas.lock_mixin import LockSchemaMixin

class CTXSequenceSchema(LockSchemaMixin, NodeSchema):
```

### `core/nodes/schemas/gaffer.py`

```python
from core.nodes.schemas.lock_mixin import LockSchemaMixin

class CTXLightGafferSchema(LockSchemaMixin, NodeSchema):
```

### `core/nodes/schemas/asset.py`

```python
from core.nodes.schemas.lock_mixin import LockSchemaMixin

class CTXAssetSchema(LockSchemaMixin, NodeSchema):
```

**Important:** Read each file before editing. Do not remove any existing attributes or
change any existing logic. Only add the mixin inheritance and ensure lock attributes
are created on the Maya node.

---

## 4. Wrapper Additions

### `core/nodes/wrappers/shot.py` — add convenience methods

```python
def lock(self, user=None):
    """Lock this shot node."""
    from core.lock_manager import LockManager
    LockManager.lock_node(self.node_name, user=user)

def unlock(self):
    """Unlock this shot node."""
    from core.lock_manager import LockManager
    LockManager.unlock_node(self.node_name)

def is_locked(self):
    """Return True if this shot is locked directly or via its sequence."""
    from core.lock_manager import LockManager
    return LockManager.is_effectively_locked(self.node_name)

def get_lock_info(self):
    """Return lock metadata dict."""
    from core.lock_manager import LockManager
    return LockManager.get_lock_info(self.node_name)
```

Add equivalent `lock()`, `unlock()`, `is_locked()`, `get_lock_info()` to
`CTXSequenceNode`, `CTXLightGafferNode`, and `CTXAssetNode` wrappers.

---

## Tests — `tests/test_lock_manager.py`

```python
# test_lock_mixin_attributes_exist
#   — LockSchemaMixin has LOCK_ATTRIBUTES with is_locked/locked_by/locked_at

# test_lock_manager_lock_node_mock
#   — mock cmds; lock_node sets is_locked=True, locked_by, locked_at

# test_lock_manager_unlock_node_mock
#   — mock cmds; unlock_node clears all three attributes

# test_is_locked_returns_false_when_no_maya
#   — MAYA_AVAILABLE=False; is_locked returns False

# test_get_lock_info_returns_defaults_when_no_maya
#   — returns {'is_locked': False, 'locked_by': '', 'locked_at': ''}

# test_is_effectively_locked_direct
#   — shot directly locked; is_effectively_locked returns True

# test_is_effectively_locked_via_sequence
#   — shot not locked, seq locked; is_effectively_locked returns True

# test_is_effectively_locked_neither
#   — neither locked; returns False

# test_lock_sequence_cascade
#   — lock_sequence locks seq + all shots under it

# test_unlock_sequence_cascade
#   — unlock_sequence unlocks seq + all shots

# test_lock_sequence_no_cascade
#   — cascade=False; only seq locked, shots untouched
```

---

## Completion Criteria

- [ ] `core/nodes/schemas/lock_mixin.py` created
- [ ] `core/lock_manager.py` created — all 7 public methods implemented
- [ ] `CTXShotSchema` inherits `LockSchemaMixin`
- [ ] `CTXSequenceSchema` inherits `LockSchemaMixin`
- [ ] `CTXLightGafferSchema` inherits `LockSchemaMixin`
- [ ] `CTXAssetSchema` inherits `LockSchemaMixin`
- [ ] Lock/unlock/is_locked convenience methods added to all 4 wrappers
- [ ] All tests pass
- [ ] No regressions in existing test suite
