"""Session render state registry.

Tracks render status for shots in the current Maya session.
Not persisted to disk -- cleared on scene open/new.
"""

from __future__ import absolute_import, division, print_function

from core.logging_config import get_logger

logger = get_logger(__name__)

# Module-level state: { shot_id: status_string }
_state = {}

# Notify callbacks: list of callables accepting (shot_id, status)
_callbacks = []

QUEUED = 'queued'
RENDERING = 'rendering'
DONE = 'done'
FAILED = 'failed'
CANCELLED = 'cancelled'


def set_status(shot_id, status):
    """Set render status for a shot and notify listeners.

    Args:
        shot_id (str): Shot identifier (ep_seq_shot).
        status (str): One of the module-level constants.
    """
    _state[shot_id] = status
    logger.debug("Render state: %s -> %s", shot_id, status)
    _notify(shot_id, status)


def get_status(shot_id):
    """Return render status for a shot, or None if not tracked.

    Args:
        shot_id (str): Shot identifier.

    Returns:
        str|None
    """
    return _state.get(shot_id)


def clear():
    """Clear all tracked state. Called on scene open/new."""
    _state.clear()
    logger.debug("Render state cleared")


def add_listener(callback):
    """Register a callback to be called on any status change.

    Args:
        callback (callable): Called with (shot_id, status).
    """
    if callback not in _callbacks:
        _callbacks.append(callback)


def remove_listener(callback):
    """Unregister a callback.

    Args:
        callback (callable): Previously registered callback.
    """
    if callback in _callbacks:
        _callbacks.remove(callback)


def _notify(shot_id, status):
    """Invoke all registered listeners."""
    for cb in list(_callbacks):
        try:
            cb(shot_id, status)
        except Exception as exc:
            logger.warning("Render state listener error: %s", exc)
