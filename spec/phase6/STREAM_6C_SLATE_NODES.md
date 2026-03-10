# Stream 6-C — Slate Nodes: Schemas, Wrappers, Connections

**Status:** Not Started
**Round:** 1 (parallel with 6-A)
**Branch:** `feature/phase6-lock-slate`
**Dependencies:** None

---

## Goal

Build the data layer for the Slate Manager. No UI, no resolver logic in this stream.
Four deliverables: `CTXSlateSchema`, `CTXSlateLayerSchema`, their wrappers, and
connection attributes added to Shot and Sequence schemas.

The Slate node pair is a direct analog of the Gaffer node pair:

| Gaffer system       | Slate system          |
|---------------------|-----------------------|
| `CTXLightGafferNode` | `CTXSlateNode`       |
| `CTXLightContextNode`| `CTXSlateLayerNode`  |
| `parentGaffer`      | `parentSlate`         |
| `lights` (multi)    | `layers` (multi)      |
| `CTXSequence.gaffer`| `CTXSequence.slate`   |
| `CTXShot.gaffer`    | `CTXShot.slate`       |
| `gafferType`        | `slateType`           |
| `intensityEnabled`  | `renderableEnabled`   |

Read `core/nodes/schemas/gaffer.py` and `core/nodes/schemas/light_context.py`
before writing any code — these are the reference patterns.

---

## 1. `core/nodes/schemas/slate.py` — NEW FILE

```python
"""CTXSlateSchema — schema for the CTX_Slate node.

Analog of CTXLightGafferSchema. One CTXSlateNode per scope level
(master, sequence, or shot). Connected to CTXSequenceNode or CTXShotNode.
Inherits from parent slate via parentSlate connection.
"""

from core.nodes.schemas.base import NodeSchema


class CTXSlateSchema(NodeSchema):
    """Schema for CTX_Slate nodes.

    Attributes
    ----------
    ctx_type : string
        Always 'CTX_Slate'. Used for node type identification.
    slateName : string
        Human-readable label for this slate (e.g. 'Master', 'sq0070', 'SH0170').
    slateType : string
        Scope level: 'master', 'sequence', or 'shot'.
    scopeCode : string
        Sequence or shot code this slate applies to (empty for master).
    enabled : bool
        Whether this slate participates in resolution. If False, it is skipped
        in the chain walk (same as CTXLightGaffer.enabled).
    notes : string
        Free-text notes for leads.

    Connections
    -----------
    parentSlate : INPUT
        Receives message from the parent CTXSlateNode.
        Enables inheritance: master -> sequence -> shot.
    layers : INPUT (multi)
        Receives messages from CTXSlateLayerNodes owned by this slate.
    """

    NODE_TYPE = 'CTX_Slate'

    ATTRIBUTES = {
        'ctx_type':   {'type': 'string',  'default': 'CTX_Slate'},
        'slateName':  {'type': 'string',  'default': ''},
        'slateType':  {'type': 'string',  'default': 'master'},
        'scopeCode':  {'type': 'string',  'default': ''},
        'enabled':    {'type': 'bool',    'default': True},
        'notes':      {'type': 'string',  'default': ''},
    }

    CONNECTIONS = {
        'parentSlate': {
            'type':      'message',
            'multi':     False,
            'direction': 'input',
        },
        'layers': {
            'type':      'message',
            'multi':     True,
            'direction': 'input',
        },
    }
```

---

## 2. `core/nodes/schemas/slate_layer.py` — NEW FILE

```python
"""CTXSlateLayerSchema — schema for the CTX_SlateLayer node.

Analog of CTXLightContextSchema. One CTXSlateLayerNode per render layer
entry within a slate. Stores the renderable override value and its enabled flag.

Phase 6 scope: renderable control only.
Future phases may add collection membership, AOV overrides, etc.
"""

from core.nodes.schemas.base import NodeSchema


class CTXSlateLayerSchema(NodeSchema):
    """Schema for CTX_SlateLayer nodes.

    Attributes
    ----------
    ctx_type : string
        Always 'CTX_SlateLayer'.
    layerName : string
        Name of the render layer as it exists in Maya Render Setup.
        Must match exactly (case-sensitive).
    renderable : bool
        The renderable state this slate entry records.
        True = layer should be renderable when this shot is active.
        False = layer should NOT be renderable.
    renderableEnabled : bool
        Whether this slate OVERRIDES the renderable state.
        False (default) = inherit from parent slate — do not apply.
        True = this entry owns the value and applies it.

        This mirrors the {attr}Enabled pattern in CTXLightContextSchema
        (e.g. intensityEnabled, colorEnabled).
    """

    NODE_TYPE = 'CTX_SlateLayer'

    ATTRIBUTES = {
        'ctx_type':          {'type': 'string', 'default': 'CTX_SlateLayer'},
        'layerName':         {'type': 'string', 'default': ''},
        'renderable':        {'type': 'bool',   'default': True},
        'renderableEnabled': {'type': 'bool',   'default': False},
    }

    CONNECTIONS = {}
```

---

## 3. `core/nodes/wrappers/slate.py` — NEW FILE

Read `core/nodes/wrappers/gaffer.py` as the reference pattern before writing.

```python
"""CTXSlateNode wrapper — analog of CTXLightGafferNode."""

from core.nodes.wrappers.base import NodeWrapper
from core.nodes.schemas.slate import CTXSlateSchema

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False


class CTXSlateNode(NodeWrapper):
    """Wrapper for CTX_Slate Maya nodes.

    Analog of CTXLightGafferNode. Stores per-scope render layer renderable
    overrides. Inherits from parent slate via parentSlate connection.

    Usage
    -----
    # Create a master slate
    master = CTXSlateNode.create(slateName='Master', slateType='master')

    # Create a sequence-level slate that inherits from master
    seq_slate = CTXSlateNode.create(slateName='sq0070', slateType='sequence',
                                    scopeCode='sq0070')
    seq_slate.set_parent_slate(master)

    # Assign to sequence
    seq_node.set_slate(seq_slate)
    """

    SCHEMA = CTXSlateSchema

    # ------------------------------------------------------------------
    # Layer management
    # ------------------------------------------------------------------

    def get_layers(self):
        """Return list of CTXSlateLayerNode wrappers connected to this slate.

        Returns:
            list[CTXSlateLayerNode]: Layer entries, order not guaranteed.
        """
        from core.nodes.wrappers.slate_layer import CTXSlateLayerNode
        if not MAYA_AVAILABLE:
            return []
        connected = cmds.listConnections(
            '{}.layers'.format(self.node_name),
            source=True,
            destination=False,
        ) or []
        return [CTXSlateLayerNode(n) for n in connected if cmds.objExists(n)]

    def get_layer_by_name(self, layer_name):
        """Return the CTXSlateLayerNode for a given render layer name, or None.

        Args:
            layer_name (str): Render layer name to look up.

        Returns:
            CTXSlateLayerNode|None
        """
        for layer in self.get_layers():
            try:
                if cmds.getAttr('{}.layerName'.format(layer.node_name)) == layer_name:
                    return layer
            except Exception:
                continue
        return None

    def add_layer(self, layer_name, renderable=True, enabled=False):
        """Create a CTXSlateLayerNode and connect it to this slate.

        If a layer with this name already exists in the slate, returns the
        existing node without creating a duplicate.

        Args:
            layer_name (str): Render layer name (must match scene layer exactly).
            renderable (bool): Initial renderable value.
            enabled (bool): Initial renderableEnabled value. Default False (inherit).

        Returns:
            CTXSlateLayerNode: The created or existing layer node.
        """
        from core.nodes.wrappers.slate_layer import CTXSlateLayerNode

        existing = self.get_layer_by_name(layer_name)
        if existing is not None:
            return existing

        layer_node = CTXSlateLayerNode.create(
            layerName=layer_name,
            renderable=renderable,
            renderableEnabled=enabled,
        )
        cmds.connectAttr(
            '{}.message'.format(layer_node.node_name),
            '{}.layers'.format(self.node_name),
            nextAvailable=True,
        )
        return layer_node

    def remove_layer(self, layer_name):
        """Disconnect and delete the CTXSlateLayerNode for a render layer.

        Args:
            layer_name (str): Render layer name to remove.
        """
        layer = self.get_layer_by_name(layer_name)
        if layer is None:
            return
        try:
            connections = cmds.listConnections(
                '{}.message'.format(layer.node_name),
                plugs=True,
                source=False,
                destination=True,
            ) or []
            for plug in connections:
                cmds.disconnectAttr('{}.message'.format(layer.node_name), plug)
            cmds.delete(layer.node_name)
        except Exception as exc:
            from core.logging_config import get_logger
            get_logger(__name__).error(
                'Failed to remove layer %s from slate: %s', layer_name, exc
            )

    # ------------------------------------------------------------------
    # Parent slate (inheritance chain)
    # ------------------------------------------------------------------

    def get_parent_slate(self):
        """Return the parent CTXSlateNode, or None.

        Returns:
            CTXSlateNode|None
        """
        if not MAYA_AVAILABLE:
            return None
        connected = cmds.listConnections(
            '{}.parentSlate'.format(self.node_name),
            source=True,
            destination=False,
        ) or []
        if connected:
            return CTXSlateNode(connected[0])
        return None

    def set_parent_slate(self, parent):
        """Wire a parent slate into this slate's parentSlate attribute.

        Args:
            parent (CTXSlateNode|str): Parent slate node or node name.
        """
        parent_name = parent if isinstance(parent, str) else parent.node_name
        cmds.connectAttr(
            '{}.message'.format(parent_name),
            '{}.parentSlate'.format(self.node_name),
            force=True,
        )

    def clear_parent_slate(self):
        """Remove the parentSlate connection, making this slate a root."""
        try:
            connected = cmds.listConnections(
                '{}.parentSlate'.format(self.node_name),
                source=True,
                destination=False,
                plugs=True,
            ) or []
            for plug in connected:
                cmds.disconnectAttr(plug, '{}.parentSlate'.format(self.node_name))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Enabled flag
    # ------------------------------------------------------------------

    def is_enabled(self):
        """Return True if this slate participates in chain resolution."""
        try:
            return bool(cmds.getAttr('{}.enabled'.format(self.node_name)))
        except Exception:
            return True

    def set_enabled(self, value):
        """Set the enabled flag."""
        cmds.setAttr('{}.enabled'.format(self.node_name), bool(value))

    # ------------------------------------------------------------------
    # Class-level queries
    # ------------------------------------------------------------------

    @classmethod
    def list_all(cls):
        """Return all CTXSlateNode wrappers in the current scene.

        Returns:
            list[CTXSlateNode]
        """
        if not MAYA_AVAILABLE:
            return []
        nodes = cmds.ls(type='network') or []
        results = []
        for n in nodes:
            try:
                if cmds.getAttr('{}.ctx_type'.format(n)) == 'CTX_Slate':
                    results.append(cls(n))
            except Exception:
                continue
        return results
```

---

## 4. `core/nodes/wrappers/slate_layer.py` — NEW FILE

Read `core/nodes/wrappers/light_context.py` as the reference pattern.

```python
"""CTXSlateLayerNode wrapper — analog of CTXLightContextNode."""

from core.nodes.wrappers.base import NodeWrapper
from core.nodes.schemas.slate_layer import CTXSlateLayerSchema

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False


class CTXSlateLayerNode(NodeWrapper):
    """Wrapper for CTX_SlateLayer Maya nodes.

    Stores the renderable override value and its enabled flag for one
    render layer within a slate.
    """

    SCHEMA = CTXSlateLayerSchema

    def get_layer_name(self):
        """Return the render layer name stored on this node.

        Returns:
            str: Layer name.
        """
        try:
            return cmds.getAttr('{}.layerName'.format(self.node_name)) or ''
        except Exception:
            return ''

    def get_renderable(self):
        """Return the stored renderable value.

        Returns:
            bool
        """
        try:
            return bool(cmds.getAttr('{}.renderable'.format(self.node_name)))
        except Exception:
            return True

    def set_renderable(self, value):
        """Set the renderable value.

        Args:
            value (bool): Renderable state to store.
        """
        cmds.setAttr('{}.renderable'.format(self.node_name), bool(value))

    def is_override_enabled(self):
        """Return True if renderableEnabled is True (this slate owns the value).

        Returns:
            bool
        """
        try:
            return bool(cmds.getAttr('{}.renderableEnabled'.format(self.node_name)))
        except Exception:
            return False

    def set_override_enabled(self, value):
        """Set renderableEnabled flag.

        Args:
            value (bool): True = this slate overrides renderable.
                          False = inherit from parent slate.
        """
        cmds.setAttr('{}.renderableEnabled'.format(self.node_name), bool(value))

    def set_override(self, renderable, enabled=True):
        """Convenience: set renderable value and enable the override in one call.

        Args:
            renderable (bool): Renderable state.
            enabled (bool): Whether to enable the override. Default True.
        """
        self.set_renderable(renderable)
        self.set_override_enabled(enabled)

    def to_dict(self):
        """Return layer state as a dict for snapshotting.

        Returns:
            dict: {'layerName': str, 'renderable': bool, 'renderableEnabled': bool}
        """
        return {
            'layerName':         self.get_layer_name(),
            'renderable':        self.get_renderable(),
            'renderableEnabled': self.is_override_enabled(),
        }
```

---

## 5. `core/nodes/wrappers/__init__.py` — Add Exports

Read the file first. Add:

```python
from .slate import CTXSlateNode
from .slate_layer import CTXSlateLayerNode
```

And add both names to `__all__`.

---

## 6. Schema Connection Additions — Shot and Sequence

### `core/nodes/schemas/shot.py`

Read the file. In `CONNECTIONS`, add:

```python
'slate': {
    'type':      'message',
    'multi':     False,
    'direction': 'input',
},
```

### `core/nodes/schemas/sequence.py`

Same addition to `CONNECTIONS`.

---

## 7. Wrapper Connection Methods — Shot and Sequence

### `core/nodes/wrappers/shot.py` — add:

```python
def get_slate(self):
    """Return the CTXSlateNode assigned to this shot, or None.

    Returns:
        CTXSlateNode|None
    """
    from core.nodes.wrappers.slate import CTXSlateNode
    if not MAYA_AVAILABLE:
        return None
    connected = cmds.listConnections(
        '{}.slate'.format(self.node_name),
        source=True,
        destination=False,
    ) or []
    if connected:
        return CTXSlateNode(connected[0])
    return None

def set_slate(self, slate):
    """Connect a CTXSlateNode to this shot.

    Args:
        slate (CTXSlateNode|str): Slate node or node name.
    """
    from core.nodes.wrappers.slate import CTXSlateNode
    slate_name = slate if isinstance(slate, str) else slate.node_name
    cmds.connectAttr(
        '{}.message'.format(slate_name),
        '{}.slate'.format(self.node_name),
        force=True,
    )

def clear_slate(self):
    """Remove the slate connection from this shot."""
    try:
        connected = cmds.listConnections(
            '{}.slate'.format(self.node_name),
            source=True,
            destination=False,
            plugs=True,
        ) or []
        for plug in connected:
            cmds.disconnectAttr(plug, '{}.slate'.format(self.node_name))
    except Exception:
        pass
```

### `core/nodes/wrappers/sequence.py` — add identical methods:

`get_slate()`, `set_slate(slate)`, `clear_slate()` — same implementation, same pattern.

---

## Tests — `tests/test_slate_nodes.py`

```python
# test_ctx_slate_schema_attributes
#   — CTXSlateSchema has all expected attribute keys

# test_ctx_slate_schema_connections
#   — CONNECTIONS has parentSlate (single input) and layers (multi input)

# test_ctx_slate_layer_schema_attributes
#   — layerName, renderable, renderableEnabled present with correct defaults

# test_ctx_slate_node_create_mock
#   — CTXSlateNode.create() calls cmds with correct attrs

# test_ctx_slate_layer_node_create_mock
#   — CTXSlateLayerNode.create() sets layerName, renderable, renderableEnabled

# test_add_layer_creates_and_connects
#   — slate.add_layer('beauty') creates CTXSlateLayerNode + connectAttr

# test_add_layer_no_duplicate
#   — calling add_layer twice with same name returns existing node

# test_remove_layer_disconnects_and_deletes
#   — slate.remove_layer('beauty') disconnects and deletes the node

# test_get_layer_by_name_found
#   — returns correct CTXSlateLayerNode when name matches

# test_get_layer_by_name_not_found
#   — returns None when name not present

# test_set_parent_slate_connects
#   — set_parent_slate() calls connectAttr correctly

# test_get_parent_slate_returns_wrapper
#   — get_parent_slate() returns CTXSlateNode from connected node

# test_set_override_convenience
#   — set_override(False, enabled=True) sets both attrs

# test_to_dict_returns_correct_keys
#   — CTXSlateLayerNode.to_dict() has layerName, renderable, renderableEnabled

# test_shot_set_slate_connects
#   — CTXShotNode.set_slate() calls connectAttr to shot.slate

# test_shot_get_slate_returns_wrapper
#   — CTXShotNode.get_slate() returns CTXSlateNode

# test_sequence_set_slate_connects
#   — CTXSequenceNode.set_slate() calls connectAttr to sequence.slate

# test_list_all_returns_slate_nodes
#   — CTXSlateNode.list_all() filters by ctx_type == 'CTX_Slate'
```

---

## Completion Criteria

- [ ] `core/nodes/schemas/slate.py` created — `CTXSlateSchema`
- [ ] `core/nodes/schemas/slate_layer.py` created — `CTXSlateLayerSchema`
- [ ] `core/nodes/wrappers/slate.py` created — `CTXSlateNode` with full API
- [ ] `core/nodes/wrappers/slate_layer.py` created — `CTXSlateLayerNode` with full API
- [ ] `CTXSlateNode`, `CTXSlateLayerNode` exported from `core/nodes/wrappers/__init__.py`
- [ ] `CTXShotSchema.CONNECTIONS` has `slate` (single input message)
- [ ] `CTXSequenceSchema.CONNECTIONS` has `slate` (single input message)
- [ ] `CTXShotNode` has `get_slate()`, `set_slate()`, `clear_slate()`
- [ ] `CTXSequenceNode` has `get_slate()`, `set_slate()`, `clear_slate()`
- [ ] All tests pass
- [ ] No regressions in existing test suite
