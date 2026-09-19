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

from core import asset_types
from core.logging_config import get_logger
from core.compat import string_types

logger = get_logger(__name__)

# Namespaces that extend an asset namespace but are not assets themselves
_DEFAULT_NAMESPACE_SUFFIXES = ('_Shade', '_Groom')

# Attributes a record needs before resolve_asset_path can build a path
_RECORD_FIELDS = ('template', 'department', 'version', 'extension')


def _get_template(config, name):
    """Read a named template from the config, tolerating config=None."""
    getter = getattr(config, 'get_template', None)
    if not callable(getter):
        return None
    try:
        return getter(name)
    except Exception:
        return None


def _namespace_suffixes(config):
    """Suffixes marking a shader or groom namespace rather than an asset.

    Both extend the asset namespace ('$assetType_$assetName_$variant_Shade'),
    so the suffix is whatever the shader/groom template adds to it.
    """
    base = _get_template(config, 'namespace') or '$assetType_$assetName_$variant'

    suffixes = []
    for name in ('namespaceShader', 'namespaceGroom'):
        template = _get_template(config, name)
        if template and template.startswith(base) and len(template) > len(base):
            suffixes.append(template[len(base):])

    return tuple(suffixes) or _DEFAULT_NAMESPACE_SUFFIXES


def _parse_namespace(namespace, config=None):
    """Parse a reference namespace into (asset_type, asset_name, variant).

    Format: TYPE_Name_Variant  (e.g. CHAR_BuffA_001, PROP_StuffyWooWooToyA_002)
    Multi-part names are supported (e.g. CHAR_Cat_Stompie_001 -> name='Cat_Stompie').

    Parsing goes through core.asset_types, the parser publish names use, so a
    record carries the same type, name and variant Add Shots would record.
    Shader and groom namespaces are not assets and return None -- splitting
    them by hand made 'CHAR_Ajay_001_Shade' an asset named 'Ajay_001' with
    variant 'Shade'.

    Args:
        namespace (str): Maya reference namespace.
        config: Optional ProjectConfig instance.

    Returns:
        tuple: (asset_type, asset_name, variant) or None if unparseable.
    """
    if not namespace:
        return None

    for suffix in _namespace_suffixes(config):
        if namespace.endswith(suffix):
            return None

    # A basename namespace (CFX) carries the whole publish name; the asset half
    # is what follows the shot separator
    asset_part = namespace.rsplit(asset_types.SHOT_ASSET_SEPARATOR, 1)[-1]

    parsed = asset_types.parse_asset_part(asset_part, config)
    if not parsed:
        return None

    return (parsed['type'], parsed['name'], parsed['variant'])


def _read_shot_context(node_name):
    """Read (ep, seq, shot) from a CTX_Shot node, legacy attribute names included."""
    codes = []
    for names in (('ep_code', 'ep'), ('seq_code', 'seq'), ('shot_code', 'shot')):
        value = ''
        for attr in names:
            if cmds.attributeQuery(attr, node=node_name, exists=True):
                value = cmds.getAttr('{}.{}'.format(node_name, attr)) or ''
                if value:
                    break
        codes.append(value)
    return tuple(codes)


def _shot_publishes(config, node_name):
    """What the shot published, keyed by (asset type, name, variant).

    The same discovery Add Shots uses (core/asset_scanner), so a record the
    reconciler writes carries the shot's own department and version and points
    at a file that exists.

    Returns:
        dict: {(type, name, variant): {'dept', 'version', 'file_path', 'info'}};
            empty when the config or the shot context is unavailable.
    """
    if config is None:
        logger.warning("No project config: cannot tell what %s published", node_name)
        return {}

    ep, seq, shot = _read_shot_context(node_name)
    if not all((ep, seq, shot)):
        logger.warning("Incomplete shot context on %s (ep=%s seq=%s shot=%s)",
                       node_name, ep, seq, shot)
        return {}

    try:
        from core.asset_scanner import AssetScanner

        return AssetScanner(config).discover_shot_assets(ep, seq, shot)
    except Exception as exc:
        logger.warning("Could not scan the publishes of %s: %s", node_name, exc)
        return {}


def _fill_record(node_name, asset_type, publish, config):
    """Fill in what a record needs to resolve: template and publish fields.

    Only empty attributes are written, so values from Add Shots or an artist
    are kept.  A record created without a template resolved no path at all:
    resolve_asset_path starts from the template and returns None without one.

    Args:
        node_name (str): CTX_Asset node name.
        asset_type (str): Asset type code (e.g. 'CHAR').
        publish (dict): The shot's publish entry for this asset.
        config: ProjectConfig instance or None.

    Returns:
        list: Names of the attributes written.
    """
    from core.nodes.wrappers.asset import CTXAssetNode

    asset = CTXAssetNode(node_name)
    values = {
        'template': asset_types.get_asset_path_template(asset_type, config),
        'department': publish.get('dept'),
        'version': publish.get('version'),
        'extension': (publish.get('info') or {}).get('ext'),
    }

    written = []
    for attr in _RECORD_FIELDS:
        value = values.get(attr)
        if not value:
            continue
        try:
            if asset.get_attribute(attr):
                continue
            asset.set_attribute(attr, value)
        except Exception as exc:
            logger.debug("Could not set %s on %s: %s", attr, node_name, exc)
            continue
        written.append(attr)

    return written


def _get_shot_code(shot_node):
    """Extract shot code from a CTXShotNode (wrapper or string).

    Args:
        shot_node: CTXShotNode instance or node name string.

    Returns:
        str: Shot code (e.g. 'SH0140'), or empty string.
    """
    if not MAYA_AVAILABLE:
        return ''

    node_name = shot_node if isinstance(shot_node, string_types) else shot_node.node_name

    if not cmds.objExists(node_name):
        return ''

    return _read_shot_code(node_name)


def _read_shot_code(node_name):
    """Read the shot code attribute of a CTX_Shot node.

    Schema-based shot nodes store it as 'shot_code'; 'shot' is the legacy
    name.  Reading only 'shot' made reconciliation skip every schema-based
    shot ("could not determine shot code").
    """
    for attr in ('shot_code', 'shot'):
        if cmds.attributeQuery(attr, node=node_name, exists=True):
            value = cmds.getAttr('{}.{}'.format(node_name, attr))
            if value:
                return value
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
    shot_code = _read_shot_code(shot_node_name)

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


def reconcile_assets_for_shot(shot_node, config=None):
    """Scan scene references and repair missing CTX_Asset linkage for a shot.

    For each Maya reference in the scene whose namespace matches the standard
    asset pattern (TYPE_Name_Variant):
      - If a CTX_Asset node already exists for this shot+namespace, ensure it
        is wired to both the shot and the reference node, and fill in any
        record field it lacks.
      - If no CTX_Asset node exists, create one, set its attributes, wire it
        to the shot, and link it to the reference.

    A record is only useful once it carries a template: resolve_asset_path
    builds every path from it.

    Args:
        shot_node: CTXShotNode wrapper instance or node name string.
        config: Optional ProjectConfig instance.  Resolved for the open scene
            when omitted; pass the caller's config to avoid the lookup.

    Returns:
        dict: {'created': int, 'linked': int, 'skipped': int, 'repaired': int,
               'created_nodes': list, 'linked_nodes': list}
              created_nodes/linked_nodes contain CTX_Asset node name strings.
    """
    empty = {'created': 0, 'linked': 0, 'skipped': 0, 'repaired': 0,
             'created_nodes': [], 'linked_nodes': []}

    if not MAYA_AVAILABLE:
        logger.warning("reconcile_assets_for_shot: Maya not available")
        return empty

    node_name = shot_node if isinstance(shot_node, string_types) else shot_node.node_name

    if not cmds.objExists(node_name):
        logger.warning("reconcile_assets_for_shot: shot node does not exist: %s",
                        node_name)
        return empty

    shot_code = _get_shot_code(node_name)
    if not shot_code:
        logger.warning("reconcile_assets_for_shot: could not determine shot code "
                        "from %s", node_name)
        return empty

    logger.debug("Reconciling assets for shot %s (%s)", shot_code, node_name)

    if config is None:
        config = _resolve_config()

    publishes = _shot_publishes(config, node_name)

    created = 0
    linked = 0
    skipped = 0
    repaired = 0
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

        parsed = _parse_namespace(ref_ns, config)
        if parsed is None:
            # Not a standard asset namespace (e.g. shader references)
            continue

        asset_type, asset_name, variant = parsed

        publish = publishes.get((asset_type, asset_name, variant))
        if publish is None:
            # The shot published no such asset: the reference belongs to another
            # shot, or is a set piece inside one.  A record would resolve to a
            # file that does not exist ("does not exist" on every shot switch).
            logger.debug("  Skipping %s -- %s published no such asset",
                         ref_ns, shot_code)
            skipped += 1
            continue

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

            # Records this created before only carried wiring, so they had no
            # template and resolved no path
            if _fill_record(existing, asset_type, publish, config):
                logger.debug("  Filled record fields on %s", existing)
                repaired += 1
                if existing not in linked_nodes:
                    linked_nodes.append(existing)
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
            logger.debug("  Created %s for %s (namespace: %s)",
                         new_asset.node_name, shot_code, ref_ns)

            # The template and publish fields Add Shots records, so the new
            # record resolves a path like any other
            _fill_record(new_asset.node_name, asset_type, publish, config)

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

    logger.info("Reconciled %s: created=%d, linked=%d, repaired=%d, skipped=%d",
                 shot_code, created, linked, repaired, skipped)

    return {'created': created, 'linked': linked, 'skipped': skipped,
            'repaired': repaired,
            'created_nodes': created_nodes, 'linked_nodes': linked_nodes}


def find_stale_records(shot_node, config=None):
    """CTX_Asset records wired to a shot that the shot never published.

    Scenes built before the publish check carry records the reconciler adopted
    from any reference in the scene: shader and groom namespaces, references
    nested inside a set, and other shots' assets.  None of them resolves a
    path, so every shot switch logs "does not exist" or "Unexpanded tokens".

    Nothing is reported when the shot's publishes cannot be read, so a failed
    scan never condemns a scene's records.

    Args:
        shot_node: CTXShotNode wrapper instance or node name string.
        config: Optional ProjectConfig instance.

    Returns:
        list: [{'node': str, 'namespace': str, 'reason': str}, ...]
    """
    if not MAYA_AVAILABLE:
        return []

    node_name = shot_node if isinstance(shot_node, string_types) else shot_node.node_name
    if not cmds.objExists(node_name):
        return []

    if config is None:
        config = _resolve_config()

    publishes = _shot_publishes(config, node_name)
    if not publishes:
        logger.warning("No publishes found for %s -- not reporting its records",
                       node_name)
        return []

    stale = []
    records = cmds.listConnections('{}.assets'.format(node_name),
                                   source=True, destination=False) or []

    for record in records:
        if not cmds.attributeQuery('namespace', node=record, exists=True):
            continue
        namespace = cmds.getAttr('{}.namespace'.format(record)) or ''

        parsed = _parse_namespace(namespace, config)
        if parsed is None:
            stale.append({'node': record, 'namespace': namespace,
                          'reason': 'not an asset namespace'})
            continue

        if parsed not in publishes:
            stale.append({'node': record, 'namespace': namespace,
                          'reason': 'the shot published no such asset'})

    return stale


def repair_scene_records(config=None, remove_stale=False):
    """Bring every shot's records in line with what the shot published.

    For a scene built before the publish check:
      - reconcile each shot, so a publish loaded in the scene gets the record
        it needs and existing records get their template, department, version
        and extension filled in
      - report the records that describe no publish of their shot

    Nothing is deleted unless remove_stale is set, so the report can be shown
    first.

    Args:
        config: Optional ProjectConfig instance.
        remove_stale (bool): Delete the reported records.

    Returns:
        dict: {'shots': int, 'created': int, 'repaired': int, 'removed': int,
               'stale': [{'shot', 'node', 'namespace', 'reason'}, ...]}
    """
    report = {'shots': 0, 'created': 0, 'repaired': 0, 'removed': 0, 'stale': []}

    if not MAYA_AVAILABLE:
        logger.warning("repair_scene_records: Maya not available")
        return report

    if config is None:
        config = _resolve_config()

    for node in cmds.ls(type='network') or []:
        if not cmds.attributeQuery('ctx_type', node=node, exists=True):
            continue
        if cmds.getAttr('{}.ctx_type'.format(node)) != 'CTX_Shot':
            continue

        report['shots'] += 1

        stats = reconcile_assets_for_shot(node, config=config)
        report['created'] += stats['created']
        report['repaired'] += stats.get('repaired', 0)

        for record in find_stale_records(node, config=config):
            entry = dict(record)
            entry['shot'] = node
            report['stale'].append(entry)

    if remove_stale:
        report['removed'] = remove_records(
            [entry['node'] for entry in report['stale']])

    logger.info("Repaired %d shots: created=%d, repaired=%d, stale=%d, removed=%d",
                report['shots'], report['created'], report['repaired'],
                len(report['stale']), report['removed'])
    return report


def remove_records(nodes):
    """Delete CTX_Asset nodes.

    Args:
        nodes (list): CTX_Asset node names.

    Returns:
        int: How many were deleted.
    """
    if not MAYA_AVAILABLE:
        return 0

    removed = 0
    for node in nodes:
        try:
            if cmds.objExists(node):
                cmds.delete(node)
                removed += 1
        except Exception as exc:
            logger.warning("Could not delete %s: %s", node, exc)

    return removed


def _resolve_config():
    """Load the project config for the open scene, or None when unavailable.

    Callers that already hold a config pass it in; this is the fallback for
    the ones that do not, so a record is never written without a template.
    """
    try:
        from config.config_resolver import resolve_config_path
        from config.project_config import ProjectConfig

        return ProjectConfig(resolve_config_path())
    except Exception as exc:
        logger.warning("Could not load the project config: %s", exc)
        return None
