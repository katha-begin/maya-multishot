# -*- coding: utf-8 -*-
"""Shot Manager - High-level tool for managing shots in the scene.

This module provides shot management functionality:
- Create, delete, duplicate shots
- Get shot information
- List all shots
- Validate shot codes
- Import/export shot configuration
- Compare shots
- Validate shot integrity
- Gather shot statistics

Author: Pipeline TD
Date: 2024
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import re
import json
import os

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    # Mock Maya commands for testing outside Maya
    class MockCmds(object):
        """Mock Maya commands for testing."""
        
        def objExists(self, name):
            """Mock objExists."""
            return False
        
        def createNode(self, node_type, name=None):
            """Mock createNode."""
            return name if name else "node1"
        
        def delete(self, *nodes):
            """Mock delete."""
            pass
        
        def getAttr(self, attr):
            """Mock getAttr."""
            return None
        
        def setAttr(self, attr, value, **kwargs):
            """Mock setAttr."""
            pass
        
        def listConnections(self, node, **kwargs):
            """Mock listConnections."""
            return []
        
        def ls(self, *args, **kwargs):
            """Mock ls."""
            return []
        
        def connectAttr(self, src, dst, **kwargs):
            """Mock connectAttr."""
            pass
        
        def addAttr(self, node, **kwargs):
            """Mock addAttr."""
            pass
    
    cmds = MockCmds()
    MAYA_AVAILABLE = False


class ShotManager(object):
    """High-level shot management tool.
    
    This class provides utilities to:
    - Create and manage shots
    - Import/export shot configuration
    - Validate shots
    - Compare shots
    - Gather statistics
    
    Example:
        >>> from tools.shot_manager import ShotManager
        >>> from core.custom_nodes import CTXManagerNode, CTXShotNode
        >>> 
        >>> shot_mgr = ShotManager()
        >>> 
        >>> # Create a shot
        >>> shot_node = shot_mgr.create_shot('Ep04', 'sq0070', 'SH0170', 'CTX_Manager')
        >>> print(shot_node)
        'CTX_Shot_SH0170'
        >>> 
        >>> # List all shots
        >>> shots = shot_mgr.list_all_shots()
        >>> print(shots)
        ['CTX_Shot_SH0170', 'CTX_Shot_SH0180']
    """
    
    # Shot code validation patterns
    EP_PATTERN = re.compile(r'^Ep\d{2}$')  # Ep01, Ep02, ..., Ep99
    SEQ_PATTERN = re.compile(r'^sq\d{4}$')  # sq0001, sq0002, ..., sq9999
    SHOT_PATTERN = re.compile(r'^SH\d{4}$')  # SH0001, SH0002, ..., SH9999
    
    def __init__(self, custom_nodes=None, display_layer_manager=None):
        """Initialize shot manager.
        
        Args:
            custom_nodes (dict, optional): Dict with 'manager', 'shot', 'asset' node classes
            display_layer_manager (DisplayLayerManager, optional): Display layer manager
        """
        self.custom_nodes = custom_nodes or {}
        self.layer_manager = display_layer_manager
    
    def validate_shot_code(self, ep, seq, shot):
        """Validate shot code format.
        
        Args:
            ep (str): Episode code (e.g., 'Ep04')
            seq (str): Sequence code (e.g., 'sq0070')
            shot (str): Shot code (e.g., 'SH0170')
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not self.EP_PATTERN.match(ep):
            return (False, "Invalid episode code '{}'. Expected format: Ep## (e.g., Ep04)".format(ep))
        
        if not self.SEQ_PATTERN.match(seq):
            return (False, "Invalid sequence code '{}'. Expected format: sq#### (e.g., sq0070)".format(seq))
        
        if not self.SHOT_PATTERN.match(shot):
            return (False, "Invalid shot code '{}'. Expected format: SH#### (e.g., SH0170)".format(shot))
        
        return (True, None)
    
    def create_shot(self, ep, seq, shot, manager_node):
        """Create a new shot.
        
        Args:
            ep (str): Episode code
            seq (str): Sequence code
            shot (str): Shot code
            manager_node (str): CTX_Manager node name
        
        Returns:
            str: Created shot node name
        """
        # Validate shot codes
        is_valid, error = self.validate_shot_code(ep, seq, shot)
        if not is_valid:
            raise ValueError(error)
        
        # Check manager exists
        if not cmds.objExists(manager_node):
            raise ValueError("Manager node '{}' does not exist".format(manager_node))

        # Build shot node name
        shot_node_name = "CTX_Shot_{}".format(shot)

        # Check if shot already exists
        if cmds.objExists(shot_node_name):
            raise ValueError("Shot '{}' already exists".format(shot_node_name))

        # Create shot node
        shot_node = cmds.createNode('network', name=shot_node_name)

        # Add attributes
        cmds.addAttr(shot_node, longName='ep', dataType='string')
        cmds.addAttr(shot_node, longName='seq', dataType='string')
        cmds.addAttr(shot_node, longName='shot', dataType='string')
        cmds.addAttr(shot_node, longName='dept', dataType='string')
        cmds.addAttr(shot_node, longName='manager', attributeType='message')
        cmds.addAttr(shot_node, longName='assets', attributeType='message', multi=True)

        # Set attribute values
        cmds.setAttr("{}.ep".format(shot_node), ep, type='string')
        cmds.setAttr("{}.seq".format(shot_node), seq, type='string')
        cmds.setAttr("{}.shot".format(shot_node), shot, type='string')

        # Connect to manager
        cmds.connectAttr("{}.message".format(shot_node), "{}.shots".format(manager_node), nextAvailable=True)

        # Create display layer if layer manager available
        if self.layer_manager:
            self.layer_manager.create_display_layer(ep, seq, shot)

        return shot_node

    def delete_shot(self, shot_node):
        """Delete a shot and all its assets.

        Args:
            shot_node (str): Shot node name

        Returns:
            bool: True if successful
        """
        if not cmds.objExists(shot_node):
            raise ValueError("Shot node '{}' does not exist".format(shot_node))

        # Get connected assets
        assets = cmds.listConnections("{}.assets".format(shot_node), source=True, destination=False) or []

        # Delete assets
        for asset in assets:
            if cmds.objExists(asset):
                cmds.delete(asset)

        # Delete shot node
        cmds.delete(shot_node)

        return True

    def duplicate_shot(self, shot_node, new_shot_code):
        """Duplicate a shot with a new shot code.

        Args:
            shot_node (str): Source shot node name
            new_shot_code (str): New shot code (e.g., 'SH0180')

        Returns:
            str: New shot node name
        """
        if not cmds.objExists(shot_node):
            raise ValueError("Shot node '{}' does not exist".format(shot_node))

        # Get shot info
        ep = cmds.getAttr("{}.ep".format(shot_node))
        seq = cmds.getAttr("{}.seq".format(shot_node))

        # Get manager
        manager = cmds.listConnections("{}.manager".format(shot_node), source=False, destination=True)
        if not manager:
            raise ValueError("Shot '{}' is not connected to a manager".format(shot_node))

        manager_node = manager[0]

        # Create new shot
        new_shot_node = self.create_shot(ep, seq, new_shot_code, manager_node)

        # Copy department if set
        dept = cmds.getAttr("{}.dept".format(shot_node))
        if dept:
            cmds.setAttr("{}.dept".format(new_shot_node), dept, type='string')

        # Note: Assets are not duplicated, only the shot structure

        return new_shot_node

    def get_shot_info(self, shot_node):
        """Get shot metadata.

        Args:
            shot_node (str): Shot node name

        Returns:
            dict: Shot information
        """
        if not cmds.objExists(shot_node):
            raise ValueError("Shot node '{}' does not exist".format(shot_node))

        # Get attributes
        info = {
            'node': shot_node,
            'ep': cmds.getAttr("{}.ep".format(shot_node)),
            'seq': cmds.getAttr("{}.seq".format(shot_node)),
            'shot': cmds.getAttr("{}.shot".format(shot_node)),
            'dept': cmds.getAttr("{}.dept".format(shot_node)) or '',
        }

        # Get asset count
        assets = cmds.listConnections("{}.assets".format(shot_node), source=True, destination=False) or []
        info['asset_count'] = len(assets)
        info['assets'] = assets

        return info

    def list_all_shots(self):
        """List all shots in the scene.

        Returns:
            list: List of shot node names
        """
        # Find all CTX_Shot nodes
        all_nodes = cmds.ls(type='network')
        shot_nodes = [node for node in all_nodes if node.startswith('CTX_Shot_')]

        return shot_nodes

    def export_shot(self, shot_node, filepath):
        """Export shot configuration to JSON.

        Args:
            shot_node (str): Shot node name
            filepath (str): Output JSON file path

        Returns:
            bool: True if successful
        """
        # Get shot info
        info = self.get_shot_info(shot_node)

        # Get asset details
        asset_details = []
        for asset_node in info['assets']:
            if cmds.objExists(asset_node):
                asset_info = {
                    'node': asset_node,
                    'assetType': cmds.getAttr("{}.assetType".format(asset_node)) or '',
                    'assetName': cmds.getAttr("{}.assetName".format(asset_node)) or '',
                    'variant': cmds.getAttr("{}.variant".format(asset_node)) or '',
                    'version': cmds.getAttr("{}.version".format(asset_node)) or '',
                    'path': cmds.getAttr("{}.path".format(asset_node)) or '',
                }
                asset_details.append(asset_info)

        # Build export data
        export_data = {
            'shot': {
                'ep': info['ep'],
                'seq': info['seq'],
                'shot': info['shot'],
                'dept': info['dept'],
            },
            'assets': asset_details
        }

        # Write to file
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)

        return True

    def import_shot(self, filepath, manager_node):
        """Import shot configuration from JSON.

        Args:
            filepath (str): Input JSON file path
            manager_node (str): CTX_Manager node name

        Returns:
            str: Created shot node name
        """
        # Read file
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Validate schema
        if 'shot' not in data:
            raise ValueError("Invalid JSON: missing 'shot' key")

        shot_data = data['shot']
        required_keys = ['ep', 'seq', 'shot']
        for key in required_keys:
            if key not in shot_data:
                raise ValueError("Invalid JSON: missing '{}' in shot data".format(key))

        # Create shot
        shot_node = self.create_shot(
            shot_data['ep'],
            shot_data['seq'],
            shot_data['shot'],
            manager_node
        )

        # Set department if present
        if 'dept' in shot_data and shot_data['dept']:
            cmds.setAttr("{}.dept".format(shot_node), shot_data['dept'], type='string')

        # Note: Assets are not imported automatically, only shot structure

        return shot_node

    def validate_shot(self, shot_node):
        """Validate shot integrity.

        Args:
            shot_node (str): Shot node name

        Returns:
            dict: Validation report with 'valid', 'errors', 'warnings'
        """
        errors = []
        warnings = []

        # Check node exists
        if not cmds.objExists(shot_node):
            return {
                'valid': False,
                'errors': ["Shot node '{}' does not exist".format(shot_node)],
                'warnings': []
            }

        # Validate shot codes
        try:
            ep = cmds.getAttr("{}.ep".format(shot_node))
            seq = cmds.getAttr("{}.seq".format(shot_node))
            shot = cmds.getAttr("{}.shot".format(shot_node))

            is_valid, error = self.validate_shot_code(ep, seq, shot)
            if not is_valid:
                errors.append(error)
        except:
            errors.append("Failed to read shot attributes")

        # Check manager connection
        manager = cmds.listConnections("{}.manager".format(shot_node), source=False, destination=True)
        if not manager:
            warnings.append("Shot is not connected to a manager")

        # Check display layer
        if self.layer_manager:
            layer = self.layer_manager.get_layer_for_shot(ep, seq, shot)
            if not layer:
                warnings.append("Display layer not found for shot")

        # Check asset paths
        assets = cmds.listConnections("{}.assets".format(shot_node), source=True, destination=False) or []
        for asset_node in assets:
            if cmds.objExists(asset_node):
                try:
                    path = cmds.getAttr("{}.path".format(asset_node))
                    if path and not os.path.exists(path):
                        warnings.append("Asset path does not exist: {}".format(path))
                except:
                    pass

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def get_shot_stats(self, shot_node):
        """Get shot statistics.

        Args:
            shot_node (str): Shot node name

        Returns:
            dict: Statistics dictionary
        """
        if not cmds.objExists(shot_node):
            raise ValueError("Shot node '{}' does not exist".format(shot_node))

        # Get assets
        assets = cmds.listConnections("{}.assets".format(shot_node), source=True, destination=False) or []

        # Count by type
        type_counts = {}
        total_size = 0
        version_counts = {}

        for asset_node in assets:
            if cmds.objExists(asset_node):
                # Count by type
                asset_type = cmds.getAttr("{}.assetType".format(asset_node)) or 'UNKNOWN'
                type_counts[asset_type] = type_counts.get(asset_type, 0) + 1

                # Count versions
                version = cmds.getAttr("{}.version".format(asset_node)) or 'v000'
                version_counts[version] = version_counts.get(version, 0) + 1

                # Calculate file size
                try:
                    path = cmds.getAttr("{}.path".format(asset_node))
                    if path and os.path.exists(path):
                        total_size += os.path.getsize(path)
                except:
                    pass

        return {
            'total_assets': len(assets),
            'assets_by_type': type_counts,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024.0 * 1024.0), 2),
            'version_distribution': version_counts
        }

