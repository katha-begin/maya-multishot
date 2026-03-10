# Stream 6-F — Slate UI: SlateManagerDialog (REVISED)

**Status:** In Progress (Round 4 — spec revision based on live testing)
**Branch:** `feature/phase6-lock-slate`
**Dependencies:** Stream 6-D (SlateManager, SlateResolver), Stream 6-G (SlateOriginalsNode)

---

## Identified Bugs (from live testing, fix in Round 4)

| # | Bug | Root Cause | Fix |
|---|---|---|---|
| 1 | Slate node naming wrong | `create_sequence_slate` uses `seq_code` for `slateName`, ignores user-provided name | Pass name from UI dialog through SlateManager |
| 2 | No originals system | No snapshot of pre-slate render layer state | Implement `CTXSlateOriginalsNode` (see Stream 6-G) |
| 3 | Inherited layers not shown in child | `is_override_enabled()` filter too strict; also naming bug means chain lookup fails | Remove filter; fix naming so chain resolves correctly |
| 4 | Width mismatch | SlateManagerDialog is 600px; should match MainWindow (545px) | `self.resize(545, 600)` |
| 5 | Close + reopen loses layers | `closeEvent` clears `_instance`; reopen creates new instance but `_refresh_slate_combo()` may silently fail because CTXSlateLayerNode `layers` attribute may be missing | Add `_ensure_layers_attr()` guard in `CTXSlateNode.get_layers()` |

---

## 1. Naming Convention Fix

### Problem
`SlateManager.create_sequence_slate` does:
```python
slate = CTXSlateNode.create(slateName=seq_code, ...)   # BUG: "sq0030" not "seq_sq0030"
```

The UI dialog prompts for a name (default `seq_sq0030`) but `SlateManager` ignores it.

### Correct Pattern (from gaffer study)

In gaffer: `GafferManagerDialog._create_sequence_gaffer()` prompts the user for a name, then passes it to `GafferManager.create_sequence_gaffer(seq_node, name=name, ...)`. The manager stores name in `gafferName` attribute.

### Fix: SlateManager API change

```python
@staticmethod
def create_sequence_slate(seq_node, name=None, parent_slate=None):
    """Create a sequence-level CTXSlateNode.

    Args:
        seq_node (CTXSequenceNode|str): Sequence to assign.
        name (str|None): Human name for slateName attribute.
                         Defaults to 'seq_{seq_code}'.
        parent_slate (CTXSlateNode|str|None): Parent to wire.
    """
    seq = seq_node if not isinstance(seq_node, str) else CTXSequenceNode(seq_node)
    seq_code = seq.get_attribute('sequenceCode') or seq.node_name

    slate_name = name if name else 'seq_{}'.format(seq_code)

    slate = CTXSlateNode.create(
        slateName=slate_name,
        slateType='sequence',
        scopeCode=seq_code,
    )
    if parent_slate is not None:
        slate.set_parent_slate(parent_slate)
    seq.set_slate(slate)
    return slate


@staticmethod
def create_shot_slate(shot_node, name=None, parent_slate=None):
    """Create a shot-level CTXSlateNode.

    Args:
        shot_node (CTXShotNode|str): Shot to assign.
        name (str|None): Human name. Defaults to '{seq_code}_{shot_code}'.
        parent_slate (CTXSlateNode|str|None): None = auto-wire to seq slate.
    """
    shot = shot_node if not isinstance(shot_node, str) else CTXShotNode(shot_node)
    seq_code = shot.get_seq_code()
    shot_code = shot.get_shot_code()
    shot_id = '{}_{}'.format(seq_code, shot_code)

    slate_name = name if name else shot_id

    slate = CTXSlateNode.create(
        slateName=slate_name,
        slateType='shot',
        scopeCode=shot_id,
    )
    if parent_slate is not None:
        slate.set_parent_slate(parent_slate)
    else:
        auto_parent = SlateManager._find_sequence_slate_for_shot(shot)
        if auto_parent is not None:
            slate.set_parent_slate(auto_parent)
    shot.set_slate(slate)
    return slate
```

### Fix: UI passes name

In `_create_sequence_slate()` and `_create_shot_slate()` in `SlateManagerDialog`:
```python
# Pass the user-entered name as the `name` argument
slate = SlateManager.create_sequence_slate(seq_node, name=name.strip(), parent_slate=parent)
slate = SlateManager.create_shot_slate(shot_node, name=name.strip(), parent_slate=parent)
```

### Slate combo label format

The combo must show the `slateName` attribute, not the Maya node name:
```python
# In _refresh_slate_combo():
label = '[Master] {}'.format(slate.get_attribute('slateName'))   # master
label = '[seq] {}'.format(slate.get_attribute('slateName'))       # sequence
label = '[shot] {}'.format(slate.get_attribute('slateName'))      # shot
```

---

## 2. Window Width

```python
# In __init__:
self.resize(545, 600)   # matches MainWindow.get_recommended_width()
```

---

## 3. closeEvent / Singleton Pattern

Mirror the exact gaffer pattern — clear `_instance` in `closeEvent`, always call `QtWidgets.QMainWindow.closeEvent(self, event)` (NOT `super()` — avoids stale class after module reload):

```python
def closeEvent(self, event):
    SlateManagerDialog._instance = None
    QtWidgets.QMainWindow.closeEvent(self, event)
```

### Refresh on show

`_refresh_slate_combo()` is called in `__init__()` AND in `showEvent` so that reopening the dialog always rescans the scene:

```python
def showEvent(self, event):
    QtWidgets.QMainWindow.showEvent(self, event)
    self._refresh_slate_combo()
```

---

## 4. Layer Table — Inheritance Display

### Correct approach (from gaffer study)

Gaffer builds a chain via `build_chain()`, then collects ALL lights from all gaffers in chain. Each light is tagged `is_direct=True/False`. The table renders inherited lights with `(inh)` prefix in gray.

### Slate equivalent

`_refresh_layer_table()` must:

1. Build chain: `chain = SlateResolver.build_chain(self._current_slate)`
2. Collect own layers from `chain[0]` (current slate)
3. Collect ALL layers from `chain[1:]` (parent slates) that are not already in own — regardless of `override_enabled`
4. Show own rows in normal color, inherited rows in gray `#888888` with `(inh)` suffix

```python
def _refresh_layer_table(self):
    self._layer_table.setRowCount(0)
    if self._current_slate is None:
        return

    # Build full chain
    try:
        chain = SlateResolver.build_chain(self._current_slate)
    except Exception as exc:
        logger.warning('build_chain failed: %s', exc)
        chain = [self._current_slate]

    # Own layers (on current slate)
    try:
        own_layers = {
            l.get_layer_name(): l
            for l in self._current_slate.get_layers()
            if l.get_layer_name()
        }
    except Exception:
        own_layers = {}

    # Inherited layers — ALL layers from parent slates, no override_enabled filter
    inherited = {}   # name -> (layer_entry, source_slate)
    for slate_node in chain[1:]:
        try:
            for layer_entry in slate_node.get_layers():
                name = layer_entry.get_layer_name()
                if name and name not in own_layers and name not in inherited:
                    inherited[name] = (layer_entry, slate_node)
        except Exception:
            continue

    # Ordered rows: own first, inherited second
    rows = []
    for name, entry in sorted(own_layers.items()):
        rows.append(('local', name, entry))
    for name, (entry, _src) in sorted(inherited.items()):
        rows.append(('inh', name, entry))

    gray = QtGui.QColor('#888888')
    self._layer_table.setRowCount(len(rows))

    for row, (kind, name, layer_entry) in enumerate(rows):
        is_local = kind == 'local'
        display_name = name if is_local else '{} (inh)'.format(name)

        # Col 0: Layer name
        name_item = QtWidgets.QTableWidgetItem(display_name)
        name_item.setData(QtCore.Qt.UserRole, name)   # real name without suffix
        name_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
        if not is_local:
            name_item.setForeground(gray)
        self._layer_table.setItem(row, 0, name_item)

        # Col 1: Renderable checkbox — enabled for ALL rows in edit mode
        renderable_cb = QtWidgets.QCheckBox()
        try:
            renderable_cb.setChecked(layer_entry.get_renderable())
        except Exception:
            renderable_cb.setChecked(True)
        renderable_cb.setEnabled(self._edit_mode)
        self._layer_table.setCellWidget(row, 1, self._center_widget(renderable_cb))

    self._on_search_changed(self._search_box.text())
```

### Commit — auto-creates local entry for inherited rows that changed

```python
def _commit_edit(self):
    if self._current_slate is None:
        self._exit_edit_mode()
        return
    current_state = self._read_table_state()
    for layer_name, state in current_state.items():
        snap = self._snapshot.get(layer_name, {})
        if state['renderable'] == snap.get('renderable'):
            continue   # Unchanged
        try:
            layer_entry = self._current_slate.get_layer_by_name(layer_name)
            if layer_entry is None:
                # Inherited row changed — take ownership
                layer_entry = self._current_slate.add_layer(
                    layer_name, renderable=state['renderable'], enabled=True
                )
            else:
                layer_entry.set_renderable(state['renderable'])
                layer_entry.set_override_enabled(True)
        except Exception as exc:
            logger.error('Failed to write layer %s: %s', layer_name, exc)
    self._exit_edit_mode()
```

---

## 5. `_ensure_layers_attr` — Close/Reopen Bug Fix

`CTXSlateNode.get_layers()` calls `cmds.listConnections('{}.layers'.format(self.node_name), ...)`.
If the `layers` multi-attribute doesn't exist on the node (pre-Phase-6 or partial creation), this raises an error that may be silently swallowed.

Fix in `core/nodes/wrappers/slate.py`:

```python
def _ensure_layers_attr(self):
    """Add the layers multi-attribute if absent."""
    if cmds is not None and not cmds.attributeQuery('layers', node=self.node_name, exists=True):
        cmds.addAttr(self.node_name, longName='layers',
                     attributeType='message', multi=True, indexMatters=False)

def get_layers(self):
    """Return list of CTXSlateLayerNode connected to this slate."""
    if cmds is None:
        return []
    self._ensure_layers_attr()
    connected = cmds.listConnections(
        '{}.layers'.format(self.node_name),
        source=True, destination=False
    ) or []
    from core.nodes.wrappers.slate_layer import CTXSlateLayerNode
    return [CTXSlateLayerNode(n) for n in connected]
```

Same `_ensure` pattern for `parentSlate` attribute in `CTXSlateNode`:
```python
def _ensure_parent_slate_attr(self):
    if cmds is not None and not cmds.attributeQuery('parentSlate', node=self.node_name, exists=True):
        cmds.addAttr(self.node_name, longName='parentSlate', attributeType='message')
```

---

## 6. `add_layer` default — `enabled=True`

`CTXSlateNode.add_layer()` and `SlateManager.add_layer_to_slate()` must default to `enabled=True` so newly added layers are immediately active in the inheritance chain:

```python
# core/nodes/wrappers/slate.py
def add_layer(self, layer_name, renderable=True, enabled=True):  # was: enabled=False

# core/slate/manager.py
def add_layer_to_slate(slate, layer_name, renderable=True, override_enabled=True):  # was: False

# ui/slate_manager_dialog.py  _on_add_layer()
self._current_slate.add_layer(name, renderable=True, enabled=True)  # was: False
```

---

## 7. Launch Script — Two-Window Fix

Do NOT call `dlg.show()` before `cmds.dockControl`. `dockControl` handles show internally:

```python
# launch_slate_manager.py — correct pattern (same as launch_batch_render_dockable.py)
dlg = SlateManagerDialog(parent=get_maya_main_window())
SlateManagerDialog._instance = dlg
# NO dlg.show() here
window_ptr = omui.MQtUtil.findWindow(dlg.objectName())
if window_ptr:
    cmds.dockControl(dock_control_name, ..., content=dlg.objectName(), ...)
else:
    dlg.show()
```

---

## Completion Criteria (Round 4)

- [ ] `SlateManager.create_sequence_slate(seq_node, name=None, ...)` accepts name param
- [ ] `SlateManager.create_shot_slate(shot_node, name=None, ...)` accepts name param
- [ ] UI passes user-entered name to SlateManager
- [ ] Slate combo shows `slateName` attribute, not Maya node name
- [ ] `SlateManagerDialog.resize(545, 600)` — matches MainWindow width
- [ ] `closeEvent` uses `QtWidgets.QMainWindow.closeEvent(self, event)` (not super())
- [ ] `showEvent` calls `_refresh_slate_combo()` to reload state on reopen
- [ ] `CTXSlateNode.get_layers()` has `_ensure_layers_attr()` guard
- [ ] `CTXSlateNode._ensure_parent_slate_attr()` guard added
- [ ] `add_layer` defaults: `enabled=True` everywhere
- [ ] `_refresh_layer_table` shows ALL parent layers as (inh), no `override_enabled` filter
- [ ] All rows editable in Edit Mode; inherited rows auto-create local entry on Commit
- [ ] No `dlg.show()` before `cmds.dockControl` in launch script
- [ ] `CTXSlateOriginalsNode` created (see Stream 6-G) and wired into `SlateResolver.apply_to_scene()`
