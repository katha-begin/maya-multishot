# -*- coding: utf-8 -*-
"""CTX Converter - Convert existing Maya assets to CTX-managed assets.

This module provides utilities to:
- Detect existing assets in Maya scene
- Check if assets are CTX-ready (have CTX_Asset nodes)
- Convert non-CTX assets to CTX-managed assets
- Link Maya nodes to CTX_Asset nodes using message attributes
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import logging

# Import message attribute linking functions
from core.ctx_linker import link_to_maya_node, get_linked_maya_node, get_linked_ctx_assets

logger = logging.getLogger(__name__)

# Import Maya commands
try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    logger.warning("Maya not available - using mock")
    # Mock Maya commands for testing outside Maya
    class MockCmds(object):
        """Mock Maya commands for testing."""

        def __init__(self):
            self._nodes = {}
            self._node_counter = 0

        def ls(self, *args, **kwargs):
            """Mock ls."""
            node_type = kwargs.get('type')
            if node_type:
                return [n for n, data in self._nodes.items() if data.get('type') == node_type]
            return list(self._nodes.keys())

        def objExists(self, name):
            """Mock objExists."""
            return name in self._nodes

        def getAttr(self, attr):
            """Mock getAttr."""
            node_name = attr.split('.')[0]
            attr_name = attr.split('.')[1] if '.' in attr else None
            if node_name in self._nodes and attr_name:
                return self._nodes[node_name].get('attrs', {}).get(attr_name)
            return None

        def setAttr(self, attr, value, **kwargs):
            """Mock setAttr."""
            node_name = attr.split('.')[0]
            attr_name = attr.split('.')[1] if '.' in attr else None
            if node_name in self._nodes and attr_name:
                if 'attrs' not in self._nodes[node_name]:
                    self._nodes[node_name]['attrs'] = {}
                self._nodes[node_name]['attrs'][attr_name] = value

        def addAttr(self, node, **kwargs):
            """Mock addAttr."""
            if node not in self._nodes:
                self._nodes[node] = {'attrs': {}}

        def attributeQuery(self, attr, node=None, exists=True):
            """Mock attributeQuery."""
            if node and node in self._nodes:
                return attr in self._nodes[node].get('attrs', {})
            return False

        def nodeType(self, node):
            """Mock nodeType."""
            if node in self._nodes:
                return self._nodes[node].get('type')
            return None

        def createNode(self, node_type, **kwargs):
            """Mock createNode."""
            self._node_counter += 1
            name = kwargs.get('name', 'node{}'.format(self._node_counter))
            self._nodes[name] = {'type': node_type, 'attrs': {}}
            return name

        def connectAttr(self, src, dst, **kwargs):
            """Mock connectAttr."""
            pass

    cmds = MockCmds()
    MAYA_AVAILABLE = False


class CTXConverter(object):
    """Convert existing Maya assets to CTX-managed assets."""
    
    def __init__(self):
        """Initialize CTX converter."""
        pass
    
    def detect_scene_assets(self):
        """Detect all assets in the current Maya scene.

        Scans for aiStandIn, RedshiftProxyMesh, and reference nodes.
        For each, extracts namespace and checks for linked CTX_Asset nodes.

        Returns:
            list: List of dicts with asset info:
                {
                    'maya_node': str,       # Maya node name
                    'node_type': str,       # aiStandIn, RedshiftProxyMesh, reference
                    'file_path': str,       # Current file path
                    'namespace': str,       # Namespace (e.g., 'CHAR_CatStompie_001')
                    'ctx_ready': bool,      # Has CTX_Asset node linked
                    'ctx_node': str or None  # CTX_Asset node name if linked
                }
        """
        assets = []

        # Detect Arnold StandIns
        standins = cmds.ls(type='aiStandIn') or []
        for node in standins:
            file_path = cmds.getAttr('{}.dso'.format(node))
            # Derive namespace from parent transform or node hierarchy
            namespace = self._get_node_namespace(node)
            ctx_node = self._find_ctx_node_by_namespace(namespace)

            assets.append({
                'maya_node': node,
                'node_type': 'aiStandIn',
                'file_path': file_path,
                'namespace': namespace,
                'ctx_ready': ctx_node is not None,
                'ctx_node': ctx_node
            })

        # Detect Redshift Proxies
        rs_proxies = cmds.ls(type='RedshiftProxyMesh') or []
        for node in rs_proxies:
            file_path = cmds.getAttr('{}.fileName'.format(node))
            namespace = self._get_node_namespace(node)
            ctx_node = self._find_ctx_node_by_namespace(namespace)

            assets.append({
                'maya_node': node,
                'node_type': 'RedshiftProxyMesh',
                'file_path': file_path,
                'namespace': namespace,
                'ctx_ready': ctx_node is not None,
                'ctx_node': ctx_node
            })

        # Detect Maya References
        references = cmds.ls(type='reference') or []
        for ref_node in references:
            # Skip default references
            if ref_node in ['sharedReferenceNode', '_UNKNOWN_REF_NODE_']:
                continue

            try:
                file_path = cmds.referenceQuery(ref_node, filename=True)
                if not file_path:
                    continue

                # Get reference namespace - strip leading colon
                namespace = cmds.referenceQuery(ref_node, namespace=True)
                if namespace and namespace.startswith(':'):
                    namespace = namespace[1:]

                ctx_node = self._find_ctx_node_by_namespace(namespace)

                assets.append({
                    'maya_node': ref_node,
                    'node_type': 'reference',
                    'file_path': file_path,
                    'namespace': namespace,
                    'ctx_ready': ctx_node is not None,
                    'ctx_node': ctx_node
                })

            except Exception as e:
                logger.warning("Failed to query reference {}: {}".format(ref_node, e))
                continue

        logger.info("Detected {} assets in scene ({} CTX-ready)".format(
            len(assets),
            sum(1 for a in assets if a['ctx_ready'])
        ))

        return assets

    def _get_node_namespace(self, node):
        """Get namespace for a Maya node.

        Args:
            node (str): Maya node name

        Returns:
            str: Namespace (e.g., 'CHAR_CatStompie_001'), or empty string
        """
        if ':' in node:
            return node.split(':')[0]
        # No namespace - check parent
        parents = cmds.listRelatives(node, parent=True, fullPath=False) or []
        if parents and ':' in parents[0]:
            return parents[0].split(':')[0]
        return ''

    def _find_ctx_node_by_namespace(self, namespace):
        """Find CTX_Asset node by matching namespace attribute.

        This is the PRIMARY detection method. The namespace attribute on
        CTX_Asset (e.g., 'CHAR_CatStompie_001') matches the Maya reference
        namespace exactly.

        Args:
            namespace (str): Namespace to search for (e.g., 'CHAR_CatStompie_001')

        Returns:
            str or None: First matching CTX_Asset node name, or None
        """
        if not namespace:
            return None

        all_network = cmds.ls(type='network') or []
        ctx_asset_nodes = [n for n in all_network if n.startswith('CTX_Asset_')]

        for ctx_node in ctx_asset_nodes:
            if not cmds.attributeQuery('namespace', node=ctx_node, exists=True):
                continue
            node_ns = cmds.getAttr('{}.namespace'.format(ctx_node))
            if node_ns == namespace:
                return ctx_node

        return None

    def find_all_ctx_nodes_by_namespace(self, namespace):
        """Find ALL CTX_Asset nodes matching a namespace (across shots).

        Multiple shots can share the same Maya reference. This returns all
        CTX_Asset nodes for that namespace.

        Args:
            namespace (str): Namespace to search for

        Returns:
            list: List of CTX_Asset node names
        """
        if not namespace:
            return []

        results = []
        all_network = cmds.ls(type='network') or []
        ctx_asset_nodes = [n for n in all_network if n.startswith('CTX_Asset_')]

        for ctx_node in ctx_asset_nodes:
            if not cmds.attributeQuery('namespace', node=ctx_node, exists=True):
                continue
            node_ns = cmds.getAttr('{}.namespace'.format(ctx_node))
            if node_ns == namespace:
                results.append(ctx_node)

        return results

    def find_maya_node_by_namespace(self, namespace):
        """Find Maya reference node by namespace.

        Searches all references in scene for one with matching namespace.
        For cameras, also tries with CAM_ prefix since Maya references may have it.

        Args:
            namespace (str): Expected namespace (e.g., 'CHAR_CatStompie_001' or 'SWA_Ep04_SH0140_camera')

        Returns:
            str or None: Maya reference node name, or None
        """
        if not namespace:
            return None

        references = cmds.ls(type='reference') or []

        # Build list of namespace variations to try
        namespace_variations = [namespace]

        # For cameras (no type prefix in CTX namespace), also try with CAM_ prefix
        if '_camera' in namespace and not namespace.startswith('CAM_'):
            namespace_variations.append('CAM_' + namespace)

        for ref_node in references:
            if ref_node in ['sharedReferenceNode', '_UNKNOWN_REF_NODE_']:
                continue
            try:
                ref_ns = cmds.referenceQuery(ref_node, namespace=True)
                if ref_ns and ref_ns.startswith(':'):
                    ref_ns = ref_ns[1:]

                # Check all namespace variations
                if ref_ns in namespace_variations:
                    logger.debug("Found Maya reference {} with namespace {} (matched {})".format(
                        ref_node, ref_ns, namespace))
                    return ref_node
            except Exception:
                continue

        logger.debug("No Maya reference found for namespace '{}' (tried: {})".format(
            namespace, namespace_variations))
        return None

    def link_ctx_asset_to_scene(self, ctx_asset_node):
        """Link a CTX_Asset node to its matching Maya scene node by namespace.

        Reads the namespace attribute from the CTX_Asset, finds the matching
        Maya reference in scene, and creates a message attribute connection.

        Args:
            ctx_asset_node (str): CTX_Asset node name

        Returns:
            bool: True if link was created, False otherwise
        """
        if not cmds.objExists(ctx_asset_node):
            return False

        if not cmds.attributeQuery('namespace', node=ctx_asset_node, exists=True):
            return False

        namespace = cmds.getAttr('{}.namespace'.format(ctx_asset_node))
        if not namespace:
            return False

        maya_node = self.find_maya_node_by_namespace(namespace)
        if not maya_node:
            logger.debug("No Maya node found for namespace '{}'".format(namespace))
            return False

        # Link using message attribute
        linked = link_to_maya_node(ctx_asset_node, maya_node)
        logger.info("Linked {} to {} (namespace: {})".format(
            ctx_asset_node, maya_node, namespace))
        return True
    
    def _find_ctx_node_by_identity(self, asset_type, asset_name, variant, shot_code):
        """Find CTX_Asset node by asset identity (type + name + variant + shot).

        This is the PRIMARY method for finding CTX nodes. It searches by asset identity
        instead of Maya node reference, which is more reliable.

        Args:
            asset_type (str): Asset type (e.g., 'CHAR')
            asset_name (str): Asset name (e.g., 'CatStompie')
            variant (str): Variant (e.g., '001')
            shot_code (str): Shot code (e.g., 'SH0140')

        Returns:
            str or None: CTX_Asset node name if found
        """
        logger.info("  _find_ctx_node_by_identity: Searching for {} {} {} in shot {}".format(
            asset_type, asset_name, variant, shot_code))

        # Get all CTX_Asset nodes
        all_network = cmds.ls(type='network') or []
        ctx_asset_nodes = [n for n in all_network if n.startswith('CTX_Asset_')]
        logger.info("    Found {} CTX_Asset nodes total".format(len(ctx_asset_nodes)))

        for ctx_node in ctx_asset_nodes:
            # Check if node has required attributes
            if not cmds.attributeQuery('asset_type', node=ctx_node, exists=True):
                continue
            if not cmds.attributeQuery('asset_name', node=ctx_node, exists=True):
                continue
            if not cmds.attributeQuery('variant', node=ctx_node, exists=True):
                continue

            # Get node's identity
            node_type = cmds.getAttr('{}.asset_type'.format(ctx_node))
            node_name = cmds.getAttr('{}.asset_name'.format(ctx_node))
            node_variant = cmds.getAttr('{}.variant'.format(ctx_node))

            # Check if node belongs to this shot
            # Method 1: Check if node name contains shot code
            if shot_code not in ctx_node:
                continue

            # Match identity
            if (node_type == asset_type and
                node_name == asset_name and
                node_variant == variant):
                logger.info("    Found CTX node by identity: {}".format(ctx_node))
                return ctx_node

        logger.info("    No CTX node found for identity: {} {} {} {}".format(
            asset_type, asset_name, variant, shot_code))
        return None

    def _find_ctx_node_for_maya_node(self, maya_node):
        """Find CTX_Asset node that references this Maya node.

        Uses message attribute connections (primary) or string attributes (fallback).

        Args:
            maya_node (str): Maya node name

        Returns:
            str or None: CTX_Asset node name if found
        """
        logger.info("  _find_ctx_node_for_maya_node: Searching for CTX node linked to '{}'".format(maya_node))

        # Try message connection first (fast, direct query)
        ctx_assets = get_linked_ctx_assets(maya_node)
        logger.info("    Message connection query returned: {}".format(ctx_assets))
        if ctx_assets:
            logger.info("    Found CTX node via message: {}".format(ctx_assets[0]))
            return ctx_assets[0]  # Return first CTX_Asset found

        # Fall back to scanning all CTX_Asset nodes for string attribute links
        all_network = cmds.ls(type='network') or []
        ctx_asset_nodes = [n for n in all_network if n.startswith('CTX_Asset_')]
        logger.info("    Scanning {} CTX_Asset nodes for string attribute links".format(len(ctx_asset_nodes)))

        for ctx_node in ctx_asset_nodes:
            # Check old maya_node string attribute (backward compatibility)
            if cmds.attributeQuery('maya_node', node=ctx_node, exists=True):
                linked_node = cmds.getAttr('{}.maya_node'.format(ctx_node))
                if linked_node == maya_node:
                    logger.info("    Found CTX node via maya_node string attr: {}".format(ctx_node))
                    return ctx_node

            # Check new targetNodeStr string attribute (fallback)
            if cmds.attributeQuery('targetNodeStr', node=ctx_node, exists=True):
                linked_node = cmds.getAttr('{}.targetNodeStr'.format(ctx_node))
                if linked_node == maya_node:
                    logger.info("    Found CTX node via targetNodeStr string attr: {}".format(ctx_node))
                    return ctx_node

        logger.info("    No CTX node found for maya_node '{}'".format(maya_node))
        return None
    
    def convert_to_ctx(self, maya_node, shot_node, asset_type, asset_name, variant, version, dept='anim'):
        """Convert existing Maya asset to CTX-managed asset.

        Args:
            maya_node (str): Maya node name (aiStandIn, RedshiftProxyMesh, etc.)
            shot_node (str): CTX_Shot node name
            asset_type (str): Asset type (CHAR, PROP, SET, VEH, CAM)
            asset_name (str): Asset name
            variant (str): Variant (e.g., '001')
            version (str): Version (e.g., 'v003')
            dept (str): Department (default: 'anim')

        Returns:
            str: Created CTX_Asset node name

        Raises:
            ValueError: If maya_node doesn't exist or shot_node invalid
        """
        from core.custom_nodes import CTXAssetNode, CTXShotNode

        # Validate inputs
        if not cmds.objExists(maya_node):
            raise ValueError("Maya node '{}' does not exist".format(maya_node))

        # Handle shot_node - could be string or CTXShotNode object
        if isinstance(shot_node, CTXShotNode):
            shot_node_obj = shot_node
            shot_node_name = shot_node.node_name
        else:
            shot_node_name = shot_node
            shot_node_obj = CTXShotNode(shot_node)

        # Validate shot node exists
        if not cmds.objExists(shot_node_name):
            raise ValueError("Shot node '{}' does not exist".format(shot_node_name))

        # Check if CTX_Asset node already exists by namespace or identity
        namespace = "{}_{}_{}".format(asset_type, asset_name, variant)
        shot_code = shot_node_obj.get_shot_code()
        logger.info("=" * 80)
        logger.info("CONVERT_TO_CTX DEBUG:")
        logger.info("  maya_node: {}".format(maya_node))
        logger.info("  namespace: {}".format(namespace))
        logger.info("  shot_code: {}".format(shot_code))
        logger.info("  version to set: {}".format(version))

        # Primary: find by namespace for this shot
        existing_ctx_node = self._find_ctx_node_by_identity(
            asset_type, asset_name, variant, shot_code)
        # Fallback: find by Maya node link
        if not existing_ctx_node:
            existing_ctx_node = self._find_ctx_node_for_maya_node(maya_node)
        logger.info("  existing_ctx_node found: {}".format(existing_ctx_node))

        if existing_ctx_node:
            logger.info("CTX_Asset node already exists for {}: {}".format(maya_node, existing_ctx_node))

            # Update existing node instead of creating new one
            ctx_node = CTXAssetNode(existing_ctx_node)

            # Update version if different
            current_version = ctx_node.get_version()
            logger.info("  current version in CTX node: {}".format(current_version))
            if current_version != version:
                logger.info("  Updating version from {} to {}".format(current_version, version))
                ctx_node.set_version(version)
            else:
                logger.info("  Version unchanged: {}".format(current_version))

            # Ensure link to Maya node exists
            link_to_maya_node(existing_ctx_node, maya_node)

            logger.info("  Returning existing CTX node: {}".format(ctx_node.node_name))
            logger.info("=" * 80)
            return ctx_node.node_name

        # Get file path from Maya node
        node_type = cmds.nodeType(maya_node)
        if node_type == 'aiStandIn':
            file_path = cmds.getAttr('{}.dso'.format(maya_node))
        elif node_type == 'RedshiftProxyMesh':
            file_path = cmds.getAttr('{}.fileName'.format(maya_node))
        elif node_type == 'reference':
            file_path = cmds.referenceQuery(maya_node, filename=True)
        else:
            raise ValueError("Unsupported node type: {}".format(node_type))

        # Create NEW CTX_Asset node (only if doesn't exist)
        logger.info("Creating new CTX_Asset node for {}".format(maya_node))
        ctx_node = CTXAssetNode.create_asset(
            asset_type=asset_type,
            asset_name=asset_name,
            variant=variant,
            shot_node=shot_node_obj
        )

        # Set attributes
        ctx_node.set_file_path(file_path)
        ctx_node.set_version(version)
        ctx_node.set_namespace('{}_{}_{}' .format(asset_type, asset_name, variant))

        # Link to Maya node using message attributes (with string fallback)
        use_message = link_to_maya_node(ctx_node.node_name, maya_node)

        if use_message:
            logger.info("Converted {} to CTX-managed asset: {} (message link)".format(
                maya_node, ctx_node.node_name))
        else:
            logger.info("Converted {} to CTX-managed asset: {} (string fallback)".format(
                maya_node, ctx_node.node_name))

        # Note: Connection to shot node is already done in create_asset()
        # No need to connect again here

        return ctx_node.node_name

