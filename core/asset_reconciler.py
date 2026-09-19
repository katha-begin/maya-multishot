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

import os
import re

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

# A shot code anywhere in a name, e.g. the SH0130 of SWA_Ep20_SH0130_camera
_SHOT_CODE_RE = re.compile(r'SH\d+[A-Za-z]?', re.IGNORECASE)

# '.../<dept>/publish/<ver>/' in a publish path
_PUBLISH_RE = re.compile(r'/(?P<dept>[^/]+)/publish/(?P<ver>v\d+(?:_\d+)?)/',
                         re.IGNORECASE)

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


def _parse_publish_path(path):
    """Read department, version and extension from a reference's file path.

    '.../SH0140/anim/publish/v005/Ep10_sq0030_SH0140__CHAR_BuffA_001.abc'
    -> {'dept': 'anim', 'version': 'v005', 'ext': 'abc'}

    Args:
        path (str): Reference file path.

    Returns:
        dict: Whatever could be read; keys are absent when the path does not
            follow the publish layout.
    """
    fields = {}
    if not path:
        return fields

    text = path.replace('\\', '/')

    match = _PUBLISH_RE.search(text)
    if match:
        fields['dept'] = match.group('dept')
        fields['version'] = match.group('ver')

    ext = os.path.splitext(text)[1].lstrip('.')
    if ext:
        fields['ext'] = ext

    return fields


def _reference_path(ref_node):
    """Return the file a reference points at, or '' when it cannot be read."""
    try:
        return cmds.referenceQuery(ref_node, filename=True) or ''
    except RuntimeError:
        return ''


def _names_other_shot(asset_name, shot_code):
    """True when a name carries a different shot's code.

    One camera per shot lives in a multishot scene and its publish repeats the
    shot ('SWA_Ep20_SH0130_camera'), so a record of it under another shot can
    never resolve to a file that exists.
    """
    for found in _SHOT_CODE_RE.findall(asset_name or ''):
        if found.upper() != (shot_code or '').upper():
            return True
    return False


def _fill_record(node_name, asset_type, fields, config):
    """Fill in what a record needs to resolve: template and publish fields.

    Only empty attributes are written, so values from Add Shots or an artist
    are kept.  A record created without a template resolved no path at all:
    resolve_asset_path starts from the template and returns None without one.

    Args:
        node_name (str): CTX_Asset node name.
        asset_type (str): Asset type code (e.g. 'CHAR').
        fields (dict): Output of _parse_publish_path.
        config: ProjectConfig instance or None.

    Returns:
        list: Names of the attributes written.
    """
    from core.nodes.wrappers.asset import CTXAssetNode

    asset = CTXAssetNode(node_name)
    values = {
        'template': asset_types.get_asset_path_template(asset_type, config),
        'department': fields.get('dept'),
        'version': fields.get('version'),
        'extension': fields.get('ext'),
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

        if _names_other_shot(asset_name, shot_code):
            # A per-shot publish of another shot, e.g. that shot's camera
            logger.debug("  Skipping %s -- it names another shot", ref_ns)
            skipped += 1
            continue

        fields = _parse_publish_path(_reference_path(ref_node))

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
            if _fill_record(existing, asset_type, fields, config):
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
            _fill_record(new_asset.node_name, asset_type, fields, config)

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
