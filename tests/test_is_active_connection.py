# -*- coding: utf-8 -*-
"""Test is_active to visibility connection.

This script tests the connection between CTX_Shot.is_active and DisplayLayer.visibility.
Run this in Maya Script Editor to test.
"""

from __future__ import print_function
import maya.cmds as cmds

def test_is_active_connection():
    """Test the is_active to visibility connection."""
    
    print("=" * 60)
    print("Testing is_active to visibility connection")
    print("=" * 60)
    
    # Create a test CTX_Shot node
    shot_node = 'CTX_Shot_Test'
    if cmds.objExists(shot_node):
        cmds.delete(shot_node)
    
    cmds.createNode('network', name=shot_node)
    cmds.addAttr(shot_node, longName='is_active', attributeType='bool')
    cmds.setAttr(shot_node + '.is_active', False)
    
    # Create a test display layer
    layer_name = 'CTX_Test_Layer'
    if cmds.objExists(layer_name):
        cmds.delete(layer_name)
    
    cmds.createDisplayLayer(name=layer_name, empty=True)
    
    print("\nCreated nodes:")
    print("  Shot node: {}".format(shot_node))
    print("  Layer: {}".format(layer_name))
    
    # Test 1: Try to connect is_active to visibility
    print("\n" + "=" * 60)
    print("Test 1: Connecting is_active to visibility")
    print("=" * 60)
    
    source_attr = shot_node + '.is_active'
    dest_attr = layer_name + '.visibility'
    
    try:
        cmds.connectAttr(source_attr, dest_attr, force=True)
        print("SUCCESS: Connected {} -> {}".format(source_attr, dest_attr))
        
        # Verify connection
        is_connected = cmds.isConnected(source_attr, dest_attr)
        print("Verification: isConnected = {}".format(is_connected))
        
        if is_connected:
            print("✓ Connection established successfully!")
        else:
            print("✗ Connection verification failed!")
            
    except Exception as e:
        print("FAILED: {}".format(e))
        print("\nThis might be because display layer visibility is locked or not connectable.")
        print("Let's check the attribute properties...")
        
        # Check if visibility attribute is locked
        is_locked = cmds.getAttr(dest_attr, lock=True)
        print("  visibility locked: {}".format(is_locked))
        
        # Check if visibility attribute is keyable
        is_keyable = cmds.getAttr(dest_attr, keyable=True)
        print("  visibility keyable: {}".format(is_keyable))
        
        # List attribute info
        print("\nAttribute info for {}:".format(dest_attr))
        try:
            attr_type = cmds.getAttr(dest_attr, type=True)
            print("  type: {}".format(attr_type))
        except:
            pass
    
    # Test 2: Test manual visibility control
    print("\n" + "=" * 60)
    print("Test 2: Manual visibility control")
    print("=" * 60)
    
    try:
        # Set to visible
        cmds.setAttr(dest_attr, 1)
        current = cmds.getAttr(dest_attr)
        print("After setting to 1: visibility = {}".format(current))
        
        # Set to hidden
        cmds.setAttr(dest_attr, 0)
        current = cmds.getAttr(dest_attr)
        print("After setting to 0: visibility = {}".format(current))
        
        print("✓ Manual visibility control works!")
        
    except Exception as e:
        print("✗ Manual visibility control failed: {}".format(e))
    
    # Test 3: If connection worked, test automatic update
    if cmds.isConnected(source_attr, dest_attr):
        print("\n" + "=" * 60)
        print("Test 3: Automatic visibility update via connection")
        print("=" * 60)
        
        # Set is_active to True
        cmds.setAttr(source_attr, True)
        visibility = cmds.getAttr(dest_attr)
        print("After is_active=True: visibility = {}".format(visibility))
        
        if visibility == 1:
            print("✓ Visibility updated to 1 (visible)")
        else:
            print("✗ Visibility did not update (expected 1, got {})".format(visibility))
        
        # Set is_active to False
        cmds.setAttr(source_attr, False)
        visibility = cmds.getAttr(dest_attr)
        print("After is_active=False: visibility = {}".format(visibility))
        
        if visibility == 0:
            print("✓ Visibility updated to 0 (hidden)")
        else:
            print("✗ Visibility did not update (expected 0, got {})".format(visibility))
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)
    
    # Cleanup
    print("\nCleaning up test nodes...")
    cmds.delete(shot_node)
    cmds.delete(layer_name)
    print("Done!")

if __name__ == '__main__':
    test_is_active_connection()

