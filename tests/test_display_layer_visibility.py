# -*- coding: utf-8 -*-
"""Test display layer visibility in Maya.

This script tests different methods to control display layer visibility.
Run this in Maya Script Editor to test.
"""

from __future__ import print_function
import maya.cmds as cmds

def test_display_layer_visibility():
    """Test display layer visibility control."""
    
    # Create a test cube
    cube = cmds.polyCube(name='test_cube')[0]
    
    # Create a display layer
    layer_name = 'test_layer'
    if cmds.objExists(layer_name):
        cmds.delete(layer_name)
    
    cmds.createDisplayLayer(name=layer_name, empty=True)
    
    # Add cube to layer
    cmds.editDisplayLayerMembers(layer_name, cube, noRecurse=True)
    
    print("=" * 60)
    print("Testing Display Layer Visibility")
    print("=" * 60)
    
    # List all attributes on the display layer
    print("\nAll attributes on display layer:")
    attrs = cmds.listAttr(layer_name)
    for attr in attrs:
        print("  - {}".format(attr))
    
    # Test Method 1: .visibility attribute
    print("\n" + "=" * 60)
    print("Method 1: Using .visibility attribute")
    print("=" * 60)
    
    try:
        # Get current value
        current = cmds.getAttr("{}.visibility".format(layer_name))
        print("Current visibility: {}".format(current))
        
        # Try to set to 0 (hide)
        cmds.setAttr("{}.visibility".format(layer_name), 0)
        new_value = cmds.getAttr("{}.visibility".format(layer_name))
        print("After setting to 0: {}".format(new_value))
        
        # Try to set to 1 (show)
        cmds.setAttr("{}.visibility".format(layer_name), 1)
        new_value = cmds.getAttr("{}.visibility".format(layer_name))
        print("After setting to 1: {}".format(new_value))
        
        print("Method 1: SUCCESS")
    except Exception as e:
        print("Method 1 FAILED: {}".format(e))
    
    # Test Method 2: .displayType attribute
    print("\n" + "=" * 60)
    print("Method 2: Using .displayType attribute")
    print("=" * 60)
    
    try:
        # Get current value
        current = cmds.getAttr("{}.displayType".format(layer_name))
        print("Current displayType: {}".format(current))
        
        # displayType values:
        # 0 = Normal
        # 1 = Template
        # 2 = Reference
        
        cmds.setAttr("{}.displayType".format(layer_name), 2)
        new_value = cmds.getAttr("{}.displayType".format(layer_name))
        print("After setting to 2 (Reference): {}".format(new_value))
        
        cmds.setAttr("{}.displayType".format(layer_name), 0)
        new_value = cmds.getAttr("{}.displayType".format(layer_name))
        print("After setting to 0 (Normal): {}".format(new_value))
        
        print("Method 2: SUCCESS")
    except Exception as e:
        print("Method 2 FAILED: {}".format(e))
    
    # Test Method 3: .enabled attribute
    print("\n" + "=" * 60)
    print("Method 3: Using .enabled attribute")
    print("=" * 60)
    
    try:
        if cmds.attributeQuery('enabled', node=layer_name, exists=True):
            current = cmds.getAttr("{}.enabled".format(layer_name))
            print("Current enabled: {}".format(current))
            
            cmds.setAttr("{}.enabled".format(layer_name), 0)
            new_value = cmds.getAttr("{}.enabled".format(layer_name))
            print("After setting to 0: {}".format(new_value))
            
            cmds.setAttr("{}.enabled".format(layer_name), 1)
            new_value = cmds.getAttr("{}.enabled".format(layer_name))
            print("After setting to 1: {}".format(new_value))
            
            print("Method 3: SUCCESS")
        else:
            print("Method 3: .enabled attribute does not exist")
    except Exception as e:
        print("Method 3 FAILED: {}".format(e))
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)
    
    # Cleanup
    cmds.delete(cube)
    cmds.delete(layer_name)

if __name__ == '__main__':
    test_display_layer_visibility()

