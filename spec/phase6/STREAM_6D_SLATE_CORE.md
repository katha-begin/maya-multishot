# Stream 6-D — Slate Core: SlateManager, SlateResolver, Shot-Switch Integration

**Status:** Not Started
**Round:** 2 (after 6-C)
**Branch:** `feature/phase6-lock-slate`
**Dependencies:** Stream 6-C (CTXSlateNode, CTXSlateLayerNode, connection methods)

---

## Goal

Build the operational logic for the Slate system. Three deliverables:
`SlateManager` (creates and wires slate nodes), `SlateResolver` (resolves
the inheritance chain and applies renderable state to Maya), and integration
into the shot-switch flow in `main_window.py`.

Read `core/gaffer/manager.py`, `core/gaffer/resolver.py`, and
`core/gaffer/chain_ops.py` as reference patterns before writing any code.
The slate core mirrors these files exactly in structure.

---

## 1. `core/slate/__init__.py` — NEW FILE

```python
"""Slate Manager package — per-shot render layer control."""

from core.slate.manager import SlateManager
from core.slate.resolver import SlateResolver
```

---

## 2. `core/slate/manager.py` — NEW FILE

```python
"""SlateManager — creates, connects, and queries CTXSlate nodes.

Analog of core/gaffer/manager.py.
"""

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False

from core.logging_config import get_logger

logger = get_logger(__name__)


class SlateManager(object):
    """Manages creation and wiring of CTXSlate nodes.

    All methods are static — no instance state required.
    """

    @staticmethod
    def create_master_slate(name='Master'):
        """Create a master-level CTXSlateNode.

        The master slate sits at the top of the inheritance chain.
        It is not directly assigned to any sequence or shot — child
        slates reference it via parentSlate.

        Args:
            name (str): Human label for this slate.

        Returns:
            CTXSlateNode: Created node.
        """
        from core.nodes.wrappers.slate import CTXSlateNode
        slate = CTXSlateNode.create(slateName=name, slateType='master', scopeCode='')
        logger.info("Created master slate: %s", slate.node_name)
        return slate

    @staticmethod
    def create_sequence_slate(seq_node, parent_slate=None):
        """Create a sequence-level CTXSlateNode and assign it to a sequence.

        Args:
            seq_node (CTXSequenceNode|str): Sequence to assign to.
            parent_slate (CTXSlateNode|str|None): Parent slate to inherit from.

        Returns:
            CTXSlateNode: Created node.
        """
        from core.nodes.wrappers.slate import CTXSlateNode
        from core.nodes.wrappers.sequence import CTXSequenceNode

        seq = seq_node if not isinstance(seq_node, str) else CTXSequenceNode(seq_node)
        seq_code = seq.get_attribute('sequenceCode') or seq.node_name

        slate = CTXSlateNode.create(
            slateName=seq_code,
            slateType='sequence',
            scopeCode=seq_code,
        )

        if parent_slate is not None:
            slate.set_parent_slate(parent_slate)

        seq.set_slate(slate)
        logger.info("Created sequence slate %s for sequence %s", slate.node_name, seq.node_name)
        return slate

    @staticmethod
    def create_shot_slate(shot_node, parent_slate=None):
        """Create a shot-level CTXSlateNode and assign it to a shot.

        If no parent_slate is given, automatically finds the sequence slate
        connected to the shot's parent sequence and wires it as parent.

        Args:
            shot_node (CTXShotNode|str): Shot to assign to.
            parent_slate (CTXSlateNode|str|None): Explicit parent slate, or
                                                  None for auto-wire.

        Returns:
            CTXSlateNode: Created node.
        """
        from core.nodes.wrappers.slate import CTXSlateNode
        from core.nodes.wrappers.shot import CTXShotNode

        shot = shot_node if not isinstance(shot_node, str) else CTXShotNode(shot_node)
        shot_id = '{}_{}'.format(shot.get_seq_code(), shot.get_shot_code())

        slate = CTXSlateNode.create(
            slateName=shot_id,
            slateType='shot',
            scopeCode=shot_id,
        )

        if parent_slate is not None:
            slate.set_parent_slate(parent_slate)
        else:
            # Auto-wire: find sequence slate
            auto_parent = SlateManager._find_sequence_slate_for_shot(shot)
            if auto_parent is not None:
                slate.set_parent_slate(auto_parent)
                logger.info(
                    "Auto-wired shot slate %s to sequence slate %s",
                    slate.node_name, auto_parent.node_name
                )

        shot.set_slate(slate)
        logger.info("Created shot slate %s for shot %s", slate.node_name, shot.node_name)
        return slate

    @staticmethod
    def get_or_create_shot_slate(shot_node):
        """Return existing shot slate or create one if absent.

        This is the entry point called by the +SLT button click handler.

        Args:
            shot_node (CTXShotNode|str): Shot node.

        Returns:
            CTXSlateNode: Existing or newly created slate.
        """
        from core.nodes.wrappers.shot import CTXShotNode

        shot = shot_node if not isinstance(shot_node, str) else CTXShotNode(shot_node)
        existing = shot.get_slate()
        if existing is not None:
            return existing
        return SlateManager.create_shot_slate(shot)

    @staticmethod
    def add_layer_to_slate(slate, layer_name, renderable=True, override_enabled=False):
        """Add a render layer entry to a slate.

        If the layer already exists in the slate, returns the existing node.

        Args:
            slate (CTXSlateNode|str): Target slate node.
            layer_name (str): Render layer name (must match scene exactly).
            renderable (bool): Initial renderable value.
            override_enabled (bool): Initial renderableEnabled. Default False (inherit).

        Returns:
            CTXSlateLayerNode: Created or existing layer entry.
        """
        from core.nodes.wrappers.slate import CTXSlateNode

        slate_node = slate if not isinstance(slate, str) else CTXSlateNode(slate)
        layer = slate_node.add_layer(layer_name, renderable=renderable, enabled=override_enabled)
        logger.info("Added layer %r to slate %s (renderable=%s, enabled=%s)",
                    layer_name, slate_node.node_name, renderable, override_enabled)
        return layer

    @staticmethod
    def remove_layer_from_slate(slate, layer_name):
        """Remove a render layer entry from a slate.

        Args:
            slate (CTXSlateNode|str): Target slate node.
            layer_name (str): Layer name to remove.
        """
        from core.nodes.wrappers.slate import CTXSlateNode

        slate_node = slate if not isinstance(slate, str) else CTXSlateNode(slate)
        slate_node.remove_layer(layer_name)
        logger.info("Removed layer %r from slate %s", layer_name, slate_node.node_name)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_sequence_slate_for_shot(shot_node):
        """Walk up from a shot to its parent sequence and return that sequence's slate.

        Args:
            shot_node (CTXShotNode): Shot wrapper.

        Returns:
            CTXSlateNode|None
        """
        if not MAYA_AVAILABLE:
            return None
        try:
            connected = cmds.listConnections(
                '{}.message'.format(shot_node.node_name),
                source=False,
                destination=True,
                plugs=True,
            ) or []
            for plug in connected:
                node_name = plug.split('.')[0]
                try:
                    ctx_type = cmds.getAttr('{}.ctx_type'.format(node_name))
                    if ctx_type == 'CTX_Sequence':
                        from core.nodes.wrappers.sequence import CTXSequenceNode
                        seq = CTXSequenceNode(node_name)
                        return seq.get_slate()
                except Exception:
                    continue
        except Exception:
            pass
        return None
```

---

## 3. `core/slate/resolver.py` — NEW FILE

```python
"""SlateResolver — resolves the slate inheritance chain and applies it to Maya.

Analog of core/gaffer/resolver.py (AttributeResolver).

Resolution algorithm (mirrors gaffer chain walk):
  1. Build chain: [shot_slate, seq_slate, master_slate]
     (walk parentSlate connections)
  2. For each render layer known to the chain:
     Walk chain from index 0 (shot) outward.
     First slate where renderableEnabled=True wins.
     If none found → no override, leave scene state unchanged for that layer.
  3. apply_to_scene() calls Maya Render Setup API to set renderable flags.
"""

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False

from core.logging_config import get_logger

logger = get_logger(__name__)

# Sentinel for "no override found in chain"
_NO_OVERRIDE = object()


class SlateResolver(object):

    @staticmethod
    def build_chain(slate_node):
        """Walk parentSlate connections and return the full chain.

        The returned list is ordered from most-specific to least-specific:
        [shot_slate, seq_slate, master_slate]

        A disabled slate (enabled=False) is included in the list but skipped
        during resolution (same behaviour as gaffer chain).

        Args:
            slate_node (CTXSlateNode|str): Starting slate (most specific).

        Returns:
            list[CTXSlateNode]: Chain from most-specific to root.
        """
        from core.nodes.wrappers.slate import CTXSlateNode

        current = slate_node if not isinstance(slate_node, str) else CTXSlateNode(slate_node)
        chain = []
        visited = set()

        while current is not None:
            if current.node_name in visited:
                logger.warning("Circular parentSlate connection at %s", current.node_name)
                break
            visited.add(current.node_name)
            chain.append(current)
            current = current.get_parent_slate()

        return chain

    @staticmethod
    def resolve_layer_state(shot_or_seq_node):
        """Resolve renderable state for all layers in the slate chain.

        Finds the slate for the given shot or sequence, builds the chain,
        and resolves each layer's renderable state.

        Args:
            shot_or_seq_node: CTXShotNode or CTXSequenceNode (or node name str).

        Returns:
            dict: {
                layer_name: {
                    'renderable': bool,      # resolved value
                    'source':     str,       # slate node name that owns it, or '' if no override
                    'overridden': bool,      # True if any slate in chain owns this layer
                }
            }
            Empty dict if no slate is found.
        """
        slate = SlateResolver._get_slate_for_node(shot_or_seq_node)
        if slate is None:
            return {}

        chain = SlateResolver.build_chain(slate)
        if not chain:
            return {}

        # Collect all layer names across the entire chain
        all_layer_names = set()
        for slate_node in chain:
            for layer in slate_node.get_layers():
                name = layer.get_layer_name()
                if name:
                    all_layer_names.add(name)

        result = {}
        for layer_name in sorted(all_layer_names):
            resolved_value = _NO_OVERRIDE
            source = ''

            for slate_node in chain:
                if not slate_node.is_enabled():
                    continue
                layer_entry = slate_node.get_layer_by_name(layer_name)
                if layer_entry is None:
                    continue
                if layer_entry.is_override_enabled():
                    resolved_value = layer_entry.get_renderable()
                    source = slate_node.node_name
                    break  # First owner wins (most-specific first)

            if resolved_value is _NO_OVERRIDE:
                result[layer_name] = {
                    'renderable': None,
                    'source':     '',
                    'overridden': False,
                }
            else:
                result[layer_name] = {
                    'renderable': resolved_value,
                    'source':     source,
                    'overridden': True,
                }

        return result

    @staticmethod
    def apply_to_scene(shot_or_seq_node):
        """Resolve the slate chain and apply renderable flags to Maya Render Setup.

        Only layers with overridden=True are modified. Layers with no override
        in any slate are left at their current scene state.

        Args:
            shot_or_seq_node: CTXShotNode or CTXSequenceNode (or node name str).
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

        for layer_name, state in resolved.items():
            if not state['overridden']:
                continue

            renderable = state['renderable']
            try:
                layer = rs.getRenderLayer(layer_name)
                if layer is None:
                    logger.warning("Slate apply: layer %r not found in scene", layer_name)
                    continue
                layer.setRenderable(renderable)
                logger.debug(
                    "Slate: set %r renderable=%s (source=%s)",
                    layer_name, renderable, state['source']
                )
            except Exception as exc:
                logger.warning("Failed to set renderable on layer %r: %s", layer_name, exc)

    @staticmethod
    def get_resolved_renderable_layers(shot_or_seq_node):
        """Return list of layer names that resolve to renderable=True.

        Used by ScenePreparer to determine which layers to render for a shot.

        Args:
            shot_or_seq_node: CTXShotNode or CTXSequenceNode (or node name str).

        Returns:
            list[str]: Layer names that are renderable. None if no slate found
                       (caller should fall back to scene state).
        """
        resolved = SlateResolver.resolve_layer_state(shot_or_seq_node)
        if not resolved:
            return None  # No slate — caller uses scene state

        renderable = [
            name for name, state in resolved.items()
            if state['overridden'] and state['renderable'] is True
        ]
        return renderable

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_slate_for_node(node):
        """Return the slate for a shot or sequence node.

        For a shot: returns shot slate first, then sequence slate.
        For a sequence: returns sequence slate.

        Args:
            node: CTXShotNode, CTXSequenceNode, or str.

        Returns:
            CTXSlateNode|None
        """
        if not MAYA_AVAILABLE:
            return None

        # Resolve string to wrapper
        if isinstance(node, str):
            try:
                ctx_type = cmds.getAttr('{}.ctx_type'.format(node))
                if ctx_type == 'CTX_Shot':
                    from core.nodes.wrappers.shot import CTXShotNode
                    node = CTXShotNode(node)
                elif ctx_type == 'CTX_Sequence':
                    from core.nodes.wrappers.sequence import CTXSequenceNode
                    node = CTXSequenceNode(node)
                else:
                    return None
            except Exception:
                return None

        # Try shot slate first
        shot_slate = None
        try:
            shot_slate = node.get_slate()
        except AttributeError:
            pass

        if shot_slate is not None:
            return shot_slate

        # Fall back to sequence slate (if node is a shot)
        try:
            from core.nodes.wrappers.shot import CTXShotNode
            if isinstance(node, CTXShotNode):
                seq_connections = cmds.listConnections(
                    '{}.message'.format(node.node_name),
                    source=False,
                    destination=True,
                    plugs=True,
                ) or []
                for plug in seq_connections:
                    seq_name = plug.split('.')[0]
                    try:
                        if cmds.getAttr('{}.ctx_type'.format(seq_name)) == 'CTX_Sequence':
                            from core.nodes.wrappers.sequence import CTXSequenceNode
                            seq = CTXSequenceNode(seq_name)
                            return seq.get_slate()
                    except Exception:
                        continue
        except Exception:
            pass

        return None
```

---

## 4. `ui/main_window.py` — Shot-Switch Integration

Read the `_on_set_shot()` method (or `_apply_shot_context()`) before editing.

After the existing gaffer apply block, add slate apply:

```python
# Apply slate (render layer renderable state)
try:
    from core.slate.resolver import SlateResolver
    shot_node_name = shot_node.node_name if hasattr(shot_node, 'node_name') else None
    if shot_node_name:
        SlateResolver.apply_to_scene(shot_node_name)
        logger.debug("Slate applied for shot %s", shot_node_name)
except Exception as exc:
    logger.warning("Slate apply failed for shot: %s", exc)
    # Non-fatal — do not interrupt shot switch on slate error
```

The try/except is intentional: slate errors must never block the shot switch.

---

## Tests — `tests/test_slate_resolver.py`

```python
# test_build_chain_single_slate
#   — slate with no parent returns [slate]

# test_build_chain_three_levels
#   — shot -> seq -> master chain returns list of 3

# test_build_chain_circular_guard
#   — circular parentSlate connection does not infinite-loop

# test_resolve_no_override_returns_none_renderable
#   — layer with renderableEnabled=False → overridden=False, renderable=None

# test_resolve_shot_slate_wins_over_seq
#   — shot slate and seq slate both have 'beauty'; shot slate wins (first in chain)

# test_resolve_seq_slate_fallback
#   — shot has no 'beauty' entry; seq slate has it with enabled=True → uses seq value

# test_resolve_disabled_slate_skipped
#   — slate with enabled=False is in chain; its values are not applied

# test_get_resolved_renderable_layers_returns_list
#   — layers with renderable=True returned; renderable=False excluded

# test_get_resolved_renderable_layers_no_slate_returns_none
#   — node with no slate → returns None

# test_apply_to_scene_calls_set_renderable
#   — mock renderSetup; apply_to_scene calls layer.setRenderable for overridden layers

# test_apply_to_scene_skips_non_overridden
#   — layers with overridden=False do not have setRenderable called
```

---

## Tests — `tests/test_slate_manager.py`

```python
# test_create_master_slate
#   — creates CTXSlateNode with slateType='master'

# test_create_sequence_slate_assigns_to_seq
#   — creates slate and calls seq.set_slate()

# test_create_sequence_slate_wires_parent
#   — parent_slate provided; set_parent_slate called

# test_create_shot_slate_auto_wires_seq_slate
#   — shot has parent sequence with existing slate; auto-wired as parentSlate

# test_get_or_create_returns_existing
#   — shot already has slate; no new node created

# test_add_layer_to_slate
#   — SlateManager.add_layer_to_slate creates CTXSlateLayerNode in slate

# test_remove_layer_from_slate
#   — SlateManager.remove_layer_from_slate calls slate.remove_layer
```

---

## Completion Criteria

- [ ] `core/slate/__init__.py` created
- [ ] `core/slate/manager.py` created — all 6 public methods implemented
- [ ] `core/slate/resolver.py` created — `build_chain`, `resolve_layer_state`, `apply_to_scene`, `get_resolved_renderable_layers`
- [ ] Shot-switch in `main_window.py` calls `SlateResolver.apply_to_scene()` after gaffer apply
- [ ] Slate errors in shot-switch are non-fatal (wrapped in try/except)
- [ ] All tests pass
- [ ] No regressions in existing test suite
