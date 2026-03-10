# Stream 6-G — Slate Originals: CTXSlateOriginalsNode

**Status:** Not Started
**Round:** 4 (implement alongside 6-F Round 4 fixes)
**Branch:** `feature/phase6-lock-slate`
**Dependencies:** Stream 6-D (SlateResolver)

---

## Goal

Create a singleton Maya node that stores the **original renderable state** of every
render layer in the scene, captured once before any slate override is applied.

This mirrors the gaffer `CTXLightOriginalsNode` system exactly:

| Gaffer Originals | Slate Originals |
|---|---|
| `CTXLightOriginalsNode` | `CTXSlateOriginalsNode` |
| Singleton network node per scene | Singleton network node per scene |
| `originalsJson` string attr | `originalsJson` string attr |
| `{light_shape: {intensity, color, ...}}` | `{layer_name: renderable_bool}` |
| Captured once on first `add_light_to_gaffer()` | Captured once on first `apply_to_scene()` call |
| Used by resolver for additive mode + restore | Used by resolver to restore when no slate / on cancel |

---

## 1. `core/nodes/schemas/slate_originals.py` — NEW FILE

```python
"""Schema for CTX_SlateOriginals node.

Singleton node per scene. Stores the renderable state of all render layers
before any slate override is applied.
"""

from ..base import NodeSchema


class CTXSlateOriginalsSchema(NodeSchema):
    NODE_TYPE = "network"
    NODE_PREFIX = "CTX_SlateOriginals"
    CATEGORY = "Context"
    DESCRIPTION = "Singleton: stores original render layer renderable states"

    ATTRIBUTES = {
        'ctx_type': {
            'type': 'string',
            'default': 'CTX_SlateOriginals',
        },
        'originalsJson': {
            'type': 'string',
            'default': '{}',
            'description': 'JSON dict: {layer_name: renderable_bool}',
        },
    }

    CONNECTIONS = {}
```

---

## 2. `core/nodes/wrappers/slate_originals.py` — NEW FILE

```python
"""Wrapper for CTX_SlateOriginals singleton node.

Stores and retrieves the original renderable state of render layers
before any slate override is applied. Mirrors CTXLightOriginalsNode.
"""

from __future__ import absolute_import

import json

try:
    import maya.cmds as cmds
except ImportError:
    cmds = None

from ..base import NodeWrapper
from ..schemas.slate_originals import CTXSlateOriginalsSchema
from core.logging_config import get_logger

logger = get_logger(__name__)


class CTXSlateOriginalsNode(NodeWrapper):
    """Singleton per-scene node storing original render layer renderable states."""

    SCHEMA = CTXSlateOriginalsSchema

    @classmethod
    def get_or_create(cls):
        """Return the existing originals node or create one.

        Returns:
            CTXSlateOriginalsNode: The singleton node.
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        # Find existing node
        existing = cmds.ls(type='network') or []
        for node in existing:
            try:
                if cmds.attributeQuery('ctx_type', node=node, exists=True):
                    if cmds.getAttr('{}.ctx_type'.format(node)) == 'CTX_SlateOriginals':
                        return cls(node)
            except Exception:
                continue

        # Create new singleton
        from ..base import NodeFactory
        node_name = NodeFactory.create_from_schema(cls.SCHEMA())
        logger.info("Created CTXSlateOriginalsNode: %s", node_name)
        return cls(node_name)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load(self):
        """Read and parse the stored JSON dict."""
        raw = cmds.getAttr('{}.originalsJson'.format(self.node_name)) or '{}'
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return {}

    def _save(self, data):
        """Serialize and write the JSON dict."""
        cmds.setAttr(
            '{}.originalsJson'.format(self.node_name),
            json.dumps(data),
            type='string',
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def has_layer(self, layer_name):
        """Return True if the original state for this layer is stored.

        Args:
            layer_name (str): Render layer name.

        Returns:
            bool
        """
        return layer_name in self._load()

    def store_layer(self, layer_name, renderable):
        """Store the original renderable state for a render layer.

        Should be called only once per layer (before any slate override).
        Subsequent calls are no-ops if the layer is already stored.

        Args:
            layer_name (str): Render layer name.
            renderable (bool): Original renderable state.
        """
        data = self._load()
        if layer_name not in data:
            data[layer_name] = bool(renderable)
            self._save(data)
            logger.debug("Stored original renderable for %r: %s", layer_name, renderable)

    def get_layer_renderable(self, layer_name):
        """Return the original renderable state for a layer, or None if not stored.

        Args:
            layer_name (str): Render layer name.

        Returns:
            bool|None
        """
        return self._load().get(layer_name)

    def get_all(self):
        """Return the full {layer_name: renderable_bool} dict.

        Returns:
            dict
        """
        return self._load()

    def clear(self):
        """Remove all stored originals (use with caution — one-way operation)."""
        self._save({})
        logger.warning("CTXSlateOriginalsNode cleared")
```

---

## 3. `core/nodes/wrappers/__init__.py` — Add Export

```python
from .slate_originals import CTXSlateOriginalsNode
```

---

## 4. `SlateResolver.apply_to_scene()` — Capture Before Override

In `core/slate/resolver.py`, modify `apply_to_scene()` to:

1. **Before applying any override**: snapshot the current renderable state into `CTXSlateOriginalsNode` for layers not yet stored.
2. **When no override exists** for a layer: restore it to the original value from the originals node (instead of leaving it unchanged).

```python
@staticmethod
def apply_to_scene(shot_or_seq_node):
    """Resolve the slate chain and apply renderable flags to Maya Render Setup.

    Captures originals before first application. Restores originals for
    layers with no override in any slate (same behaviour as gaffer restore).
    """
    if not MAYA_AVAILABLE:
        return

    resolved = SlateResolver.resolve_layer_state(shot_or_seq_node)
    if not resolved:
        return

    try:
        from maya.app.renderSetup.model import renderSetup as rs_module
        rs = rs_module.instance()
    except Exception as exc:
        logger.warning("Render Setup not available: %s", exc)
        return

    # Get originals node (create if needed)
    try:
        from core.nodes.wrappers.slate_originals import CTXSlateOriginalsNode
        originals_node = CTXSlateOriginalsNode.get_or_create()
    except Exception as exc:
        logger.warning("Could not access SlateOriginals node: %s", exc)
        originals_node = None

    for layer_name, state in resolved.items():
        try:
            layer = rs.getRenderLayer(layer_name)
            if layer is None:
                logger.warning("Slate apply: layer %r not found in scene", layer_name)
                continue

            # Capture original state before first override (mirrors gaffer originals)
            if originals_node is not None and not originals_node.has_layer(layer_name):
                try:
                    current_renderable = layer.isRenderable()
                    originals_node.store_layer(layer_name, current_renderable)
                except Exception as exc:
                    logger.warning("Failed to capture original for %r: %s", layer_name, exc)

            if state['overridden']:
                layer.setRenderable(state['renderable'])
                logger.debug(
                    "Slate: set %r renderable=%s (source=%s)",
                    layer_name, state['renderable'], state['source']
                )
            else:
                # No override in chain — restore to original
                if originals_node is not None:
                    original = originals_node.get_layer_renderable(layer_name)
                    if original is not None:
                        layer.setRenderable(original)
                        logger.debug(
                            "Slate: restored %r to original renderable=%s",
                            layer_name, original
                        )

        except Exception as exc:
            logger.warning("Failed to apply slate for layer %r: %s", layer_name, exc)
```

---

## 5. Restore on Shot With No Slate

Add a `SlateResolver.restore_originals()` static method — called when switching to a shot with no slate (mirrors `_restore_light_originals()` in MainWindow):

```python
@staticmethod
def restore_originals():
    """Restore all render layers to their original renderable state.

    Called when switching to a shot that has no slate at any level.
    Mirrors GafferManager's restore-originals behavior.
    """
    if not MAYA_AVAILABLE:
        return

    try:
        from core.nodes.wrappers.slate_originals import CTXSlateOriginalsNode
        originals_node = CTXSlateOriginalsNode.get_or_create()
        originals = originals_node.get_all()
    except Exception as exc:
        logger.warning("restore_originals: could not load SlateOriginals: %s", exc)
        return

    if not originals:
        return

    try:
        from maya.app.renderSetup.model import renderSetup as rs_module
        rs = rs_module.instance()
    except Exception as exc:
        logger.warning("Render Setup not available: %s", exc)
        return

    for layer_name, renderable in originals.items():
        try:
            layer = rs.getRenderLayer(layer_name)
            if layer is not None:
                layer.setRenderable(renderable)
                logger.debug("Restored %r renderable=%s", layer_name, renderable)
        except Exception as exc:
            logger.warning("Failed to restore layer %r: %s", layer_name, exc)
```

---

## 6. `ui/main_window.py` — Call `restore_originals()` on shot switch

In `_on_set_shot()`, after applying the slate chain, add restore call for shots with no slate:

```python
# Existing slate apply block (in _on_set_shot):
try:
    from core.slate.resolver import SlateResolver
    if shot_node is not None:
        from core.slate.resolver import SlateResolver as _SR
        slate = shot_node.get_slate()
        if slate is not None or _SR._get_slate_for_node(shot_node) is not None:
            _SR.apply_to_scene(shot_node)
        else:
            _SR.restore_originals()   # No slate at any level — restore originals
except Exception as exc:
    logger.warning("Slate apply failed (non-fatal): %s", exc)
```

---

## Completion Criteria

- [ ] `core/nodes/schemas/slate_originals.py` created
- [ ] `core/nodes/wrappers/slate_originals.py` created with `get_or_create()`, `store_layer()`, `get_layer_renderable()`, `has_layer()`, `restore_all()`
- [ ] `CTXSlateOriginalsNode` exported from `core/nodes/wrappers/__init__.py`
- [ ] `SlateResolver.apply_to_scene()` captures originals before first override
- [ ] `SlateResolver.apply_to_scene()` restores originals for non-overridden layers
- [ ] `SlateResolver.restore_originals()` static method added
- [ ] `ui/main_window.py` calls `restore_originals()` when shot has no slate
- [ ] Tests: `tests/test_slate_originals.py` — min 10 tests covering get_or_create, store, retrieve, has_layer, restore
