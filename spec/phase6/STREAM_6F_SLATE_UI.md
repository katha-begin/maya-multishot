# Stream 6-F — Slate UI: SlateManagerDialog and +SLT Column

**Status:** Not Started
**Round:** 3 (after 6-D)
**Branch:** `feature/phase6-lock-slate`
**Dependencies:** Stream 6-D (SlateManager, SlateResolver)

---

## Goal

Build the Slate Manager UI and integrate the `+SLT` column into the Multishot
Manager. The UI must mirror the Gaffer Manager 100% in structure, interaction
model, and visual style to minimise the learning curve.

Read `ui/gaffer_manager_dialog.py` completely before writing any code.
Every design decision in that file has a direct analog here.

---

## Side-by-Side: Gaffer Manager ↔ Slate Manager

| Gaffer Manager element | Slate Manager equivalent |
|---|---|
| `GafferManagerDialog(QMainWindow)` | `SlateManagerDialog(QMainWindow)` |
| `objectName('GafferManagerDialog')` | `objectName('SlateManagerDialog')` |
| `open_or_raise()` classmethod | `open_or_raise()` classmethod |
| `select_gaffer(gaffer)` | `select_slate(slate)` |
| Left panel: gaffer list | Left panel: slate list |
| Right panel: lights table | Right panel: layers table |
| `[+ New Gaffer]` button | `[+ New Slate]` button |
| `[Set Parent...]` button | `[Set Parent...]` button |
| `[Assign to Shot/Seq...]` | Assignment handled via `+SLT` in main window |
| Add Light popup | Add Layer popup |
| Lights table cols: Light Name, Intensity, Color, ... | Layers table cols: Layer Name, Renderable, Override, Source |
| `{attr}Enabled` checkbox per row | `renderableEnabled` checkbox = Override column |
| Source indicator: `(own)` / `(seq)` / `(master)` | Same source indicator |
| Edit / Commit / Cancel buttons | Edit / Commit / Cancel buttons (identical) |
| Lock banner (from 6-B) | Lock banner (identical pattern) |
| `menuBar()` Tools > Settings | `menuBar()` Tools > Settings |
| 460×600, 22px row height | 460×600, 22px row height |
| `_snapshot` dict for cancel restore | `_snapshot` dict for cancel restore |
| `cmds.dockControl` compatible | `cmds.dockControl` compatible |

---

## 1. `ui/slate_manager_dialog.py` — NEW FILE

### Window setup

```python
class SlateManagerDialog(QtWidgets.QMainWindow):
    """Dockable Slate Manager — per-shot render layer renderable control.

    Mirrors GafferManagerDialog structure exactly.
    """

    _instance = None

    @classmethod
    def open_or_raise(cls, parent=None):
        """Return existing instance (raised to front) or create new one."""
        if cls._instance is not None:
            try:
                cls._instance.raise_()
                cls._instance.activateWindow()
                return cls._instance
            except RuntimeError:
                cls._instance = None
        instance = cls(parent=parent)
        instance.show()
        cls._instance = instance
        return instance

    def __init__(self, parent=None):
        super(SlateManagerDialog, self).__init__(parent)
        self.setObjectName('SlateManagerDialog')
        self.setWindowTitle('Slate Manager')
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self.resize(460, 600)

        self._current_slate = None   # CTXSlateNode currently selected
        self._edit_mode = False
        self._snapshot = {}          # {layer_name: {renderable, renderableEnabled}}

        self._setup_ui()
        self._connect_signals()
        self._refresh_slate_list()
```

### Menu bar

```python
def _setup_menu(self):
    menubar = self.menuBar()
    tools_menu = menubar.addMenu('Tools')
    settings_action = QtWidgets.QAction('Settings', self)
    settings_action.triggered.connect(self._open_settings)
    tools_menu.addAction(settings_action)
```

### Layout

```
QMainWindow
  centralWidget (QWidget)
    QVBoxLayout
      [lock banner — hidden by default]
      QSplitter (horizontal)
        Left panel (200px)
          [slate list QListWidget]
          [+ New Slate] [Set Parent...] [Remove]
        Right panel (stretch)
          [layer table QTableWidget]
          [Add Layer] [Remove Layer]  ← below table
      [Edit] [Commit] [Cancel]  ← bottom bar
```

### Left panel — Slate List

```python
self._slate_list = QtWidgets.QListWidget()
self._slate_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
# Items show slate name + type, e.g. "Master [master]", "sq0070 [seq]"
```

`_refresh_slate_list()` calls `CTXSlateNode.list_all()` and repopulates the list.
Items store the `CTXSlateNode` as `item.setData(QtCore.Qt.UserRole, slate_node)`.

**Buttons below list:**

```python
self._new_slate_btn   = QtWidgets.QPushButton('+ New Slate')
self._set_parent_btn  = QtWidgets.QPushButton('Set Parent...')
self._remove_slate_btn = QtWidgets.QPushButton('Remove')
```

### Right panel — Layer Table

```python
self._layer_table = QtWidgets.QTableWidget()
self._layer_table.setColumnCount(4)
self._layer_table.setHorizontalHeaderLabels(
    ['Layer Name', 'Renderable', 'Override', 'Source']
)

# Column widths
header = self._layer_table.horizontalHeader()
header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)   # Layer Name
self._layer_table.setColumnWidth(1, 70)   # Renderable (checkbox)
self._layer_table.setColumnWidth(2, 60)   # Override (checkbox)
self._layer_table.setColumnWidth(3, 70)   # Source (text)

self._layer_table.setAlternatingRowColors(True)
self._layer_table.verticalHeader().setDefaultSectionSize(22)
self._layer_table.verticalHeader().setVisible(False)
```

**Column semantics:**

| Col | Name | Widget | Editable in edit mode |
|---|---|---|---|
| 0 | Layer Name | `QTableWidgetItem` (read-only) | No |
| 1 | Renderable | `QCheckBox` centered in cell | Yes (when Override=checked) |
| 2 | Override | `QCheckBox` centered in cell | Yes |
| 3 | Source | `QTableWidgetItem` (read-only) | No |

**Source column values:**
- `(own)` — this slate has `renderableEnabled=True` for this layer
- `(seq)` — value inherited from sequence slate
- `(master)` — value inherited from master slate
- `(–)` — no override anywhere in chain, scene state unchanged

**Renderable checkbox behaviour:**
- When `Override` is unchecked (not enabled): renderable checkbox shows inherited value
  (greyed out, not editable even in edit mode)
- When `Override` is checked: renderable checkbox is editable in edit mode

### Buttons below layer table

```python
self._add_layer_btn    = QtWidgets.QPushButton('Add Layer')
self._remove_layer_btn = QtWidgets.QPushButton('Remove Layer')
```

### Bottom bar — Edit / Commit / Cancel

```python
self._edit_btn   = QtWidgets.QPushButton('Edit')
self._commit_btn = QtWidgets.QPushButton('Commit')
self._cancel_btn = QtWidgets.QPushButton('Cancel')

self._commit_btn.setEnabled(False)
self._cancel_btn.setEnabled(False)
```

Behaviour mirrors gaffer exactly:
- **Edit**: takes `_snapshot`, enables checkboxes in table
- **Commit**: reads table state, writes diff to CTX nodes via `SlateManager`, exits edit mode
- **Cancel**: restores `_snapshot` to CTX nodes and table, exits edit mode

---

### Edit Mode Methods

```python
def _enter_edit_mode(self):
    """Snapshot current state; enable checkboxes."""
    if self._current_slate is None:
        return
    self._snapshot = self._capture_snapshot()
    self._edit_mode = True
    self._edit_btn.setEnabled(False)
    self._commit_btn.setEnabled(True)
    self._cancel_btn.setEnabled(True)
    self._refresh_layer_table()  # Re-draw with editable checkboxes

def _commit_edit(self):
    """Write table state to CTX nodes (snapshot-diff pattern)."""
    if self._current_slate is None:
        return
    current_state = self._read_table_state()
    # Write only changed values
    for layer_name, state in current_state.items():
        snap = self._snapshot.get(layer_name, {})
        layer_entry = self._current_slate.get_layer_by_name(layer_name)
        if layer_entry is None:
            continue
        if state['renderableEnabled'] != snap.get('renderableEnabled'):
            layer_entry.set_override_enabled(state['renderableEnabled'])
        if state['renderable'] != snap.get('renderable'):
            layer_entry.set_renderable(state['renderable'])
    self._exit_edit_mode()

def _cancel_edit(self):
    """Restore snapshot to CTX nodes."""
    if self._current_slate is None:
        self._exit_edit_mode()
        return
    for layer_name, state in self._snapshot.items():
        layer_entry = self._current_slate.get_layer_by_name(layer_name)
        if layer_entry is None:
            continue
        layer_entry.set_renderable(state['renderable'])
        layer_entry.set_override_enabled(state['renderableEnabled'])
    self._exit_edit_mode()

def _exit_edit_mode(self):
    self._edit_mode = False
    self._snapshot = {}
    self._edit_btn.setEnabled(True)
    self._commit_btn.setEnabled(False)
    self._cancel_btn.setEnabled(False)
    self._refresh_layer_table()
```

---

### Add Layer Popup

Mirrors the Add Light popup in Gaffer Manager:

```python
def _on_add_layer(self):
    """Open popup to select render layers from the current scene."""
    if self._current_slate is None:
        return

    try:
        from core.batch.render_setup_manager import RenderSetupManager
        all_layers = RenderSetupManager().get_all_layers()
    except Exception:
        all_layers = []

    if not all_layers:
        QtWidgets.QMessageBox.information(
            self, 'No Layers',
            'No render layers found in the current scene.'
        )
        return

    # Exclude layers already in the slate
    existing_names = {l.get_layer_name() for l in self._current_slate.get_layers()}
    available = [l for l in all_layers if l.name not in existing_names]

    if not available:
        QtWidgets.QMessageBox.information(
            self, 'All Layers Added',
            'All scene render layers are already in this slate.'
        )
        return

    dlg = _AddLayerDialog(available, parent=self)
    if dlg.exec_() != QtWidgets.QDialog.Accepted:
        return

    selected_names = dlg.get_selected_layer_names()
    for name in selected_names:
        self._current_slate.add_layer(name, renderable=True, enabled=False)

    self._refresh_layer_table()
```

### `_AddLayerDialog` — inner class (mirrors `AddShotDialog` pattern)

```python
class _AddLayerDialog(QtWidgets.QDialog):
    """Popup to pick render layers to add to a slate."""

    def __init__(self, layers, parent=None):
        super(_AddLayerDialog, self).__init__(parent)
        self.setWindowTitle('Add Layers to Slate')
        self.resize(300, 400)
        self._layers = layers  # list of RenderLayerInfo

        layout = QtWidgets.QVBoxLayout(self)

        # Filter box
        self._filter = QtWidgets.QLineEdit()
        self._filter.setPlaceholderText('Filter...')
        self._filter.textChanged.connect(self._apply_filter)
        layout.addWidget(self._filter)

        # List with checkboxes
        self._list = QtWidgets.QListWidget()
        self._list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        for layer in layers:
            item = QtWidgets.QListWidgetItem(layer.name)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Unchecked)
            self._list.addItem(item)
        layout.addWidget(self._list)

        # OK / Cancel
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _apply_filter(self, text):
        for i in range(self._list.count()):
            item = self._list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def get_selected_layer_names(self):
        """Return list of checked layer names."""
        result = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.checkState() == QtCore.Qt.Checked:
                result.append(item.text())
        return result
```

---

### `_refresh_layer_table()` — Full Redraw

```python
def _refresh_layer_table(self):
    """Redraw the layer table for the currently selected slate."""
    self._layer_table.setRowCount(0)
    if self._current_slate is None:
        return

    # Resolve chain for source indicators
    from core.slate.resolver import SlateResolver
    resolved = SlateResolver.resolve_layer_state(self._current_slate)

    layers = self._current_slate.get_layers()
    self._layer_table.setRowCount(len(layers))

    for row, layer_entry in enumerate(layers):
        name = layer_entry.get_layer_name()
        renderable = layer_entry.get_renderable()
        override_enabled = layer_entry.is_override_enabled()

        # Col 0: Layer Name (read-only)
        name_item = QtWidgets.QTableWidgetItem(name)
        name_item.setFlags(QtCore.Qt.ItemIsEnabled)
        self._layer_table.setItem(row, 0, name_item)

        # Col 1: Renderable checkbox
        renderable_cb = QtWidgets.QCheckBox()
        renderable_cb.setChecked(renderable)
        # Editable only in edit mode AND override is enabled
        renderable_cb.setEnabled(self._edit_mode and override_enabled)
        self._layer_table.setCellWidget(row, 1, self._center_widget(renderable_cb))

        # Col 2: Override checkbox (renderableEnabled)
        override_cb = QtWidgets.QCheckBox()
        override_cb.setChecked(override_enabled)
        override_cb.setEnabled(self._edit_mode)
        # When override toggled, enable/disable renderable checkbox
        override_cb.stateChanged.connect(
            lambda state, r=row, rcb=renderable_cb: rcb.setEnabled(
                self._edit_mode and bool(state)
            )
        )
        self._layer_table.setCellWidget(row, 2, self._center_widget(override_cb))

        # Col 3: Source indicator
        layer_state = resolved.get(name, {})
        if not layer_state.get('overridden'):
            source_text = '(–)'
        elif layer_state.get('source') == self._current_slate.node_name:
            source_text = '(own)'
        else:
            # Identify whether source is seq or master slate
            source_node = layer_state.get('source', '')
            try:
                import maya.cmds as cmds
                slate_type = cmds.getAttr('{}.slateType'.format(source_node))
                source_text = '({})'.format(slate_type[:3])  # 'seq' or 'mas'
            except Exception:
                source_text = '(inh)'

        source_item = QtWidgets.QTableWidgetItem(source_text)
        source_item.setFlags(QtCore.Qt.ItemIsEnabled)
        source_item.setForeground(
            QtGui.QColor('#888888') if source_text != '(own)' else QtGui.QColor('#CCCCCC')
        )
        self._layer_table.setItem(row, 3, source_item)

def _center_widget(self, widget):
    """Wrap a widget in a centered container for table cells."""
    container = QtWidgets.QWidget()
    layout = QtWidgets.QHBoxLayout(container)
    layout.addWidget(widget)
    layout.setAlignment(QtCore.Qt.AlignCenter)
    layout.setContentsMargins(0, 0, 0, 0)
    return container
```

---

## 2. `ui/main_window.py` — +SLT Column

### Column update (from 8 to 9 columns after 6-B added Lck)

After 6-B is complete, the table has 8 columns. 6-F adds col 7 `Slt`,
shifting `Rnd` from col 7 to col 8.

```python
# After 6-F:
self.shot_table.setColumnCount(9)
self.shot_table.setHorizontalHeaderLabels(
    ["#", "Lck", "Shot", "Frame Range", "Set", "Ver", "Gaf", "Slt", "Rnd"]
)
```

**All existing col 7 (Rnd) references must be updated to col 8.**

```python
# Col 7: Slt button
header.setSectionResizeMode(7, QtWidgets.QHeaderView.Fixed)
self.shot_table.setColumnWidth(7, 38)
```

### `_populate_shot_row()` — add Slt cell at col 7

```python
# Col 7: Slate button (mirrors Col 6 Gaffer button exactly)
ctx_node = shot_data.get('ctx_node')
has_slate = False
if ctx_node is not None:
    try:
        has_slate = ctx_node.get_slate() is not None
    except Exception:
        pass
slate_btn = QtWidgets.QPushButton('SLT' if has_slate else '+SLT')
slate_btn.setToolTip('Open Slate Manager for this shot')
if has_slate:
    slate_btn.setStyleSheet('background-color: #1565C0; color: white;')
slate_btn.clicked.connect(lambda checked=False, r=row: self._on_slate_click(r))
self.shot_table.setCellWidget(row, 7, slate_btn)
```

### `_on_slate_click(row)` — mirrors `_on_gaffer_click(row)` exactly

```python
def _on_slate_click(self, row):
    """Handle Slate button click on a shot row.

    Creates a shot-level slate if one does not exist, auto-wires it to
    the sequence slate (if present), then opens the Slate Manager.

    Args:
        row (int): Table row index.
    """
    if row < 0 or row >= len(self._shots):
        return

    shot_data = self._shots[row]
    ctx_node = shot_data.get('ctx_node')
    if ctx_node is None:
        return

    try:
        from core.slate.manager import SlateManager
        from ui.slate_manager_dialog import SlateManagerDialog

        slate = SlateManager.get_or_create_shot_slate(ctx_node)

        # Update button appearance
        slate_btn = self.shot_table.cellWidget(row, 7)
        if slate_btn:
            slate_btn.setText('SLT')
            slate_btn.setStyleSheet('background-color: #1565C0; color: white;')

        logger.info('Opened slate: %s', slate.node_name)

        # Open / refresh Slate Manager and pre-select this slate
        self._open_slate_manager_for(slate)

    except Exception as exc:
        logger.error('Slate button error: %s', exc)
        QtWidgets.QMessageBox.critical(
            self, 'Error', 'Failed to open slate:\n{}'.format(exc)
        )

def _open_slate_manager_for(self, slate):
    """Open (or bring to front) the Slate Manager and select a specific slate."""
    try:
        from ui.slate_manager_dialog import SlateManagerDialog
        self._slate_manager_dialog = SlateManagerDialog.open_or_raise(parent=self)
        self._slate_manager_dialog.select_slate(slate)
    except Exception as exc:
        logger.error('Failed to open Slate Manager for slate: %s', exc)
```

### Shot-switch: refresh Slate Manager (mirrors Gaffer Manager refresh)

In `_on_set_shot()`, after the existing Gaffer Manager refresh block:

```python
# Refresh Slate Manager if open; auto-select the active slate
try:
    from ui.slate_manager_dialog import SlateManagerDialog
    dlg = SlateManagerDialog._instance
    if dlg is not None:
        active_slate = None
        if shot_node is not None:
            active_slate = shot_node.get_slate()
        if active_slate is not None:
            dlg.select_slate(active_slate)
except Exception:
    pass
```

### Menu bar — Slate Manager item

In `_setup_toolbar()` or wherever the Tools menu is built:

```python
slate_action = QtWidgets.QAction('Slate Manager', self)
slate_action.setStatusTip('Open Render Layer Slate Manager')
slate_action.triggered.connect(self._open_slate_manager)
tools_menu.addAction(slate_action)
```

```python
def _open_slate_manager(self):
    """Open the Slate Manager dialog."""
    try:
        from ui.slate_manager_dialog import SlateManagerDialog
        self._slate_manager_dialog = SlateManagerDialog.open_or_raise(parent=self)
        logger.info('Opened Slate Manager')
        self.statusBar().showMessage('Slate Manager opened')
    except Exception as exc:
        logger.error('Failed to open Slate Manager: %s', exc)
        QtWidgets.QMessageBox.critical(
            self, 'Error', 'Failed to open Slate Manager:\n{}'.format(exc)
        )
```

---

## 3. `tools/maya_menu.py` — Slate Manager Menu Item

Read the file. Add after the Batch Render menu item:

```python
slate_item = cmds.menuItem(
    label='Slate Manager...',
    parent=tools_menu,
    command='exec(open(r\'{}/launch_slate_manager.py\').read())'.format(plugin_root),
)
```

---

## 4. `launch_slate_manager.py` — NEW FILE (optional, mirrors launch_batch_render_dockable.py)

```python
"""Launch the Slate Manager as a dockable panel in Maya."""

import maya.cmds as cmds


def launch_slate_manager():
    control_name = 'SlateManagerDockControl'

    if cmds.dockControl(control_name, exists=True):
        cmds.dockControl(control_name, edit=True, visible=True, raise_=True)
        return

    from ui.slate_manager_dialog import SlateManagerDialog
    dialog = SlateManagerDialog.open_or_raise()

    cmds.dockControl(
        control_name,
        label='Slate Manager',
        area='right',
        content=dialog.objectName(),
        width=460,
        allowedArea=['right', 'left'],
    )


launch_slate_manager()
```

---

## Completion Criteria

- [ ] `ui/slate_manager_dialog.py` created — full Gaffer-mirrored UI
- [ ] Left panel: slate list with `+ New Slate`, `Set Parent...`, `Remove` buttons
- [ ] Right panel: layer table with Layer Name / Renderable / Override / Source columns
- [ ] `Add Layer` popup lists scene render layers, filter box, checkboxes
- [ ] Edit / Commit / Cancel flow identical to Gaffer Manager
- [ ] Commit uses snapshot-diff to write only changed values
- [ ] Cancel restores snapshot
- [ ] Source column shows `(own)` / `(seq)` / `(mas)` / `(–)`
- [ ] Renderable checkbox greyed out when Override unchecked
- [ ] `open_or_raise()` classmethod prevents duplicate instances
- [ ] `select_slate(slate)` pre-selects a slate in the list
- [ ] `ui/main_window.py`: table has 9 columns after 6-F
- [ ] `+SLT` / `SLT` button in col 7, turns blue when slate exists
- [ ] `_on_slate_click()` creates/opens slate, mirrors `_on_gaffer_click()` exactly
- [ ] Shot-switch refreshes Slate Manager (same as Gaffer Manager refresh)
- [ ] Slate Manager menu item added to Tools menu
- [ ] No regressions in existing test suite
