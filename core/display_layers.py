# -*- coding: utf-8 -*-
"""Display Layer Management - Manage shot-specific visibility using display layers.

This module provides display layer management functionality:
- Create display layers for shots
- Assign assets to layers
- Control layer visibility
- Query layer contents
- Cleanup empty/orphaned layers

Author: Pipeline TD
Date: 2024
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging

logger = logging.getLogger(__name__)

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    # Mock Maya commands for testing outside Maya
    class MockCmds(object):
        """Mock Maya commands for testing."""
        
        def createDisplayLayer(self, name=None, empty=True, noRecurse=False):
            """Mock createDisplayLayer."""
            return name if name else "displayLayer1"
        
        def objExists(self, name):
            """Mock objExists."""
            return False
        
        def editDisplayLayerMembers(self, layer, *nodes, **kwargs):
            """Mock editDisplayLayerMembers."""
            pass
        
        def setAttr(self, attr, value):
            """Mock setAttr."""
            pass
        
        def getAttr(self, attr):
            """Mock getAttr."""
            return 1
        
        def listConnections(self, node, **kwargs):
            """Mock listConnections."""
            return []
        
        def ls(self, *args, **kwargs):
            """Mock ls."""
            return []
        
        def delete(self, *nodes):
            """Mock delete."""
            pass
    
    cmds = MockCmds()
    MAYA_AVAILABLE = False


class DisplayLayerManager(object):
    """Manage display layers for shot-specific visibility.

    Uses 2 global layers:
    - CTX_Active: Contains assets for the ACTIVE shot (visible)
    - CTX_Inactive: Contains assets for INACTIVE shots (hidden)

    When switching shots, assets are moved between these layers.

    Example:
        >>> from core.display_layers import DisplayLayerManager
        >>>
        >>> layer_mgr = DisplayLayerManager()
        >>>
        >>> # Ensure global layers exist
        >>> layer_mgr.ensure_global_layers()
        >>>
        >>> # Assign asset to active layer
        >>> layer_mgr.assign_to_active_layer('pCube1')
        >>>
        >>> # Move asset to inactive layer
        >>> layer_mgr.assign_to_inactive_layer('pCube1')
    """

    ACTIVE_LAYER = "CTX_Active"
    INACTIVE_LAYER = "CTX_Inactive"

    def __init__(self):
        """Initialize display layer manager."""
        # Ensure global layers exist
        self.ensure_global_layers()

    def ensure_global_layers(self):
        """Ensure CTX_Active and CTX_Inactive layers exist.

        Creates the layers if they don't exist and sets their visibility.
        """
        # Create CTX_Active layer (visible)
        if not cmds.objExists(self.ACTIVE_LAYER):
            cmds.createDisplayLayer(name=self.ACTIVE_LAYER, empty=True, noRecurse=True)
            logger.info("Created active layer: {}".format(self.ACTIVE_LAYER))

        # Set active layer visible
        self.show_layer(self.ACTIVE_LAYER)

        # Create CTX_Inactive layer (hidden)
        if not cmds.objExists(self.INACTIVE_LAYER):
            cmds.createDisplayLayer(name=self.INACTIVE_LAYER, empty=True, noRecurse=True)
            logger.info("Created inactive layer: {}".format(self.INACTIVE_LAYER))

        # Set inactive layer hidden
        self.hide_layer(self.INACTIVE_LAYER)

    def _connect_visibility_to_active(self, shot_node, layer_name):
        """Connect display layer visibility to CTX_Shot is_active attribute.

        This creates a direct Maya connection so that when the shot's is_active
        attribute changes, the display layer visibility automatically updates.

        Args:
            shot_node (str): CTX_Shot node name
            layer_name (str): Display layer name
        """
        logger.info("=" * 60)
        logger.info("CONNECTING VISIBILITY TO IS_ACTIVE")
        logger.info("Shot node: {}".format(shot_node))
        logger.info("Layer name: {}".format(layer_name))

        if not cmds.objExists(shot_node):
            logger.warning("Shot node does not exist: {}".format(shot_node))
            return

        if not cmds.objExists(layer_name):
            logger.warning("Layer does not exist: {}".format(layer_name))
            return

        # Check if connection already exists
        source_attr = "{}.is_active".format(shot_node)
        dest_attr = "{}.visibility".format(layer_name)

        logger.info("Source attr: {}".format(source_attr))
        logger.info("Dest attr: {}".format(dest_attr))

        # Check if already connected
        connections = cmds.listConnections(dest_attr, source=True, destination=False, plugs=True) or []
        logger.info("Existing connections to {}: {}".format(dest_attr, connections))

        if source_attr in connections:
            logger.info("Already connected! Skipping.")
            return  # Already connected

        # Disconnect any existing connections to visibility
        if connections:
            logger.info("Disconnecting existing connections...")
            for conn in connections:
                try:
                    cmds.disconnectAttr(conn, dest_attr)
                    logger.info("Disconnected: {} -> {}".format(conn, dest_attr))
                except Exception as e:
                    logger.warning("Failed to disconnect {}: {}".format(conn, e))

        # Connect is_active to visibility
        try:
            logger.info("Connecting {} -> {}".format(source_attr, dest_attr))
            cmds.connectAttr(source_attr, dest_attr, force=True)
            logger.info("SUCCESS! Connection established.")

            # Verify connection
            is_connected = cmds.isConnected(source_attr, dest_attr)
            logger.info("Verification: isConnected = {}".format(is_connected))
        except Exception as e:
            logger.error("FAILED to connect: {}".format(e))
            logger.error("Will fall back to manual visibility control")

        logger.info("=" * 60)

    def create_display_layer(self, ep_code, seq_code, shot_code, shot_node=None):
        """Create display layer for shot and link to CTX_Shot node.

        Args:
            ep_code (str): Episode code (e.g., 'Ep04')
            seq_code (str): Sequence code (e.g., 'sq0070')
            shot_code (str): Shot code (e.g., 'SH0170')
            shot_node (CTXShotNode, optional): CTX_Shot node to link to

        Returns:
            str: Layer name
        """
        # Build layer name
        layer_name = "{}{}_{}_{}".format(self.LAYER_PREFIX, ep_code, seq_code, shot_code)

        # Check if layer already exists
        if cmds.objExists(layer_name):
            # Link to shot node if provided and not already linked
            if shot_node:
                shot_node.link_display_layer(layer_name)
                # Connect is_active to visibility
                self._connect_visibility_to_active(shot_node.node_name, layer_name)
            return layer_name

        # Create new layer
        cmds.createDisplayLayer(name=layer_name, empty=True, noRecurse=True)

        # Set visible by default
        self.show_layer(layer_name)

        # Link to shot node if provided
        if shot_node:
            shot_node.link_display_layer(layer_name)
            # Connect is_active to visibility
            self._connect_visibility_to_active(shot_node.node_name, layer_name)

        return layer_name
    
    def assign_to_layer(self, maya_node, layer_name):
        """Assign Maya node to display layer using drawInfo -> drawOverride connection.

        This creates a proper Maya connection between the display layer and the transform node:
        DisplayLayer.drawInfo -> Transform.drawOverride

        Args:
            maya_node (str): Maya node name (can be reference node, shape, or transform)
            layer_name (str): Display layer name
        """
        logger.info("=" * 80)
        logger.info("ASSIGN_TO_LAYER CALLED")
        logger.info("  maya_node: {}".format(maya_node))
        logger.info("  layer_name: {}".format(layer_name))
        logger.info("=" * 80)

        if not cmds.objExists(layer_name):
            logger.error("Layer '{}' does not exist!".format(layer_name))
            raise ValueError("Layer '{}' does not exist".format(layer_name))

        if not cmds.objExists(maya_node):
            logger.error("Node '{}' does not exist!".format(maya_node))
            raise ValueError("Node '{}' does not exist".format(maya_node))

        logger.info("Both layer and node exist - proceeding...")

        # Get the top-level transform nodes
        top_nodes = self._get_top_nodes_from_asset(maya_node)

        if not top_nodes:
            logger.warning("No top nodes found for: {}".format(maya_node))
            return

        logger.info("Found {} top nodes for {}: {}".format(
            len(top_nodes), maya_node, top_nodes))

        # Connect each top node to the display layer
        for top_node in top_nodes:
            logger.info("Connecting top node: {}".format(top_node))
            self._connect_node_to_layer(top_node, layer_name)

        logger.info("=" * 80)

    def assign_to_layer_from_ctx_asset(self, ctx_asset_node, shot_node):
        """Assign asset to display layer based on shot active status.

        If shot is active, assign to CTX_Active layer.
        If shot is inactive, assign to CTX_Inactive layer.

        Args:
            ctx_asset_node (CTXAssetNode): CTX_Asset node instance
            shot_node (CTXShotNode): CTX_Shot node instance

        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("=" * 80)
        logger.info("ASSIGN_TO_LAYER_FROM_CTX_ASSET CALLED")
        logger.info("  ctx_asset_node: {}".format(ctx_asset_node.node_name))
        logger.info("  shot_node: {}".format(shot_node.node_name))
        logger.info("=" * 80)

        # Determine which layer to use based on shot active status
        is_active = shot_node.is_active()
        layer_name = self.ACTIVE_LAYER if is_active else self.INACTIVE_LAYER

        logger.info("Shot is_active: {}".format(is_active))
        logger.info("Target layer: {}".format(layer_name))

        # Ensure global layers exist
        self.ensure_global_layers()

        # Get namespace from CTX_Asset
        namespace = ctx_asset_node.get_namespace()
        logger.debug("Asset namespace: {}".format(namespace))

        if not namespace:
            logger.error("CTX_Asset has no namespace set")
            return False

        # Get the root/top node from namespace using simple helper function
        top_node = self._get_namespace_root(namespace)

        if not top_node:
            logger.warning("No top node found for namespace '{}'".format(namespace))
            return False

        logger.info("Found top node: {}".format(top_node))

        # Connect the top node to the display layer
        logger.info("Connecting top node to layer {}...".format(layer_name))
        self._connect_node_to_layer(top_node, layer_name)

        logger.info("=" * 80)
        return True

    def move_shot_assets_to_layer(self, shot_node, target_layer):
        """Move all assets of a shot to a specific layer.

        Args:
            shot_node (CTXShotNode): Shot node instance
            target_layer (str): Target layer name (CTX_Active or CTX_Inactive)

        Returns:
            int: Number of assets moved
        """
        logger.info("=" * 80)
        logger.info("MOVING SHOT ASSETS TO LAYER")
        logger.info("  Shot: {}".format(shot_node.node_name))
        logger.info("  Target layer: {}".format(target_layer))
        logger.info("=" * 80)

        # Get all assets for this shot
        assets = shot_node.get_assets()
        logger.info("Found {} assets in shot".format(len(assets)))

        moved_count = 0
        for asset in assets:
            namespace = asset.get_namespace()
            if not namespace:
                logger.warning("Asset {} has no namespace - skipping".format(asset.node_name))
                continue

            # Get top node
            top_node = self._get_namespace_root(namespace)
            if not top_node:
                logger.warning("No top node found for namespace '{}' - skipping".format(namespace))
                continue

            # Move to target layer
            logger.info("Moving {} to {}".format(top_node, target_layer))
            self._connect_node_to_layer(top_node, target_layer)
            moved_count += 1

        logger.info("Moved {} assets to {}".format(moved_count, target_layer))
        logger.info("=" * 80)
        return moved_count

    def switch_shot_layers(self, active_shot_node, all_shot_nodes):
        """Switch display layers when changing active shot.

        Uses full asset list subtraction approach:
        1. Collect ALL unique assets from ALL shots (using namespace as key)
        2. Collect active shot's assets
        3. Calculate inactive assets = all assets - active assets
        4. Move active assets to CTX_Active layer
        5. Move inactive assets to CTX_Inactive layer

        This ensures shared assets are handled correctly - if an asset is in
        the active shot, it will be visible (even if it's also in other shots).

        Args:
            active_shot_node (CTXShotNode): The shot being activated
            all_shot_nodes (list): List of all CTXShotNode instances

        Returns:
            dict: Statistics {active_moved: int, inactive_moved: int,
                             total_assets: int, shared_assets: int}
        """
        logger.info("=" * 80)
        logger.info("SWITCHING SHOT LAYERS (Full Asset List Subtraction)")
        logger.info("  Active shot: {}".format(active_shot_node.node_name))
        logger.info("  Total shots: {}".format(len(all_shot_nodes)))
        logger.info("=" * 80)

        stats = {
            'active_moved': 0,
            'inactive_moved': 0,
            'total_assets': 0,
            'shared_assets': 0,
            'skipped': 0
        }

        # Ensure global layers exist
        self.ensure_global_layers()

        # Step 1: Collect ALL unique assets from ALL shots (using namespace as key)
        logger.info("Step 1: Collecting all assets from all shots...")
        all_assets = set()  # Use set to avoid duplicates
        asset_shot_count = {}  # Track how many shots each asset appears in

        for shot_node in all_shot_nodes:
            shot_code = shot_node.get_shot_code()
            assets = shot_node.get_assets()
            logger.info("  Shot {}: {} assets".format(shot_code, len(assets)))

            for asset in assets:
                namespace = asset.get_namespace()
                if namespace:
                    all_assets.add(namespace)
                    # Track asset usage across shots
                    if namespace not in asset_shot_count:
                        asset_shot_count[namespace] = 0
                    asset_shot_count[namespace] += 1

        stats['total_assets'] = len(all_assets)
        logger.info("Total unique assets found: {}".format(stats['total_assets']))

        # Count shared assets (assets used in multiple shots)
        stats['shared_assets'] = sum(1 for count in asset_shot_count.values() if count > 1)
        if stats['shared_assets'] > 0:
            logger.info("Shared assets (used in multiple shots): {}".format(stats['shared_assets']))
            for namespace, count in asset_shot_count.items():
                if count > 1:
                    logger.debug("  {} used in {} shots".format(namespace, count))

        # Step 2: Get assets for active shot
        logger.info("Step 2: Collecting active shot's assets...")
        active_assets = set()
        for asset in active_shot_node.get_assets():
            namespace = asset.get_namespace()
            if namespace:
                active_assets.add(namespace)

        logger.info("Active shot has {} assets".format(len(active_assets)))

        # Step 3: Calculate inactive assets (all - active)
        logger.info("Step 3: Calculating inactive assets...")
        inactive_assets = all_assets - active_assets
        logger.info("Inactive assets: {}".format(len(inactive_assets)))

        # Step 4: Move active assets to CTX_Active
        logger.info("Step 4: Moving active assets to CTX_Active...")
        for namespace in active_assets:
            top_node = self._get_namespace_root(namespace)
            if top_node:
                self._connect_node_to_layer(top_node, self.ACTIVE_LAYER)
                stats['active_moved'] += 1
            else:
                logger.warning("  No top node found for namespace: {}".format(namespace))
                stats['skipped'] += 1

        # Step 5: Move inactive assets to CTX_Inactive
        logger.info("Step 5: Moving inactive assets to CTX_Inactive...")
        for namespace in inactive_assets:
            top_node = self._get_namespace_root(namespace)
            if top_node:
                self._connect_node_to_layer(top_node, self.INACTIVE_LAYER)
                stats['inactive_moved'] += 1
            else:
                logger.warning("  No top node found for namespace: {}".format(namespace))
                stats['skipped'] += 1

        logger.info("=" * 80)
        logger.info("Layer switch complete:")
        logger.info("  Total assets: {}".format(stats['total_assets']))
        logger.info("  Active (visible): {}".format(stats['active_moved']))
        logger.info("  Inactive (hidden): {}".format(stats['inactive_moved']))
        logger.info("  Shared assets: {}".format(stats['shared_assets']))
        logger.info("  Skipped: {}".format(stats['skipped']))
        logger.info("=" * 80)

        return stats

    def _get_namespace_root(self, namespace):
        """Get the root/top transform node from a namespace.

        Returns top-level transforms that are directly under world or whose parent
        is outside the namespace. Uses full path checking to ensure we get the
        actual top nodes, not intermediate nodes.

        Args:
            namespace (str): Namespace (e.g., 'CHAR_CatStompie_002')

        Returns:
            str or None: Top node name, or None if not found
        """
        logger.debug("Getting top node for namespace: {}".format(namespace))

        # Ensure namespace has trailing colon for path checking
        ns_prefix = namespace.rstrip(":") + ":"

        # Get all transforms in this namespace (long names for accurate path checking)
        namespaced_nodes = cmds.ls('{}*'.format(ns_prefix), long=True, type='transform') or []
        logger.debug("Found {} transforms in namespace".format(len(namespaced_nodes)))

        if not namespaced_nodes:
            return None

        # Find top-level nodes
        top_nodes = []
        for node in namespaced_nodes:
            parents = cmds.listRelatives(node, parent=True, fullPath=True)

            # No parent → world root → top node
            if not parents:
                logger.info("Top node (world root): {}".format(node))
                top_nodes.append(node)
                continue

            # Parent exists but not in namespace → top node
            # Check if parent's full path starts with "|namespace:"
            parent_path = parents[0]
            if not parent_path.startswith("|" + ns_prefix):
                logger.debug("Top node (parent outside namespace): {}".format(node))
                top_nodes.append(node)

        if not top_nodes:
            logger.warning("No top node found in namespace '{}'".format(namespace))
            return None

        # Sort for consistency and return the first top node
        top_nodes = sorted(top_nodes)
        logger.info("Found {} top nodes, returning first: {}".format(len(top_nodes), top_nodes[0]))
        return top_nodes[0]

    def _get_top_nodes_from_asset(self, maya_node):
        """Get top-level transform nodes from an asset.

        Handles different node types:
        - Reference nodes: Get top-level nodes from reference
        - Shape nodes: Get parent transform
        - Transform nodes: Use as-is

        Args:
            maya_node (str): Maya node name

        Returns:
            list: List of top-level transform node names
        """
        node_type = cmds.nodeType(maya_node)
        logger.info("Getting top nodes for {} (type: {})".format(maya_node, node_type))

        # Handle reference nodes
        if node_type == 'reference':
            try:
                # Get all nodes from this reference
                ref_nodes = cmds.referenceQuery(maya_node, nodes=True, dagPath=True) or []
                logger.info("Reference has {} nodes".format(len(ref_nodes)))

                # Create a set for faster lookup
                ref_nodes_set = set(ref_nodes)

                # Filter for top-level transforms
                # A top-level node is a transform whose parent is NOT in the reference
                # (i.e., parent is outside the reference or is world)
                top_nodes = []
                for node in ref_nodes:
                    if cmds.nodeType(node) == 'transform':
                        # Get parent
                        parents = cmds.listRelatives(node, parent=True, fullPath=True) or []

                        # If no parent, it's top-level
                        if not parents:
                            top_nodes.append(node)
                            logger.info("Found top-level transform (no parent): {}".format(node))
                        # If parent is not in the reference, it's top-level
                        elif not any(p in ref_nodes_set for p in parents):
                            top_nodes.append(node)
                            logger.info("Found top-level transform (parent outside ref): {}".format(node))
                        else:
                            logger.debug("Skipping {} (parent {} is in reference)".format(
                                node, parents[0]))

                logger.info("Found {} top-level transforms total".format(len(top_nodes)))
                return top_nodes
            except Exception as e:
                logger.error("Failed to query reference nodes: {}".format(e))
                import traceback
                logger.error("Traceback: {}".format(traceback.format_exc()))
                return []

        # Handle shape nodes
        elif node_type in ['mesh', 'nurbsCurve', 'nurbsSurface', 'aiStandIn', 'RedshiftProxyMesh']:
            parents = cmds.listRelatives(maya_node, parent=True, fullPath=True) or []
            if parents:
                logger.info("Using parent transform: {}".format(parents[0]))
                return [parents[0]]
            else:
                logger.warning("Shape node has no parent: {}".format(maya_node))
                return [maya_node]

        # Handle transform nodes
        elif node_type == 'transform':
            return [maya_node]

        # Unknown node type
        else:
            logger.warning("Unknown node type: {}".format(node_type))
            return [maya_node]

    def _connect_node_to_layer(self, transform_node, layer_name):
        """Connect a single transform node to display layer.

        Args:
            transform_node (str): Transform node name
            layer_name (str): Display layer name
        """
        logger.info("  _connect_node_to_layer:")
        logger.info("    transform_node: {}".format(transform_node))
        logger.info("    layer_name: {}".format(layer_name))

        # Verify layer exists and has drawInfo attribute
        if not cmds.objExists(layer_name):
            logger.error("    Layer '{}' does not exist!".format(layer_name))
            return

        # Check layer type
        layer_type = cmds.nodeType(layer_name)
        logger.info("    Layer type: {}".format(layer_type))

        # Check if layer has drawInfo attribute
        if not cmds.attributeQuery('drawInfo', node=layer_name, exists=True):
            logger.error("    Layer '{}' does not have 'drawInfo' attribute!".format(layer_name))
            logger.error("    This might not be a display layer!")
            return

        try:
            # Verify node exists
            if not cmds.objExists(transform_node):
                logger.error("    Transform node does not exist: {}".format(transform_node))
                return

            # Verify it's a transform
            node_type = cmds.nodeType(transform_node)
            logger.info("    Node type: {}".format(node_type))

            if node_type != 'transform':
                logger.warning("    Node is not a transform! Type: {}".format(node_type))
                # Try to get parent if it's a shape
                if node_type in ['mesh', 'nurbsCurve', 'nurbsSurface']:
                    parents = cmds.listRelatives(transform_node, parent=True, fullPath=True)
                    if parents:
                        transform_node = parents[0]
                        logger.info("    Using parent transform: {}".format(transform_node))
                    else:
                        logger.error("    Cannot find parent transform!")
                        return

            # Connect drawInfo to drawOverride (no array index needed!)
            source_attr = "{}.drawInfo".format(layer_name)
            dest_attr = "{}.drawOverride".format(transform_node)

            logger.info("    Attempting connection:")
            logger.info("      Source: {}".format(source_attr))
            logger.info("      Dest: {}".format(dest_attr))

            # Check if this node is already connected to ANY layer
            existing_layer_conn = cmds.listConnections(dest_attr,
                                                       source=True,
                                                       destination=False) or []
            if existing_layer_conn:
                logger.info("    {} already connected to layer: {}".format(
                    transform_node, existing_layer_conn[0]))
                # Disconnect from old layer if it's different
                if existing_layer_conn[0] != layer_name:
                    old_conn = cmds.listConnections(dest_attr,
                                                    source=True,
                                                    destination=False,
                                                    plugs=True)[0]
                    cmds.disconnectAttr(old_conn, dest_attr)
                    logger.info("    Disconnected from old layer")
                else:
                    logger.info("    Already connected to correct layer - skipping")
                    return  # Already connected to correct layer

            # Connect to new layer
            cmds.connectAttr(source_attr, dest_attr, force=True)
            logger.info("    SUCCESS! Connected {} -> {}".format(source_attr, dest_attr))

            # Verify connection was made
            is_connected = cmds.isConnected(source_attr, dest_attr)
            logger.info("    Verification: Connection exists = {}".format(is_connected))

        except Exception as e:
            logger.error("    FAILED to connect {} to layer: {}".format(transform_node, e))
            import traceback
            logger.error("    Traceback: {}".format(traceback.format_exc()))
            # DO NOT use editDisplayLayerMembers as fallback!
            # editDisplayLayerMembers adds ALL child transforms recursively,
            # but we only want the TOP transform connected.
            logger.error("    Connection failed - NOT using editDisplayLayerMembers fallback")
    
    def assign_batch(self, maya_nodes, layer_name):
        """Assign multiple nodes to display layer.
        
        Args:
            maya_nodes (list): List of Maya node names
            layer_name (str): Display layer name
        """
        for node in maya_nodes:
            self.assign_to_layer(node, layer_name)
    
    def set_layer_visibility(self, layer_name, visible):
        """Set display layer visibility.

        Args:
            layer_name (str): Display layer name
            visible (bool): True to show, False to hide
        """
        if not cmds.objExists(layer_name):
            raise ValueError("Layer '{}' does not exist".format(layer_name))

        # Maya display layers use .visibility attribute
        # 0 = hidden, 1 = visible
        cmds.setAttr("{}.visibility".format(layer_name), 1 if visible else 0)

        # Refresh the Layer Editor UI using the correct MEL command
        # layerButton is the correct command for display layer UI updates
        try:
            import maya.mel as mel
            mel.eval('layerButton -edit -layerVisible {} "{}"'.format(
                1 if visible else 0, layer_name))
        except Exception as e:
            # If MEL command fails, try forcing viewport refresh
            try:
                cmds.refresh(force=True)
            except:
                pass

    def show_layer(self, layer_name):
        """Show display layer.

        Args:
            layer_name (str): Display layer name
        """
        self.set_layer_visibility(layer_name, True)

    def hide_layer(self, layer_name):
        """Hide display layer.

        Args:
            layer_name (str): Display layer name
        """
        self.set_layer_visibility(layer_name, False)

    def get_layer_for_shot(self, ep_code, seq_code, shot_code):
        """Get layer name for shot.

        NOTE: This method is deprecated in the 2-layer system.
        We now use global CTX_Active and CTX_Inactive layers instead of per-shot layers.

        Args:
            ep_code (str): Episode code
            seq_code (str): Sequence code
            shot_code (str): Shot code

        Returns:
            str: Always returns None (per-shot layers no longer used)
        """
        logger.warning("get_layer_for_shot() is deprecated - using global 2-layer system")
        return None

    def get_layer_members(self, layer_name):
        """Get nodes in display layer.

        Args:
            layer_name (str): Display layer name

        Returns:
            list: List of node names in layer
        """
        if not cmds.objExists(layer_name):
            return []

        # Query layer members
        members = cmds.editDisplayLayerMembers(layer_name, query=True, fullNames=True)

        return members if members else []

    def get_all_ctx_layers(self):
        """Get all CTX display layers.

        Returns:
            list: List of CTX layer names
        """
        # Get all display layers
        all_layers = cmds.ls(type='displayLayer')

        # Filter for CTX layers
        ctx_layers = [layer for layer in all_layers if layer.startswith(self.LAYER_PREFIX)]

        return ctx_layers

    def is_in_layer(self, maya_node, layer_name):
        """Check if node is in display layer.

        Args:
            maya_node (str): Maya node name
            layer_name (str): Display layer name

        Returns:
            bool: True if node is in layer
        """
        members = self.get_layer_members(layer_name)
        return maya_node in members

    def cleanup_empty_layers(self, dry_run=False):
        """Remove display layers with no members.

        Args:
            dry_run (bool): If True, only return layers that would be deleted

        Returns:
            list: List of deleted (or would-be-deleted) layer names
        """
        empty_layers = []

        # Get all CTX layers
        ctx_layers = self.get_all_ctx_layers()

        # Find empty layers
        for layer in ctx_layers:
            members = self.get_layer_members(layer)
            if not members:
                empty_layers.append(layer)

        # Delete if not dry run
        if not dry_run and empty_layers:
            for layer in empty_layers:
                cmds.delete(layer)

        return empty_layers

    def cleanup_orphaned_layers(self, shot_nodes, dry_run=False):
        """Remove layers not linked to any shot nodes.

        Args:
            shot_nodes (list): List of CTX_Shot node names
            dry_run (bool): If True, only return layers that would be deleted

        Returns:
            list: List of deleted (or would-be-deleted) layer names
        """
        orphaned_layers = []

        # Get all CTX layers
        ctx_layers = self.get_all_ctx_layers()

        # Build set of valid layer names from shot nodes
        valid_layers = set()
        for shot_node in shot_nodes:
            # Extract ep, seq, shot from node attributes
            if cmds.objExists(shot_node):
                try:
                    ep = cmds.getAttr("{}.ep_code".format(shot_node))
                    seq = cmds.getAttr("{}.seq_code".format(shot_node))
                    shot = cmds.getAttr("{}.shot_code".format(shot_node))
                    layer_name = "{}{}_{}_{}".format(self.LAYER_PREFIX, ep, seq, shot)
                    valid_layers.add(layer_name)
                except:
                    pass

        # Find orphaned layers
        for layer in ctx_layers:
            if layer not in valid_layers:
                orphaned_layers.append(layer)

        # Delete if not dry run
        if not dry_run and orphaned_layers:
            for layer in orphaned_layers:
                cmds.delete(layer)

        return orphaned_layers

