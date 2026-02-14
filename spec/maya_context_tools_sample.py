"""
Maya Context Variables Tool - v6 (Bug Fixes)
Supports: Arnold StandIn + Redshift Proxy + Maya References

Fixes:
- Reference nodes: Store data in fileInfo (no locked error)
- Template preservation: Proper callback timing
- Added silent mode for context detection
"""

import maya.cmds as cmds
import maya.OpenMayaUI as omui
import re
import os
from functools import partial

try:
    from PySide2 import QtWidgets, QtCore, QtGui
    from shiboken2 import wrapInstance
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui
    from shiboken6 import wrapInstance


# =============================================================================
# NODE TYPE DEFINITIONS
# =============================================================================

NODE_TYPES = {
    "aiStandIn": {
        "name": "Arnold StandIn",
        "path_attr": "dso",
        "icon_color": "#E6A800",
        "category": "proxy",
    },
    "RedshiftProxyMesh": {
        "name": "Redshift Proxy",
        "path_attr": "fileName",
        "icon_color": "#E63E3E",
        "category": "proxy",
    },
    "reference": {
        "name": "Reference",
        "path_attr": None,
        "icon_color": "#4A90D9",
        "category": "reference",
    },
}


# =============================================================================
# CONTEXT MANAGER
# =============================================================================

class ContextManager:
    """Manages context variables stored in Maya fileInfo"""
    
    PREFIX = "ctx_"
    CONTEXT_KEYS = ["ep", "seq", "shot"]
    
    _change_callbacks = []
    _callbacks_enabled = True  # Flag to temporarily disable callbacks
    
    @classmethod
    def set(cls, key, value, silent=False):
        """Set a context variable. silent=True skips callbacks."""
        old_value = cls.get(key)
        if old_value != value:
            cmds.fileInfo(f"{cls.PREFIX}{key}", str(value))
            if not silent and cls._callbacks_enabled:
                cls._notify_change()
        
    @classmethod
    def get(cls, key, default=""):
        result = cmds.fileInfo(f"{cls.PREFIX}{key}", query=True)
        return result[0] if result else default
    
    @classmethod
    def get_all(cls):
        return {key: cls.get(key) for key in cls.CONTEXT_KEYS}
    
    @classmethod
    def set_all(cls, ep=None, seq=None, shot=None, silent=False):
        """Set multiple context values. silent=True skips callbacks."""
        changed = False
        if ep is not None and cls.get("ep") != ep:
            cmds.fileInfo(f"{cls.PREFIX}ep", str(ep))
            changed = True
        if seq is not None and cls.get("seq") != seq:
            cmds.fileInfo(f"{cls.PREFIX}seq", str(seq))
            changed = True
        if shot is not None and cls.get("shot") != shot:
            cmds.fileInfo(f"{cls.PREFIX}shot", str(shot))
            changed = True
        
        if changed and not silent and cls._callbacks_enabled:
            cls._notify_change()
    
    @classmethod
    def set_from_path(cls, path, silent=False):
        """
        Auto-detect and set context from a file path.
        silent=True: Only detect and set values, don't trigger callbacks.
        Returns detected values dict.
        """
        patterns = {
            "ep": r"(Ep\d+)",
            "seq": r"(sq\d+)",
            "shot": r"(SH\d+)",
        }
        
        detected = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, path, re.IGNORECASE)
            if match:
                detected[key] = match.group(1)
        
        if detected:
            cls.set_all(silent=silent, **detected)
        
        return detected
                
    @classmethod
    def expand_tokens(cls, path, version_override=None):
        result = path
        
        for key in cls.CONTEXT_KEYS:
            token = f"${key}"
            value = cls.get(key)
            if value:
                result = result.replace(token, value)
        
        if version_override:
            result = result.replace("$ver", version_override)
            
        return result
    
    @classmethod
    def register_change_callback(cls, callback):
        if callback not in cls._change_callbacks:
            cls._change_callbacks.append(callback)
            
    @classmethod
    def unregister_change_callback(cls, callback):
        if callback in cls._change_callbacks:
            cls._change_callbacks.remove(callback)
    
    @classmethod
    def _notify_change(cls):
        if not cls._callbacks_enabled:
            return
        for callback in cls._change_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"[ContextVars] Callback error: {e}")
    
    @classmethod
    def suspend_callbacks(cls):
        """Temporarily disable callbacks"""
        cls._callbacks_enabled = False
        
    @classmethod
    def resume_callbacks(cls):
        """Re-enable callbacks"""
        cls._callbacks_enabled = True


# =============================================================================
# NODE MANAGER - Handles Proxies and References
# =============================================================================

class NodeManager:
    """Manages proxy nodes and references with context-aware paths"""
    
    VERSION_ATTR = "ctxVersion"
    TEMPLATE_ATTR = "ctxTemplatePath"
    
    # For references, we store in fileInfo with this prefix
    REF_PREFIX = "ctxRef_"
    
    # =========================
    # Node Discovery
    # =========================
    
    @classmethod
    def get_all_nodes(cls):
        """Get all supported nodes (proxies + references)"""
        nodes = []
        
        for node_type in NODE_TYPES.keys():
            if node_type == "reference":
                continue
            found = cmds.ls(type=node_type) or []
            nodes.extend(found)
        
        refs = cls.get_all_references()
        nodes.extend(refs)
        
        return nodes
    
    @classmethod
    def get_all_references(cls):
        """Get all reference nodes"""
        refs = cmds.ls(type="reference") or []
        valid_refs = []
        for ref in refs:
            try:
                if "shared" in ref.lower():
                    continue
                if "_UNKNOWN_REF_NODE" in ref:
                    continue
                cmds.referenceQuery(ref, filename=True)
                valid_refs.append(ref)
            except:
                pass
        return valid_refs
    
    # =========================
    # Attribute Setup (Proxy only)
    # =========================
    
    @classmethod
    def setup_proxy(cls, node):
        """Add context attributes to a PROXY node (not reference)"""
        node_type = cmds.nodeType(node)
        if node_type == "reference":
            return  # References use fileInfo, not attributes
            
        if not cmds.attributeQuery(cls.VERSION_ATTR, node=node, exists=True):
            cmds.addAttr(node, ln=cls.VERSION_ATTR, dt="string", keyable=False)
            cmds.setAttr(f"{node}.{cls.VERSION_ATTR}", "v001", type="string")
            
        if not cmds.attributeQuery(cls.TEMPLATE_ATTR, node=node, exists=True):
            cmds.addAttr(node, ln=cls.TEMPLATE_ATTR, dt="string", keyable=False)
    
    # =========================
    # Template Path (different storage for proxy vs reference)
    # =========================
    
    @classmethod
    def set_template_path(cls, node, template_path):
        """Set the template path with tokens"""
        node_type = cmds.nodeType(node)
        
        if node_type == "reference":
            # Store in fileInfo for references (avoids locked node issue)
            cmds.fileInfo(f"{cls.REF_PREFIX}{node}_template", template_path)
        else:
            cls.setup_proxy(node)
            cmds.setAttr(f"{node}.{cls.TEMPLATE_ATTR}", template_path, type="string")
        
    @classmethod
    def get_template_path(cls, node):
        """Get the template path"""
        node_type = cmds.nodeType(node)
        
        if node_type == "reference":
            result = cmds.fileInfo(f"{cls.REF_PREFIX}{node}_template", query=True)
            return result[0] if result else ""
        else:
            try:
                if cmds.attributeQuery(cls.TEMPLATE_ATTR, node=node, exists=True):
                    return cmds.getAttr(f"{node}.{cls.TEMPLATE_ATTR}") or ""
            except:
                pass
        return ""
    
    # =========================
    # Version (different storage for proxy vs reference)
    # =========================
    
    @classmethod
    def set_version(cls, node, version):
        """Set version for a specific node"""
        node_type = cmds.nodeType(node)
        
        if node_type == "reference":
            cmds.fileInfo(f"{cls.REF_PREFIX}{node}_version", version)
        else:
            cls.setup_proxy(node)
            cmds.setAttr(f"{node}.{cls.VERSION_ATTR}", version, type="string")
        
    @classmethod
    def get_version(cls, node):
        """Get version for a specific node"""
        node_type = cmds.nodeType(node)
        
        if node_type == "reference":
            result = cmds.fileInfo(f"{cls.REF_PREFIX}{node}_version", query=True)
            return result[0] if result else "v001"
        else:
            try:
                if cmds.attributeQuery(cls.VERSION_ATTR, node=node, exists=True):
                    return cmds.getAttr(f"{node}.{cls.VERSION_ATTR}") or "v001"
            except:
                pass
        return "v001"
    
    # =========================
    # Current Path (Read/Write)
    # =========================
    
    @classmethod
    def get_current_path(cls, node):
        """Get current file path from node"""
        node_type = cmds.nodeType(node)
        
        if node_type == "reference":
            try:
                return cmds.referenceQuery(node, filename=True, withoutCopyNumber=True)
            except:
                return ""
        else:
            node_def = NODE_TYPES.get(node_type)
            if node_def and node_def["path_attr"]:
                try:
                    return cmds.getAttr(f"{node}.{node_def['path_attr']}") or ""
                except:
                    pass
        return ""
    
    @classmethod
    def set_current_path(cls, node, path, reload_ref=True):
        """Set file path on node (actual path, not template)"""
        node_type = cmds.nodeType(node)
        
        if node_type == "reference":
            if reload_ref:
                cls._reload_reference(node, path)
        else:
            node_def = NODE_TYPES.get(node_type)
            if node_def and node_def["path_attr"]:
                try:
                    cmds.setAttr(f"{node}.{node_def['path_attr']}", path, type="string")
                except Exception as e:
                    print(f"[ContextVars] Error setting path on {node}: {e}")
    
    @classmethod
    def _reload_reference(cls, ref_node, new_path):
        """Reload a reference with a new path"""
        try:
            is_loaded = cmds.referenceQuery(ref_node, isLoaded=True)
            cmds.file(new_path, loadReference=ref_node)
            
            if not is_loaded:
                cmds.file(unloadReference=ref_node)
                
            print(f"[ContextVars] Reloaded reference: {ref_node} -> {new_path}")
            return True
            
        except Exception as e:
            print(f"[ContextVars] Error reloading reference {ref_node}: {e}")
            return False
    
    # =========================
    # Path Resolution
    # =========================
    
    @classmethod
    def resolve_path(cls, node):
        """Resolve template path to actual path using context"""
        template = cls.get_template_path(node)
        if not template:
            return ""
        
        version = cls.get_version(node)
        return ContextManager.expand_tokens(template, version)
    
    @classmethod
    def apply_resolved_path(cls, node, reload_ref=True):
        """Apply resolved path to node's actual path attribute"""
        template = cls.get_template_path(node)
        if not template:
            return None  # No template = don't touch the path
            
        resolved = cls.resolve_path(node)
        if resolved:
            cls.set_current_path(node, resolved, reload_ref=reload_ref)
            return resolved
        return None
    
    @classmethod
    def apply_all(cls, reload_refs=True):
        """Apply resolved paths to all nodes that have templates"""
        results = []
        for node in cls.get_all_nodes():
            template = cls.get_template_path(node)
            if template:  # Only process nodes WITH templates
                resolved = cls.apply_resolved_path(node, reload_ref=reload_refs)
                if resolved:
                    results.append((node, resolved))
        return results
    
    # =========================
    # Template Conversion
    # =========================
    
    @classmethod
    def convert_path_to_template(cls, path, context=None):
        """
        Convert a resolved path back to template with tokens.
        context: Optional dict of {ep, seq, shot} to use for conversion.
                 If None, uses current context.
        """
        template = path
        
        if context is None:
            context = ContextManager.get_all()
        
        for key in ContextManager.CONTEXT_KEYS:
            value = context.get(key, "")
            if value:
                template = template.replace(value, f"${key}")
        
        version_match = re.search(r"[/\\](v\d{3,4})[/\\]", template)
        if version_match:
            template = template.replace(version_match.group(1), "$ver")
            
        return template


# =============================================================================
# AUTO-UPDATE SYSTEM
# =============================================================================

def on_context_changed():
    """Called automatically when any context variable changes"""
    ctx = ContextManager.get_all()
    print(f"[ContextVars] Context changed: ep={ctx['ep']}, seq={ctx['seq']}, shot={ctx['shot']}")
    print("[ContextVars] Updating all node paths...")
    
    results = NodeManager.apply_all(reload_refs=True)
    for node, path in results:
        exists = os.path.exists(path) if path else False
        status = "✓" if exists else "✗"
        node_type = cmds.nodeType(node)
        type_def = NODE_TYPES.get(node_type, {})
        type_name = type_def.get("name", "Unknown")
        print(f"  {status} [{type_name}] {node} -> {path}")
    print(f"[ContextVars] Updated {len(results)} node(s)")

ContextManager.register_change_callback(on_context_changed)


# =============================================================================
# PRE-RENDER CALLBACK
# =============================================================================

def pre_render_callback(*args):
    """Pre-render callback to resolve all paths"""
    print("[ContextVars] Pre-render: Resolving all paths...")
    results = NodeManager.apply_all(reload_refs=True)
    for node, path in results:
        print(f"  {node} -> {path}")


def register_render_callback():
    """Register pre-render callback"""
    cmds.setAttr("defaultRenderGlobals.preMel", 
                 'python("pre_render_callback()")', type="string")
    
    if cmds.objExists("redshiftOptions"):
        try:
            current = cmds.getAttr("redshiftOptions.preRenderMel") or ""
            if "pre_render_callback" not in current:
                new_script = current + '; python("pre_render_callback()")'
                cmds.setAttr("redshiftOptions.preRenderMel", new_script.strip("; "), type="string")
        except:
            pass
    
    print("[ContextVars] Pre-render callback registered")


# =============================================================================
# UI
# =============================================================================

def get_maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)


class ContextVariablesUI(QtWidgets.QDialog):
    """Context variables panel"""
    
    WINDOW_TITLE = "Context Variables"
    WINDOW_NAME = "contextVariablesWindow"
    
    def __init__(self, parent=get_maya_main_window()):
        super().__init__(parent)
        
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setObjectName(self.WINDOW_NAME)
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        
        self._updating = False
        
        self.build_ui()
        self.refresh_all()
        
        ContextManager.register_change_callback(self.on_external_context_change)
        
    def closeEvent(self, event):
        ContextManager.unregister_change_callback(self.on_external_context_change)
        super().closeEvent(event)
        
    def build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)
        
        # === CONTEXT SECTION ===
        context_group = QtWidgets.QGroupBox("Scene Context")
        context_layout = QtWidgets.QVBoxLayout(context_group)
        
        fields_layout = QtWidgets.QGridLayout()
        fields_layout.setColumnStretch(1, 1)
        
        self.context_fields = {}
        labels = {"ep": "$ep", "seq": "$seq", "shot": "$shot"}
        placeholders = {"ep": "Ep04", "seq": "sq0070", "shot": "SH0170"}
        
        for row, key in enumerate(ContextManager.CONTEXT_KEYS):
            label = QtWidgets.QLabel(labels[key])
            label.setStyleSheet("font-weight: bold; color: #FFA500; font-size: 14px;")
            label.setFixedWidth(50)
            
            field = QtWidgets.QLineEdit()
            field.setPlaceholderText(placeholders[key])
            field.setStyleSheet("font-size: 14px; padding: 4px;")
            field.returnPressed.connect(self.apply_context)
            
            self.context_fields[key] = field
            fields_layout.addWidget(label, row, 0)
            fields_layout.addWidget(field, row, 1)
        
        context_layout.addLayout(fields_layout)
        
        ctx_btn_layout = QtWidgets.QHBoxLayout()
        
        apply_ctx_btn = QtWidgets.QPushButton("Apply Context")
        apply_ctx_btn.setStyleSheet("background-color: #4A7C4E; font-weight: bold; padding: 8px;")
        apply_ctx_btn.clicked.connect(self.apply_context)
        
        detect_btn = QtWidgets.QPushButton("Auto-Detect from Selection")
        detect_btn.clicked.connect(self.auto_detect_context)
        
        ctx_btn_layout.addWidget(apply_ctx_btn)
        ctx_btn_layout.addWidget(detect_btn)
        
        context_layout.addLayout(ctx_btn_layout)
        main_layout.addWidget(context_group)
        
        # === FILTER TABS ===
        self.filter_tabs = QtWidgets.QTabWidget()
        self.filter_tabs.currentChanged.connect(self.refresh_nodes)
        
        self.filter_tabs.addTab(QtWidgets.QWidget(), "All")
        self.filter_tabs.addTab(QtWidgets.QWidget(), "References")
        self.filter_tabs.addTab(QtWidgets.QWidget(), "Arnold")
        self.filter_tabs.addTab(QtWidgets.QWidget(), "Redshift")
        
        main_layout.addWidget(self.filter_tabs)
        
        # === NODE LIST ===
        node_group = QtWidgets.QGroupBox("Nodes")
        node_layout = QtWidgets.QVBoxLayout(node_group)
        
        toolbar = QtWidgets.QHBoxLayout()
        
        refresh_btn = QtWidgets.QPushButton("Refresh")
        refresh_btn.setFixedWidth(80)
        refresh_btn.clicked.connect(self.refresh_nodes)
        
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet("color: #888888;")
        
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.status_label)
        
        node_layout.addLayout(toolbar)
        
        # Node table
        self.node_table = QtWidgets.QTableWidget()
        self.node_table.setColumnCount(5)
        self.node_table.setHorizontalHeaderLabels(["Type", "Node", "Ver", "Template", "Current Path"])
        self.node_table.horizontalHeader().setStretchLastSection(True)
        self.node_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.node_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.node_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.node_table.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.node_table.setAlternatingRowColors(True)
        self.node_table.itemSelectionChanged.connect(self.on_node_selected)
        
        node_layout.addWidget(self.node_table)
        main_layout.addWidget(node_group)
        
        # === SELECTED NODE EDITOR ===
        detail_group = QtWidgets.QGroupBox("Setup Selected Node")
        detail_layout = QtWidgets.QFormLayout(detail_group)
        
        # Node info
        node_info_layout = QtWidgets.QHBoxLayout()
        self.detail_node_label = QtWidgets.QLabel("-")
        self.detail_node_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.detail_type_label = QtWidgets.QLabel("")
        self.detail_type_label.setStyleSheet("padding: 2px 6px; border-radius: 3px;")
        
        node_info_layout.addWidget(self.detail_node_label)
        node_info_layout.addWidget(self.detail_type_label)
        node_info_layout.addStretch()
        
        # Version
        version_layout = QtWidgets.QHBoxLayout()
        self.detail_version_edit = QtWidgets.QLineEdit()
        self.detail_version_edit.setPlaceholderText("v001")
        self.detail_version_edit.setFixedWidth(80)
        self.detail_version_edit.textChanged.connect(self.update_resolved_preview)
        
        version_layout.addWidget(self.detail_version_edit)
        version_layout.addStretch()
        
        # Template
        self.detail_template_edit = QtWidgets.QLineEdit()
        self.detail_template_edit.setPlaceholderText("V:/project/$ep/$seq/$shot/publish/$ver/$ep_$seq_$shot__asset.ma")
        self.detail_template_edit.textChanged.connect(self.update_resolved_preview)
        
        # Resolved preview
        self.detail_resolved_label = QtWidgets.QLabel("-")
        self.detail_resolved_label.setWordWrap(True)
        self.detail_resolved_label.setStyleSheet("color: #88CC88; padding: 6px; background: #2a2a2a; border-radius: 4px;")
        
        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        
        set_from_current_btn = QtWidgets.QPushButton("Current Path → Template")
        set_from_current_btn.setToolTip("Convert current path to template with $tokens")
        set_from_current_btn.clicked.connect(self.set_template_from_current)
        
        apply_template_btn = QtWidgets.QPushButton("Apply Template")
        apply_template_btn.clicked.connect(self.apply_template)
        apply_template_btn.setStyleSheet("background-color: #4A7C4E;")
        
        btn_layout.addWidget(set_from_current_btn)
        btn_layout.addWidget(apply_template_btn)
        
        detail_layout.addRow("Node:", node_info_layout)
        detail_layout.addRow("$ver:", version_layout)
        detail_layout.addRow("Template:", self.detail_template_edit)
        detail_layout.addRow("Resolved:", self.detail_resolved_label)
        detail_layout.addRow(btn_layout)
        
        main_layout.addWidget(detail_group)
        
        # === BOTTOM BUTTONS ===
        bottom_layout = QtWidgets.QHBoxLayout()
        
        register_callback_btn = QtWidgets.QPushButton("Register Pre-Render Callback")
        register_callback_btn.clicked.connect(self.register_callback)
        
        bottom_layout.addWidget(register_callback_btn)
        bottom_layout.addStretch()
        
        main_layout.addLayout(bottom_layout)
        
        # Connect context field changes to preview
        for field in self.context_fields.values():
            field.textChanged.connect(self.update_resolved_preview)
        
    def refresh_all(self):
        self.refresh_context()
        self.refresh_nodes()
        
    def refresh_context(self):
        self._updating = True
        for key, field in self.context_fields.items():
            field.setText(ContextManager.get(key))
        self._updating = False
            
    def refresh_nodes(self):
        self.node_table.setRowCount(0)
        
        tab_index = self.filter_tabs.currentIndex()
        filter_type = None
        if tab_index == 1:
            filter_type = "reference"
        elif tab_index == 2:
            filter_type = "aiStandIn"
        elif tab_index == 3:
            filter_type = "RedshiftProxyMesh"
        
        all_nodes = NodeManager.get_all_nodes()
        
        if filter_type:
            nodes = [n for n in all_nodes if cmds.nodeType(n) == filter_type]
        else:
            nodes = all_nodes
        
        self.node_table.setRowCount(len(nodes))
        
        valid_count = 0
        missing_count = 0
        template_count = 0
        ref_count = 0
        arnold_count = 0
        rs_count = 0
        
        for row, node in enumerate(nodes):
            node_type = cmds.nodeType(node)
            
            # Setup proxy attributes (not for references)
            if node_type != "reference":
                NodeManager.setup_proxy(node)
            
            type_def = NODE_TYPES.get(node_type, {})
            type_name = type_def.get("name", "Unknown")
            type_color = type_def.get("icon_color", "#888888")
            
            if node_type == "reference":
                ref_count += 1
            elif node_type == "aiStandIn":
                arnold_count += 1
            elif node_type == "RedshiftProxyMesh":
                rs_count += 1
            
            # Type column
            type_item = QtWidgets.QTableWidgetItem(type_name)
            type_item.setFlags(type_item.flags() & ~QtCore.Qt.ItemIsEditable)
            type_item.setForeground(QtGui.QBrush(QtGui.QColor(type_color)))
            
            # Node name
            node_item = QtWidgets.QTableWidgetItem(node)
            node_item.setFlags(node_item.flags() & ~QtCore.Qt.ItemIsEditable)
            
            # Version
            version = NodeManager.get_version(node)
            version_item = QtWidgets.QTableWidgetItem(version)
            version_item.setFlags(version_item.flags() & ~QtCore.Qt.ItemIsEditable)
            
            # Template
            template = NodeManager.get_template_path(node)
            template_item = QtWidgets.QTableWidgetItem(template if template else "(no template)")
            template_item.setFlags(template_item.flags() & ~QtCore.Qt.ItemIsEditable)
            if template:
                template_count += 1
                template_item.setForeground(QtGui.QBrush(QtGui.QColor("#FFA500")))
            else:
                template_item.setForeground(QtGui.QBrush(QtGui.QColor("#666666")))
            
            # Current path
            current_path = NodeManager.get_current_path(node)
            path_item = QtWidgets.QTableWidgetItem(current_path)
            path_item.setFlags(path_item.flags() & ~QtCore.Qt.ItemIsEditable)
            
            if current_path and os.path.exists(current_path):
                path_item.setForeground(QtGui.QBrush(QtGui.QColor("#88CC88")))
                valid_count += 1
            elif current_path:
                path_item.setForeground(QtGui.QBrush(QtGui.QColor("#CC8888")))
                missing_count += 1
            
            self.node_table.setItem(row, 0, type_item)
            self.node_table.setItem(row, 1, node_item)
            self.node_table.setItem(row, 2, version_item)
            self.node_table.setItem(row, 3, template_item)
            self.node_table.setItem(row, 4, path_item)
        
        self.status_label.setText(
            f"Ref: {ref_count} | Arnold: {arnold_count} | RS: {rs_count} | "
            f"Templated: {template_count} | Valid: {valid_count} | Missing: {missing_count}"
        )
    
    def apply_context(self):
        """Apply context and update all paths"""
        if self._updating:
            return
            
        ep = self.context_fields["ep"].text()
        seq = self.context_fields["seq"].text()
        shot = self.context_fields["shot"].text()
        
        # This triggers callbacks which update all node paths
        ContextManager.set_all(ep=ep, seq=seq, shot=shot)
            
    def on_external_context_change(self):
        self.refresh_context()
        self.refresh_nodes()
        self.update_resolved_preview()
        
    def on_node_selected(self):
        rows = self.node_table.selectionModel().selectedRows()
        if not rows:
            return
            
        row = rows[0].row()
        node = self.node_table.item(row, 1).text()
        
        node_type = cmds.nodeType(node)
        type_def = NODE_TYPES.get(node_type, {})
        type_name = type_def.get("name", "Unknown")
        type_color = type_def.get("icon_color", "#888888")
        
        self.detail_node_label.setText(node)
        self.detail_type_label.setText(type_name)
        self.detail_type_label.setStyleSheet(
            f"color: white; background-color: {type_color}; padding: 2px 6px; border-radius: 3px;"
        )
        
        self.detail_version_edit.setText(NodeManager.get_version(node))
        self.detail_template_edit.setText(NodeManager.get_template_path(node))
        self.update_resolved_preview()
        
        try:
            if node_type != "reference":
                parent = cmds.listRelatives(node, parent=True)
                if parent:
                    cmds.select(parent[0], replace=True)
                else:
                    cmds.select(node, replace=True)
        except:
            pass
        
    def update_resolved_preview(self):
        template = self.detail_template_edit.text()
        version = self.detail_version_edit.text() or "v001"
        
        if template:
            resolved = ContextManager.expand_tokens(template, version)
            self.detail_resolved_label.setText(resolved)
            
            if os.path.exists(resolved):
                self.detail_resolved_label.setStyleSheet("color: #88CC88; padding: 6px; background: #2a2a2a; border-radius: 4px;")
            else:
                self.detail_resolved_label.setStyleSheet("color: #CC8888; padding: 6px; background: #2a2a2a; border-radius: 4px;")
        else:
            self.detail_resolved_label.setText("-")
            self.detail_resolved_label.setStyleSheet("color: #888888; padding: 6px; background: #2a2a2a; border-radius: 4px;")
            
    def set_template_from_current(self):
        """Convert current path to template - FIXED VERSION"""
        node = self.detail_node_label.text()
        if node == "-":
            cmds.warning("Select a node first")
            return
            
        current_path = NodeManager.get_current_path(node)
        if not current_path:
            cmds.warning("Node has no path set")
            return
        
        # Step 1: Detect context from path (SILENT - no callbacks!)
        detected = ContextManager.set_from_path(current_path, silent=True)
        
        # Step 2: Convert path to template using detected context
        template = NodeManager.convert_path_to_template(current_path, context=detected)
        
        # Step 3: Extract version
        version = "v001"
        version_match = re.search(r"[/\\](v\d{3,4})[/\\]", current_path)
        if version_match:
            version = version_match.group(1)
        
        # Step 4: Save template and version to node FIRST
        NodeManager.set_template_path(node, template)
        NodeManager.set_version(node, version)
        
        # Step 5: Update UI
        self.detail_template_edit.setText(template)
        self.detail_version_edit.setText(version)
        self.refresh_context()  # Show detected context in UI
        
        self.update_resolved_preview()
        
        print(f"[ContextVars] Detected context: {detected}")
        print(f"[ContextVars] Template: {template}")
        print(f"[ContextVars] Template saved to node: {node}")
            
    def apply_template(self):
        """Apply template to node and resolve path"""
        node = self.detail_node_label.text()
        if node == "-":
            cmds.warning("Select a node first")
            return
            
        template = self.detail_template_edit.text()
        version = self.detail_version_edit.text() or "v001"
        
        if not template:
            cmds.warning("Enter a template path")
            return
        
        # Save template and version
        NodeManager.set_template_path(node, template)
        NodeManager.set_version(node, version)
        
        # Resolve and apply
        NodeManager.apply_resolved_path(node, reload_ref=True)
        
        self.refresh_nodes()
        print(f"[ContextVars] Applied template to {node}")
        
    def auto_detect_context(self):
        """Detect context from selected node (just updates context, no template change)"""
        sel = cmds.ls(selection=True)
        if not sel:
            cmds.warning("Select a node")
            return
        
        node = None
        
        for s in sel:
            node_type = cmds.nodeType(s)
            if node_type in NODE_TYPES:
                node = s
                break
        
        if not node:
            for s in sel:
                for check_type in NODE_TYPES.keys():
                    if check_type == "reference":
                        continue
                    shapes = cmds.listRelatives(s, shapes=True, type=check_type) or []
                    if shapes:
                        node = shapes[0]
                        break
                if node:
                    break
                    
        if not node:
            cmds.warning("Select a Reference, Arnold StandIn, or Redshift Proxy node")
            return
            
        current_path = NodeManager.get_current_path(node)
        
        if current_path:
            # Silent detection - just update context display
            detected = ContextManager.set_from_path(current_path, silent=True)
            self.refresh_context()
            print(f"[ContextVars] Detected from {current_path}: {detected}")
            
    def register_callback(self):
        register_render_callback()
        cmds.confirmDialog(
            title="Context Variables",
            message="Pre-render callback registered.",
            button=["OK"]
        )


# =============================================================================
# LAUNCH
# =============================================================================

def show():
    """Show the Context Variables UI"""
    global context_vars_window
    
    try:
        context_vars_window.close()
        context_vars_window.deleteLater()
    except:
        pass
        
    context_vars_window = ContextVariablesUI()
    context_vars_window.show()
    return context_vars_window


# =============================================================================
# API
# =============================================================================

def set_context(ep=None, seq=None, shot=None):
    """Set context and auto-update all nodes"""
    ContextManager.set_all(ep=ep, seq=seq, shot=shot)
    
def get_context():
    """Get current context"""
    return ContextManager.get_all()

def resolve_path(template_path, version="v001"):
    """Resolve a template path with current context"""
    return ContextManager.expand_tokens(template_path, version)


if __name__ == "__main__":
    show()