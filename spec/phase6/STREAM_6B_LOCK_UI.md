# Stream 6-B — Lock UI: Column, Context Menu, Gaffer Banner

**Status:** Not Started
**Round:** 2 (after 6-A)
**Branch:** `feature/phase6-lock-slate`
**Dependencies:** Stream 6-A (LockManager, lock attributes on schemas)

---

## Goal

Surface the lock system in the UI. Three deliverables:
1. Lock column (col 1) in the Multishot Manager shot table
2. Right-click context menu additions for lock/unlock actions
3. Gaffer Manager lock banner and Edit Mode enforcement

---

## 1. `ui/main_window.py` — Shot Table Column Changes

### Current columns (7)

```
Col 0: #           (20px)
Col 1: Shot        (stretch)
Col 2: Frame Range
Col 3: Set
Col 4: Ver         (38px)
Col 5: Gaf         (38px)
Col 6: Rnd         (28px)
```

### New columns (8 after 6-B; 9 after 6-F adds Slt)

```
Col 0: #           (20px)
Col 1: Lck         (20px)   ← NEW
Col 2: Shot        (stretch)
Col 3: Frame Range
Col 4: Set
Col 5: Ver         (38px)
Col 6: Gaf         (38px)
Col 7: Rnd         (28px)   ← shifts right by 1
```

**All existing column index references (3, 4, 5, 6) must be incremented by 1.**
Read `main_window.py` fully before editing — search for every `cellWidget(row, N)`,
`setColumnWidth(N`, `setCellWidget(row, N`, and update the index.

### Header change

```python
# Before
self.shot_table.setColumnCount(7)
self.shot_table.setHorizontalHeaderLabels(["#", "Shot", "Frame Range", "Set", "Ver", "Gaf", "Rnd"])

# After
self.shot_table.setColumnCount(8)
self.shot_table.setHorizontalHeaderLabels(
    ["#", "Lck", "Shot", "Frame Range", "Set", "Ver", "Gaf", "Rnd"]
)
```

### Lock column sizing

```python
# Col 1: Lock — fixed 20px, no resize
header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
self.shot_table.setColumnWidth(1, 20)
```

### `_populate_shot_row(row, shot_data)` — add lock cell

After writing col 0 (`#`), write col 1 (`Lck`):

```python
# Col 1: Lock indicator
self._update_lock_cell(row, shot_data)
```

### New method: `_update_lock_cell(row, shot_data)`

```python
def _update_lock_cell(self, row, shot_data):
    """Set the lock indicator cell for a shot row.

    Shows a lock icon label. Color indicates lock state:
      - no lock:                   blank (no widget)
      - locked directly:           amber text label  "[L]"
      - locked via seq (cascade):  amber, slightly dimmer, tooltip shows source

    Args:
        row (int): Table row index.
        shot_data (dict): Shot data dict from self._shots.
    """
    from core.lock_manager import LockManager

    ctx_node = shot_data.get('ctx_node')
    if ctx_node is None:
        self.shot_table.setCellWidget(row, 1, None)
        return

    node_name = ctx_node.node_name if hasattr(ctx_node, 'node_name') else str(ctx_node)
    direct_locked = LockManager.is_locked(node_name)
    info = LockManager.get_lock_info(node_name) if direct_locked else {}

    # Check sequence cascade
    seq_locked = False
    seq_info = {}
    if not direct_locked:
        from core.lock_manager import LockManager as LM
        seq_node = LM._get_parent_sequence(node_name)
        if seq_node and LM.is_locked(seq_node):
            seq_locked = True
            seq_info = LM.get_lock_info(seq_node)

    if not direct_locked and not seq_locked:
        self.shot_table.setCellWidget(row, 1, None)
        item = QtWidgets.QTableWidgetItem('')
        item.setFlags(QtCore.Qt.NoItemFlags)
        self.shot_table.setItem(row, 1, item)
        return

    label = QtWidgets.QLabel('L')
    label.setAlignment(QtCore.Qt.AlignCenter)
    label.setFixedWidth(20)

    if direct_locked:
        label.setStyleSheet('color: #FFA000; font-weight: bold; font-size: 10px;')
        by = info.get('locked_by', '')
        at = info.get('locked_at', '')
        label.setToolTip('Locked by {} at {}'.format(by, at) if by else 'Locked')
    else:
        # Cascade from sequence — slightly dimmer
        label.setStyleSheet('color: #CC8800; font-size: 10px;')
        by = seq_info.get('locked_by', '')
        at = seq_info.get('locked_at', '')
        label.setToolTip('Locked via sequence (by {} at {})'.format(by, at) if by else 'Locked via sequence')

    self.shot_table.setCellWidget(row, 1, label)
```

---

## 2. Right-Click Context Menu Additions

Read the existing `_show_context_menu()` method in `main_window.py` before editing.
Add the following actions after the existing items, separated by a `addSeparator()`:

```python
menu.addSeparator()

# Lock / Unlock Shot
lock_info = LockManager.get_lock_info(node_name)
if lock_info['is_locked']:
    unlock_shot_action = menu.addAction('Unlock Shot')
    unlock_shot_action.triggered.connect(
        lambda checked=False, n=node_name: self._on_unlock_shot(n)
    )
else:
    lock_shot_action = menu.addAction('Lock Shot')
    lock_shot_action.triggered.connect(
        lambda checked=False, n=node_name: self._on_lock_shot(n)
    )

# Lock / Unlock Sequence
seq_node = LockManager._get_parent_sequence(node_name)
if seq_node:
    seq_info = LockManager.get_lock_info(seq_node)
    if seq_info['is_locked']:
        unlock_seq_action = menu.addAction('Unlock Sequence')
        unlock_seq_action.triggered.connect(
            lambda checked=False, sn=seq_node: self._on_unlock_sequence(sn)
        )
    else:
        lock_seq_action = menu.addAction('Lock Sequence')
        lock_seq_action.triggered.connect(
            lambda checked=False, sn=seq_node: self._on_lock_sequence(sn)
        )
```

### Handler methods

```python
def _on_lock_shot(self, node_name):
    """Lock a single shot node."""
    from core.lock_manager import LockManager
    try:
        LockManager.lock_node(node_name)
        self._refresh_lock_column()
        self.statusBar().showMessage('Shot locked: {}'.format(node_name))
    except Exception as exc:
        logger.error('Failed to lock shot %s: %s', node_name, exc)

def _on_unlock_shot(self, node_name):
    """Unlock a single shot node."""
    from core.lock_manager import LockManager
    try:
        LockManager.unlock_node(node_name)
        self._refresh_lock_column()
        self.statusBar().showMessage('Shot unlocked: {}'.format(node_name))
    except Exception as exc:
        logger.error('Failed to unlock shot %s: %s', node_name, exc)

def _on_lock_sequence(self, seq_node):
    """Lock a sequence and all shots under it (cascade)."""
    from core.lock_manager import LockManager
    try:
        LockManager.lock_sequence(seq_node, cascade=True)
        self._refresh_lock_column()
        self.statusBar().showMessage('Sequence locked: {}'.format(seq_node))
    except Exception as exc:
        logger.error('Failed to lock sequence %s: %s', seq_node, exc)

def _on_unlock_sequence(self, seq_node):
    """Unlock a sequence and all shots under it (cascade)."""
    from core.lock_manager import LockManager
    try:
        LockManager.unlock_sequence(seq_node, cascade=True)
        self._refresh_lock_column()
        self.statusBar().showMessage('Sequence unlocked: {}'.format(seq_node))
    except Exception as exc:
        logger.error('Failed to unlock sequence %s: %s', seq_node, exc)

def _refresh_lock_column(self):
    """Refresh the Lck column for all rows."""
    for row, shot_data in enumerate(self._shots):
        self._update_lock_cell(row, shot_data)
```

---

## 3. `ui/gaffer_manager_dialog.py` — Lock Banner and Edit Mode Enforcement

Read `gaffer_manager_dialog.py` fully before editing.

### Lock banner widget

Add a `QLabel` banner at the top of the dialog (above the gaffer list), hidden by default:

```python
# In _setup_ui(), after creating the main layout:
self._lock_banner = QtWidgets.QLabel('')
self._lock_banner.setStyleSheet(
    'background-color: #7B3F00; color: #FFD54F; '
    'padding: 4px 8px; font-weight: bold;'
)
self._lock_banner.setVisible(False)
self._lock_banner.setAlignment(QtCore.Qt.AlignCenter)
main_layout.insertWidget(0, self._lock_banner)  # top of layout
```

### Lock/Unlock button in toolbar

Add a `QPushButton` in the button bar alongside the Edit/Commit/Cancel buttons:

```python
self._lock_btn = QtWidgets.QPushButton('Lock Gaffer')
self._lock_btn.setToolTip('Lock this gaffer so its values cannot be edited')
self._lock_btn.clicked.connect(self._on_toggle_gaffer_lock)
button_layout.addWidget(self._lock_btn)
```

### `_refresh_lock_state()` method

Called whenever a gaffer is selected or the lock state changes:

```python
def _refresh_lock_state(self):
    """Update banner visibility, Edit button state, and lock button label."""
    gaffer = self._current_gaffer()  # returns current CTXLightGafferNode or None
    if gaffer is None:
        self._lock_banner.setVisible(False)
        self._lock_btn.setVisible(False)
        return

    from core.lock_manager import LockManager
    info = LockManager.get_lock_info(gaffer.node_name)
    locked = info['is_locked']

    self._lock_banner.setVisible(locked)
    if locked:
        by = info.get('locked_by', '')
        self._lock_banner.setText(
            'Read only — locked by {}. Edit mode disabled.'.format(by) if by
            else 'Read only — locked. Edit mode disabled.'
        )

    # Edit button disabled when locked
    self._edit_btn.setEnabled(not locked)

    # Lock button label toggles
    self._lock_btn.setText('Unlock Gaffer' if locked else 'Lock Gaffer')
    self._lock_btn.setVisible(True)
```

Call `_refresh_lock_state()`:
- After selecting a gaffer in the gaffer list (`_on_gaffer_selected`)
- After committing changes (`_on_commit`)
- On dialog show (`showEvent`)

### `_on_toggle_gaffer_lock()` handler

```python
def _on_toggle_gaffer_lock(self):
    """Toggle lock state of the currently selected gaffer."""
    gaffer = self._current_gaffer()
    if gaffer is None:
        return

    from core.lock_manager import LockManager
    if LockManager.is_locked(gaffer.node_name):
        LockManager.unlock_node(gaffer.node_name)
    else:
        LockManager.lock_node(gaffer.node_name)

    self._refresh_lock_state()
```

### Edit Mode guard

In the `_on_enter_edit_mode()` method (or wherever Edit button click is handled),
add a guard at the top:

```python
def _on_enter_edit_mode(self):
    gaffer = self._current_gaffer()
    if gaffer is None:
        return
    from core.lock_manager import LockManager
    if LockManager.is_locked(gaffer.node_name):
        QtWidgets.QMessageBox.information(
            self, 'Locked',
            'This gaffer is locked and cannot be edited.\n'
            'Use "Unlock Gaffer" to enable editing.'
        )
        return
    # ... rest of existing edit mode logic
```

---

## Completion Criteria

- [ ] Shot table has 8 columns — headers updated, all existing column indices incremented
- [ ] Lock column (col 1) shows amber `L` label for locked shots, dimmer for cascade-locked
- [ ] Tooltip on lock label shows locked_by and locked_at
- [ ] Right-click: Lock Shot / Unlock Shot present and functional
- [ ] Right-click: Lock Sequence / Unlock Sequence present and functional (cascade)
- [ ] `_refresh_lock_column()` updates all rows after any lock/unlock action
- [ ] Gaffer Manager shows lock banner when gaffer is locked
- [ ] Gaffer Manager Edit button disabled when locked
- [ ] Gaffer Manager Lock/Unlock button toggles state
- [ ] Edit Mode guard prevents entering edit on locked gaffer
- [ ] No regressions in existing test suite
