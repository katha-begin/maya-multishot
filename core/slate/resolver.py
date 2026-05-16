"""SlateResolver -- resolves the slate inheritance chain and applies it to Maya.

Analog of core/gaffer/resolver.py (AttributeResolver).

Resolution algorithm (mirrors gaffer chain walk):
  1. Build chain: [shot_slate, seq_slate, master_slate]
     (walk parentSlate connections)
  2. For each render layer known to the chain:
     Walk chain from index 0 (shot) outward.
     First slate where renderableEnabled=True wins.
     If none found -> no override, restore to original (if captured).
  3. apply_to_scene() calls Maya Render Setup API to set renderable flags.
"""

from __future__ import absolute_import, division, print_function

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

        Captures originals before first application. Restores originals for
        layers with no override in any slate (same behaviour as gaffer restore).

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
                    # No override in chain -- restore to original
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
            return None  # No slate -- caller uses scene state

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

        # Try shot/sequence slate directly
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
