# -*- coding: utf-8 -*-

"""CTX Asset to Maya Node Linking Module.

This module provides functions for creating bidirectional links between CTX_Asset
metadata nodes and Maya asset nodes (aiStandIn, RedshiftProxyMesh, reference) using
message attributes.

Primary Method: Message attributes (bidirectional, auto-cleanup)
Fallback Method: String attributes (for locked reference nodes)
"""

import logging
from maya import cmds

logger = logging.getLogger(__name__)


def link_to_maya_node(ctx_asset_node, maya_node):
    """Link CTX_Asset to Maya node using message attributes.
    
    Creates a bidirectional connection using message attributes. Falls back to
    string attribute if the Maya node is locked (common with references).
    
    Args:
        ctx_asset_node (str): CTX_Asset node name
        maya_node (str): Maya node name (aiStandIn, RedshiftProxyMesh, reference)
        
    Returns:
        bool: True if message connection succeeded, False if fallback was used
        
    Raises:
        ValueError: If either node doesn't exist
    """
    # Validate inputs
    if not cmds.objExists(ctx_asset_node):
        raise ValueError("CTX_Asset node '{}' does not exist".format(ctx_asset_node))
    if not cmds.objExists(maya_node):
        raise ValueError("Maya node '{}' does not exist".format(maya_node))
    
    # Add targetNode message attribute to CTX_Asset if not exists
    if not cmds.attributeQuery('targetNode', node=ctx_asset_node, exists=True):
        cmds.addAttr(ctx_asset_node, longName='targetNode', attributeType='message')
        logger.debug("Added targetNode attribute to {}".format(ctx_asset_node))
    
    # Handle different node types
    node_type = cmds.nodeType(maya_node)
    
    # For references, try to get the reference node
    if node_type == 'reference':
        try:
            ref_node = cmds.referenceQuery(maya_node, referenceNode=True)
            maya_node = ref_node
            logger.debug("Using reference node: {}".format(ref_node))
        except RuntimeError:
            logger.debug("Could not get reference node for {}".format(maya_node))
    
    # Try to create message connection
    try:
        # For reference nodes, connect directly to .message without adding custom attributes
        # Reference nodes are locked and can't have custom attributes added
        if node_type == 'reference':
            # Connect reference.message -> CTX_Asset.targetNode
            cmds.connectAttr(
                '{}.message'.format(maya_node),
                '{}.targetNode'.format(ctx_asset_node),
                force=True
            )
            logger.info("Linked {} to reference {} using message attribute".format(
                ctx_asset_node, maya_node))
            return True
        else:
            # For other node types (aiStandIn, RedshiftProxyMesh), add custom attribute
            if not cmds.attributeQuery('ctx_metadata', node=maya_node, exists=True):
                cmds.addAttr(maya_node, longName='ctx_metadata', attributeType='message')
                logger.debug("Added ctx_metadata attribute to {}".format(maya_node))

            # Create connection: Maya node.message -> CTX_Asset.targetNode
            cmds.connectAttr(
                '{}.message'.format(maya_node),
                '{}.targetNode'.format(ctx_asset_node),
                force=True
            )

            logger.info("Linked {} to {} using message attribute".format(
                ctx_asset_node, maya_node))
            return True

    except RuntimeError as e:
        # Node is locked or connection failed - fall back to string attribute
        logger.warning("Cannot connect to node {}, using string fallback: {}".format(
            maya_node, str(e)))
        return _link_with_string_fallback(ctx_asset_node, maya_node)


def _link_with_string_fallback(ctx_asset_node, maya_node):
    """Fallback to string attribute for locked nodes.
    
    Args:
        ctx_asset_node (str): CTX_Asset node name
        maya_node (str): Maya node name
        
    Returns:
        bool: False (indicates fallback was used)
    """
    # Add targetNodeStr attribute if not exists
    if not cmds.attributeQuery('targetNodeStr', node=ctx_asset_node, exists=True):
        cmds.addAttr(ctx_asset_node, longName='targetNodeStr', dataType='string')
        logger.debug("Added targetNodeStr attribute to {}".format(ctx_asset_node))
    
    # Store node name as string
    cmds.setAttr('{}.targetNodeStr'.format(ctx_asset_node), maya_node, type='string')
    
    logger.info("Linked {} to {} using string fallback".format(ctx_asset_node, maya_node))
    return False


def get_linked_maya_node(ctx_asset_node):
    """Get Maya node linked to CTX_Asset.
    
    Queries message connection first, then falls back to string attribute.
    
    Args:
        ctx_asset_node (str): CTX_Asset node name
        
    Returns:
        str or None: Maya node name if found, None otherwise
    """
    if not cmds.objExists(ctx_asset_node):
        logger.warning("CTX_Asset node '{}' does not exist".format(ctx_asset_node))
        return None
    
    # Try message connection first
    if cmds.attributeQuery('targetNode', node=ctx_asset_node, exists=True):
        connections = cmds.listConnections('{}.targetNode'.format(ctx_asset_node))
        if connections:
            maya_node = connections[0]
            if cmds.objExists(maya_node):
                logger.debug("Found linked Maya node via message: {}".format(maya_node))
                return maya_node
    
    # Fall back to string attribute
    if cmds.attributeQuery('targetNodeStr', node=ctx_asset_node, exists=True):
        maya_node = cmds.getAttr('{}.targetNodeStr'.format(ctx_asset_node))
        if maya_node and cmds.objExists(maya_node):
            logger.debug("Found linked Maya node via string: {}".format(maya_node))
            return maya_node
        elif maya_node:
            logger.warning("Linked Maya node '{}' no longer exists".format(maya_node))
    
    return None


def get_linked_ctx_assets(maya_node):
    """Get all CTX_Assets linked to a Maya node.

    Queries reverse message connections to find all CTX_Asset nodes that
    reference this Maya node. Supports multi-shot workflow where one Maya
    node can be referenced by multiple CTX_Assets.

    Args:
        maya_node (str): Maya node name

    Returns:
        list: List of CTX_Asset node names
    """
    if not cmds.objExists(maya_node):
        logger.warning("Maya node '{}' does not exist".format(maya_node))
        return []

    # Query reverse connection via ctx_metadata attribute
    if cmds.attributeQuery('ctx_metadata', node=maya_node, exists=True):
        connections = cmds.listConnections('{}.ctx_metadata'.format(maya_node))
        if connections:
            logger.debug("Found {} CTX_Assets linked to {}".format(len(connections), maya_node))
            return connections

    return []


def unlink_from_maya_node(ctx_asset_node):
    """Remove link between CTX_Asset and Maya node.

    Breaks message connection or clears string attribute.

    Args:
        ctx_asset_node (str): CTX_Asset node name

    Returns:
        bool: True if unlink succeeded, False otherwise
    """
    if not cmds.objExists(ctx_asset_node):
        logger.warning("CTX_Asset node '{}' does not exist".format(ctx_asset_node))
        return False

    # Try to disconnect message connection
    if cmds.attributeQuery('targetNode', node=ctx_asset_node, exists=True):
        connections = cmds.listConnections(
            '{}.targetNode'.format(ctx_asset_node),
            source=True,
            destination=False,
            plugs=True
        )
        if connections:
            try:
                cmds.disconnectAttr(connections[0], '{}.targetNode'.format(ctx_asset_node))
                logger.info("Unlinked {} from Maya node".format(ctx_asset_node))
                return True
            except RuntimeError as e:
                logger.warning("Failed to disconnect: {}".format(str(e)))

    # Clear string attribute if exists
    if cmds.attributeQuery('targetNodeStr', node=ctx_asset_node, exists=True):
        cmds.setAttr('{}.targetNodeStr'.format(ctx_asset_node), '', type='string')
        logger.info("Cleared string link for {}".format(ctx_asset_node))
        return True

    return False

