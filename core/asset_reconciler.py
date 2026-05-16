"""Asset reconciler -- repairs CTX_Asset linkage on shot-switch.

When switching to a shot, Maya references may exist in the scene without
a corresponding CTX_Asset node for that shot.  This module scans all
scene references, identifies unlinked ones, and creates + wires the
missing CTX_Asset nodes so that the Asset Manager sees them correctly.

Usage:
    from core.asset_reconciler import reconcile_assets_for_shot
    stats = reconcile_assets_for_shot(shot_node)
    # stats = {'created': 3, 'linked': 1, 'skipped': 8}
"""

from __future__ import absolute_import, division, print_function

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    MAYA_AVAILABLE = False

from core.logging_config import get_logger

logger = get_logger(__name__)


def _parse_namespace(namespace):
    """Parse a reference namespace into (asset_type, asset_name, variant).

    Format: TYPE_Name_Variant  (e.g. CHAR_BuffA_001, PROP_StuffyWooWooToyA_002)
    Multi-part names are supported (e.g. CHAR_Cat_Stompie_001 -> name='Cat_Stompie').

    Args:
        namespace (str): Maya reference namespace.

    Returns:
        tuple: (asset_type, asset_name, variant) or None if unparseable.
    """
    if not namespace:
        return None

    parts = namespace.split('_')
    if len(parts) < 3:
        return None

    asset_type = parts[0]
    variant = parts[-1]
    asset_name = '_'.join(parts[1:-1])

    if not asset_type or not asset_name or not variant:
        return None

    return (asset_type, asset_name, variant)


def _get_shot_code(shot_node):
    """Extract shot code from a CTXShotNode (wrapper or string).

    Args:
        shot_node: CTXShotNode instance or node name string.

    Returns:
        str: Shot code (e.g. 'SH0140'), or empty string.
    """
    if not MAYA_AVAILABLE:
        return ''

    node_name = shot_node if isinstance(shot_node, str) else shot_node.node_name

    if not cmds.objExists(node_name):
        return ''

    if cmds.attributeQuery('shot', node=node_name, exists=True):
        return cmds.getAttr('{}.shot'.format(node_name)) or ''

    return ''


def _find_ctx_asset_for_shot(shot_node_name, namespace):
    """Check whether a CTX_Asset node already exists for this shot + namespace.

    Searches two ways:
      1. Walk shot.assets[] connections and match by namespace attribute.
      2. Scan all CTX_Asset_ nodes whose name contains the shot code and
         whose namespace attribute matches.

    Args:
        shot_node_name (str): CTX_Shot node name.
        namespace (str): Expected namespace (e.g. 'CHAR_BuffA_001').

    Returns:
        str or None: Existing CTX_Asset node name, or None.
    """
    # Method 1: walk shot's connected assets
    connections = cmds.listConnections(
        '{}.assets'.format(shot_node_name),
        source=True, destination=False
    ) or []

    for node in connections:
        if not cmds.attributeQuery('namespace', node=node, exists=True):
            continue
        if cmds.getAttr('{}.namespace'.format(node)) == namespace:
            return node

    # Method 2: scan all CTX_Asset nodes (handles orphaned nodes not yet wired)
    shot_code = ''
    if cmds.attributeQuery('shot', node=shot_node_name, exists=True):
        shot_code = cmds.getAttr('{}.shot'.format(shot_node_name)) or ''

    if shot_code:
        all_network = cmds.ls(type='network') or []
        for node in all_network:
            if not node.startswith('CTX_Asset_'):
                continue
            if shot_code not in node:
                continue
            if not cmds.attributeQuery('namespace', node=node, exists=True):
                continue
            if cmds.getAttr('{}.namespace'.format(node)) == namespace:
                return node

    return None


def _is_connected_to_shot(asset_node_name, shot_node_name):
    """Check if an asset node is already wired to a shot's assets[] array.

    Args:
        asset_node_name (str): CTX_Asset node name.
        shot_node_name (str): CTX_Shot node name.

    Returns:
        bool: True if connection exists.
    """
    connections = cmds.listConnections(
        '{}.message'.format(asset_node_name),
        source=False, destination=True,
        plugs=True
    ) or []

    for plug in connections:
        if plug.startswith('{}.assets'.format(shot_node_name)):
            return True

    return False


def _link_reference_to_ctx(ref_node, ctx_asset_node):
    """Connect reference.message -> CTX_Asset.targetNode.

    Args:
        ref_node (str): Maya reference node name.
        ctx_asset_node (str): CTX_Asset node name.

    Returns:
        bool: True if connected successfully.
    """
    if not cmds.attributeQuery('targetNode', node=ctx_asset_node, exists=True):
        cmds.addAttr(ctx_asset_node, longName='targetNode', attributeType='message')

    try:
        cmds.connectAttr(
            '{}.message'.format(ref_node),
            '{}.targetNode'.format(ctx_asset_node),
            force=True
        )
        return True
    except RuntimeError as exc:
        logger.warning("Failed to link %s -> %s.targetNode: %s",
                        ref_node, ctx_asset_node, exc)
        return False


def reconcile_assets_for_shot(shot_node):
    """Scan scene references and repair missing CTX_Asset linkage for a shot.

    For each Maya reference in the scene whose namespace matches the standard
    asset pattern (TYPE_Name_Variant):
      - If a CTX_Asset node already exists for this shot+namespace, ensure it
        is wired to both the shot and the reference node.
      - If no CTX_Asset node exists, create one, set its attributes, wire it
        to the shot, and link it to the reference.

    Args:
        shot_node: CTXShotNode wrapper instance or node name string.

    Returns:
        dict: {'created': int, 'linked': int, 'skipped': int,
               'created_nodes': list, 'linked_nodes': list}
              created_nodes/linked_nodes contain CTX_Asset node name strings.
    """
    empty = {'created': 0, 'linked': 0, 'skipped': 0,
             'created_nodes': [], 'linked_nodes': []}

    if not MAYA_AVAILABLE:
        logger.warning("reconcile_assets_for_shot: Maya not available")
        return empty

    node_name = shot_node if isinstance(shot_node, str) else shot_node.node_name

    if not cmds.objExists(node_name):
        logger.warning("reconcile_assets_for_shot: shot node does not exist: %s",
                        node_name)
        return empty

    shot_code = _get_shot_code(node_name)
    if not shot_code:
        logger.warning("reconcile_assets_for_shot: could not determine shot code "
                        "from %s", node_name)
        return empty

    logger.info("Reconciling assets for shot %s (%s)", shot_code, node_name)

    created = 0
    linked = 0
    skipped = 0
    created_nodes = []
    linked_nodes = []

    references = cmds.ls(type='reference') or []

    for ref_node in references:
        if ref_node in ('sharedReferenceNode', '_UNKNOWN_REF_NODE_'):
            continue

        try:
            ref_ns = cmds.referenceQuery(ref_node, namespace=True)
        except RuntimeError:
            continue

        if ref_ns and ref_ns.startswith(':'):
            ref_ns = ref_ns[1:]

        if not ref_ns:
            continue

        parsed = _parse_namespace(ref_ns)
        if parsed is None:
            # Not a standard asset namespace (e.g. shader references)
            continue

        asset_type, asset_name, variant = parsed

        # Check if CTX_Asset already exists for this shot + namespace
        existing = _find_ctx_asset_for_shot(node_name, ref_ns)

        if existing:
            # Ensure it is wired to the shot
            was_linked = False
            if not _is_connected_to_shot(existing, node_name):
                cmds.connectAttr(
                    '{}.message'.format(existing),
                    '{}.assets'.format(node_name),
                    nextAvailable=True
                )
                logger.info("  Wired existing %s to %s", existing, node_name)
                linked += 1
                was_linked = True

            # Ensure targetNode link exists
            target_conns = cmds.listConnections(
                '{}.targetNode'.format(existing),
                source=True, destination=False
            ) if cmds.attributeQuery('targetNode', node=existing, exists=True) else None

            if not target_conns:
                _link_reference_to_ctx(ref_node, existing)
                linked += 1
                was_linked = True

            if was_linked:
                linked_nodes.append(existing)
            else:
                skipped += 1
        else:
            # Create a new CTX_Asset node for this shot
            from core.nodes.wrappers.asset import CTXAssetNode

            new_asset = CTXAssetNode.create(
                asset_type=asset_type,
                asset_name=asset_name,
                variant=variant,
                shot_code=shot_code,
                namespace=ref_ns
            )
            logger.info("  Created %s for %s (namespace: %s)",
                         new_asset.node_name, shot_code, ref_ns)

            # Wire to shot: asset.message -> shot.assets[i]
            cmds.connectAttr(
                '{}.message'.format(new_asset.node_name),
                '{}.assets'.format(node_name),
                nextAvailable=True
            )

            # Link reference -> CTX_Asset.targetNode
            _link_reference_to_ctx(ref_node, new_asset.node_name)

            created += 1
            created_nodes.append(new_asset.node_name)

    logger.info("Reconcile complete for %s: created=%d, linked=%d, skipped=%d",
                 shot_code, created, linked, skipped)

    return {'created': created, 'linked': linked, 'skipped': skipped,
            'created_nodes': created_nodes, 'linked_nodes': linked_nodes}
