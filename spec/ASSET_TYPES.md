# Asset Type System - Extensible Handler Architecture

**Version:** 1.0  
**Last Updated:** 2026-02-20  
**Status:** Planning Phase  
**Related Docs:** [NODE_ARCHITECTURE.md](NODE_ARCHITECTURE.md), [RENDERER_ADAPTERS.md](RENDERER_ADAPTERS.md)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Asset Type Handler Pattern](#2-asset-type-handler-pattern)
3. [Supported Asset Types](#3-supported-asset-types)
4. [USD Support](#4-usd-support)
5. [Implementation Guide](#5-implementation-guide)
6. [Testing](#6-testing)

---

## 1. Overview

### 1.1 Purpose

The Asset Type System provides a **plugin-like architecture** for handling different Maya asset node types (Arnold StandIn, Redshift Proxy, USD, References, etc.) through a unified interface.

### 1.2 Key Features

- ✅ **Unified API** - Same interface for all asset types
- ✅ **Extensible** - Add new types without modifying core code
- ✅ **USD Ready** - Built-in support for USD workflows
- ✅ **Renderer-Agnostic** - Works with any renderer
- ✅ **Testable** - Each handler can be tested independently

---

## 2. Asset Type Handler Pattern

### 2.1 Base Handler Class

```python
# core/asset_types/base.py

class AssetTypeHandler(object):
    """Base class for asset type handlers."""
    
    # Override in subclasses
    MAYA_NODE_TYPE = None           # Maya node type
    PATH_ATTRIBUTE = None           # Path attribute name
    SUPPORTED_EXTENSIONS = []       # File extensions
    DISPLAY_NAME = None             # UI display name
    RENDERER = None                 # Associated renderer (optional)
    
    def create_node(self, namespace, file_path):
        """Create Maya node for this asset type.
        
        Args:
            namespace (str): Node namespace
            file_path (str): Path to asset file
            
        Returns:
            str: Created node name
        """
        raise NotImplementedError
    
    def get_path(self, node):
        """Get file path from node.
        
        Args:
            node (str): Maya node name
            
        Returns:
            str: File path
        """
        raise NotImplementedError
    
    def set_path(self, node, path):
        """Set file path on node.
        
        Args:
            node (str): Maya node name
            path (str): New file path
        """
        raise NotImplementedError
    
    def is_valid_node(self, node):
        """Check if node is valid for this type.
        
        Args:
            node (str): Maya node name
            
        Returns:
            bool: True if valid
        """
        if not cmds.objExists(node):
            return False
        return cmds.nodeType(node) == self.MAYA_NODE_TYPE
    
    def reload(self, node):
        """Reload asset (optional).
        
        Args:
            node (str): Maya node name
        """
        pass
    
    def unload(self, node):
        """Unload asset (optional).
        
        Args:
            node (str): Maya node name
        """
        pass
```

### 2.2 Registry Pattern

```python
# core/asset_types/registry.py

class AssetTypeRegistry(object):
    """Registry for asset type handlers."""
    
    _handlers = {}
    
    @classmethod
    def register(cls, handler_class):
        """Register an asset type handler.
        
        Args:
            handler_class: AssetTypeHandler subclass
            
        Returns:
            handler_class: For decorator usage
        """
        cls._handlers[handler_class.MAYA_NODE_TYPE] = handler_class()
        return handler_class
    
    @classmethod
    def get_handler(cls, maya_node_type):
        """Get handler for Maya node type.
        
        Args:
            maya_node_type (str): Maya node type
            
        Returns:
            AssetTypeHandler: Handler instance or None
        """
        return cls._handlers.get(maya_node_type)
    
    @classmethod
    def get_handler_by_extension(cls, extension):
        """Get handler for file extension.
        
        Args:
            extension (str): File extension (e.g., '.abc', '.usd')
            
        Returns:
            AssetTypeHandler: Handler instance or None
        """
        for handler in cls._handlers.values():
            if extension in handler.SUPPORTED_EXTENSIONS:
                return handler
        return None
    
    @classmethod
    def list_supported_types(cls):
        """List all registered asset types.
        
        Returns:
            list: List of (maya_type, display_name) tuples
        """
        return [(h.MAYA_NODE_TYPE, h.DISPLAY_NAME) 
                for h in cls._handlers.values()]
```

---

## 3. Supported Asset Types

### 3.1 Arnold StandIn

```python
# core/asset_types/arnold.py

@AssetTypeRegistry.register
class ArnoldStandInHandler(AssetTypeHandler):
    """Handler for Arnold StandIn nodes."""
    
    MAYA_NODE_TYPE = 'aiStandIn'
    PATH_ATTRIBUTE = 'dso'
    SUPPORTED_EXTENSIONS = ['.abc', '.ass', '.ass.gz']
    DISPLAY_NAME = 'Arnold StandIn'
    RENDERER = 'Arnold'
    
    def create_node(self, namespace, file_path):
        node = cmds.createNode('aiStandIn', name=namespace)
        cmds.setAttr(f"{node}.dso", file_path, type='string')
        return node
    
    def get_path(self, node):
        return cmds.getAttr(f"{node}.dso")
    
    def set_path(self, node, path):
        cmds.setAttr(f"{node}.dso", path, type='string')
```

### 3.2 Redshift Proxy

```python
# core/asset_types/redshift.py

@AssetTypeRegistry.register
class RedshiftProxyHandler(AssetTypeHandler):
    """Handler for Redshift Proxy nodes."""
    
    MAYA_NODE_TYPE = 'RedshiftProxyMesh'
    PATH_ATTRIBUTE = 'fileName'
    SUPPORTED_EXTENSIONS = ['.rs', '.abc']
    DISPLAY_NAME = 'Redshift Proxy'
    RENDERER = 'Redshift'
    
    def create_node(self, namespace, file_path):
        node = cmds.createNode('RedshiftProxyMesh', name=namespace)
        cmds.setAttr(f"{node}.fileName", file_path, type='string')
        return node
    
    def get_path(self, node):
        return cmds.getAttr(f"{node}.fileName")
    
    def set_path(self, node, path):
        cmds.setAttr(f"{node}.fileName", path, type='string')
```

---

## 4. USD Support

### 4.1 USD Reference Handler

```python
# core/asset_types/usd.py

@AssetTypeRegistry.register
class USDReferenceHandler(AssetTypeHandler):
    """Handler for USD reference nodes."""
    
    MAYA_NODE_TYPE = 'mayaUsdProxyShape'
    PATH_ATTRIBUTE = 'filePath'
    SUPPORTED_EXTENSIONS = ['.usd', '.usda', '.usdc', '.usdz']
    DISPLAY_NAME = 'USD Reference'
    RENDERER = None  # Renderer-agnostic
    
    def create_node(self, namespace, file_path):
        """Create USD proxy shape."""
        # Create transform and shape
        transform = cmds.createNode('transform', name=namespace)
        shape = cmds.createNode('mayaUsdProxyShape', 
                               name=f"{namespace}Shape",
                               parent=transform)
        
        # Set file path
        cmds.setAttr(f"{shape}.filePath", file_path, type='string')
        
        return transform
    
    def get_path(self, node):
        """Get USD file path."""
        shapes = cmds.listRelatives(node, shapes=True, 
                                    type='mayaUsdProxyShape')
        if shapes:
            return cmds.getAttr(f"{shapes[0]}.filePath")
        return None
    
    def set_path(self, node, path):
        """Set USD file path."""
        shapes = cmds.listRelatives(node, shapes=True, 
                                    type='mayaUsdProxyShape')
        if shapes:
            cmds.setAttr(f"{shapes[0]}.filePath", path, type='string')
    
    def reload(self, node):
        """Reload USD stage."""
        shapes = cmds.listRelatives(node, shapes=True, 
                                    type='mayaUsdProxyShape')
        if shapes:
            # Trigger USD reload
            cmds.setAttr(f"{shapes[0]}.reload", 1)
```

### 4.2 USD Requirements

**Maya USD Plugin:**
- Requires Maya USD plugin to be loaded
- Available in Maya 2022+ by default
- Can be installed separately for older versions

**Supported Formats:**
- `.usd` - Binary USD
- `.usda` - ASCII USD
- `.usdc` - Crate (compressed) USD
- `.usdz` - Packaged USD

---

## 5. Implementation Guide

### 5.1 Adding a New Asset Type

**Step 1: Create Handler Class**

```python
# core/asset_types/my_custom_type.py

from .base import AssetTypeHandler
from .registry import AssetTypeRegistry

@AssetTypeRegistry.register
class MyCustomTypeHandler(AssetTypeHandler):
    """Handler for my custom asset type."""
    
    MAYA_NODE_TYPE = 'myCustomNode'
    PATH_ATTRIBUTE = 'filePath'
    SUPPORTED_EXTENSIONS = ['.custom']
    DISPLAY_NAME = 'My Custom Type'
    RENDERER = None
    
    def create_node(self, namespace, file_path):
        # Implementation
        pass
    
    def get_path(self, node):
        # Implementation
        pass
    
    def set_path(self, node, path):
        # Implementation
        pass
```

**Step 2: Register Handler**

```python
# core/asset_types/__init__.py

from .arnold import ArnoldStandInHandler
from .redshift import RedshiftProxyHandler
from .usd import USDReferenceHandler
from .my_custom_type import MyCustomTypeHandler  # Add this

# Handlers are auto-registered via decorator
```

**Step 3: Use Handler**

```python
# Automatic - works immediately
from core.asset_types.registry import AssetTypeRegistry

handler = AssetTypeRegistry.get_handler_by_extension('.custom')
node = handler.create_node('my_asset', '/path/to/file.custom')
```

---

## 6. Testing

### 6.1 Unit Tests

```python
# tests/test_asset_types.py

import unittest
from core.asset_types.registry import AssetTypeRegistry
from core.asset_types.usd import USDReferenceHandler

class TestAssetTypeRegistry(unittest.TestCase):
    
    def test_get_handler_by_extension(self):
        """Test getting handler by file extension."""
        handler = AssetTypeRegistry.get_handler_by_extension('.usd')
        self.assertIsInstance(handler, USDReferenceHandler)
    
    def test_list_supported_types(self):
        """Test listing all supported types."""
        types = AssetTypeRegistry.list_supported_types()
        self.assertGreater(len(types), 0)
        
        # Check USD is in list
        usd_found = any(t[0] == 'mayaUsdProxyShape' for t in types)
        self.assertTrue(usd_found)
```

---

**Document Status:** ✅ Complete  
**Next Steps:** Implement handlers in Phase 3  
**Maintainer:** CTX Pipeline Team

