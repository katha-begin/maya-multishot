# Renderer Adapter System - Multi-Renderer Support

**Version:** 1.0  
**Last Updated:** 2026-02-20  
**Status:** Planning Phase  
**Related Docs:** [NODE_ARCHITECTURE.md](NODE_ARCHITECTURE.md), [ASSET_TYPES.md](ASSET_TYPES.md)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Renderer Adapter Pattern](#2-renderer-adapter-pattern)
3. [Supported Renderers](#3-supported-renderers)
4. [Gaffer Integration](#4-gaffer-integration)
5. [Implementation Guide](#5-implementation-guide)

---

## 1. Overview

### 1.1 Purpose

The Renderer Adapter System provides a **unified interface** for renderer-specific operations (lights, shaders, proxies) across different renderers (Arnold, Redshift, Karma, etc.).

### 1.2 Key Features

- ✅ **Renderer-Agnostic Core** - Core code doesn't know about renderers
- ✅ **Unified API** - Same interface for all renderers
- ✅ **Auto-Detection** - Automatically detects active renderer
- ✅ **Extensible** - Easy to add new renderers
- ✅ **Gaffer-Ready** - Integrates with light gaffer system

---

## 2. Renderer Adapter Pattern

### 2.1 Base Adapter Class

```python
# core/renderers/base.py

class RendererAdapter(object):
    """Base class for renderer-specific operations."""
    
    RENDERER_NAME = None
    PROXY_NODE_TYPES = []
    LIGHT_NODE_TYPES = []
    
    def create_proxy_node(self, namespace, file_path):
        """Create proxy/cache node.
        
        Args:
            namespace (str): Node namespace
            file_path (str): Path to cache file
            
        Returns:
            str: Created node name
        """
        raise NotImplementedError
    
    def assign_shader(self, geometry, shader):
        """Assign shader to geometry.
        
        Args:
            geometry (str): Geometry node
            shader (str): Shader node
        """
        raise NotImplementedError
    
    def get_lights(self):
        """Get all lights in scene.
        
        Returns:
            list: List of light node names
        """
        raise NotImplementedError
    
    def set_light_attribute(self, light, attribute, value):
        """Set light attribute using generic name.
        
        Args:
            light (str): Light node name
            attribute (str): Generic attribute name (intensity, exposure, color, etc.)
            value: Attribute value
        """
        raise NotImplementedError
    
    def get_light_attribute(self, light, attribute):
        """Get light attribute using generic name.
        
        Args:
            light (str): Light node name
            attribute (str): Generic attribute name
            
        Returns:
            Attribute value or None
        """
        raise NotImplementedError
```

### 2.2 Registry Pattern

```python
# core/renderers/registry.py

class RendererRegistry(object):
    """Registry for renderer adapters."""
    
    _adapters = {}
    _active_renderer = None
    
    @classmethod
    def register(cls, adapter_class):
        """Register a renderer adapter."""
        cls._adapters[adapter_class.RENDERER_NAME] = adapter_class()
        return adapter_class
    
    @classmethod
    def get_adapter(cls, renderer_name=None):
        """Get renderer adapter.
        
        Args:
            renderer_name (str): Renderer name, or None for active renderer
            
        Returns:
            RendererAdapter: Adapter instance
        """
        if renderer_name is None:
            renderer_name = cls.get_active_renderer()
        return cls._adapters.get(renderer_name)
    
    @classmethod
    def get_active_renderer(cls):
        """Detect active renderer in Maya.
        
        Returns:
            str: Renderer name
        """
        if cls._active_renderer:
            return cls._active_renderer
        
        # Auto-detect from Maya
        current_renderer = cmds.getAttr('defaultRenderGlobals.currentRenderer')
        if 'arnold' in current_renderer.lower():
            return 'Arnold'
        elif 'redshift' in current_renderer.lower():
            return 'Redshift'
        
        return 'Arnold'  # Default
    
    @classmethod
    def set_active_renderer(cls, renderer_name):
        """Set active renderer.
        
        Args:
            renderer_name (str): Renderer name
        """
        cls._active_renderer = renderer_name
```

---

## 3. Supported Renderers

### 3.1 Arnold Adapter

```python
# core/renderers/arnold.py

@RendererRegistry.register
class ArnoldAdapter(RendererAdapter):
    """Arnold renderer adapter."""
    
    RENDERER_NAME = 'Arnold'
    PROXY_NODE_TYPES = ['aiStandIn']
    LIGHT_NODE_TYPES = ['aiAreaLight', 'aiSkyDomeLight', 'aiPhotometricLight']
    
    # Generic to Arnold attribute mapping
    LIGHT_ATTR_MAP = {
        'intensity': 'intensity',
        'exposure': 'exposure',
        'color': 'color',
        'temperature': 'aiColorTemperature',
        'normalize': 'aiNormalize',
        'muted': 'aiExposure',  # Set to -999 to mute
    }
    
    def create_proxy_node(self, namespace, file_path):
        node = cmds.createNode('aiStandIn', name=namespace)
        cmds.setAttr(f"{node}.dso", file_path, type='string')
        return node
    
    def assign_shader(self, geometry, shader):
        shading_group = cmds.listConnections(shader, type='shadingEngine')[0]
        cmds.sets(geometry, edit=True, forceElement=shading_group)
    
    def get_lights(self):
        lights = []
        for light_type in self.LIGHT_NODE_TYPES:
            lights.extend(cmds.ls(type=light_type) or [])
        return lights
    
    def set_light_attribute(self, light, attribute, value):
        """Set light attribute using generic name."""
        arnold_attr = self.LIGHT_ATTR_MAP.get(attribute)
        if arnold_attr:
            if attribute == 'muted' and value:
                # Mute by setting exposure to -999
                cmds.setAttr(f"{light}.aiExposure", -999)
            else:
                cmds.setAttr(f"{light}.{arnold_attr}", value)
    
    def get_light_attribute(self, light, attribute):
        """Get light attribute using generic name."""
        arnold_attr = self.LIGHT_ATTR_MAP.get(attribute)
        if arnold_attr and cmds.objExists(f"{light}.{arnold_attr}"):
            return cmds.getAttr(f"{light}.{arnold_attr}")
        return None
```

### 3.2 Redshift Adapter

```python
# core/renderers/redshift.py

@RendererRegistry.register
class RedshiftAdapter(RendererAdapter):
    """Redshift renderer adapter."""
    
    RENDERER_NAME = 'Redshift'
    PROXY_NODE_TYPES = ['RedshiftProxyMesh']
    LIGHT_NODE_TYPES = ['RedshiftPhysicalLight', 'RedshiftDomeLight']
    
    # Generic to Redshift attribute mapping
    LIGHT_ATTR_MAP = {
        'intensity': 'intensity',
        'exposure': 'exposure',
        'color': 'color',
        'temperature': 'temperature',
        'normalize': 'normalize',
        'muted': 'on',  # Invert for mute
    }
    
    def create_proxy_node(self, namespace, file_path):
        node = cmds.createNode('RedshiftProxyMesh', name=namespace)
        cmds.setAttr(f"{node}.fileName", file_path, type='string')
        return node
    
    def assign_shader(self, geometry, shader):
        shading_group = cmds.listConnections(shader, type='shadingEngine')[0]
        cmds.sets(geometry, edit=True, forceElement=shading_group)
    
    def get_lights(self):
        lights = []
        for light_type in self.LIGHT_NODE_TYPES:
            lights.extend(cmds.ls(type=light_type) or [])
        return lights
    
    def set_light_attribute(self, light, attribute, value):
        """Set light attribute using generic name."""
        rs_attr = self.LIGHT_ATTR_MAP.get(attribute)
        if rs_attr:
            if attribute == 'muted':
                # Mute by turning off light
                cmds.setAttr(f"{light}.on", not value)
            else:
                cmds.setAttr(f"{light}.{rs_attr}", value)
    
    def get_light_attribute(self, light, attribute):
        """Get light attribute using generic name."""
        rs_attr = self.LIGHT_ATTR_MAP.get(attribute)
        if rs_attr and cmds.objExists(f"{light}.{rs_attr}"):
            return cmds.getAttr(f"{light}.{rs_attr}")
        return None
```

---

## 4. Gaffer Integration

### 4.1 Renderer-Agnostic Light Control

The gaffer system uses renderer adapters for light control:

```python
# core/gaffer/inheritance.py

from core.renderers.registry import RendererRegistry

class GafferInheritance(object):
    """Resolve light values through gaffer chain."""
    
    @staticmethod
    def apply_light_overrides(light_name, gaffer_chain):
        """Apply light overrides from gaffer chain.
        
        Args:
            light_name (str): Maya light node name
            gaffer_chain (list): List of gaffer nodes (Shot → Seq → Master)
        """
        # Get active renderer adapter
        renderer = RendererRegistry.get_adapter()
        
        # Resolve each attribute through chain
        for attr in ['intensity', 'exposure', 'color', 'muted']:
            value, source = resolve_attribute(light_name, attr, gaffer_chain)
            
            if value is not None:
                # Apply using renderer adapter (renderer-agnostic!)
                renderer.set_light_attribute(light_name, attr, value)
```

### 4.2 Generic Attribute Names

The gaffer system uses **generic attribute names** that are mapped to renderer-specific attributes:

| Generic Name | Arnold | Redshift | Description |
|--------------|--------|----------|-------------|
| `intensity` | `intensity` | `intensity` | Light intensity multiplier |
| `exposure` | `exposure` | `exposure` | Exposure in stops |
| `color` | `color` | `color` | Light color (RGB) |
| `temperature` | `aiColorTemperature` | `temperature` | Color temperature (Kelvin) |
| `normalize` | `aiNormalize` | `normalize` | Normalize by area |
| `muted` | `aiExposure=-999` | `on=False` | Mute light |

---

## 5. Implementation Guide

### 5.1 Adding a New Renderer

**Step 1: Create Adapter Class**

```python
# core/renderers/karma.py

from .base import RendererAdapter
from .registry import RendererRegistry

@RendererRegistry.register
class KarmaAdapter(RendererAdapter):
    """Karma (Houdini) renderer adapter."""
    
    RENDERER_NAME = 'Karma'
    PROXY_NODE_TYPES = []  # Karma uses USD
    LIGHT_NODE_TYPES = ['houdiniLight']
    
    LIGHT_ATTR_MAP = {
        'intensity': 'intensity',
        'exposure': 'exposure',
        'color': 'lightColor',
        # ... map other attributes
    }
    
    def create_proxy_node(self, namespace, file_path):
        # Karma uses USD references
        pass
    
    def assign_shader(self, geometry, shader):
        # Karma shader assignment
        pass
    
    def get_lights(self):
        return cmds.ls(type='houdiniLight') or []
    
    def set_light_attribute(self, light, attribute, value):
        karma_attr = self.LIGHT_ATTR_MAP.get(attribute)
        if karma_attr:
            cmds.setAttr(f"{light}.{karma_attr}", value)
    
    def get_light_attribute(self, light, attribute):
        karma_attr = self.LIGHT_ATTR_MAP.get(attribute)
        if karma_attr and cmds.objExists(f"{light}.{karma_attr}"):
            return cmds.getAttr(f"{light}.{karma_attr}")
        return None
```

**Step 2: Register Adapter**

```python
# core/renderers/__init__.py

from .arnold import ArnoldAdapter
from .redshift import RedshiftAdapter
from .karma import KarmaAdapter  # Add this

# Adapters are auto-registered via decorator
```

**Step 3: Use Adapter**

```python
# Automatic - works immediately
from core.renderers.registry import RendererRegistry

# Set active renderer
RendererRegistry.set_active_renderer('Karma')

# Get adapter
renderer = RendererRegistry.get_adapter()

# Use unified API
lights = renderer.get_lights()
renderer.set_light_attribute('keyLight1', 'intensity', 1.5)
```

---

**Document Status:** ✅ Complete  
**Next Steps:** Implement adapters in Phase 2  
**Maintainer:** CTX Pipeline Team

