"""SlateManager -- creates, connects, and queries CTXSlate nodes.

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

    All methods are static -- no instance state required.
    """

    @staticmethod
    def create_master_slate(name='Master'):
        """Create a master-level CTXSlateNode.

        The master slate sits at the top of the inheritance chain.
        It is not directly assigned to any sequence or shot -- child
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
    def create_sequence_slate(seq_node, name=None, parent_slate=None):
        """Create a sequence-level CTXSlateNode and assign it to a sequence.

        Args:
            seq_node (CTXSequenceNode|str): Sequence to assign to.
            name (str|None): Human name for slateName attribute.
                             Defaults to 'seq_{seq_code}'.
            parent_slate (CTXSlateNode|str|None): Parent slate to inherit from.

        Returns:
            CTXSlateNode: Created node.
        """
        from core.nodes.wrappers.slate import CTXSlateNode
        from core.nodes.wrappers.sequence import CTXSequenceNode

        seq = seq_node if not isinstance(seq_node, str) else CTXSequenceNode(seq_node)
        seq_code = seq.get_attribute('sequenceCode') or seq.node_name

        slate_name = name if name else 'seq_{}'.format(seq_code)

        slate = CTXSlateNode.create(
            slateName=slate_name,
            slateType='sequence',
            scopeCode=seq_code,
        )

        if parent_slate is not None:
            slate.set_parent_slate(parent_slate)

        seq.set_slate(slate)
        logger.info("Created sequence slate %s for sequence %s", slate.node_name, seq.node_name)
        return slate

    @staticmethod
    def create_shot_slate(shot_node, name=None, parent_slate=None):
        """Create a shot-level CTXSlateNode and assign it to a shot.

        If no parent_slate is given, automatically finds the sequence slate
        connected to the shot's parent sequence and wires it as parent.

        Args:
            shot_node (CTXShotNode|str): Shot to assign to.
            name (str|None): Human name for slateName attribute.
                             Defaults to '{seq_code}_{shot_code}'.
            parent_slate (CTXSlateNode|str|None): Explicit parent slate, or
                                                  None for auto-wire.

        Returns:
            CTXSlateNode: Created node.
        """
        from core.nodes.wrappers.slate import CTXSlateNode
        from core.nodes.wrappers.shot import CTXShotNode

        shot = shot_node if not isinstance(shot_node, str) else CTXShotNode(shot_node)
        shot_id = '{}_{}'.format(shot.get_seq_code(), shot.get_shot_code())

        slate_name = name if name else shot_id

        slate = CTXSlateNode.create(
            slateName=slate_name,
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
    def add_layer_to_slate(slate, layer_name, renderable=True, override_enabled=True):
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
